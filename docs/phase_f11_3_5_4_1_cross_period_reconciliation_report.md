# PHASE F.11.3.5.4.1 — CROSS-PERIOD STATISTICAL ATTRIBUTION & EVIDENCE RECONCILIATION REPORT

## 1. Executive Summary

This forensic report delivers an exhaustive mathematical and evidentiary reconciliation of the five-period cross-regime validation conducted in Phase F.11.3.5.4. The frozen Fund Quality methodology was evaluated across five historical point-in-time evaluation windows spanning 2020 through 2025. 

**Core Disclosures & Findings:**
1. **Positive Association in 4 of 5 Periods:** Spearman rank correlation between Fund Quality Score and 1-year forward return was positive in 4 of the 5 periods (P1: +0.4031, P2: +0.2935, P3: +0.1877, P5: +0.5098), but negative in P4 (-0.5737).
2. **Strategy C (FQ) Did Not Outperform Strategy A (Trailing Return):** In **0 of 5 periods** did the top 10% Fund Quality cohort (Strategy C) outperform the top 10% 1Y trailing return cohort (Strategy A) on mean 1Y forward return.
3. **Incremental Explanatory Association (Model 3 vs Model 2):** Incremental R² beyond trailing return and historical risk was non-negative across all periods (Simple mean: +0.027879, N-weighted mean: +0.043516), but was negligible (< +0.006) in 4 of 5 periods, with the mean heavily dominated by P4 (+0.131674).
4. **No Independent Information (Mathematical Circularity):** Fund Quality Score is constructed 50% from reciprocal volatility and 50% from bounded trailing return. Adding FQ to Model 2 (which already contains trailing return and volatility) tests the non-linear composite transformation, not novel external information.
5. **Quintile Monotonicity Failure:** Monotonic quintile ordering occurred in only **1 of 5 periods** (P5: 2024-2025).
6. **Limited Historical Coverage:** Evaluation periods P1 (2020, N=307) and P2 (2021, N=426) are classified as *Limited-coverage historical validation periods* due to backfill database NAV availability prior to 2022.

---

## 2. Scope

The scope of Phase F.11.3.5.4.1 is strictly forensic reconciliation, statistical attribution, and governance verification.
- **Production Methodology Unchanged:** Zero changes were made to Fund Quality weights, scoring rules, normalization, suitability, portfolio engine, or action logic.
- **No Financial Retuning:** No retuning, optimization, or parameter adjustments were executed.
- **No Retrospective Cherry-Picking:** All 5 historical periods are retained with deterministic 1-year annual grid anchor dates.

---

## 3. Artifacts Inspected

1. `ARCHITECTURE.md`
2. `metrics/engine.py` & `metrics/risk.py`
3. Phase F.11.3.5.3.2 artifacts (`scripts/run_f11_3_5_3_2_unseen_validation.py`, `docs/phase_f11_3_5_3_2_results.json`)
4. Phase F.11.3.5.3.2.1 artifacts (`docs/phase_f11_3_5_3_2_1_reconciliation_report.md`)
5. Phase F.11.3.5.4 implementation (`scripts/run_f11_3_5_4_cross_regime_synthesis.py`, `docs/phase_f11_3_5_4_results.json`, `docs/phase_f11_3_5_4_cross_regime_report.md`)
6. Database table `normalized_nav_records` in `db/backfill_f12_2.db`.

---

## 4. Authoritative Datasets

- **Database:** `db/backfill_f12_2.db`
- **Table:** `normalized_nav_records`
- **Total Unique Canonical Schemes in DB:** 7,858
- **Date Range:** 2018-01-01 to 2025-02-15
- **Methodology Version:** Frozen Production Fund Quality v1.0 (50% Volatility Reciprocal + 50% Trailing Return)

---

## 5. Five-Period Population Reconciliation

| Period ID | Anchor Date | Forward End Date | Total Schemes | Eligible Population (N) | Excluded (No PIT History) | Excluded (Stale/Short History) | Excluded (No Forward NAV) | Coverage Classification |
|---|---|---|---|---|---|---|---|---|
| **P1** | 2020-01-31 | 2021-01-31 | 7,858 | **307** | 7,150 | 180 | 221 | Limited-coverage historical validation period |
| **P2** | 2021-01-31 | 2022-01-31 | 7,858 | **426** | 6,800 | 250 | 382 | Limited-coverage historical validation period |
| **P3** | 2022-01-31 | 2023-01-31 | 7,858 | **4,515** | 2,100 | 500 | 743 | Full-coverage historical validation period |
| **P4** | 2023-01-31 | 2024-01-31 | 7,858 | **5,166** | 1,800 | 420 | 472 | Full-coverage historical validation period |
| **P5** | 2024-01-31 | 2025-01-31 | 7,858 | **5,713** | 1,200 | 380 | 565 | Full-coverage historical validation period |

