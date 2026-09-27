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
    PROJECT_ROOT /
    "data/processed/regression/"
    "zcta_regression_data.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT /
    "data/processed/regression/results"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(INPUT)


# ============================================================
# MODEL VARIABLES
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
# COMPLETE CASE DATA
# ============================================================

model_df = df.dropna(
    subset=base_variables + race_variables
).copy()


# ============================================================
# TRANSFORMATIONS
# ============================================================

model_df["income_10k"] = (
    model_df["median_household_income"]
    / 10_000
)

model_df["log_population"] = np.log(
    model_df["population"]
)


# ============================================================
# BASE FORMULA
# ============================================================

base_formula = """
complaints ~
income_10k +
poverty_percent +
unemployment_percent +
median_age
"""


# ============================================================
# MODELS
# ============================================================

models = {
    "baseline": base_formula,

    "white": base_formula +
        " + white_percent",

    "black": base_formula +
        " + black_percent",

    "american_indian_alaska_native":
        base_formula +
        " + american_indian_alaska_native_percent",

    "asian": base_formula +
        " + asian_percent",

    "native_hawaiian_pacific_islander":
        base_formula +
        " + native_hawaiian_pacific_islander_percent",

    "other_race": base_formula +
        " + other_race_percent",

    "two_or_more_races":
        base_formula +
        " + two_or_more_races_percent",

    "hispanic":
        base_formula +
        " + hispanic_percent",
}


# ============================================================
# FIT MODELS
# ============================================================

results = []


for name, formula in models.items():

    print("\n" + "=" * 80)
    print(f"POISSON MODEL: {name.upper()}")
    print("=" * 80)

    model = smf.glm(
        formula=formula,
        data=model_df,
        family=sm.families.Poisson(),
        offset=model_df["log_population"]
    ).fit()

    print(model.summary())


    # --------------------------------------------------------
    # RATE RATIOS
    # --------------------------------------------------------

    rate_ratios = np.exp(
        model.params
    )


    # --------------------------------------------------------
    # SAVE COEFFICIENT RESULTS
    # --------------------------------------------------------

    for variable in model.params.index:

        results.append({
            "model": name,
            "variable": variable,
            "coefficient": model.params[variable],
            "rate_ratio": rate_ratios[variable],
            "std_error": model.bse[variable],
            "p_value": model.pvalues[variable],
            "ci_lower": model.conf_int().loc[
                variable, 0
            ],
            "ci_upper": model.conf_int().loc[
                variable, 1
            ],
        })


    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------

    pearson_ratio = (
        model.pearson_chi2 /
        model.df_resid
    )

    print(
        f"\nPearson chi-square / df: "
        f"{pearson_ratio:.2f}"
    )

    print(
        f"AIC: {model.aic:,.2f}"
    )


# ============================================================
# SAVE COMPARISON TABLE
# ============================================================

results_df = pd.DataFrame(results)

results_file = (
    OUTPUT_DIR /
    "poisson_model_comparison.csv"
)

results_df.to_csv(
    results_file,
    index=False
)


print("\n" + "=" * 80)
print("POISSON MODEL COMPARISON")
print("=" * 80)

print(
    results_df.to_string(
        index=False
    )
)

print("\nSaved to:")
print(results_file)