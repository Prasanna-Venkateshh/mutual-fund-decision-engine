# Phase F — Investor Suitability & Risk Alignment Engine Implementation Plan

**Document Status:** GOVERNED IMPLEMENTATION PLAN  
**Plan Version:** `1.0.0`  
**Phase:** Phase F — Specification & Implementation Planning Only (No Implementation in Phase F)

---

## 1. Executive Summary

This document defines the 11-stage implementation roadmap for building the **Investor Suitability & Risk Alignment Engine**. Each sub-phase is structured with explicit dependencies, module boundaries, acceptance criteria, test requirements, and governance controls.

---

## 2. Phased Implementation Roadmap

```
Phase F.1: Specification & Governance (COMPLETED IN PHASE F)
    ↓
Phase F.2: Data Contracts & Profile Persistence Dataclasses
    ↓
Phase F.3: Risk Capacity Evaluation Engine
    ↓
Phase F.4: Risk Tolerance Behavioral Evaluation Engine
    ↓
Phase F.5: Lower-of-the-Two Risk Alignment Orchestrator
    ↓
Phase F.6: Goal-Level Context & Time Horizon Engine
    ↓
Phase F.7: Affordability & Sustainable Contribution Engine
    ↓
Phase F.8: Existing Portfolio Context Integration
    ↓
Phase F.9: Material Change Detector & Reassessment Trigger
    ↓
Phase F.10: Suitability Explanation & Audit Repository
    ↓
Phase F.11: Comprehensive Test Suite & QA Validation
```

---

## 3. Detailed Sub-Phase Specifications

### Phase F.1 — Specification & Governance Documentation
- **Status:** `COMPLETED IN PHASE F`
- **Deliverables:** `docs/phase_f_suitability_risk_alignment_specification.md`, `docs/phase_f_suitability_risk_alignment_implementation_plan.md`.
- **Acceptance Criteria:** Full architectural boundary separation approved; traceability matrix updated.

---

### Phase F.2 — Data Contracts & Profile Persistence (`suitability/models.py`)
- **Target Modules:** `models/investor_profile.py`, `models/suitability_assessment.py`, `models/goal_profile.py`.
- **Dependencies:** `models/fund_quality_dataset.py`, `scoring/models.py`.
- **Key Responsibilities:** Define frozen dataclasses for `InvestorProfileSnapshot`, `FinancialCapacitySnapshot`, `BehavioralToleranceSnapshot`, `GoalProfile`, `SuitabilityAssessmentResult`.
- **Acceptance Criteria:** 100% immutable dataclasses (`frozen=True`), schema versioning fields included, full compatibility with `FundQualityScoreResult`.
- **Tests:** Contract serialization/deserialization tests.

---

### Phase F.3 — Risk Capacity Evaluation Engine (`suitability/capacity.py`)
- **Target Modules:** `suitability/capacity.py`.
- **Dependencies:** `models/investor_profile.py`.
- **Key Responsibilities:** Compute `RiskCapacityLevel` from emergency reserve cover, net savings ratio, debt servicing ratio, and liquid stability.
- **Financial Rules Requiring Validation:** Provisional Rule RC-01 (Income debt-servicing cap at 60%).
- **Acceptance Criteria:** High income with low reserves evaluates to `LOW` capacity. Deterministic scoring in range `[1, 5]`.
- **Tests:** Unit tests for emergency cover tiers, savings ratio edge cases, and debt-overload caps.

---

### Phase F.4 — Risk Tolerance Behavioral Engine (`suitability/tolerance.py`)
- **Target Modules:** `suitability/tolerance.py`.
- **Dependencies:** `models/investor_profile.py`.
- **Key Responsibilities:** Evaluate scenario questionnaire responses to compute `RiskToleranceLevel` and `behavioral_consistency_score`.
- **Acceptance Criteria:** Conflicting scenario responses trigger conservative lower-tier fallback and reduce consistency score.
- **Tests:** Single-question behavioral tests, contradictory response handling, and past crash action log integration.

---

### Phase F.5 — Lower-of-the-Two Risk Alignment Orchestrator (`suitability/alignment.py`)
- **Target Modules:** `suitability/alignment.py`, `suitability/config.py`.
- **Dependencies:** `suitability/capacity.py`, `suitability/tolerance.py`.
- **Key Responsibilities:** Enforce `Effective Risk Alignment = Min(Capacity, Tolerance)`.
- **Acceptance Criteria:** Aggressive risk tolerance with low financial capacity **never** yields a high-risk alignment.
- **Tests:** Matrix tests across all 25 Capacity × Tolerance combinations.

