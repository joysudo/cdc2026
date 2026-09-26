import pandas as pd
from pathlib import Path

# Project root: cdc2026/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    PROJECT_ROOT
    / "scripts"
    / "data"
    / "processed"
    / "state_analysis"
)

COMPLAINTS_FILE = INPUT_DIR / "state_complaints.csv"
POPULATION_FILE = INPUT_DIR / "acs_2024_state_population.csv"
OUTPUT_FILE = INPUT_DIR / "state_complaint_rates.csv"


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

complaints = pd.read_csv(COMPLAINTS_FILE)
population = pd.read_csv(POPULATION_FILE)


# ---------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------

if complaints["State"].duplicated().any():
    raise ValueError("Duplicate states found in complaint data.")

if population["State"].duplicated().any():
    raise ValueError("Duplicate states found in population data.")

if len(complaints) != 51:
    raise ValueError(
        f"Expected 51 states/DC in complaint data, found {len(complaints)}."
    )

if len(population) != 51:
    raise ValueError(
        f"Expected 51 states/DC in population data, found {len(population)}."
    )


# ---------------------------------------------------------
# Merge complaint counts with population
# ---------------------------------------------------------

merged = complaints.merge(
    population[["State", "population"]],
    on="State",
    how="left",
    validate="one_to_one",
)


# ---------------------------------------------------------
# Check for missing population values
# ---------------------------------------------------------

if merged["population"].isna().any():
    missing_states = merged.loc[
        merged["population"].isna(), "State"
    ].tolist()

    raise ValueError(
        f"Missing population for states/DC: {missing_states}"
    )


if (merged["population"] <= 0).any():
    bad_states = merged.loc[
        merged["population"] <= 0, "State"
    ].tolist()

    raise ValueError(
        f"Non-positive population found for: {bad_states}"
    )


# ---------------------------------------------------------
# Calculate complaint rate
#
# 2025 CFPB complaints
# -------------------- × 100,000
# 2024 ACS population
# ---------------------------------------------------------

merged["complaints_per_100000"] = (
    merged["complaints"]
    / merged["population"]
    * 100_000
)


# ---------------------------------------------------------
# Sort by complaint rate
# ---------------------------------------------------------

merged = merged.sort_values(
    "complaints_per_100000",
    ascending=False
).reset_index(drop=True)


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

merged.to_csv(OUTPUT_FILE, index=False)


# ---------------------------------------------------------
# Print validation / summary
# ---------------------------------------------------------

print("=" * 60)
print("STATE COMPLAINT RATE ANALYSIS COMPLETE")
print("=" * 60)

print(f"States/DC: {len(merged)}")
print(f"Total complaints: {merged['complaints'].sum():,}")
print(f"Total population: {merged['population'].sum():,}")

print()
print("Top 10 states/DC by complaints per 100,000:")
print(
    merged[
        ["State", "complaints", "population", "complaints_per_100000"]
    ]
    .head(10)
    .to_string(index=False)
)

print()
print("North Carolina:")
print(
    merged[merged["State"] == "NC"][
        ["State", "complaints", "population", "complaints_per_100000"]
    ].to_string(index=False)
)

print()
print(f"Output: {OUTPUT_FILE}")