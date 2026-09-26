import pandas as pd
import requests
from pathlib import Path
from io import BytesIO


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

# This file:
# cdc2026/scripts/stage1.1postQgis/get_state_population.py

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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
# Download 2024 ACS 5-year population data
# ---------------------------------------------------------

URL = (
    "https://www2.census.gov/programs-surveys/acs/"
    "summary_file/2024/table-based-SF/data/5YRData/"
    "acsdt5y2024-b01003.dat"
)

print("Downloading 2024 ACS state population data...")
print()

response = requests.get(
    URL,
    timeout=120,
)

response.raise_for_status()

df = pd.read_csv(
    BytesIO(response.content),
    sep="|",
    dtype=str,
)

print(f"Rows downloaded: {len(df):,}")
print()


# ---------------------------------------------------------
# Check columns / geography structure
# ---------------------------------------------------------

print("Columns found:")
print(df.columns.tolist())
print()

print("First 20 GEO_ID values:")
print(
    df["GEO_ID"]
    .head(20)
    .tolist()
)
print()


# ---------------------------------------------------------
# Keep state records
# ---------------------------------------------------------

# In the table-based ACS file, state GEO_IDs use:
#
#     0400000US01 = Alabama
#     0400000US37 = North Carolina
#
# The final two digits are the state FIPS code.

STATE_GEO_PREFIX = "0400000US"

state_mask = df["GEO_ID"].str.startswith(STATE_GEO_PREFIX, na=False)

states = df.loc[state_mask, ["GEO_ID", "B01003_E001"]].copy()

# The Census file also includes Puerto Rico (FIPS 72).
# This analysis uses the 50 states + Washington, D.C.
states = states[states["GEO_ID"] != "0400000US72"].copy()

if len(states) != 51:
    raise ValueError(
        "Expected 51 state/DC records after excluding Puerto Rico "
        f"but found {len(states)}."
    )

# ---------------------------------------------------------
# Extract state FIPS
# ---------------------------------------------------------

states["State FIPS"] = (
    states["GEO_ID"]
    .str.replace(
        STATE_GEO_PREFIX,
        "",
        regex=False,
    )
)


# ---------------------------------------------------------
# State FIPS → state abbreviation
# ---------------------------------------------------------

state_fips = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
}


states["State"] = states["State FIPS"].map(
    state_fips
)


# ---------------------------------------------------------
# Verify every FIPS code mapped
# ---------------------------------------------------------

if states["State"].isna().any():
    unmapped = states.loc[
        states["State"].isna(),
        "State FIPS",
    ].tolist()

    raise ValueError(
        f"Unmapped state FIPS codes: {unmapped}"
    )


# ---------------------------------------------------------
# Convert population
# ---------------------------------------------------------

states["population"] = pd.to_numeric(
    states["B01003_E001"],
    errors="coerce",
)


# ---------------------------------------------------------
# Keep useful columns
# ---------------------------------------------------------

states = states[
    [
        "State",
        "State FIPS",
        "population",
    ]
].copy()


# Remove anything that failed conversion
states = states.dropna(
    subset=[
        "State",
        "population",
    ]
)

states["population"] = states[
    "population"
].astype(int)


# ---------------------------------------------------------
# Final validation
# ---------------------------------------------------------

if len(states) != 51:
    raise ValueError(
        "Final state population dataset does not "
        f"contain 51 states/DC records. Found {len(states)}."
    )

if states["State"].duplicated().any():
    raise ValueError(
        "Duplicate state abbreviations found."
    )


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

output_file = (
    OUTPUT_DIR
    / "acs_2024_state_population.csv"
)

states.to_csv(
    output_file,
    index=False,
)


# ---------------------------------------------------------
# Verification
# ---------------------------------------------------------

print("=" * 60)
print("STATE POPULATION DOWNLOAD COMPLETE")
print("=" * 60)

print(
    f"States/DC found: {len(states)}"
)

print()

print(
    states
    .sort_values(
        "population",
        ascending=False,
    )
    .head(10)
    .to_string(index=False)
)

print()

print("North Carolina:")

print(
    states[
        states["State"] == "NC"
    ].to_string(index=False)
)

print()

print(f"Output: {output_file}")