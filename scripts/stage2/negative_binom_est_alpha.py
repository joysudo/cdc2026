from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    PROJECT_ROOT
    / "data/processed/regression/zcta_regression_data.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data/processed/regression/results"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(INPUT)


# ============================================================
# VARIABLES
# ============================================================

base_variables = [
    "complaints",
    "population",
    "median_household_income",
    "poverty_percent",
    "unemployment_percent",
    "median_age",
]

race_variables = [
    "white_percent",
    "black_percent",
    "american_indian_alaska_native_percent",
    "asian_percent",
    "native_hawaiian_pacific_islander_percent",
    "other_race_percent",
    "two_or_more_races_percent",
    "hispanic_percent",
]


# ============================================================
# KEEP COMPLETE OBSERVATIONS
# ============================================================

model_df = df.dropna(
    subset=base_variables + race_variables
).copy()


if len(model_df) == 0:
    raise ValueError("No complete observations available.")


# ============================================================
# VALIDATE POPULATION
# ============================================================

if (model_df["population"] <= 0).any():
    raise ValueError(
        "Found observations with population <= 0."
    )


if (model_df["complaints"] < 0).any():
    raise ValueError(
        "Found negative complaint counts."
    )


# ============================================================
# TRANSFORMATIONS
# ============================================================

model_df["income_10k"] = (
    model_df["median_household_income"] / 10_000
)

model_df["log_population"] = np.log(
    model_df["population"]
)


# ============================================================
# FORMULAS
# ============================================================

base_formula = """
complaints ~
income_10k +
poverty_percent +
unemployment_percent +
median_age
"""


models = {
    "baseline": base_formula,

    "white":
        base_formula +
        " + white_percent",

    "black":
        base_formula +
        " + black_percent",

    "american_indian_alaska_native":
        base_formula +
        " + american_indian_alaska_native_percent",

    "asian":
        base_formula +
        " + asian_percent",

    "native_hawaiian_pacific_islander":
        base_formula +
        " + native_hawaiian_pacific_islander_percent",

    "other_race":
        base_formula +
        " + other_race_percent",

    "two_or_more_races":
        base_formula +
        " + two_or_more_races_percent",

    "hispanic":
        base_formula +
        " + hispanic_percent",
}


# ============================================================
# ESTIMATE ALPHA
# ============================================================
#
# Negative Binomial NB2 variance:
#
#     Var(Y_i) = mu_i + alpha * mu_i^2
#
# Therefore:
#
#     E[(Y_i - mu_i)^2 - Y_i] = alpha * mu_i^2
#
# The aggregate method-of-moments estimator is:
#
#     alpha =
#       sum[(Y_i - mu_i)^2 - Y_i]
#       --------------------------------
#              sum(mu_i^2)
#
# We first fit Poisson to obtain mu.
#
# Then we iteratively:
#
#   1. Fit NB using current alpha
#   2. Get new fitted means
#   3. Re-estimate alpha
#   4. Repeat until alpha stabilizes
#
# This is NOT the unstable discrete NB MLE that previously
# failed to converge.
# ============================================================

print("\n" + "=" * 80)
print("NEGATIVE BINOMIAL DISPERSION ESTIMATION")
print("=" * 80)

print(
    f"Observations used: {len(model_df):,}"
)

print(
    f"Mean complaints: "
    f"{model_df['complaints'].mean():,.4f}"
)

print(
    f"Variance of complaints: "
    f"{model_df['complaints'].var():,.4f}"
)


# ============================================================
# STEP 1: BASELINE POISSON
# ============================================================

print("\nFitting baseline Poisson...")

poisson_model = smf.glm(
    formula=base_formula,
    data=model_df,
    family=sm.families.Poisson(),
    offset=model_df["log_population"]
).fit()

mu = np.asarray(
    poisson_model.fittedvalues,
    dtype=float
)

y = np.asarray(
    model_df["complaints"],
    dtype=float
)


# ============================================================
# ALPHA ESTIMATOR
# ============================================================

def estimate_alpha(y, mu):
    """
    Aggregate method-of-moments estimator for NB2:

        Var(Y) = mu + alpha * mu^2

        alpha =
            sum((y - mu)^2 - y)
            ------------------
                 sum(mu^2)
    """

    numerator = np.sum(
        (y - mu) ** 2 - y
    )

    denominator = np.sum(
        mu ** 2
    )

    if denominator <= 0:
        raise ValueError(
            "Cannot estimate alpha: "
            "sum(mu^2) <= 0."
        )

    alpha = numerator / denominator

    # Numerical safeguard.
    # Alpha must be positive for the NB model.
    return max(float(alpha), 1e-8)


# ============================================================
# INITIAL ALPHA
# ============================================================

alpha = estimate_alpha(
    y,
    mu
)

print(
    f"\nInitial alpha from Poisson: "
    f"{alpha:.8f}"
)


# ============================================================
# ITERATIVELY REFINE ALPHA
# ============================================================

MAX_ITERATIONS = 20
TOLERANCE = 1e-6

alpha_history = []

