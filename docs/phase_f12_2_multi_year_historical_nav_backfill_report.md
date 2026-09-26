# Phase F.12.2 Multi-Year Hybrid Historical NAV Backfill Execution & Decision Dataset Creation Report

## Executive Summary

Phase F.12.2 has executed the authorized 10-year hybrid historical NAV backfill into the dedicated isolated database [`db/backfill_f12_2.db`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/db/backfill_f12_2.db) using the official AMFI NAV History API (`AMFI_OFFICIAL`). 

The backfill strictly adheres to the approved hybrid sampling policy established in F.12.1 / F.12.1.2:
- **Recent 3 Years Daily Window**: 2021-02-01 to 2024-01-31 (1,096 daily acquisition windows)
- **Older 7 Years Monthly Window**: 2014-02-01 to 2021-01-31 (84 month-end acquisition windows)
- **Total Acquisition Scope**: 1,180 acquisition windows (all returning HTTP 200 / `SUCCESS`)

Every acquired window was verified against the strict Data Quality Reconciliation Equation:
$$Raw = Normalized + NAV\_Quarantine + Mapping\_Quarantine$$
yielding **100.0% raw-observation disposition reconciliation** ($6,187,660 = 4,766,297 + 94,541 + 1,326,822$) across all windows.

---

## 1. Scope & Date Ranges

| Scope Parameter | Value / Boundary |
|---|---|
| **Authorizing Gate** | Phase F.12.1.2 Final Evidence Reconciliation Gate |
| **Dataset Version** | `f12_2_v1.0.0` |
| **Historical Horizon** | ~10 Years (2014-02-28 to 2024-01-31) |
| **Monthly Scope (7Y Tail)** | 2014-02-01 through 2021-01-31 (84 windows) |
| **Daily Scope (3Y Window)** | 2021-02-01 through 2024-01-31 (1,096 windows) |
| **Total Requested Windows** | 1,180 acquisition windows |
| **Sampling Policy** | Deterministic month-end date selection for 7Y tail + Actual daily trading dates for 3Y window |

---

## 2. Source Authority & Endpoint

| Attribute | Specification |
|---|---|
| **Source Identifier** | `AMFI_OFFICIAL` |
| **Source Authority Level** | `OFFICIAL_REGULATOR` (Level 1) |
| **Official Endpoint URL** | `https://www.amfiindia.com/api/nav-history?query_type=all_for_date&from_date=YYYY-MM-DD` |
| **Synthetic Data Usage** | ZERO (0) — 100% authoritative AMFI HTTP payloads |
| **Fallback Sources** | None allowed or invoked |

---

## 3. Dataset Versioning & Execution Metadata

