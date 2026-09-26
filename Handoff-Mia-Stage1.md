# CFPB Consumer Complaint Data Science Project --- Chat Handoff

## Purpose of this document

This document is a complete handoff for continuing the CFPB Consumer
Complaint Database data science / GIS hackathon project in a new ChatGPT
conversation. It captures the project idea, team plan, work completed,
exact local setup, results, decisions, and immediate next steps.

------------------------------------------------------------------------

# 1. Project overview

The project uses the **CFPB Consumer Complaint Database** to tell a
data-driven story about geographic patterns in consumer complaints.

Official CFPB page:
https://www.consumerfinance.gov/data-research/consumer-complaints/

The goal is **not** simply to make a map of complaints. The team wants
to investigate:

-   Where complaints are geographically concentrated.
-   Whether apparent high-complaint areas remain high after population
    normalization.
-   Whether different complaint types have different geographic
    patterns.
-   What products/issues drive complaints in unusual areas.
-   Whether complaint tags such as Older American or Servicemember are
    disproportionately represented.
-   Whether company response patterns vary geographically after
    accounting for complaint type.
-   Whether geographic patterns change or persist over time.
-   Whether socioeconomic/geographic/systemic factors might help explain
    reporting patterns.

Potential systemic factors being considered include:

-   redlining / historical lending patterns
-   residential segregation / dissimilarity
-   rurality
-   access to financial services
-   employment
-   poverty
-   age
-   demographics
-   military / servicemember populations
-   population density
-   other Census / NC OSBM variables

A key analytical caution: **CFPB complaints are not a statistical sample
of all consumers and are not a direct measure of financial harm.**
Findings should be phrased as geographic patterns in **reported CFPB
complaints**, not as geographic patterns in actual financial harm.

------------------------------------------------------------------------

# 2. Team project structure

The current rough project plan is:

## Stage 1 --- Geographic baseline / GIS

Goal:

> Build a geographic baseline of CFPB complaints in 2025, identify areas
> with unusually high complaint rates, and characterize what types of
> complaints and company responses drive those geographic patterns.

Questions:

1.  Where are CFPB complaints geographically concentrated?
2.  Do the same apparent hotspots remain after population normalization?
3.  Do different complaint types have different geographic hotspots?
4.  What products/issues account for complaints in the highest-rate
    ZIPs?
5.  Are CFPB tags (Older American, Servicemember, etc.)
    disproportionately represented?
6.  Do company response patterns differ across geographic areas after
    accounting for complaint type?
7.  Are geographic patterns persistent over time? (More fully Stage 4.)

Initial outputs:

-   cleaned 2025 CFPB dataset
-   ZIP-level complaint counts
-   complaints per 1,000 residents
-   raw-count map in QGIS
-   population-normalized map in QGIS
-   5--10 candidate high-rate areas with profiles
-   product-specific maps
-   descriptive statistics / tables

Important terminology: - Use **Census ZCTAs** for mapping rather than
treating USPS ZIP codes as polygons. - A high rate in a tiny ZIP does
not automatically mean a statistically significant spatial hotspot. -
Initially call these **candidate high-rate areas**. - Later, actual
spatial clustering methods such as Getis-Ord Gi\* or Local Moran's I can
test whether high-rate areas are surrounded by other high-rate areas.

## Stage 2 --- Explain the geographic pattern / systemic factors

The central research question should move from simply **"where are complaints high?"** to **"what characteristics or processes might explain why complaint rates differ geographically?"**

The current candidate explanations are:

1. **Population size** — raw complaint counts naturally favor large population centers, so normalize by population first.
2. **Complaint composition** — some areas may have unusually high concentrations of credit reporting, debt collection, mortgage, etc.
3. **Race / demographic composition** — test whether geographic complaint rates are associated with the racial composition of an area, especially Black population share. This came from the team's observation that some of the state-level geographic pattern appears to line up with places with larger Black populations and from the hypothesis that complaint submission rates may differ across demographic groups.
4. **Economic conditions** — poverty, income, employment, education, housing, etc.
5. **Access / geography** — rurality, population density, access to financial services, and related geographic measures.
6. **Historical structural factors** — historical redlining, residential segregation, and related measures, if appropriate data can be obtained.
7. **Complaint-system / reporting behavior** — submission method, repeat complaints, mass/duplicate complaints, or other factors that could cause complaint counts to differ even without corresponding differences in underlying consumer harm.
8. **Company concentration** — some areas may generate more complaints because particular companies/products are concentrated there.

### Race-normalization idea — important methodological distinction

