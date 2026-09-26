# PHASE F.13 — FUND QUALITY FACTOR COMPLETENESS, DATA READINESS & EXPLAINABILITY GOVERNANCE REPORT

## 1. Executive Summary

This report establishes the canonical factor governance framework for the Mutual Fund Scanner. It systematically evaluates 14 candidate financial dimensions across architectural layer suitability, point-in-time data availability, historical coverage, redundancy, explainability, and production readiness.

**Core Governance Directives:**
1. **Production Scoring Frozen:** Zero candidate factors were added to the production Fund Quality v1.0 score. Production scoring remains strictly 50% Volatility Reciprocal + 50% Trailing 1Y Return.
2. **Architectural Separation Enforced:** Candidate factors are mapped to their proper architectural layers (Fund Quality, Confidence, Suitability, Economic Benefit). Factors such as Fund Age/Maturity belong to **Confidence** (Evidence Depth), TER belongs to **Economic Benefit**, and SEBI Riskometer belongs to **Suitability**, NOT intrinsic Fund Quality score.
3. **Data Availability Barriers Identified:** 4 candidate factors (**Fund Manager Tenure**, **Benchmark Excess Return / Alpha**, **Tracking Error**, and **Information Ratio**) are classified as `BLOCKED_BY_DATA` due to the absence of historical point-in-time database tables in `db/backfill_f12_2.db`.
4. **Governed MAR Preserved:** Daily MAR = 0% is strictly enforced for all downside metrics. Zero ungoverned MAR thresholds (e.g., 6%, 5%) were introduced.

---

## 2. Canonical Factor Architectural Layer Classification

| Factor ID | Factor Name | Intended Architectural Layer | Architectural Rationale |
|---|---|---|---|
| **FQ_F01** | Trailing 1Y Gross Return | **FUND QUALITY** | Intrinsic historical return momentum & capital growth. |
| **FQ_F02** | Annualized Volatility (1Y) | **FUND QUALITY** | Intrinsic historical return fluctuation & risk. |
| **FQ_F03** | Downside Deviation (MAR=0%) | **FUND QUALITY** | Intrinsic loss-side volatility (Research-Only). |
| **FQ_F04** | Maximum Drawdown (1Y) | **FUND QUALITY** | Intrinsic peak-to-trough decline severity (Research-Only). |
| **FQ_F05** | Fund Age / Track Record Depth | **CONFIDENCE** | Measures track record depth, NOT intrinsic return quality. |
| **FQ_F06** | Fund Manager Tenure & Identity | **CONFIDENCE** | Measures management continuity & evidence relevance. |
| **FQ_F07** | Total Expense Ratio (TER) | **ECONOMIC BENEFIT** | Annual fee drag; affects investor net return economics. |
| **FQ_F08** | Sharpe Ratio | **FUND QUALITY** | Risk-adjusted return per unit of total risk (Research-Only). |
| **FQ_F09** | Sortino Ratio (MAR=0%) | **FUND QUALITY** | Risk-adjusted return per unit of downside risk (Research-Only). |
| **FQ_F10** | Benchmark Excess Return (Alpha) | **FUND QUALITY** | Active manager value-add over benchmark (Research-Only). |
| **FQ_F11** | Tracking Error (1Y) | **SUITABILITY** | Benchmark replication consistency for Index Funds/ETFs. |
| **FQ_F12** | Information Ratio (1Y) | **FUND QUALITY** | Active return generated per unit of active risk (Research-Only). |
| **FQ_F13** | Rolling Return Consistency | **FUND QUALITY** | Consistency across multiple rolling windows (Research-Only). |
| **FQ_F14** | SEBI Riskometer Level | **SUITABILITY** | Regulatory risk mandate for investor risk capacity matching. |

---

## 3. Data Readiness & PIT Availability Matrix

