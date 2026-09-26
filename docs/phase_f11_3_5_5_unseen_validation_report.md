# PHASE F.11.3.5.5 — GENUINE UNSEEN-PERIOD DECISION-VALUE VALIDATION REPORT

## 1. Executive Summary

This report evaluates whether the frozen Fund Quality framework provides measurable decision value when applied to a genuinely unseen historical period (Anchor date `2024-01-31`, Forward period `2024-02-01` to `2025-01-31`). All validation rules were frozen in a machine-readable manifest (`docs/phase_f11_3_5_5_validation_manifest.json`) prior to outcome interpretation.

**Core Findings & Decision-Value Assessment:**
1. **Positive Unseen Association:** Fund Quality Score exhibited a strong positive Spearman rank correlation ($\rho = \mathbf{+0.5098}$) with 1Y forward returns in the 2024–2025 unseen expansion period.
2. **Strategy C (FQ) Did Not Beat Strategy A (Trailing Return):** Strategy C (Top 10% FQ) delivered a mean forward return of **11.85%**, which did NOT exceed Strategy A (Top 10% Trailing Return) at **12.23%**. Strategy C and Strategy A had an **88.45% cohort overlap** (536 shared schemes out of 571).
3. **Incremental Explanatory Power:** Adding FQ to Model 2 (which already contains trailing return, volatility, and downside deviation) yielded a modest positive incremental $R^2$ of **+0.005874** ($0.59$ percentage points, $F$-stat significant at $p < 0.0001$).
4. **No Independent Information (Mathematical Circularity):** Because Fund Quality Score is constructed 50% from reciprocal volatility and 50% from trailing return, the $+0.005874$ increment reflects non-linear composite score fitting rather than novel fundamental information discovery.
5. **Quintile Monotonicity:** Fund Quality quintiles exhibited perfect monotonic ordering ($Q1: 12.02\% > Q2: 10.18\% > Q3: 8.07\% > Q4: 7.10\% > Q5: 3.17\%$).
6. **Forward Drawdowns:** Mean individual-fund forward MDD for Strategy C (**16.80%**) was virtually identical to Strategy A (**16.83%**).

---

## 2. Validation Objective

Determine whether the frozen Fund Quality v1.0 framework produces decision-relevant differences in outcomes during a genuinely unseen out-of-sample forward period (2024-2025), maintaining 100% field-level explainability and point-in-time safety.

---

## 3. Validation Manifest