A proposed analysis is to examine whether the geographic pattern changes when accounting for **racial composition**, particularly the share or number of Black residents in each area.

This needs to be framed carefully. The CFPB complaint dataset does **not** provide the race of the individual who submitted each complaint, so we cannot directly calculate something like "complaints per Black person" and interpret it as an individual-level Black complaint rate. A denominator based on Black population would instead be an **area-level/ecological measure**.

A better first analysis is likely to:

- add Census ACS measures such as total Black population and Black population share for each ZCTA/state;
- compare complaint rates with Black population share;
- examine whether high-rate areas have systematically different racial compositions;
- potentially model complaint rate/count as a function of racial composition while also controlling for other socioeconomic/geographic variables;
- compare whether the apparent state-level pattern changes after demographic adjustment.

If the team wants to calculate a rate using Black population as a denominator, label it explicitly as an **area-level complaints-per-Black-resident measure**, not as the complaint rate of Black individuals.

Also, do not assume in advance that Black residents "write more complaints." The project should test that hypothesis. The existing CFPB research can provide context about demographic differences in complaint submission, but the team's 2025 data should be analyzed directly rather than treating the hypothesis as established.

Potential data:
- Census ACS
- NC OSBM
- employment
- poverty
- age
- demographics / racial composition
- rurality
- military populations
- historical redlining / segregation measures
- population density
- access to financial services
- other ZIP/ZCTA- or county-level indicators

The key question is whether these variables explain some of the geographic variation **after accounting for population and complaint composition**, not simply whether they overlap visually on a map.

Also normalize/compare company response types within complaint type rather than naively comparing raw response distributions.

Potential data: - Census ACS - NC OSBM - employment - poverty - age -
demographics - rurality - military populations - historical redlining /
segregation measures - other ZIP/county-level indicators

Also normalize/compare company response types within complaint type
rather than naively comparing raw response distributions.

## Stage 3 --- Modeling

Use statistical models to test the candidate explanations rather than relying only on maps.

Potential approaches:

- **Count/rate models:** model complaint counts while accounting for population exposure, potentially using an offset.
- **Regression with ACS variables:** test relationships between complaint rates and Black population share, poverty, income, age, density, rurality, etc.
- **Product-specific models:** determine whether demographic/geographic relationships are different for credit reporting versus other products.
- **Multinomial or categorical models:** potentially investigate differences in complaint/product or response categories.
- **Company-adjusted analysis:** determine whether geographic differences remain after accounting for the companies/products represented in an area.

The goal is not to claim a causal effect from observational geographic data. The models should identify **associations and explanatory factors** that are consistent with the observed pattern and quantify how much geographic variation they account for.

## Stage 4 --- Spatial statistics and time

### Spatial statistics

After the descriptive maps and demographic/economic analysis, test whether high-rate areas actually form spatial clusters.

Potential methods:
- Global Moran's I — asks whether complaint rates are spatially autocorrelated overall.
- Local Moran's I — identifies local clusters/outliers.
- Getis-Ord Gi* — identifies statistically concentrated high/low areas.

This is where the project can move from calling areas **candidate high-rate areas** to making a statistically supported statement about spatial clustering.

### Time

Look at geographic patterns over time and visualize whether they:
- persist;
- emerge;
- disappear;
- change in magnitude;
- change product composition; or
- change in demographic/geographic relationships.

The team can eventually compare yearly complaint rates and determine whether the 2025 pattern is unusual or persistent.

## Final deliverable

Likely: - slideshow and/or website - GitHub repository - visual
storytelling - clear methodology and limitations

Another teammate, Audrija, is asking Claude which ZIP codes/areas have
the highest complaint levels as a quick comparison.

------------------------------------------------------------------------

# 2A. Detailed current status — what has actually been completed

The project has now progressed substantially beyond the original raw-data-processing stage. The following work is complete and should be treated as the current baseline rather than repeated from scratch.

## Raw CFPB data processing

- Raw file: `data/raw/complaints.csv` (~5.1 GB).
- Total rows processed: **18,023,390**.
- 2025 complaints: **5,442,963**.
- 2025 complaints with valid 5-digit ZIP codes: **5,090,297 (93.52%)**.
- The raw file is processed in chunks because the machine has ~15.7 GB RAM.
- A complaint-level cleaned 2025 file was subsequently created at `data/processed/cfpb_2025_cleaned.csv`; this is ~1.6 GB and should not be committed to GitHub.

## ZIP-level aggregation

