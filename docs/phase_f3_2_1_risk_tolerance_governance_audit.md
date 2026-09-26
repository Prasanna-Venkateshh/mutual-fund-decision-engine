# Phase F.3.2.1 — Risk Tolerance Calibration & Default Governance Audit Report

**Phase:** Phase F.3.2.1 — Risk Tolerance Calibration & Default Governance Audit  
**Date:** 2026-09-10 UTC  
**Final Decision:** `PHASE F.3.2.1 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Governance & implementation audit of Phase F.3.2 Risk Tolerance Engine code, parameter inventory, default compatibility audit, startup mode isolation, partial-assessment rules, consistency stddev metric audit, construct isolation, hidden-rule scan, and test suite verification.

---

## 1. Executive Summary

Phase F.3.2.1 performs a targeted governance and implementation audit of the completed Phase F.3.2 Risk Tolerance Engine ([`tolerance_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_engine.py), [`tolerance_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_models.py), [`tolerance_config.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/risk/tolerance_config.py)).

### Audit Findings Summary

1. **Zero Hidden Production Behavioral Rules:** All calibration thresholds default to `None` in `PRODUCTION` mode contract ([`tolerance_config.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/risk/tolerance_config.py#L23)). In `PRODUCTION` mode, missing parameters cause the engine to halt execution safely with `AssessmentStatus.CONFIGURATION_ERROR` and an unclassified tier (`None`).
2. **Compatibility of Default Statements Verified:** Synthetic values (e.g. 0.20, 0.40, 0.25) exist **strictly as test fixtures** in `create_test_config()`. They are never accessible in `PRODUCTION` mode.
3. **Complete Construct Separation Verified:** Changing financial inputs (income, debt, expenses, reserves), Risk Capacity tiers, investment horizons, fund quality scores, or demographics has **zero impact** on Risk Tolerance.
4. **Missing-Data Safety Verified:** `MISSING ≠ ZERO`, `MISSING ≠ LOWEST`. Assessments with $< 2$ responses produce `INSUFFICIENT_INFORMATION` and an unclassified tier (`None`).
5. **No Loss-Aversion Multiplier / Cronbach Cutoff Invented:** Confirmed that no hardcoded 2.25x loss aversion multiplier or Cronbach $\alpha = 0.70$ individual cutoff exists anywhere in production code.
6. **246/246 Tests Passed:** 100% clean test execution with zero regressions.

---

## 2. Parameter Default Audit Table

The audit verified that numerical defaults reported in Phase F.3.2 exist **strictly as test fixtures or research parameters** and are **never hidden production fallbacks**:

| Parameter | Production Default | Research Default | Test Default | Hidden Fallback in Engine? | Status |
|---|---|---|---|---|---|
| `loss_reaction_weight_map` | `None` | Optional Dict | Synthetic Dict | No | `TBD` |
| `stagnation_comfort_weight_map` | `None` | Optional Dict | Synthetic Dict | No | `TBD` |
| `drawdown_action_weight_map` | `None` | Optional Dict | Synthetic Dict | No | `TBD` |
| `volatility_preference_weight_map` | `None` | Optional Dict | Synthetic Dict | No | `TBD` |
| `very_low_upper_threshold` | `None` | Optional float | `0.20` | No | `PROVISIONAL` |
| `low_upper_threshold` | `None` | Optional float | `0.40` | No | `PROVISIONAL` |
| `moderate_upper_threshold` | `None` | Optional float | `0.60` | No | `PROVISIONAL` |
| `high_upper_threshold` | `None` | Optional float | `0.80` | No | `PROVISIONAL` |
| `consistency_std_dev_threshold_moderate` | `None` | Optional float | `0.25` | No | `PROVISIONAL` |
| `consistency_std_dev_threshold_material` | `None` | Optional float | `0.40` | No | `PROVISIONAL` |
| `confidence_penalty_per_missing_response` | `None` | Optional float | `0.20` | No | `PROVISIONAL` |
| `confidence_penalty_inconsistent_responses` | `None` | Optional float | `0.20` | No | `PROVISIONAL` |
| `partial_assessment_confidence_cap` | `None` | Optional float | `0.70` | No | `PROVISIONAL` |
| `insufficient_info_confidence_cap` | `None` | Optional float | `0.20` | No | `PROVISIONAL` |
| `min_required_responses_count` | `2` | `2` | `2` | No | `PROVISIONAL` |

---

## 3. Complete Parameter Inventory

The engine inventory contains 15 externalized behavioral parameters across 5 functional categories:

1. **Scenario Choice Weight Maps (4):** `loss_reaction_weight_map`, `stagnation_comfort_weight_map`, `drawdown_action_weight_map`, `volatility_preference_weight_map`.
2. **Ordinal Tier Boundaries (4):** `very_low_upper_threshold`, `low_upper_threshold`, `moderate_upper_threshold`, `high_upper_threshold`.
3. **Consistency Thresholds (2):** `consistency_std_dev_threshold_moderate`, `consistency_std_dev_threshold_material`.
4. **Confidence Penalty & Cap Parameters (4):** `confidence_penalty_per_missing_response`, `confidence_penalty_inconsistent_responses`, `partial_assessment_confidence_cap`, `insufficient_info_confidence_cap`.
5. **Coverage Requirement (1):** `min_required_responses_count`.

---

## 4. Minimum Response Requirement & Partial Assessment Audit

- **Minimum Response Threshold ($N=2$):** Classed as a `PROVISIONAL` product methodology choice. It prevents single-question assessments from producing classified Risk Tolerance tiers while allowing partial assessments when $\ge 50\%$ of items are answered.
- **Coverage Rules:**
  - $0$ or $1$ choice supplied $\rightarrow$ `AssessmentStatus.INSUFFICIENT_INFORMATION`, `overall_tolerance_tier = None`.
  - $2$ or $3$ choices supplied $\rightarrow$ `AssessmentStatus.PARTIAL`, returns calculated tier with reduced confidence score (capped at 0.70) and emits `PARTIAL_BEHAVIORAL_RESPONSES` token.
  - $4$ choices supplied $\rightarrow$ `AssessmentStatus.COMPLETE`.
- **Governance Finding:** A partial assessment is **never represented as equivalent** to a complete assessment. The confidence score deduction and explicit `PARTIAL` status tag preserve full auditability.

---

## 5. Response Consistency & Standard Deviation Audit

- **Metric:** Sample standard deviation $S$ across normalized scenario responses $[0.0, 1.0]$.
- **Governance Audit:**
  - Standard deviation is an internal dispersion metric, **not** Cronbach's alpha.
  - Cronbach $\alpha = 0.70$ is **not** used as an individual investor cutoff (per F.2B audit finding).
  - $S \ge 0.40$ (`MATERIALLY_INCONSISTENT`) and $S \ge 0.25$ (`MODERATELY_INCONSISTENT`) are classified as `PROVISIONAL` product metrics pending empirical calibration.
  - Inconsistency lowers confidence and emits explanation tokens, but **does NOT alter the raw behavioral score or ordinal tier**.

---

## 6. Loss-Aversion & Behavioral Research Audit

- **Kahneman/Tversky Loss Aversion:** Confirmed that **no hardcoded 2.25x loss aversion multiplier** or hidden loss aversion coefficient exists in production code.
- **Justification:** Behavioral research establishes loss aversion as a conceptual principle, not a direct production multiplier for this platform. The engine evaluates loss reaction explicitly via multi-choice scenario questions.

---

## 7. Construct Isolation Audit

The audit verified complete independence across all non-behavioral constructs:

1. **Demographic Isolation:** Age, gender, income, wealth, occupation, employment status, and marital status have **0 influence** on Risk Tolerance.
2. **Financial Isolation:** Changing financial capacity parameters (gross income, fixed expenses, debt servicing, emergency reserves) while keeping behavioral choices identical yields **100% identical Risk Tolerance** ([`test_12_financial_data_isolation`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_risk_tolerance_engine.py#L201)).
3. **Risk Capacity Isolation:** Risk Capacity scores and tiers have **0 influence** on Risk Tolerance.
4. **Horizon Isolation:** Goal horizon years and target dates have **0 influence** on Risk Tolerance.
5. **Fund Quality Isolation:** Fund returns, volatility, drawdowns, Sharpe ratio, and Fund Quality scores have **0 influence** on Risk Tolerance.

---

## 8. Missing-Response Test Matrix Results

| Supplied Choices Count | Status | Tier Returned | Confidence Score | Explanation Token |
|---|---|---|---|---|
| 0 choices | `INSUFFICIENT_INFORMATION` | `None` | `0.20` | `INSUFFICIENT_BEHAVIORAL_RESPONSES` |
| 1 choice | `INSUFFICIENT_INFORMATION` | `None` | `0.20` | `INSUFFICIENT_BEHAVIORAL_RESPONSES` |
| 2 choices | `PARTIAL` | Calculated Tier | $\le 0.60$ | `PARTIAL_BEHAVIORAL_RESPONSES` |
| 3 choices | `PARTIAL` | Calculated Tier | $\le 0.70$ | `PARTIAL_BEHAVIORAL_RESPONSES` |
| 4 choices | `COMPLETE` | Calculated Tier | `1.00` (if consistent) | Scenario & Consistency Tokens |

---

## 9. Hidden-Rule Scan Audit Table

A code search of all Risk Tolerance production code ([`tolerance_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_engine.py), [`tolerance_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_models.py), [`tolerance_config.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/risk/tolerance_config.py)) for numerical threshold constants was performed:

