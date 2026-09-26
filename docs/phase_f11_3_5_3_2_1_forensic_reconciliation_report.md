# PHASE F.11.3.5.3.2.1 — OOS STATISTICAL INTERPRETATION & MODEL SPECIFICATION RECONCILIATION REPORT

## A. Executive Status

- **Final Status**: `PHASE F.11.3.5.3.2.1 PASSED WITH LIMITATIONS`
- **Tests Passed**: 24 / 24 (`tests/data_quality/test_phase_f11_3_5_3_2_1_forensic_reconciliation.py`)
- **Historical Pre-Freeze Classification**: RETROSPECTIVE POINT-IN-TIME BACKTESTING — PROSPECTIVE/PRE-REGISTERED STATUS NOT PROVEN
- **Production Methodology**: UNCHANGED / 100% FROZEN

## B. Governance Verification

1. Verified [`ARCHITECTURE.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/ARCHITECTURE.md) and [`PRODUCT_SPEC.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/PRODUCT_SPEC.md).
2. Read F.11.3.5.3.2 validation script [`scripts/run_f11_3_5_3_2_unseen_validation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f11_3_5_3_2_unseen_validation.py), results JSON [`docs/phase_f11_3_5_3_2_results.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_2_results.json), and report [`docs/phase_f11_3_5_3_2_unseen_validation_report.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_2_unseen_validation_report.md).
3. Read MAR-governance reconciliation artifacts ([`metrics/risk.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/metrics/risk.py), MAR=0.0%).
4. Production Fund Quality scoring, weights (25/20/15/15/15/10), normalization, suitability, action logic, and portfolio rules remain 100% frozen.

## C. Population Waterfall Reconciliation

- **Stage 1 (Total Database Schemes)**: 17,507 schemes
- **Stage 2 (PIT Active Schemes $\le 2024-01-31$)**: 16,808 schemes
- **Stage 3 (Forward Reachable Schemes $> 2024-01-31$)**: 5,889 schemes
- **Stage 4 (Minimum History $\ge 20$ obs & Active in Jan 2024)**: 5,826 schemes
- **Stage 5 (Final Eligible Validation Population)**: 5,713 schemes

*Reconciliation Note*: From the governed F.12.3.1.2 dataset, 5,889 forward-reachable schemes are filtered down to 5,826 schemes by applying the minimum 20-observation PIT rule and recent activity in Jan 2024, and further reduced to 5,713 schemes by requiring $\ge 2$ forward observations extending through mid/late January 2025.

## D. Point-in-Time (PIT) Integrity Verification

- **Cutoff Date**: 2024-01-31
- **Future Leakage Audit**: PASSED. Zero future data leakage. All inputs to scoring (returns, volatility, downside deviation, drawdown, maturity) evaluated strictly on NAV observations dated $\le 2024-01-31$.

## E. Confidence-Dispersion Reconciliation

- **High Confidence ($\ge 0.99$)**: $N=5,130$ | Return Mean = 7.87% | **Return Std Dev = 6.90%** | MDD Mean = 6.78% | MDD Std Dev = 7.18%
- **Low Confidence ($< 0.99$)**: $N=583$ | Return Mean = 10.13% | **Return Std Dev = 6.22%** | MDD Mean = 8.88% | MDD Std Dev = 7.97%
- **Reconciled Contradiction**: High confidence schemes exhibited **HIGHER** return standard deviation (6.90%) than low confidence schemes (6.22%). The previous narrative summary incorrectly stated that high confidence exhibited lower return dispersion. High confidence exhibited lower dispersion only for Maximum Drawdown (7.18% vs 7.97%).
- **Specification Status**: Threshold 0.99 was introduced post-hoc in F.11.3.5.3.2 and is classified as **EXPLORATORY / POST-HOC**.

## F. Exact Regression Specification & Incremental $R^2$

All models estimated via OLS on $N=5,713$ schemes with dependent variable $y = \text{1Y Equal-Weighted Forward Gross NAV Return}$:

- **Model 0**: $y \sim 1$ | $R^2 = 0.000000$
- **Model 1**: $y \sim 1 + \text{trailing\_1y\_return}$ | $R^2 = 0.155483$
- **Model 2**: $y \sim 1 + \text{trailing\_1y\_return} + \text{volatility\_1y} + \text{downside\_mar0}$ | $R^2 = 0.380564$
- **Model 3**: $y \sim 1 + \text{trailing\_1y\_return} + \text{volatility\_1y} + \text{downside\_mar0} + \text{fq\_score}$ | $R^2 = 0.386438$
  - **FQ Score Beta**: $+0.935340$
  - **FQ Standard Error**: $0.126525$
  - **t-Statistic**: $+7.3925$
  - **p-Value**: $p < 0.001$ (Classical IID OLS t-test on $df=5,708$)
