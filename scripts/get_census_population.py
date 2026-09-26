import os
import io
import zipfile
import requests
import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

OUTPUT_DIR = "data/census"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "acs_2024_zcta_population.csv"
)

DATA_URL = (
    "https://www2.census.gov/"
    "programs-surveys/acs/summary_file/2024/"
    "table-based-SF/data/5YRData/"
    "acsdt5y2024-b01003.dat"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# DOWNLOAD B01003
# ============================================================

print("=" * 70)
print("DOWNLOADING 2024 ACS 5-YEAR B01003")
print("=" * 70)

print("\nSource:")
print(DATA_URL)

response = requests.get(
    DATA_URL,
    timeout=120
)

response.raise_for_status()

print(
    f"\nDownloaded {len(response.content) / 1_000_000:.1f} MB"
)


# ============================================================
# READ THE TABLE-BASED SUMMARY FILE
# ============================================================

print("\nReading Census data...")

df = pd.read_csv(
    io.BytesIO(response.content),
    sep="|",
    dtype="string",
    low_memory=False,
)

print(f"Rows downloaded: {len(df):,}")

print("\nColumns:")
print(df.columns.tolist())


# ============================================================
# KEEP ZCTAs
# ============================================================

# 2024 ACS table-based Summary File uses
# 860Z200US for ZIP Code Tabulation Areas.
zcta_mask = df["GEO_ID"].str.startswith(
    "860Z200US",
    na=False
)

zcta = df.loc[
    zcta_mask,
    ["GEO_ID", "B01003_E001"]
].copy()


# ============================================================
# CLEAN ZCTA CODE
# ============================================================

zcta["ZIP code"] = (
    zcta["GEO_ID"]
    .str.replace(
        "860Z200US",
        "",
        regex=False
    )
)

zcta["population"] = pd.to_numeric(
    zcta["B01003_E001"],
    errors="coerce"
)

zcta = zcta[
    ["ZIP code", "population"]
].copy()

# ============================================================
# VALIDATE
# ============================================================

zcta = zcta[
    zcta["ZIP code"].str.fullmatch(
        r"\d{5}",
        na=False
    )
].copy()

zcta = zcta[
    zcta["population"].notna()
].copy()

zcta["population"] = zcta["population"].astype("Int64")

zcta = zcta.drop_duplicates(
    subset="ZIP code"
)

zcta = zcta.sort_values(
    "ZIP code"
)


# ============================================================
# SAVE
# ============================================================

zcta.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("CENSUS POPULATION DATA COMPLETE")
print("=" * 70)

print(
    f"ZCTAs extracted: {len(zcta):,}"
)

print(
    f"ZCTAs with population: "
    f"{zcta['population'].notna().sum():,}"
)

print("\nFirst 10 rows:")
print(
    zcta.head(10).to_string(
        index=False
    )
)

print("\nPopulation summary:")
print(
    zcta["population"].describe()
)

print("\nSaved to:")
print(OUTPUT_FILE)