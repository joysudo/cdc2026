"""
Negative Binomial Analysis of 2025 CFPB Credit-Reporting Complaints

Purpose
-------
Analyze geographic associations between 2025 credit-reporting complaint
counts and ZCTA-level socioeconomic/demographic characteristics.

Outcome:
    Number of 2025 CFPB complaints for:
    "Credit reporting or other personal consumer reports"

Model:
    Negative Binomial regression with a population offset.

Interpretation:
    Rate ratios describe the multiplicative change in expected complaint
    rates associated with a one-unit increase in a predictor, holding the
    other variables in that model constant.

IMPORTANT:
    This is a ZCTA-level ecological analysis. It does NOT contain the race
    or socioeconomic characteristics of individual complainants and should
    not be interpreted as individual-level behavior or causation.

Outputs
-------
data/processed/regression/credit_reporting/
    credit_reporting_zcta_regression_data.csv
    negative_binomial_results.csv
    negative_binomial_diagnostics.csv
    negative_binomial_alpha_estimation.csv

    figures/
        demographic_irr_forest.png
        socioeconomic_irr_forest.png
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm


# ============================================================
# 1. PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_COMPLAINTS = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cfpb_2025_cleaned.csv"
)

DEMOGRAPHICS = (
    PROJECT_ROOT
    / "data"
    / "census"
    / "acs_2024_zcta_demographics.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "regression"
    / "credit_reporting"
)

FIGURE_DIR = OUTPUT_DIR / "figures"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. SETTINGS
# ============================================================

CREDIT_REPORTING_PRODUCT = (
    "Credit reporting or other personal consumer reports"
)

# Read the large complaint file in chunks.
CHUNK_SIZE = 250_000

# Iterative estimation settings for Negative Binomial alpha.
MAX_ALPHA_ITERATIONS = 20
ALPHA_TOLERANCE = 1e-6

# Do not use tiny populations in the regression.
# This removes invalid/near-zero population denominators.
MIN_POPULATION = 1


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def clean_zip(series):
    """
    Convert ZIP values to five-digit strings.

    Examples:
        27514.0 -> 27514
        "27514" -> 27514

    Invalid values become NaN.
    """
    s = series.astype("string").str.strip()

    # Remove decimal suffixes such as "27514.0"
    s = s.str.replace(r"\.0$", "", regex=True)

    # Keep only five-digit ZIPs
    s = s.where(s.str.fullmatch(r"\d{5}"))

    return s


def estimate_alpha(y, mu):
    """
    Method-of-moments estimate of the Negative Binomial dispersion parameter.

    For NB2:

        Var(Y) = mu + alpha * mu^2

    Rearranging gives:

        alpha =
            sum((y - mu)^2 - y)
            -------------------
                sum(mu^2)

    Negative estimates are clipped to a small positive number.
    """
    numerator = np.sum((y - mu) ** 2 - y)
    denominator = np.sum(mu ** 2)

    if denominator <= 0:
        return 1e-8

    alpha = numerator / denominator

    return max(alpha, 1e-8)


def fit_nb_with_alpha_iteration(
    y,
    X,
    offset,
    initial_alpha=1.0,
    max_iterations=20,
    tolerance=1e-6,
):
    """
    Iteratively estimate alpha and refit a GLM Negative Binomial model.

    The statsmodels GLM NegativeBinomial family treats alpha as fixed,
    so we estimate alpha externally and repeatedly refit until it stabilizes.
    """

    alpha = initial_alpha
    history = []

    for iteration in range(max_iterations):

        family = sm.families.NegativeBinomial(alpha=alpha)

        model = sm.GLM(
            y,
            X,
            family=family,
            offset=offset,
        )

        result = model.fit()

        mu = result.fittedvalues

        new_alpha = estimate_alpha(y, mu)

        history.append(
            {
                "iteration": iteration,
                "alpha_before": alpha,
                "alpha_after": new_alpha,
            }
        )

        print(
            f"    iteration {iteration + 1}: "
            f"alpha = {new_alpha:.6f}"
        )

        if abs(new_alpha - alpha) < tolerance:
            alpha = new_alpha
            break

        alpha = new_alpha

    # Final fit using stabilized alpha
    family = sm.families.NegativeBinomial(alpha=alpha)

    model = sm.GLM(
        y,
        X,
        family=family,
        offset=offset,
    )

    result = model.fit()

    return result, alpha, pd.DataFrame(history)


def extract_model_results(
    result,
    model_name,
    alpha,
):
    """
    Convert model coefficients to rate ratios and 95% confidence intervals.
    """

    coefficients = result.params
    standard_errors = result.bse
    p_values = result.pvalues

    confidence_intervals = result.conf_int()

    rows = []

    for variable in coefficients.index:

        coefficient = coefficients[variable]
        std_error = standard_errors[variable]

        ci_low = confidence_intervals.loc[variable, 0]
        ci_high = confidence_intervals.loc[variable, 1]

        rate_ratio = np.exp(coefficient)

        ci_lower = np.exp(ci_low)
        ci_upper = np.exp(ci_high)

        rows.append(
            {
                "model": model_name,
                "variable": variable,
                "coefficient": coefficient,
                "rate_ratio": rate_ratio,
                "std_error": std_error,
                "p_value": p_values[variable],
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "alpha": alpha,
            }
        )

    return pd.DataFrame(rows)


def model_diagnostics(
    result,
    model_name,
    alpha,
):
    """
    Calculate useful model diagnostics.
    """

    pearson_chi_square = np.sum(
        result.resid_pearson ** 2
    )

    pearson_df = (
        pearson_chi_square
        / result.df_resid
    )

    return {
        "model": model_name,
        "alpha": alpha,
        "observations": int(result.nobs),
        "residual_df": int(result.df_resid),
        "deviance": result.deviance,
        "pearson_chi_square": pearson_chi_square,
        "pearson_chi_square_df": pearson_df,
        "aic": result.aic,
        "log_likelihood": result.llf,
        "converged": result.converged,
    }


# ============================================================
# 4. LOAD AND FILTER CFPB COMPLAINTS
# ============================================================

print("\n" + "=" * 70)
print("STEP 1: LOAD 2025 CFPB COMPLAINTS")
print("=" * 70)

print(f"\nInput:")
print(RAW_COMPLAINTS)

if not RAW_COMPLAINTS.exists():
    raise FileNotFoundError(
        f"Could not find complaint file:\n{RAW_COMPLAINTS}"
    )


required_columns = [
    "Product",
    "ZIP code",
]


credit_chunks = []

total_rows = 0
credit_rows = 0

for chunk_number, chunk in enumerate(
    pd.read_csv(
        RAW_COMPLAINTS,
        usecols=required_columns,
        dtype={
            "Product": "string",
            "ZIP code": "string",
        },
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ),
    start=1,
):

    total_rows += len(chunk)

    # Keep only the desired CFPB product.
    chunk = chunk[
        chunk["Product"]
        == CREDIT_REPORTING_PRODUCT
    ].copy()

    if len(chunk) == 0:
        continue

    # Clean ZIP codes.
    chunk["ZIP code"] = clean_zip(
        chunk["ZIP code"]
    )

    # Remove invalid / XXXXX / missing ZIPs.
    chunk = chunk[
        chunk["ZIP code"].notna()
    ]

    credit_rows += len(chunk)

    credit_chunks.append(
        chunk[["ZIP code"]]
    )

    if chunk_number % 5 == 0:
        print(
            f"  Processed {total_rows:,} rows | "
            f"credit-reporting rows: {credit_rows:,}"
        )


if not credit_chunks:
    raise RuntimeError(
        "No credit-reporting complaints were found."
    )


credit_complaints = pd.concat(
    credit_chunks,
    ignore_index=True,
)

print("\nFinished reading complaints.")

print(
    f"Total rows processed: "
    f"{total_rows:,}"
)

print(
    f"Valid 2025 credit-reporting complaints: "
    f"{len(credit_complaints):,}"
)


# ============================================================
# 5. AGGREGATE COMPLAINTS BY ZIP
# ============================================================

print("\n" + "=" * 70)
print("STEP 2: AGGREGATE CREDIT-REPORTING COMPLAINTS")
print("=" * 70)

complaint_counts = (
    credit_complaints
    .groupby("ZIP code")
    .size()
    .reset_index(name="complaint_count")
)

print(
    f"ZIP codes with at least one credit-reporting complaint: "
    f"{len(complaint_counts):,}"
)


# ============================================================
# 6. LOAD ACS DEMOGRAPHICS
# ============================================================

print("\n" + "=" * 70)
print("STEP 3: LOAD 2024 ACS ZCTA DEMOGRAPHICS")
print("=" * 70)

if not DEMOGRAPHICS.exists():
    raise FileNotFoundError(
        f"Could not find demographics file:\n{DEMOGRAPHICS}"
    )

demographics = pd.read_csv(
    DEMOGRAPHICS,
    dtype={"ZCTA": "string"},
)

demographics["ZCTA"] = clean_zip(
    demographics["ZCTA"]
)

print(
    f"ACS ZCTAs loaded: "
    f"{len(demographics):,}"
)


# ============================================================
# 7. CHECK REQUIRED DEMOGRAPHIC VARIABLES
# ============================================================

required_demographic_columns = [
    "ZCTA",
    "population",
    "median_household_income",
    "poverty_percent",
    "unemployment_percent",
    "white_percent",
    "black_percent",
    "american_indian_alaska_native_percent",
    "asian_percent",
    "native_hawaiian_pacific_islander_percent",
    "other_race_percent",
    "two_or_more_races_percent",
    "hispanic_percent",
    "median_age",
]

missing_columns = [
    col
    for col in required_demographic_columns
    if col not in demographics.columns
]

if missing_columns:
    raise ValueError(
        "The demographics file is missing these columns:\n"
        + "\n".join(missing_columns)
    )


# ============================================================
# 8. EXCLUDE PUERTO RICO
# ============================================================

print("\nExcluding Puerto Rico ZCTAs.")

# Puerto Rico ZIP/ZCTA prefixes are 006-009.
demographics = demographics[
    ~demographics["ZCTA"].str.startswith(
        ("006", "007", "008", "009"),
        na=False,
    )
].copy()


# ============================================================
# 9. MERGE COMPLAINTS WITH ALL ZCTAs
# ============================================================

print("\n" + "=" * 70)
print("STEP 4: CREATE ANALYSIS DATASET")
print("=" * 70)

analysis = demographics.merge(
    complaint_counts,
    left_on="ZCTA",
    right_on="ZIP code",
    how="left",
)

analysis["complaint_count"] = (
    analysis["complaint_count"]
    .fillna(0)
    .astype(int)
)

analysis = analysis.drop(
    columns=["ZIP code"],
    errors="ignore",
)

# Only retain areas with positive population.
analysis = analysis[
    analysis["population"] >= MIN_POPULATION
].copy()


# ============================================================
# 10. CALCULATE COMPLAINT RATE
# ============================================================

analysis["complaints_per_1000"] = (
    analysis["complaint_count"]
    / analysis["population"]
    * 1000
)


print(
    f"Final ZCTAs in analysis: "
    f"{len(analysis):,}"
)

print(
    f"ZCTAs with zero complaints: "
    f"{(analysis['complaint_count'] == 0).sum():,}"
)

print(
    f"ZCTAs with complaints: "
    f"{(analysis['complaint_count'] > 0).sum():,}"
)

print(
    f"Total credit-reporting complaints: "
    f"{analysis['complaint_count'].sum():,}"
)

print(
    f"Total population represented: "
    f"{analysis['population'].sum():,}"
)


# ============================================================
# 11. REMOVE ROWS WITH MISSING MODEL VARIABLES
# ============================================================

predictors = [
    "income_10k",
    "poverty_percent",
    "unemployment_percent",
    "median_age",
    "white_percent",
    "black_percent",
    "american_indian_alaska_native_percent",
    "asian_percent",
    "native_hawaiian_pacific_islander_percent",
    "other_race_percent",
    "two_or_more_races_percent",
    "hispanic_percent",
]

# Create income in $10,000 units.
analysis["income_10k"] = (
    analysis["median_household_income"]
    / 10_000
)

required_model_columns = [
    "ZCTA",
    "complaint_count",
    "population",
] + predictors

before = len(analysis)

analysis = analysis.dropna(
    subset=required_model_columns
).copy()

after = len(analysis)

print(
    f"\nRows removed due to missing model data: "
    f"{before - after:,}"
)

print(
    f"Final regression observations: "
    f"{after:,}"
)


# ============================================================
# 12. SAVE CANONICAL REGRESSION DATASET
# ============================================================

regression_output = (
    OUTPUT_DIR
    / "credit_reporting_zcta_regression_data.csv"
)

analysis.to_csv(
    regression_output,
    index=False,
)

print(
    f"\nSaved regression dataset:\n"
    f"{regression_output}"
)


# ============================================================
# 13. PREPARE MODEL VARIABLES
# ============================================================

y = analysis["complaint_count"].astype(float)

# Population offset:
#
# log(E[Y]) =
#     X beta + log(population)
#
# This converts the count model into a model of complaint rates.
offset = np.log(
    analysis["population"].astype(float)
)


# ============================================================
# 14. BASELINE SOCIOECONOMIC MODEL
# ============================================================

print("\n" + "=" * 70)
print("STEP 5: BASELINE NEGATIVE BINOMIAL MODEL")
print("=" * 70)

baseline_variables = [
    "income_10k",
    "poverty_percent",
    "unemployment_percent",
    "median_age",
]

X_baseline = analysis[
    baseline_variables
].copy()

X_baseline = sm.add_constant(
    X_baseline,
    has_constant="add",
)

print("\nVariables:")
print(
    ["Intercept"] + baseline_variables
)

baseline_result, baseline_alpha, baseline_alpha_history = (
    fit_nb_with_alpha_iteration(
        y=y,
        X=X_baseline,
        offset=offset,
        initial_alpha=1.0,
        max_iterations=MAX_ALPHA_ITERATIONS,
        tolerance=ALPHA_TOLERANCE,
    )
)

print(
    f"\nFinal baseline alpha: "
    f"{baseline_alpha:.6f}"
)


# ============================================================
# 15. SAVE BASELINE RESULTS
# ============================================================

all_results = []

baseline_results = extract_model_results(
    baseline_result,
    "baseline",
    baseline_alpha,
)

all_results.append(
    baseline_results
)


# ============================================================
# 16. SEPARATE DEMOGRAPHIC MODELS
# ============================================================

print("\n" + "=" * 70)
print("STEP 6: DEMOGRAPHIC NEGATIVE BINOMIAL MODELS")
print("=" * 70)

demographic_variables = [
    "white_percent",
    "black_percent",
    "american_indian_alaska_native_percent",
    "asian_percent",
    "native_hawaiian_pacific_islander_percent",
    "other_race_percent",
    "two_or_more_races_percent",
    "hispanic_percent",
]

demographic_model_names = {
    "white_percent": "white",
    "black_percent": "black",
    "american_indian_alaska_native_percent":
        "american_indian_alaska_native",
    "asian_percent": "asian",
    "native_hawaiian_pacific_islander_percent":
        "native_hawaiian_pacific_islander",
    "other_race_percent": "other_race",
    "two_or_more_races_percent":
        "two_or_more_races",
    "hispanic_percent": "hispanic",
}

alpha_histories = [
    baseline_alpha_history.assign(
        model="baseline"
    )
]

diagnostics = [
    model_diagnostics(
        baseline_result,
        "baseline",
        baseline_alpha,
    )
]


for demographic_variable in demographic_variables:

    model_name = demographic_model_names[
        demographic_variable
    ]

    print(
        f"\n--- {model_name} model ---"
    )

    # Each model controls for the same socioeconomic variables
    # while adding ONE demographic characteristic.
    model_variables = (
        baseline_variables
        + [demographic_variable]
    )

    X = analysis[
        model_variables
    ].copy()

    X = sm.add_constant(
        X,
        has_constant="add",
    )

    result, alpha, alpha_history = (
        fit_nb_with_alpha_iteration(
            y=y,
            X=X,
            offset=offset,
            initial_alpha=baseline_alpha,
            max_iterations=MAX_ALPHA_ITERATIONS,
            tolerance=ALPHA_TOLERANCE,
        )
    )

    model_results = extract_model_results(
        result,
        model_name,
        alpha,
    )

    all_results.append(
        model_results
    )

    alpha_histories.append(
        alpha_history.assign(
            model=model_name
        )
    )

    diagnostics.append(
        model_diagnostics(
            result,
            model_name,
            alpha,
        )
    )


# ============================================================
# 17. COMBINE RESULTS
# ============================================================

results_df = pd.concat(
    all_results,
    ignore_index=True,
)

diagnostics_df = pd.DataFrame(
    diagnostics
)

alpha_df = pd.concat(
    alpha_histories,
    ignore_index=True,
)


# ============================================================
# 18. SAVE MODEL RESULTS
# ============================================================

results_path = (
    OUTPUT_DIR
    / "negative_binomial_results.csv"
)

diagnostics_path = (
    OUTPUT_DIR
    / "negative_binomial_diagnostics.csv"
)

alpha_path = (
    OUTPUT_DIR
    / "negative_binomial_alpha_estimation.csv"
)

results_df.to_csv(
    results_path,
    index=False,
)

diagnostics_df.to_csv(
    diagnostics_path,
    index=False,
)

alpha_df.to_csv(
    alpha_path,
    index=False,
)

print("\n" + "=" * 70)
print("MODEL RESULTS SAVED")
print("=" * 70)

print(results_path)
print(diagnostics_path)
print(alpha_path)


# ============================================================
# 19. PRINT IMPORTANT RESULTS
# ============================================================

print("\n" + "=" * 70)
print("DEMOGRAPHIC RATE RATIOS")
print("=" * 70)

demographic_results = results_df[
    results_df["variable"].isin(
        demographic_variables
    )
].copy()

demographic_results["percent_change"] = (
    (demographic_results["rate_ratio"] - 1)
    * 100
)

display_columns = [
    "model",
    "variable",
    "rate_ratio",
    "ci_lower",
    "ci_upper",
    "p_value",
    "percent_change",
]

print(
    demographic_results[
        display_columns
    ].to_string(index=False)
)


# ============================================================
# 20. FOREST PLOT: DEMOGRAPHIC VARIABLES
# ============================================================

print("\n" + "=" * 70)
print("CREATING DEMOGRAPHIC FOREST PLOT")
print("=" * 70)

plot_df = demographic_results.copy()

label_map = {
    "white_percent":
        "White %",
    "black_percent":
        "Black %",
    "american_indian_alaska_native_percent":
        "American Indian / Alaska Native %",
    "asian_percent":
        "Asian %",
    "native_hawaiian_pacific_islander_percent":
        "Native Hawaiian / Pacific Islander %",
    "other_race_percent":
        "Other race %",
    "two_or_more_races_percent":
        "Two or more races %",
    "hispanic_percent":
        "Hispanic %",
}

plot_df["label"] = plot_df[
    "variable"
].map(label_map)

# Sort from lowest to highest IRR.
plot_df = plot_df.sort_values(
    "rate_ratio"
).reset_index(drop=True)

y_positions = np.arange(
    len(plot_df)
)

fig, ax = plt.subplots(
    figsize=(10, 6.5)
)

ax.errorbar(
    plot_df["rate_ratio"],
    y_positions,
    xerr=[
        plot_df["rate_ratio"]
        - plot_df["ci_lower"],

        plot_df["ci_upper"]
        - plot_df["rate_ratio"],
    ],
    fmt="o",
    capsize=4,
    markersize=6,
)

# No-association reference line.
ax.axvline(
    1.0,
    linestyle="--",
    linewidth=1.2,
)

ax.set_yticks(
    y_positions
)

ax.set_yticklabels(
    plot_df["label"]
)

ax.set_xlim(
    0.94,
    1.09
)

ax.set_xlabel(
    "Incidence Rate Ratio (IRR)"
)

ax.set_title(
    "Community Demographic Characteristics\n"
    "Associated With Credit-Reporting Complaint Rates"
)

ax.grid(
    axis="x",
    alpha=0.2,
)

plt.tight_layout()

demographic_figure = (
    FIGURE_DIR
    / "demographic_irr_forest.png"
)

plt.savefig(
    demographic_figure,
    dpi=300,
    bbox_inches="tight",
)

plt.show()

print(
    f"Saved:\n{demographic_figure}"
)


# ============================================================
# 21. SOCIOECONOMIC MODEL
# ============================================================

print("\n" + "=" * 70)
print("PREPARING SOCIOECONOMIC FOREST PLOT")
print("=" * 70)

baseline_plot = results_df[
    results_df["model"] == "baseline"
].copy()

baseline_plot = baseline_plot[
    baseline_plot["variable"].isin(
        baseline_variables
    )
].copy()


# ------------------------------------------------------------
# IMPORTANT:
#
# The raw coefficients have different units.
#
# We transform them into meaningful changes:
#
# income       = +$10,000
# poverty      = +10 percentage points
# unemployment = +10 percentage points
# median age   = +10 years
# ------------------------------------------------------------

scales = {
    "income_10k": 1,
    "poverty_percent": 10,
    "unemployment_percent": 10,
    "median_age": 10,
}

labels = {
    "income_10k":
        "+$10,000 median household income",

    "poverty_percent":
        "+10 percentage points poverty",

    "unemployment_percent":
        "+10 percentage points unemployment",

    "median_age":
        "+10 years median age",
}


socio_rows = []

for _, row in baseline_plot.iterrows():

    variable = row["variable"]

    scale = scales[variable]

    # Transform coefficient and confidence limits.
    transformed_irr = np.exp(
        np.log(row["rate_ratio"])
        * scale
    )

    transformed_lower = np.exp(
        np.log(row["ci_lower"])
        * scale
    )

    transformed_upper = np.exp(
        np.log(row["ci_upper"])
        * scale
    )

    socio_rows.append(
        {
            "variable": variable,
            "label": labels[variable],
            "rate_ratio": transformed_irr,
            "ci_lower": transformed_lower,
            "ci_upper": transformed_upper,
            "p_value": row["p_value"],
        }
    )


socio_df = pd.DataFrame(
    socio_rows
)

socio_df = socio_df.sort_values(
    "rate_ratio"
).reset_index(drop=True)


# ============================================================
# 22. FOREST PLOT: SOCIOECONOMIC VARIABLES
# ============================================================

y_positions = np.arange(
    len(socio_df)
)

fig, ax = plt.subplots(
    figsize=(10, 5)
)

ax.errorbar(
    socio_df["rate_ratio"],
    y_positions,
    xerr=[
        socio_df["rate_ratio"]
        - socio_df["ci_lower"],

        socio_df["ci_upper"]
        - socio_df["rate_ratio"],
    ],
    fmt="o",
    capsize=4,
    markersize=6,
)

ax.axvline(
    1.0,
    linestyle="--",
    linewidth=1.2,
)

ax.set_yticks(
    y_positions
)

ax.set_yticklabels(
    socio_df["label"]
)

ax.set_xlabel(
    "Incidence Rate Ratio (IRR)"
)

ax.set_title(
    "Socioeconomic Characteristics\n"
    "Associated With Credit-Reporting Complaint Rates"
)

ax.grid(
    axis="x",
    alpha=0.2,
)

plt.tight_layout()

socioeconomic_figure = (
    FIGURE_DIR
    / "socioeconomic_irr_forest.png"
)

plt.savefig(
    socioeconomic_figure,
    dpi=300,
    bbox_inches="tight",
)

plt.show()

print(
    f"Saved:\n{socioeconomic_figure}"
)


# ============================================================
# 23. FINAL MODEL DIAGNOSTICS
# ============================================================

print("\n" + "=" * 70)
print("MODEL DIAGNOSTICS")
print("=" * 70)

print(
    diagnostics_df[
        [
            "model",
            "alpha",
            "observations",
            "pearson_chi_square_df",
            "aic",
            "converged",
        ]
    ].to_string(index=False)
)


# ============================================================
# 24. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)

print(
    "\nThe analysis uses:"
)

print(
    f"  • 2025 CFPB credit-reporting complaints only"
)

print(
    f"  • {len(analysis):,} ZCTAs"
)

print(
    f"  • {analysis['complaint_count'].sum():,} complaints"
)

print(
    f"  • 2024 ACS population and community characteristics"
)

print(
    f"  • Negative Binomial regression"
)

print(
    f"  • Population offset: log(population)"
)

print(
    f"  • Estimated overdispersion parameter"
)

print(
    f"\nFigures:"
)

print(
    f"  • {demographic_figure}"
)

print(
    f"  • {socioeconomic_figure}"
)