- **Exact Incremental $R^2$**: $0.386438 - 0.380564 = \mathbf{+0.005874}$ (0.59 percentage points).

## G. FQ Component Overlap & Construct Circularity Assessment

- **Component Mapping**:
  - Trailing 1Y Return: Present in Model 2 $\rightarrow$ Direct Overlap (50% score weight).
  - Historical Volatility: Present in Model 2 $\rightarrow$ Direct Overlap (50% score weight via $1/(1+\text{vol})$).
  - Downside Deviation: Present in Model 2 $\rightarrow$ Conceptual Overlap.
- **Classification**: **Classification B** — Incremental explanatory association demonstrated, but independent information NOT established due to component circularity (Fund Quality is constructed directly from trailing return and volatility).

## H. Strategy Cohorts & Overlap Reconciliation

- **Selected Cohort Size**: $N=571$ schemes for all deciles (Top 10% of $N=5,713$).
- **Strategy A vs Strategy C Overlap**: **536 shared schemes** out of 571 (Jaccard similarity **0.8845**).
- **Corrected Cohort Claim**: Strategy C is **NOT** a "materially distinct cohort" from Strategy A. It is a **93.87% overlapping cohort** with 35 unique fund substitutions (**11.55% cohort non-overlap**).
- **Cohort Membership Turnover Proxy**: 11.55% (35 / 571). It represents cohort membership drift, **NOT investor portfolio transaction turnover**.

## I. Claim-Language Audit & Corrections

1. **Dispersion Claim**: Corrected to state high confidence schemes exhibit higher return standard deviation (6.90% vs 6.22%).
2. **Cohort Distinctness Claim**: Corrected to state Strategy C is 88.45% similar to Strategy A (536/571 shared).
3. **Incremental R² Claim**: Characterized as modest (+0.005874 / 0.59%), reflecting non-linear composite term fitting rather than independent fundamental discovery.
4. **Prohibited Terms Enforced**: All terms (`predicts`, `predictive superiority`, `risk protection`, `causal`, `investor benefit`, `alpha`) strictly removed/prohibited.

## J. Final Required Answers (Section 19 Compliance)

1. **Was the confidence-dispersion conclusion correct?**
   **NO.** Corrected: High confidence exhibited HIGHER return Std Dev (6.90% vs 6.22%).
2. **What exactly is the +0.005874 incremental R²?**
   The exact difference between Model 3 $R^2$ (0.386438) and Model 2 $R^2$ (0.380564).
3. **Does it establish independent information from Fund Quality?**
   **NO.** FQ is constructed directly from trailing return and volatility, creating mathematical component circularity.
4. **Is the +0.935340 FQ beta reproducible?**
   **YES.** Beta $+0.935340$ ($SE = 0.126525$, $t=7.39$) exactly reproduced.
5. **What statistical inference method produced p < 0.001?**
   Classical IID OLS t-test on $N=5,713$ ($df=5,708$).
6. **Were Strategies A/B/C constructed without future information?**
   **YES.** Evaluated strictly on PIT data dated $\le 2024-01-31$.
7. **Is the 11.55% figure portfolio turnover or cohort-membership turnover?**
   **COHORT MEMBERSHIP TURNOVER PROXY.**
8. **Is the A-vs-C cohort actually materially different or largely overlapping?**
   **HIGHLY OVERLAPPING** (536 out of 571 funds shared, Jaccard 0.8845).
9. **Are the 12.23%, 4.34%, and 11.85% returns calculated under one identical outcome definition?**
   **YES.** Equal-weighted arithmetic mean of 1Y forward gross NAV returns.
10. **Are the MDD figures calculated under one identical outcome definition?**
    **YES.** Mean individual-fund forward maximum drawdown.
11. **Is the quintile relationship merely observed association or evidence of prediction?**
    Retrospective observed association in a single 1Y forward period.
12. **Which findings are genuinely supported?**
    PIT calculation integrity, 536/571 cohort overlap, exact regression beta $+0.935340$ and $+0.005874$ $R^2$ increment.
13. **Which findings remain unproven?**
    Independent information, causal risk protection, investor economic benefit, multi-regime predictive stability.
14. **Does anything justify a production methodology change?**
    **NO AUTOMATIC PRODUCTION CHANGE.**