The 2025 complaints were aggregated by ZIP code, with additional ZIP-level measures for later analysis. Current outputs include:

- `data/processed/zip_analysis/cfpb_2025_zip_summary.csv`
- `data/processed/zip_analysis/cfpb_2025_zip_product.csv`
- `data/processed/zip_analysis/cfpb_2025_zip_issue.csv`

Results:

- **22,024 unique ZIP codes** appear in the valid 5-digit ZIP complaint data.
- The ZIP-level totals reproduce the complaint counts from the raw-data processing, providing a consistency check.
- ZIP-level measures include complaint counts, unique companies/products, timely-response information, monetary/nonmonetary relief, and CFPB tags such as Older American and Servicemember.

## Census population normalization

Because 2025 ACS 5-year population data are not yet available, the project uses **2024 ACS 5-year ZCTA population** as the denominator for 2025 complaints. The population variable is `B01003_E001` (total population).

The downloaded table-based ACS file was successfully filtered to Census ZCTAs and saved as:

`data/census/acs_2024_zcta_population.csv`

It contains **33,772 ZCTAs**.

The complaint ZIP data were merged to the Census ZCTA population data and converted to:

`complaints_per_1000 = complaints / population * 1000`

The resulting file is:

`data/processed/zip_analysis/cfpb_2025_zip_rates.csv`

The match results were checked:

- Complaint ZIPs: **22,024**
- Matched to Census ZCTAs: **19,226 (87.30%)**
- Unmatched ZIPs: **2,798**
- Complaint records with positive-population ZCTAs: **5,060,992**, or **99.42% of valid-ZIP complaints**.
- An initial population threshold of **1,000 residents** is being used for descriptive rate analysis to reduce instability from very small populations.

## Initial rate analysis

Among ZCTAs with population >=1,000:

- ZCTAs analyzed: **17,748**
- Complaints represented: **5,049,523**
- Population represented: **320,919,882**
- Median complaint rate: **4.80 per 1,000**
- 90th percentile: **28.23 per 1,000**
- 95th percentile: **42.12 per 1,000**
- 99th percentile: **80.24 per 1,000**
- Maximum: **332.54 per 1,000**

The distribution is extremely right-skewed. This matters because raw counts and per-capita rates tell different stories, and very high rates can occur in relatively small populations.

## Top-1% descriptive analysis

The current descriptive comparison defines the top 1% of qualifying ZCTAs by complaint rate as the **178 ZCTAs at or above 80.239 complaints per 1,000**. This is a descriptive grouping, not a statistical hotspot test.

Top 1% group:
- **178 ZCTAs**
- **547,749 complaints**
- **5,298,810 population**
- Mean rate: **106.06 per 1,000**
- Median rate: **99.63 per 1,000**
- Complaint share: **10.85%**
- Population share: **1.65%**

Other 99%:
- **17,570 ZCTAs**
- **4,501,774 complaints**
- **315,621,072 population**
- Mean rate: **9.88 per 1,000**
- Median rate: **4.71 per 1,000**
- Complaint share: **89.15%**
- Population share: **98.35%**

This gives the project a useful descriptive finding to investigate further: a relatively small share of the population is located in ZCTAs that account for a disproportionately large share of reported CFPB complaints. It does **not** establish why those areas have higher complaint rates.

## Product composition analysis

Credit reporting dominates both groups, but it is even more concentrated in the highest-rate group.

Other 99% of ZCTAs:
- Credit reporting: **88.92%**
- Debt collection: **5.08%**
- Credit card: **1.61%**
- Checking/savings: **1.46%**
- Money transfer: **1.37%**

Top 1% of ZCTAs:
- Credit reporting: **92.79%**
- Debt collection: **4.37%**
- Money transfer: **0.84%**
- Checking/savings: **0.68%**
- Credit card: **0.62%**

The interpretation at this stage is descriptive: credit reporting accounts for a very large fraction of complaints everywhere, and an even larger fraction in the highest-rate ZCTAs. This does not establish that credit reporting causes the geographic differences.

## QGIS work completed

QGIS Desktop **3.44.14** is installed and the Census ZCTA5 shapefile has been loaded. The processed CFPB attribute table has been joined to the ZCTA polygons using:

- Join field: `ZIP code`
- Target field: `ZCTA5CE20`

A graduated choropleth using `complaints_per_1000` has been created. The national map is visually dense, so the next visualization work should focus on clearer regional views, high-rate-area highlighting, and product-specific maps rather than relying only on a dense national map.

## Pre-QGIS analysis outputs