- **Dataset Version**: `f12_2_v1.0.0`
- **Target Database**: [`db/backfill_f12_2.db`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/db/backfill_f12_2.db)
- **Ingestion Pipeline Version**: `2.0.0`
- **Normalization Version**: `1.0.0`
- **Lifecycle Engine Version**: `1.0.0`
- **Metadata Persistence**: Persistent coverage ledger (`acquisition_coverage_ledger`) & version descriptor [`docs/dataset_version_f12_2.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/dataset_version_f12_2.json).

---

## 4. Empirical Acquisition & Reconciliation Summary

> [!IMPORTANT]
> **100% Raw-Observation Disposition Reconciliation Verified**:
> $$Raw = Normalized + NAV\_Quarantine + Mapping\_Quarantine$$
> $$6,187,660 = 4,766,297 + 94,541 + 1,326,822$$

| Metric / Category | Empirical Count / Percentage |
|---|---|
| **Total Acquisition Windows** | 1,180 |
| **Successful Acquisition Windows** | 1,180 (100.0%) |
| **Failed / Retry Required Windows** | 0 (0.0%) |
| **Total Raw Observations Ingested** | 6,187,660 |
| **Total Normalized NAV Records** | 4,766,297 (77.03%) |
| **Total NAV Quality Quarantine Records** | 94,541 (1.53%) |
| **Total Mapping Quarantine Records** | 1,326,822 (21.44%) |
| **Raw Disposition Reconciliation Ratio** | **100.0% Exact Match** |
| **Unique Canonical Schemes Resolved** | 16,808 |

---

## 5. Mapping & NAV Quarantine Governance & Reason Taxonomy

In strict compliance with F.12.1.2 conservative governance:
1. **Zero Fuzzy Matching**: No scheme names were merged or mapped based on text similarity thresholding.
2. **Zero Synthetic Inference**: Plan types (Direct vs Regular) and Option types (Growth vs IDCW) were never guessed where text evidence was missing.
3. **Quarantine Taxonomy Breakdown**:

| Quarantine Category | Specific Reason | Count | Percentage |
|---|---|---|---|
| **Mapping Quarantine** | `AMBIGUOUS_SCHEME_NAME` (Plan/option type missing explicit demarcation) | 1,326,822 | 93.35% of quarantine |
| **NAV Quality Quarantine** | Non-positive NAV value: `0.0000` | 56,741 | 3.99% of quarantine |
| **NAV Quality Quarantine** | Non-positive NAV value: `0` | 36,227 | 2.55% of quarantine |
| **NAV Quality Quarantine** | Unparseable NAV value: `'N.A.'` | 1,573 | 0.11% of quarantine |
| **Total Quarantine** | All isolated observations | **1,421,363** | **100.0%** |

---

## 6. NAV Level Quality & Numeric Validation

Every normalized record satisfies:
1. Valid numeric `nav_value > 0`.
2. Valid calendar date `nav_date` matching requested acquisition date.
3. Valid `canonical_scheme_id` linked via canonical scheme master (`CAN_AMFI_{amfi_code}`).
4. Uniqueness constraint on `(canonical_scheme_id, nav_date)`. Zero duplicate logical observations.

---

## 7. Scheme Longitudinal Depth & Coverage Distribution

Distribution of canonical schemes by usable observation count across the 10-year backfill dataset:

- **Schemes with $\ge 1$ observation**: 16,808 schemes (100.0%)
- **Schemes with $\ge 20$ observations**: 14,050 schemes (83.59%)
- **Schemes with $\ge 22$ observations**: 13,779 schemes (81.98%)
- **Schemes with $\ge 250$ observations (~1Y Daily)**: 6,558 schemes (39.02%)
- **Schemes with $\ge 750$ observations (~3Y Daily)**: 3,453 schemes (20.54%)
- **Schemes with $\ge 800$ observations (Multi-Year Hybrid)**: 605 schemes (3.60%)

---

## 8. Financial Metric Computability Assessment

Using the exact unchanged metric engine (`src/metrics/fund_metrics.py`), the computability of historical fund quality metrics on the backfilled dataset is:

| Financial Metric | Minimum History Required | Eligible Schemes Count | Insufficiency Reason |
|---|---|---|---|
| **Absolute Return** | $\ge 2$ observations | 16,406 | History $< 2$ dates |
| **CAGR 1Y** | $\ge 365$ days span & $\ge 2$ obs | 14,016 | History span $< 1\text{Y}$ |
| **CAGR 3Y** | $\ge 1,095$ days span & $\ge 2$ obs | 7,978 | History span $< 3\text{Y}$ |
| **CAGR 5Y** | $\ge 1,825$ days span & $\ge 2$ obs | 3,663 | History span $< 5\text{Y}$ |
| **CAGR 10Y** | $\ge 3,650$ days span & $\ge 2$ obs | 0 | Max span acquired is 3,624d ($< 10\text{Y}$) |
| **Annualized Volatility** | $\ge 20$ observations | 14,050 | Observations $< 20$ |
| **Downside Deviation** | $\ge 20$ observations | 14,050 | Observations $< 20$ |
| **Maximum Drawdown** | $\ge 20$ observations | 14,050 | Observations $< 20$ |

> [!NOTE]
> Insufficient history is explicitly preserved as `None` or flagged as insufficient. Financial formulas were **not** altered, tuned, or relaxed to manufacture metric counts.

---

## 9. Hybrid Daily vs Monthly Sampling Conformance

- **Daily Scope (Years 1–3)**: Preserved actual trading date NAVs including weekends/holidays as published by AMFI.
- **Monthly Scope (Years 4–10)**: Preserved actual month-end NAV observations published by AMFI without synthesizing artificial intermediate dates.
- **Governance Statement**: *"Hybrid ingestion is supported for the current metric architecture with explicit scope boundaries."*

---

## 10. Point-in-Time & Survivorship Safeguards

1. **Survivorship Bias Control**: Historical observations from closed, merged, or renamed schemes are retained immutably in `raw_nav_observations` and `normalized_nav_records`.
2. **Lifecycle Safety**: Zero automatic NAV stitching across scheme mergers or reorganizations.
3. **No Metadata Fabrication**:
   - `TER`: Preserved as `None` (not backfilled from current TER).
   - `Riskometer`: Preserved as `None` (not inferred from current Riskometer).
   - `Benchmark`: Preserved as `None` (not backfilled from current benchmark).
   - `Category`: Preserved as `None` where historical AMFI classification is absent.

---

## 11. Verification & Test Suite Results

Dedicated test suite [`tests/data_quality/test_phase_f12_2_backfill.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f12_2_backfill.py) covers:
1. Date range bounds & hybrid sampling policy.
2. 100% raw-observation disposition reconciliation.
3. NAV numeric validation ($NAV > 0$).
4. Logical duplicate prevention.
5. Ledger integrity & HTTP 200 verification.
6. Provenance retention (`source_id`, `retrieval_timestamp`, `raw_scheme_code`, `raw_date`).
7. Dataset versioning metadata.
8. Survivorship scheme preservation.
9. Metric computability eligibility calculation.
10. Zero synthetic/mock data contamination.

