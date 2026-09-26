# Phase F.1.1 — Suitability Financial Rule Governance Correction Report

**Phase:** Phase F.1.1 — Financial Rule Governance Correction  
**Date:** 2026-09-09 UTC  
**Final Status:** `PHASE F.1.1 ACCEPTED`  
**Scope:** Governance audit and correction of numerical suitability parameters across Phase F documents. No engine implementation in Phase F.1.1.

---

## 1. Executive Summary

Phase F.1.1 performs a rigorous governance review of all numerical thresholds, percentages, time boundaries, and rules introduced in the Phase F Investor Suitability & Risk Alignment specification.

The governing principle enforced is:

> **DO NOT INVENT FINANCIAL THRESHOLDS.**  
> A plausible or reasonable numerical threshold is **not** automatically an approved financial product rule. All newly introduced numerical values are explicitly externalized, configurable as defaults, and marked `PROVISIONAL — REQUIRES VALIDATION`.

---

## 2. Complete Audit of Numerical Rules

Every numerical threshold introduced in Phase F was audited and classified into four governance categories:

- **A. Explicitly Approved:** Established by `PRODUCT_SPEC.md` or previously accepted phase reports.
- **B. Architectural / Data Contract Structure:** Pure software or schema organization (not a financial advice rule).
- **C. Provisional Financial Rule:** Unapproved numerical parameter retained only as a configurable default marked `PROVISIONAL — REQUIRES VALIDATION`.
- **D. Unsupported Assumption:** Arbitrary hardcoded rule (defused or converted to configurable default).

### Detailed Audit Table

| Rule ID | Parameter / Rule Description | Phase F Value | Governance Classification | Status & Governance Treatment |
|---|---|---|---|---|
| **RC-01** | Debt Servicing Burden Cap | `EMI > 60% of income` | C (Provisional Rule) | Concept approved (debt constrains capacity); numerical threshold `DEFAULT_DEBT_SERVICING_CAP_RATIO = 0.60` externalized as configurable default marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **RC-02** | Emergency Reserve Minimum | `Reserves < 3 months` | C (Provisional Rule) | Concept approved (liquidity constrains capacity); numerical threshold `DEFAULT_MIN_EMERGENCY_RESERVE_MONTHS = 3.0` externalized as configurable default marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **RC-03** | Risk Capacity Savings Tiers | $<10\%$, $10-20\%$, $20-35\%$, $35-50\%$, $>50\%$ | C (Provisional Rule) | Tiers externalized as configurable dictionary `DEFAULT_CAPACITY_SAVINGS_TIERS` marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **RT-01** | Drawdown Scenario Loss % | `20% market decline` | C (Provisional Rule) | Scenario concept approved; loss percentage parameter `DEFAULT_SCENARIO_DRAWDOWN_PCT = 0.20` externalized as configurable default marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **RT-02** | Inconsistency Score Limit | `Consistency < 0.70` | C (Provisional Rule) | Externalized as configurable parameter `DEFAULT_INCONSISTENCY_SCORE_THRESHOLD = 0.70` marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **H-01** | Ultra-Short Horizon Ceiling | `Horizon < 1.0 Year` | C (Provisional Rule) | Horizon ceiling principle approved; exact boundary `DEFAULT_ULTRA_SHORT_HORIZON_YEARS = 1.0` externalized as configurable default marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **H-02** | Horizon Tier Boundaries | `1-3 Yrs`, `3-5 Yrs`, `5-7 Yrs`, `> 7 Yrs` | C (Provisional Rule) | Externalized as configurable tier dictionary `DEFAULT_HORIZON_TIERS` marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **MC-01** | Income Shift Event Limit | `Income change > 20%` | C (Provisional Rule) | Reassessment trigger approved; threshold `DEFAULT_MATERIAL_INCOME_CHANGE_RATIO = 0.20` externalized as configurable default marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **MC-02** | Portfolio Drift Event Limit | `Allocation drift > 15%` | C (Provisional Rule) | Reassessment trigger approved; threshold `DEFAULT_MATERIAL_PORTFOLIO_DRIFT_RATIO = 0.15` externalized as configurable default marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **MC-03** | Profile Expiry Duration | `Profile age > 12 months` | C (Provisional Rule) | Staleness concept approved; limit `DEFAULT_PROFILE_STALENESS_MONTHS = 12` externalized as configurable default marked `PROVISIONAL — REQUIRES VALIDATION`. |
| **AF-01** | Sustainable Monthly Capacity Formula | Net Income - Expenses - Debt - Emergency | B (Data Contract) | Formula structure clarified to treat emergency contribution as a temporary savings allocation toward emergency target (preventing double-counting with fixed expenses). |

---

## 3. Specific Governance Policy Corrections

### A. Risk Capacity (RC-01, RC-02)
- **Concept Approved:** High financial debt commitments and inadequate liquid reserves reduce an investor's ability to absorb loss.
- **Correction:** The specific numbers ($60\%$ debt servicing, $3$ months emergency reserve) are **NOT** hardcoded. They are externalized as configurable parameters and marked `PROVISIONAL — REQUIRES VALIDATION`.

