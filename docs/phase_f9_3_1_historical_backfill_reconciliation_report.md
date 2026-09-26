# PHASE F.9.3.1 — HISTORICAL BACKFILL RECONCILIATION & DATE-SEMANTICS CORRECTION REPORT

## 1. EXECUTIVE CONCLUSION

Phase F.9.3.1 has completed a thorough forensic investigation and quantitative reconciliation of the Phase F.9.3 historical real-data backfill results and date semantics.

Key Findings & Reconciled Facts:
1. **Root Cause of Discrepancy Resolved**:
   - The intermediate summary in F.9.3 (**27,358 Normalized | 417 NAV Quarantine | 9,753 Mapping Quarantine**) is the **authoritative primary-stage classification** produced by the production pipeline (`NAVNormalizer` + `HistoricalNAVPipeline`).
   - The later summary in F.9.3 (**37,111 Normalized | 417 NAV Quarantine | 0 Mapping Quarantine**) was generated during a temporary test modification where `AMBIGUOUS` scheme mappings were assigned `quality_state=QUARANTINED` inside `NormalizedNAVRecord` objects instead of generating a separate `QuarantineRecord` at the `SCHEME_MAPPING` stage.
   - **Reconciliation**: Both totals sum to **37,528 raw observations**. Under governed primary-stage accounting (`RAW = NORMALIZED + NAV_QUARANTINE + MAPPING_QUARANTINE`), the 9,753 records whose raw scheme names lack explicit plan or option text (26.0%) are isolated as `Mapping Quarantine`.
2. **Unique AMFI Scheme Code Count Sourced**:
   - Across the 7 historical windows, **19,902 unique 6-digit AMFI scheme codes** were sourced.
   - Sourced (AMFI Scheme Code, Observation Date) unique tuples total **37,528** (matching the total raw observation count exactly).
3. **Date Semantics Verified for 2024-01-14 (Sunday)**:
   - For `from_date=2024-01-14` (Sunday), the official AMFI API returned **814 raw observations**, every single one of which has `hNAV_Date` == `'2024-01-14T00:00:00.000Z'`.
   - The schemes returned are **Liquid Funds and Overnight Funds**, which publish NAV 365 days a year under SEBI regulations.
   - On Monday (`2024-01-15`), AMFI returned 7,194 records. All 814 liquid/overnight funds were present on Monday, with 652 (80%) reflecting Sunday-to-Monday interest yield updates.
4. **Canonical Identity Stability (F.9.2.5)**:
   - Preserved `CAN_AMFI_{amfi_code}` entity identity across all quality states. Zero `QUARANTINE_CAN_` entity IDs were generated.
5. **No Synthetic Data & No NAV Stitching**:
   - Zero synthetic NAVs, zero interpolated returns, and zero artificial NAV stitching across mergers/closures.

**Final Status**: `PHASE F.9.3.1 HISTORICAL BACKFILL RECONCILIATION PASSED — F.9.3 READY FOR ACCEPTANCE`

---

## 2. PREVIOUS CONTRADICTORY RESULTS & ROOT CAUSE ANALYSIS

### The Contradictory Figures Reported in F.9.3

| Metric | Intermediate F.9.3 Summary | Task-1223 Final Summary | Status |
| :--- | :--- | :--- | :--- |
| **Raw Observations** | 37,528 | 37,528 | Identical |
| **Normalized Records** | 27,358 | 37,111 | Discrepancy (+9,753) |
| **NAV Quarantine** | 417 | 417 | Identical |
| **Mapping Quarantine** | 9,753 | 0 | Discrepancy (-9,753) |
| **Unique AMFI Scheme Codes** | 14,048 (subset) / 19,620 | 19,902 (full) | Discrepancy (population scope) |

### Root Cause Analysis

1. **Pipeline Architecture**:
   - In `NAVNormalizer.normalize_record()`, when a raw scheme name lacks explicit plan ("Direct"/"Regular") or option ("Growth"/"IDCW") text (e.g. legacy scheme names like `"HDFC Index Fund - Nifty 50 Plan"`), `SchemeMaster` assigns `MappingConfidence.AMBIGUOUS`.
   - The production pipeline returns `(None, q_rec)` for `AMBIGUOUS` mapping confidence, routing the record to `mapping_quarantine_count` (9,753 records).
   - Only exact/high-confidence mappings are returned as `NormalizedNAVRecord` (27,358 records).
   - Invalid NAV strings like `"N.A."` are routed to `nav_quarantine_count` (417 records).

