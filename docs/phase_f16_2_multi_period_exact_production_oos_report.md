# PHASE F.16.2 — MULTI-PERIOD EXACT-PRODUCTION OOS ROBUSTNESS VALIDATION REPORT

## EXECUTIVE SUMMARY
This report details the multi-period out-of-sample (OOS) robustness validation of the frozen v1.0.0 production Fund Quality Scoring Engine (`FundQualityScoringEngine`).

Across three historical annual anchor periods (2022-01-31, 2023-01-31, and 2024-01-31), the frozen production engine was executed independently without modifying any formulas, weights, normalization methods (`PeerGroupNormalizer`), or exact peer key definitions (`category::subcategory::plan_type`).

## PERIOD-BY-PERIOD OUTCOME TABLE

| Anchor | Status | N | FQ Mean Return | Trailing Mean Return | Volatility Mean Return | FQ Mean MDD | Trailing Mean MDD | Volatility Mean MDD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2022-01-31 | PREVIOUSLY EVALUATED / REUSED | 3,705 | 0.94% | 1.83% | 5.42% | 17.39% | 17.60% | 0.68% |
| 2023-01-31 | PREVIOUSLY EVALUATED / REUSED | 4,249 | 7.19% | 31.45% | 5.46% | 0.12% | 5.62% | 0.06% |
| 2024-01-31 | GENUINELY UNSEEN | 4,958 | 13.01% | 12.98% | 6.33% | 14.86% | 16.67% | 0.11% |

*Aggregate Summary Weighting:*
- Equal-Period Weighted Spearman $\rho$: $+0.1225$
- N-Weighted Spearman $\rho$: $+0.1492$

## EVIDENCE CONSISTENCY CLASSIFICATION

**Classification: MIXED**

- **Directional Variation:** Spearman rank correlation between anchor FQ score and 1Y forward return varies materially across market regimes:
  - 2022-01-31 $\rightarrow$ 2023-01-31: $\rho = +0.0516$
  - 2023-01-31 $\rightarrow$ 2024-01-31: $\rho = -0.2391$ (Strong equity bull run favored momentum/high-volatility schemes)
  - 2024-01-31 $\rightarrow$ 2025-01-31: $\rho = +0.5551$ (Balanced market environment)
- **Drawdown Protection:** FQ Strategy C produced lower forward Maximum Drawdown (MDD) than Trailing Return Strategy A in 3 out of 3 evaluated periods.
- **Return Dominance:** FQ Strategy C achieved higher forward return than Trailing Return Strategy A in only 1 out of 3 evaluated periods (2024-01-31 anchor).

## REQUIRED CLAIM MATRIX

| Claim | Evidence | Status |
|---|---|---|
| Exact production engine used | `FundQualityScoringEngine` executed directly | SUPPORTED |
| Exact production peer groups used | `category::subcategory::plan_type` exact peer key enforced | SUPPORTED |
| PIT integrity | Strictly zero future metadata/NAV access at anchor date | SUPPORTED |
| Multi-period forward association | Evaluated across 3 historical anchor periods | SUPPORTED |
| Consistent positive association | Spearman $\rho$ varies from $-0.2391$ to $+0.5551$ | NOT SUPPORTED |
| FQ consistently exceeds trailing return | FQ return higher in 1 of 3 periods | NOT SUPPORTED |
| FQ consistently has lower MDD | FQ MDD lower than trailing return in 3 of 3 periods | SUPPORTED |
| Quintile monotonicity persists | Monotonic in 2024 period, non-monotonic in 2023 equity-bull regime | NOT SUPPORTED |
| Incremental model-fit contribution persists | Positive incremental R² across evaluated periods | SUPPORTED |
| Independent information established | Component circularity present (Return + Volatility composite) | NOT SUPPORTED |
| Economic benefit established | Gross NAV evaluation (no tax, fee, or turnover costs) | NOT SUPPORTED |
| Causal risk protection established | Observational correlation only | NOT SUPPORTED |
| Consequential decision readiness established | Requires Action Engine and Suitability layer integration | NOT SUPPORTED |

## PRODUCTION & GOVERNANCE STATUS
- **Production Methodology:** FROZEN (v1.0.0, no changes permitted).
- **Final Validation Status:** **PASSED WITH LIMITATIONS** (Mechanically reproducible, PIT-safe, exact-production, but multi-period outcome consistency is mixed across macro regimes).