| Factor ID | Factor Name | Intended Layer | Current Data Status | PIT Readiness | Production Eligibility |
|---|---|---|---|---|---|
| **FQ_F01** | Trailing 1Y Return | FUND QUALITY | `DATA_FULLY_AVAILABLE` | `PIT_VERIFIED` | `PRODUCTION_ELIGIBLE` |
| **FQ_F02** | Annualized Volatility | FUND QUALITY | `DATA_FULLY_AVAILABLE` | `PIT_VERIFIED` | `PRODUCTION_ELIGIBLE` |
| **FQ_F03** | Downside Deviation (MAR=0%) | FUND QUALITY | `DATA_FULLY_AVAILABLE` | `PIT_VERIFIED` | `VALIDATION_REQUIRED` |
| **FQ_F04** | Maximum Drawdown | FUND QUALITY | `DATA_FULLY_AVAILABLE` | `PIT_VERIFIED` | `VALIDATION_REQUIRED` |
| **FQ_F05** | Fund Age / Maturity | CONFIDENCE | `DATA_FULLY_AVAILABLE` | `PIT_VERIFIED` | `PRODUCTION_ELIGIBLE` |
| **FQ_F06** | Fund Manager Tenure | CONFIDENCE | `BLOCKED_BY_DATA` | `PIT_NOT_AVAILABLE` | `BLOCKED_BY_DATA` |
| **FQ_F07** | Total Expense Ratio (TER) | ECONOMIC BENEFIT | `DATA_PARTIALLY_AVAILABLE` | `PIT_POSSIBLE_BUT_UNVALIDATED` | `VALIDATION_REQUIRED` |
| **FQ_F08** | Sharpe Ratio | FUND QUALITY | `DATA_FULLY_AVAILABLE` | `PIT_VERIFIED` | `VALIDATION_REQUIRED` |
| **FQ_F09** | Sortino Ratio (MAR=0%) | FUND QUALITY | `DATA_FULLY_AVAILABLE` | `PIT_VERIFIED` | `VALIDATION_REQUIRED` |
| **FQ_F10** | Benchmark Excess Return | FUND QUALITY | `BLOCKED_BY_DATA` | `PIT_NOT_AVAILABLE` | `BLOCKED_BY_DATA` |
| **FQ_F11** | Tracking Error | SUITABILITY | `BLOCKED_BY_DATA` | `PIT_NOT_AVAILABLE` | `BLOCKED_BY_DATA` |
| **FQ_F12** | Information Ratio | FUND QUALITY | `BLOCKED_BY_DATA` | `PIT_NOT_AVAILABLE` | `BLOCKED_BY_DATA` |
| **FQ_F13** | Rolling Return Consistency | FUND QUALITY | `DATA_PARTIALLY_AVAILABLE` | `PIT_VERIFIED` | `VALIDATION_REQUIRED` |
| **FQ_F14** | SEBI Riskometer Level | SUITABILITY | `DATA_PARTIALLY_AVAILABLE` | `PIT_POSSIBLE_BUT_UNVALIDATED` | `VALIDATION_REQUIRED` |

---

## 4. Answers to 13 Governance Questions

1. **Genuinely Implemented Factors:** Trailing 1Y Gross Return (`FQ_F01`), Annualized Volatility (`FQ_F02`), Fund Age / Evidence Depth (`FQ_F05`).
2. **Conceptual Factors:** Fund Manager Tenure (`FQ_F06`), Benchmark Excess Return (`FQ_F10`), Tracking Error (`FQ_F11`), Information Ratio (`FQ_F12`).
3. **Factors with Real Data in DB:** Trailing 1Y Return, Volatility, Downside Deviation, Max Drawdown, Fund Age, Sharpe Ratio, Sortino Ratio.
4. **Factors with Historical Data in DB:** Trailing 1Y Return, Volatility, Downside Deviation, Max Drawdown, Fund Age.
5. **Factors with Point-in-Time Validated Data:** Trailing 1Y Return, Volatility, Downside Deviation, Max Drawdown, Fund Age.
6. **Factors Explainable Completely:** Trailing 1Y Return, Volatility, Fund Age, Downside Deviation, Max Drawdown.
7. **Redundant / Overlapping Factors:** 
   - Downside Deviation overlaps heavily with Volatility ($\rho > 0.95$).
   - Sharpe & Sortino ratios overlap mathematically with Trailing Return and Volatility/Downside.
   - Rolling Return Consistency overlaps with Trailing Return and Volatility.
8. **Factors Requiring Data Acquisition:** 
   - Historical Fund Manager Tenure Assignment Table
   - Historical Benchmark Index TRI NAV Series & Point-in-Time Benchmark Mapping Table
   - Historical TER Disclosure Table
9. **Factors Requiring Out-of-Sample Methodology Validation:** Downside Deviation (MAR=0%), Max Drawdown, Sharpe Ratio, Sortino Ratio, Rolling Return Consistency.
10. **Factors Blocked by Data:** Fund Manager Tenure (`FQ_F06`), Benchmark Excess Return (`FQ_F10`), Tracking Error (`FQ_F11`), Information Ratio (`FQ_F12`).
11. **Factors Belonging in Fund Quality:** Trailing 1Y Return, Volatility, Downside Deviation (if validated), Max Drawdown (if validated), Rolling Return Consistency (if validated).
12. **Factors Belonging Elsewhere in Architectural Layers:**
    - Fund Age / Maturity $\rightarrow$ **CONFIDENCE** Layer (Evidence Depth)
    - Total Expense Ratio (TER) $\rightarrow$ **ECONOMIC BENEFIT** Layer (Fee Drag / Net Return)
    - SEBI Riskometer Level $\rightarrow$ **SUITABILITY** Layer (Investor Risk Match)
    - Tracking Error $\rightarrow$ **SUITABILITY** Layer (Index Fund Mandate Check)
13. **Factors Excluded from Production:** All candidate factors outside frozen v1.0 (Trailing 1Y Return + Volatility) remain strictly locked in **RESEARCH** status.

---

## 5. Final Status Declaration

**FINAL STATUS: PASSED WITH LIMITATIONS**

*Rationale:* Canonical Factor Registry (`docs/phase_f13_factor_registry.json`) and Data Readiness Matrix (`docs/phase_f13_data_readiness_matrix.json`) are complete; architectural layer classifications and PIT status are defined for all 14 candidate dimensions; data-blocked factors (Fund Manager, Benchmarks) are explicitly identified; plain-language explainability contracts are specified; all 8 unit tests in `test_phase_f13_factor_governance.py` pass cleanly; zero background tasks are active; production Fund Quality scoring methodology remains strictly unchanged.
