# Phase F.6.3.1 Action QA Correction Report
**Economic Benefit State Alignment + Score Comparability Governance Correction**

---

## Executive Summary

Phase F.6.3.1 completes a narrow governance correction of the Action Decision Engine (`action/engine.py`, `action/models.py`) to resolve two critical issues:
1. **Economic Benefit State Vocabulary Alignment:** Aligned Action Engine state consumption strictly with the canonical Phase F.5 vocabulary (`ECONOMICALLY_BENEFICIAL`, `ECONOMICALLY_NOT_BENEFICIAL`, `ECONOMICALLY_NEUTRAL`, `NO_EVALUABLE_CHANGE`, `BENEFIT_UNCERTAIN`, `INSUFFICIENT_INFORMATION`, `INVALID_ASSESSMENT`). Removed non-canonical Action-only states (`HIGH_BENEFIT`, `MODERATE_BENEFIT`) from production decision code.
2. **Fund Quality Score Comparability Guardrail:** Integrated explicit score comparability governance (`fund_quality_comparison_valid: Optional[bool]`). If candidate and holding Fund Quality scores are non-comparable (`False`) or comparability is unknown (`None`), replacement score comparison MUST NOT support position liquidation (`SELL`), forcing safe fallback to `REVIEW`.

---

## A. Economic Benefit Taxonomy Audit
- **Audit Findings:** The previous implementation contained references to `HIGH_BENEFIT` and `MODERATE_BENEFIT` alongside `ECONOMICALLY_BENEFICIAL`.
- **Classification:** 🔴 **Genuine defect / must fix**
- **Governance Requirement:** Phase F.5 established the canonical Economic Benefit state vocabulary. Action must consume the canonical F.5 states and must not independently invent or rely on unapproved taxonomy extensions.

---

## B. Exact HIGH/MODERATE Benefit Findings
- **Inspection Result:** `HIGH_BENEFIT` and `MODERATE_BENEFIT` were present in Stage 4 and Stage 6 tuple checks in `action/engine.py`. They were Action-only assumptions not emitted by the F.5 specification.
- **Action Taken:** Removed `HIGH_BENEFIT` and `MODERATE_BENEFIT` completely from `action/engine.py`.

---

## C. Canonical F.5 Alignment
- **Canonical Positive State:** `ECONOMICALLY_BENEFICIAL` is now the ONLY state that satisfies the positive economic benefit prerequisite for `BUY` (Stage 6) or `SELL` (Stage 4).
- **Non-Beneficial & Uncertain States:**
  - `ECONOMICALLY_NOT_BENEFICIAL` $\rightarrow$ blocks `BUY`/`SELL` (returns `REVIEW` with `SWITCH_NOT_JUSTIFIED` in Stage 4, `NO_ACTION`/`HOLD` in Stage 6).
  - `ECONOMICALLY_NEUTRAL`, `NO_EVALUABLE_CHANGE`, `BENEFIT_UNCERTAIN`, `INSUFFICIENT_INFORMATION`, `INVALID_ASSESSMENT` $\rightarrow$ block `BUY`/`SELL` (returns `REVIEW` in Stage 4, `NO_ACTION`/`HOLD` in Stage 6).

---

## D. Fund Quality Comparability Audit
- **Audit Findings:** Two Fund Quality scores are comparable ONLY when their governing comparison context matches (category/subcategory, plan, option, methodology version, config version).
- **Classification:** 🔴 **Genuine defect / must fix**
- **Upstream Contract:** Added `fund_quality_comparison_valid: Optional[bool] = True` to `ActionEvaluationContext`.
- **Guardrail Enforced:** If `fund_quality_comparison_valid is not True` (`False` or `None`), score comparison cannot justify replacement, blocking `SELL` and returning `ActionState.REVIEW` with `ReasonCode.INSUFFICIENT_EVIDENCE` and warning `"Switch Guardrail: Fund Quality comparison is invalid or unknown."`.

---

## E. SELL Re-Audit
- **Complete Prerequisites Verified:**
  1. `position_context == EXISTING_POSITION`
  2. Upstream holding assessment valid
  3. Deterioration signal present (`MATERIAL_DETERIORATION`)
  4. Deterioration methodology validated (`deterioration_validated=True`)
  5. Replacement candidate identified (`has_suitable_replacement=True`)
  6. Replacement candidate suitable (`SUITABLE` / `CONDITIONALLY_SUITABLE`)
  7. Fund Quality score comparison valid (`fund_quality_comparison_valid=True`)
  8. Tax metadata known (`tax_liability_known=True`)
  9. Exit load metadata known (`exit_load_known=True`)
  10. Canonical Economic Benefit state verified (`economic_benefit_state == "ECONOMICALLY_BENEFICIAL"`)
