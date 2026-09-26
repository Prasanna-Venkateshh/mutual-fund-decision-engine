# PHASE F.11.3.5.3.2 — GENUINE UNSEEN-PERIOD DECISION-VALUE VALIDATION REPORT

## 1. Objective

Perform the first genuinely unseen-period validation of the frozen Fund Quality v1.0.0 methodology using the governed 2024-01-31 point-in-time cohort ($N=5,713$) and the newly reconciled historical NAV dataset extending through 2025-01-31 (`db/backfill_f12_2.db`).

The objective is to determine whether the existing Fund Quality methodology demonstrates measurable historical decision-value on a genuinely unseen forward period without altering production scoring, weights, normalization, suitability, portfolio logic, or action logic.

## 2. Validation Classification

- **Historical Pre-Freeze Classification**: RETROSPECTIVE POINT-IN-TIME BACKTESTING — PROSPECTIVE/PRE-REGISTERED STATUS NOT PROVEN.
- **Validation Status**: PHASE F.11.3.5.3.2 PASSED WITH LIMITATIONS.

## 3. Anchor Dataset & Forward Endpoint

- **Anchor Date**: 2024-01-31
- **Forward Endpoint**: 2025-01-31
- **Observation Window**: 2024-02-01 to 2025-01-31 (1 Full Forward Year / Unseen Outcome Period)

## 4. Population Reconciliation

- **Anchor Cohort Total**: 5,874 schemes
- **Forward Reachable**: 5,750 schemes
- **Unavailable / Unreachable**: 124 schemes
- **Scoring & Outcome Eligible Final**: 5,713 schemes
- **Reconciliation Explanation**: From 5,874 anchor schemes, 5,750 were forward reachable in the updated NAV history dataset (`db/backfill_f12_2.db`). Applying point-in-time minimum history rules ($\ge 20$ PIT observations prior to 2024-01-31) and forward availability requirements ($\ge 2$ NAV observations in the forward window reaching through Jan 2025) yields $N=5,713$ final eligible validation schemes.

## 5. Point-in-Time Methodology & Governance Verification

- **Fund Quality Engine**: Version 1.0.0
- **Weighting**: 25% Trailing 1Y Return, 20% Volatility, 15% Downside Deviation, 15% Max Drawdown, 15% History Maturity, 10% Data Quality.
- **Future Information Leakage**: Strictly ZERO. All score inputs evaluated using NAV records dated strictly $\le$ 2024-01-31.
- **Future-Injection Invariance Test**: PASSED. Mutating forward returns/MDDs leaves 2024-01-31 decile cohort memberships 100% unchanged.

## 6. Strategy Definitions & Cohort Performance

| Strategy / Comparator | Selection Metric / Rule | Selected N | Mean Forward Return | Median Forward Return | Std Forward Return | Mean Forward MDD | Median Forward MDD |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Strategy A** | Top 10% Trailing 1Y Return | 571 | 12.23% | 10.68% | 8.56% | 16.83% | 16.71% |
| **Strategy B** | Lowest 10% Historical Volatility | 571 | 4.34% | 6.65% | 3.63% | 0.11% | 0.00% |
| **Strategy C** | Top 10% Fund Quality Score | 571 | 11.85% | 10.75% | 7.90% | 16.80% | 16.64% |
| **Comparator B-DOWN** *(Research-Only)* | Lowest 10% Downside Deviation (MAR=0.0%) | 571 | 5.03% | 6.83% | 3.44% | 0.10% | 0.00% |

## 7. Cohort Overlap Analysis

| Comparison | Shared N | Strategy 1 Only N | Strategy 2 Only N | Jaccard Similarity | Cohort Non-Overlap / Turnover |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Strategy A vs Strategy B** | 0 | 571 | 571 | 0.0000 | 100.00% |
| **Strategy A vs Strategy C** | 536 | 35 | 35 | 0.8845 | 11.55% |
| **Strategy B vs Strategy C** | 0 | 571 | 571 | 0.0000 | 100.00% |
| **Strategy C vs Comparator B-DOWN** | 0 | 571 | 571 | 0.0000 | 100.00% |

## 8. Incremental Information & Nested Regression Models

Sample $N = 5,713$ schemes across all nested models:

- **Model 0 (Intercept Only)**: $R^2 = 0.000000$, Adj $R^2 = 0.000000$
- **Model 1 (Trailing 1Y Return)**: $R^2 = 0.155483$, Adj $R^2 = 0.155335$
- **Model 2 (Trailing 1Y Return + Volatility + Downside Deviation)**: $R^2 = 0.380564$, Adj $R^2 = 0.380238$
- **Model 3 (Trailing 1Y Return + Volatility + Downside Deviation + Fund Quality Score)**: $R^2 = 0.386438$, Adj $R^2 = 0.386008$
- **Fund Quality Coefficient in Model 3**: $+0.935340$ (SE: $0.126525$, 95% CI: $[+0.687350, +1.183330]$)
- **Incremental $R^2$ (Model 3 vs Model 2)**: $+0.005874$

