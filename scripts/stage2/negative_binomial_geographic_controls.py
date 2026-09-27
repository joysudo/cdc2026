"""
Geographic robustness analysis for 2025 CFPB credit-reporting complaints.

Purpose
-------
Test whether the associations between ZCTA-level demographic composition
and 2025 credit-reporting complaint rates persist after controlling for
state-level geographic differences.

Models
------
For each demographic variable:

1. Socioeconomic controls only
2. Socioeconomic controls + state fixed effects

Demographic variables:
    - black_percent
    - asian_percent

Outcome:
    complaint_count

Model:
    Negative Binomial GLM with a population offset.

Important interpretation
------------------------
This is a ZCTA-level ecological analysis.

The CFPB complaint data do NOT contain complainant race. Therefore,
the Black/Asian variables describe the racial composition of the
geographic area, not the race of individual complainants.

The analysis estimates associations, not causal effects.

State fixed effects account for differences between states, but they
do not completely account for local spatial dependence between
neighboring ZCTAs.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import statsmodels.api as sm


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ------------------------------------------------------------
# Regression dataset
# ------------------------------------------------------------
REGRESSION_DATA = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "regression"
    / "credit_reporting"
    / "credit_reporting_zcta_regression_data.csv"
)

# ------------------------------------------------------------
# 2024 ZCTA shapefile
# ------------------------------------------------------------
ZCTA_SHAPEFILE = (
    PROJECT_ROOT
    / "data"
    / "census"
    / "zcta"
    / "tl_2024_us_zcta520.shp"
)

# ------------------------------------------------------------
# 2024 State shapefile
# ------------------------------------------------------------
STATE_SHAPEFILE = (
    PROJECT_ROOT
    / "data"
    / "census"
    / "states"
    / "tl_2024_us_state.shp"
)

# ------------------------------------------------------------
# Output directory
# ------------------------------------------------------------
OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "regression"
    / "credit_reporting"
    / "geographic_controls"
)

FIGURE_DIR = OUTPUT_DIR / "figures"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# 2. MODEL SETTINGS
# ============================================================

ALPHA_TOLERANCE = 1e-6
MAX_ALPHA_ITERATIONS = 20


# ============================================================
# 3. NEGATIVE BINOMIAL FUNCTIONS
# ============================================================

def estimate_alpha(y, mu):
    """
    Estimate the NB2 dispersion parameter alpha using:

        Var(Y) = mu + alpha * mu^2

    Method-of-moments estimator:

        alpha =
        sum[(y - mu)^2 - y] / sum(mu^2)
    """

    numerator = np.sum(
        (y - mu) ** 2 - y
    )

    denominator = np.sum(
        mu ** 2
    )

    if denominator <= 0:
        return 1e-8

    alpha = numerator / denominator

    return max(
        float(alpha),
        1e-8,
    )


def fit_negative_binomial(
    y,
    X,
    offset,
    initial_alpha=1.0,
    max_iterations=20,
    tolerance=1e-6,
):
    """
    Iteratively estimate alpha and fit a Negative Binomial GLM.
    """

    alpha = initial_alpha

    history = []

    for iteration in range(
        max_iterations
    ):

        family = (
            sm.families.NegativeBinomial(
                alpha=alpha
            )
        )

        model = sm.GLM(
            y,
            X,
            family=family,
            offset=offset,
        )

        result = model.fit()

        mu = result.fittedvalues

        new_alpha = estimate_alpha(
            y,
            mu,
        )

        history.append(
            {
                "iteration": iteration + 1,
                "alpha_before": alpha,
                "alpha_after": new_alpha,
            }
        )

        print(
            f"        Iteration {iteration + 1}: "
            f"alpha = {new_alpha:.6f}"
        )

        if abs(
            new_alpha - alpha
        ) < tolerance:

            alpha = new_alpha

            break

        alpha = new_alpha

    # --------------------------------------------------------
    # Final model using stabilized alpha
    # --------------------------------------------------------

    family = (
        sm.families.NegativeBinomial(
            alpha=alpha
        )
    )

    model = sm.GLM(
        y,
        X,
        family=family,
        offset=offset,
    )

    result = model.fit()

    return (
        result,
        alpha,
        pd.DataFrame(history),
    )


# ============================================================
# 4. EXTRACT MODEL COEFFICIENT
# ============================================================

def extract_coefficient(
    result,
    variable,
    model_name,
    alpha,
):
    """
    Extract coefficient, IRR, confidence interval, and p-value.
    """

    coefficient = result.params[
        variable
    ]

    standard_error = result.bse[
        variable
    ]

    p_value = result.pvalues[
        variable
    ]

    confidence_interval = (
        result.conf_int()
        .loc[variable]
    )

    lower_coefficient = (
        confidence_interval.iloc[0]
    )

    upper_coefficient = (
        confidence_interval.iloc[1]
    )

    return {
        "model": model_name,
        "variable": variable,
        "coefficient": coefficient,
        "rate_ratio": np.exp(
            coefficient
        ),
        "std_error": standard_error,
        "p_value": p_value,
        "ci_lower": np.exp(
            lower_coefficient
        ),
        "ci_upper": np.exp(
            upper_coefficient
        ),
        "alpha": alpha,
    }


# ============================================================
# 5. MODEL DIAGNOSTICS
# ============================================================

def get_diagnostics(
    result,
    model_name,
    alpha,
):
    """
    Calculate basic Negative Binomial diagnostics.
    """

    pearson_chi_square = np.sum(
        result.resid_pearson ** 2
    )

    pearson_ratio = (
        pearson_chi_square
        / result.df_resid
    )

    return {
        "model": model_name,
        "alpha": alpha,
        "observations": int(
            result.nobs
        ),
        "residual_df": int(
            result.df_resid
        ),
        "pearson_chi_square": (
            pearson_chi_square
        ),
        "pearson_chi_square_df": (
            pearson_ratio
        ),
        "deviance": result.deviance,
        "aic": result.aic,
        "log_likelihood": result.llf,
        "converged": result.converged,
    }


# ============================================================
# 6. LOAD REGRESSION DATA
# ============================================================

print("\n" + "=" * 75)
print("STEP 1: LOAD REGRESSION DATA")
print("=" * 75)

if not REGRESSION_DATA.exists():

    raise FileNotFoundError(
        f"""
