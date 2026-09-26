# Phase F.10.2 — Authoritative TER, Riskometer & Benchmark Source Discovery and Validation Report

**Project:** `mutual-fund-decision-engine`  
**Execution Date:** 2026-09-14 UTC  
**Phase:** F.10.2 (Authoritative TER, Riskometer & Benchmark Source Discovery and Validation)  
**Status:** **PHASE F.10.2 AUTHORITATIVE METADATA SOURCE DISCOVERY & VALIDATION PASSED**  

---

## 1. Executive Summary & Discovery Findings

Phase F.10.2 performed a comprehensive metadata source discovery and validation investigation to resolve the data-source failures identified in Phase F.10.1.

### Key Investigation Results
1. **AMFI Daily NAV Feed (`AMFI_NAV_LIVE`)**:
   - URL: `https://www.amfiindia.com/spages/NAVAll.txt`
   - Status: **VALIDATED & LIVE OPERATIONAL** (HTTP 200 OK, 1.5MB payload, 14,361 live records).
   - Provides scheme code, ISIN, scheme name, NAV, date, category headers, plan type, option type.

2. **TER (Total Expense Ratio) Bulk Feed**:
   - URL: `https://www.amfiindia.com/modules/TERData` (and related endpoints)
   - Status: **UNAVAILABLE_HTTP_404**.
   - Discovery Finding: SEBI mandates AMC daily TER disclosures on AMC websites and monthly filings with AMFI. AMFI does not provide an unauthenticated public bulk CSV/JSON download API.
   - Classification: Marked `UNAVAILABLE_HTTP_404` in [`config/sources/sources.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/sources/sources.json).

3. **Riskometer Bulk Feed**:
   - URL: `https://www.amfiindia.com/modules/RiskometerData`
   - Status: **UNAVAILABLE_HTTP_404**.
   - Discovery Finding: SEBI mandates monthly Riskometer disclosures by AMCs on AMC websites and AMFI portal. AMFI displays Riskometer visually on fund detail web pages, but direct bulk CSV/JSON feeds are not available.
   - Classification: Marked `UNAVAILABLE_HTTP_404` in [`config/sources/sources.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/sources/sources.json).

4. **Benchmark Bulk Feed**:
   - URL: `https://www.amfiindia.com/modules/BenchmarkData`
   - Status: **UNAVAILABLE_HTTP_404**.
   - Discovery Finding: SEBI mandates benchmark disclosures in Scheme Information Documents (SID/KIM) and monthly portfolio disclosures. Direct public bulk CSV/JSON download endpoints are not available on AMFI's public server.
   - Classification: Marked `UNAVAILABLE_HTTP_404` in [`config/sources/sources.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/sources/sources.json).

5. **Scheme Master CSV**:
   - URL: `https://www.amfiindia.com/spages/SchemeMaster.csv`
   - Status: **UNAVAILABLE_HTTP_404**.
   - Classification: Marked `UNAVAILABLE_HTTP_404` in [`config/sources/sources.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/sources/sources.json).

---

## 2. Test Baseline & Execution Verification

- **Pre-Implementation Baseline Test Count**: `608 passed, 76 warnings in 9.25s`
- **Post-Implementation Test Suite Count**: `614 passed, 76 warnings in 14.79s`
- **Net Focused Discovery Tests Added**: 6 tests in [`tests/data_quality/test_phase_f10_2_source_discovery.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f10_2_source_discovery.py).

---

## 3. Third-Party Vendor Evaluation & Validation

Probed secondary APIs (e.g. `api.mfapi.in`):
- **HTTP Status**: 200 OK (5.7MB dataset).
- **Supported Fields**: Scheme Code, Scheme Name, Date, NAV.
- **Evaluation**: Does NOT supply TER percentage, Riskometer labels, or Benchmark index names.
- **Governance Classification**: Retained as `UNVALIDATED_THIRD_PARTY` / `PROVISIONAL`. Cannot be substituted into production as an authoritative metadata source.

---

## 4. Production Dataset Population & Missing-Data Governance

Per strict data-governance principles:
- In live production dataset snapshots generated from official live HTTP feeds (`NAVAll.txt`), persisted values for TER, Riskometer, and Benchmark remain **0 / 14,361 = 0.0% populated** (`MODELLED_BUT_NOT_POPULATED` / `UNPOPULATED_LIVE`).
- **No Synthetic Data Generation**: Zero synthetic default values (e.g., no TER 0.75/1.75 defaults, no MEDIUM Riskometer defaults, no category benchmark substitution).
- **Explicit Missing Values**: Missing metadata fields remain explicitly `None` (`Missing != 0`).

---

## 5. Verified 10 Genuine Real AMFI Schemes from Live `NAVAll.txt`

| AMFI Code | Genuine Scheme Name from Live `NAVAll.txt` | Category Header | NAV | Date | Plan | Option |
|---|---|---|---|---|---|---|
| `135762` | Axis Children's Fund - Direct Plan - Growth Option | Children's Fund | 29.9628 | 11-Sep-2026 | Direct Plan | Growth Option |
| `135765` | Axis Children's Fund - Direct Plan - IDCW Option | Children's Fund | 27.6011 | 11-Sep-2026 | Direct Plan | IDCW Option |
| `135759` | Axis Children's Fund - Regular Plan - Growth Option | Children's Fund | 26.0960 | 11-Sep-2026 | Regular Plan | Growth Option |
| `135760` | Axis Children's Fund - Regular Plan - IDCW Option | Children's Fund | 24.0757 | 11-Sep-2026 | Regular Plan | IDCW Option |
| `119551` | Aditya Birla Sun Life Banking & PSU Debt Fund - Direct - IDCW | Debt / Banking & PSU | 107.0790 | 11-Sep-2026 | Direct Plan | IDCW Option |
| `119552` | Aditya Birla Sun Life Banking & PSU Debt Fund - Direct - Monthly | Debt / Banking & PSU | 116.9690 | 11-Sep-2026 | Direct Plan | IDCW Option |
| `100033` | Aditya Birla Sun Life Large & Mid Cap Fund - Regular - Growth | Equity / Large & Mid | 947.8800 | 11-Sep-2026 | Regular Plan | Growth Option |
| `100034` | Aditya Birla Sun Life Large & Mid Cap Fund - Regular - IDCW | Equity / Large & Mid | 138.0500 | 11-Sep-2026 | Regular Plan | IDCW Option |
| `100038` | Aditya Birla Sun Life Medium to Long Term Fund - Regular | Debt / Medium to Long | 129.4917 | 11-Sep-2026 | Regular Plan | Growth Option |
| `100037` | Aditya Birla Sun Life Medium to Long Term Fund - Quarterly IDCW | Debt / Medium to Long | 13.0383 | 11-Sep-2026 | Regular Plan | IDCW Option |

---

## 6. Code Modifications & Deliverables

1. [`config/sources/sources.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/sources/sources.json): Updated source entries with exact validation statuses (`UNAVAILABLE_HTTP_404` for direct bulk metadata download URLs).
2. [`models/source.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/models/source.py): Updated `ValidationStatus` Enum to support `UNAVAILABLE_HTTP_404` and `DEPRECATED`.
3. [`tests/data_quality/test_phase_f10_2_source_discovery.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f10_2_source_discovery.py) `[NEW]`: Added 6 focused source discovery and validation tests.
4. [`docs/phase_f10_2_authoritative_metadata_source_discovery_and_validation.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f10_2_authoritative_metadata_source_discovery_and_validation.md) `[NEW]`: Master Phase F.10.2 Discovery & Validation Report.
5. [`docs/documentation_traceability_matrix.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/documentation_traceability_matrix.md): Registered Phase F.10.2.

---

## 7. Safety & Production Boundaries

> [!CAUTION]
> - **Financial Methodology Unaltered**: Zero modifications to Fund Quality weights, scoring formulas, Risk Capacity, Risk Tolerance, Risk Alignment, Suitability, Portfolio Need, Economic Benefit, or Action decision rules.
> - **Production Recommendation Boundary**: Production investment recommendations (`BUY`, `ACCUMULATE`, `HOLD`, `SELL`), automated portfolio execution, and real-money transactions remain **100% UNAUTHORIZED**.
> - **F.11 Requirement**: Downstream F.11 decision engines must be designed to gracefully handle explicit `None` metadata values without crashing or substituting synthetic defaults.

---

## 8. Project Progress & Qualitative Readiness Toward F.12

1. **Completed Phases**: F.1 through F.9.4.3, F.10, F.10.1, F.10.2.
2. **Current Phase**: **F.10.2 Completed**.
3. **Remaining Major Phases before F.12**: F.11 (Downstream Decision Engine Real-Data Integration), F.12 (Final Production Readiness & Governance Signoff).
4. **What can now be tested in UI using real data**: Real production dataset snapshots containing daily NAV, Scheme Code, ISIN, Scheme Name, Plan, Option, Category, Subcategory, Lock-in, and Provenance metadata across 8,082 valid funds.
5. **What backend/data work remains**: Downstream decision engine integration (F.11) handling explicit `None` metadata.
6. **What empirical financial-methodology work remains**: Downstream decision engine backtesting and validation on production datasets (F.11).
7. **What remains before human-supervised pilot testing**: F.11 and F.12 completion.
8. **Qualitative Readiness toward F.12**: *Substantially Built & Integration-Ready* (Source authority catalog updated, metadata feeds classified as `UNAVAILABLE_HTTP_404`, and missing-data guardrails enforced).

---

## 9. Final Acceptance Status

**PHASE F.10.2 AUTHORITATIVE METADATA SOURCE DISCOVERY & VALIDATION PASSED**