The current pre-QGIS script is `scripts/stage1preQgis/pre_qgis_analysis.py`. It has produced:

- `top_1_percent_zctas.csv`
- `top_25_rates.csv`
- `rate_group_comparison.csv`
- `product_composition_by_rate_group.csv`
- `product_comparison.csv`
- `issue_composition_by_rate_group.csv`
- `cfpb_2025_qgis_attributes.csv`

These outputs support both QGIS visualization and later statistical analysis.

# 2B. Revised project question / story

The project has evolved from the simple question **“Where are CFPB complaints highest?”** to a more interesting question:

> **Why do reported CFPB complaint rates differ so much across geographic areas, and how much of the pattern can be explained by population composition, complaint type, company mix, reporting behavior, and socioeconomic/geographic characteristics?**

The eventual story should distinguish between:

1. **Where complaints are reported.**
2. **How large the complaint rate is after population normalization.**
3. **What kinds of complaints make up those rates.**
4. **Whether demographic/economic composition is associated with the pattern.**
5. **Whether complaint-system behavior or submission practices could contribute to the pattern.**
6. **Whether high-rate areas form statistically meaningful spatial clusters.**
7. **Whether the pattern persists over time.**

The project should not assume any one explanation in advance. The analyses are designed to test competing explanations.

# 2C. New team idea — race / Black population normalization

A new hypothesis from the team is that part of the geographic pattern may track **racial composition**, particularly the share of the population that is Black. The observation motivating this idea is that some states/areas with high CFPB complaint rates also have relatively large Black populations. The team has discussed whether the apparent alignment could reflect differences in complaint-reporting behavior.

This should be treated as a **testable hypothesis, not an established explanation**. In particular, the project should not assume that Black residents “write more complaints” as a general causal fact. Instead, we can measure whether complaint rates are associated with the racial composition of an area and investigate possible mechanisms.

Possible analyses:

### A. State-level comparison

For each state, calculate:

- CFPB complaints per 100,000 residents
- Black population share
- potentially other racial/ethnic population shares

Then visualize the relationship between complaint rate and Black population share. This is a descriptive association and should not be interpreted causally.

### B. ZIP/ZCTA-level comparison

For each ZCTA, add Census racial-composition variables, especially Black population share. Then examine whether high complaint-rate ZCTAs tend to have different racial compositions than lower-rate ZCTAs.

### C. Race-specific denominator / normalization

Rather than simply dividing all complaints by total population, investigate alternative denominators or standardized rates where the data support them. For example, if a complaint category can reasonably be associated with a particular population group, compare its complaint rate relative to the size of that group. This needs to be designed carefully because CFPB complaint records generally do not identify the race of the individual complainant.

### D. Multivariable analysis

Race should ultimately be analyzed alongside other variables such as poverty, income, age, employment, rurality, population density, and access to financial services. This helps determine whether an observed racial-composition association remains after accounting for other correlated geographic characteristics.

### E. Expected-vs-observed complaints

A stronger version of “normalizing for race” would be to construct an expected complaint rate based on population composition and compare observed complaints with expected complaints. This could help distinguish a simple demographic-composition effect from areas with unusually high or low complaint reporting relative to their population structure. The exact method should be selected after examining the available Census and CFPB variables.

**Important limitation:** because the CFPB database does not generally provide complainant race as a field for every complaint, area-level racial composition is an ecological variable. A relationship between the racial composition of a ZCTA and its complaint rate cannot be interpreted as proving that individuals of a particular race are more or less likely to complain.

# 2D. Expanded analysis plan

## Phase 1 — Geographic baseline

**Completed:**
- clean/filter 2025 CFPB complaints
- validate ZIP coverage
- aggregate complaints by ZIP
- obtain 2024 ACS ZCTA population
- calculate complaints per 1,000
- compare raw counts with normalized rates
- create initial QGIS map
- characterize top-rate ZCTAs
- compare product and issue composition

**Next:**
- complete state-level complaint counts and state population rates
- create a state-level map/table as a simpler geographic baseline
- examine state × product composition
- make a credit-reporting-only geographic map

## Phase 2 — Explain what is driving the geographic pattern

For high-rate versus other areas, examine:
- product composition
- issue composition
- company concentration / dominant companies
- submission method (`Submitted via`)
- company response type
- timely-response rate
- monetary/nonmonetary relief
- Older American and Servicemember tags
- racial composition
- poverty/income
- employment
- age
- rurality/density
- access to financial services
- other relevant Census/NC OSBM variables

