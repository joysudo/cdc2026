import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

# This file:
# cdc2026/scripts/stage1.1postQgis/state_analysis.py
#
# parents[0] = stage1.1postQgis
# parents[1] = scripts
# parents[2] = project root (cdc2026)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------
# Input
# ---------------------------------------------------------

CLEANED_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cfpb_2025_cleaned.csv"
)


# ---------------------------------------------------------
# Output
# ---------------------------------------------------------

OUTPUT_DIR = (
    PROJECT_ROOT
    / "scripts"
    / "data"
    / "processed"
    / "state_analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

CHUNK_SIZE = 250_000


# ---------------------------------------------------------
# Valid states
# ---------------------------------------------------------

VALID_STATES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "DC",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
}


# ---------------------------------------------------------
# Process CFPB data
# ---------------------------------------------------------

state_counts = {}

total_rows = 0
valid_state_rows = 0


print("Reading CFPB complaints...")
print(f"Input: {CLEANED_FILE}")
print()


for chunk in pd.read_csv(
    CLEANED_FILE,
    chunksize=CHUNK_SIZE,
    low_memory=False,
    usecols=["State"],
):

    total_rows += len(chunk)

    # Standardize state abbreviations
    chunk["State"] = (
        chunk["State"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # Keep only states/DC that have a Census population record
    chunk = chunk.loc[
        chunk["State"].isin(VALID_STATES)
    ]

    valid_state_rows += len(chunk)

    # Count complaints by state
    counts = chunk["State"].value_counts()

    for state, count in counts.items():

        state_counts[state] = (
            state_counts.get(state, 0)
            + int(count)
        )

    print(
        f"Processed {total_rows:,} rows",
        end="\r",
    )


# ---------------------------------------------------------
# Convert to DataFrame
# ---------------------------------------------------------

state_df = pd.DataFrame(
    {
        "State": list(state_counts.keys()),
        "complaints": list(
            state_counts.values()
        ),
    }
)


# ---------------------------------------------------------
# Sort by complaint count
# ---------------------------------------------------------

state_df = state_df.sort_values(
    "complaints",
    ascending=False,
)


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

output_file = (
    OUTPUT_DIR
    / "state_complaints.csv"
)

state_df.to_csv(
    output_file,
    index=False,
)


# ---------------------------------------------------------
# Verification
# ---------------------------------------------------------

print()
print()
print("=" * 60)
print("STATE ANALYSIS COMPLETE")
print("=" * 60)

print(
    f"Total rows processed: {total_rows:,}"
)

print(
    f"Valid state records: {valid_state_rows:,}"
)

print(
    f"Excluded records: "
    f"{total_rows - valid_state_rows:,}"
)

print(
    f"States found: {len(state_df)}"
)

print()

print("Top 20 states by complaint count:")
print()

print(
    state_df
    .head(20)
    .to_string(index=False)
)

print()

print(f"Output: {output_file}")