Could not find the regression dataset:

{REGRESSION_DATA}

Run your credit-reporting negative-binomial analysis first.
"""
    )

df = pd.read_csv(
    REGRESSION_DATA,
    dtype={
        "ZCTA": "string"
    },
)

# Standardize ZCTA format.
df["ZCTA"] = (
    df["ZCTA"]
    .astype("string")
    .str.strip()
    .str.replace(
        r"\.0$",
        "",
        regex=True,
    )
    .str.zfill(5)
)

print(
    f"Regression observations: "
    f"{len(df):,}"
)

print(
    f"Columns available: "
    f"{len(df.columns)}"
)


# ============================================================
# 7. CHECK REQUIRED REGRESSION VARIABLES
# ============================================================

required_columns = [
    "ZCTA",
    "complaint_count",
    "population",
    "income_10k",
    "poverty_percent",
    "unemployment_percent",
    "median_age",
    "black_percent",
    "asian_percent",
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:

    raise ValueError(
        "The regression dataset is missing "
        "these required columns:\n"
        + "\n".join(
            missing_columns
        )
    )


# ============================================================
# 8. LOAD ZCTA SHAPEFILE
# ============================================================

print("\n" + "=" * 75)
print("STEP 2: LOAD ZCTA SHAPEFILE")
print("=" * 75)

if not ZCTA_SHAPEFILE.exists():

    raise FileNotFoundError(
        f"""
Could not find:

{ZCTA_SHAPEFILE}
"""
    )

zcta = gpd.read_file(
    ZCTA_SHAPEFILE
)

print(
    f"ZCTA polygons: "
    f"{len(zcta):,}"
)

print(
    "\nZCTA shapefile columns:"
)

print(
    zcta.columns.tolist()
)


# ============================================================
# 9. CHECK ZCTA ID
# ============================================================

if "ZCTA5CE20" not in zcta.columns:

    raise ValueError(
        """