The company-response analysis should compare areas within similar complaint types where possible, rather than interpreting raw response distributions without accounting for the fact that different products/issues may have different response patterns.

## Phase 3 — Demographic and socioeconomic modeling

Build a ZCTA-level modeling dataset combining complaint rates/counts with Census variables. Candidate predictors include racial composition, poverty, income, age, employment, rurality, population density, and financial-access measures.

Potential models include count/rate regression and, if appropriate for the outcome, multinomial regression for complaint/product categories or response categories. Model choice should follow the structure of the data rather than being predetermined.

The main goal is to estimate associations while controlling for correlated geographic factors, not to claim causal effects from observational ZIP-level data.

## Phase 4 — Spatial statistics

After descriptive maps and covariate analysis, test whether high-rate areas actually cluster geographically. Candidate methods:
- Global Moran’s I
- Local Moran’s I
- Getis-Ord Gi*

This is where the term **statistical hotspot/cluster** becomes appropriate if the method supports it. Until then, use “high-rate area” or “candidate hotspot.”

## Phase 5 — Time analysis

Repeat the geographic aggregation for multiple years and determine whether high-rate areas:
- persist
- emerge
- disappear
- change product composition
- change demographic associations

This can help distinguish persistent geographic patterns from one-year anomalies.

## Phase 6 — Final story

The final presentation/website should move from observation to explanation:

1. **Raw map:** where are the most complaints?
2. **Normalized map:** what changes after accounting for population?
3. **Composition:** what types of complaints create the geographic differences?
4. **Demographics:** how much of the pattern is associated with population composition, including race?
5. **Systemic factors:** what other socioeconomic/geographic variables are associated?
6. **Spatial analysis:** are high-rate areas actually clustered?
7. **Time:** do the patterns persist?
8. **Limitations:** what can and cannot be inferred from CFPB complaint data?

This gives the project a data-science story rather than a collection of disconnected maps.

# 3. Interesting hypotheses / story ideas discussed

Some early observations / hypotheses:

-   Credit reporting / consumer reporting complaints make up a large
    share of CFPB complaints, but the team thinks simply analyzing the
    largest category may be less interesting.
-   Older consumers sometimes report that a debt was paid/discharged
    while the company says the debt still exists.
-   Servicemembers have higher percentages of some debt-related
    complaints, especially mortgage, somewhat similar to patterns seen
    among older consumers.
-   A possible geographic story is: **historical redlining → residential
    segregation / financial access → differences in credit/consumer
    reporting complaints**
-   Another key idea: **large cities may have more complaints simply
    because they have more people**, so raw counts need population
    normalization.

The project should tell a story rather than just present maps.

------------------------------------------------------------------------

# 4. Local development setup

Project folder:

``` text
C:\Users\miala\CDC\cdc2026
```

Git Bash is being used in VS Code, NOT PowerShell.

Terminal prompt looks approximately:

``` text
(.venv)
miala@LAPTOP-... MINGW64 ~/CDC/cdc2026 (main)
$
```

The project now has a Python virtual environment:

``` text
.venv/
```

The user selected Python rather than Conda `base` when VS Code asked
about the environment.

Pandas is installed in the virtual environment.

To activate it in Git Bash:

``` bash
source .venv/Scripts/activate
```

To verify pandas:

``` bash
python -c "import pandas; print(pandas.__version__)"
```

------------------------------------------------------------------------

# 5. Raw CFPB data

The raw CFPB CSV was downloaded and unzipped into:

``` text
data/raw/complaints.csv
```

File size:

``` text
5.1 GB
```

Computer RAM:

``` text
15.7 GB
```

Because the raw CSV is huge, it must NOT be loaded into memory all at
once with ordinary:

``` python
pd.read_csv(...)
```

Instead, the project processes it in chunks of 100,000 rows.

The raw file should NOT be pushed to GitHub.

------------------------------------------------------------------------

# 6. CFPB CSV columns

The actual header is:

``` text
Date received,Product,Sub-product,Issue,Sub-issue,Company public response,Company,State,ZIP code,Tags,Submitted via,Date sent to company,Company response to consumer,Timely response?,Complaint ID
```

The current Stage 1 processing script uses:

``` text
Date received
Product
Sub-product
Issue
Sub-issue
Company
State
ZIP code
Tags
Company response to consumer
Timely response?
Complaint ID
```

It intentionally excludes for now:

``` text
Company public response
Submitted via
Date sent to company
```

------------------------------------------------------------------------

# 7. Current processing script

File:

``` text
notebooks/stage1_process_cfpb.py
```

Important: the script's paths were corrected because it is run from the
project root.

