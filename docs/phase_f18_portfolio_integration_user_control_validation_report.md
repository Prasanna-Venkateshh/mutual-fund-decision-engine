# Phase F.18 — Decision Engine Governance, Portfolio Integration & User-Control Validation Report

**Phase Identifier:** F.18  
**Status:** PASSED WITH LIMITATIONS  
**Audit Date:** 2026-09-16  
**Governed Orchestrator Class:** `integration.orchestrator.DecisionOrchestrator`  
**Production Methodology Frozen:** YES (v1.0.0)  

---

## 1. Executive Summary & Objective

Phase F.18 completes the architectural, state-management, safety, user-agency, and integration validation of the decision engine operating at portfolio level:

$$\text{DECISION ENGINE} \longrightarrow \text{PORTFOLIO INTEGRATION} \longrightarrow \text{USER CONTROL} \longrightarrow \text{ASSESSMENT HISTORY} \longrightarrow \text{REASSESSMENT / CHANGE MANAGEMENT}$$

### Primary Objective
To verify that the engine safely operates as a portfolio-level decision-support system **without silently changing investor state, creating unintended turnover, overriding user constraints, or confusing recommendations with transactions**.

### Key Validation Findings
1. **Strict Layer Separation:** The decision engine emits immutable recommendation contracts (`EndToEndDecisionResult`). It never places trades, mutates holdings, or alters monthly SIP amounts.
2. **Zero Silent State Mutation:** Across all 25 portfolio scenarios, 0 holdings, 0 SIPs, 0 goal targets, and 0 timelines were mutated by assessment generation.
3. **User Control & Agency:** User rejection of a recommendation leaves portfolio state 100% untouched. User adjustments (e.g. adjusting a ₹10,000 recommendation to ₹5,000) recalculate impact while preserving system recommendations separately in the audit log.
4. **Living Profile & Immutable History:** Updating an investor's profile triggers a distinct versioned assessment ($v_2$). Historical assessments ($v_1$) remain frozen and immutable.
5. **Anti-Churn Principles:** Low Fund Quality alone on an existing holding never triggers a `SELL` action. Anti-churn guardrails require validated material deterioration, a suitable replacement, and net positive after-cost economic benefit before a `SELL` recommendation can occur.

---

## 2. Core Architecture & Layer Separation

```
[ ASSESSMENT ]  --> Emits immutable EndToEndDecisionResult
      │
      ▼
[ RECOMMENDATION ] --> Displays system advice & rationale to user
      │
      ▼
[ USER REVIEW ]     --> User inspects, edits contribution, or rejects
      │
      ▼
[ USER CONFIRMATION ] -> Explicit user confirmation required
      │
      ▼
[ TRANSACTION / EXECUTION ] -> External execution layer (strictly unbuilt/decoupled in decision engine)
```

---

## 3. Required Portfolio Decision Matrix

All 25 deterministic portfolio scenarios were executed directly through `DecisionOrchestrator`:

| Scenario ID & Description | FQ | Suitability | Portfolio Need | Economic Benefit | Portfolio Context | User State | Action State | Result |
|---|---|---|---|---|---|---|---|---|
| **P1:** High FQ + Suitable + Genuine Need + Beneficial | 90.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | BUY | **PASS** |
| **P2:** High FQ + Unsuitable Investor Profile | 95.0 | NOT_SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | NO_ACTION | **PASS** |
| **P3:** High FQ + No Portfolio Need | 95.0 | SUITABLE | NO_MATERIAL_NEED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | NO_ACTION | **PASS** |
| **P4:** High FQ + Excessive Overlap Constraint | 95.0 | SUITABLE | CANNOT_FULFILL_NEED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | NO_ACTION | **PASS** |
| **P5:** High FQ + Risk Capacity Constrained | 90.0 | NOT_SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | NO_ACTION | **PASS** |
| **P6:** High FQ + Risk Tolerance Constrained | 90.0 | NOT_SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | NO_ACTION | **PASS** |
| **P7:** Low FQ + Existing Holding (No Deterioration) | 15.0 | SUITABLE | NO_MATERIAL_NEED | NO_EVALUABLE_CHANGE | EXISTING_POSITION | NONE | HOLD | **PASS** |
| **P8:** Low FQ + Deterioration + Replacement + Beneficial | 15.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | EXISTING_POSITION | NONE | SELL | **PASS** |
| **P9:** Low FQ + High Switching Cost / Friction | 15.0 | SUITABLE | NO_MATERIAL_NEED | NOT_BENEFICIAL | EXISTING_POSITION | NONE | REVIEW | **PASS** |
| **P10:** Low FQ + No Suitable Replacement | 15.0 | SUITABLE | NO_MATERIAL_NEED | ECONOMICALLY_BENEFICIAL | EXISTING_POSITION | NONE | REVIEW | **PASS** |
| **P11:** Missing Essential FQ Evidence | 90.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | NO_ACTION | **PASS** |
| **P12:** Immature Fund History | 85.0 | CONDITIONALLY_SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | BUY | **PASS** |
| **P13:** New Money Allocation Opportunity | 88.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | BUY | **PASS** |
| **P14:** Switch Opportunity With Friction | 15.0 | SUITABLE | NO_MATERIAL_NEED | NOT_BENEFICIAL | EXISTING_POSITION | NONE | REVIEW | **PASS** |
| **P15:** Multiple Goals (Targeted Fulfillment) | 85.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | BUY | **PASS** |
| **P16:** Windfall Capital Distribution | 90.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | BUY | **PASS** |
| **P17:** Goal Target Increase Reassessment | 90.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | BUY | **PASS** |
| **P18:** Goal Target Decrease Reassessment | 90.0 | SUITABLE | NO_MATERIAL_NEED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | NO_ACTION | **PASS** |
| **P19:** Affordability Constrained | 88.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | ACCUMULATE | **PASS** |
| **P20:** Material Income Change Reassessment | 90.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | BUY | **PASS** |
| **P21:** Portfolio Over-Concentration Limit | 90.0 | SUITABLE | EXCESS_EXPOSURE | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | NO_ACTION | **PASS** |
| **P22:** Repeated Assessment Identical Recommendation | 90.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | BUY | **PASS** |
| **P23:** Temporal Integrity (Past Assessment Frozen) | 90.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | NONE | BUY | **PASS** |
| **P24:** User Rejection of Recommendation | 90.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | REJECTED | BUY | **PASS** |
| **P25:** User Adjustment of Contribution (10k -> 5k) | 88.0 | SUITABLE | NEED_IDENTIFIED | ECONOMICALLY_BENEFICIAL | NEW_POSITION | ADJUSTED | ACCUMULATE | **PASS** |

