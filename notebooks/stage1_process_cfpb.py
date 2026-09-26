import pandas as pd
from collections import Counter

INPUT_FILE = "data/raw/complaints.csv"
OUTPUT_FILE = "data/processed/cfpb_2025_zip_counts.csv"

USE_COLS = [
    "Date received",
    "Product",
    "Sub-product",
    "Issue",
    "Sub-issue",
    "Company",
    "State",
    "ZIP code",
    "Tags",
    "Company response to consumer",
    "Timely response?",
    "Complaint ID"
]

# Keep running counts rather than storing millions of rows
zip_counts = Counter()

total_rows = 0
total_2025 = 0
valid_zip_2025 = 0

for chunk in pd.read_csv(
    INPUT_FILE,
    usecols=USE_COLS,
    chunksize=100_000,
    low_memory=False
):
    total_rows += len(chunk)

    # Convert date
    chunk["Date received"] = pd.to_datetime(
        chunk["Date received"],
        errors="coerce"
    )

    # Keep only 2025
    chunk_2025 = chunk[
        (chunk["Date received"] >= "2025-01-01") &
        (chunk["Date received"] < "2026-01-01")
    ]

    total_2025 += len(chunk_2025)

    # Clean ZIP codes
    zips = (
        chunk_2025["ZIP code"]
        .astype("string")
        .str.strip()
    )

    valid = zips.str.fullmatch(r"\d{5}", na=False)

    valid_zips = zips[valid]

    valid_zip_2025 += len(valid_zips)

    # Count complaints by ZIP
    zip_counts.update(valid_zips)

    print(
        f"Processed {total_rows:,} rows | "
        f"2025 complaints: {total_2025:,} | "
        f"valid ZIP complaints: {valid_zip_2025:,}"
    )

# Convert counts to DataFrame
complaints_by_zip = pd.DataFrame(
    zip_counts.items(),
    columns=["ZIP code", "complaints"]
)

# Sort highest → lowest
complaints_by_zip = complaints_by_zip.sort_values(
    "complaints",
    ascending=False
)

# Save
complaints_by_zip.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nDONE!")
print(f"Total rows processed: {total_rows:,}")
print(f"2025 complaints: {total_2025:,}")
print(f"2025 complaints with valid 5-digit ZIP: {valid_zip_2025:,}")

print(
    f"Percent with valid ZIP: "
    f"{valid_zip_2025 / total_2025 * 100:.2f}%"
)

print(f"\nSaved to: {OUTPUT_FILE}")

print("\nTop 20 ZIP codes by complaint count:")
print(complaints_by_zip.head(20).to_string(index=False))