for iteration in range(1, MAX_ITERATIONS + 1):

    nb_model = smf.glm(
        formula=base_formula,
        data=model_df,
        family=sm.families.NegativeBinomial(
            alpha=alpha
        ),
        offset=model_df["log_population"]
    ).fit()

    new_mu = np.asarray(
        nb_model.fittedvalues,
        dtype=float
    )

    new_alpha = estimate_alpha(
        y,
        new_mu
    )

    alpha_history.append({
        "iteration": iteration,
        "alpha_before": alpha,
        "alpha_after": new_alpha,
        "difference": abs(new_alpha - alpha),
    })

    print(
        f"Iteration {iteration:2d}: "
        f"alpha = {new_alpha:.8f} "
        f"(change = {abs(new_alpha - alpha):.8f})"
    )

    if abs(new_alpha - alpha) < TOLERANCE:
        alpha = new_alpha
        print(
            f"\nAlpha converged after "
            f"{iteration} iterations."
        )
        break

    alpha = new_alpha

else:
    print(
        "\nWARNING: Alpha did not converge within "
        f"{MAX_ITERATIONS} iterations."
    )


# ============================================================
# SAVE ALPHA ESTIMATION HISTORY
# ============================================================

alpha_history_df = pd.DataFrame(
    alpha_history
)

alpha_history_file = (
    OUTPUT_DIR
    / "negative_binomial_alpha_estimation.csv"
)

alpha_history_df.to_csv(
    alpha_history_file,
    index=False
)


# ============================================================
# FINAL ALPHA
# ============================================================

print("\n" + "=" * 80)
print("FINAL DISPERSION PARAMETER")
print("=" * 80)

print(
    f"Estimated alpha: {alpha:.8f}"
)

print(
    "\nNegative Binomial variance function:"
)

print(
    f"Var(Y) = mu + {alpha:.8f} * mu^2"
)


# ============================================================
# FIT ALL 9 NEGATIVE BINOMIAL MODELS
# ============================================================

coefficient_results = []
diagnostic_results = []


for name, formula in models.items():

    print("\n" + "=" * 80)
    print(
        f"NEGATIVE BINOMIAL MODEL: "
        f"{name.upper()}"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # FIT
    # --------------------------------------------------------

    model = smf.glm(
        formula=formula,
        data=model_df,
        family=sm.families.NegativeBinomial(
            alpha=alpha
        ),
        offset=model_df["log_population"]
    ).fit()

    print(model.summary())


    # --------------------------------------------------------
    # COEFFICIENTS
    # --------------------------------------------------------

    rate_ratios = np.exp(
        model.params
    )

    confidence_intervals = (
        model.conf_int()
    )


    for variable in model.params.index:

        coefficient_results.append({
            "model": name,
            "variable": variable,
            "coefficient": model.params[variable],
            "rate_ratio": rate_ratios[variable],
            "std_error": model.bse[variable],
            "p_value": model.pvalues[variable],
            "ci_lower": np.exp(
                confidence_intervals.loc[
                    variable, 0
                ]
            ),
            "ci_upper": np.exp(
                confidence_intervals.loc[
                    variable, 1
                ]
            ),
        })


    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------

    pearson_chi2 = (
        model.pearson_chi2
    )

    residual_df = (
        model.df_resid
    )

    pearson_ratio = (
        pearson_chi2 /
        residual_df
    )


    diagnostic_results.append({
        "model": name,
        "alpha": alpha,
        "observations": int(model.nobs),
        "residual_df": int(model.df_resid),
        "deviance": model.deviance,
        "pearson_chi_square": pearson_chi2,
        "pearson_chi_square_df": pearson_ratio,
        "aic": model.aic,
        "log_likelihood": model.llf,
        "converged": True,
    })


    print(
        f"\nAlpha used: {alpha:.8f}"
    )

    print(
        f"Pearson chi-square: "
        f"{pearson_chi2:,.2f}"
    )

    print(
        f"Pearson chi-square / df: "
        f"{pearson_ratio:.4f}"
    )

    print(
        f"AIC: {model.aic:,.2f}"
    )

    print(
        f"Log-likelihood: "
        f"{model.llf:,.2f}"
    )


# ============================================================
# RESULTS DATAFRAMES
# ============================================================

coefficient_df = pd.DataFrame(
    coefficient_results
)

diagnostic_df = pd.DataFrame(
    diagnostic_results
)


# ============================================================
# IMPORTANT:
# ALPHA IS NOT A REGRESSION COEFFICIENT
# ============================================================
#
# Therefore alpha is deliberately NOT included in
# negative_binomial_model_comparison.csv.
#
# It belongs in the diagnostics table instead.
# ============================================================


# ============================================================
# SAVE RESULTS
# ============================================================

coefficient_file = (
    OUTPUT_DIR
    / "negative_binomial_model_comparison.csv"
)

diagnostic_file = (
    OUTPUT_DIR
    / "negative_binomial_model_diagnostics.csv"
)

coefficient_df.to_csv(
    coefficient_file,
    index=False
)

diagnostic_df.to_csv(
    diagnostic_file,
    index=False
)


# ============================================================
# CLEAN SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("NEGATIVE BINOMIAL MODEL COMPARISON")
print("=" * 80)

print(
    coefficient_df.to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("NEGATIVE BINOMIAL DIAGNOSTICS")
print("=" * 80)

print(
    diagnostic_df.to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(
    f"Coefficient results:\n"
    f"{coefficient_file}"
)

print(
    f"\nModel diagnostics:\n"
    f"{diagnostic_file}"
)

print(
    f"\nAlpha estimation history:\n"
    f"{alpha_history_file}"
)

print("\nDone.")