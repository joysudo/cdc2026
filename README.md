# Geographic Analysis of CFPB Consumer Complaints

An exploratory data science and GIS project analyzing geographic patterns in complaints submitted to the **Consumer Financial Protection Bureau (CFPB)**.

The project combines CFPB consumer complaint data with U.S. Census population estimates and geographic boundaries to examine where reported consumer complaints are concentrated, how complaint rates vary across communities, and which financial products and issues contribute to geographic differences.

> **Project status:** Exploratory analysis and initial GIS visualization. Further analysis of credit-reporting complaints, spatial clustering, socioeconomic factors, and time trends is planned.

---

## Research Questions

The project is centered around several questions:

1. **Where are CFPB complaints concentrated geographically?**
2. **How do complaint rates change after accounting for population size?**
3. **Are areas with unusually high complaint rates geographically clustered?**
4. **Which financial products and complaint issues account for these patterns?**
5. **Are geographic patterns particularly pronounced for credit-reporting complaints?**
6. **How are complaint patterns related to characteristics of the communities in which they occur?**
7. **Do geographic patterns persist or change over time?**

The analysis is designed to move from descriptive geographic patterns toward more detailed investigation rather than assuming that a geographic concentration has a particular cause.

---

## Data Sources

### Consumer Financial Protection Bureau

The primary dataset is the **CFPB Consumer Complaint Database**, which contains complaints submitted by consumers about financial products and services.

The dataset includes information such as:

- Date received
- Product
- Sub-product
- Issue
- Sub-issue
- Company
- State
- ZIP code
- Tags
- Submission method
- Company response
- Timely response indicator
- Complaint ID

The analysis currently focuses on complaints received during **2025**.

Source:

https://www.consumerfinance.gov/data-research/consumer-complaints/

---

### U.S. Census Bureau

Population estimates are from the **2024 American Community Survey (ACS) 5-year estimates**.

The population variable used is:

- `B01003_E001` — Total Population estimate

Population estimates are associated with Census **ZIP Code Tabulation Areas (ZCTAs)**.

The 2024 ACS is used because the 2025 ACS 5-year estimates are not yet available for this analysis.

Source:

https://www.census.gov/programs-surveys/acs

---

### Census TIGER/Line ZCTA Boundaries

Geographic boundaries are from the **2024 Census TIGER/Line ZCTA5 shapefile**.

These boundaries allow the ZIP/ZCTA-level complaint data to be visualized geographically in QGIS.

Source:

https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html

---

## Methodology

### 1. CFPB Data Processing

The raw CFPB complaint dataset is several gigabytes in size, so it is processed in chunks rather than loaded entirely into memory.

The processing pipeline:

1. Read the CFPB data in chunks.
2. Select complaints received during 2025.
3. Validate and standardize five-digit ZIP codes.
4. Aggregate complaints by ZIP code.
5. Calculate complaint and company-response measures.
6. Aggregate complaints by ZIP/product and ZIP/issue combinations.

The raw dataset contains:

**18,023,390 total complaint records**

of which:

**5,442,963 were received in 2025.**

Of the 2025 complaints:

**5,090,297 had valid five-digit ZIP codes**, representing approximately **93.5%** of 2025 complaints.

---

### 2. Population Normalization

Raw complaint counts can be misleading because larger populations will generally generate more complaints.

To account for population size, complaints are normalized using:

```text
complaints per 1,000 residents =
    complaints / population × 1,000