---

## 4. Required State-Mutation Matrix

Verifies zero silent state mutation across all decision engine operations:

| Operation | Investor Profile | Goal Profiles | Holdings | SIPs | Target Amounts | Timelines | Transactions Executed |
|---|---|---|---|---|---|---|---|
| **Assessment Evaluation** | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | NONE (0) |
| **Recommendation Emission** | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | NONE (0) |
| **User Rejection** | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | NONE (0) |
| **User Adjustment** | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | NONE (0) |
| **Reassessment Trigger** | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | NONE (0) |

---

## 5. Required Reassessment Matrix

| Trigger Event | Previous Assessment ($v_1$) | New Assessment ($v_2$) | Changed Inputs | Action Transition | User Confirmation Required |
|---|---|---|---|---|---|
| **Goal Target Increase** | BUY ($v_1$) | BUY ($v_2$) | Target Amount Increased | BUY $\rightarrow$ BUY (Higher Gap) | YES |
| **Goal Target Decrease** | BUY ($v_1$) | NO_ACTION ($v_2$) | Target Amount Reduced | BUY $\rightarrow$ NO_ACTION | YES |
| **Material Income Drop** | BUY ($v_1$) | ACCUMULATE ($v_2$) | Sustainable Monthly Capacity | BUY $\rightarrow$ ACCUMULATE | YES |
| **Category Over-Concentration** | BUY ($v_1$) | NO_ACTION ($v_2$) | Category Exposure Breach | BUY $\rightarrow$ NO_ACTION | YES |
| **Material Scheme Deterioration** | HOLD ($v_1$) | SELL ($v_2$) | Deterioration Signal Validated | HOLD $\rightarrow$ SELL | YES |

---

## 6. Required Claim Matrix

| Claim | Architectural & Empirical Evidence | Governed Status |
|---|---|---|
| **Assessment is separate from transaction execution** | `DecisionOrchestrator` emits immutable `EndToEndDecisionResult` contracts; zero order APIs exist. | **SUPPORTED** |
| **Recommendations do not silently mutate portfolio state** | Holdings, SIPs, goals, and targets remained 100% unchanged across 25 scenarios. | **SUPPORTED** |
| **User rejection preserves portfolio state** | Portfolio state snapshot before/after rejection is identical. | **SUPPORTED** |
| **User adjustment is distinguished from system recommendation** | Audit record preserves system recommended value alongside user-adjusted value. | **SUPPORTED** |
| **Historical assessments remain immutable** | Profile updates emit $v_2$ result; $v_1$ snapshot remains frozen and unchanged. | **SUPPORTED** |
| **Material changes can trigger reassessment where governed** | Goal target/income changes produce distinct new versioned assessments. | **SUPPORTED** |
| **Multiple goals remain distinct** | Goal-specific candidate fulfillment is evaluated independently per `goal_id`. | **SUPPORTED** |
| **Portfolio context affects candidate evaluation** | `EXCESS_EXPOSURE` inhibits `BUY` recommendations. | **SUPPORTED** |
| **New money is distinguished from switching** | New money evaluates EB without switching frictions; switch evaluates tax/exit loads. | **SUPPORTED** |
| **Switching costs can inhibit action** | High switching cost / non-beneficial EB gates `SELL` to `REVIEW`. | **SUPPORTED** |
| **Concentration does not automatically trigger SELL** | Over-concentration prevents new `BUY`/`ACCUMULATE` without forcing asset liquidation. | **SUPPORTED** |
| **Missing required evidence restricts consequential action** | `fund_quality_evidence_valid=False` restricts `NEW_POSITION` to `NO_ACTION`. | **SUPPORTED** |
| **Temporal integrity is preserved** | Historical assessment at $T$ cannot consume data after $T$. | **SUPPORTED** |
| **"What changed?" is explainable** | Decision explanations detail FQ score, Suitability, Need, EB, and Action reason codes. | **SUPPORTED** |
| **Audit history reconstructs the decision state** | `UserDecisionRecord` and `EndToEndDecisionResult` provide full audit traceability. | **SUPPORTED** |
| **Repeated assessments are deterministic** | Repeated runs across all 25 scenarios produce 100% identical outputs. | **SUPPORTED** |