2. **Source of Discrepancy**:
   - During a temporary test edit in F.9.3, `NAVNormalizer` was modified so that `AMBIGUOUS` confidence assigned `quality_state = DataQualityState.QUARANTINED` inside `NormalizedNAVRecord` and returned `(norm_rec, None)`.
   - Because `norm_rec` was returned, all 9,753 ambiguous records were counted in `Normalized` (making `Normalized` = 27,358 + 9,753 = 37,111) and `Mapping Quarantine` became 0.
   - When the normalizer was reverted to enforce primary-stage mapping quarantine as required by `test_08` and `test_09` in integration tests, the counts reverted to 27,358 Normalized and 9,753 Mapping Quarantine.

3. **Authoritative Determination**:
   - Under the repository implementation, the pipeline enforces primary-stage separation:
     `Raw (37,528) == Normalized (27,358) + NAV_Quarantine (417) + Mapping_Quarantine (9,753)`
   - The 9,753 ambiguous records are authoritatively classified as **Mapping Quarantine**, NOT as Normalized records.

---

## 3. ACTUAL REPOSITORY & DATA EVIDENCE

### Per-Window Authoritative Reconciliation Table

| Requested Date | HTTP Status | Request Status | Completion Status | Raw Records | Normalized Records | NAV Quarantine | Mapping Quarantine | Unique AMFI Codes | Payload Hash |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2010-01-15** | 200 | SUCCESS | COMPLETED | 2,726 | 1,123 | 148 | 1,455 | 2,726 | `b6fbf41010a...` |
| **2015-01-15** | 200 | SUCCESS | COMPLETED | 9,399 | 6,347 | 53 | 2,999 | 9,399 | `31c06e85cd4...` |
| **2020-01-15** | 200 | SUCCESS | COMPLETED | 9,425 | 7,124 | 0 | 2,301 | 9,425 | `d21e98a167d...` |
| **2024-01-14** (Sun) | 200 | SUCCESS | COMPLETED | 814 | 625 | 0 | 189 | 814 | `541292c4341...` |
| **2024-01-15** | 200 | SUCCESS | COMPLETED | 7,194 | 5,722 | 108 | 1,364 | 7,194 | `2c599de81c5...` |
| **2025-01-15** | 200 | SUCCESS | COMPLETED | 7,970 | 6,417 | 108 | 1,445 | 7,970 | `767c07952da...` |
| **2005-01-15** | 200 | SUCCESS_EMPTY | COMPLETED | 0 | 0 | 0 | 0 | 0 | `4d00b792a13...` |
| **AGGREGATE TOTAL** | | | | **37,528** | **27,358** | **417** | **9,753** | **19,902** | |

---

## 4. UNIQUE AMFI SCHEME CODE RECONCILIATION

1. **Total Unique 6-Digit AMFI Scheme Codes Sourced**: **19,902** unique codes across the 6 non-empty historical windows.
2. **Total Unique (AMFI Scheme Code, Observation Date) Tuples**: **37,528** (every raw observation represents a unique scheme-date pair).
3. **Reconciliation**:
   - The figure of 14,048 reported in early text was an incomplete count from a subset of normalized schemes.
   - The authoritative total count of unique 6-digit AMFI scheme codes across the 7 historical windows is **19,902**.

---

## 5. DATE SEMANTICS FOR 2024-01-14 (SUNDAY / NON-TRADING DAY)

1. **API Endpoint Behavior**: Endpoint parameter `from_date=2024-01-14` requested data for Sunday, 14-Jan-2024.
2. **Payload Inspection**: AMFI returned **814 raw observations**. Every single record has `hNAV_Date` == `'2024-01-14T00:00:00.000Z'`.
3. **Scheme Classification**: The 814 schemes returned on Sunday are **Liquid Funds and Overnight Funds**, which calculate and publish NAV 365 days a year under SEBI mutual fund guidelines.
4. **Monday (`2024-01-15`) Comparison**:
   - Monday's payload returned 7,194 records (including equity, debt, hybrid, and liquid funds).
   - All 814 liquid/overnight schemes from Sunday were present on Monday.
   - 652 of those liquid schemes (80.1%) had updated NAV values on Monday reflecting Sunday-to-Monday interest yield accrual.
