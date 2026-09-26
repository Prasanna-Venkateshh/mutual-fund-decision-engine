# PHASE F.19.1.1.1.2 — F.16 RETURN AVAILABILITY, FIELD-SEMANTICS & REPRESENTATIVE PEER-GROUP CLOSURE REPORT

## Executive Summary
This phase provides complete forensic closure of the remaining population, field-semantic, and peer-group questions for Phase F.16.

### Key Forensic Findings
1. **Explanation of 90 "Volatility Only" Schemes:** In `scoring/engine.py` (L81), the Return metric value is extracted using: `(target_input.metrics.cagr_overall or target_input.metrics.rolling_1y_mean)`. For 90 schemes, `cagr_overall` was calculated as exactly `0.0`. In Python, `0.0` evaluates as boolean `False`, causing the `or` expression to evaluate `None`, which sets `data_available = False` for Return. Volatility was valid ($> 0$), yielding 1 active dimension. Rescaled volatility weight became 100.0%, but because active weight sum ($15.0\%$) was below the engine's $40.0\%$ threshold (`scoring/engine.py` L179), final score became `None`.
2. **Explanation of 77 "Zero Dimension" Schemes:** For 77 schemes, `cagr_overall` was `0.0` (suppressing Return), while standard deviation of daily log returns was `0` (zero variance in NAV series), setting `annualized_volatility = None` (suppressing Volatility). Active weight sum was $0.0\%$, yielding final score `None`.
3. **`cagr_overall` Field Semantics vs F.16 Mapping:**
   - **Normal Engine Semantics:** Multi-year Compound Annual Growth Rate (`metrics/returns.py`).
   - **F.16 Validation Mapping:** Simple 1-Year point-to-point NAV return ($r_{1y} = (\text{NAV}_T / \text{NAV}_{T-252}) - 1.0$) assigned to `cagr_overall`.
   - **Classification:** **Validation-Specific Field Repurposing**. F.16 validated production engine software execution, not multi-year CAGR or full 6-dimension methodology.
4. **Representative Scheme `CAN_AMFI_100033` Audit:** Database record has `category = UNASSIGNED`, `sub_category = UNASSIGNED`. F.16 applied fallback default `Equity::Large Cap::REGULAR`. Status: **UNVERIFIED / FALLBACK DEFAULT**.

---

## 1. Population Reconciliation & Active Dimension Table

| Active Dimensions | Scheme Count | Percentage | Rescaled Weight Pattern | Score Status |
|---|---:|---:|---|---|
| **0 Active Dimensions** | 77 | 1.50% | Active Weight Sum = 0.0% | Score `None` (Active Weight Sum < 40.0%) |
| **1 Active Dimension** | 90 | 1.76% | Volatility 100.0% | Score `None` (Active Weight Sum = 15.0% < 40.0%) |
| **2 Active Dimensions** | 4,958 | 96.74% | Return 62.5%, Volatility 37.5% | Score Valid (Active Weight Sum = 40.0%) |
| **Total Scored Population** | **5,125** | **100.00%** | | |

---

## 2. Representative Scheme `CAN_AMFI_100033` Audit Table

- **Canonical Scheme ID:** `CAN_AMFI_100033`
- **AMFI Code:** `100033` | **ISIN:** `INF209K01165`
- **Scheme Name:** `Aditya Birla Sun Life Large & Mid Cap Fund - Regular Growth`
- **Database Category / Subcategory:** `UNASSIGNED` / `UNASSIGNED`
- **Script Fallback Peer Group:** `Equity::Large Cap::REGULAR`
- **Peer Group Status:** `UNVERIFIED / FALLBACK DEFAULT`

| Dimension | Raw Value | Data Available? | Normalized Score | Rescaled Weight | Weighted Contribution |
|---|---:|---|---:|---:|---:|
| Return | 0.3059 | YES | 80.95 | 62.5% | 50.59 |
| Volatility | 0.1036 | YES | 20.11 | 37.5% | 7.54 |
| **Final Score** | | | | | **58.1** |

---

## 3. Final Required Governance Table

- **FINAL STATUS:** `PASSED WITH LIMITATIONS`
- **PRODUCTION CODE CHANGED:** `NONE`
- **PRODUCTION METHODOLOGY CHANGED:** `NONE`
- **F.16 POPULATION:** 5,125 Scored Schemes (4,958 Valid Scored, 167 Score None)
- **ONE-DIMENSIONAL SCHEME CAUSE:** Python boolean `or` evaluation of `cagr_overall == 0.0`
- **ZERO-DIMENSIONAL SCHEME CAUSE:** `cagr_overall == 0.0` AND zero NAV variance (`ann_vol == None`)
- **F.16 RETURN MAPPING CLASSIFICATION:** Validation-Specific Field Repurposing
- **DYNAMIC RESCALING GOVERNANCE:** PRODUCTION IMPLEMENTED BUT EMPIRICALLY UNVALIDATED