### B. Risk Tolerance (RT-01)
- **Concept Approved:** Progressive behavioral loss scenarios evaluate psychological willingness to stay invested.
- **Correction:** The $20\%$ drawdown scenario parameter is marked `PROVISIONAL — REQUIRES VALIDATION`. The specification explicitly prohibits inferring tolerance solely from age, income, wealth, or experience.

### C. Time Horizon Boundaries (H-01, H-02)
- **Concept Approved:** Short investment horizons constrain asset class risk suitability regardless of high risk capacity or tolerance.
- **Correction:** The $1.0$-year ultra-short horizon ceiling and intermediate tier boundaries are externalized as configurable parameters marked `PROVISIONAL — REQUIRES VALIDATION`.

### D. Material Change Detection (MC-01, MC-02, MC-03)
- **Concept Approved:** Reassessment is triggered by material changes in investor financial status, goals, or portfolio drift.
- **Correction:** Thresholds ($>20\%$ income shift, $>15\%$ portfolio drift, $>12$ months profile age) are externalized as configurable defaults marked `PROVISIONAL — REQUIRES VALIDATION`.

### E. Affordability Formula & Double-Counting Prevention (AF-01)
- Sustainable Monthly Contribution is defined as:
  $$\text{Sustainable Capacity} = \text{Gross Monthly Income} - \text{Fixed Monthly Expenses} - \text{Debt Servicing EMIs} - \text{Emergency Target Contribution}$$
- **Clarification:** Emergency contribution is defined strictly as a *temporary savings allocation* required to build the target emergency fund (if reserves are below target). It is not part of recurring fixed expenses, preventing double-counting.

---

## 4. Multi-Layer Validation Strategy

To prevent misrepresenting software testing as financial advice validation, validation is explicitly separated into 5 distinct domains:

```
FIVE-LAYER VALIDATION FRAMEWORK
  ├── Layer 1: Software & Logic Validation (Unit tests, edge case assertions, deterministic outputs)
  ├── Layer 2: Mathematical Validation (Range bounds, min/max matrix math, non-negative bounds)
  ├── Layer 3: Behavioral Questionnaire Validation (Consistency checks, scenario choice clarity)
  ├── Layer 4: Financial Methodology Validation (Fiduciary alignment, lower-of-two rule compliance)
  └── Layer 5: Empirical Calibration (Empirical demographic data, market cycle backtesting)
```

Synthetic data is used **ONLY** for Layer 1 and Layer 2 software/mathematical testing, and is **NEVER** cited as empirical validation for Layer 5 financial methodology.

---

## 5. Formal Provisional Rule Register

| Rule ID | Parameter Key | Default Value | Governance Status | Required Evidence for Final Validation |
|---|---|---|---|---|
| **RC-01** | `DEFAULT_DEBT_SERVICING_CAP_RATIO` | `0.60` | `PROVISIONAL — REQUIRES VALIDATION` | Empirical default rates across debt servicing ratios in Indian retail portfolios. |
| **RC-02** | `DEFAULT_MIN_EMERGENCY_RESERVE_MONTHS` | `3.0` | `PROVISIONAL — REQUIRES VALIDATION` | Retail cash-flow shock survival statistics under job loss / emergency events. |
| **RC-03** | `DEFAULT_CAPACITY_SAVINGS_TIERS` | Dict (10-50%) | `PROVISIONAL — REQUIRES VALIDATION` | Household savings distribution statistics from national financial surveys. |
| **RT-01** | `DEFAULT_SCENARIO_DRAWDOWN_PCT` | `0.20` | `PROVISIONAL — REQUIRES VALIDATION` | Behavioral panic-sale trigger thresholds from historical investor transaction logs. |
| **RT-02** | `DEFAULT_INCONSISTENCY_SCORE_THRESHOLD` | `0.70` | `PROVISIONAL — REQUIRES VALIDATION` | Psychometric questionnaire consistency and re-test reliability studies. |
| **H-01** | `DEFAULT_ULTRA_SHORT_HORIZON_YEARS` | `1.0` | `PROVISIONAL — REQUIRES VALIDATION` | Historical recovery period probabilities for fixed income vs equity categories. |
| **MC-01** | `DEFAULT_MATERIAL_INCOME_CHANGE_RATIO` | `0.20` | `PROVISIONAL — REQUIRES VALIDATION` | Financial planning sensitivity analysis of income volatility on goal probability. |
| **MC-02** | `DEFAULT_MATERIAL_PORTFOLIO_DRIFT_RATIO` | `0.15` | `PROVISIONAL — REQUIRES VALIDATION` | Rebalancing tracking error and transaction friction trade-off analysis. |
| **MC-03** | `DEFAULT_PROFILE_STALENESS_MONTHS` | `12` | `PROVISIONAL — REQUIRES VALIDATION` | Annual financial review regulatory guidelines and profile decay metrics. |

---

## 6. Summary Matrix

- **Numerical Rules Audited:** 12 parameters
- **Approved Conceptual Principles:** 6 core principles (Capacity vs Tolerance, Lower-of-Two, Time Horizon Ceiling, Affordability Primary Constraint, Progressive Profiling, Material Change Reassessment)
- **Provisional Numerical Rules Registered:** 9 configurable parameters explicitly marked `PROVISIONAL — REQUIRES VALIDATION`
- **Code Execution Status in Phase F.1.1:** 0 engine files created (Specification & Governance correction only)
- **Regression Safety:** 170 / 170 project tests passing
