# Phase F.17.1 — Low-Confidence Actionability & Conditional-Suitability Forensic Reconciliation Report

**Phase Identifier:** F.17.1  
**Status:** PASSED WITH LIMITATIONS  
**Audit Date:** 2026-09-16  
**Governed Orchestrator Class:** `integration.orchestrator.DecisionOrchestrator`  
**Production Methodology Changed:** NO  
**Decision Orchestrator Changed:** NO  

---

## 1. Executive Summary & Objective

Phase F.17.1 performs a narrow forensic reconciliation of the F.17 end-to-end decision-chain validation findings. Specifically, it reconciles:
1. Low Fund Quality confidence ($0.05$) and consequential Action gating.
2. `CONDITIONALLY_SUITABLE` $\rightarrow$ `BUY` behavior.
3. Missing-evidence gating semantics across domain contracts.
4. Formal alignment of F.17 claims with the governed contracts and frozen v1.0.0 architecture.

---

## 2. Governed Contract Analysis

### A. Is Fund Quality confidence an input to Action?
- **Yes**, as descriptive metadata (`fund_quality_confidence` field in `ActionEvaluationContext`). However, in `action/engine.py`, `fund_quality_confidence` is **not** used as a numerical filter cutoff to block or change `ActionState`.

### B. Is Actionability an independent input to Action?
- **No.** `actionability_status` ("ACTIONABLE", "CONSTRAINED", "UNACTIONABLE") is an **output indicator** produced by `ActionEngine` reflecting input completeness and position status.

### C. Is there an existing governed minimum-confidence rule?
- **No.** Neither `scoring/config.py`, `integration/orchestrator.py`, nor `action/engine.py` contains a numerical confidence threshold (e.g., `confidence < 0.5` $\rightarrow$ `NO_ACTION`).

### D. Is there an existing governed rule that low confidence must reduce or prevent consequential actions?
- **No.** Upstream confidence (such as low FQ confidence or low Suitability confidence) reduces evidence confidence or emits warnings (e.g. in `SuitabilityEngine` when fund history is immature), but does **not** automatically gate consequential actions via numerical cutoffs in `ActionEngine`. `action/models.py` explicitly documents:
  > `action_confidence` represents an evidence-sufficiency and structural actionability indicator... It is NOT a statistical probability of financial correctness, does NOT claim empirical calibration, does NOT override upstream Fund Quality or Suitability confidence, and is NOT used as a numerical cutoff to filter actions.

### E. Is `0.05` explicitly classified as low confidence anywhere?
- **No.** `0.05` was arbitrarily passed in S12 as a test input representing low numerical confidence, but there is zero rule in the codebase treating `0.05` as a hard cutoff.

### F. Does the existing contract distinguish Score, Confidence, Suitability, Actionability, and Evidence validity?
- **Yes.** They are strictly typed separate fields across `FundQualityScoreResult`, `SuitabilityAssessmentResult`, and `ActionAssessmentResult`.

### G. Is `CONDITIONALLY_SUITABLE` explicitly allowed to proceed to BUY?
- **Yes.** `phase_f3_4_3_suitability_decision_logic_specification.md` and `test_decision_orchestrator.py` explicitly define `CONDITIONALLY_SUITABLE` as conditional permission with attached warnings/constraints, **not** a hard rejection (`NOT_SUITABLE`).

### H. What exact conditions are required for `CONDITIONALLY_SUITABLE` to proceed to BUY?
- `CONDITIONALLY_SUITABLE` proceeds to `BUY` if:
  1. All downstream prerequisites (Portfolio Need = `NEED_IDENTIFIED`, Economic Benefit = `ECONOMICALLY_BENEFICIAL`, evidence valid) are satisfied.
  2. Contextual warnings (e.g., immature track record, goal horizon mismatch, portfolio overlap) are attached to `warnings`.
  3. No hard lock-in conflict or hard `NOT_SUITABLE` constraint is present.

---

## 3. S12 Forensic Reproduction & Root Cause

- **Scenario S12:** FQ Score = $90.0$, Confidence = $0.05$, Evidence Valid = `True`, Suitability = `SUITABLE`, Need = `NEED_IDENTIFIED`, EB = `ECONOMICALLY_BENEFICIAL`.
- **Observed Result:** `BUY` with `final_decision_status = IntegrationStatus.VALID`.
- **Root Cause:** In the governed v1.0.0 engine, numerical confidence is carried as descriptive metadata. `ActionEngine` checks `fund_quality_evidence_valid` (boolean flag), **not** numerical confidence scores (`0.05`). Because `evidence_valid` was `True` and all prerequisites passed, Tier 6 BUY guardrails correctly emitted `BUY`.

