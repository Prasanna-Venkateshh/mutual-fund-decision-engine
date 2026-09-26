# PHASE F.11.3.5.3.1.1.2.1.1.1 — Downside Comparator MDD & 6.82% Exact Calculation Closure Report

## 1. Objective

Perform a narrow forensic closure of the remaining unresolved historical downside-risk comparator evidence.

This report establishes the exact 571-scheme downside-risk comparator cohort, determines the exact origin and calculation of $6.87\%$, classifies $6.82\%$ and $0.45\%$, prevents cross-contamination with Governed Strategy B, and verifies future-injection safety without changing production Fund Quality scoring, weights, normalization, suitability, portfolio logic, or action logic.

---

## 2. Exact Comparator B-DOWN Definition

- **Comparator Name**: `COMPARATOR B-DOWN` (Secondary Historical Comparator — Not Strategy B).
- **Governed Metric**: `LOWEST 10% HISTORICAL DOWNSIDE DEVIATION`.
- **Selection Variable**: Annualized Downside Deviation below MAR $6.0\%$ ($0.06 / 252$ daily benchmark return).
- **Observation Window**: Trailing 250 observations prior to anchor date `2024-01-31`.
- **Sort Direction**: Ascending (Lowest Risk First).
- **Universe Denominator**: $N = 5,713$ total scored schemes.
- **Selected Cohort Size**: $N = 571$ schemes ($10\%$ of $5,713$, integer truncated).
- **Cohort SHA256 Hash**: `7df2abfa4b0cb902a249c5bb08f0a04cb6801037f59d57a5b3a4ed740e53a5e8`.
- **Executable Selection Line**: [`scripts/run_f11_3_5_3_1_1_2_strategy_governance_reconciliation.py:289`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_1_1_2_strategy_governance_reconciliation.py#L289) (`idx_b_down = np.argsort(down_a)[:n_top]`).

---

## 3. 571-Scheme Cohort Reconstruction & Overlap

- **Scored Universe**: $N = 5,713$.
- **Selected Cohort N**: $N = 571$.
- **Intersection with Governed Strategy B (Volatility Sort)**: $N = 475$ schemes.
- **Volatility-Only Schemes**: $N = 96$.
- **Downside-Only Schemes**: $N = 96$.
- **Jaccard Similarity**: $0.7121$ ($71.21\%$).

---

## 4. Return Provenance (6.87% vs 6.82%)

| Figure | Status & Classification | Raw Unrounded Value | Formula & Aggregation | Exact Origin |
| :--- | :--- | ---:| :--- | :--- |
| **6.87%** | **`6.87% = RECONCILED SECONDARY COMPARATOR RETURN`** | $0.068705$ | Equal-weighted arithmetic mean of 1Y forward gross NAV returns | [`scripts/run_f11_3_5_3_1_1_2_strategy_governance_reconciliation.py:290`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_1_1_2_strategy_governance_reconciliation.py#L290) $\rightarrow$ [`docs/phase_f11_3_5_3_1_1_2_results.json:37`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_1_1_2_results.json#L37) |
| **6.82%** | **`UNRECONCILED HISTORICAL NARRATIVE VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE`** | *N/A* | None | Narrative Table 29 of [`docs/phase_f11_3_5_3_unseen_period_decision_value_report.md:89`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_unseen_period_decision_value_report.md#L89) |

### 4.1 Discrepancy Reconciliation (6.82% vs 6.87%)
- **Numerical Difference**: $0.05$ percentage points ($6.87\% - 6.82\%$).
- **Classification**: `6.82% VS 6.87% = UNRESOLVED DISCREPANCY`.
- **Governance Finding**: Ordinary mathematical rounding of $6.87\%$ does not produce $6.82\%$. $6.82\%$ cannot be reproduced by any executable code on the $5,713$-scheme population and is classified as an unreproducible historical narrative artifact rather than math rounding.

---

## 5. MDD Reconstruction & Provenance (0.13%, 0.00%, 0.45%)

Using the exact 571-scheme cohort of Comparator B-DOWN over the forward window `2024-02-01` to `2025-01-31`:

| Metric | Raw Unrounded Value | Display Formatted | Metric Classification & Status |
| :--- | ---:| ---:| :--- |
| **Mean Forward MDD** | $0.001332$ | **0.13%** | **`0.13% = RECONCILED COMPARATOR B-DOWN MEAN MDD`** (`MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN`) |
| **Median Forward MDD** | $0.000020$ | **0.00%** | **`0.00% = RECONCILED COMPARATOR B-DOWN MEDIAN MDD`** (`MEDIAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN`) |
| **Narrative 0.45% MDD** | *N/A* | **0.45%** | **`0.45 STATUS = UNRECONCILED HISTORICAL VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE FROM CURRENT DATASET`** |

> [!IMPORTANT]
> The exact $571$-scheme downside cohort has mean MDD $0.13\%$ and median MDD $0.00\%$. The narrative $0.45\%$ figure in Table 29 cannot be reproduced from the current dataset and is retained as an unproven historical narrative artifact.

---

## 6. Prevention of Cross-Contamination with Governed Strategy B

- **Governed Strategy B**: Lowest 10% Historical Volatility $\rightarrow$ Return = **4.34%**, Mean MDD = **0.11%**.
- **Comparator B-DOWN**: Lowest 10% Historical Downside Deviation $\rightarrow$ Return = **6.87%**, Mean MDD = **0.13%**, Median MDD = **0.00%**.
- **Cross-Contamination Verification**: `NO CROSS-CONTAMINATION DETECTED` (Pass).

---

## 7. Primary Authoritative Comparison vs Secondary Comparators

### Primary Comparison (Governed Definitions)
| Strategy | Selection Rule | N | Forward Return | Forward Mean MDD | Governance Classification |
| :--- | :--- | ---:| ---:| ---:| :--- |
| **Strategy A** | Top 10% Trailing 1Y Return | 571 | 12.23% | 16.83% | Retrospective Point-in-Time Backtest |
| **Strategy B** | Lowest 10% Historical Volatility | 571 | **4.34%** | **0.11%** | Retrospective Point-in-Time Backtest |
| **Strategy C** | Top 10% Fund Quality Score | 571 | **7.81%** | **1.26%** | Retrospective Point-in-Time Backtest |

### Secondary Comparators Table
| Name | Selection Rule | N | Forward Return | Forward Mean MDD | Forward Median MDD | Governance Status |
| :--- | :--- | ---:| ---:| ---:| ---:| :--- |
| **Comparator B-DOWN** | Lowest 10% Historical Downside Deviation | 571 | 6.87% | 0.13% | 0.00% | **SECONDARY COMPARATOR — NOT GOVERNED STRATEGY B** |

---

## 8. Future-Data Safety Verification

A future-injection invariance test was executed by mutating forward outcomes with $10.0\times$ random noise.

- **Comparator B-DOWN Membership Invariant**: `TRUE` (Pass).

---

## 9. Testing & Deliverables

- **Dedicated Tests**: [`tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_1_downside_comparator_closure.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_1_downside_comparator_closure.py) ($12/12$ passed).
- **Files Created/Modified**:
  - [`scripts/run_f11_3_5_3_1_1_2_1_1_1_downside_comparator_closure.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_1_1_2_1_1_1_downside_comparator_closure.py)
  - [`docs/phase_f11_3_5_3_1_1_2_1_1_1_results.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_1_1_2_1_1_1_results.json)
  - [`docs/phase_f11_3_5_3_1_1_2_1_1_1_downside_comparator_closure_report.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_1_1_2_1_1_1_downside_comparator_closure_report.md)
  - [`tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_1_downside_comparator_closure.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_1_downside_comparator_closure.py)
  - [`walkthrough.md`](file:///C:/Users/npask/.gemini/antigravity-ide/brain/b69e81a7-c5b9-45f4-a563-1c98f86b2be6/walkthrough.md)

---

## 10. Final Status Rule

`PHASE F.11.3.5.3.1.1.2.1.1.1 PASSED WITH LIMITATIONS`
