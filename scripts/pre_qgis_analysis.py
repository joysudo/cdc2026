import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

RATE_FILE = Path(
    "data/processed/zip_analysis/cfpb_2025_zip_rates.csv"
)

PRODUCT_FILE = Path(
    "data/processed/zip_analysis/cfpb_2025_zip_product.csv"
)

ISSUE_FILE = Path(
    "data/processed/zip_analysis/cfpb_2025_zip_issue.csv"
)

OUTPUT_DIR = Path(
    "data/processed/pre_analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD ZIP-LEVEL DATA
# ============================================================

print("=" * 70)
print("LOADING ZIP-LEVEL DATA")
print("=" * 70)

rates = pd.read_csv(
    RATE_FILE,
    dtype={"ZIP code": "string"}
)

print(f"Total ZIP records: {len(rates):,}")


# ============================================================
# ANALYTICAL POPULATION
# ============================================================

# Exclude ZIP/ZCTAs where the population denominator is too small
# to produce a stable complaint rate.

analysis = rates[
    rates["population"] >= 1000
].copy()

print(f"ZCTAs with population >= 1,000: {len(analysis):,}")
print(
    f"Complaints represented: "
    f"{analysis['complaints'].sum():,}"
)


# ============================================================
# RATE DISTRIBUTION
# ============================================================

print()
print("=" * 70)
print("COMPLAINT RATE DISTRIBUTION")
print("=" * 70)

rate = analysis["complaints_per_1000"]

percentiles = {
    "25th": rate.quantile(0.25),
    "50th (median)": rate.quantile(0.50),
    "75th": rate.quantile(0.75),
    "90th": rate.quantile(0.90),
    "95th": rate.quantile(0.95),
    "99th": rate.quantile(0.99),
}

for label, value in percentiles.items():
    print(f"{label:15s}: {value:10.3f}")


# ============================================================
# DEFINE HIGH-RATE ZCTAs
# ============================================================

top_1_cutoff = rate.quantile(0.99)

analysis["rate_group"] = "Other 99%"

analysis.loc[
    analysis["complaints_per_1000"] >= top_1_cutoff,
    "rate_group"
] = "Top 1%"


top_1 = analysis[
    analysis["rate_group"] == "Top 1%"
].copy()

print()
print("=" * 70)
print("HIGH-RATE ZCTAs")
print("=" * 70)

print(f"99th percentile cutoff: {top_1_cutoff:.3f}")
print(f"Top 1% ZCTAs: {len(top_1):,}")
print(
    f"Complaints in top 1%: "
    f"{top_1['complaints'].sum():,}"
)


# ============================================================
# SAVE HIGH-RATE ZIP TABLE
# ============================================================

top_1 = top_1.sort_values(
    "complaints_per_1000",
    ascending=False
)

top_1.to_csv(
    OUTPUT_DIR / "top_1_percent_zctas.csv",
    index=False
)


# ============================================================
# COMPARE TOP 1% WITH OTHER ZCTAs
# ============================================================

print()
print("=" * 70)
print("TOP 1% VS OTHER 99%")
print("=" * 70)

comparison = (
    analysis
    .groupby("rate_group")
    .agg(
        zctas=("ZIP code", "count"),
        complaints=("complaints", "sum"),
        population=("population", "sum"),
        mean_rate=("complaints_per_1000", "mean"),
        median_rate=("complaints_per_1000", "median"),
    )
)

comparison["complaint_share"] = (
    comparison["complaints"]
    / comparison["complaints"].sum()
)

comparison["population_share"] = (
    comparison["population"]
    / comparison["population"].sum()
)

print(comparison.to_string())

comparison.to_csv(
    OUTPUT_DIR / "rate_group_comparison.csv"
)


# ============================================================
# TOP-RATE ZIP LIST
# ============================================================

top_25 = analysis.nlargest(
    25,
    "complaints_per_1000"
)

top_25[
    [
        "ZIP code",
        "complaints",
        "population",
        "complaints_per_1000",
        "rate_group",
    ]
].to_csv(
    OUTPUT_DIR / "top_25_rates.csv",
    index=False
)


# ============================================================
# LOAD PRODUCT DATA
# ============================================================

print()
print("=" * 70)
print("ANALYZING PRODUCTS")
print("=" * 70)

products = pd.read_csv(
    PRODUCT_FILE,
    dtype={"ZIP code": "string"}
)

# Identify high-rate ZIPs

high_rate_zips = set(
    top_1["ZIP code"]
)

products["rate_group"] = products["ZIP code"].isin(
    high_rate_zips
).map({
    True: "Top 1%",
    False: "Other 99%"
})


# ============================================================
# PRODUCT COMPOSITION
# ============================================================

product_summary = (
    products
    .groupby(
        ["rate_group", "Product"],
        as_index=False
    )["complaints"]
    .sum()
)

# Calculate product share within each group

product_summary["product_share"] = (
    product_summary
    .groupby("rate_group")["complaints"]
    .transform(
        lambda x: x / x.sum()
    )
)

product_summary = product_summary.sort_values(
    ["rate_group", "complaints"],
    ascending=[True, False]
)

print()
print("Product composition:")
print(
    product_summary
    .head(30)
    .to_string(index=False)
)

product_summary.to_csv(
    OUTPUT_DIR / "product_composition_by_rate_group.csv",
    index=False
)


# ============================================================
# PRODUCT COMPARISON TABLE
# ============================================================

product_pivot = (
    product_summary
    .pivot(
        index="Product",
        columns="rate_group",
        values=["complaints", "product_share"]
    )
)

product_pivot.to_csv(
    OUTPUT_DIR / "product_comparison.csv"
)


# ============================================================
# ISSUE ANALYSIS
# ============================================================

print()
print("=" * 70)
print("ANALYZING ISSUES")
print("=" * 70)

issues = pd.read_csv(
    ISSUE_FILE,
    dtype={"ZIP code": "string"}
)

issues["rate_group"] = issues["ZIP code"].isin(
    high_rate_zips
).map({
    True: "Top 1%",
    False: "Other 99%"
})


issue_summary = (
    issues
    .groupby(
        ["rate_group", "Issue"],
        as_index=False
    )["complaints"]
    .sum()
)

issue_summary["issue_share"] = (
    issue_summary
    .groupby("rate_group")["complaints"]
    .transform(
        lambda x: x / x.sum()
    )
)

issue_summary = issue_summary.sort_values(
    ["rate_group", "complaints"],
    ascending=[True, False]
)

print()
print("Top issues:")
print(
    issue_summary
    .head(40)
    .to_string(index=False)
)

issue_summary.to_csv(
    OUTPUT_DIR / "issue_composition_by_rate_group.csv",
    index=False
)


# ============================================================
# SAVE ANALYSIS DATASET FOR QGIS
# ============================================================

qgis_data = analysis[
    [
        "ZIP code",
        "complaints",
        "population",
        "complaints_per_1000",
        "rate_group",
        "unique_companies",
        "unique_products",
        "timely_response_rate",
        "monetary_relief_rate",
        "nonmonetary_relief_rate",
        "older_american_rate",
        "servicemember_rate",
    ]
].copy()

qgis_data.to_csv(
    OUTPUT_DIR / "cfpb_2025_qgis_attributes.csv",
    index=False
)


# ============================================================
# FINAL REPORT
# ============================================================

print()
print("=" * 70)
print("PRE-ANALYSIS COMPLETE")
print("=" * 70)

print()
print("Created:")
print(
    OUTPUT_DIR / "top_1_percent_zctas.csv"
)
print(
    OUTPUT_DIR / "top_25_rates.csv"
)
print(
    OUTPUT_DIR / "rate_group_comparison.csv"
)
print(
    OUTPUT_DIR / "product_composition_by_rate_group.csv"
)
print(
    OUTPUT_DIR / "product_comparison.csv"
)
print(
    OUTPUT_DIR / "issue_composition_by_rate_group.csv"
)
print(
    OUTPUT_DIR / "cfpb_2025_qgis_attributes.csv"
)