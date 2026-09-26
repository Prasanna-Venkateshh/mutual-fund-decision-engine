# Mutual Fund Decision Engine — Authoritative Data Sources Catalogue

**Project:** `mutual-fund-decision-engine`  
**Version:** 1.1  
**Related Documents:** [`PRODUCT_SPEC.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/PRODUCT_SPEC.md), [`ARCHITECTURE.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/ARCHITECTURE.md), [`FEATURE_CATALOG.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/FEATURE_CATALOG.md), [`DECISION_RULES.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/DECISION_RULES.md)

---

## Overview

As mandated by [`PRODUCT_SPEC.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/PRODUCT_SPEC.md) Section 24 and 26, the **Mutual Fund Decision Engine** prioritizes free, authoritative sources for all material factual claims.

Publicly accessible data feeds are **not** assumed to be free or legally usable without verification. Unvalidated third-party sources are strictly isolated and never dictate system architecture.

Source authority is **FIELD-SPECIFIC**. No single universal hierarchy (e.g., AMFI > SEBI > AMC > Exchange) applies across all data fields; rather, the authoritative source depends on the specific domain (e.g., AMFI for daily NAVs, SEBI for regulatory categorization rules, AMFI/AMC for TER, CBDT for taxation, NSE/BSE for index data).

---

## Source Hierarchy & Data Source Matrix

### 1. Primary Authoritative Sources

#### 1.1 AMFI — Association of Mutual Funds in India
* **Information Sourced:** Official Daily NAV text feeds, scheme master registry, AMFI scheme codes, ISINs (Growth & Reinvestment), AMC directory, NAV History, TER disclosures.
* **Authority Level:** **Level 1 (Primary Industry Body)**.
* **Why Appropriate:** Official industry association established under SEBI guidelines; official repository for daily NAV and TER disclosures in India.
* **Official URL:** [`https://www.amfiindia.com`](https://www.amfiindia.com)
* **Specific Data URLs:** 
  - Daily NAV Feed: `https://www.amfiindia.com/spages/NAVAll.txt`
  - NAV Download Portal: `https://www.amfiindia.com/net-asset-value/nav-download`
  - NAV History Portal: `https://www.amfiindia.com/net-asset-value/nav-history` (supports historical date-range retrieval up to a maximum 90-day period per request)
  - TER Disclosure Portal: `https://www.amfiindia.com/ter-of-mf-schemes` (dedicated facility filtered by Financial Year, Month, Fund Type, Category, and Mutual Fund)
* **Update Frequency:** Daily (end-of-day NAV publishing and daily TER disclosures).
* **Historical Availability:** **`PARTIALLY VALIDATED (SELECTED HISTORICAL DATES TESTED)`**. Phase B Controlled Prototype successfully tested historical retrieval at selected dates spanning 2010–2025 (2,700 to 9,400 schemes per tested day). Earliest successfully tested date: `2010-01-15`. Latest successfully tested date: `2025-01-15`. Tested pre-2010 window (`2006-01-15`) returned `{"message": "No records to display"}`. Continuous historical coverage across all intermediate trading days remains unverified.
* **Free / Accessibility Status:** Free public access on official website.

* **Licensing / Usage Terms:** Public industry data for non-commercial/investor support decision platforms.
* **Validation Status:** **`VALIDATED`** (Current daily NAV feed); **`HISTORICAL DEPTH TO BE VERIFIED`** (Multi-year historical archives).
* **Source vs Calculated:**
  - *Sourced from AMFI:* Raw Net Asset Value (NAV), NAV date, Scheme Code, Scheme Name, ISIN, Scheme TER.
  - *Calculated by Platform:* CAGR, rolling returns, downside risk metrics, fund quality scores.

#### 1.2 SEBI — Securities and Exchange Board of India
* **Information Sourced:** Scheme categorization circulars, asset allocation mandates, mutual fund regulations, regulatory filings.
* **Authority Level:** **Level 2 (Statutory Regulator)**.
* **Why Appropriate:** Statutory regulatory authority governing Indian capital markets and mutual fund classifications.
* **Official URL:** [`https://www.sebi.gov.in`](https://www.sebi.gov.in)
* **Key Regulatory References:**
  - *SEBI Categorization Circular (October 6, 2017):* Circular SEBI/HO/IMD/DF3/CIR/P/2017/114 ("Categorization and Rationalization of Mutual Fund Schemes").
  - *SEBI Superseding Categorization Circular (February 26, 2026):* Circular updating and superseding the 2017 categorization framework.
* **Update Frequency:** Periodic (as regulatory circulars and amendments are gazetted).
* **Free / Accessibility Status:** Free public access.
* **Validation Status:** **`VALIDATED`** (Current categorization rules); **`DATA SOURCE TO BE VALIDATED`** (Point-in-time classification timeline across multiple regulatory regimes).
* **Historical Classification Architecture Requirement:**
  Point-in-time scheme category classification must support **MULTIPLE REGULATORY REGIMES** (e.g., 2017 SEBI framework, 2026 superseding framework). Point-in-time classification records must explicitly capture:
  - `regulatory_regime` (e.g., `SEBI_2017_FRAMEWORK`, `SEBI_2026_FRAMEWORK`)
  - `effective_date`
  - `category`
  - `sub_category`
  - `source_provenance`
  Exact transition implementation dates for individual schemes must be verified from disclosures rather than assumed.
* **Source vs Calculated:**
  - *Sourced from SEBI:* Regulatory category definitions (e.g., Large Cap minimum 80% equity rule), sub-category mandates, risk-o-meter guidelines.
  - *Calculated by Platform:* Fund compliance verification, category peer-group boundaries.

#### 1.3 RBI — Reserve Bank of India
* **Information Sourced:** Benchmark repo rates, monetary policy interest rates, government bond yields, macroeconomic indicators.
* **Authority Level:** **Level 3 (Central Bank)**.
* **Why Appropriate:** Central bank of India; official source for risk-free rates and debt market context.
* **Official URL:** [`https://www.rbi.org.in`](https://www.rbi.org.in)
* **Update Frequency:** Periodic (Bi-monthly monetary policy & daily treasury updates).
* **Free / Accessibility Status:** Free public access.
* **Validation Status:** **`VALIDATED`**.
* **Source vs Calculated:**
  - *Sourced from RBI:* Repo rate, 10-year G-Sec yield, inflation target ranges.
  - *Calculated by Platform:* Debt fund yield-spread context, goal discount rate assumptions.

#### 1.4 CBDT / Income Tax Department (Government of India)
* **Information Sourced:** Income Tax Act regulations, Short-Term Capital Gains (STCG) rates, Long-Term Capital Gains (LTCG) rates, holding period boundaries, indexation rules.
* **Authority Level:** **Level 4 (Tax Authority)**.
* **Why Appropriate:** Official government tax authority; sole authority for Indian personal taxation rules.
* **Official URL:** [`https://incometaxindia.gov.in`](https://incometaxindia.gov.in)
* **Update Frequency:** Annual (Finance Act enactments) and periodic circulars.
* **Free / Accessibility Status:** Free official public access.
* **Validation Status:** **`VALIDATED`**.
* **Source vs Calculated:**
  - *Sourced from CBDT:* Statutory tax rates, holding period thresholds (e.g., 12 months for equity, 36 months for legacy debt).
  - *Calculated by Platform:* Investor tax-lot liability, net after-tax switch benefit.

#### 1.5 AMFI TER Portal & AMC Statutory Disclosures (TER & Portfolio Sourced Data)
* **Information Sourced:** Total Expense Ratio (TER), monthly portfolio disclosures, full security holdings, sector exposure percentages, fund manager history, exit load schedules.
* **Authority Level:** **Level 5 (Industry TER Portal & Issuing AMCs)**.
* **Why Appropriate:** AMFI operates a centralized statutory disclosure portal for TER; AMCs are legal issuers of mutual fund schemes.
* **TER Sourcing Hierarchy:**
  - **PRIMARY CANDIDATE:** AMFI TER Disclosure Portal ([`https://www.amfiindia.com/ter-of-mf-schemes`](https://www.amfiindia.com/ter-of-mf-schemes)), which provides a dedicated facility with filters (Financial Year, Month, Fund Type, Category, Mutual Fund) and daily scheme TER disclosures.
  - **SECONDARY / CROSS-CHECK:** AMC statutory disclosures published on individual AMC websites.
* **Update Frequency:** Daily (AMFI TER disclosure portal) and Monthly (AMC portfolio holdings).
* **Free / Accessibility Status:** Free statutory disclosures.
* **Validation Status:** **`DATA SOURCE TO BE VALIDATED`** (Historical TER coverage and multi-year depth remain to be verified).
* **Source vs Calculated:**
  - *Sourced from AMFI/AMC:* Scheme TER percentages (Direct vs Regular), effective dates, monthly stock/bond holding lists, exit load terms.
  - *Calculated by Platform:* Portfolio stock overlap, sector concentration, cost drag impact.

#### 1.6 Official Stock Exchanges & Index Providers (NSE Indices / BSE)
* **Information Sourced:** Benchmark index values, historical Total Return Index (TRI) daily series (e.g., Nifty 50 TRI, Nifty Midcap 150 TRI, BSE Sensex TRI).
* **Authority Level:** **Level 6 (Official Stock Exchanges & Index Providers)**.
* **Why Appropriate:** Official index providers publishing official benchmark index data.
* **Official Data Offering:** NSE Indices Data Subscription (`https://www.niftyindices.com/`).
* **Methodology Classification:** **SECOND-STAGE / OPTIONAL FOR CORE FUND QUALITY VALIDATION**. Benchmark data is NOT a prerequisite for core NAV-based empirical scoring validation (point-to-point returns, rolling returns, volatility, Max Drawdown).
* **Licensing / Terms Status:** **`LICENSE / TERMS TO BE VALIDATED`** (Commercial API redistribution terms require audit before production integration).
* **Validation Status:** **`DATA SOURCE TO BE VALIDATED`**.
* **Source vs Calculated:**
  - *Sourced from Exchanges:* Raw benchmark index TRI time-series.
  - *Calculated by Platform:* Category relative alpha, benchmark tracking error.

---

### 2. Unvalidated / Prototype Sources

#### 2.1 MFAPI (`api.mfapi.in`)
* **Information Sourced:** Historical NAV JSON feed for scheme code lookup.
* **Authority Level:** **Level 7 (Unvalidated Third-Party Source)**.
* **Classification:** **Secondary / Prototype Source Only**.
* **Status:** Used strictly during early prototyping and testing.
* **Governance Rule:** Must **NOT** dictate production system architecture or replace official AMFI daily NAV feeds.

---

## 12. Field-by-Field Source Validation Matrix

The following matrix evaluates candidate sources across all 17 required historical data fields:

| Field Name | Candidate Source | Source Classification | Documented Status | Depth Available | Update Freq | Machine Readable | Free / Public? | Licensing / Terms Status | Provenance Req | Limitations | Validation Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A. Daily NAV** | AMFI Official (`amfiindia.com`) | Primary Authoritative | Documented | **HISTORICAL DEPTH TO BE VERIFIED** (Max 90-day range/req) | Daily | Yes (TXT/CSV) | Yes (Free Public) | Public Industry Disclosures | Raw Line, Timestamp, AMFI Code | End-of-day publication delay; 90-day req cap | **`VALIDATED`** (Daily Feed); **`DEPTH TO BE VERIFIED`** |
| **B. AMFI Scheme Code** | AMFI Scheme Master | Primary Authoritative | Documented | Multi-Year | Daily/Monthly | Yes | Yes (Free Public) | Public Industry Data | AMFI Code | Re-used historical codes edge case | **`VALIDATED`** |
| **C. Scheme Name** | AMFI Scheme Master | Primary Authoritative | Documented | Current/Historical | Daily | Yes | Yes (Free Public) | Public Industry Data | Raw Scheme Name | Minor naming string variations | **`VALIDATED`** |
| **D. AMC** | AMFI / AMC Disclosures | Primary Authoritative | Documented | Full History | Periodic | Yes | Yes (Free Public) | Public Industry Data | AMC Name | AMC M&A name changes | **`VALIDATED`** |
| **E. ISIN** | AMFI Scheme Master | Primary Authoritative | Documented | Current | Daily/Monthly | Yes | Yes (Free Public) | Public Industry Data | ISIN Growth / Reinvest | ISIN assignment gaps on legacy funds | **`VALIDATED`** |
| **F. Direct / Regular** | AMFI Master / Text Parser | Primary Authoritative | Documented | Current | Daily | Yes | Yes (Free Public) | Public Industry Data | Parsed Plan Type | Text token ambiguity quarantined | **`VALIDATED`** |
| **G. Growth / IDCW** | AMFI Master / Text Parser | Primary Authoritative | Documented | Current | Daily | Yes | Yes (Free Public) | Public Industry Data | Parsed Option Type | Historical option naming changes | **`VALIDATED`** |
| **H. Category** | SEBI Circulars (2017 & 2026) / AMFI | Primary Authoritative | Documented | Multiple Regulatory Regimes | Periodic | Yes | Yes (Free Public) | Public Regulatory Data | Regime, Effective Date, Category | Point-in-time regime shifts; transition dates to verify | **`PARTIALLY VALIDATED`** (Current); **`DATA SOURCE TO BE VALIDATED`** (History) |
| **I. Sub-Category** | SEBI Circulars (2017 & 2026) / AMFI | Primary Authoritative | Documented | Multiple Regulatory Regimes | Periodic | Yes | Yes (Free Public) | Public Regulatory Data | Regime, Effective Date, Sub-Cat | Point-in-time regime shifts; transition dates to verify | **`PARTIALLY VALIDATED`** (Current); **`DATA SOURCE TO BE VALIDATED`** (History) |
| **J. Lifecycle Status** | AMFI / AMC Disclosures | Primary Authoritative | Not Documented | Historical | Event-driven | Partial | Yes (Free Public) | Public Statutory Data | Event Date, Active Status | No unified AMFI lifecycle feed | **`DATA SOURCE TO BE VALIDATED`** |
| **K. Merger Events** | SEBI Gazette / AMC Notices | Primary Authoritative | Not Documented | Event History | Event-driven | PDF / Text | Yes (Free Public) | Public Statutory Data | Merger Date, Target Scheme ID | PDF parsing required | **`DATA SOURCE TO BE VALIDATED`** |
| **L. Closure Events** | AMFI / AMC Winding-Up | Primary Authoritative | Not Documented | Event History | Event-driven | PDF / Text | Yes (Free Public) | Public Statutory Data | Closure Date, Reason | Manual verification required | **`DATA SOURCE TO BE VALIDATED`** |
| **M. Rename Events** | AMC Change Notices | Primary Authoritative | Not Documented | Event History | Event-driven | PDF / Text | Yes (Free Public) | Public Statutory Data | Rename Date, Old/New Name | AMC press release archives | **`DATA SOURCE TO BE VALIDATED`** |
| **N. Plan/Option Changes**| AMC Notices / Scheme Addenda| Primary Authoritative | Not Documented | Event History | Event-driven | PDF / Text | Yes (Free Public) | Public Statutory Data | Conversion Date, Ratio | Infrequent operational events | **`DATA SOURCE TO BE VALIDATED`** |
| **O. Historical TER** | AMFI TER Portal [Primary] / AMC [Secondary] | Primary Authoritative | Documented (`amfiindia.com/ter-of-mf-schemes`) | **HISTORICAL DEPTH TO BE VERIFIED** | Daily / Monthly | Partial (HTML/PDF) | Yes (Free Public) | Public Statutory Data | Effective Date, Scheme ID, TER | Multi-year archival depth to be verified | **`DATA SOURCE TO BE VALIDATED`** |
| **P. Benchmark Identity**| SEBI Primary Benchmarks / SID | Primary Authoritative | Not Documented | Current/Historical| Periodic | Text | Yes (Free Public) | Public Regulatory Data | Primary Benchmark Name | Benchmark mandate changes | **`DATA SOURCE TO BE VALIDATED`** (Second-Stage / Optional) |
| **Q. Historical TRI** | NSE Indices (`niftyindices.com`) / BSE | Primary Authoritative | Documented | Multi-Year Daily | Daily | API / CSV | Public / Restricted | **LICENSE / TERMS TO BE VALIDATED** | Index Provider, TRI Value | Commercial API terms require audit | **`DATA SOURCE TO BE VALIDATED`** (Second-Stage / Optional) |

---

## 13. Authoritative vs Third-Party Source Classification

Candidate sources are classified into five strict governance tiers:

1. **Primary Authoritative (Level 1–6)**: Official statutory bodies, regulators, official exchanges, and primary disclosure platforms (AMFI, SEBI, RBI, CBDT, AMCs, NSE/BSE). Used for production data and decision logic.
2. **Official Secondary**: Consolidated regulatory publications or official AMC association feeds.
3. **Validated Third-Party**: Commercial data vendors subjected to formal validation gates, cross-checks against primary sources, and licensing reviews.
4. **Unvalidated Third-Party (Level 7)**: Aggregators such as `mfapi.in`. Allowed **ONLY** as a temporary development/backtesting convenience; **STRICTLY PROHIBITED** from dictating production architecture or overwriting primary data.
5. **Not Suitable**: Scraped unverified personal blogs, social media feeds, or uncredentialed third-party forums.

---

## 14. Licensing & Production Use Assessment

For every data source, legal and operational usage permissions must be explicitly distinguished:

- **Publicly Viewable**: Web browser rendering permitted (does not imply automated scraping rights).
- **Downloadable**: Manual file download permitted.
- **Machine-Readable**: Formatted CSV, TXT, JSON, or API endpoints available.
- **Free for Research**: Non-commercial backtesting permitted.
- **Free for Production**: Unrestricted use in commercial investor-support applications.
- **Redistribution Restrictions**: Terms prohibiting raw data resale or external API forwarding.

> [!CAUTION]
> Never equate "free to view on website" with "free for unrestricted production use". Sources where commercial redistribution rights are unconfirmed are marked **`LICENSE / TERMS TO BE VALIDATED`**.

---

## 15. Source Integrity & Validation Checks

Before any raw observation dataset is promoted to validated status, it must pass 10 automated integrity checks:
1. **Identity Correctness**: Valid AMFI code or ISIN join against Canonical Scheme Master.
2. **Field Correctness**: NAV is positive float ($NAV > 0.0$), non-numeric values rejected.
3. **Date Correctness**: ISO 8601 date parseable, $NAV\_Date \le \text{Current Date}$.
4. **Historical Completeness**: Sequence continuity checks for missing daily gap dates.
5. **Duplicate Handling**: `INSERT OR IGNORE` on `(canonical_scheme_id, nav_date, source_id)` preventing silent overwrites.
6. **Revision Handling**: Re-published historic NAV revisions logged with retrieval timestamps.
7. **Source Timestamp**: Original publication date preserved.
8. **Retrieval Timestamp**: Execution UTC timestamp recorded.
9. **Reproducibility**: Deterministic raw-to-normalized execution trace.
10. **Cross-Source Verification**: Spot checks comparing AMFI text feeds against official AMC disclosures.

---

## 16. Source Registry Architecture Audit & Assessment

An audit of `SourceRegistry` (`data/ingestion/source_registry.py`) and `source_registry` SQLite table:

```
Existing Capabilities:
  [x] source_id, source_name, source_type, authority_level
  [x] official_url, specific_data_url, supported_data_fields
  [x] update_frequency, historical_availability
  [x] free_status, licensing_status, validation_status
  [x] last_successful_retrieval, last_validation_date

Required Historical Data Foundation Extensions (Conceptual):
  [ ] Domain-specific field authority mappings (NAV vs TER vs Category vs Tax)
  [ ] Historical depth versioning (start_date, end_date of available archives)
  [ ] License redistribution classification (Research vs Production)
```

The existing `source_registry` schema is structurally adequate for Slice 1/2 and can represent source metadata without requiring immediate schema refactoring.

---

## 17. Data Acquisition Decision Gate

Before any candidate source is ingested into the production backtesting dataset, it must pass a 9-stage approval gate:

$$\text{Discovered} \rightarrow \text{Documented} \rightarrow \text{Authority} \rightarrow \text{Field Coverage} \rightarrow \text{Historical Depth} \rightarrow \text{Licensing} \rightarrow \text{Sample Validated} \rightarrow \text{Cross-Checked} \rightarrow \text{APPROVED}$$

If a source fails any gate, it is assigned `DataQualityState.QUARANTINED` or `DATA SOURCE TO BE VALIDATED` and excluded from the production-quality backtesting dataset.

---

## 18. Current Source Status Summary Matrix

Domain readiness summary across all historical data requirements:

| Data Domain | Current Source Status | Recommended Action |
| :--- | :--- | :--- |
| **Daily NAV Observations (Current)** | **`READY / VALIDATED`** | Official AMFI daily feed (`NAVAll.txt`) validated for current end-of-day NAV ingestion. |
| **Historical NAV Archives** | **`PIPELINE OPERATIONAL`** (Phase B.2 Implemented, Dataset Not Fully Populated) | Phase B.2 Historical NAV Acquisition Pipeline designed & validated. Features resumability, coverage ledger (`acquisition_coverage_ledger`), gap detection, rate-consciousness, and strict data reconciliation ($Raw = Normalized + NAV\_Q + Map\_Q$). Live 2-day smoke test validated (15,940 raw records processed, zero errors). System status: **HISTORICAL NAV ACQUISITION PIPELINE — NOT YET FULLY POPULATED.** |
| **Scheme Master & Identifiers** | **`READY / VALIDATED`** | AMFI Scheme Master & ISIN mapping validated in Slice 1. |
| **Current SEBI Category** | **`READY / VALIDATED`** | Static current SEBI category rules validated in Slice 1. |
| **Historical Scheme Lifecycle** | **`DATA SOURCE TO BE VALIDATED`** | Historical mergers/closures require AMC/AMFI statutory disclosure validation. |
| **Point-in-Time Category History** | **`DATA SOURCE TO BE VALIDATED`** | Reclassification across multiple regulatory regimes (SEBI 2017 & 2026 circulars) requires validation. |
| **Historical TER / Cost Data** | **`DATA SOURCE TO BE VALIDATED`** | Primary candidate is AMFI TER Portal (`amfiindia.com/ter-of-mf-schemes`); secondary is AMC disclosures. Multi-year depth to be tested. |
| **Benchmark TRI Series** | **`DATA SOURCE TO BE VALIDATED`** / **`LICENSE / TERMS TO BE VALIDATED`** | Second-stage / optional for core NAV scoring. NSE Indices data offerings require licensing audit. |


