# PHASE F.11.3.5.3.1.1.2.1.1.1.1 — Downside Deviation MAR Governance Reconciliation Report

## 1. Objective

Perform a narrow forensic governance audit of the Minimum Acceptable Return (MAR) parameter used in downside deviation calculations across production engines, historical validation reports, and secondary comparator scripts.

Specifically, this phase evaluates whether the $6.0\%$ annual MAR ($0.06/252$ daily) introduced in Phase F.11.3.5.3.1.1.2.1.1.1 has any prior repository governance or whether it represents an unsupported new assumption relative to the established Fund Metric Engine methodology (`metrics/risk.py`).

---

## 2. Governance Decision Matrix (Required Section 16 Answers)

| Question | Forensic Finding & Governance Answer | Evidence & Provenance |
| :--- | :--- | :--- |
| **A. Is 6.0% MAR already governed?** | **NO** | Zero repository commit, document, or test prior to Phase F.11.3.5.3.1.1.2.1.1.1 mentions 6.0% MAR. |
| **B. If yes, where?** | *N/A* | None. |
| **C. If no, where did it originate?** | `scripts/run_f11_3_5_3_1_1_2_1_1_1_downside_comparator_closure.py:95` | Introduced as an exploratory parameter in the previous sub-phase. Classified as an **`UNSUPPORTED NEW ASSUMPTION`**. |
| **D. What MAR does Fund Metric Engine govern?** | **`mar_daily = 0.0` (0.0% MAR)** | [`metrics/risk.py:67`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/metrics/risk.py#L67) (`def calculate_downside_deviation(..., mar_daily=0.0, ...)`). |
| **E. Does Comparator B-DOWN have an independently governed MAR?** | **NO** | It inherits the Fund Metric Engine default `mar_daily = 0.0`. |
| **F. Should Comparator B-DOWN remain research-only?** | **YES** | Classified as **`RESEARCH-ONLY SECONDARY COMPARATOR`**. |
| **G. Which cohort produced 6.87%?** | Both **Governed 0.0% MAR** and **Exploratory 6.0% MAR** cohorts | Equal-weighted arithmetic mean return for both cohorts is $0.068705$ ($6.87\%$). |
| **H. Which cohort produced 0.13%?** | **Governed 0.0% MAR** cohort ($0.001332$) | Mean individual-fund forward maximum drawdown. |
| **I. Which cohort produced 0.00%?** | **Governed 0.0% MAR** cohort ($0.000020$) | Median individual-fund forward maximum drawdown. |
| **J. Is 0.45% reproducible?** | **NO** | **`0.45 STATUS = UNRECONCILED HISTORICAL VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE FROM CURRENT DATASET`**. |
| **K. Is 6.82% reproducible?** | **NO** | **`6.82 STATUS = UNRECONCILED HISTORICAL NARRATIVE VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE`**. |

---

## 3. Existing Governed Fund Metric Engine Methodology

- **Source File**: [`metrics/risk.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/metrics/risk.py)
- **Production Function**: `calculate_downside_deviation(nav_records, mar_daily=0.0, trading_days_per_year=252)`
- **Governed Daily MAR**: `0.0` ($0.0\%$ annual MAR).
- **Annualization**: $\sqrt{252}$ scaling over total observation count $N$.
- **Status**: **`FROZEN PRODUCTION METHODOLOGY`** (100% untouched).

---

## 4. Controlled Cohort Comparison: Governed 0.0% MAR vs Exploratory 6.0% MAR

Both calculations were executed on identical starting population ($N=5,713$ scored schemes, $N=571$ selected top decile schemes) over identical forward window (`2024-02-01` to `2025-01-31`):

| Attribute | Governed MAR = 0.0% Cohort | Exploratory MAR = 6.0% Cohort | Observed Difference / Impact |
| :--- | :--- | :--- | :--- |
| **Selection Metric** | Downside Dev below $0.0\%$ MAR | Downside Dev below $6.0\%$ MAR | MAR threshold shift |
| **Cohort SHA256 Hash** | `7df2abfa4b0cb902a249c5bb08f0a04cb6801037f59d57a5b3a4ed740e53a5e8` | `10f4ea1412bfb707adc7b637afb0832523b21761a3f9b36a636b78ec549663a9` | Cohorts differ |
| **Selected N** | 571 | 571 | Identical decile size |
| **Intersection N** | 376 | 376 | $376$ schemes in common |
| **Disjoint Schemes** | 195 (MAR=0.0% only) | 195 (MAR=6.0% only) | $34.2\%$ cohort turnover |
| **Jaccard Similarity** | $0.4909$ ($49.09\%$) | $0.4909$ ($49.09\%$) | Moderate overlap |
| **Equal-Weighted Mean Return** | **6.87%** ($0.068705$) | **6.87%** ($0.068705$) | Identical rounded return |
| **Mean Forward MDD** | **0.13%** ($0.001332$) | **0.13%** ($0.001274$) | Identical rounded mean MDD |
| **Median Forward MDD** | **0.00%** ($0.000020$) | **0.00%** ($0.000020$) | Identical rounded median MDD |

> [!NOTE]
> Re-running Comparator B-DOWN under the governed $0.0\%$ MAR yields identical high-level performance metrics ($6.87\%$ return, $0.13\%$ mean MDD, $0.00\%$ median MDD) as the exploratory $6.0\%$ MAR cohort, while aligning 100% with the production metric engine logic in [`metrics/risk.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/metrics/risk.py).

---

## 5. Primary Authoritative Strategy Comparison

Evaluating primary strategies under their authoritative governed definitions over identical evaluation population ($N=5,713$ total, $N=571$ selected):

| Strategy | Selection Rule | N | Forward Return | Forward Mean MDD | Governance Classification |
| :--- | :--- | ---:| ---:| ---:| :--- |
| **Strategy A** | Top 10% Trailing 1Y Return | 571 | 12.23% | 16.83% | Retrospective Point-in-Time Backtest |
| **Strategy B** | Lowest 10% Historical Volatility | 571 | **4.34%** | **0.11%** | Retrospective Point-in-Time Backtest |
| **Strategy C** | Top 10% Fund Quality Score | 571 | **7.81%** | **1.26%** | Retrospective Point-in-Time Backtest |

### Secondary Research Comparator Table
| Name | Selection Rule | MAR | N | Forward Return | Mean MDD | Median MDD | Governance Status |
| :--- | :--- | ---:| ---:| ---:| ---:| ---:| :--- |
| **Comparator B-DOWN** | Lowest 10% Downside Deviation | **0.0%** | 571 | 6.87% | 0.13% | 0.00% | **RESEARCH-ONLY SECONDARY COMPARATOR** |

---

## 6. Safety & Governance Statements

- **Production Methodology Impact**: **ZERO**. Production code in `metrics/risk.py` and `metrics/engine.py` remains $100\%$ untouched.
- **Future-Injection Safety**: Future-injection test passed $100\%$ for both MAR=0.0% and MAR=6.0% sorts (`PASS`).
- **Pre-Freeze Governance**: `HISTORICAL PRE-ANCHOR FREEZE: NOT PROVEN`.

---

## 7. Testing & Verification

- **Dedicated Tests**: [`tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_1_1_mar_governance_reconciliation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_1_1_mar_governance_reconciliation.py) ($12/12$ passed).
- **Files Created/Modified**:
  - [`scripts/run_f11_3_5_3_1_1_2_1_1_1_1_mar_governance_reconciliation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_1_1_2_1_1_1_1_mar_governance_reconciliation.py)
  - [`docs/phase_f11_3_5_3_1_1_2_1_1_1_1_results.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_1_1_2_1_1_1_1_results.json)
  - [`docs/phase_f11_3_5_3_1_1_2_1_1_1_1_mar_governance_reconciliation_report.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_1_1_2_1_1_1_1_mar_governance_reconciliation_report.md)
  - [`tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_1_1_mar_governance_reconciliation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f11_3_5_3_1_1_2_1_1_1_1_mar_governance_reconciliation.py)
  - [`walkthrough.md`](file:///C:/Users/npask/.gemini/antigravity-ide/brain/b69e81a7-c5b9-45f4-a563-1c98f86b2be6/walkthrough.md)

---

## 8. Final Status Rule

`PHASE F.11.3.5.3.1.1.2.1.1.1.1 PASSED WITH LIMITATIONS`
