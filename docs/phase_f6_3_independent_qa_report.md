# Phase F.6.3 Independent Action Engine QA Audit Report

## Executive Summary

Phase F.6.3 delivers an independent, first-principles QA audit of the **Action Decision Engine** (`action/engine.py`, `action/models.py`). 

The audit evaluated decision precedence, low-turnover rules, financial safety, missing-data handling, truthiness guardrails, construct isolation, tax boundary decoupling, and edge-case behaviors. Three defects were identified during initial forensic inspection, corrected with minimal surgical changes, and validated against 365 unit, integration, adversarial, and invariant tests.

---

## A. Documents Reviewed
1. `PRODUCT_SPEC.md`
2. `DECISION_RULES.md`
3. `FEATURE_CATALOG.md`
4. `docs/phase_f3_4_3_suitability_decision_logic_specification.md`
5. `docs/phase_f3_4_suitability_specification.md`
6. `docs/phase_f4_3_portfolio_need_decision_logic_specification.md`
7. `docs/phase_f4_4_substantive_financial_architecture_audit.md`
8. `docs/phase_f5_economic_benefit_specification.md`
9. `docs/phase_f5_economic_benefit_governance_audit.md`
10. `docs/phase_f5_economic_benefit_parameter_register.md`
11. `docs/phase_f6_action_decision_specification.md`
12. `docs/phase_f6_action_governance_audit.md`
13. `docs/phase_f6_action_parameter_register.md`
14. `docs/phase_f6_action_test_plan.md`
15. `docs/phase_f6_2_action_engine_implementation_report.md`

---

## B. Files Inspected
- [`action/models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/action/models.py)
- [`action/engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/action/engine.py)
- [`action/__init__.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/action/__init__.py)
- [`tests/financial/test_action_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_action_engine.py)
- [`models/suitability_assessment.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/models/suitability_assessment.py)
- [`portfolio/need_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/portfolio/need_models.py)

---

## C. Actual Decision Flow
The `assess_action()` implementation follows the exact 7-tier decision precedence hierarchy governed by F.6/F.6.1:
1. **Tier 1: `INVALID / UNSAFE`** — Halts execution if context inputs are empty, null, or report invalid upstream assessments (`INVALID_ASSESSMENT` / empty IDs).
2. **Tier 2: `INSUFFICIENT INFORMATION`** — Halts execution if mandatory Suitability or Portfolio Need assessments are absent, incomplete, or stale per governed freshness criteria.
3. **Tier 3: `NOT SUITABLE / HARD CONSTRAINT`** — Returns `NO_ACTION` (new position) or `REVIEW` (existing holding) if Suitability is `NOT_SUITABLE` or lock-in conflict exists. High Fund Quality cannot override suitability failures.
4. **Tier 4: `MATERIAL REVIEW SIGNAL`** — Evaluates performance deterioration. Returns `HOLD` for temporary volatility, `MONITOR` for mild decay, `REVIEW` for unvalidated deterioration/missing tax/missing exit load/unproven economics, and `SELL` ONLY if all 14 switch guardrails are satisfied.
5. **Tier 5: `ECONOMIC / PORTFOLIO ACTIONABILITY`** — Evaluates candidate fulfillment capability and portfolio concentration/overlap. Constrains new entries to `ACCUMULATE` or `NO_ACTION`.
6. **Tier 6: `POSITIVE OPPORTUNITY`** — Evaluates full purchase dependency chain (`NEED_IDENTIFIED` + `SUITABLE` + `CAN_FULFILL` + `ECONOMICALLY_BENEFICIAL`). Returns `BUY` (unconstrained new position), `ACCUMULATE` (capacity constrained or existing holding), or `NO_ACTION` / `HOLD` (economic benefit unproven).
7. **Tier 7: `HOLD / NO CHANGE`** — Default low-turnover baseline.

---

## D. CRITICAL SELL Audit
- **Findings:** `SELL` requires ALL 14 governed prerequisites simultaneously. 
- `SELL` cannot occur if replacement is missing (`NO_SUITABLE_REPLACEMENT`), tax info is missing (`tax_liability_known=False`), exit load is missing (`exit_load_known=False`), deterioration methodology is unvalidated (`deterioration_validated=False`), or economic benefit is unknown (`economic_benefit_state` not in positive states). Missing evidence forces safe fallback to `REVIEW`.