---

### Phase F.6 — Goal-Level Context & Time Horizon Engine (`suitability/horizon.py`)
- **Target Modules:** `suitability/horizon.py`.
- **Dependencies:** `suitability/alignment.py`, `models/goal_profile.py`.
- **Key Responsibilities:** Apply time-horizon ceiling rules to constrain maximum permissible asset class risk per goal.
- **Acceptance Criteria:** Goals with horizon $< 1$ year are strictly restricted to `ULTRA_LOW_RISK` debt assets.
- **Tests:** Horizon ceiling tests ($< 1$ yr, $1-3$ yrs, $3-5$ yrs, $> 5$ yrs).

---

### Phase F.7 — Affordability & Sustainable Contribution Engine (`suitability/affordability.py`)
- **Target Modules:** `suitability/affordability.py`.
- **Dependencies:** `suitability/capacity.py`, `models/goal_profile.py`.
- **Key Responsibilities:** Calculate sustainable monthly contribution capacity and generate funding gap resolution pathways.
- **Acceptance Criteria:** Funding gap triggers timeline/target adjustments without forcing an unsuitable risk tier increase.
- **Tests:** Sustainable capacity calculations, unaffordable goal pathway generation.

---

### Phase F.8 — Existing Portfolio Context Integration (`suitability/portfolio_context.py`)
- **Target Modules:** `suitability/portfolio_context.py`.
- **Dependencies:** `models/investor_profile.py`.
- **Key Responsibilities:** Incorporate existing asset allocation and concentration metrics as suitability input constraints.
- **Acceptance Criteria:** Consumes portfolio context without performing portfolio optimization or trade generation.
- **Tests:** Concentration ceiling tests, existing asset risk contribution tests.

---

### Phase F.9 — Material Change Detector & Reassessment Trigger (`suitability/reassessment.py`)
- **Target Modules:** `suitability/reassessment.py`.
- **Dependencies:** `models/investor_profile.py`.
- **Key Responsibilities:** Detect income shifts ($> 20\%$), goal updates, or stale profiles ($> 12$ months) and issue reassessment events.
- **Acceptance Criteria:** Material changes flag profile as stale and trigger reassessment notifications; zero automatic trades.
- **Tests:** Event detection unit tests, stale profile expiry tests.

---

### Phase F.10 — Suitability Explanation & Audit Repository (`suitability/explanations.py`, `suitability/repository.py`)
- **Target Modules:** `suitability/explanations.py`, `data/repositories/suitability_repository.py`.
- **Dependencies:** `suitability/alignment.py`.
- **Key Responsibilities:** Generate natural language explanations and persist immutable assessment audit logs.
- **Acceptance Criteria:** Human-readable explanations generated for every assessment status (`SUITABLE`, `NOT_SUITABLE`, etc.); append-only historical log.
- **Tests:** Rationale text generation tests, historical reproducibility tests.

---

### Phase F.11 — Comprehensive Test Suite & QA Validation (`tests/financial/test_suitability_engine.py`)
- **Target Modules:** `tests/financial/test_suitability_engine.py`.
- **Dependencies:** All `suitability/` modules.
- **Key Responsibilities:** Execute complete suite of 25+ suitability tests across Layer 1 (Software) and Layer 2 (Mathematical) validation, verifying zero regression against existing 170/170 project tests.
- **Acceptance Criteria:** 100% test pass rate across full repository. Layer 5 empirical financial calibration remains pending real demographic/regime data.

---

## 4. Summary Matrix

- **Total Implementation Phases:** 11 phases (F.1 to F.11)
- **Code Execution Status in Phase F / F.1.1:** 0 engine files created (Specification & Governance Correction only)
- **Target Output Directory:** `suitability/` package
- **Provisional Financial Rules Externalized:** 9 configurable parameters registered in Provisional Rule Register
- **Validation Framework:** 5-Layer Validation Framework enforced (Software, Math, Behavioral, Fiduciary, Empirical)
- **Regression Safety Boundary:** 170 / 170 baseline project tests preserved
