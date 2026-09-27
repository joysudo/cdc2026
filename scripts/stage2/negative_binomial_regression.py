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
    "data/processed/regression/zcta_regression_data.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(INPUT)


# ============================================================
# KEEP COMPLETE OBSERVATIONS
# ============================================================

model_df = df.dropna(subset=[
    "complaints",
    "population",
    "median_household_income",
    "poverty_percent",
    "unemployment_percent",
    "black_percent",
    "median_age"
]).copy()


# ============================================================
# PREPARE MODEL VARIABLES
# ============================================================

# Income in $10,000 units
model_df["income_10k"] = (
    model_df["median_household_income"] / 10_000
)

# Population offset
model_df["log_population"] = np.log(
    model_df["population"]
)


# ============================================================
# MODEL FORMULA
# ============================================================

formula = """
complaints ~
income_10k +
poverty_percent +
unemployment_percent +
black_percent +
median_age
"""


# ============================================================
# NEGATIVE BINOMIAL MODEL
# ============================================================

negative_binomial = smf.glm(
    formula=formula,
    data=model_df,
    family=sm.families.NegativeBinomial(),
    offset=model_df["log_population"]
).fit()


# ============================================================
# RESULTS
# ============================================================

print("=" * 80)
print("NEGATIVE BINOMIAL REGRESSION")
print("=" * 80)

print(negative_binomial.summary())


# ============================================================
# RATE RATIOS
# ============================================================

print("\n" + "=" * 80)
print("RATE RATIOS")
print("=" * 80)

rate_ratios = np.exp(
    negative_binomial.params
)

print(
    pd.DataFrame({
        "coefficient": negative_binomial.params,
        "rate_ratio": rate_ratios,
        "p_value": negative_binomial.pvalues
    })
)


# ============================================================
# MODEL DIAGNOSTICS
# ============================================================

print("\n" + "=" * 80)
print("MODEL DIAGNOSTICS")
print("=" * 80)

print(
    f"Observations: "
    f"{int(negative_binomial.nobs):,}"
)

print(
    f"Deviance: "
    f"{negative_binomial.deviance:,.2f}"
)

print(
    f"Pearson chi-square: "
    f"{negative_binomial.pearson_chi2:,.2f}"
)

print(
    f"Pearson chi-square / df: "
    f"{negative_binomial.pearson_chi2 / negative_binomial.df_resid:.2f}"
)

print(
    f"AIC: "
    f"{negative_binomial.aic:,.2f}"
)