| Searched Value | File Location | Occurrence Context | Classification |
|---|---|---|---|
| `0.20` | `config/risk/tolerance_config.py` | `create_test_config()` synthetic parameter | `TEST FIXTURE` |
| `0.25` | `config/risk/tolerance_config.py` | `create_test_config()` synthetic parameter | `TEST FIXTURE` |
| `0.30` | `config/risk/tolerance_config.py` | `create_test_config()` choice map weight | `TEST FIXTURE` |
| `0.40` | `config/risk/tolerance_config.py` | `create_test_config()` synthetic parameter | `TEST FIXTURE` |
| `0.50` | `config/risk/tolerance_config.py` | `create_test_config()` choice map weight | `TEST FIXTURE` |
| `0.60` | `config/risk/tolerance_config.py` | `create_test_config()` synthetic parameter | `TEST FIXTURE` |
| `0.70` | `config/risk/tolerance_config.py` | `create_test_config()` confidence cap | `TEST FIXTURE` |
| `0.80` | `config/risk/tolerance_config.py` | `create_test_config()` synthetic parameter | `TEST FIXTURE` |
| `1.0` | `risk/tolerance_engine.py` | Clamping bound `max(0.0, min(1.0, x))` | `LEGITIMATE MATHEMATICAL CONSTANT` |
| `2.25` | Repository-wide | None | `NOT PRESENT` |

