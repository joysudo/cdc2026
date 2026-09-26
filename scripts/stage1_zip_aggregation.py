import pandas as pd
from pathlib import Path
from collections import defaultdict

INPUT = Path("data/processed/cfpb_2025_cleaned.csv")
OUTPUT_DIR = Path("data/processed/zip_analysis")

CHUNK_SIZE = 100_000

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# Storage for ZIP-level counts
# ------------------------------------------------------------

zip_complaints = defaultdict(int)
zip_timely_yes = defaultdict(int)
zip_timely_total = defaultdict(int)

zip_monetary_relief = defaultdict(int)
zip_nonmonetary_relief = defaultdict(int)
zip_closed = defaultdict(int)

zip_older_american = defaultdict(int)
zip_servicemember = defaultdict(int)

# ZIP x Product
zip_product = defaultdict(int)

# ZIP x Issue
zip_issue = defaultdict(int)

# Unique companies/products per ZIP
zip_companies = defaultdict(set)
zip_products = defaultdict(set)


# ------------------------------------------------------------
# Read cleaned CFPB data in chunks
# ------------------------------------------------------------

columns = [
    "Product",
    "Issue",
    "Company",
    "ZIP code",
    "Tags",
    "Company response to consumer",
    "Timely response?",
]

print("=" * 70)
print("PROCESSING CLEANED CFPB DATA")
print("=" * 70)

total_rows = 0
valid_zip_rows = 0

for chunk_number, chunk in enumerate(
    pd.read_csv(
        INPUT,
        usecols=columns,
        chunksize=CHUNK_SIZE,
        dtype={
            "Product": "string",
            "Issue": "string",
            "Company": "string",
            "ZIP code": "string",
            "Tags": "string",
            "Company response to consumer": "string",
            "Timely response?": "string",
        },
    ),
    start=1,
):

    total_rows += len(chunk)

    # --------------------------------------------------------
    # Clean ZIP
    # --------------------------------------------------------

    chunk["ZIP code"] = (
        chunk["ZIP code"]
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )

    valid = chunk["ZIP code"].str.fullmatch(r"[0-9]{5}", na=False)

    chunk = chunk.loc[valid].copy()

    valid_zip_rows += len(chunk)

    if chunk_number % 10 == 0:
        print(
            f"Chunks: {chunk_number:,} | "
            f"Rows read: {total_rows:,} | "
            f"Valid ZIP rows: {valid_zip_rows:,}"
        )

    # --------------------------------------------------------
    # Basic complaint counts
    # --------------------------------------------------------

    for zip_code, group in chunk.groupby("ZIP code", sort=False):

        zip_complaints[zip_code] += len(group)

        # Unique companies/products
        companies = group["Company"].dropna().unique()
        products = group["Product"].dropna().unique()

        zip_companies[zip_code].update(companies)
        zip_products[zip_code].update(products)

        # Timely response
        timely = group["Timely response?"].str.strip().str.lower()

        zip_timely_yes[zip_code] += (timely == "yes").sum()
        zip_timely_total[zip_code] += timely.notna().sum()

        # Company response
        responses = (
            group["Company response to consumer"]
            .fillna("")
            .str.strip()
            .str.lower()
        )

        zip_monetary_relief[zip_code] += (
            responses == "closed with monetary relief"
        ).sum()

        zip_nonmonetary_relief[zip_code] += (
            responses == "closed with non-monetary relief"
        ).sum()

        zip_closed[zip_code] += responses.str.startswith("closed").sum()

        # Tags
        tags = group["Tags"].fillna("").str.lower()

        zip_older_american[zip_code] += (
            tags.str.contains("older american", regex=False)
        ).sum()

        zip_servicemember[zip_code] += (
            tags.str.contains("servicemember", regex=False)
        ).sum()

        # ----------------------------------------------------
        # Product counts
        # ----------------------------------------------------

        product_counts = group["Product"].dropna().value_counts()

        for product, count in product_counts.items():
            zip_product[(zip_code, product)] += int(count)

        # ----------------------------------------------------
        # Issue counts
        # ----------------------------------------------------

        issue_counts = group["Issue"].dropna().value_counts()

        for issue, count in issue_counts.items():
            zip_issue[(zip_code, issue)] += int(count)


