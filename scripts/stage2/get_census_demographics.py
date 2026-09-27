from pathlib import Path
import io
import requests
import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "census"

OUTPUT_FILE = (
    OUTPUT_DIR /
    "acs_2024_zcta_demographics.csv"
)

BASE_URL = (
    "https://www2.census.gov/"
    "programs-surveys/acs/summary_file/2024/"
    "table-based-SF/data/5YRData/"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# ACS TABLES
# ============================================================

TABLES = [
    "B01003",  # Population
    "B19013",  # Median household income
    "B17001",  # Poverty
    "B23025",  # Employment
    "B02001",  # Race
    "B01002",  # Median age
    "B03003",  # Hispanic or Latino
]


# ============================================================
# DOWNLOAD + READ ONE TABLE
# ============================================================

def read_acs_table(table):

    url = (
        BASE_URL +
        f"acsdt5y2024-{table.lower()}.dat"
    )

    print("\n" + "-" * 70)
    print(f"Downloading {table}")
    print(url)

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    print(
        f"Downloaded "
        f"{len(response.content) / 1_000_000:.1f} MB"
    )

    df = pd.read_csv(
        io.BytesIO(response.content),
        sep="|",
        dtype="string",
        low_memory=False,
    )

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    return df


# ============================================================
# DOWNLOAD ALL TABLES
# ============================================================

tables = {}

for table in TABLES:
    tables[table] = read_acs_table(table)


# ============================================================
# KEEP ZCTAs
# ============================================================

ZCTA_PREFIX = "860Z200US"

zcta_tables = {}

for table, df in tables.items():

    print(
        f"\nFiltering {table} to ZCTAs..."
    )

    zcta_mask = df["GEO_ID"].str.startswith(
        ZCTA_PREFIX,
        na=False
    )

    zcta = df.loc[zcta_mask].copy()

    print(
        f"ZCTAs: {len(zcta):,}"
    )

    zcta_tables[table] = zcta


# ============================================================
# HELPER
# ============================================================

def select_columns(table, columns):
    """Select columns and verify they exist."""
    
    missing = [
        col for col in columns
        if col not in zcta_tables[table].columns
    ]

    if missing:
        raise ValueError(
            f"{table} is missing columns: {missing}"
        )

    return zcta_tables[table][columns].copy()


# ============================================================
# POPULATION
# ============================================================

population = select_columns(
    "B01003",
    [
        "GEO_ID",
        "B01003_E001"
    ]
)

population = population.rename(
    columns={
        "B01003_E001": "population"
    }
)


# ============================================================
# MEDIAN HOUSEHOLD INCOME
# ============================================================

income = select_columns(
    "B19013",
    [
        "GEO_ID",
        "B19013_E001"
    ]
)

income = income.rename(
    columns={
        "B19013_E001":
        "median_household_income"
    }
)


# ============================================================
# POVERTY
# ============================================================

poverty = select_columns(
    "B17001",
    [
        "GEO_ID",
        "B17001_E001",
        "B17001_E002"
    ]
)

poverty = poverty.rename(
    columns={
        "B17001_E001":
        "poverty_universe",

        "B17001_E002":
        "below_poverty"
    }
)


# ============================================================
# EMPLOYMENT
# ============================================================

employment = select_columns(
    "B23025",
    [
        "GEO_ID",
        "B23025_E003",
        "B23025_E005"
    ]
)

employment = employment.rename(
    columns={
        "B23025_E003":
        "labor_force",

        "B23025_E005":
        "unemployed"
    }
)


# ============================================================
# RACE
# ============================================================

race = select_columns(
    "B02001",
    [
        "GEO_ID",
        "B02001_E002",  # White alone
        "B02001_E003",  # Black or African American alone
        "B02001_E004",  # American Indian / Alaska Native alone
        "B02001_E005",  # Asian alone
        "B02001_E006",  # Native Hawaiian / Pacific Islander alone
        "B02001_E007",  # Some other race alone
        "B02001_E008",  # Two or more races
    ]
)

race = race.rename(
    columns={
        "B02001_E002":
            "white_population",

        "B02001_E003":
            "black_population",

        "B02001_E004":
            "american_indian_alaska_native_population",

        "B02001_E005":
            "asian_population",

        "B02001_E006":
            "native_hawaiian_pacific_islander_population",

        "B02001_E007":
            "other_race_population",

        "B02001_E008":
            "two_or_more_races_population",
    }
)


# ============================================================
# MEDIAN AGE
# ============================================================

age = select_columns(
    "B01002",
    [
        "GEO_ID",
        "B01002_E001"
    ]
)

age = age.rename(
    columns={
        "B01002_E001":
        "median_age"
    }
)


# ============================================================
# HISPANIC / LATINO
# ============================================================

hispanic = select_columns(
    "B03003",
    [
        "GEO_ID",
        "B03003_E001",
        "B03003_E003"
    ]
)

hispanic = hispanic.rename(
    columns={
        "B03003_E001":
            "hispanic_universe",

        "B03003_E003":
            "hispanic_population",
    }
)


# ============================================================
# MERGE TABLES
# ============================================================

print("\n" + "=" * 70)
print("MERGING ACS TABLES")
print("=" * 70)

demographics = population.copy()

for table_df in [
    income,
    poverty,
    employment,
    race,
    age,
    hispanic,
]:

    demographics = demographics.merge(
        table_df,
        on="GEO_ID",
        how="left",
        validate="one_to_one"
    )


# ============================================================
# CREATE ZCTA
# ============================================================

demographics["ZCTA"] = (
    demographics["GEO_ID"]
    .str.replace(
        ZCTA_PREFIX,
        "",
        regex=False
    )
)


# ============================================================
# CONVERT NUMERIC VARIABLES
# ============================================================

numeric_columns = [
    "population",
    "median_household_income",
    "poverty_universe",
    "below_poverty",
    "labor_force",
    "unemployed",

    "white_population",
    "black_population",
    "american_indian_alaska_native_population",
    "asian_population",
    "native_hawaiian_pacific_islander_population",
    "other_race_population",
    "two_or_more_races_population",

    "median_age",

    "hispanic_universe",
    "hispanic_population",
]

for column in numeric_columns:

    demographics[column] = pd.to_numeric(
        demographics[column],
        errors="coerce"
    )


# ============================================================
# ECONOMIC PERCENTAGES
# ============================================================

demographics["poverty_percent"] = (
    demographics["below_poverty"]
    / demographics["poverty_universe"]
    * 100
)

demographics["unemployment_percent"] = (
    demographics["unemployed"]
    / demographics["labor_force"]
    * 100
)


# ============================================================
# RACE PERCENTAGES
# ============================================================

race_columns = {
    "white_population":
        "white_percent",

    "black_population":
        "black_percent",

    "american_indian_alaska_native_population":
        "american_indian_alaska_native_percent",

    "asian_population":
        "asian_percent",

    "native_hawaiian_pacific_islander_population":
        "native_hawaiian_pacific_islander_percent",

    "other_race_population":
        "other_race_percent",

    "two_or_more_races_population":
        "two_or_more_races_percent",
}

for count_column, percent_column in race_columns.items():

    demographics[percent_column] = (
        demographics[count_column]
        / demographics["population"]
        * 100
    )


# ============================================================
# HISPANIC PERCENT
# ============================================================

demographics["hispanic_percent"] = (
    demographics["hispanic_population"]
    / demographics["hispanic_universe"]
    * 100
)


# ============================================================
# SELECT FINAL COLUMNS
# ============================================================

demographics = demographics[
    [
        "ZCTA",

        "population",

        "median_household_income",

        "white_percent",
        "black_percent",
        "american_indian_alaska_native_percent",
        "asian_percent",
        "native_hawaiian_pacific_islander_percent",
        "other_race_percent",
        "two_or_more_races_percent",
        "hispanic_percent",

        "poverty_percent",
        "unemployment_percent",
        "median_age",
    ]
].copy()


# ============================================================
# CLEAN
# ============================================================

demographics = demographics[
    demographics["ZCTA"].str.fullmatch(
        r"\d{5}",
        na=False
    )
].copy()

demographics = demographics[
    demographics["population"].notna()
    & (demographics["population"] > 0)
].copy()

demographics = demographics.drop_duplicates(
    subset="ZCTA"
)

demographics = demographics.sort_values(
    "ZCTA"
)


# ============================================================
# SAVE
# ============================================================

demographics.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("CENSUS DEMOGRAPHICS COMPLETE")
print("=" * 70)

print(
    f"\nZCTAs: {len(demographics):,}"
)

print("\nColumns:")
print(
    demographics.columns.tolist()
)

print("\nMissing values:")
print(
    demographics.isna().sum()
)

print("\nFirst 10 rows:")
print(
    demographics.head(10).to_string(
        index=False
    )
)

print("\nSaved to:")
print(OUTPUT_FILE)