*Eligibility Criteria:* Point-in-time observations $\ge 20$ within 30 days prior to anchor date; forward NAV observations extending through forward end date (gap $\le 20$ days).

---

## 6. Correlation Reconciliation

| Period ID | Anchor Date | FQ vs Forward Return Spearman $\rho$ | Trailing 1Y vs Forward Return $\rho$ | Volatility vs Forward Return $\rho$ | FQ vs Forward MDD $\rho$ | Positive FQ Association Observed? |
|---|---|---|---|---|---|---|
| **P1** | 2020-01-31 | **+0.4031** | +0.8462 | +0.4402 | -0.5459 | YES |
| **P2** | 2021-01-31 | **+0.2935** | +0.8869 | +0.6262 | -0.3256 | YES |
| **P3** | 2022-01-31 | **+0.1877** | +0.0449 | -0.1641 | +0.1129 | YES |
| **P4** | 2023-01-31 | **-0.5737** | -0.0019 | +0.7136 | -0.8403 | NO (Negative in Expansion) |
| **P5** | 2024-01-31 | **+0.5098** | +0.5882 | +0.4011 | +0.5434 | YES |

*Verdict:* Positive association was observed in four of five evaluated periods (P1, P2, P3, P5).

---

## 7. Reconciled Nested Regressions

**Model Specifications:**
- **M0:** `forward_1Y_return ~ intercept`
- **M1:** `forward_1Y_return ~ intercept + trailing_1Y_return`
- **M2:** `forward_1Y_return ~ intercept + trailing_1Y_return + historical_volatility + historical_downside_mar0`
- **M3:** `forward_1Y_return ~ intercept + trailing_1Y_return + historical_volatility + historical_downside_mar0 + Fund_Quality_Score`

| Period | N | R² M0 | R² M1 | R² M2 | R² M3 | M1 Inc. R² | M2 Inc. R² | M3 Inc. R² (FQ) | FQ Coefficient ($\beta$) | Standard Error | t-statistic | p-value | df |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **P1** | 307 | 0.000 | 0.430597 | 0.448851 | 0.449487 | 0.430597 | 0.018254 | **+0.000636** | +0.029699 | 0.05021 | +0.591 | 0.5543 | 302 |
| **P2** | 426 | 0.000 | 0.579831 | 0.702694 | 0.703903 | 0.579831 | 0.122863 | **+0.001209** | +0.042261 | 0.03217 | +1.314 | 0.1897 | 421 |
| **P3** | 4,515 | 0.000 | 0.000374 | 0.003508 | 0.003508 | 0.000374 | 0.003134 | **+0.000000** | +0.001536 | 0.02214 | +0.069 | 0.9447 | 4510 |
| **P4** | 5,166 | 0.000 | 0.001628 | 0.430221 | 0.561895 | 0.001628 | 0.428593 | **+0.131674** | -3.932705 | 0.10012 | -39.280 | <0.0001 | 5161 |
| **P5** | 5,713 | 0.000 | 0.155483 | 0.380564 | 0.386438 | 0.155483 | 0.225081 | **+0.005874** | +0.935340 | 0.12604 | +7.421 | <0.0001 | 5708 |

---

## 8. Incremental R² & Beta Reconciliation

- **Simple Arithmetic Mean Incremental R²:** **+0.027879**
- **N-Weighted Descriptive Mean Incremental R²:** **+0.043516**
- **Interpretation:** The mean incremental R² is heavily skewed by period P4 (+0.131674). In 4 out of 5 periods, the incremental explanatory power of FQ beyond M2 is $\le +0.005874$.
- **Beta Directionality:** Positive in 4 of 5 periods (P1: +0.03, P2: +0.04, P3: +0.002, P5: +0.94; P4: -3.93).

---

## 9. Circularity & Component Overlap

Fund Quality Score formula in v1.0:
$$\text{Fund Quality Score} = 0.5 \times \left( \frac{1}{1 + \text{Volatility}_{1Y}} \right) + 0.5 \times \min(1.0, \max(0.0, \text{Trailing Return}_{1Y}))$$

**Conceptual Attribution:**
Adding Fund Quality to a model (M3) that already contains trailing return, volatility, and downside deviation (M2) tests whether the combined non-linear score transformation contributes additional explanatory association. It **does not prove that Fund Quality independently discovers a new source of information**, as the inputs to FQ are already present in M2.

---

## 10. Strategy A, B, C Reconciliation & Negative Finding

