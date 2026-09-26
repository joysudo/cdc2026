import os
import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

INPUT_FILE = "data/raw/complaints.csv"
OUTPUT_FILE = "data/processed/cfpb_2025_cleaned.csv"

CHUNK_SIZE = 100_000


# ============================================================
# COLUMNS TO KEEP
# ============================================================

USECOLS = [
    "Date received",
    "Product",
    "Sub-product",
    "Issue",
    "Sub-issue",
    "Company public response",
    "Company",
    "State",
    "ZIP code",
    "Tags",
    "Submitted via",
    "Date sent to company",
    "Company response to consumer",
    "Timely response?",
    "Complaint ID",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(series):
    """
    Standardize text columns:
    - Convert missing values to pandas NA
    - Strip leading/trailing whitespace
    - Convert empty strings to NA
    """
    series = series.astype("string").str.strip()
    series = series.replace("", pd.NA)
    return series


def clean_zip(series):
    """
    Clean CFPB ZIP codes.

    Keeps only exactly five-digit ZIP codes.
    ZIP+4 values and other invalid values become NA.
    """
    zip_clean = (
        series
        .astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )

    valid = zip_clean.str.fullmatch(r"\d{5}")

    zip_clean = zip_clean.where(valid, pd.NA)

    return zip_clean


# ============================================================
# PROCESS RAW FILE IN CHUNKS
# ============================================================

os.makedirs("data/processed", exist_ok=True)

first_chunk = True

total_rows = 0
total_2025 = 0
total_valid_zip = 0

output_columns = USECOLS.copy()


for chunk_number, chunk in enumerate(
    pd.read_csv(
        INPUT_FILE,
        usecols=USECOLS,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ),
    start=1,
):

    # --------------------------------------------------------
    # Track raw rows
    # --------------------------------------------------------

    total_rows += len(chunk)


    # --------------------------------------------------------
    # Clean dates
    # --------------------------------------------------------

    chunk["Date received"] = pd.to_datetime(
        chunk["Date received"],
        errors="coerce"
    )

    chunk["Date sent to company"] = pd.to_datetime(
        chunk["Date sent to company"],
        errors="coerce"
    )


    # --------------------------------------------------------
    # Keep only complaints received during 2025
    # --------------------------------------------------------

    chunk = chunk[
        (chunk["Date received"] >= "2025-01-01")
        & (chunk["Date received"] < "2026-01-01")
    ].copy()

    total_2025 += len(chunk)


    # Skip empty chunks
    if chunk.empty:
        continue


    # --------------------------------------------------------
    # Clean ZIP codes
    # --------------------------------------------------------

    chunk["ZIP code"] = clean_zip(chunk["ZIP code"])

    total_valid_zip += chunk["ZIP code"].notna().sum()


    # --------------------------------------------------------
    # Clean text columns
    # --------------------------------------------------------

    text_columns = [
        "Product",
        "Sub-product",
        "Issue",
        "Sub-issue",
        "Company public response",
        "Company",
        "State",
        "Tags",
        "Submitted via",
        "Company response to consumer",
        "Timely response?",
    ]

    for column in text_columns:
        chunk[column] = clean_text(chunk[column])


    # --------------------------------------------------------
    # Clean Complaint ID
    # --------------------------------------------------------

    chunk["Complaint ID"] = pd.to_numeric(
        chunk["Complaint ID"],
        errors="coerce",
    ).astype("Int64")


    # --------------------------------------------------------
    # Write chunk to output
    # --------------------------------------------------------

    chunk.to_csv(
        OUTPUT_FILE,
        mode="w" if first_chunk else "a",
        header=first_chunk,
        index=False,
    )

    first_chunk = False


    # --------------------------------------------------------
    # Progress
    # --------------------------------------------------------

    print(
        f"Processed chunk {chunk_number:,} | "
        f"Raw rows: {total_rows:,} | "
        f"2025 rows: {total_2025:,}"
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("PROCESSING COMPLETE")
print("=" * 60)

print(f"Total raw rows processed:       {total_rows:,}")
print(f"2025 complaints:                {total_2025:,}")
print(f"2025 complaints with valid ZIP: {total_valid_zip:,}")

if total_2025 > 0:
    coverage = total_valid_zip / total_2025 * 100
    print(f"Valid ZIP coverage:             {coverage:.2f}%")

print(f"\nSaved to:")
print(OUTPUT_FILE)