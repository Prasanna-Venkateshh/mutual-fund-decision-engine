# Phase F.3.4.3 — Suitability Decision Logic Specification, Rule Matrix & Precedence (Governance Corrected)

**Phase:** Phase F.3.4.3 — Suitability Decision Logic Correction & Governance Gate  
**Date:** 2026-09-10 UTC  
**Status:** Approved Corrected Specification  
**Final Decision:** `PHASE F.3.4.3 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Corrected business decision logic, rule matrix, precedence hierarchy, conflict resolution, missing data handling, and governance audit for the Suitability Engine.

---

## 1. Governance Verification & Defect Corrections

The previous draft of Phase F.3.4.3 contained numerical threshold contradictions (`Fund Quality >= 90`, `Fund Quality < 30`, `Short Horizon -> NOT_SUITABLE` hard rejection, mechanical young fund rejection) that violated the F.3.4.1 governance corrections. This document completely removes those unsupported cutoffs and establishes a financially sound decision tree.

### Summary of Defects Corrected:
1. **Removed Arbitrary Fund Quality Cutoffs:** Completely eliminated `Fund Quality >= 90` and `Fund Quality < 30`. Fund Quality is consumed as contextual evidence (`FundQualityScore`, `confidence_score`, completeness), not as an arbitrary hard threshold.
2. **Removed Mechanical Young Fund Rejections:** Young/immature funds ($< 1$ year) consume upstream `FundMaturity` status. They affect evidence confidence and conditionality, but **never** cause automatic mechanical rejections.
3. **Removed Hard Horizon Rejection:** Removed `Short Horizon -> NOT_SUITABLE` hard rule. Horizon compatibility uses conceptual outcomes (`HORIZON_COMPATIBLE`, `HORIZON_CONCERN`, `HORIZON_UNKNOWN`).
4. **Enforced Riskometer Mapping Isolation:** Sourced `FundRiskProfile` explicitly without assuming `SEBI Riskometer = Investor RiskLevel 1-5`.
5. **Removed Portfolio Percentage Thresholds:** Portfolio overlap and AMC concentration use conceptual classifications (`HEALTHY`, `MATERIAL`, `EXCESSIVE`, `UNKNOWN`) without hard-coded percentages in core decision logic.

---

## 2. Core Architectural Boundary & Scope

The Suitability Engine answers:
> *"Given this investor, this fund, this goal/context, and the available evidence, is this investment appropriate?"*

Suitability does **NOT** answer *"Should the investor buy this?"* (reserved downstream for Economic Benefit / Action Engine).

```text
DATA → METRIC ENGINE → FUND QUALITY → RISK ALIGNMENT → SUITABILITY → PORTFOLIO NEED / ECONOMIC BENEFIT → ACTION / EXECUTION
```

---

## 3. Five Suitability States Semantics & Fund Maturity Clarification

1. **`SUITABLE`**: Sufficient evidence exists. No governed material incompatibility is identified. Contextual concerns are not sufficiently material to prevent an unconditional conclusion.
2. **`CONDITIONALLY_SUITABLE`**: The investment may be appropriate, but one or more documented contextual concerns prevent an unconditional conclusion.
3. **`NOT_SUITABLE`**: Sufficient evidence establishes a material incompatibility under an approved/governed Suitability rule (e.g. verified risk envelope violation, statutory lock-in conflict).
4. **`INSUFFICIENT_INFORMATION`**: Evidence required for a responsible conclusion is unavailable, incomplete, unknown, or stale beyond acceptable use.
5. **`INVALID_ASSESSMENT`**: Inputs violate structural/data contracts or contain invalid information preventing assessment.

*Governance Guarantee:* Missing data $\ne$ `NOT_SUITABLE`; Unknown $\ne$ `UNSUITABLE`; Invalid $\ne$ `MISSING`.

### Fund Maturity Explicit Governance Boundary:
Fund Maturity is consumed from the upstream Fund Maturity framework as an evidence/maturity characteristic. Immaturity affects evidence completeness, evidence confidence, and contextual explanation, but immaturity ALONE must **NOT** automatically determine `SUITABLE`, `CONDITIONALLY_SUITABLE`, or `NOT_SUITABLE`. Immaturity contributes to a `CONDITIONALLY_SUITABLE` conclusion only when combined with another separately governed contextual concern (such as an unvalidated track record under high category volatility). Zero mechanical age cutoffs (e.g., $<1$ year) are permitted to directly alter Suitability state.

---

## 4. Decision-First Pipeline & Rule Precedence Hierarchy

Evaluation follows a strict precedence hierarchy (zero weighted scores):

$$\text{INVALID\_ASSESSMENT} > \text{INSUFFICIENT\_INFORMATION} > \text{HARD\_CONSTRAINT} > \text{CONDITIONAL\_CONCERN} > \text{POSITIVE\_EVIDENCE}$$

```text
                       ┌─────────────────────────┐
                       │  Step 1: Invalidation   │
                       └────────────┬────────────┘
                                    │
                         Is contract/input valid?
                         /                     \
                   NO   /                       \   YES
                       ▼                         ▼
          ┌─────────────────────────┐ ┌─────────────────────────┐
          │   INVALID_ASSESSMENT    │ │ Step 2: Information Req │
          └─────────────────────────┘ └────────────┬────────────┘
                                                   │
                                      Is required evidence present?
                                      /                         \
                                NO   /                           \   YES
                                    ▼                             ▼
                       ┌─────────────────────────┐ ┌─────────────────────────┐
                       │INSUFFICIENT_INFORMATION │ │Step 3: Hard Constraints │
                       └─────────────────────────┘ └────────────┬────────────┘
                                                                │
                                                    Any Hard Bound Violated?
                                                    /                       \
                                              YES  /                         \   NO
                                                  ▼                           ▼
                                     ┌─────────────────────────┐ ┌─────────────────────────┐
                                     │      NOT_SUITABLE       │ │ Step 4: Conditionals    │
                                     └─────────────────────────┘ └────────────┬────────────┘
                                                                              │
                                                                   Any Conditional Concern?
                                                                   /                       \
                                                             YES  /                         \   NO
                                                                 ▼                           ▼
                                                    ┌─────────────────────────┐ ┌─────────────────────────┐
                                                    │ CONDITIONALLY_SUITABLE  │ │        SUITABLE         │
                                                    └─────────────────────────┘ └─────────────────────────┘