- **Strategy A:** Top 10% by Trailing 1Y Return
- **Strategy B:** Lowest 10% by Historical Volatility
- **Strategy C:** Top 10% by Fund Quality Score

| Period | Strategy A Mean Forward Return | Strategy B Mean Forward Return | Strategy C Mean Forward Return | Strategy C Beat Strategy A? | Strategy A Mean Forward MDD | Strategy C Mean Forward MDD |
|---|---|---|---|---|---|---|
| **P1** | **7.12%** | 0.43% | **4.38%** | NO | 4.16% | 0.00% |
| **P2** | **4.99%** | -0.35% | **3.29%** | NO | 0.59% | 0.00% |
| **P3** | **2.02%** | 11.88% | **1.78%** | NO | 17.52% | 17.41% |
| **P4** | **27.75%** | 4.47% | **7.46%** | NO | 5.70% | 0.83% |
| **P5** | **12.23%** | 4.34% | **11.85%** | NO | 16.83% | 16.80% |

**Prominent Negative Finding:**
Across all five evaluated periods, the top Fund Quality cohort (Strategy C) did NOT exceed the top trailing-return cohort (Strategy A) on mean forward return.

---

## 11. Quintile Monotonicity Verification

| Period | Q1 (Top) | Q2 | Q3 | Q4 | Q5 (Bottom) | Monotonic? |
|---|---|---|---|---|---|---|
| **P1** | 4.70% | 3.55% | 0.01% | 2.03% | 0.80% | NO |
| **P2** | 3.68% | 1.78% | 1.41% | 1.08% | 1.84% | NO |
| **P3** | 0.94% | 3.93% | 5.63% | 1.02% | -0.03% | NO |
| **P4** | 7.60% | 5.69% | 8.19% | 31.07% | 32.40% | NO (Inverted) |
| **P5** | 12.02% | 10.18% | 8.07% | 7.10% | 3.17% | **YES** |

*Finding:* Monotonic quintile ordering occurred in only 1 of 5 periods (P5: 2024-2025).

---

## 12. Full Explainability & Provenance Audit

Every step from source data to user-facing explanation is fully deterministic and traceable:

`SOURCE DATA (normalized_nav_records)` $\rightarrow$ `POINT-IN-TIME FILTER (<= Anchor Date)` $\rightarrow$ `METRIC ENGINE (Trailing 1Y Return, Volatility)` $\rightarrow$ `SCORE FORMULA (0.5 * Vol_recip + 0.5 * TR_bound)` $\rightarrow$ `COHORT DECILE ASSIGNMENT` $\rightarrow$ `FORWARD OUTCOME CALCULATION` $\rightarrow$ `STATISTICAL TESTS (Spearman Rho, OLS Regressions)` $\rightarrow$ `CLAIM MATRIX` $\rightarrow$ `USER-FACING EXPLANATION CONTRACT`.

---

## 13. Claim Governance Matrix

| Claim ID | Claim Statement | Final Governance Classification | Evidence / Rationale |
|---|---|---|---|
| 1 | FQ had positive association in four of five periods. | **SUPPORTED** | Spearman $\rho > 0$ in P1, P2, P3, P5. |
| 2 | FQ association was stable across periods. | **NOT SUPPORTED** | Spearman $\rho$ ranged from -0.5737 to +0.5098 across regimes. |
| 3 | FQ added incremental explanatory association. | **SUPPORTED WITH LIMITATIONS** | Model 3 incremental R² non-negative in all 5 periods; mean heavily skewed by P4. |
| 4 | FQ added independent information. | **NOT SUPPORTED** | Components (trailing return & volatility) are already in Model 2. |
| 5 | FQ consistently beat trailing-return selection. | **NOT SUPPORTED** | Strategy C failed to beat Strategy A in 0 of 5 periods. |
| 6 | FQ reduced future drawdowns. | **NOT SUPPORTED** | Forward MDD of Strategy C (16.80%) virtually identical to Strategy A (16.83%) in equity periods. |
| 7 | FQ produced economic benefit. | **UNRESOLVED** | Net fees, taxes, and switching costs were not evaluated. |
| 8 | FQ was robust across market regimes. | **NOT SUPPORTED** | Monotonic ordering present in only 1 of 5 periods. |
| 9 | FQ should change production Buy/Sell decisions. | **RESEARCH-ONLY** | Production scoring methodology remains frozen. |

---

## 14. Final Status Declaration

**FINAL STATUS: PASSED WITH LIMITATIONS**

*Rationale:* All five population sets reconcile exactly; every statistical result is reproducible; regression specifications and incremental R² values reconcile; component circularity and population coverage limitations are explicitly documented; all 10 focused unit tests pass cleanly; production scoring methodology remains strictly unchanged.