---

## 7. Classification of Findings

### 🔴 Genuine Defects (0)
- None.

### 🟠 Material Governance / Methodology Concerns (0)
- None.

### 🟡 Provisional Assumptions (1)
- **External Order Execution Layer:** The engine operates strictly as a decision-support system. Transaction submission infrastructure is deliberately out of scope and unbuilt.

### 🔵 Optional Improvements (1)
- **Interactive Reassessment Differential Dashboard:** UI diff tool showing side-by-side comparison of $v_1$ vs $v_2$ assessment outputs upon profile changes.

### 🟢 Sound Components (7)
1. `DecisionOrchestrator` decision pipeline (`integration/orchestrator.py`).
2. Recommendation vs Transaction separation architecture.
3. User agency preservation & adjustment recording contracts.
4. Portfolio state immutability safeguards.
5. Goal-level candidate fulfillment evaluation.
6. Economic Benefit switching cost & friction gating.
7. Immutable assessment history versioning.

---

## 8. Final Status Summary

```
FINAL STATUS: PASSED WITH LIMITATIONS

TESTS:
- scripts/run_f18_portfolio_integration_user_control_validation.py (25/25 passed, 100%)
- tests/data_quality/test_phase_f18_portfolio_integration_user_control.py (14/14 passed, 100%)
- pytest tests/data_quality/ (100% passed across all data quality suites)

PRODUCTION METHODOLOGY CHANGED: NO

PORTFOLIO INTEGRATION: PASSED (Evaluates category exposure, fulfillment, and concentration limits)
GOAL INTEGRATION: PASSED (Supports multiple independent goals per investor)
MULTI-GOAL RESULT: PASSED (Fulfillment evaluated independently per goal_id without cross-leakage)
NEW MONEY VS SWITCH: PASSED (New money evaluated without switching friction; switch checks tax/load)
CONCENTRATION / OVERLAP: PASSED (Over-exposure inhibits BUY without forcing market liquidation)
AFFORDABILITY: PASSED (Affordability-constrained scenarios yield ACCUMULATE)
WINDFALL: PASSED (Windfall capital evaluated at goal/portfolio level)
REASSESSMENT: PASSED (Material change triggers distinct v2 assessment)
MATERIAL CHANGE: PASSED (Income/target changes re-evaluate gap while keeping v1 immutable)
IMMUTABLE HISTORY: PASSED (Old assessment snapshots remain frozen)
RECOMMENDATION VS TRANSACTION: PASSED (100% decoupled; zero trade executions)
USER REJECTION: PASSED (User rejection leaves portfolio state untouched)
USER ADJUSTMENT: PASSED (User adjustment preserved separately from system recommendation)
STATE MUTATION: PASSED (0 holdings, 0 SIPs, 0 targets, 0 timelines mutated)
TAX / COST GATING: PASSED (Non-beneficial EB gates action to REVIEW)
MISSING-DATA BEHAVIOR: PASSED (Missing essential evidence safely inhibits consequential actions)
TEMPORAL SAFETY: PASSED (Point-in-time observation dates strictly preserved)
EXPLAINABILITY: PASSED (100% of decisions explain FQ, Suitability, Need, EB, and Action reasons)
AUDITABILITY: PASSED (Full decision traceability across SYSTEM, USER, and ASSESSMENT records)
DETERMINISM: PASSED (100% identical outputs on repeated runs)

DECISION-CHAIN STATUS: VERIFIED
DECISION-USE STATUS: APPROVED WITH GOVERNANCE LIMITATIONS (System verified as safe decision-support engine; transaction execution remains decoupled)
PRODUCTION STATUS: FROZEN v1.0.0
UNRESOLVED ITEMS: NONE
```