- **Manifest Path:** [`docs/phase_f11_3_5_5_validation_manifest.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_5_validation_manifest.json)
- **Manifest Version:** `F.11.3.5.5-v1.0`
- **Anchor Date:** `2024-01-31`
- **Forward Period:** `2024-02-01` to `2025-01-31`
- **Dataset Version:** `F.12.3.1.2 Reconciled Baseline Dataset`
- **Methodology Version:** `Frozen Production Fund Quality v1.0`

---

## 4. Dataset and Provenance

- **Database:** `db/backfill_f12_2.db` (Table: `normalized_nav_records`)
- **Total Unique Canonical Schemes in DB:** 7,858
- **Date Range:** 2018-01-01 to 2025-02-15

---

## 5. Anchor Population

Reconciled against F.12.3.1.2 baseline anchor cohort:
- **Baseline Anchor Population:** **5,874 schemes**
- **Forward-Reachable Population:** **5,750 schemes**
- **Forward-Unavailable Population:** **124 schemes**

---

## 6. Population Waterfall

`5,874 BASELINE ANCHOR COHORT`
$\rightarrow$ `5,750 FORWARD NAV AVAILABLE` (124 Unavailable dropped due to missing forward NAVs)
$\rightarrow$ `5,713 FINAL OUTCOME POPULATION` (37 dropped due to $< 20$ PIT daily NAV observations)
$\rightarrow$ `571 DECILE COHORT SIZE` ($N_{\text{decile}} = \lfloor 5,713 / 10 \rfloor$)

---

## 7. Point-in-Time Leakage Audit

- **Audit Rule:** `observation_date <= 2024-01-31` for all scoring inputs.
- **Max Observation Date Checked:** `2024-01-31`
- **Future Information Leakage Detected:** **NO** (0 instances).

---

## 8. Fund Quality Score Reconstruction

$$\text{Fund Quality Score} = 0.5 \times \left( \frac{1}{1 + \text{Volatility}_{1Y}} \right) + 0.5 \times \min(1.0, \max(0.0, \text{Trailing Return}_{1Y}))$$
All 5,713 eligible schemes reconstructed cleanly with zero score variance against production implementation.

---

## 9–11. Strategy Performance Summary (A, B, C, B-DOWN)

- **Strategy A:** Top 10% Trailing 1Y Return
- **Strategy B:** Lowest 10% Historical Volatility
- **Strategy C:** Top 10% Fund Quality Score
- **Comparator B-DOWN (Research-Only):** Lowest 10% Downside Deviation (MAR = 0%)

| Strategy | Selection Metric | Decile Cohort N | Mean Forward 1Y Return | Mean Forward MDD | Cohort Overlap with Strategy A | Jaccard Similarity vs A | Membership Turnover Proxy |
|---|---|---|---|---|---|---|---|
| **Strategy A** | Top 10% Trailing Return | 571 | **12.23%** | 16.83% | 571 (100%) | 1.0000 | 0.00% |
| **Strategy B** | Lowest 10% Volatility | 571 | **4.34%** | 0.11% | 0 (0%) | 0.0000 | 100.00% |
| **Strategy C** | Top 10% Fund Quality | 571 | **11.85%** | 16.80% | 536 (93.9%) | **0.8845** | **6.13%** |
| **Comparator B-DOWN** | Lowest 10% Downside (MAR=0%) | 571 | **5.03%** | 0.10% | 0 (0%) | 0.0000 | 100.00% |

---

## 12. Cohort Overlap Analysis

Strategy C (FQ) and Strategy A (Trailing Return) shared **536 schemes out of 571** ($88.45\%$ overlap, Jaccard $= 0.8845$). The 35 non-overlapping schemes in Strategy C were lower-volatility funds with slightly lower trailing returns, which reduced Strategy C's forward return by 0.38 percentage points relative to Strategy A.

---

## 13–14. Forward Return & Drawdown Results

- **Mean Forward 1Y Return:** Strategy A ($12.23\%$) > Strategy C ($11.85\%$) > Comparator B-DOWN ($5.03\%$) > Strategy B ($4.34\%$).
- **Mean Forward MDD:** Strategy C ($16.80\%$) vs Strategy A ($16.83\%$). Lower volatility strategies (Strategy B: $0.11\%$, B-DOWN: $0.10\%$) had dramatically lower drawdowns due to fixed-income / debt fund concentration.

---

## 15. Nested Regression Results ($N = 5,713$)

- **M0:** `FwdRet ~ Intercept` ($R^2 = 0.000000$)
- **M1:** `FwdRet ~ Intercept + TrailingReturn` ($R^2 = 0.155483$)
- **M2:** `FwdRet ~ Intercept + TrailingReturn + Volatility + DownsideMAR0` ($R^2 = 0.380564$)
- **M3:** `FwdRet ~ Intercept + TrailingReturn + Volatility + DownsideMAR0 + FundQuality` ($R^2 = \mathbf{0.386438}$)

**Incremental R² (M3 vs M2):** **+0.005874**
- **FQ Coefficient ($\beta_3$):** **+0.935340**
- **Standard Error:** $0.12604$
- **t-statistic:** **+7.421** ($p < 0.0001$)
- **Degrees of Freedom:** $5,708$

---

## 16. Quintile Results

| Quintile | FQ Score Range | Cohort Size N | Mean Forward Return | Mean Forward MDD | Monotonicity Check |
|---|---|---|---|---|---|
| **Q1 (Highest FQ)** | Top 20% | 1,142 | **12.02%** | 16.50% | Base |
| **Q2** | 60%–80% | 1,142 | **10.18%** | 14.20% | $Q1 > Q2$ (PASS) |
| **Q3** | 40%–60% | 1,142 | **8.07%** | 11.10% | $Q2 > Q3$ (PASS) |
| **Q4** | 20%–40% | 1,142 | **7.10%** | 8.40% | $Q3 > Q4$ (PASS) |
| **Q5 (Lowest FQ)** | Bottom 20% | 1,145 | **3.17%** | 3.20% | $Q4 > Q5$ (PASS) |

*Result:* **Perfect Monotonic Ordering** ($12.02\% > 10.18\% > 8.07\% > 7.10\% > 3.17\%$).

---

## 17. Confidence Analysis

Confidence is calculated strictly as $\min(1.0, \text{observation\_count} / 250.0)$. It reflects history completeness, not return direction or risk prediction.

---

## 18. Decision-Value Comparison Summary

In this unseen period, Fund Quality produced outcomes closely matching Trailing Return (11.85% vs 12.23%) with high cohort overlap (88.45%). FQ provided monotonic quintile separation (Q1 12.02% vs Q5 3.17%), but did **not** outperform simple trailing-return selection on top-decile return.

---

## 19–20. Explainability & Provenance Audit

- **100% Traceability Demonstrated:** Reconstructed metric inputs, components, final score, and forward outcomes for representative schemes in [`phase_f11_3_5_5_results.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_5_results.json).
- **Explanation Objects:** Structured 12-field explanation objects built for all major metrics.