**Scan Conclusion:** Zero prohibited hidden behavioral rules exist in production engine code.

---

## 10. Complete Governance Classification Table

| Methodology Component | Classification | Governance Rationale |
|---|---|---|
| Four Behavioral Dimensions | `APPROVED` | Grounded in Phase F.2A/F.2B behavioral suitability architecture. |
| Choice Weight Mappings | `TBD` | Uncalibrated in production; synthetic in test mode. |
| Minimum Response Count ($N=2$) | `PROVISIONAL` | Pragmatic product methodology choice to prevent 1-item classifications. |
| Partial Assessment Rule | `PROVISIONAL` | Product methodology choice; tagged `PARTIAL` with reduced confidence. |
| Consistency StdDev Metric | `PROVISIONAL` | Internal dispersion metric; does not claim Cronbach $\alpha$ individual validation. |
| Consistency Thresholds (0.25 / 0.40) | `PROVISIONAL` | Product parameters pending empirical calibration. |
| Ordinal Tier Boundaries (0.20..0.80) | `PROVISIONAL` | Product boundaries pending empirical calibration. |
| Confidence Penalties & Caps | `PROVISIONAL` | Output quality indicators; strictly separated from score calculation. |
| Loss-Aversion Treatment | `APPROVED` | No arbitrary 2.25x multiplier invented. Evaluated via direct scenarios. |
| Missing-Response Behavior | `APPROVED` | `MISSING ≠ ZERO`, `MISSING ≠ DEFAULT`. Unclassified if $< 2$ responses. |
| Construct Isolation | `APPROVED` | Financial capacity, horizon, fund quality, and demographics have 0 influence. |
| Questionnaire Versioning | `APPROVED` | Preserves questionnaire, methodology, rule versions, and UTC timestamps. |
| Production Configuration Behavior | `APPROVED` | Refuses execution (`CONFIGURATION_ERROR`) if calibration is missing. |

---

## 11. Test Suite Verification Summary

- **Baseline Suite:** 246 / 246 passed.
- **Targeted Risk Tolerance Tests:** 27 / 27 passed.
- **Final Regression Suite:** 246 / 246 passed in 2.38 seconds.

---

## 12. Post-Audit QA Results

| Category | Status | Evaluation Summary |
|---|---|---|
| A. Behavioral methodology | **PASS** | Multi-scenario assessment; directionality verified. |
| B. Parameter governance | **PASS** | All parameters externalized; `PRODUCTION` mode fail-safe enforced. |
| C. Missing responses | **PASS** | `MISSING ≠ ZERO`. $< 2$ responses returns `INSUFFICIENT_INFORMATION`. |
| D. Partial assessments | **PASS** | Explicit `PARTIAL` status tag and confidence cap applied. |
| E. Confidence separation | **PASS** | Confidence calculated strictly AFTER score; 0 effect on score or tier. |
| F. Construct isolation | **PASS** | Financial data, capacity, horizon, fund quality, and demographics have 0 influence. |
| G. Configuration isolation | **PASS** | Production mode refuses uncalibrated execution; Research/Test tag outputs. |
| H. Questionnaire provenance | **PASS** | Full audit metadata and timestamps preserved in output contract. |
| I. Explainability | **PASS** | Tokens emitted strictly when supported by explicit responses. |
| J. Determinism | **PASS** | 100% reproducible results across multiple executions. |
| K. Regression | **PASS** | 246 / 246 tests passing cleanly. |

---

## 13. Final Decision — Exactly One

```text
PHASE F.3.2.1 ACCEPTED WITH PROVISIONAL METHODOLOGY
```

*Note: Phase F.3.2 (Risk Tolerance Engine Implementation) is fully accepted with provisional methodology. Phase F.3.3 (Risk Alignment Engine Implementation) may NOT begin automatically.*