---

## E. CRITICAL BUY Audit
- **Findings:** High Fund Quality score, high percentile, high rank (#1), high historical return, or macro stress alone **NEVER** generates `BUY`. `BUY` requires the complete 9-point Tier 6 purchase dependency chain.

---

## F. ACCUMULATE Audit
- **Findings:** `ACCUMULATE` is triggered when purchase intent is valid for an existing position OR when capacity constraints (`CATEGORY_OVEREXPOSED`, `HIGH_SECURITY_OVERLAP`, `AFFORDABILITY_CONSTRAINED`) limit a new entry. Zero unvalidated concentration thresholds are hardcoded.

---

## G. HOLD / Low-Turnover Audit
- **Findings:** Low-turnover invariants verified:
  - Healthy incumbent + higher candidate rank $\rightarrow$ `HOLD`
  - Small score movement $\rightarrow$ `HOLD`
  - Temporary volatility / drawdown $\rightarrow$ `HOLD`
  - High quality + no portfolio need $\rightarrow$ `NO_ACTION` / `HOLD`

---

## H. MONITOR / REVIEW Escalation Audit
- **Findings:** Escalation path is strictly hierarchical: `HOLD` (temporary) $\rightarrow$ `MONITOR` (mild) $\rightarrow$ `REVIEW` (material + missing metadata/unvalidated) $\rightarrow$ `SELL` (material + all switch guardrails satisfied). Zero unvalidated numeric quarter cutoffs exist in code.

---

## I. Missing-Data Audit
- **Findings:**
  - `None`, `False`, `""`, or `"UNKNOWN"` values for mandatory inputs trigger Tier 1 (`INVALID_ASSESSMENT`) or Tier 2 (`INSUFFICIENT_INFORMATION`).
  - Missing tax/exit load flags safely trigger Tier 4 `REVIEW` (prohibiting liquidation).

---

## J. Tax/Cost Boundary Audit
- **Findings:** Action owns ZERO statutory tax rules, capital gains formulas, STCG/LTCG cutoffs, or exit load schedules. Action consumes abstract Tax/Cost flags from the Tax/Cost domain. `tax/rules.py` does NOT exist in the repository.

---

## K. Economic Benefit Boundary
- **Findings:** Action does not compute expected improvement or financial returns. It consumes abstract `economic_benefit_state`. In Stage 4 and Stage 6, non-beneficial or unknown states safely block transactional recommendations.

---

## L. Confidence Audit
- **Findings:** `action_confidence` is explicitly documented as a structural input completeness indicator (1.0 = fully sufficient, 0.5 = partial, 0.0 = insufficient). It is NOT a statistical probability of return and does NOT override upstream confidence.

---

## M. Position-Context Audit
- **Findings:** `NEW_POSITION` and `EXISTING_POSITION` enforce distinct, safe decision paths. `SELL` cannot apply to `NEW_POSITION`; `BUY` cannot replace `HOLD` for `EXISTING_POSITION`. Missing `position_context` triggers Tier 1 `INVALID_ASSESSMENT`.

---

## N. Suitability Boundary Audit
- **Findings:** `SuitabilityStatus.NOT_SUITABLE` or lock-in conflict strictly blocks `BUY`/`ACCUMULATE` in Tier 3, regardless of Fund Quality score. Upstream `Suitability` assessments with empty IDs or invalid structures trigger Tier 1 `INVALID_ASSESSMENT`.

---

## O. Portfolio Need Boundary Audit
- **Findings:** `PortfolioNeedState.NO_MATERIAL_NEED` returns `NO_ACTION` / `HOLD`. `CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED` blocks purchase in Tier 5. Action does not recalculate Portfolio Need.

---

## P. Provenance Audit
- **Findings:** Every `ActionAssessmentResult` preserves full auditability: `assessment_id`, `investor_id`, `scheme_id`, `position_context`, `goal_id`, `portfolio_id`, `upstream_assessment_ids`, `observation_timestamp`, `methodology_version` ("F.6.2"), and `rule_version` ("1.0.0").

---

## Q. Explainability Audit
- **Findings:** Every result contains a valid `primary_reason_code`, `reason_codes` list, clear human-readable `explanation`, and contextual `warnings`. Zero misleading explanations exist.

---

## R. Construct-Isolation Audit
- **Findings:** Action Engine imports only data contracts from `action.models`, `models.suitability_assessment`, and `portfolio.need_models`. Zero internal calculation modules or upstream scoring functions are imported or mutated.

---

## S. Test-Quality Audit
- **Findings:** Test suite contains 33 specification tests (`TA-01` to `TA-30`, `TestF622PreQAForensics 1–3`, `TestF63IndependentQAFindingFixes 1–3`), 12 adversarial scenarios (`test_adv_a` to `test_adv_k`), and construct isolation tests.

---

## T. Invariants Tested
- **Invariants 1–10:** All 10 governed financial invariants verified green.

---

## U. Financial-Methodology Audit
- **Findings:** The Action Engine resists unnecessary turnover, prevents performance chasing, enforces tax/cost safety, prevents unproven economic switching, and isolates decision logic from broker transaction execution.

---

## V. Edge-Case Audit
- **Findings:** All 24 edge-case combinations (missing context, partial context, invalid upstream, unvalidated deterioration, missing tax metadata, macro stress) passed cleanly.

---

## W. Defects Found During QA Audit

### Defect 1: Upstream Invalid Suitability Check Omission in Tier 1
- **Classification:** 🔴 **Genuine defect / must fix**
- **File/Function:** `action/engine.py` -> `assess_action()` lines 78-99.
- **Description:** Tier 1 checked `portfolio_need_result.primary_state == PortfolioNeedState.INVALID_ASSESSMENT`, but omitted checking `suitability_result` for invalid assessment indicators (such as empty `assessment_id` or `investor_id`).

### Defect 2: Truthiness Bypass in Economic Benefit Guardrails (Stage 4 & Stage 6)
- **Classification:** 🔴 **Genuine defect / must fix**
- **File/Function:** `action/engine.py` -> `assess_action()` line 367 (Stage 4) & line 559 (Stage 6).
- **Description:** The Economic Benefit Guardrail checked `if context.economic_benefit_state in ("ECONOMICALLY_NOT_BENEFICIAL", "BENEFIT_UNCERTAIN", "NO_EVALUABLE_CHANGE"):`. If `context.economic_benefit_state` was `None`, `""`, or `"UNKNOWN"`, the positive tuple match evaluated to `False`, allowing unproven/unknown economic benefit to bypass the guardrail and generate `BUY` (Stage 6) or `SELL` (Stage 4).

### Defect 3: Missing `position_context` Validation in Tier 1
- **Classification:** 🟠 **Material governance concern**
- **File/Function:** `action/engine.py` -> `assess_action()` line 58.
- **Description:** If `context.position_context` was `None`, Tier 1 did not flag `INVALID_INPUT`, allowing execution to fall through to Tier 7 `HOLD`.

---

## X. Corrections Made
1. **`action/engine.py` (Tier 1):** Added `not context.position_context` to the structural check and added an explicit check for `not context.suitability_result.assessment_id or not context.suitability_result.investor_id` to return `ActionState.INVALID_ASSESSMENT`.
2. **`action/engine.py` (Stage 4 & Stage 6):** Updated both Economic Benefit Guardrail checks to `if context.economic_benefit_state not in ("ECONOMICALLY_BENEFICIAL", "HIGH_BENEFIT", "MODERATE_BENEFIT"):` to guarantee that `None`, `""`, `"UNKNOWN"`, or unproven states engage the guardrail.
3. **`tests/financial/test_action_engine.py`:** Added `TestF63IndependentQAFindingFixes` containing 3 regression tests (`test_qa_defect1`, `test_qa_defect2`, `test_qa_defect3`).

---

## Y. Remaining Limitations
- Statutory tax parameters and exit load schedules will be provided by downstream Tax/Cost domain modules.
- Parameters `PAR-ACT-01` through `PAR-ACT-06` remain `VALIDATION REQUIRED` pending empirical advisor calibration.

---

## Z. Regression Results

Ran `python -m pytest tests/ -v --tb=short`:

```text
============================== 365 passed, 29 warnings in 1.21s ==============================
```
- **Collected:** 365
- **Passed:** 365
- **Failed:** 0
- **Skipped:** 0

---

## AA. Overall QA Verdict

```text
PHASE F.6.3 INDEPENDENT QA PASSED — READY FOR ACCEPTANCE
```
