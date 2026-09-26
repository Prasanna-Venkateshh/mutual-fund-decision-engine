# Phase F.3.2 — Risk Tolerance Engine Implementation Report

**Phase:** Phase F.3.2 — Risk Tolerance Engine Implementation  
**Date:** 2026-09-10 UTC  
**Final Status:** `PHASE F.3.2 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Risk Tolerance Engine implementation, multi-scenario behavioral assessment, response normalization, intra-respondent consistency evaluation, missing-response safety, 5-level ordinal tier mapping, confidence separation, construct independence, 3 startup modes, unit and independent math fixture tests, documentation, and QA review.

---

## 1. Executive Summary

Phase F.3.2 implements the Risk Tolerance Engine governed by the Phase F suitability architecture and Phase F.2A/F.2B behavioral research findings.

Risk Tolerance measures the investor's behavioral willingness to accept investment loss, volatility, uncertainty, and drawdowns. It is strictly independent of financial capacity, income, expenses, debt, emergency reserves, savings, net worth, portfolio value, goal horizon, fund quality, or demographic attributes.

### Key Governance Accomplishments

1. **Strict Construct Isolation:** The Risk Tolerance Engine consumes ONLY `BehavioralToleranceSnapshot`. No financial fields (`monthly_gross_income`, `fixed_expenses`, `debt_servicing`, `liquid_emergency_reserves`), no capacity tier, no horizon years, no fund quality scores, and no demographic parameters enter the Risk Tolerance calculation.
2. **Multi-Scenario Questionnaire Design:** Evaluates multi-item responses across four distinct behavioral dimensions:
   - Loss reaction choice (immediate loss acceptance)
   - Stagnation comfort choice (patience during prolonged market sideways movement)
   - Historical drawdown action (behavior during severe market declines)
   - Volatility preference (comfort with fluctuation)
3. **No Invented Production Thresholds / Multipliers:**
   - No hardcoded Kahneman/Tversky 2.25x loss aversion multiplier.
   - No hardcoded Cronbach's alpha = 0.70 cutoff as an individual investor rule.
   - All scenario weights, ordinal score boundaries, consistency thresholds, and confidence penalties remain externalized in configuration.
4. **Missing-Response Safety (MISSING ≠ ZERO / LOWEST):**
   - Missing responses are never converted to zero, low, or default scores.
   - If $< 2$ choices are supplied, assessment status is `INSUFFICIENT_INFORMATION` and `overall_tolerance_tier` is `None`.
   - If $2$ or $3$ choices are supplied, assessment status is `PARTIAL` with a bounded confidence score.
5. **Intra-Respondent Consistency Analysis:**
   - Evaluates sample standard deviation across normalized behavioral signals $[0.0, 1.0]$.
   - Inconsistency lowers the output confidence score and emits `INCONSISTENT_BEHAVIORAL_RESPONSES` explanation tokens, but does NOT alter the raw behavioral score or ordinal tier.
6. **Three Startup Modes Implemented:**
   - `PRODUCTION`: Fails safely (`CONFIGURATION_ERROR` status) if calibration parameters are missing.
   - `RESEARCH`: Accepts provisional parameters, tags outputs `RESEARCH_MODE_NOT_FOR_PRODUCTION`.
   - `TEST`: Accepts synthetic parameters, tags outputs `SYNTHETIC_TEST_DATA`.
7. **246/246 Tests Passed:** Complete test suite passes (219 baseline + 27 new targeted Risk Tolerance unit, integration, construct separation, and independent math fixture tests).

---

## 2. Methodology & Architecture

The Risk Tolerance Engine executes a 9-step assessment pipeline in [`tolerance_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_engine.py):