- Missing ANY single prerequisite safely halts liquidation and falls back to `REVIEW`.

---

## F. BUY Re-Audit
- **Complete Prerequisites Verified:**
  1. `position_context == NEW_POSITION`
  2. `portfolio_need_state == NEED_IDENTIFIED`
  3. `candidate_fulfillment == CAN_FULFILL`
  4. `suitability_state == SUITABLE` / `CONDITIONALLY_SUITABLE`
  5. Canonical Economic Benefit verified (`economic_benefit_state == "ECONOMICALLY_BENEFICIAL"`)
- `BENEFIT_UNCERTAIN`, `NO_EVALUABLE_CHANGE`, `ECONOMICALLY_NOT_BENEFICIAL`, `ECONOMICALLY_NEUTRAL`, `INSUFFICIENT_INFORMATION`, or `INVALID_ASSESSMENT` strictly block `BUY`.

---

## G. Tests Added/Updated
Added `TestF631QACorrection` in [`tests/financial/test_action_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_action_engine.py):
- **TEST A (`test_f631_test_a_...`):** Canonical `ECONOMICALLY_BENEFICIAL` satisfies prerequisite for BUY and SELL.
- **TEST B (`test_f631_test_b_...`):** Non-canonical `HIGH_BENEFIT` / `MODERATE_BENEFIT` cannot produce BUY.
- **TEST C (`test_f631_test_c_...`):** `BENEFIT_UNCERTAIN` cannot produce BUY or SELL.
- **TEST D (`test_f631_test_d_...`):** `NO_EVALUABLE_CHANGE` cannot produce BUY or SELL.
- **TEST E (`test_f631_test_e_...`):** `ECONOMICALLY_NOT_BENEFICIAL` cannot produce BUY or SELL.
- **TEST F (`test_f631_test_f_...`):** `fund_quality_comparison_valid=False` blocks SELL (returns `REVIEW`).
- **TEST G (`test_f631_test_g_...`):** `fund_quality_comparison_valid=None` blocks SELL (returns `REVIEW`).
- **TEST H (`test_f631_test_h_...`):** `fund_quality_comparison_valid=True` allows SELL when all other prerequisites are satisfied.

---

## H. Provenance Verification
- Action results continue to record `assessment_id`, `investor_id`, `scheme_id`, `position_context`, `goal_id`, `portfolio_id`, `upstream_assessment_ids` (including `fund_quality_assessment_id`, `suitability_assessment_id`, `portfolio_need_assessment_id`), `methodology_version` ("F.6.2"), and `rule_version` ("1.0.0").

---

## I. Explainability Verification
- Explanations now explicitly state:
  - *"Material deterioration confirmed, suitable replacement available, candidate Fund Quality comparison is valid, and net economic benefit is verified. Recommended SELL."*
  - *"Fund Quality comparison between holding and replacement candidate is unavailable or invalid; replacement cannot be justified on that evidence."*

---

## J. Files Changed
1. [`action/models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/action/models.py): Added `fund_quality_comparison_valid: Optional[bool] = True` to `ActionEvaluationContext`; updated F.5 state vocabulary comments.
2. [`action/engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/action/engine.py): Updated Stage 4 and Stage 6 to require canonical `economic_benefit_state == "ECONOMICALLY_BENEFICIAL"`; added `fund_quality_comparison_valid is not True` guardrail check in Stage 4.
3. [`tests/financial/test_action_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_action_engine.py): Added `TestF631QACorrection` (8 tests A–H).
4. [`docs/phase_f6_3_1_action_qa_correction_report.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f6_3_1_action_qa_correction_report.md): Created Phase F.6.3.1 QA correction report.

---

## K. Regression Results

Ran `python -m pytest tests/ -v --tb=short`:

```text
============================== 373 passed, 29 warnings in 1.29s ==============================
```
- **Collected:** 373
- **Passed:** 373
- **Failed:** 0
- **Skipped:** 0

---

## L. Remaining Limitations
- Statutory tax parameters and exit load schedules will be provided by downstream Tax/Cost domain modules.
- Parameters `PAR-ACT-01` through `PAR-ACT-06` remain `VALIDATION REQUIRED` pending empirical calibration.

---

## FINAL STATUS

```text
PHASE F.6.3.1 CORRECTION ACCEPTED — READY FOR FINAL QA ACCEPTANCE
```