The ZCTA shapefile does not contain ZCTA5CE20.

Available columns are:

"""
        + "\n".join(
            zcta.columns.tolist()
        )
    )


# ============================================================
# 10. LOAD STATE SHAPEFILE
# ============================================================

print("\n" + "=" * 75)
print("STEP 3: LOAD STATE SHAPEFILE")
print("=" * 75)

if not STATE_SHAPEFILE.exists():

    raise FileNotFoundError(
        f"""
Could not find the state shapefile:

{STATE_SHAPEFILE}

Make sure you downloaded and unzipped:

tl_2024_us_state.zip

into:

data/census/states/
"""
    )

states = gpd.read_file(
    STATE_SHAPEFILE
)

print(
    f"State polygons: "
    f"{len(states):,}"
)

print(
    "\nState shapefile columns:"
)

print(
    states.columns.tolist()
)


# ============================================================
# 11. CHECK STATE FIPS
# ============================================================

if "STATEFP" not in states.columns:

    raise ValueError(
        """
The STATE shapefile does not contain STATEFP.

Available columns are:

"""
        + "\n".join(
            states.columns.tolist()
        )
    )


# ============================================================
# 12. MATCH CRS
# ============================================================

print("\n" + "=" * 75)
print("STEP 4: MATCH GEOGRAPHIC CRS")
print("=" * 75)

print(
    f"ZCTA CRS: {zcta.crs}"
)

print(
    f"State CRS: {states.crs}"
)

states = states.to_crs(
    zcta.crs
)


# ============================================================
# 13. CREATE REPRESENTATIVE POINTS FOR ZCTAs
# ============================================================

print("\n" + "=" * 75)
print("STEP 5: ASSIGN ZCTAs TO STATES")
print("=" * 75)

print(
    "Creating representative points..."
)

"""
A centroid can occasionally fall outside an irregular polygon.

representative_point() guarantees that the point lies within
the polygon, which is preferable for this spatial join.
"""

zcta_points = zcta[
    [
        "ZCTA5CE20",
        "geometry",
    ]
].copy()

zcta_points["geometry"] = (
    zcta_points.geometry
    .representative_point()
)


# ============================================================
# 14. SPATIAL JOIN ZCTAs TO STATES
# ============================================================

print(
    "Spatially joining ZCTAs to states..."
)

zcta_state = gpd.sjoin(
    zcta_points,
    states[
        [
            "STATEFP",
            "geometry",
        ]
    ],
    how="left",
    predicate="within",
)

zcta_state = zcta_state[
    [
        "ZCTA5CE20",
        "STATEFP",
    ]
].copy()

zcta_state["ZCTA"] = (
    zcta_state["ZCTA5CE20"]
    .astype("string")
    .str.strip()
    .str.zfill(5)
)

zcta_state["STATEFP"] = (
    zcta_state["STATEFP"]
    .astype("string")
    .str.strip()
)

# Remove duplicate ZCTA assignments if any.
zcta_state = (
    zcta_state
    .drop_duplicates(
        subset=["ZCTA"]
    )
)


print(
    f"ZCTAs assigned to states: "
    f"{len(zcta_state):,}"
)

print(
    "Missing state assignments: "
    f"{zcta_state['STATEFP'].isna().sum():,}"
)


# ============================================================
# 15. MERGE STATE INTO REGRESSION DATA
# ============================================================

print(
    "\nMerging state information into "
    "regression dataset..."
)

df = df.merge(
    zcta_state[
        [
            "ZCTA",
            "STATEFP",
        ]
    ],
    on="ZCTA",
    how="left",
)


# ============================================================
# 16. CHECK MISSING STATES
# ============================================================

missing_state = (
    df["STATEFP"]
    .isna()
    .sum()
)

print(
    f"Regression observations without "
    f"state: {missing_state:,}"
)

if missing_state > 0:

    print(
        "\nFirst ZCTAs without state:"
    )

    print(
        df.loc[
            df["STATEFP"].isna(),
            "ZCTA",
        ]
        .head(20)
        .tolist()
    )

    df = df[
        df["STATEFP"].notna()
    ].copy()


# ============================================================
# 17. REMOVE PUERTO RICO
# ============================================================

"""
Puerto Rico is STATEFP = 72.

