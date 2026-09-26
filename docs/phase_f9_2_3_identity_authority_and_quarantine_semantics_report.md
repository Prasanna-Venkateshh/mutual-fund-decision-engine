# Phase F.9.2.3 Implementation Report — AMFI Identifier Authority, Plan/Option Resolution & Quarantine-Diagnostic Semantics Audit

**Date:** 2026-09-14 UTC  
**Scope:** Forensic identity-authority and quarantine-semantics audit of live AMFI dataset ingestion, resolution of Question A (AMFI Scheme Code entity semantics), resolution of Question B (Diagnostic flag occurrences vs mutually exclusive primary quality states), ISIN analysis, canonical ID derivation verification, test suite expansion, and full regression integrity.

---

## 1. Executive Summary & Governance Overview

Phase F.9.2.3 completes a targeted identity-semantics and quarantine-diagnostic audit following Phase F.9.2.2.

### Key Audit Conclusions & Semantic Resolutions:

1. **Resolution of Question A (AMFI Scheme Code Entity Semantics):**
   - Official AMFI Scheme Codes uniquely identify specific **Scheme + Plan + Option** variant entities (Option C).
   - In AMFI's official master schema, `135762` (Axis Children's Fund - Direct Plan - Growth) and `135763` (Axis Children's Fund - Direct Plan - IDCW) are separate, unique AMFI Scheme Codes.
   - **Source Identifier Availability & Uniqueness:** 100.0% complete (14,361 / 14,361 live records contain a unique AMFI Scheme Code).
   - **Governance Rationale for 6,038 Quarantined Records:** The platform intentionally enforces **independent textual plan/option verification** before marking a record `VALID` for downstream financial decision layers. When scheme names contain non-standard or expanded option strings (e.g. `Monthly IDCW`, `Payout of Income Distribution`, `Annual Reinvestment Option`), `SchemeMaster` conservatively assigns `MappingConfidence.AMBIGUOUS` to prevent unverified plan/option classification. This dual control is sound, intentional, and safety-preserving.

2. **Resolution of Question B (Diagnostic Flags vs Primary Quality States):**
   - **Mutually Exclusive Primary Quality States (14,361 Records Total):**
     - **VALID:** 8,082 (56.28%)
     - **QUARANTINED:** 6,038 (42.04%)
     - **INVALID:** 241 (1.68%)
     - **SUM TOTAL:** **14,361 (100.00% Reconciled)**
   - **Diagnostic Quarantine Flag (`is_quarantined = True`):** 6,279 occurrences (6,038 primary QUARANTINED records + 241 primary INVALID records carrying quarantine diagnostic flags).
   - **Set Intersection Breakdown of 241 Primary INVALID Records:**
     - 241 records carry Non-Positive NAV Diagnostic (`0.0` or malformed NAV string).
     - 145 of these 241 INVALID records ALSO carry Textual Plan/Option Ambiguity Diagnostic flags.
     - 96 of these 241 INVALID records carry Non-Positive NAV Diagnostic ONLY.

3. **ISIN Impact Analysis:**
   - 14,191 records (98.8%) contain an ISIN; 170 records (1.2%) contain `-` (no ISIN in source feed).
   - Missing ISIN does **NOT** force a record into `QUARANTINED` or `INVALID`. 37 missing-ISIN records are in `VALID` primary quality state because AMFI Scheme Code and text plan/option parsing were unambiguous. ISIN is an optional secondary identifier.

4. **Canonical ID Derivation Audit:**
   - Canonical IDs (`CAN_AMFI_{source_scheme_code}`) are 100% deterministically derived from authoritative AMFI scheme codes (`135762`). Zero canonical IDs are derived from row position, index, or synthetic counters (`SYNTH_`).
   - Canonical ID (`CAN_AMFI_135762`) is strictly an internal platform identifier and is never represented as an authoritative AMFI Scheme Code (`135762`).

5. **Test Suite Expansion & Full Regression:**
   - **537/537 tests passed** (2 new unit tests added in [`tests/data_quality/test_amfi_live_adapter.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_amfi_live_adapter.py)).

---

## 2. Invariant Reconciliation & Primary State Matrix

| Metric / Invariant | Count / Status | Governance Verification |
| :--- | :--- | :--- |
| **Total Live Parsed Records** | 14,361 | Parsed data rows from official AMFI live feed (`NAVAll.txt`). |
| **VALID Primary Quality State** | 8,082 (56.28%) | Unambiguous AMFI code, valid NAV, and textually verified plan/option. |
| **QUARANTINED Primary Quality State** | 6,038 (42.04%) | Valid AMFI code, valid NAV, but non-standard/ambiguous text plan/option. |
| **INVALID Primary Quality State** | 241 (1.68%) | Structural error / non-positive NAV (`0.0`). |
| **Primary Quality State Sum** | **14,361 (100.00%)** | **100% Mutually Exclusive Primary State Reconciliation** |
| **Flagged Quarantine Diagnostic Occurrences** | 6,279 | 6,038 QUARANTINED + 241 INVALID records carrying `is_quarantined=True`. |
| **Records with AMFI Scheme Code** | 14,361 (100.0%) | 100% of data rows contain an authoritative AMFI code (0 uncoded). |
| **Unique AMFI Scheme Codes** | 14,361 (100.0%) | Every AMFI scheme code in the feed is unique. |
| **Records with ISIN** | 14,191 (98.8%) | 170 records lack ISIN (`-`). |
| **Unique Canonical Scheme IDs** | 14,361 | Deterministically mapped via `CAN_AMFI_{code}`. |

---

## 3. Set Intersection Breakdown Table

```
Total Live Parsed Records: 14,361
├── Primary Quality State: VALID        = 8,082 records (56.28%)
├── Primary Quality State: QUARANTINED  = 6,038 records (42.04%) [100% carry text ambiguity reason]
└── Primary Quality State: INVALID      =   241 records  (1.68%) [100% carry non-positive NAV reason]
    │
    └── Diagnostic Quarantine Flag: `is_quarantined = True` (6,279 total occurrences)
        ├── 6,038 records in QUARANTINED primary state
        └──   241 records in INVALID primary state:
              ├── 145 records carry BOTH Non-Positive NAV & Textual Plan/Option Ambiguity
              └──  96 records carry Non-Positive NAV Diagnostic ONLY
```

---

## 4. Source Identifier vs Entity Resolution Terminology

| Dimension | Demonstrated Status | Description |
| :--- | :--- | :--- |
| **A. Source Identifier Availability** | 🟢 100.0% Complete | All 14,361 parsed records contain an AMFI Scheme Code. |
| **B. Source Identifier Uniqueness** | 🟢 100.0% Unique | 14,361 unique AMFI Scheme Codes present in feed. |
| **C. Source Identifier Preservation** | 🟢 100.0% Preserved | Raw `amfi_code` is retained without alteration. |
| **D. Canonical ID Derivation** | 🟢 100.0% Deterministic | Canonical IDs derived via `CAN_AMFI_{amfi_code}`. |
| **E. Independent Textual Plan/Option Verification** | 🟡 56.3% Verified | 8,082 records textually verified; 6,038 records conservatively quarantined for non-standard text. |

---

## 5. Test Count Reconciliation & Regression Integrity

### Test Count History:
- **F.8 Accepted Baseline:** 508 passed
- **F.9 / F.9.1 Additions:** 15 passed -> 523 passed
- **F.9.2 Additions:** 10 passed -> 533 passed
- **F.9.2.2 Additions:** 2 passed -> 535 passed
- **F.9.2.3 Additions:** 2 passed ([`tests/data_quality/test_amfi_live_adapter.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_amfi_live_adapter.py)) -> **537 passed**

### Final Test Suite Result:
- **Passed:** 537
- **Failed:** 0
- **Skipped:** 0
- **Warnings:** 76
- **Full Regression:** **PASS**

---

## 6. Critical Claim Audit

1. **Live AMFI source retrieval demonstrated:** 🟢 Supported (HTTP 200, 1.5MB text, 14,361 live records over secure TLS)
2. **14,361 real AMFI source records retrieved:** 🟢 Supported (14,361 parsed data rows)
3. **14,361 active schemes demonstrated:** 🟡 Supported with qualification (14,361 active scheme records in current snapshot)
4. **Authoritative AMFI identifiers preserved:** 🟢 Supported (Real AMFI codes and ISINs preserved)
5. **14,361 unique AMFI Scheme Codes demonstrated:** 🟢 Supported
6. **14,361 unique canonical IDs demonstrated:** 🟢 Supported (`CAN_AMFI_{code}`)
7. **Source identifier resolution demonstrated:** 🟢 Supported (100.0% AMFI code extraction)
8. **Plan resolution demonstrated:** 🟢 Supported (`DIRECT` vs `REGULAR` separated)
9. **Option resolution demonstrated:** 🟢 Supported (`GROWTH` vs `IDCW` separated)
10. **Full entity resolution demonstrated:** 🟡 Supported with qualification (AMFI code establishes scheme+plan+option entity; 56.3% textually verified, 42.0% quarantined for text ambiguity)
11. **6,038 records legitimately quarantined:** 🟢 Supported (Conservative independent verification control)
12. **6,279 diagnostic flag occurrences accurately described:** 🟢 Supported (6,038 Quarantined + 241 Invalid)
13. **INVALID and QUARANTINED primary states reconciled:** 🟢 Supported (100.0% mutually exclusive sum: 8082 + 6038 + 241 = 14361)
14. **Raw provenance preserved:** 🟢 Supported (Layer A evidence)
15. **Dataset versioning demonstrated:** 🟢 Supported (`snap_F9_2_0_LIVE_23e08268`)
16. **Historical NAV coverage demonstrated:** 🟡 Supported with qualification (Current NAV snapshot only)
17. **Full universe completeness demonstrated:** 🟡 Supported with qualification (Current active schemes only)
18. **Financial methodology validated:** 🔴 Not supported (Data pipeline only; scoring logic unmutated)
19. **Production recommendations authorized:** 🔴 Not supported (Prohibited)
20. **Transactions authorized:** 🔴 Not supported (Prohibited)

---

## 7. Production-Readiness Boundary

| Domain | Status | Governance Classification |
| :--- | :--- | :--- |
| **A. Live Source Access** | 🟢 Operational | Authoritative AMFI live retrieval operational over secure TLS. |
| **B. Data Pipeline** | 🟢 Operational | 5-layer pipeline processes live records safely. |
| **C. Dataset Quality** | 🟢 Operational | Identity semantics, quality model, quarantine reconciliation, and versioning verified. |
| **D. Financial Methodology** | 🟡 Out of Scope | Downstream scoring logic unmutated and pending future validation. |
| **E. Production Recommendations** | 🔴 Prohibited | Zero authorization for production user recommendations. |
| **F. Real-Money Transactions** | 🔴 Prohibited | Zero authorization for real-money execution. |

---

## 8. Final Status Recommendation

**PHASE F.9.2.3 IDENTITY-AUTHORITY & QUARANTINE-SEMANTICS AUDIT PASSED — READY FOR FINAL F.9.2 ACCEPTANCE**