---

## 4. Conditional Suitability Reconciliation (S19)

- **Scenario S19:** FQ Score = $85.0$, Confidence = $0.95$, Suitability = `CONDITIONALLY_SUITABLE`, Need = `NEED_IDENTIFIED`, EB = `ECONOMICALLY_BENEFICIAL`.
- **Observed Result:** `BUY` with warning `"Suitability status: CONDITIONALLY_SUITABLE"` attached.
- **Governed Contract Verification:** `CONDITIONALLY_SUITABLE` represents acceptable suitability with contextual warnings (e.g., limited track record, mild overlap). Hard rejection (`NO_ACTION`) occurs **only** when `suitability_status == NOT_SUITABLE` or hard lock-in conflict exists.

---

## 5. Missing Evidence Semantics

- **Action-Specific Gating:** Setting `fund_quality_evidence_valid=False` blocks `BUY`/`ACCUMULATE` actions for `NEW_POSITION`, yielding `NO_ACTION` with `INSUFFICIENT_EVIDENCE`.
- **Scope:** Missing required evidence blocks consequential action **when that evidence is required for that specific action**. Non-required metadata does not force a universal block.

---

## 6. Scenario Reconciliation Matrix

| Scenario | FQ | Confidence | Suitability | Need | Economic Benefit | Expected Action | Actual Action | Result |
|---|---|---|---|---|---|---|---|---|
| **S12_REPRO:** High FQ + Low Conf (0.05) + Valid Evidence | 90.0 | 0.05 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | BUY | BUY | **PASS** |
| **S12_VAR1:** High FQ + Invalid Evidence Flag | 90.0 | 0.05 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NO_ACTION | NO_ACTION | **PASS** |
| **S19_REPRO:** CONDITIONALLY_SUITABLE + Prerequisites | 85.0 | 0.95 | CONDITIONALLY_SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | BUY | BUY | **PASS** |
| **S19_VAR1:** CONDITIONALLY_SUITABLE + Lock-in Conflict | 85.0 | 0.95 | CONDITIONALLY_SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NO_ACTION | NO_ACTION | **PASS** |
| **S19_VAR2:** NOT_SUITABLE Hard Rejection | 85.0 | 0.95 | NOT_SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NO_ACTION | NO_ACTION | **PASS** |
| **MISSING_EV_FQ:** Missing FQ Evidence for New Position | 85.0 | 0.95 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NO_ACTION | NO_ACTION | **PASS** |
| **MISSING_EV_EB:** Uncertain EB Evidence for New Position | 85.0 | 0.95 | SUITABLE | NEED_IDENTIFIED | BENEFIT_UNCERTAIN | NO_ACTION | NO_ACTION | **PASS** |
| **LOW_FQ_LOW_CONF_HOLD:** Low FQ + Low Conf (0.05) + Existing | 10.0 | 0.05 | SUITABLE | NO_MATERIAL_NEED | NO_EVALUABLE_CHANGE | HOLD | HOLD | **PASS** |
| **LOW_FQ_LOW_CONF_SELL:** Low FQ + Low Conf + Deterioration + Replacement | 10.0 | 0.05 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | SELL | SELL | **PASS** |
| **LOW_FQ_LOW_CONF_REVIEW:** Low FQ + Low Conf + High Switching Cost | 10.0 | 0.05 | SUITABLE | NO_MATERIAL_NEED | ECONOMICALLY_NOT_BENEFICIAL | REVIEW | REVIEW | **PASS** |

---

## 7. Formal Claim Matrix