Your main state-level analysis excludes Puerto Rico, so we
keep the geographic scope consistent here.
"""

df = df[
    df["STATEFP"] != "72"
].copy()

print(
    f"\nFinal observations: "
    f"{len(df):,}"
)

print(
    f"States represented: "
    f"{df['STATEFP'].nunique()}"
)


# ============================================================
# 18. CREATE MODEL DATA
# ============================================================

print("\n" + "=" * 75)
print("STEP 6: PREPARE MODEL VARIABLES")
print("=" * 75)

baseline_variables = [
    "income_10k",
    "poverty_percent",
    "unemployment_percent",
    "median_age",
]

demographic_variables = [
    "black_percent",
    "asian_percent",
]


# ------------------------------------------------------------
# Convert model variables to numeric
# ------------------------------------------------------------

numeric_variables = (
    [
        "complaint_count",
        "population",
    ]
    + baseline_variables
    + demographic_variables
)

for column in numeric_variables:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )


# ------------------------------------------------------------
# Remove rows missing model variables
# ------------------------------------------------------------

model_variables = (
    [
        "complaint_count",
        "population",
    ]
    + baseline_variables
    + demographic_variables
)

before = len(df)

df = df.dropna(
    subset=model_variables
).copy()

after = len(df)

print(
    f"Rows removed because of "
    f"missing model variables: "
    f"{before - after:,}"
)

print(
    f"Rows available for models: "
    f"{after:,}"
)


# ============================================================
# 19. OUTCOME AND OFFSET
# ============================================================

y = (
    df["complaint_count"]
    .astype(float)
)

"""
The population offset turns the count model into a model
of complaint rate.

log(E[complaints]) =
    predictors + log(population)
