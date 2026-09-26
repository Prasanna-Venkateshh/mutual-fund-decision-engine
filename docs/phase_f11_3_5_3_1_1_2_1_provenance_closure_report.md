# PHASE F.11.3.5.3.1.1.2.1 — Strategy Return & MDD Provenance Closure Report

## 1. Objective

Perform a narrow forensic provenance closure for the remaining conflicting Strategy A, Strategy B, and Strategy C return ($12.23\%$ vs $7.56\%$, $4.34\%$ vs $6.82\% / 6.87\%$, $7.81\%$) and MDD ($16.83\%$, $0.11\%$, $0.45\%$, $1.26\%$) figures from F.11.3.5.3, F.11.3.5.3.1, F.11.3.5.3.1.1, and F.11.3.5.3.1.1.2.

This phase establishes the exact origin, formula, population, and terminology of historical strategy metrics without modifying any production Fund Quality scoring, weights, normalization, suitability, portfolio logic, or action logic.

---

## 2. Governing Artifacts Reviewed

- [`scripts/run_f11_3_5_3_unseen_validation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_unseen_validation.py)
- [`docs/phase_f11_3_5_3_results.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json)
- [`docs/phase_f11_3_5_3_unseen_period_decision_value_report.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_unseen_period_decision_value_report.md)
- [`scripts/run_f11_3_5_3_1_1_2_strategy_governance_reconciliation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_1_1_2_strategy_governance_reconciliation.py)
- [`docs/phase_f11_3_5_3_1_1_2_results.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_1_1_2_results.json)
- Production Fund Quality v1.0.0 scoring methodology & configuration

---

## 3. Strategy A Provenance (12.23% vs 7.56%)

| Metric / Value | Selection Rule | Population | Aggregation Formula | Exact Origin | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy A — 12.23%** | Top 10% Trailing 1Y Return | Valid scored schemes ($N=5,713$, Top Decile $N=571$) | Equal-weighted arithmetic mean of individual scheme 1Y forward gross NAV returns | [`scripts/run_f11_3_5_3_unseen_validation.py:440`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_unseen_validation.py#L440) $\rightarrow$ [`docs/phase_f11_3_5_3_results.json:76`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json#L76) | **RECONCILED** (Authoritative) |
| **Strategy A — 7.56%** | Top 10% Trailing 1Y Return | Unknown draft subset | Unknown | Legacy prompt audit question note; absent from all codebase scripts and JSON output files | **UNRECONCILED — ORIGIN NOT PROVEN** |

---

## 4. Strategy B Provenance (4.34% vs 6.82% / 6.87%)

| Metric / Value | Selection Rule | Population | Aggregation Formula | Exact Origin | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy B — 4.34%** | Lowest 10% Raw Historical Volatility | Valid scored schemes ($N=5,713$, Top Decile $N=571$) | Equal-weighted arithmetic mean of individual scheme 1Y forward gross NAV returns | [`scripts/run_f11_3_5_3_unseen_validation.py:444`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_unseen_validation.py#L444) $\rightarrow$ [`docs/phase_f11_3_5_3_results.json:82`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json#L82) | **RECONCILED** (Governed Strategy B) |
| **Strategy B Baseline — 6.82% / 6.87%** | Lowest 10% Historical Downside Risk | Valid scored schemes ($N=5,713$, Top Decile $N=571$) | Equal-weighted arithmetic mean of individual scheme 1Y forward gross NAV returns | Table 29 of [`docs/phase_f11_3_5_3_unseen_period_decision_value_report.md:89`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_unseen_period_decision_value_report.md#L89) | **RECONCILED AS SEPARATE DOWNSIDE RISK COMPARATOR** |

---

## 5. Strategy C Provenance (7.81%)

| Metric / Value | Selection Rule | Population | Aggregation Formula | Exact Origin | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy C — 7.81%** | Top 10% Fund Quality Score | Valid scored schemes ($N=5,713$, Top Decile $N=571$) | Equal-weighted arithmetic mean of individual scheme 1Y forward gross NAV returns | [`scripts/run_f11_3_5_3_unseen_validation.py:448`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_unseen_validation.py#L448) $\rightarrow$ [`docs/phase_f11_3_5_3_results.json:88`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json#L88) | **RECONCILED** (Strategy C) |

---

## 6. Return Aggregation Reconciliation

- **Authoritative Common Outcome Metric**: `EQUAL-WEIGHTED ARITHMETIC MEAN OF INDIVIDUAL SCHEME 1Y FORWARD GROSS NAV RETURNS`.
- All three strategies (A, B, C) operate on identical evaluation population ($N=5,713$ total scored schemes, $N=571$ selected in top/lowest decile), evaluate over identical forward window (`2024-02-01` to `2025-01-31`), and utilize identical forward NAV calculation math.

---

## 7. MDD Provenance Closure

| Metric Value | Strategy / Sort Basis | Correct Terminology | Exact Origin | Status |
| :--- | :--- | :--- | :--- | :--- |
| **16.83%** | Strategy A (Trailing Return) | `MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN` | [`docs/phase_f11_3_5_3_results.json:77`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json#L77) | **RECONCILED** |
| **0.11%** | Strategy B (Historical Volatility) | `MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN` | [`docs/phase_f11_3_5_3_results.json:83`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json#L83) | **RECONCILED** |
| **0.45%** | Strategy B (Downside Risk Sort) | `MEDIAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN` | [`docs/phase_f11_3_5_3_unseen_period_decision_value_report.md:89`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_unseen_period_decision_value_report.md#L89) | **RECONCILED AS MEDIAN COMPARATOR** |
| **1.26%** | Strategy C (Fund Quality) | `MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN` | [`docs/phase_f11_3_5_3_results.json:89`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_results.json#L89) | **RECONCILED** |

> [!NOTE]
> None of these metrics represent a portfolio equity curve path drawdown. They represent descriptive statistics of individual schemes selected by each strategy.

---

## 8. Current Freeze vs Historical Pre-Anchor Freeze

- **CURRENT PRODUCTION METHODOLOGY**: `FROZEN` (v1.0.0 composite weights 25/20/15/15/15/10 and scoring logic are strictly frozen).
- **HISTORICAL PRE-ANCHOR FREEZE**: `NOT PROVEN`. Repository commit history begins in May 2026. No pre-registered trial manifest prior to `2024-01-31` exists in the repository.
- **Formal Classification**: `RETROSPECTIVE POINT-IN-TIME BACKTESTING — PROSPECTIVE/PRE-REGISTERED STATUS NOT PROVEN`.

---

## 9. Claim Governance & Prohibited Terminology

The following terms are **strictly prohibited** in project reporting:
- *Predictive superiority*
- *Proven strategy*
- *Risk protection* / *Portfolio protection*
- *Causal risk reduction*
- *Alpha* / *Investor benefit*

**Permitted Wording**:
- *"Observed mean forward return under the specified retrospective point-in-time selection rule."*
- *"Mean individual-fund forward maximum drawdown among the selected schemes."*

---

## 10. Verification & Test Evidence

Dedicated test suite created at [`tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_provenance_closure.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_provenance_closure.py) covering all 13 required test gates.

- **Dedicated Test Results**: 13 Passed, 0 Failed.
- **Full Data Quality Regression Suite**: 440 Passed, 0 Failed.

---

## 11. Final Status Rule

`PHASE F.11.3.5.3.1.1.2.1 PASSED WITH LIMITATIONS`

All metrics have been fully traced, reconciled, or explicitly classified as unreconciled/unproven.
