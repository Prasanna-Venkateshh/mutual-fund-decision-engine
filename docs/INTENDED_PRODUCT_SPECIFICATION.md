# INTENDED PRODUCT SPECIFICATION — MUTUAL FUND DECISION ENGINE

**Document Title:** Intended Product Specification  
**Document Type:** Independent Verification Baseline (Product Intent & Governed Architecture)  
**Governance Standard:** Immutable Intended Baseline (Un-reconciled to Implementation)  
**Date:** September 2026 UTC  

---

## 1. PRODUCT OVERVIEW & MANDATORY V1 REQUIREMENTS

The **Mutual Fund Decision Engine** is an objective, evidence-based, conflict-free quantitative recommendation and decision-support backend for Indian Mutual Fund investors.

### MANDATORY V1 REQUIREMENTS (`MANDATORY V1 REQUIREMENT`)
1. **Point-in-Time Action Recommendations:** Must issue structured recommendations (`BUY`, `ACCUMULATE`, `HOLD`, `MONITOR`, `REVIEW`, `SELL`) strictly based on point-in-time snapshot data.
2. **Anti-Survivorship Bias:** Peer group comparisons must evaluate funds strictly relative to point-in-time eligible peer populations.
3. **Lower-of-Two Risk Alignment:** Aligned Risk Tier must strictly equal $\min(\text{Risk Capacity Tier}, \text{Risk Tolerance Tier})$.
4. **Portfolio Need Before Recommendation:** Recommending a fund requires validating asset allocation gaps, subcategory exposure caps, and candidate fulfillment.
5. **Economic Friction Evaluation:** Switching recommendations must evaluate net return improvement after deducting exit loads and capital gains tax (STCG/LTCG) hurdles.
6. **100% Auditability & Explainability:** Every assessment outcome must generate an immutable audit log payload and structured natural-language rationale.
7. **User-Control Separation:** System Recommendation $\neq$ User Decision $\neq$ Execution Status. Zero automated broker trade execution or silent portfolio mutation.
8. **Zero-Return Non-None Retainment (`REQ-FQ-003`):** Numerical return observations of `0.0%` must be retained as valid active return metrics and distinguished from `None` (missing/unpopulated data) to ensure accurate peer-group scoring.

---

## 2. INTENDED V1 ARCHITECTURAL CAPABILITIES (`INTENDED V1 CAPABILITY`)

The intended system architecture processes data through 7 distinct, decoupled layers:

```
+-----------------------------------------------------------------------------------+
| 1. DATA LAYER (AMFI, NAV, Scheme Master, Investor Profile, Portfolio Snapshot)   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 2. METRIC ENGINE (CAGR, Rolling Returns, Volatility, Downside Risk, Drawdown, TER)|
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 3. FUND QUALITY ENGINE (Category-Family Weighted Percentile Rank Score [0-100])    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 4. RISK & SUITABILITY ENGINE (Capacity, Tolerance, Lower-of-Two Alignment, Horizon)|
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 5. PORTFOLIO NEED ENGINE (Asset Class Gaps, Subcategory Caps, Overlap Lookthrough)|
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 6. ECONOMIC BENEFIT ENGINE (Net Benefit Math, Exit Load & STCG/LTCG Tax Hurdle)   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 7. ACTION DECISION ENGINE (BUY, ACCUMULATE, HOLD, MONITOR, REVIEW, SELL)           |
+-----------------------------------------------------------------------------------+
```

### Intended Methodology Specifications
- **Category-Family Weighting Profiles (Equity):** Return `25%`, Consistency `20%`, Volatility `15%`, Downside Risk `15%`, Max Drawdown `15%`, Cost Efficiency `10%`.
- **Rank-Based Midpoint Normalization:** $\text{Percentile} = \frac{\text{Rank} - 0.5}{N} \times 100$.
- **Dynamic Missing-Data Rescaling:** Available dimension weights rescaled to sum to 100% (minimum required active weight sum is `40.0%`).
- **5-Step Suitability Gating:** `INVALID_ASSESSMENT > INSUFFICIENT_INFORMATION > HARD_CONSTRAINT > CONDITIONAL_CONCERN > POSITIVE_EVIDENCE`.
- **Action Precedence & Deterioration:** $\text{BLOCK} > \text{HOLD} > \text{BUY/SELL/SWITCH}$. Deterioration path: $\text{HOLD} \longrightarrow \text{MONITOR} \longrightarrow \text{REVIEW} \longrightarrow \text{SELL}$.