"""

offset = np.log(
    df["population"]
    .astype(float)
)


# ============================================================
# 20. CREATE STATE FIXED EFFECTS
# ============================================================

print("\n" + "=" * 75)
print("STEP 7: CREATE STATE FIXED EFFECTS")
print("=" * 75)

state_dummies = pd.get_dummies(
    df["STATEFP"],
    prefix="state",
    drop_first=True,
    dtype=float,
)

print(
    f"State fixed-effect columns: "
    f"{state_dummies.shape[1]}"
)

print(
    f"States represented: "
    f"{df['STATEFP'].nunique()}"
)


# ============================================================
# 21. RUN MODELS
# ============================================================

print("\n" + "=" * 75)
print("STEP 8: RUN BLACK AND ASIAN MODELS")
print("=" * 75)

all_results = []

all_diagnostics = []

all_alpha_history = []


for demographic_variable in (
    demographic_variables
):

    if (
        demographic_variable
        == "black_percent"
    ):

        demographic_label = "Black"

    else:

        demographic_label = "Asian"


    print("\n")
    print("-" * 75)

    print(
        f"{demographic_label.upper()} ANALYSIS"
    )

    print("-" * 75)


    # ========================================================
    # MODEL 1: NO STATE FIXED EFFECTS
    # ========================================================

    model_name = (
        demographic_label.lower()
        + "_socioeconomic_only"
    )

    print(
        f"\nRunning {model_name}"
    )

    variables = (
        baseline_variables
        + [demographic_variable]
    )

    X = df[
        variables
    ].copy()

    X = sm.add_constant(
        X,
        has_constant="add",
    )

    result, alpha, history = (
        fit_negative_binomial(
            y=y,
            X=X,
            offset=offset,
            initial_alpha=1.0,
            max_iterations=(
                MAX_ALPHA_ITERATIONS
            ),
            tolerance=(
                ALPHA_TOLERANCE
            ),
        )
    )

    all_results.append(
        extract_coefficient(
            result=result,
            variable=demographic_variable,
            model_name=model_name,
            alpha=alpha,
        )
    )

    all_diagnostics.append(
        get_diagnostics(
            result=result,
            model_name=model_name,
            alpha=alpha,
        )
    )

    all_alpha_history.append(
        history.assign(
            model=model_name
        )
    )


    # ========================================================
    # MODEL 2: STATE FIXED EFFECTS
    # ========================================================

    model_name = (
        demographic_label.lower()
        + "_plus_state_fixed_effects"
    )

    print(
        f"\nRunning {model_name}"
    )

    X = pd.concat(
        [
            df[
                variables
            ].reset_index(
                drop=True
            ),

            state_dummies.reset_index(
                drop=True
            ),
        ],
        axis=1,
    )

    X = sm.add_constant(
        X,
        has_constant="add",
    )

    result, alpha, history = (
        fit_negative_binomial(
            y=y,
            X=X,
            offset=offset,
            initial_alpha=1.0,
            max_iterations=(
                MAX_ALPHA_ITERATIONS
            ),
            tolerance=(
                ALPHA_TOLERANCE
            ),
        )
    )

    all_results.append(
        extract_coefficient(
            result=result,
            variable=demographic_variable,
            model_name=model_name,
            alpha=alpha,
        )
    )

    all_diagnostics.append(
        get_diagnostics(
            result=result,
            model_name=model_name,
            alpha=alpha,
        )
    )

    all_alpha_history.append(
        history.assign(
            model=model_name
        )
    )


# ============================================================
# 22. CREATE RESULTS DATAFRAMES
# ============================================================

results_df = pd.DataFrame(
    all_results
)

diagnostics_df = pd.DataFrame(
    all_diagnostics
)

alpha_df = pd.concat(
    all_alpha_history,
    ignore_index=True,
)


# ============================================================
# 23. ADD INTERPRETABLE PERCENT CHANGE
# ============================================================

results_df[
    "percent_change_per_1pp"
] = (
    results_df["rate_ratio"] - 1
) * 100


# ============================================================
# 24. SAVE RESULTS
# ============================================================

print("\n" + "=" * 75)
print("STEP 9: SAVE MODEL RESULTS")
print("=" * 75)

results_path = (
    OUTPUT_DIR
    / "black_asian_geographic_robustness_results.csv"
)

diagnostics_path = (
    OUTPUT_DIR
    / "black_asian_geographic_robustness_diagnostics.csv"
)

alpha_path = (
    OUTPUT_DIR
    / "black_asian_geographic_robustness_alpha.csv"
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


# ============================================================
# 25. PRINT RESULTS
# ============================================================

print("\n" + "=" * 75)
print("KEY RESULTS")
print("=" * 75)

display_columns = [
    "model",
    "variable",
    "rate_ratio",
    "ci_lower",
    "ci_upper",
    "percent_change_per_1pp",
    "p_value",
]

print(
    results_df[
        display_columns
    ].to_string(
        index=False
    )
)


# ============================================================
# 26. CREATE PLOT DATA
# ============================================================

plot_df = results_df.copy()

plot_df["demographic"] = (
    plot_df["variable"]
    .map(
        {
            "black_percent":
                "Black population %",
            "asian_percent":
                "Asian population %",
        }
    )
)

plot_df["geographic_control"] = (
    plot_df["model"]
    .str.contains(
        "state_fixed_effects"
    )
)

plot_df["control_label"] = np.where(
    plot_df["geographic_control"],
    "State fixed effects",
    "No state fixed effects",
)


# ============================================================
# 27. PLOT
# ============================================================

print("\n" + "=" * 75)
print("STEP 10: CREATE ROBUSTNESS PLOT")
print("=" * 75)

fig, ax = plt.subplots(
    figsize=(10, 6)
)


# ------------------------------------------------------------
# Y positions
# ------------------------------------------------------------

race_positions = {
    "Black population %": 1,
    "Asian population %": 0,
}

model_offsets = {
    False: -0.13,
    True: 0.13,
}

plot_df["y"] = (
    plot_df.apply(
        lambda row:
            race_positions[
                row["demographic"]
            ]
            + model_offsets[
                row["geographic_control"]
            ],
        axis=1,
    )
)


# ------------------------------------------------------------
# Plot each estimate
# ------------------------------------------------------------

for _, row in plot_df.iterrows():

    lower_error = (
        row["rate_ratio"]
        - row["ci_lower"]
    )

    upper_error = (
        row["ci_upper"]
        - row["rate_ratio"]
    )

    ax.errorbar(
        row["rate_ratio"],
        row["y"],
        xerr=[
            [lower_error],
            [upper_error],
        ],
        fmt="o",
        markersize=7,
        capsize=5,
        linewidth=1.5,
    )


# ------------------------------------------------------------
# No-association reference line
# ------------------------------------------------------------

ax.axvline(
    1.0,
    linestyle="--",
    linewidth=1.2,
)


# ------------------------------------------------------------
# Labels
# ------------------------------------------------------------

ax.set_yticks(
    [
        0,
        1,
    ]
)

ax.set_yticklabels(
    [
        "Asian population %",
        "Black population %",
    ]
)

ax.set_xlabel(
    "Incidence Rate Ratio (IRR)"
)

ax.set_ylabel(
    ""
)

ax.set_title(
    "Robustness of Demographic Associations\n"
    "After Controlling for State"
)

ax.set_xlim(
    0.94,
    1.09,
)

ax.grid(
    axis="x",
    alpha=0.2,
)


# ------------------------------------------------------------
# Legend
# ------------------------------------------------------------

from matplotlib.lines import Line2D

legend_elements = [

    Line2D(
        [0],
        [0],
        marker="o",
        linestyle="None",
        markersize=7,
        label="No state fixed effects",
    ),

    Line2D(
        [0],
        [0],
        marker="o",
        linestyle="None",
        markersize=7,
        label="State fixed effects",
    ),

]

ax.legend(
    handles=legend_elements,
    loc="best",
)


plt.tight_layout()


# ============================================================
# 28. SAVE FIGURE
# ============================================================

figure_path = (
    FIGURE_DIR
    / "black_asian_state_robustness.png"
)

plt.savefig(
    figure_path,
    dpi=300,
    bbox_inches="tight",
)

plt.show()


# ============================================================
# 29. CREATE PRESENTATION-FRIENDLY SUMMARY
# ============================================================

summary_df = (
    results_df[
        [
            "model",
            "variable",
            "rate_ratio",
            "ci_lower",
            "ci_upper",
            "percent_change_per_1pp",
            "p_value",
            "alpha",
        ]
    ]
    .copy()
)

summary_df[
    "demographic"
] = summary_df[
    "variable"
].map(
    {
        "black_percent":
            "Black population %",
        "asian_percent":
            "Asian population %",
    }
)

summary_df[
    "geographic_control"
] = np.where(
    summary_df[
        "model"
    ].str.contains(
        "state_fixed_effects"
    ),
    "State fixed effects",
    "None",
)

summary_df = summary_df[
    [
        "demographic",
        "geographic_control",
        "rate_ratio",
        "ci_lower",
        "ci_upper",
        "percent_change_per_1pp",
        "p_value",
        "alpha",
    ]
]


summary_path = (
    OUTPUT_DIR
    / "black_asian_state_robustness_summary.csv"
)

summary_df.to_csv(
    summary_path,
    index=False,
)


# ============================================================
# 30. FINISHED
# ============================================================

print("\n" + "=" * 75)
print("ANALYSIS COMPLETE")
print("=" * 75)

print(
    "\nResults:"
)

print(
    results_path
)

print(
    "\nDiagnostics:"
)

print(
    diagnostics_path
)

print(
    "\nAlpha history:"
)

print(
    alpha_path
)

print(
    "\nFigure:"
)

print(
    figure_path
)

print(
    "\nSummary:"
)

print(
    summary_path
)

print("\nDone.")