```text
Inputs: BehavioralToleranceSnapshot
                 ↓
┌─────────────────────────────────────────────────┐
│ 1. Startup Mode & Config Validation            │
├─────────────────────────────────────────────────┤
│ 2. Input Choice Validation                      │
├─────────────────────────────────────────────────┤
│ 3. Response Normalization [0.0, 1.0]            │
├─────────────────────────────────────────────────┤
│ 4. Status & Coverage Assessment                 │
│    - < 2 choices -> INSUFFICIENT_INFORMATION    │
│    - < 4 choices -> PARTIAL                     │
│    - 4 choices -> COMPLETE                      │
├─────────────────────────────────────────────────┤
│ 5. Raw Score Calculation                        │
│    - Arithmetic mean of normalized signals      │
├─────────────────────────────────────────────────┤
│ 6. Response Consistency Analysis                │
│    - Sample StdDev across normalized signals    │
│    - Level: HIGHLY / MODERATELY / MATERIALLY    │
├─────────────────────────────────────────────────┤
│ 7. Ordinal Tier Mapping (5 Tiers)               │
│    - VERY_LOW, LOW, MODERATE, HIGH, VERY_HIGH   │
├─────────────────────────────────────────────────┤
│ 8. Confidence Score Calculation (Output-only)   │
│    - Deducts for missing inputs & inconsistency │
├─────────────────────────────────────────────────┤
│ 9. Structured Explanation Generation            │
└─────────────────────────────────────────────────┘
                 ↓
Output: RiskToleranceAssessmentResult
```

---

## 3. Data Contracts & Configuration

### Files Created/Modified

| Module | File Path | Responsibilities |
|---|---|---|
| Configuration | [`config/risk/tolerance_config.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/risk/tolerance_config.py) | Externalized config contract, choice weight maps, ordinal thresholds, consistency thresholds, startup modes (`PRODUCTION`, `RESEARCH`, `TEST`), `validate()`, mode factories. |
| Models | [`risk/tolerance_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_models.py) | `BehavioralConsistencyLevel` enum and `RiskToleranceAssessmentResult` immutable data contract. |
| Engine | [`risk/tolerance_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_engine.py) | End-to-end Risk Tolerance assessment pipeline execution. |
| Package Init | [`risk/__init__.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/__init__.py) | Exports `RiskToleranceEngine`, `BehavioralConsistencyLevel`, and `RiskToleranceAssessmentResult`. |
| Test Suite | [`tests/financial/test_risk_tolerance_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_risk_tolerance_engine.py) | 24 targeted unit, integration, construct separation, and startup mode tests. |
| Math Fixtures | [`tests/financial/test_risk_tolerance_fixtures.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_risk_tolerance_fixtures.py) | 3 independent mathematical test fixtures. |

---

## 4. Behavioral Formulas & Mapping

### 4.1 Raw Tolerance Score Calculation
$$\text{Raw Tolerance Score} = \frac{1}{N} \sum_{i=1}^{N} \text{Weight}(C_i)$$
where $C_i$ are the normalized scenario choices $[0.0, 1.0]$ and $N$ is the number of supplied choices ($N \ge 2$).

### 4.2 Response Consistency Calculation
$$\mu = \text{Raw Tolerance Score}, \quad S = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (x_i - \mu)^2}$$
$$\text{Consistency Score} = \max(0.0, 1.0 - S)$$
- If $S \ge \text{consistency\_std\_dev\_threshold\_material}$ (default 0.40) $\rightarrow$ `MATERIALLY_INCONSISTENT`
- Else if $S \ge \text{consistency\_std\_dev\_threshold\_moderate}$ (default 0.25) $\rightarrow$ `MODERATELY_INCONSISTENT`
- Else $\rightarrow$ `HIGHLY_CONSISTENT`

### 4.3 5-Level Ordinal Tier Mapping
- Score $< \text{very\_low\_upper\_threshold}$ (0.20) $\rightarrow$ `VERY_LOW`
- Score $< \text{low\_upper\_threshold}$ (0.40) $\rightarrow$ `LOW`
- Score $< \text{moderate\_upper\_threshold}$ (0.60) $\rightarrow$ `MODERATE`
- Score $< \text{high\_upper\_threshold}$ (0.80) $\rightarrow$ `HIGH`
- Score $\ge \text{high\_upper\_threshold}$ (0.80) $\rightarrow$ `VERY_HIGH`

---

## 5. Construct Separation Verification