---

## 12. F.11.3 Investment-Outcome Validation Readiness Assessment

| Evaluation Dimension | Readiness Status | Evidence / Notes |
|---|---|---|
| **A. Real Historical NAV Depth** | **READY** | ~10 years longitudinal coverage (2014–2024), 4,766,297 normalized records |
| **B. Risk & Volatility Metric Sufficiency** | **READY** | 14,050 schemes with $\ge 20$ observations |
| **C. Rolling 1Y / 3Y Return Sufficiency** | **READY** | 14,016 schemes for 1Y, 7,978 schemes for 3Y |
| **D. Point-in-Time Safeguards** | **READY** | Zero look-ahead bias in NAV observations |
| **E. Historical Metadata Availability (TER / Riskometer / Benchmark)** | **NOT READY / LIMITED** | Regulatory historical metadata unavailable from AMFI |
| **F. After-Tax & After-Cost Outcome Validation** | **LIMITED** | Requires historical TER and tax exit-load schedules |

---

## 13. Financial Methodology Lock

No financial decision rules, scoring weights, suitability thresholds, or action semantics were modified during Phase F.12.2.

$$\text{DATA} \rightarrow \text{METRIC ENGINE} \rightarrow \text{FUND QUALITY} \rightarrow \text{SUITABILITY} \rightarrow \text{PORTFOLIO NEED} \rightarrow \text{ECONOMIC BENEFIT} \rightarrow \text{ACTION}$$

---

## 14. Governance Recommendation & Declared Status

### Declared Final Status

```
PHASE F.12.2 PASSED — COMPLETE HISTORICAL NAV BACKFILL CREATED
```

### Next Phase Recommendation

Proceed to **Phase F.11.3 (Investment-Outcome Validation)** with explicit limitations: fund metrics and rolling returns can be evaluated against longitudinal historical NAVs, but after-cost / after-tax outcome validation remains conditionally scoped due to the absence of regulatory historical TER and Riskometer metadata.