5. **Conclusion**: Sourced observation dates match requested dates exactly. No synthetic dates or prior-day fallbacks were injected.

---

## 6. PRIMARY-STATE VS DIAGNOSTIC-FLAG SEPARATION

1. **Mutually Exclusive Primary States**:
   - Every raw observation maps to EXACTLY ONE primary outcome: `NORMALIZED` (27,358), `NAV_QUARANTINE` (417), or `MAPPING_QUARANTINE` (9,753).
   - Primary accounting equation holds with zero error:
     `Raw (37,528) = Normalized (27,358) + NAV_Quarantine (417) + Mapping_Quarantine (9,753)`
2. **Diagnostic Flags**:
   - Diagnostic reasons (e.g. `AMBIGUOUS_SCHEME_NAME`, `INVALID_NAV_STRING`) are stored in `quarantine_records.reason` and do NOT create duplicate primary states.

---

## 7. CANONICAL IDENTITY & LIFECYCLE STABILITY (F.9.2.5)

1. **Invariant Enforcement**: Primary canonical entity identity is strictly `CAN_AMFI_{amfi_code}` for all records possessing an official AMFI scheme code.
2. **Quality State Independence**: `VALID`, `QUARANTINED`, and `INVALID` observations for the same AMFI code share the same canonical entity ID `CAN_AMFI_{amfi_code}`.
3. **No Synthetic Identifiers**: Zero `QUARANTINE_CAN_` entity IDs were generated.
4. **No Artificial NAV Stitching**: Absence before scheme inception is preserved as lifecycle absence. Mergers preserve independent scheme history.

---

## 8. PROVENANCE & IDEMPOTENCY

1. **Raw Source Provenance**: Every observation retains `raw_record_id`, `source_id` (`AMFI_OFFICIAL`), `retrieval_timestamp`, and raw string payload.
2. **Idempotency**: Rerunning acquisition windows checks the local coverage ledger and response payload hash. Repeated acquisition produces identical database state without duplicate rows.

---

## 9. TEST METRICS & REGRESSION INTEGRITY

- **Baseline Test Count**: 546 passed (from F.9.3)
- **Final Test Count**: 548 passed
- **Tests Added**: 2 new targeted tests in [`tests/data_quality/test_historical_nav_pipeline_f9_3.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_historical_nav_pipeline_f9_3.py):
  1. `test_07_sunday_liquid_fund_date_semantics`
  2. `test_08_reconciled_primary_state_accounting`
- **Regression Command**: `python -m pytest tests/ -v --tb=short`
- **Regression Result**: `548 passed, 76 warnings in 2.66s`

---

## 10. REMAINING LIMITATIONS & FINANCIAL SAFETY BOUNDARY

1. **Coverage Scope**: Historical backfill is validated across 7 representative windows (37,528 observations). Complete 20-year daily historical backfill will be executed in future operational slices.
2. **Financial Safety Boundary**:
   - Data infrastructure only.
   - Financial scoring methodology remains UNVALIDATED in this phase.
   - Zero production recommendations authorized.
   - Zero real-money transactions authorized.

---

## 11. FILES CREATED OR MODIFIED

1. `tests/data_quality/test_historical_nav_pipeline_f9_3.py` — Added targeted F.9.3.1 reconciliation & date semantics tests.
2. `scratch/investigate_f9_3_1.py` — Created forensic acquisition & reconciliation script.
3. `scratch/investigate_date_semantics.py` — Created Sunday 2024-01-14 date semantics inspection script.
4. `docs/phase_f9_3_historical_real_data_backfill_report.md` — Corrected quantitative totals and per-window table to match authoritative primary-stage accounting.
5. `docs/phase_f9_3_1_historical_backfill_reconciliation_report.md` — Created master F.9.3.1 reconciliation report.
6. `docs/documentation_traceability_matrix.md` — Updated traceability matrix with F.9.3.1 status.

---

## 12. EXACT FINAL TEST COMMAND AND RESULT

```bash
python -m pytest tests/ -v --tb=short
```

**Result**: `548 passed, 76 warnings in 2.66s`

**Final Status Declaration**:
`PHASE F.9.3.1 HISTORICAL BACKFILL RECONCILIATION PASSED — F.9.3 READY FOR ACCEPTANCE`