| Claim | Architectural & Empirical Evidence | Governed Status |
|---|---|---|
| **Fund Quality is separated from Suitability** | `SuitabilityAssessmentResult` is evaluated independently of FQ score. High FQ under `NOT_SUITABLE` yields `NO_ACTION`. | **SUPPORTED** |
| **Fund Quality is separated from Portfolio Need** | `PortfolioNeedAssessmentResult` evaluates funding gap independently. High FQ with `NO_MATERIAL_NEED` yields `NO_ACTION`. | **SUPPORTED** |
| **Fund Quality is separated from Economic Benefit** | Net economic benefit checks costs independently. High FQ with `BENEFIT_UNCERTAIN` yields `NO_ACTION`. | **SUPPORTED** |
| **Fund Quality does not automatically trigger BUY** | Removal of any downstream prerequisite from a 95.0 FQ scheme changes Action to `NO_ACTION`. | **SUPPORTED** |
| **Low Fund Quality does not automatically trigger SELL** | Low FQ (10.0) on existing holding yields `HOLD` if no deterioration exists, and `REVIEW` if switching costs are non-beneficial. | **SUPPORTED** |
| **Risk Capacity constrains action** | Low Risk Capacity constrains overall Risk Alignment budget via lower-of-two rule. | **SUPPORTED** |
| **Risk Tolerance constrains action** | Low Risk Tolerance constrains overall Risk Alignment budget via lower-of-two rule. | **SUPPORTED** |
| **Missing required evidence blocks consequential action** | `fund_quality_evidence_valid=False` blocks `BUY`/`SELL` for `NEW_POSITION`, defaulting safely to `NO_ACTION`. | **SUPPORTED** |
| **Economic Benefit is required where governed** | `BENEFIT_UNCERTAIN` and `INSUFFICIENT_INFORMATION` systematically inhibit `BUY`. | **SUPPORTED** |
| **CONDITIONALLY_SUITABLE can proceed to BUY** | `CONDITIONALLY_SUITABLE` allows `BUY` with attached warnings when all downstream prerequisites pass and no hard constraint exists. | **SUPPORTED** |
| **Low confidence can proceed to BUY in v1.0.0** | Confidence is descriptive metadata in v1.0.0; no numerical cutoff rule exists in `ActionEngine`. | **SUPPORTED (AS GOVERNED IN V1.0.0)** |

---

## 8. Final Status Summary

```
FINAL STATUS: PASSED WITH LIMITATIONS

TESTS:
- scripts/run_f17_1_low_confidence_actionability_reconciliation.py (10/10 passed, 100%)
- tests/data_quality/test_phase_f17_1_low_confidence_actionability.py (12/12 passed, 100%)
- tests/data_quality/test_phase_f17_end_to_end_decision_chain_validation.py (12/12 passed, 100%)

PRODUCTION METHODOLOGY CHANGED: NO
DECISION ORCHESTRATOR CHANGED: NO

S12 REPRODUCTION: REPRODUCED (BUY emitted per governed v1.0.0 contract)
S12 ROOT CAUSE: Confidence is descriptive metadata in v1.0.0; ActionEngine filters on boolean boolean evidence validity flag, not numerical confidence cutoffs.

CONFIDENCE GOVERNANCE: Descriptive metadata in v1.0.0; numerical confidence-to-actionability gating requires a future governed methodology decision.
ACTIONABILITY GOVERNANCE: Output status ("ACTIONABLE", "CONSTRAINED", "UNACTIONABLE") reflecting input completeness and position context.
CONDITIONALLY_SUITABLE GOVERNANCE: Conditional permission with warnings attached; permits BUY/ACCUMULATE when downstream prerequisites pass and no hard lock-in constraint exists.
MISSING-EVIDENCE GOVERNANCE: Action-specific gating enforced via `fund_quality_evidence_valid` and upstream assessment statuses.

BUY GUARDRAIL: PASSED
ACCUMULATE GUARDRAIL: PASSED
SELL GUARDRAIL: PASSED
LOW-CONFIDENCE SELL RESULT: PASSED (Low confidence does not force SELL; requires validated deterioration, suitable replacement, and net positive economic benefit)
DETERMINISM: PASSED (100% identical outputs)
REGRESSION TESTS: PASSED (Zero regressions across existing F.17 test suite)

GENUINE DEFECTS: NONE
GOVERNANCE CONCERNS: NONE
PROVISIONAL ASSUMPTIONS:
- Numerical Confidence Gating: In v1.0.0, numerical confidence scores do not act as hard filter cutoffs in ActionEngine. If a future business requirement demands numerical confidence thresholds (e.g. confidence < 0.50 -> NO_ACTION), it must be formally governed as a new methodology specification.

OPTIONAL IMPROVEMENTS:
- Future policy module for explicit numerical confidence-to-actionability threshold gating.

SOUND COMPONENTS:
- `DecisionOrchestrator` decision pipeline logic (`integration/orchestrator.py`)
- `ActionEngine` precedence tiers & guardrails (`action/engine.py`)
- Suitability conditional evaluation & warning propagation
- Integration contract builders (`integration/contracts.py`)

DECISION-USE STATUS: APPROVED WITH GOVERNANCE LIMITATIONS (Reconciliation confirms decision engine correctness under governed v1.0.0 contracts)
PRODUCTION STATUS: FROZEN v1.0.0
UNRESOLVED ITEMS: NONE
```
