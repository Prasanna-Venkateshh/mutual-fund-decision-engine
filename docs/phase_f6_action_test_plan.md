# Phase F.6 Action Engine Specification-Level Test Plan (Corrected - F.6.1)

## 1. Overview
This document specifies the required 30 specification-level test scenarios and invariants that the proposed Action Engine shall satisfy when constructed in future phases. Zero production test code has been added during Phase F.6.1.

---

## 2. Test Invariant & Scenario Matrix

| Test ID | Scenario Category | Input Conditions | Proposed Action Outcome | Verification Objective |
| :--- | :--- | :--- | :--- | :--- |
| **`TA-01`** | Primary Action: `BUY` | Suitable candidate, `NEED_IDENTIFIED`, `ECONOMICALLY_BENEFICIAL`, validated actionability, new position | `BUY` | Verify valid purchase recommendation generation. |
| **`TA-02`** | Primary Action: `ACCUMULATE` | Suitable candidate, `NEED_IDENTIFIED`, `AFFORDABILITY_CONSTRAINED`, new/existing position | `ACCUMULATE` | Verify staged allocation entry recommendation under capacity constraint. |
| **`TA-03`** | Primary Action: `HOLD` | Suitable owned fund, `NO_MATERIAL_NEED`, no deterioration, low switching benefit | `HOLD` | Verify default low-turnover maintain position recommendation. |
| **`TA-04`** | Primary Action: `MONITOR` | Owned fund, 1-quarter mild alpha drop, evidence insufficient for review | `MONITOR` | Verify observation state assignment without transaction recommendation. |
| **`TA-05`** | Primary Action: `REVIEW` | Owned fund, persistent 3-quarter underperformance, material style drift | `REVIEW` | Verify explicit position reassessment flag. |
| **`TA-06`** | Primary Action: `SELL` | Owned fund, severe deterioration, suitable replacement, positive net economic benefit | `SELL` | Verify full liquidation/switch recommendation under validated conditions. |
| **`TA-07`** | Excellent Fund + No Need | Quality = 95, `NO_MATERIAL_NEED`, candidate new position | `NO_ACTION` / `HOLD` | Prohibit unneeded purchase recommendations. |
| **`TA-08`** | Excellent Fund + Need | Quality = 95, `NEED_IDENTIFIED`, `SUITABLE`, `ECONOMICALLY_BENEFICIAL` | `BUY` | Verify purchase when all upstream requirements are met. |
| **`TA-09`** | Need + Unsuitable Fund | `NEED_IDENTIFIED`, Quality = 90, Suitability = `NOT_SUITABLE` | `NO_ACTION` / `REVIEW` | Verify suitability constraint overrides quality and need. |
| **`TA-10`** | Need + Constrained Affordability | `NEED_IDENTIFIED`, `SUITABLE`, Affordability = `CONSTRAINED` | `ACCUMULATE` | Verify need preservation and action sizing constraint. |
| **`TA-11`** | Need + Unknown Affordability | `NEED_IDENTIFIED`, `SUITABLE`, Affordability = `UNKNOWN` | `ACCUMULATE` (Constrained) | Prevent unconstrained lump-sum recommendation. |
| **`TA-12`** | Unknown Expected Improvement | `NEED_IDENTIFIED`, Expected Improvement = `UNKNOWN` | `MONITOR` / `REVIEW` | Prevent purchase/switch claim when economics are unquantified. |
| **`TA-13`** | Missing Tax Information | Owned fund deterioration, Tax Liability = `UNKNOWN` | `REVIEW` (With Warning) | Prohibit `SELL`/`SWITCH` when tax costs are missing. |
| **`TA-14`** | Missing Exit Load Info | Owned fund deterioration, Exit Load = `UNKNOWN` | `REVIEW` (With Warning) | Prohibit `SELL`/`SWITCH` when load costs are missing. |
| **`TA-15`** | High Switching Cost | Candidate Quality = 85, Incumbent = 80, Net Benefit = Negative | `HOLD` | Prevent tax/load-inefficient switching. |
| **`TA-16`** | Lower vs Higher Incumbent | Incumbent Quality = 75, Candidate = 78, Net Benefit = Minimal | `HOLD` | Prevent cosmetic rank-chasing turnover. |
| **`TA-17`** | Minor Score Change | Incumbent Quality score drops from 82 to 80 | `HOLD` | Verify tolerance for minor score shifts. |
| **`TA-18`** | Material Deterioration | Incumbent Quality drops from 85 to 55 | `REVIEW` $\rightarrow$ `SELL` | Verify escalation on material quality collapse. |
| **`TA-19`** | Temporary Underperformance | 1-quarter market drawdown, fund strategy intact | `HOLD` / `MONITOR` | Resist panic selling on short-lived volatility. |
| **`TA-20`** | Persistent Deterioration | 4-quarter category-relative alpha decay, manager exit | `REVIEW` / `SELL` | Verify escalation on confirmed long-term decay. |
| **`TA-21`** | No Suitable Replacement | Deteriorating owned fund, zero suitable category replacements | `REVIEW` / `HOLD` | Prevent liquidation into unsuitable candidates. |
| **`TA-22`** | Invalid Upstream Assessment | Upstream Portfolio Need = `INVALID_ASSESSMENT` | `INVALID_ASSESSMENT` | Verify Tier 1 precedence enforcement. |
| **`TA-23`** | Insufficient Information | Upstream Suitability = `INSUFFICIENT_INFORMATION` | `INSUFFICIENT_INFO` | Verify Tier 2 precedence enforcement. |
| **`TA-24`** | Stale Upstream Assessment | Upstream Suitability assessment flagged stale per governed freshness criteria | `REVIEW` (Stale Flag) | Force reassessment on outdated inputs. |
| **`TA-25`** | New vs Existing Position | Candidate fund not owned | Prohibit `SELL`/`HOLD` | Enforce position applicability rules. |
| **`TA-26`** | Excessive Portfolio Concentration | `NEED_IDENTIFIED`, candidate causes >40% category concentration | `ACCUMULATE` / `HOLD` | Prevent concentration risk creation. |
| **`TA-27`** | High Overlap Candidate | Candidate has 75% stock overlap with existing holdings | `ACCUMULATE` / `HOLD` | Prevent overlap duplication. |
| **`TA-28`** | Candidate Cannot Fulfill Need | `NEED_IDENTIFIED`, candidate fulfillment = `CANNOT_FULFILL` | `NO_ACTION` | Prohibit incapable candidate recommendations. |
| **`TA-29`** | Macro Stress Context | Market VIX spike, macro stress flag active | Contextual Warning | Prevent automated panic selling or timing. |
| **`TA-30`** | Construct Isolation Audit | Evaluate Action engine execution | Zero upstream mutation | Confirm zero mutation of Suitability, Need, or Quality. |