Correct paths:

``` python
INPUT_FILE = "data/raw/complaints.csv"
OUTPUT_FILE = "data/processed/cfpb_2025_zip_counts.csv"
```

NOT:

``` python
../data/raw/complaints.csv
```

The script:

1.  Reads the raw CSV in 100,000-row chunks.
2.  Parses `Date received`.
3.  Filters to:

``` text
2025-01-01 <= Date received < 2026-01-01
```

4.  Converts ZIP to string.
5.  Keeps only exactly 5-digit ZIPs.
6.  Incrementally counts complaints by ZIP.
7.  Saves the result.

It was run with:

``` bash
python notebooks/stage1_process_cfpb.py
```

------------------------------------------------------------------------

# 8. Current CFPB processing results

The script successfully completed.

Exact output:

``` text
Total rows processed: 18,023,390
2025 complaints: 5,442,963
2025 complaints with valid 5-digit ZIP: 5,090,297
Percent with valid ZIP: 93.52%

Saved to: data/processed/cfpb_2025_zip_counts.csv
```

The resulting file is:

``` text
data/processed/cfpb_2025_zip_counts.csv
```

File size:

``` text
216 KB
```

This file is small enough to commit to GitHub.

Top 20 ZIP codes by raw complaint count:

``` text
ZIP code  complaints
30349       10843
33025        9356
77449        9337
33311        9167
60411        9090
33178        8896
30253        8661
30331        7867
35215        7594
30318        7226
33169        7184
77493        7084
30058        7017
30016        6596
75052        6566
33023        6539
30281        6498
30213        6415
60620        6397
93313        6326
```

Interpretation so far: - These are raw counts only. - They should NOT
yet be called geographic hotspots. - Population is a major confounder. -
The next step is population normalization.

The 93.52% valid ZIP coverage is strong and should be documented as a
limitation/coverage statistic.

------------------------------------------------------------------------

# 9. GitHub status / recommended push

The user asked whether to push the work now. Recommendation: **yes**,
but only the code and small processed output.

Do NOT push: - `data/raw/complaints.csv` - `.venv/` - large Census
shapefiles - API keys/secrets

Suggested `.gitignore`:

``` gitignore
# Python
.venv/
__pycache__/
*.pyc

# Raw CFPB data — VERY large
data/raw/

# Local QGIS files
*.qgz~
*.qgs~

# OS / editor
.DS_Store/
.vscode/
```

Do NOT ignore `data/processed/` because the processed ZIP-level CSV is
only \~216 KB and is useful to teammates.

Suggested commands:

``` bash
git status
```

Verify that `data/raw/complaints.csv` and `.venv/` are NOT listed.

Then:

``` bash
git add .gitignore notebooks/stage1_process_cfpb.py data/processed/cfpb_2025_zip_counts.csv
git commit -m "Add CFPB 2025 ZIP-level complaint baseline"
git push
```

Potential README note: - raw CFPB data are intentionally excluded
because of file size - source is CFPB Consumer Complaint Database - raw
file should be downloaded separately from the official CFPB site

------------------------------------------------------------------------

# 10. NEXT STEP --- Census population data

The next immediate task is to get population for Census ZCTAs and
calculate complaint rates.

We decided to use **2024 ACS 5-year population** as the denominator
because the complaint period is 2025 and the 2025 ACS 5-year dataset is
not yet available.

Use:

``` text
2024 ACS 5-year
B01003_001E = Total Population
Geography = ZIP Code Tabulation Area (ZCTA)
```

Official Census ACS developer page:
https://www.census.gov/data/developers/data-sets/acs-5year.html

Census 2024 ACS total population table:
https://data.census.gov/table/ACSDT5Y2024.B01003

Census API key signup: https://api.census.gov/data/key_signup.html

Important: **Do not commit the Census API key to GitHub.**

------------------------------------------------------------------------

# 11. Planned Census script

Create:

``` text
notebooks/get_census_population.py
```

Planned code:

``` python
import os
import requests
import pandas as pd

CENSUS_KEY = os.environ.get("CENSUS_API_KEY")

if not CENSUS_KEY:
    raise ValueError("CENSUS_API_KEY environment variable is not set.")

URL = (
    "https://api.census.gov/data/2024/acs/acs5"
    "?get=NAME,B01003_001E"
    "&for=zip%20code%20tabulation%20area:*"
    f"&key={CENSUS_KEY}"
)

response = requests.get(URL)
response.raise_for_status()

data = response.json()

df = pd.DataFrame(data[1:], columns=data[0])

df = df.rename(columns={
    "zip code tabulation area": "ZIP code",
    "B01003_001E": "population"
})

df["ZIP code"] = df["ZIP code"].astype(str).str.zfill(5)
df["population"] = pd.to_numeric(df["population"], errors="coerce")

df = df[["ZIP code", "population"]]

output = "data/census/acs_2024_zcta_population.csv"
df.to_csv(output, index=False)

print(f"Saved {len(df):,} ZCTAs to {output}")
print(df.head())
```