```

---

## 5. Comprehensive Rule Matrix

| Rule ID | Category | Input / Trigger | Result Effect | Missing Data Behavior | Invalid Data Behavior | Confidence Effect | Owner | Governance Status | Token Emitted |
|---|---|---|---|---|---|---|---|---|---|
| `R-INV-1` | `INVALIDATION` | Malformed object / negative confidence | `INVALID_ASSESSMENT` | Emits Missing Token | Halt | $0.0$ | Data Validation | `APPROVED` | `INVALID_INPUT_DATA` |
| `R-INF-1` | `INFORMATION_REQ` | Missing Risk Alignment Assessment | `INSUFFICIENT_INFORMATION` | Halt | `INVALID_ASSESSMENT` | $0.0$ | Risk Alignment | `APPROVED` | `MISSING_RISK_ALIGNMENT` |
| `R-INF-2` | `INFORMATION_REQ` | Unmapped Fund Category | `INVALID_ASSESSMENT` | Halt | `INVALID_ASSESSMENT` | $0.0$ | Scheme Master | `APPROVED` | `UNMAPPED_FUND_CATEGORY` |
| `R-HARD-1` | `HARD_CONSTRAINT` | Fund Risk Profile > Aligned Risk Envelope | `NOT_SUITABLE` | `INSUFFICIENT` | `INVALID` | Unaffected | Risk Alignment | `PROVISIONAL / TBD` | `RISK_EXCEEDS_ALIGNED_ENVELOPE` |
| `R-HARD-2` | `HARD_CONSTRAINT` | Authoritative Lock-In > Goal Horizon | `NOT_SUITABLE` | `INSUFFICIENT` | `INVALID` | Unaffected | Scheme Master / Data Provider | `PROVISIONAL / TBD` | `STATUTORY_LOCKIN_HORIZON_CONFLICT` |
| `R-COND-1` | `CONDITIONAL` | Lower-Risk Fund Profile (Below Envelope) | `SUITABLE` | N/A | N/A | Unaffected | Risk Alignment | `PROVISIONAL` | `LOWER_RISK_CONTEXT_WARNING` |
| `R-COND-2` | `CONDITIONAL` | Goal Horizon Contextual Mismatch | `CONDITIONALLY_SUITABLE` | `GENERAL_WEALTH` | `INVALID` | Reduced Confidence | Goal Profile | `PROVISIONAL / TBD` | `HORIZON_MISMATCH_CONCERN` |
| `R-COND-3` | `CONDITIONAL` | Material Security Overlap | `CONDITIONALLY_SUITABLE` | Ignore | `INVALID` | Reduced Confidence | Portfolio Subsystem | `PROVISIONAL / TBD` | `MATERIAL_PORTFOLIO_OVERLAP` |
| `R-COND-4` | `CONDITIONAL` | High AMC Exposure | `CONDITIONALLY_SUITABLE` | Ignore | `INVALID` | Reduced Confidence | Portfolio Subsystem | `PROVISIONAL / TBD` | `HIGH_AMC_CONCENTRATION` |
| `R-COND-5` | `CONDITIONAL` | Immature Fund / Limited History | `CONDITIONALLY_SUITABLE` | `INSUFFICIENT` | `INVALID` | Reduced Evidence Confidence | Fund Maturity | `APPROVED` | `NEW_FUND_LIMITED_HISTORY` |
| `R-POS-1` | `POSITIVE_EVIDENCE` | Compatible Risk & Timeline + Strong Quality | `SUITABLE` | N/A | N/A | Unaffected | Fund Quality | `APPROVED` | `SUITABLE_RISK_AND_HORIZON_MATCH` |

---

## 6. Signal Conflict Resolution Matrix

| Conflict Scenario | Winning Precedence Level | Resulting Suitability State | Confidence Effect | Rationale & Governance Rule |
|---|---|---|---|---|
| High Fund Quality Score + Verified Over-Risk Violation | `HARD_CONSTRAINT` | `NOT_SUITABLE` | Unaffected | High quality **cannot** override an aligned risk envelope violation. |
| High Fund Quality Score + Authoritative Lock-In Conflict | `HARD_CONSTRAINT` | `NOT_SUITABLE` | Unaffected | High quality **cannot** override a legal lock-in conflict. |
| Compatible Risk + Immature Fund Track Record | `CONDITIONAL_CONCERN` | `CONDITIONALLY_SUITABLE` | Reduced Evidence Confidence | Immature fund affects evidence availability/confidence; does not cause hard rejection. |
| Compatible Risk + Material Portfolio Overlap | `CONDITIONAL_CONCERN` | `CONDITIONALLY_SUITABLE` | Reduced Confidence | Overlap triggers portfolio warning without disqualifying fund. |
| Partial Risk Alignment + Strong Fund Quality | `INFORMATION_REQ` | `CONDITIONALLY_SUITABLE` | Reduced Confidence | Partial upstream evidence caps confidence; does not trigger hard rejection. |
| Insufficient Risk Alignment + Strong Fund Quality | `INFORMATION_REQ` | `INSUFFICIENT_INFORMATION` | $0.0$ | High fund quality **cannot** replace missing investor risk alignment. |
| Stale Risk Alignment + Favorable Fund Evidence | `INFORMATION_REQ` | `CONDITIONALLY_SUITABLE` | Reduced Confidence | Stale input degrades confidence; leaves risk tier unchanged. |

---

## 7. Numerical Parameter Governance Register

| Parameter Name | Value | Purpose | Source | Governance Status | Validation Required |
|---|---|---|---|---|---|
| `horizon_equity_min_years` | `TBD` | Min goal horizon for equity funds | Industry Practice | `PROVISIONAL / TBD` | Empirical risk study |
| `horizon_hybrid_min_years` | `TBD` | Min goal horizon for hybrid funds | Industry Practice | `PROVISIONAL / TBD` | Empirical risk study |
| `horizon_debt_min_years` | `TBD` | Min goal horizon for debt funds | Industry Practice | `PROVISIONAL / TBD` | Duration audit |
| `overlap_material_threshold` | `TBD` | Material security overlap cutoff | Diversification Practice | `PROVISIONAL / TBD` | Overlap study |
| `overlap_excessive_threshold` | `TBD` | Excessive security overlap cutoff | Diversification Practice | `PROVISIONAL / TBD` | Overlap study |
---

## 7.1 Future Implementation Methodology Boundary & Explicit TBD Register

Future implementation can proceed without inventing methodology that has already been specified. However, explicitly unresolved `PROVISIONAL / TBD` methodology must remain governed and must **NOT** be silently promoted to production logic without empirical validation.

### Explicit PROVISIONAL / TBD Register:
1. **FundRiskProfile $\rightarrow$ RiskAlignment Compatibility:** Sourced `FundRiskProfile` mapping to investor `RiskLevel 1–5` remains unvalidated.
2. **Lock-In Compatibility:** Source authority and compatibility rules for non-statutory lock-in structures remain `TBD`.
3. **Horizon Compatibility:** Category-specific goal horizon minimums remain `PROVISIONAL / TBD` and must not cause hard rejections.
4. **Portfolio Overlap & Concentration:** Quantitative thresholds ($30\%/60\%$ overlap, $40\%$ AMC) remain `PROVISIONAL / TBD`.
---

## 7.2 Planned Future Decision-Logic Test Suite Register (23 Scenarios)

The following 23 scenarios are formally recorded as **PLANNED FUTURE TESTS** for the future production Suitability Engine (`tests/financial/test_suitability_engine.py`):

1. **Hard Incompatibility Scenario:** Verified over-risk violation $\rightarrow$ `NOT_SUITABLE`.
2. **Conditional Concern Scenario:** Immature fund + volatility concern $\rightarrow$ `CONDITIONALLY_SUITABLE`.
3. **Positive Evidence Scenario:** Aligned risk & timeline + high quality $\rightarrow$ `SUITABLE`.
4. **Insufficient Information Scenario:** Missing Risk Alignment $\rightarrow$ `INSUFFICIENT_INFORMATION`.
5. **Invalid Assessment Scenario:** Negative confidence or malformed input $\rightarrow$ `INVALID_ASSESSMENT`.
6. **Risk Compatibility Scenario:** Aligned risk level matching fund risk envelope.
7. **Risk Mismatch Candidate Scenario:** Fund risk exceeding investor aligned level.
8. **Unknown Riskometer Mapping Scenario:** Sourced Riskometer value unmapped to 1-5 scale $\rightarrow$ `PROVISIONAL`.
9. **Horizon Concern Scenario:** Goal horizon mismatch with fund duration context.
10. **Horizon Unknown Scenario:** Missing goal horizon in Goal-Linked context $\rightarrow$ `CONDITIONALLY_SUITABLE`.
11. **Lock-In Conflict Scenario:** Statutory lock-in exceeding goal target date $\rightarrow$ `NOT_SUITABLE`.
12. **Lock-In Unknown Scenario:** Missing lock-in data $\ne$ zero lock-in.
13. **Immature Fund (No Other Concern) Scenario:** Immature fund alone $\rightarrow$ Reduced Evidence Confidence (does NOT force `CONDITIONALLY_SUITABLE`).
14. **Immature Fund (With Other Concern) Scenario:** Immature fund + volatility concern $\rightarrow$ `CONDITIONALLY_SUITABLE`.
15. **Portfolio Overlap Concern Scenario:** High security overlap $\rightarrow$ `CONDITIONALLY_SUITABLE`.
16. **Missing Portfolio Scenario:** Absent portfolio context $\rightarrow$ Standalone assessment performed without inferring zero overlap.
17. **Partial Risk Alignment Scenario:** Partial upstream input $\rightarrow$ Reduced confidence cap ($0.70$).
18. **Insufficient Risk Alignment Scenario:** Insufficient capacity/tolerance $\rightarrow$ `INSUFFICIENT_INFORMATION`.
19. **Conflicting Evidence Scenario:** Multi-source conflict $\rightarrow$ Reduced confidence penalty.
20. **Multiple Concerns Scenario:** Horizon + overlap concerns $\rightarrow$ Combined confidence degradation.
21. **Lower-Risk Fund Scenario:** Fund risk below investor envelope $\rightarrow$ `SUITABLE` with contextual warning.
22. **High Quality + Hard Incompatibility Scenario:** High Fund Quality Score + risk violation $\rightarrow$ `NOT_SUITABLE` (Quality cannot override).
23. **Low Quality + Compatible Context Scenario:** Low Fund Quality Score + aligned risk/horizon $\rightarrow$ Evaluated on context (no automatic rejection).

---

## 8. Regression Verification

- **Command Executed:** `python -m pytest tests/ -v --tb=short`
- **Result:** **286 / 286 passed cleanly in 1.08s**. Zero regressions.

---

## 9. Final Decision — Exactly One

```text
PHASE F.3.4.3 ACCEPTED WITH PROVISIONAL METHODOLOGY
```

---

## 10. Explicit Downstream Gate

```text
================================================================================
IMPLICIT EXECUTION GATE ENFORCED
================================================================================
Production Suitability Engine implementation (risk/suitability_engine.py or similar)
is STRICTLY BLOCKED in this phase.
It requires separate explicit user authorization and a dedicated task prompt.
================================================================================
```
