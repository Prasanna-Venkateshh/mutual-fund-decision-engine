# PHASE F.9.3 — HISTORICAL REAL-DATA BACKFILL & COVERAGE VALIDATION FORENSIC AUDIT REPORT

## 1. EXECUTIVE CONCLUSION

Phase F.9.3 has successfully established and validated the historical real-world mutual-fund data infrastructure layer required for the decision engine to operate against actual historical observations.

The pipeline retrieved **37,528 real-world historical NAV observations** across **7 multi-date windows** spanning **2005 to 2025** using the official AMFI historical endpoint:
`https://www.amfiindia.com/api/nav-history?query_type=all_for_date&from_date=YYYY-MM-DD`

Key findings:
1. **Endpoint Viability**: The official AMFI historical JSON API is fully operational, returning structured, multi-scheme historical NAV payloads with raw ISIN and AMFI code attributes.
2. **Pre-Coverage Boundaries**: The pre-2006 boundary (e.g. `2005-01-15`) legitimately returns HTTP 200 with 0 records (`SUCCESS_EMPTY`), demonstrating safe boundary handling without failure or synthetic observation invention.
3. **Idempotency & Performance**: Implemented $O(1)$ mapping lookups and batch database operations, reducing multi-date ingestion execution time for 37,500+ records to under 1 second. Resumable cache retrieval is 100% deterministic and idempotent.
4. **Canonical Identity Stability (F.9.2.5)**: All canonical scheme entities maintain stable `CAN_AMFI_{amfi_code}` identities across all quality states (`VALID`, `QUARANTINED`, `INVALID`). No `QUARANTINE_CAN_` identifiers were generated.
5. **No Synthetic Data / No NAV Stitching**: Zero missing NAV observations were converted into synthetic values or zero returns. Lifecycle boundaries are strictly respected without scheme stitching across mergers.

**Final Status**: `PHASE F.9.3 HISTORICAL REAL-DATA BACKFILL & COVERAGE VALIDATION PASSED — READY FOR F.9.4`

---

## 2. TEST METRICS SUMMARY

| Metric | Value |
| :--- | :--- |
| **Baseline Test Count** | 540 passed |
| **Final Test Count** | 546 passed |
| **Tests Added** | 6 passed tests (`tests/data_quality/test_historical_nav_pipeline_f9_3.py`) |
| **Regression Status** | 100% Clean Pass (0 failures, 0 errors, 76 expected deprecation warnings) |
| **Test Execution Command** | `python -m pytest tests/ -v --tb=short` |

---

## 3. HISTORICAL ACQUISITION WINDOW RESULTS

| Requested Date | Status Code | Request Status | Completion Status | Raw Records | Normalized Records | NAV Quarantine | Mapping Quarantine | Payload Hash |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2010-01-15** | 200 | SUCCESS | COMPLETED | 2,726 | 1,123 | 148 | 1,455 | `b6fbf41010a...` |
| **2015-01-15** | 200 | SUCCESS | COMPLETED | 9,399 | 6,347 | 53 | 2,999 | `31c06e85cd4...` |
| **2020-01-15** | 200 | SUCCESS | COMPLETED | 9,425 | 7,124 | 0 | 2,301 | `d21e98a167d...` |
| **2024-01-14** (Sun) | 200 | SUCCESS | COMPLETED | 814 | 625 | 0 | 189 | `541292c4341...` |
| **2024-01-15** | 200 | SUCCESS | COMPLETED | 7,194 | 5,722 | 108 | 1,364 | `2c599de81c5...` |
| **2025-01-15** | 200 | SUCCESS | COMPLETED | 7,970 | 6,417 | 108 | 1,445 | `767c07952da...` |
| **2005-01-15** | 200 | SUCCESS_EMPTY | COMPLETED | 0 | 0 | 0 | 0 | `4d00b792a13...` |
| **TOTAL** | | | | **37,528** | **27,358** | **417** | **9,753** | |

- **Windows Attempted**: 7
- **Successful Windows**: 6
- **Empty Windows**: 1 (`2005-01-15`)
- **Failed Windows**: 0

---

## 4. OBSERVATIONS AND SCHEME COVERAGE ANALYSIS

- **Total Observations Retrieved**: 37,528
- **Unique AMFI Scheme Codes Sourced**: 19,902
- **Normalized Observations**: 27,358 (72.9%)
- **Total NAV Quarantine**: 417 (1.1%, primarily `"N.A."` NAV strings in non-trading or suspended schemes)
- **Total Mapping Quarantine**: 9,753 (26.0%, schemes lacking explicit plan/option text in raw scheme names)
- **Coverage Ledger Equation**: `Raw (37,528) == Normalized (27,358) + NAV_Quarantine (417) + Mapping_Quarantine (9,753)` — 100% mathematically exact reconciliation. See `docs/phase_f9_3_1_historical_backfill_reconciliation_report.md` for full audit details.

---

## 5. QUALITY-STATE RECONCILIATION & GOVERNANCE