| Construct | Used in Risk Tolerance? | Justification |
|---|---|---|
| Monthly Income / Fixed Expenses | **NO** | Financial capacity, not behavioral tolerance. |
| Debt Servicing / Reserves | **NO** | Financial capacity, not behavioral tolerance. |
| Net Worth / Existing Wealth | **NO** | Wealthy investors can be risk-averse; constrained investors can be risk-seeking. |
| Risk Capacity Score / Level | **NO** | Risk Capacity is evaluated separately and combined later in Risk Alignment. |
| Investment Horizon / Years to Goal | **NO** | Goal horizon is a separate suitability dimension. |
| Fund Quality / Historical Returns | **NO** | Asset characteristics belong to Fund Quality scoring. |
| Demographics (Age, Gender, etc.) | **NO** | Demographics must not silently alter behavioral preferences. |

Unit tests `test_12_financial_data_isolation` and `test_13` through `test_16` explicitly prove construct separation.

---

## 6. Hidden-Rule Scan Audit

A scan of all newly created production Python code for hardcoded financial/behavioral threshold constants confirmed:
- No prohibited hardcoded rules exist in `risk/tolerance_engine.py` or `config/risk/tolerance_config.py`.
- All scenario weights, score boundaries, consistency thresholds, and confidence penalties default to `None` in `PRODUCTION` mode.
- In `PRODUCTION` mode, missing calibration parameters trigger safe `CONFIGURATION_ERROR` status.
- Synthetic parameters in `create_test_config()` are strictly isolated to test mode.

---

## 7. QA Review Results

| Category | Status | Evaluation Summary |
|---|---|---|
| A. Behavioral methodology QA | **PASS** | Evaluates multi-scenario choices; directionality verified. |
| B. Mathematical QA | **PASS** | Independent fixtures verify exact arithmetic calculations. |
| C. Missing-response QA | **PASS** | Missing responses never default to zero/lowest tier. |
| D. Construct-separation QA | **PASS** | Financial data, capacity, horizon, fund quality, and demographics have 0 influence. |
| E. Configuration QA | **PASS** | All parameters externalized; fail-safe startup mode enforced. |
| F. Confidence separation QA | **PASS** | Confidence calculated strictly AFTER score; does not alter tier. |
| G. Explainability QA | **PASS** | Tokens emitted strictly when supported by explicit responses. |
| H. Provenance QA | **PASS** | Full audit metadata and timestamp preserved in output contract. |
| I. Determinism QA | **PASS** | 100% reproducible results across multiple executions. |
| J. Regression QA | **PASS** | 246 / 246 tests passing cleanly. |
| K. Hidden-rule scan | **PASS** | No hardcoded 2.25x loss aversion multiplier or Cronbach cutoffs exist. |

---

## 8. Test Suite Execution Summary

- **Baseline Test Suite:** 219 / 219 passed.
- **New Targeted Risk Tolerance Tests:** 27 / 27 passed (24 unit + 3 independent math fixtures).
- **Final Regression Suite:** 246 / 246 passed in 2.42 seconds.

---

## 9. Parameters Remaining Provisional / TBD

### Provisional Parameters (Configurable Stubs):
- `loss_reaction_weight_map`: Scenario weights for loss reaction choices (TBD empirical calibration).
- `stagnation_comfort_weight_map`: Scenario weights for stagnation choices (TBD empirical calibration).
- `drawdown_action_weight_map`: Scenario weights for historical drawdown choices (TBD empirical calibration).
- `volatility_preference_weight_map`: Scenario weights for volatility choices (TBD empirical calibration).
- `very_low_upper_threshold`, `low_upper_threshold`, `moderate_upper_threshold`, `high_upper_threshold`: Ordinal classification boundaries (TBD empirical calibration).
- `consistency_std_dev_threshold_moderate`, `consistency_std_dev_threshold_material`: Consistency standard deviation thresholds (TBD empirical calibration).
- `confidence_penalty_per_missing_response`, `confidence_penalty_inconsistent_responses`: Confidence penalties (TBD empirical calibration).

---

## 10. Final Status — Exactly One

```text
PHASE F.3.2 ACCEPTED WITH PROVISIONAL METHODOLOGY
```

*Note: Phase F.3.3 (Risk Alignment Engine Implementation) may NOT begin automatically.*
