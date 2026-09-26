import os
import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

COMPLAINT_FILE = (
    "data/processed/zip_analysis/"
    "cfpb_2025_zip_summary.csv"
)

POPULATION_FILE = (
    "data/census/"
    "acs_2024_zcta_population.csv"
)

OUTPUT_FILE = (
    "data/processed/zip_analysis/"
    "cfpb_2025_zip_rates.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("LOADING DATA")
print("=" * 70)

complaints = pd.read_csv(
    COMPLAINT_FILE,
    dtype={"ZIP code": "string"}
)

population = pd.read_csv(
    POPULATION_FILE,
    dtype={"ZIP code": "string"}
)

print(f"Complaint ZIPs: {len(complaints):,}")
print(f"Census ZCTAs:   {len(population):,}")


# ============================================================
# CLEAN ZIP CODES
# ============================================================

complaints["ZIP code"] = (
    complaints["ZIP code"]
    .str.strip()
    .str.zfill(5)
)

population["ZIP code"] = (
    population["ZIP code"]
    .str.strip()
    .str.zfill(5)
)


# ============================================================
# CHECK FOR DUPLICATES
# ============================================================

print("\nChecking for duplicate ZIP/ZCTA records...")

complaint_duplicates = complaints[
    complaints["ZIP code"].duplicated()
]

population_duplicates = population[
    population["ZIP code"].duplicated()
]

print(
    f"Duplicate complaint ZIP rows: "
    f"{len(complaint_duplicates):,}"
)

print(
    f"Duplicate Census ZCTA rows: "
    f"{len(population_duplicates):,}"
)


# ============================================================
# MERGE
# ============================================================

print("\nMerging CFPB complaints with Census population...")

merged = complaints.merge(
    population,
    on="ZIP code",
    how="left",
    validate="one_to_one",
    indicator=True,
)


# ============================================================
# MATCH QUALITY
# ============================================================

matched = merged["_merge"] == "both"
unmatched = merged["_merge"] == "left_only"

print("\n" + "=" * 70)
print("MERGE QUALITY")
print("=" * 70)

print(
    f"CFPB ZIPs:                  {len(complaints):,}"
)

print(
    f"Matched to Census ZCTA:     {matched.sum():,}"
)

print(
    f"Did not match Census ZCTA:  {unmatched.sum():,}"
)

match_rate = matched.mean() * 100

print(
    f"ZIP match rate:             {match_rate:.2f}%"
)


# ============================================================
# SHOW UNMATCHED ZIP CODES
# ============================================================

if unmatched.any():

    print("\nUnmatched ZIP codes:")

    print(
        merged.loc[
            unmatched,
            ["ZIP code", "complaints"]
        ]
        .sort_values(
            "complaints",
            ascending=False
        )
        .head(25)
        .to_string(index=False)
    )


# ============================================================
# REMOVE MERGE INDICATOR
# ============================================================

merged = merged.drop(
    columns=["_merge"]
)


# ============================================================
# REMOVE ZERO / MISSING POPULATION
# ============================================================

missing_population = merged["population"].isna().sum()

zero_population = (
    merged["population"] == 0
).sum()

print("\nPopulation quality:")

print(
    f"Missing population: "
    f"{missing_population:,}"
)

print(
    f"Zero population:    "
    f"{zero_population:,}"
)


# ============================================================
# CALCULATE COMPLAINT RATE
# ============================================================

merged["complaints_per_1000"] = (
    merged["complaints"]
    / merged["population"]
    * 1000
)

# Don't calculate a meaningful rate for zero-population ZCTAs.
merged.loc[
    merged["population"] <= 0,
    "complaints_per_1000"
] = pd.NA


# ============================================================
# SORT
# ============================================================

merged = merged.sort_values(
    "complaints_per_1000",
    ascending=False
)


# ============================================================
# SAVE
# ============================================================

merged.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("MERGE COMPLETE")
print("=" * 70)

print(f"Saved to:")
print(OUTPUT_FILE)

print("\nTop 20 ZIPs by complaints per 1,000 residents:")

print(
    merged[
        [
            "ZIP code",
            "complaints",
            "population",
            "complaints_per_1000",
        ]
    ]
    .head(20)
    .to_string(index=False)
)