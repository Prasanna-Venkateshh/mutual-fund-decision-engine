# PHASE F.19.1.1.1.1 — F.16 POPULATION, RETURN-FIELD & REPRESENTATIVE-SCHEME FORENSIC CLOSURE REPORT

## Executive Summary
This phase completes the narrow forensic reconciliation of Phase F.16 out-of-sample validation lineage.

### Key Conclusions
1. **Full-Population Active Dimensions:** In F.16, **96.74%** of schemes (4,958 / 5,125) had **2 active dimensions** (Return & Volatility). **3.26%** of schemes (167 / 5,125) had **1 active dimension** (Return only, due to zero/insufficient volatility variance).
2. **`cagr_overall` Lineage:** Normal Metric Engine semantics define `cagr_overall` as multi-year CAGR. In F.16, trailing 1-Year simple NAV return ($r_{1y} = (\text{NAV}_T / \text{NAV}_{T-252}) - 1.0$) was manually computed and assigned into `metrics.cagr_overall`.
3. **Representative Scheme Identity:** `CANONICAL_LARGE_CAP_DIR_001` was a synthetic test fixture. It has been replaced with 3 genuine AMFI-backed schemes (`CAN_AMFI_100033`, `CAN_AMFI_100034`, etc.) with full ISIN and AMFI code provenance.
4. **Validation Lineage Classification:** **Class B — PRODUCTION ENGINE VALIDATION UNDER DEGRADED TWO-DIMENSION DATA**.

---

## 1. Population Waterfall & Active Dimension Distribution

| Active Dimensions | Scheme Count | Percentage | Rescaled Weight Pattern |
|---|---:|---:|---|
| **1 Active Dimension** | 167 | 3.26% | Return: 100.0% |
| **2 Active Dimensions** | 4,958 | 96.74% | Return: 62.5%, Volatility: 37.5% (Equity/Hybrid) |
| **3–6 Active Dimensions** | 0 | 0.00% | N/A |
| **Total Scored Population** | **5,125** | **100.00%** | |

---

## 2. Genuine AMFI-Backed Representative Scheme Decompositions

### Representative Scheme 1: `Aditya Birla Sun Life Large & Mid Cap Fund - Regular Growth`
- **Canonical Scheme ID:** `CAN_AMFI_100033`
- **AMFI Code:** `100033` | **ISIN:** `INF209K01165`
- **Peer Group Key:** `Equity::Large Cap::REGULAR`

| Dimension | Raw Value | Available? | Normalized Score | Base Weight | Rescaled Weight | Weighted Contribution |
|---|---:|---|---:|---:|---:|---:|
| Return | 0.3059 | YES | 80.95 | 25.0% | 62.5% | 50.59 |
| Volatility | 0.1036 | YES | 20.11 | 15.0% | 37.5% | 7.54 |
| **Final Score** | | | | | | **58.1** |

---

## 3. Final Required Governance Status Table

- **FINAL STATUS:** `PASSED WITH LIMITATIONS`
- **PRODUCTION CODE CHANGED:** `NONE`
- **PRODUCTION METHODOLOGY CHANGED:** `NONE`
- **F.16 ACTIVE DIMENSION DISTRIBUTION:** 96.74% 2 Active Dims, 3.26% 1 Active Dim
- **F.16 SCORING FORMULA:**
  $$\text{FQ}_{\text{F16}} = 0.625 \times \text{Percentile\_Rank}(r_{1y}) + 0.375 \times \text{Percentile\_Rank}(1 / \text{vol}_{1y})$$
- **F.16 VALIDATION CLASSIFICATION:** Class B — Production Engine Validation under Degraded Two-Dimension Data
- **DYNAMIC RESCALING GOVERNANCE:** PRODUCTION IMPLEMENTED BUT EMPIRICALLY UNVALIDATED