---

## 21–22. Lifecycle Safety & Statistical Limitations

- **No Future Leakage:** Verified observation date bounds.
- **Clustered Observations:** OLS standard errors assume independent errors; mutual funds in the same category/AMC exhibit correlated returns.
- **Component Circularity:** FQ inputs are already present in Model 2.

---

## 23–25. Claim Governance & Negative Findings

| Claim ID | Statement | Final Status | Rationale |
|---|---|---|---|
| A | FQ had a positive relationship in this unseen period. | **SUPPORTED** | Spearman $\rho = +0.5098$, regression $\beta = +0.935340$. |
| B | FQ predicted future returns. | **NOT SUPPORTED** | Association does not imply predictive certainty or causality. |
| C | FQ added incremental explanatory association. | **SUPPORTED WITH LIMITATIONS** | Incremental $R^2 = +0.005874$ over Model 2. |
| D | FQ added independent information. | **NOT SUPPORTED** | Component circularity with Model 2 predictors. |
| E | FQ beat trailing-return selection. | **NOT SUPPORTED** | Strategy C (11.85%) did NOT beat Strategy A (12.23%). |
| F | FQ reduced future drawdown. | **NOT SUPPORTED** | Strategy C MDD (16.80%) virtually identical to Strategy A (16.83%). |
| G | FQ produced economic benefit. | **UNRESOLVED** | Fees, taxes, and switching costs not evaluated. |
| H | FQ is robust across market regimes. | **NOT SUPPORTED** | Single-period result cannot establish multi-regime robustness. |
| I | FQ should change production Buy/Sell decisions. | **RESEARCH-ONLY** | Production scoring methodology remains frozen. |

---

## 26–29. Final Status Declaration

**FINAL STATUS: PASSED WITH LIMITATIONS**

*Rationale:* Manifest was frozen prior to outcome interpretation; anchor population ($5,874$), forward reachable ($5,750$), and outcome population ($5,713$) reconcile 100%; point-in-time safety is verified; score, strategy, regression, and quintile calculations are fully reproducible; field-level explainability and provenance are demonstrated; negative findings are preserved; all 11 unit tests pass; production scoring methodology remains unchanged.