# ------------------------------------------------------------
# Create ZIP summary
# ------------------------------------------------------------

print()
print("=" * 70)
print("BUILDING ZIP SUMMARY")
print("=" * 70)

summary_rows = []

for zip_code in zip_complaints:

    complaints = zip_complaints[zip_code]
    timely_total = zip_timely_total[zip_code]
    closed_total = zip_closed[zip_code]

    summary_rows.append({
        "ZIP code": zip_code,
        "complaints": complaints,

        "unique_companies": len(zip_companies[zip_code]),
        "unique_products": len(zip_products[zip_code]),

        "timely_yes": zip_timely_yes[zip_code],
        "timely_total": timely_total,

        "timely_response_rate": (
            zip_timely_yes[zip_code] / timely_total
            if timely_total > 0
            else None
        ),

        "monetary_relief": zip_monetary_relief[zip_code],
        "nonmonetary_relief": zip_nonmonetary_relief[zip_code],
        "closed_total": closed_total,

        "monetary_relief_rate": (
            zip_monetary_relief[zip_code] / closed_total
            if closed_total > 0
            else None
        ),

        "nonmonetary_relief_rate": (
            zip_nonmonetary_relief[zip_code] / closed_total
            if closed_total > 0
            else None
        ),

        "older_american": zip_older_american[zip_code],
        "servicemember": zip_servicemember[zip_code],

        "tagged_complaints": (
            zip_older_american[zip_code]
            + zip_servicemember[zip_code]
        ),

        "older_american_rate": (
            zip_older_american[zip_code] / complaints
            if complaints > 0
            else None
        ),

        "servicemember_rate": (
            zip_servicemember[zip_code] / complaints
            if complaints > 0
            else None
        ),
    })


summary = pd.DataFrame(summary_rows)

summary = summary.sort_values(
    "complaints",
    ascending=False
)

summary.to_csv(
    OUTPUT_DIR / "cfpb_2025_zip_summary.csv",
    index=False
)


# ------------------------------------------------------------
# Product table
# ------------------------------------------------------------

product_rows = [
    {
        "ZIP code": zip_code,
        "Product": product,
        "complaints": count,
    }
    for (zip_code, product), count in zip_product.items()
]

product_df = pd.DataFrame(product_rows)

if not product_df.empty:
    product_df = product_df.sort_values(
        ["ZIP code", "complaints"],
        ascending=[True, False],
    )

product_df.to_csv(
    OUTPUT_DIR / "cfpb_2025_zip_product.csv",
    index=False
)


# ------------------------------------------------------------
# Issue table
# ------------------------------------------------------------

issue_rows = [
    {
        "ZIP code": zip_code,
        "Issue": issue,
        "complaints": count,
    }
    for (zip_code, issue), count in zip_issue.items()
]

issue_df = pd.DataFrame(issue_rows)

if not issue_df.empty:
    issue_df = issue_df.sort_values(
        ["ZIP code", "complaints"],
        ascending=[True, False],
    )

issue_df.to_csv(
    OUTPUT_DIR / "cfpb_2025_zip_issue.csv",
    index=False
)


# ------------------------------------------------------------
# Final report
# ------------------------------------------------------------

print()
print("=" * 70)
print("COMPLETE")
print("=" * 70)

print(f"Total rows read:       {total_rows:,}")
print(f"Valid ZIP rows:        {valid_zip_rows:,}")
print(f"Unique ZIPs:           {len(summary):,}")

if not summary.empty:
    print()
    print("Top 20 ZIPs by complaint count:")
    print(
        summary[
            ["ZIP code", "complaints"]
        ].head(20).to_string(index=False)
    )

print()
print("Saved:")
print(OUTPUT_DIR / "cfpb_2025_zip_summary.csv")
print(OUTPUT_DIR / "cfpb_2025_zip_product.csv")
print(OUTPUT_DIR / "cfpb_2025_zip_issue.csv")