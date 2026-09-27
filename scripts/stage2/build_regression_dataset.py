from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CENSUS_INPUT = (
    PROJECT_ROOT /
    "data/census/acs_2024_zcta_demographics.csv"
)

COMPLAINT_INPUT = (
    PROJECT_ROOT /
    "data/processed/zip_analysis/"
    "cfpb_2025_zip_summary.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT /
    "data/processed/regression"
)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "zcta_regression_data.csv"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD DATA
# ============================================================

print("Loading Census demographics...")

census = pd.read_csv(
    CENSUS_INPUT,
    dtype={"ZCTA": str}
)

print(
    f"Census ZCTAs: {len(census):,}"
)


print("\nLoading CFPB complaint data...")

complaints = pd.read_csv(
    COMPLAINT_INPUT,
    dtype={"ZIP code": str}
)

print(
    f"Complaint ZIPs: {len(complaints):,}"
)


# ============================================================
# STANDARDIZE ZCTA / ZIP
# ============================================================

census["ZCTA"] = (
    census["ZCTA"]
    .str.extract(r"(\d{5})")[0]
)

complaints["ZCTA"] = (
    complaints["ZIP code"]
    .astype(str)
    .str.extract(r"(\d{5})")[0]
)


# ============================================================
# KEEP COMPLAINT VARIABLES
# ============================================================

complaints = complaints[
    [
        "ZCTA",
        "complaints"
    ]
].copy()


# ============================================================
# CHECK FOR DUPLICATES
# ============================================================

if complaints["ZCTA"].duplicated().any():

    raise ValueError(
        "Complaint data contains duplicate ZCTAs."
    )


if census["ZCTA"].duplicated().any():

    raise ValueError(
        "Census data contains duplicate ZCTAs."
    )


# ============================================================
# MERGE
# ============================================================

print("\nMerging Census + CFPB data...")

regression = census.merge(
    complaints,
    on="ZCTA",
    how="left",
    validate="one_to_one"
)


# ============================================================
# ZERO COMPLAINT ZCTAs
# ============================================================

regression["complaints"] = (
    regression["complaints"]
    .fillna(0)
)


regression["complaints"] = (
    regression["complaints"]
    .astype(int)
)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("REGRESSION DATASET")
print("=" * 70)

print(
    f"Total ZCTAs: "
    f"{len(regression):,}"
)

print(
    f"ZCTAs with complaints: "
    f"{(regression['complaints'] > 0).sum():,}"
)

print(
    f"ZCTAs with zero complaints: "
    f"{(regression['complaints'] == 0).sum():,}"
)

print(
    f"Total complaints: "
    f"{regression['complaints'].sum():,}"
)

print(
    f"Total population: "
    f"{regression['population'].sum():,.0f}"
)

print("\nMissing values:")

print(
    regression.isna().sum()
)


# ============================================================
# SAVE
# ============================================================

regression.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nSaved to:")
print(OUTPUT_FILE)