Install requests in the virtual environment:

``` bash
python -m pip install requests
```

Then, in Git Bash, after getting a Census API key:

``` bash
export CENSUS_API_KEY="YOUR_KEY_HERE"
```

Do NOT commit that command or key.

Test:

``` bash
echo $CENSUS_API_KEY
```

Then run:

``` bash
python notebooks/get_census_population.py
```

Expected output should be something like:

``` text
Saved 33,xxx ZCTAs to data/census/acs_2024_zcta_population.csv
```

------------------------------------------------------------------------

# 12. Merge CFPB and Census data

After the Census CSV is created, merge:

``` python
complaints_by_zip = pd.read_csv(
    "data/processed/cfpb_2025_zip_counts.csv",
    dtype={"ZIP code": str}
)

population = pd.read_csv(
    "data/census/acs_2024_zcta_population.csv",
    dtype={"ZIP code": str}
)

zip_data = complaints_by_zip.merge(
    population,
    on="ZIP code",
    how="left"
)

zip_data["complaints_per_1000"] = (
    zip_data["complaints"] / zip_data["population"] * 1000
)

zip_data.to_csv(
    "data/processed/cfpb_2025_zip_rates.csv",
    index=False
)
```

The final dataset should look like:

``` text
ZIP code | complaints | population | complaints_per_1000
```

Keep both: - raw complaints - normalized complaints per 1,000

This matters because very small populations can create unstable rates.

------------------------------------------------------------------------

# 13. GIS / QGIS next step

The user is a **complete beginner to GIS/QGIS**, so explanations should
be hands-on and step-by-step.

QGIS: https://qgis.org/download/

We will eventually download the Census 2024 ZCTA TIGER/Line shapefile
from:

https://www2.census.gov/geo/tiger/TIGER2024/ZCTA520/

The Census ZCTA shapefile is large and should NOT be committed to
GitHub.

Important: - Use **Census ZCTA polygons**, not literal USPS ZIP
boundaries. - The ZCTA target field will likely be:

``` text
ZCTA5CE20
```

-   Join to our CSV field:

``` text
ZIP code
```

Planned QGIS workflow:

1.  Download and unzip Census 2024 ZCTA shapefile.
2.  Open the `.shp` file in QGIS.
3.  Add `cfpb_2025_zip_rates.csv` as a delimited-text table with no
    geometry.
4.  Join the CSV to the ZCTA polygon layer.
5.  Open Layer Properties → Symbology.
6.  Choose Graduated.
7.  First map:
    -   value = `complaints`
    -   use a sequential color ramp
    -   5 quantile classes for exploration
8.  Duplicate the layer.
9.  Second map:
    -   value = `complaints_per_1000`
10. Compare raw-count and normalized maps.

The first map answers: \> Where are the most complaints?

The second asks: \> Where are complaints unusually high relative to the
population?

Do not describe the quantile classes as statistically significant
hotspots.

------------------------------------------------------------------------

# 14. Later geographic analysis

After basic maps work, consider:

### Product-specific maps

For example: - credit reporting - debt collection - mortgage - credit
card - checking/savings

This can reveal that overall complaint geography may hide very different
patterns by complaint type.

### Candidate high-rate ZIP profiles

For perhaps 5--10 interesting ZIPs, create a table:

``` text
ZIP
Population
2025 complaints
Complaints per 1,000
Dominant product
Dominant issue
Company response distribution
Tags
```

The selection should not simply be the top raw counts. Prefer areas that
are interesting after normalization and have enough complaints to be
reasonably stable.

### Spatial statistics

Later, if needed: - Getis-Ord Gi\* - Local Moran's I - other spatial
clustering methods

These can distinguish an isolated high-rate ZIP from a true cluster of
neighboring high-rate ZIPs.

------------------------------------------------------------------------

# 15. Potential story structure

A possible eventual narrative:

### Part 1

"At first glance, complaints are concentrated in large population
centers."

### Part 2

"After normalizing by population, a different geographic pattern
emerges."

### Part 3