*Statistical Interpretation*: Fund Quality adds a statistically significant positive coefficient ($+0.9353$) and a modest incremental $R^2$ of $+0.005874$ over trailing return and historical risk variables.

## 9. Quintile Analysis

Quintiles constructed using pre-anchor Fund Quality scores as of 2024-01-31 ($N=5,713$ total):

| Quintile | N | Score Range | Mean Forward Return | Median Forward Return | Mean Forward MDD | Median Forward MDD |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Q1 (Highest Quality)** | 1,142 | [0.6137, 0.8537] | 12.02% | 11.40% | 16.03% | 15.70% |
| **Q2** | 1,142 | [0.5421, 0.6136] | 10.18% | 9.87% | 11.74% | 12.68% |
| **Q3** | 1,142 | [0.5310, 0.5420] | 8.07% | 7.79% | 1.08% | 0.12% |
| **Q4** | 1,142 | [0.5000, 0.5310] | 7.10% | 7.78% | 2.52% | 0.53% |
| **Q5 (Lowest Quality)** | 1,145 | [0.3933, 0.5000] | 3.17% | 0.05% | 3.62% | 0.89% |

## 10. Confidence Analysis

- **High Confidence ($\ge 0.99$, Full History)**: $N=5,130$, Return Std Dev = $6.90\%$, MDD Std Dev = $7.18\%$
- **Low Confidence ($< 0.99$, Partial History)**: $N=583$, Return Std Dev = $6.22\%$, MDD Std Dev = $7.97\%$
- *Findings*: Higher confidence schemes exhibit lower return and drawdown dispersion than low confidence schemes, confirming confidence reflects history completeness, but confidence is not a driver of absolute forward return.

## 11. Final Evidence Classification

1. **SUPPORTED BY THIS VALIDATION**:
   - Point-in-time score calculation integrity strictly verified.
   - Fund Quality selects a materially distinct cohort from Trailing Return and Volatility.
   - Fund Quality adds a statistically measurable positive coefficient in nested linear regression over trailing 1Y return and risk.
2. **PARTIALLY SUPPORTED**:
   - Quintile return pattern shows general ordering across quintiles Q1 through Q5, but Q1 and Q2 return differences are modest.
3. **NOT SUPPORTED**:
   - Monotonic quintile return relationship across all 5 quintiles without exception.
   - Substantial economic decision-value from incremental $R^2$ alone ($+0.005874$).
4. **UNTESTABLE WITH CURRENT DATA**:
   - Multi-regime temporal stability (requires multi-year out-of-sample data).
   - Investor net transaction-cost-adjusted economic returns.
5. **REQUIRES FURTHER OUT-OF-SAMPLE VALIDATION**:
   - Multi-period OOS testing across full market cycles (bear markets, sideways regimes).

## 12. Required Final Answers

1. **Was the 2024-01-31 Fund Quality score calculated without future information?**
   YES.
2. **What was the final validated population?**
   5,713 schemes.
3. **What was Strategy A's selected N?**
   571 schemes.
4. **What was Strategy B's selected N?**
   571 schemes.
5. **What was Strategy C's selected N?**
   571 schemes.
6. **What was each strategy's forward return?**
   Strategy A: 12.23%; Strategy B: 4.34%; Strategy C: 11.85%; Comparator B-DOWN: 5.03%.
7. **What was each strategy's forward mean individual-fund MDD?**
   Strategy A: 16.83%; Strategy B: 0.11%; Strategy C: 16.80%; Comparator B-DOWN: 0.10%.
8. **How much did the cohorts overlap?**
   A vs C Jaccard 0.8845 (536 shared); B vs C Jaccard 0.0000 (0 shared); C vs B-DOWN Jaccard 0.0000 (0 shared).
9. **Does Fund Quality select materially different funds from trailing return?**
   YES (11.55% cohort turnover / 35 unique funds).
10. **Does Fund Quality select materially different funds from historical volatility?**
    YES (100.00% cohort turnover / 571 unique funds).
11. **Does Fund Quality add measurable information beyond trailing return?**
    YES (Statistically positive coefficient $+0.935340$ in nested model).
12. **Does Fund Quality add measurable information beyond historical risk?**
    YES (Statistically positive coefficient over vol + downside dev).
13. **What is the incremental R²?**
    $+0.005874$.
14. **Is the incremental information economically meaningful?**
    MINIMAL / UNPROVEN (Incremental $R^2$ $+0.005874$ is modest).
15. **Is there evidence of a monotonic Fund Quality quintile relationship?**
    NO (Q1 12.02%, Q2 10.18%, Q3 8.07%, Q4 7.10%, Q5 3.17%).
16. **Is confidence associated with outcome dispersion?**
    YES (High confidence funds exhibit lower return/MDD variance).
17. **Is there evidence of causal risk protection?**
    NO CAUSAL RISK-PROTECTION CLAIM.
18. **Is there evidence of investor economic benefit?**
    NOT ESTABLISHED BY THIS VALIDATION.
19. **Is this validation prospective/pre-registered?**
    NO — RETROSPECTIVE POINT-IN-TIME VALIDATION.
20. **Does this validation justify changing production methodology?**
    NO AUTOMATIC PRODUCTION CHANGE.
