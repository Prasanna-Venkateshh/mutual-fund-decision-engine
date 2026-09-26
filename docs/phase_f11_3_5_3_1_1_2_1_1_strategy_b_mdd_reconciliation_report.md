# PHASE F.11.3.5.3.1.1.2.1.1 — Strategy B Comparator & MDD Exact-Origin Reconciliation Report

## 1. Objective

Perform a narrow forensic reconciliation of the Strategy B return ($4.34\%$, $6.82\%$, $6.87\%$) and MDD ($0.11\%$, $0.45\%$) figures from Phase F.11.3.5.3 and subsequent audit phases.

This phase resolves the exact governing definition of Strategy B, separates governed Strategy B from secondary historical risk comparators, establishes exact metric definitions, and validates future-injection safety without changing production Fund Quality scoring, weights, normalization, suitability, portfolio logic, or action logic.

---

## 2. Governed Strategy B Definition

- **Governed Definition**: `LOWEST 10% HISTORICAL VOLATILITY`.
- **Repository Provenance**: [`scripts/run_f11_3_5_3_unseen_validation.py:437`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_unseen_validation.py#L437) (`vol_sorted_idx = np.argsort(hist_vol)`) $\rightarrow$ [`docs/phase_f11_3_5_3_results.json:80`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json#L80) (`strategy_b_vol`).
- **Selection Variable**: Annualized Historical Standard Deviation of Daily NAV Returns (Trailing 250 observations prior to anchor date `2024-01-31`).

---

## 3. Strategy B Return Provenance (4.34% vs 6.82% / 6.87%)

| Figure | Metric / Sort Basis | Population & Denominator | Aggregation Formula | Exact Origin | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **4.34%** | Governed Strategy B (Lowest 10% Historical Volatility) | Valid scored schemes ($N=5,713$, Selected $N=571$) | Equal-weighted arithmetic mean of 1Y forward gross NAV returns | [`scripts/run_f11_3_5_3_unseen_validation.py:444`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_unseen_validation.py#L444) $\rightarrow$ [`docs/phase_f11_3_5_3_results.json:82`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json#L82) | **`4.34% = RECONCILED GOVERNED STRATEGY B RESULT`** |
| **6.82%** | Secondary Comparator (Lowest 10% Historical Downside Risk) | Valid scored schemes ($N=5,713$, Selected $N=571$) | Equal-weighted arithmetic mean of 1Y forward gross NAV returns | Table 29 of [`docs/phase_f11_3_5_3_unseen_period_decision_value_report.md:89`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_unseen_period_decision_value_report.md#L89) | **`6.82% = HISTORICAL NARRATIVE VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE`** |
| **6.87%** | Secondary Comparator (Lowest 10% Historical Downside Risk) | Valid scored schemes ($N=5,713$, Selected $N=571$) | Equal-weighted arithmetic mean of 1Y forward gross NAV returns | [`scripts/run_f11_3_5_3_1_1_2_strategy_governance_reconciliation.py:290`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_1_1_2_strategy_governance_reconciliation.py#L290) $\rightarrow$ [`docs/phase_f11_3_5_3_1_1_2_results.json:37`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_1_1_2_results.json#L37) | **`RECONCILED AS SECONDARY HISTORICAL COMPARATOR (Comparator B-DOWN)`** |

### 3.1 6.82% vs 6.87% Reconciliation
- **Exact Difference**: $0.05$ percentage points ($6.87\% - 6.82\%$).
- **Explanation**: `6.82%` is a truncated narrative report artifact in Table 29 of the F.11.3.5.3 decision value report; `6.87%` is the exact unrounded equal-weighted arithmetic mean return for the Lowest 10% Historical Downside Risk cohort.

---

## 4. MDD Provenance Reconciliation (0.11% vs 0.45%)

| MDD Value | Strategy / Sort Basis | Exact Metric Definition | Exact Origin | Status |
| :--- | :--- | :--- | :--- | :--- |
| **0.11%** | Governed Strategy B (Lowest Historical Volatility) | `MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN` | [`docs/phase_f11_3_5_3_results.json:83`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json#L83) | **`0.11% = RECONCILED GOVERNED STRATEGY B MDD`** |
| **0.45%** | Comparator B-DOWN (Lowest Historical Downside Risk) | `MEDIAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN` | Table 29 of [`docs/phase_f11_3_5_3_unseen_period_decision_value_report.md:89`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_unseen_period_decision_value_report.md#L89) | **`RECONCILED AS SECONDARY COMPARATOR MEDIAN MDD`** |

> [!CAUTION]
> Strategy A ($16.83\%$), Governed Strategy B ($0.11\%$), and Strategy C ($1.26\%$) all use `MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN`. The $0.45\%$ figure is a `MEDIAN` statistic for the Downside Risk comparator and is statistically incomparable to the mean MDD figures.

---

## 5. Population Reconciliation

- **Total Eligible Scored Universe**: $N = 5,713$ schemes (SET_A reachable schemes meeting baseline observation criteria).
- **Selected Decile Population**: $N = 571$ schemes ($10\%$ of $5,713$, integer truncated via `len(cohort) // 10`).

---

## 6. Primary Authoritative Strategy Comparison

Evaluating all three strategies under identical population ($N=5,713$, Selected $N=571$), identical forward period (`2024-02-01` to `2025-01-31`), and identical outcome definitions (`EQUAL-WEIGHTED ARITHMETIC MEAN OF INDIVIDUAL SCHEME 1Y FORWARD GROSS NAV RETURNS` and `MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN`):

| Strategy | Selection Rule | Selected N | Forward Return | Forward MDD | Governance Classification |
| :--- | :--- | ---:| ---:| ---:| :--- |
| **Strategy A** | Top 10% Trailing 1Y Return | 571 | 12.23% | 16.83% | Retrospective Point-in-Time Backtest |
| **Strategy B** | Lowest 10% Historical Volatility | 571 | **4.34%** | **0.11%** | Retrospective Point-in-Time Backtest |
| **Strategy C** | Top 10% Fund Quality Score | 571 | **7.81%** | **1.26%** | Retrospective Point-in-Time Backtest |

---

## 7. Secondary Risk Comparators Table

| Name | Selection Variable | Population N | Forward Return | Mean MDD | Median MDD | Governance Status |
| :--- | :--- | ---:| ---:| ---:| ---:| :--- |
| **Comparator B-DOWN** | Lowest 10% Historical Downside Risk | 571 | 6.87% | 0.11% | 0.45% | **SECONDARY HISTORICAL COMPARATOR — NOT GOVERNED STRATEGY B** |

---

## 8. Future-Data Safety Verification

A future-injection invariance test was conducted by mutating forward NAV returns and forward MDDs by a $10.0\times$ random noise transformation.

- **Governed Strategy B (Volatility Sort) Membership Invariant**: `TRUE` (Pass).
- **Comparator B-DOWN (Downside Risk Sort) Membership Invariant**: `TRUE` (Pass).

---

## 9. Claim Governance & Production Impact

- **Current Production Status**: `FROZEN` (v1.0.0 composite weights 25/20/15/15/15/10 and scoring logic remain 100% untouched).
- **Historical Pre-Anchor Freeze**: `NOT PROVEN`.
- **Prohibited Terms**: "Portfolio MDD", "Risk protection", "Portfolio protection", "Causal risk reduction", "Predictive superiority", "Alpha".

---

## 10. Testing & Verification

- **Dedicated Tests**: [`tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_strategy_b_mdd_reconciliation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_strategy_b_mdd_reconciliation.py) ($12/12$ passed).
- **Full Data Quality Regression Suite**: All passing.

---

## 11. Final Status Rule

`PHASE F.11.3.5.3.1.1.2.1.1 PASSED`