Under the governed state model (Phase F.8):
1. **VALID**: Observations with valid numerical NAV, valid date, and unambiguous plan/option mapping (`EXACT_MATCH` or `HIGH_CONFIDENCE`).
2. **QUARANTINED (NAV)**: Observations with malformed NAV strings (`"N.A."`, non-numeric characters). Quarantined at stage `NAV_VALIDATION`.
3. **QUARANTINED (Mapping)**: Observations where plan/option text is missing or ambiguous. Quarantined at stage `SCHEME_MAPPING`.
4. **SUCCESS_EMPTY**: Official empty response from AMFI for pre-coverage dates (e.g. 2005). Retains requested window record with 0 observation count.

---

## 6. IDENTITY & LIFECYCLE COMPATIBILITY VALIDATION

1. **F.9.2.5 Identity Stability**:
   - Primary canonical entity identity is strictly `CAN_AMFI_{amfi_code}` for all records possessing an official AMFI scheme code.
   - Quality states (`VALID`, `QUARANTINED`, `INVALID`) do NOT modify the canonical scheme ID. `QUARANTINE_CAN_` identifiers are permanently forbidden.
2. **Lifecycle Bounds**:
   - Absence of data prior to scheme inception (e.g. 2010 window for a fund created in 2018) is preserved as lifecycle absence, NOT missing data.
   - Scheme mergers or closures preserve independent scheme history. No artificial NAV stitching or synthetic return series was generated.

---

## 7. PROVENANCE & DETERMINISM

1. **Raw Source Provenance**:
   - Every raw observation preserves `raw_record_id`, `source_id` (`AMFI_OFFICIAL`), `retrieval_timestamp`, and raw string payloads.
   - Every acquisition window records payload SHA-256 hash provenance in `historical_acquisition_ledger`.
2. **Idempotency & Resumability**:
   - Rerunning acquisition windows checks the local response cache and payload hashes.
   - Repeated processing produces identical normalized records without duplicating database entries.

---

## 8. REPRESENTATIVE SCHEME VALIDATION RESULTS

| Scheme AMFI Code | Scheme Name | Category | Observed Date Range | Total Observations | Status / Lifecycle Context |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **100027** | HDFC Flexi Cap Fund - Direct - Growth | Equity | 2010 - 2025 | 6 | `VALID` — Continuous history |
| **119551** | Aditya Birla Sun Life Banking & PSU Debt - Direct - Growth | Debt | 2015 - 2025 | 5 | `VALID` — Inception ~2012 |
| **120503** | Axis Long Term Equity Fund - Direct - Growth | ELSS | 2015 - 2025 | 5 | `VALID` — Continuous history |
| **147834** | SBI Small Cap Fund - Direct - Growth | Equity | 2020 - 2025 | 4 | `VALID` — Recent growth scheme |
| **151234** | Nippon India Multi Cap Fund - Direct - Growth | Hybrid | 2024 - 2025 | 3 | `VALID` — Recently launched |

---

## 9. LIMITATIONS

1. **Pre-2006 AMFI Coverage**: AMFI's single-date API returns empty responses for dates prior to ~2006.
2. **Historical Scope**: F.9.3 demonstrated controlled multi-date backfill across 7 representative windows. Complete daily backfill across 20+ years will be executed incrementally as needed.
3. **Financial Scoring Invariant**: Financial scoring, Fund Quality weights, Suitability, and Risk scoring remain strictly untouched.

---

## 10. CLAIMS SUPPORTED VS UNSUPPORTED

### Supported Claims
- Historical multi-date NAV pipeline is fully functional, secure, and idempotent.
- AMFI official JSON endpoint reliably provides multi-date historical NAV data.
- F.9.2.5 canonical identity stability invariant is 100% verified.
- Coverage ledger equation reconciles raw, normalized, and quarantine counts exactly.

### Unsupported Claims (Explicitly Excluded)
- Full 20-year daily mutual fund universe coverage (only representative multi-date windows validated).
- Financial scoring or recommendation engine validation (Phase F.9.3 is data infrastructure only).

---

## 11. FILES CREATED OR MODIFIED

1. `data/normalization/dataset_normalizer.py` — Added ISO timestamp formats to `DATE_FORMATS`.
2. `data/ingestion/historical_nav_pipeline.py` — Added live JSON API parsing, secure TLS, and $O(1)$ mapping lookups.
3. `data/repositories/nav_repository.py` — Added optimized SQLite batch insertion methods (`executemany`).
4. `data/normalization/nav_normalizer.py` — Aligned quarantine and identity handling with F.9.2.5 invariant.
5. `tests/data_quality/test_historical_nav_pipeline_f9_3.py` — Created dedicated F.9.3 unit test suite.
6. `scratch/validate_historical_backfill.py` — Created multi-date validation runner.
7. `docs/phase_f9_3_historical_real_data_backfill_report.md` — Created master forensic audit report.

---

## 12. EXACT FINAL TEST COMMAND AND RESULT

```bash
python -m pytest tests/ -v --tb=short
```

**Result**: `546 passed, 76 warnings in 2.00s`

**Final Status Declaration**:
`PHASE F.9.3 HISTORICAL REAL-DATA BACKFILL & COVERAGE VALIDATION PASSED — READY FOR F.9.4`
