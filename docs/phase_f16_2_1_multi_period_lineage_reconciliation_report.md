# PHASE F.16.2.1 — MULTI-PERIOD VALIDATION LINEAGE, REUSE CLASSIFICATION & STATISTICAL CLAIM RECONCILIATION REPORT

## EXECUTIVE SUMMARY
This report details the forensic lineage audit and statistical claim reconciliation of Phase F.16.2. It establishes the explicit classification of evaluated historical periods into genuinely unseen out-of-sample evidence versus reused replication evidence.

Across all evaluated periods, the frozen v1.0.0 production engine (`FundQualityScoringEngine`) was executed directly without modifying any formulas, weights, peer keys (`category::subcategory::plan_type`), or normalization parameters (`PeerGroupNormalizer`).

---

## 1. REQUIRED LINEAGE & PERIOD RECONCILIATION TABLE

| Anchor | Outcome | Classification | Exact Production? | N | FQ Return | Trailing Return | FQ MDD | Trailing MDD | Spearman rho |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| **2021-01-31** | 2021$\rightarrow$2022 | NOT AVAILABLE | NO | 0 | N/A | N/A | N/A | N/A | N/A |
| **2022-01-31** | 2022$\rightarrow$2023 | REUSED / REPLICATION | YES | 3,705 | 0.94% | 1.83% | 17.39% | 17.60% | +0.0516 |
| **2023-01-31** | 2023$\rightarrow$2024 | REUSED / REPLICATION | YES | 4,249 | 7.19% | 31.45% | 0.12% | 5.62% | -0.2391 |
| **2024-01-31** | 2024$\rightarrow$2025 | GENUINELY UNSEEN OOS | YES | 4,958 | 13.01% | 12.98% | 14.86% | 16.67% | +0.5551 |

---

## 2. REQUIRED OOS CLASSIFICATION SUMMARY

- **GENUINELY UNSEEN OOS PERIODS (1):**
  - `2024-01-31 to 2025-01-31` (First evaluated strictly OOS under frozen production engine in F.16)
- **REUSED / REPLICATION PERIODS (2):**
  - `2022-01-31 to 2023-01-31` (Outcomes previously exposed to methodology decisions in F.11)
  - `2023-01-31 to 2024-01-31` (Outcomes previously exposed to methodology decisions in F.11/F.15)
- **UNAVAILABLE PERIODS (1):**
  - `2021-01-31 to 2022-01-31` (Database depth lacks $\ge 252$ daily PIT records prior to 2020-01-31)

---

## 3. POPULATION WATERFALL RECONCILIATION

Population reductions across anchors are fully explained by point-in-time minimum history constraints:
- **2022 Anchor:** Stage 1 Anchor $N = 5,556 \rightarrow$ Excluded $1,851$ schemes lacking $\ge 252$ daily PIT NAV records $\rightarrow$ Final Scored $N = 3,705$ ($k = 371$).
- **2023 Anchor:** Stage 1 Anchor $N = 5,489 \rightarrow$ Excluded $1,240$ schemes lacking $\ge 252$ daily PIT NAV records $\rightarrow$ Final Scored $N = 4,249$ ($k = 425$).
- **2024 Anchor:** Stage 1 Anchor $N = 5,874 \rightarrow$ Excluded $696$ schemes lacking $\ge 252$ daily PIT NAV records and $220$ non-scored/unreachable schemes $\rightarrow$ Final Scored $N = 4,958$ ($k = 496$).

---

## 4. PERIOD-BY-PERIOD NESTED REGRESSION (INCREMENTAL MODEL FIT)

| Anchor Date | Outcome Period | N | M0 R² | M1 R² (Return) | M2 R² (Ret+Vol) | M3 R² (M2+FQ) | Incremental R² (M3-M2) |
|---|---|---:|---:|---:|---:|---:|---:|
| **2022-01-31** | 2022$\rightarrow$2023 | 3,705 | 0.0000 | 0.0014 | 0.0025 | 0.0027 | **+0.0001** |
| **2023-01-31** | 2023$\rightarrow$2024 | 4,249 | 0.0000 | 0.0006 | 0.0508 | 0.1056 | **+0.0548** |
| **2024-01-31** | 2024$\rightarrow$2025 | 4,958 | 0.0000 | 0.2053 | 0.2280 | 0.3325 | **+0.1045** |

> [!WARNING]
> **Component Circularity Statement:** Production FQ is directly constructed from percentile ranks of Trailing 1Y Return and Reciprocal Volatility. Therefore, incremental $R^2$ represents additional non-linear composite model fit, **NOT** independent fundamental information.

---

## 5. RECONCILIATION OF PRIOR ARTIFACT RESULTS

- **F.11.3.5.5 Comparison (2024 Anchor):** F.11.3.5.5 reported Trailing Return = 12.23% and FQ Return = 11.85% ($N=5,713$). F.16.2.1 yields Trailing Return = 12.98% and FQ Return = 13.01% ($N=4,958$). The discrepancy is explained by F.11 using an early raw-value prototype formula without intra-category peer normalization and including schemes with $<252$ daily PIT records.
- **F.16 / F.16.1 Comparison (2024 Anchor):** 100% exact numerical match ($N=4,958$, FQ Return = 13.01%, FQ MDD = 14.86%, Spearman $\rho = +0.5551$).

---

## 6. MARKET REGIME & LANGUAGE GOVERNANCE
- Unsubstantiated causal and macroeconomic regime labels (such as "momentum bull run" or "balanced market") have been completely removed.
- Periods are designated strictly by neutral anchor dates (2022, 2023, and 2024 anchor periods).

---

## 7. REQUIRED GOVERNANCE CLAIM MATRIX

| Claim | Evidence | Status |
|---|---|---|
| Multi-period forward association | Evaluated across 3 historical anchor periods | **SUPPORTED** |
| Consistent positive association | Spearman $\rho$ varies from $-0.2391$ to $+0.5551$ | **NOT SUPPORTED** |
| FQ consistently exceeds trailing return | FQ return higher in 1 of 3 evaluated periods | **NOT SUPPORTED** |
| FQ consistently has lower MDD | FQ MDD lower than trailing return across all 3 evaluated periods | **SUPPORTED DESCRIPTIVELY** |
| Quintile monotonicity persists | Monotonic in 1 of 3 evaluated periods (2024 anchor) | **NOT SUPPORTED** |
| Incremental model-fit contribution persists | Positive incremental R² across evaluated periods | **SUPPORTED** |
| Independent information established | Component circularity present (Return + Volatility composite) | **NOT SUPPORTED** |
| Economic benefit established | Gross NAV evaluation (no tax, fee, or turnover costs) | **NOT SUPPORTED** |
| Causal risk protection established | Observational correlation only | **NOT SUPPORTED** |
| Consequential decision readiness | Requires Action Engine and Suitability layer integration | **NOT SUPPORTED** |

---

## 8. PRODUCTION & GOVERNANCE STATUS
- **Production Scoring Engine:** FROZEN v1.0.0 (`FundQualityScoringEngine`).
- **Final Validation Status:** **PASSED WITH LIMITATIONS** (Lineage and mechanics fully reconciled; evidence consists of 1 genuinely unseen OOS period and 2 replication periods).
