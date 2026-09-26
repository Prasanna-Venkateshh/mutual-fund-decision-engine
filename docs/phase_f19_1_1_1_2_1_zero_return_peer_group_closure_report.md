# PHASE F.19.1.1.1.2.1 — ZERO-RETURN ENGINE HANDLING & POINT-IN-TIME REPRESENTATIVE PEER-GROUP CLOSURE REPORT

## Executive Summary
This phase completes the narrow forensic governance closure of the zero-return engine defect and representative scheme point-in-time peer group classification.

### Key Governance Conclusions
1. **Defect Classification (DEFECT-FQ-2026-001):** Confirmed **GENUINE PRODUCTION CODE DEFECT**. In `scoring/engine.py` L81, `(target_input.metrics.cagr_overall or target_input.metrics.rolling_1y_mean)` evaluates float `0.0` as boolean `False`, incorrectly treating valid 0.0% return observations as missing data.
2. **F.16 Downstream OOS Contamination:** **0.0% (Zero Contamination)**. All 167 zero-return schemes (90 1-dim Volatility-Only and 77 0-dim) received final score `None` because active weight sum ($15.0\%$ or $0.0\%$) was below the engine's $40.0\%$ threshold (`scoring/engine.py` L179). They were completely excluded from the valid scored population ($N = 4,958$) used for OOS evaluation.
3. **Representative Scheme `CAN_AMFI_100033` Peer Group Status:** **UNVERIFIED / FALLBACK DEFAULT**. Database columns for category/subcategory were `UNASSIGNED`. The F.16 validation script applied fallback `'Equity::Large Cap'`. The 58.1 score decomposition is mathematically reproducible under script fallbacks, but illustrative only.
4. **Production Code Status:** `UNCHANGED`. Production scoring code strictly preserved per governance constraints. Fix logged in Defect Register (`docs/defect_register_f19_1_1_1_2_1.json`).

---

## 1. Defect Classification Register (DEFECT-FQ-2026-001)

| Field | Detail |
|---|---|
| **Defect ID** | `DEFECT-FQ-2026-001` |
| **Title** | Legitimate Zero-Return Value (0.0) Treated as Missing Data via Python Boolean OR Fallback |
| **Classification** | **GENUINE PRODUCTION CODE DEFECT** |
| **Affected Component** | `scoring/engine.py` (Lines 81 & 89) |
| **Affected Code** | `(target_input.metrics.cagr_overall or target_input.metrics.rolling_1y_mean)` |
| **Observed Behavior** | Float `0.0` evaluates as boolean `False`, falling back to `rolling_1y_mean` (`None`). Return dimension `data_available` set to `False`. |
| **Expected Behavior** | Engine should use explicit non-None check (`cagr_overall is not None`) so that 0.0% return is retained as a valid input. |
| **F.16 Contamination** | **0.0%** (All 167 affected schemes received score `None` and were excluded from valid OOS dataset). |
| **Production Fix Status** | Documented & covered by regression tests; unfixed in current phase per absolute rule. |

---

## 2. Sample 1-Dim Volatility-Only Schemes (NAV Evidence Table)

| Scheme CID | AMFI Code | Scheme Name | NAV Start (2023-01-31) | NAV End (2024-01-31) | Calculated $r_{1y}$ | Engine Return Avail? | Engine Vol Avail? | Final Score |
|---|---|---|---:|---:|---:|---|---|---|
| `CAN_AMFI_100044` | 100044 | ABSL Liquid Fund - Retail | 163.694 | 163.694 | **0.0000** | FALSE (Defect) | TRUE (0.00186) | `None` |
| `CAN_AMFI_100842` | 100842 | Nippon India Liquid Fund | 1524.280 | 1524.280 | **0.0000** | FALSE (Defect) | TRUE (0.00165) | `None` |
| `CAN_AMFI_101840` | 101840 | DSP Credit Risk Fund | 10.2481 | 10.2505 | **0.0000** (rounded) | FALSE (Defect) | TRUE (0.00299) | `None` |
| `CAN_AMFI_101972` | 101972 | ABSL Money Market Fund | 100.015 | 100.015 | **0.0000** | FALSE (Defect) | TRUE (0.00107) | `None` |
| `CAN_AMFI_103160` | 103160 | Tata Treasury Advantage | 1003.5288 | 1003.5288 | **0.0000** | FALSE (Defect) | TRUE (0.00075) | `None` |

---

## 3. Final Required Governance Table

- **FINAL STATUS:** `PASSED WITH LIMITATIONS`
- **PRODUCTION CODE CHANGED:** `NONE`
- **PRODUCTION METHODOLOGY CHANGED:** `NONE`
- **CONFIRMED ENGINE DEFECT:** `DEFECT-FQ-2026-001` (Python Boolean OR zero-return defect)
- **DEFECT CLASSIFICATION:** Genuine Production Code Defect
- **DEFECT F.16 CONTAMINATION:** 0.0% (All affected schemes received score `None`)
- **CAN_AMFI_100033 PEER GROUP STATUS:** UNVERIFIED / FALLBACK DEFAULT
- **DYNAMIC RESCALING GOVERNANCE:** PRODUCTION IMPLEMENTED BUT EMPIRICALLY UNVALIDATED