---

## 3. RESEARCH & VALIDATION OBJECTIVES (`RESEARCH / VALIDATION OBJECTIVE`)

1. **Out-of-Sample (OOS) Predictive Value:** Empirical validation (such as Phase F.16) was required to test whether the Fund Quality scoring methodology adds useful forward information and decision value relative to simpler baselines.
2. **Factor Incremental $R^2$ Contribution:** Regression modeling ($M_1, M_2, M_3$) evaluated whether composite quality scores add explanatory value beyond 1Y trailing return and volatility.
3. **Class B Validation Classification:** The F.16 empirical validation was established as `Class B: Production Engine Validation under Degraded Two-Dimension Historical Data`. It verified that the production engine executes deterministically under historical data constraints, but did not constitute a multi-decade 6-dimension predictive alpha proof.

---

## 4. FUTURE / V2 CAPABILITIES (`FUTURE / V2 / EXTENSION`)

1. **Multi-Year Automated Tax-Harvesting Algorithms:** Multi-period tax-loss harvesting and dynamic multi-year portfolio rebalancing algorithms (beyond single-trade STCG/LTCG hurdle evaluation).
2. **Macro-Regime Adaptive Weighting:** Fully dynamic macro-regime score weight adaptation.
3. **Direct Broker API Execution Integration:** Automated order placement and execution status webhooks.

---

## 5. KNOWN LIMITATIONS (`KNOWN LIMITATIONS`)

1. **Incomplete TER Data:** Historical Total Expense Ratio availability prior to 2021 is partial.
2. **Incomplete Riskometer Data:** Historical SEBI Riskometer level progression depth is limited.
3. **Incomplete Benchmark Index Data:** Index TRI time-series for minor custom benchmarks are partially missing.
4. **Historical Point-in-Time Category Mapping:** Relies on AMFI master snapshots for historical categorizations.
5. **Dynamic Six-Dimensional Weight-Rescaling:** Dynamic weight rescaling logic is verified mathematically, but not empirically validated over long OOS market regimes.
6. **Limited Unseen-Period Empirical Evidence:** Empirical testing (F.16) evaluated a single forward year (`2024-01-31` to `2025-01-31`).
7. **No Universal Predictive Superiority Claim:** Fund Quality scores assess historical quality & consistency; they do NOT guarantee future returns.
8. **No Causal Risk Protection Claim:** Downside risk metrics reflect historical behavior, not guaranteed future downside protection.
9. **Unvalidated Tax & Exit-Load Optimization:** Tax-aware switching hurdles are specified, but multi-year tax optimization algorithms are not empirically backtested.
10. **Transaction Execution Outside Scope:** Engine provides recommendation payloads only; broker transaction execution is deliberately excluded.

---

## 6. UNVERIFIED ITEMS (`UNVERIFIED`)

1. **Third-Party Commercial Data Feeds:** Ingestion from non-official proprietary commercial APIs.
2. **Multi-Asset Commodity Derivatives Math:** Direct physical commodity evaluation beyond Gold/Silver ETF tracking.

---

## DOCUMENT SCOPE

This document establishes the **Intended Product Specification & Governed Architecture Baseline** for the `mutual-fund-decision-engine`.

**What it DOES establish:**
- Mandatory V1 requirements, intended architectural capabilities, research objectives, and future scope.
- Governed decision architecture and phase validation lineage.

**What it DOES NOT establish:**
- Proof that the codebase currently implements every specified detail identically (see `IMPLEMENTATION_CODEBASE_MAP.md` for codebase map and discrepancy register).