"Those high-rate areas are not all the same --- different
products/issues drive different geographic patterns."

### Part 4

"Some of those patterns overlap with demographic/economic/geographic
characteristics."

### Part 5

"Certain complaint types / groups / company response patterns may help
explain what is happening."

### Part 6

"Some patterns persist or change over time."

This should be tested with data rather than assumed.

------------------------------------------------------------------------

# 16. Important methodological cautions

1.  **Complaints are not prevalence.** A high complaint rate does not
    necessarily mean residents experience more financial harm.

2.  **Reporting behavior matters.** A low complaint rate could reflect
    low harm, low awareness, low access to complaint channels, or
    underreporting.

3.  **Population denominator is imperfect.** Using 2024 ACS population
    for 2025 complaints is reasonable but should be labeled clearly.

4.  **ZIP codes vs ZCTAs.** CFPB uses ZIP codes while Census provides
    ZCTAs. The mapping is an approximation.

5.  **Small-area rates can be unstable.** A ZIP with a tiny population
    can have a huge per-capita rate from relatively few complaints.

6.  **Do not call a choropleth's top class a statistical hotspot.** Use
    "high-rate area" or "candidate hotspot" until spatial statistics are
    performed.

7.  **Do not infer causation from geographic overlap.** If a
    high-complaint area overlaps a historical redlining area, that is an
    association worth investigating, not proof that redlining caused the
    complaints.

------------------------------------------------------------------------

# 17. Useful commands for continuing

Activate environment:

``` bash
source .venv/Scripts/activate
```

Check Git status:

``` bash
git status
```

Run Stage 1 CFPB processing:

``` bash
python notebooks/stage1_process_cfpb.py
```

List processed data:

``` bash
ls -lh data/processed/
```

Preview processed CSV:

``` bash
head data/processed/cfpb_2025_zip_counts.csv
```

Install packages:

``` bash
python -m pip install pandas
python -m pip install requests
```

Run Census script:

``` bash
python notebooks/get_census_population.py
```

------------------------------------------------------------------------

# 18. Current exact stopping point

The CFPB raw data processing is **DONE**.

The latest successful results are:

``` text
18,023,390 total rows processed
5,442,963 complaints in 2025
5,090,297 valid 5-digit ZIP complaints
93.52% valid ZIP coverage
data/processed/cfpb_2025_zip_counts.csv created
```

The processed CSV is 216 KB.

The project is now past the original Census/QGIS setup stage. The immediate next tasks are:

**1. Finish the state-level baseline.**
- Run the `GEO_ID` diagnostic on the downloaded 2024 ACS table-based file.
- Extract state population correctly.
- Merge state complaint counts + population.
- Calculate complaints per 100,000 residents.
- Make a state-level comparison/map.

**2. Build the demographic/race analysis.**
- Add ACS racial composition variables, especially Black population/share.
- Compare complaint rates against racial composition.
- Test the team's hypothesis about the observed state/geographic alignment rather than assuming it is true.
- Be explicit that race is available at the area level, not for individual complainants.

**3. Build the product-specific analysis.**
- Separate credit reporting from other products.
- Map credit-reporting complaint rates.
- Analyze the major credit-reporting issues.
- Determine whether the overall geographic pattern is mostly a credit-reporting phenomenon.

**4. Profile candidate high-rate areas.**
For selected areas, combine:
- population;
- complaint rate;
- dominant products/issues;
- company concentration;
- submission method;
- company response patterns;
- CFPB tags;
- demographic/economic variables.

**5. Add socioeconomic/systemic variables.**
Test poverty, income, employment, age, density, rurality, financial access, segregation/redlining measures, and other appropriate variables.

**6. Perform spatial statistics.**
Use Moran's I / Local Moran's I / Getis-Ord Gi* if the data support it, so that the project can distinguish isolated high-rate areas from actual spatial clusters.

**7. Add time analysis.**
Compare years to determine whether geographic patterns persist, emerge, disappear, or change composition.

**8. Build the final story.**
The intended story is roughly:

```text
Raw complaint counts
      ↓
Population normalization
      ↓
Geographic concentration
      ↓
What types of complaints drive it?
      ↓
Does demographic/economic composition explain part of it?
      ↓
Does company / submission behavior explain part of it?
      ↓
Are there statistically significant spatial clusters?
      ↓
Do the patterns persist over time?
```

The goal is to move from a descriptive map to a defensible explanation of the geographic variation in **reported CFPB complaints**.

The user prefers step-by-step guidance and wants to understand what each
step means, not just receive code.
