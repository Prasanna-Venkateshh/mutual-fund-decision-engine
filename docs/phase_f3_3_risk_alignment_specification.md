# Phase F.3.3 — Risk Alignment Methodology & Specification Document

**Phase:** Phase F.3.3 — Risk Alignment Methodology & Specification  
**Date:** 2026-09-10 UTC  
**Status:** Approved Specification  
**Final Decision:** `PHASE F.3.3 SPECIFICATION ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Design of the methodology, data contracts, lower-of-two constraint rules, alignment states, confidence handling, construct isolation, provenance preservation, explainability, test specification, and parameter register for the Risk Alignment layer (`Risk Capacity + Risk Tolerance → Risk Alignment`).

---

## 1. Executive Summary

Phase F.3.3 establishes the financially defensible methodology and architectural specification for combining two independently assessed investor constructs:
1. **Risk Capacity** (financial ability to absorb investment losses without destabilizing essential living expenses or debt obligations).
2. **Risk Tolerance** (behavioral willingness to endure market volatility, drawdown, and investment uncertainty).

### Core Governing Principle
$$\text{Aligned Risk Level} \le \text{Risk Capacity}$$
$$\text{Aligned Risk Level} \le \text{Risk Tolerance}$$

When both underlying assessments yield valid ordinal tiers:
$$\text{Aligned Risk Level} = \min(\text{Risk Capacity Level}, \text{Risk Tolerance Level})$$

The engine preserves the independent visibility of both constructs. It **never** averages Capacity and Tolerance, **never** allows high Risk Tolerance to override inadequate Risk Capacity, and **never** allows high Risk Capacity to force an uncomfortably high Risk Tolerance.

---

## 2. Governance Verification & Construct Separation

### Construct Audit Matrix

| Dimension | Risk Capacity | Risk Tolerance | Risk Alignment |
|---|---|---|---|
| **Underlying Construct** | Financial resilience & surplus | Psychological / behavioral willingness | Envelope of permissible risk |
| **Primary Inputs** | Income, debt, reserves, expenses | Loss reaction, volatility choice, drawdown behavior | Capacity & Tolerance results |
| **Primary Constraint** | Financial survivability bound | Behavioral comfort bound | Lower of Capacity & Tolerance |
| **Demographic Leakage** | Excluded | Excluded | Excluded |
| **Fund Quality Leakage** | Excluded | Excluded | Excluded |
| **Downstream Role** | Input to Alignment | Input to Alignment | Boundary for Suitability Engine |

### Verification Assertions
- **Independence:** Risk Capacity and Risk Tolerance are assessed by separate engines ([`risk/capacity_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_engine.py), [`risk/tolerance_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_engine.py)) without cross-contamination.
- **Lower-of-Two Guarantee:** The aligned level is strictly bounded by $\min(\text{Capacity}, \text{Tolerance})$.
- **No Replacement:** The underlying Capacity assessment result and Tolerance assessment result are preserved in full inside the Risk Alignment output contract.

---

## 3. Risk Alignment Model Architecture

```text
┌────────────────────────────────────────┐     ┌────────────────────────────────────────┐
│        Risk Capacity Engine            │     │        Risk Tolerance Engine           │
│    (Financial Resilience & Surplus)    │     │   (Behavioral Comfort & Drawdown)      │
└───────────────────┬────────────────────┘     └───────────────────┬────────────────────┘
                    │                                              │
                    │ RiskCapacityAssessmentResult                 │ RiskToleranceAssessmentResult
                    │                                              │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                       ┌───────────────────────────────────────┐
                       │        Risk Alignment Engine          │
                       │   (Enforces Lower-of-Two Constraint)   │
                       └───────────────────┬───────────────────┘
                                           │
                                           │ RiskAlignmentAssessmentResult
                                           ▼
                       ┌───────────────────────────────────────┐
                       │      Downstream Suitability Engine    │
                       │  (Evaluates Fund & Portfolio Match)   │
                       └───────────────────────────────────────┘
```

---

## 4. Input & Output Data Contracts

### Input Contracts
1. `RiskCapacityAssessmentResult` ([`risk/capacity_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_models.py#L55)): Contains `overall_capacity_tier`, `assessment_status`, `confidence_score`, `assessment_timestamp_utc`, `provenance`.
2. `RiskToleranceAssessmentResult` ([`risk/tolerance_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_models.py#L34)): Contains `overall_tolerance_tier`, `assessment_status`, `confidence_score`, `assessment_timestamp_utc`, `provenance`.
3. `InvestorProfileSnapshot` ([`models/investor_profile.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/models/investor_profile.py#L107)): Optional context container supplying profile identity and observation date.

### Output Contract Specification (`RiskAlignmentAssessmentResult`)
Defined in [`risk/alignment_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_models.py):

| Field Name | Type | Governance & Description |
|---|---|---|
| `assessment_id` | `str` | Unique UUID for the alignment execution record. |
| `investor_id` | `str` | Canonical investor identifier. |
| `profile_version_used` | `str` | Version of the investor profile snapshot evaluated. |
| `observation_date` | `date` | Effective date $T$ of the observation. |
| `assessment_timestamp_utc` | `datetime` | UTC timestamp of calculation execution. |
| `startup_mode` | `StartupMode` | Execution environment (`PRODUCTION`, `RESEARCH`, `TEST`). |
| `alignment_status` | `AlignmentStatus` | Controlled enum state (`FULLY_ALIGNED`, `CAPACITY_CONSTRAINED`, etc.). |
| `limiting_constraint` | `LimitingConstraint` | Identifies binding constraint (`RISK_CAPACITY`, `RISK_TOLERANCE`, `NONE`, etc.). |
| `aligned_risk_level` | `Optional[AlignedRiskLevel]` | Final ordinal risk envelope (`VERY_LOW` .. `VERY_HIGH` or `None`). |
| `risk_capacity_level` | `Optional[RiskCapacityLevel]` | Preserved Capacity tier from underlying result. |
| `risk_tolerance_level` | `Optional[RiskToleranceLevel]` | Preserved Tolerance tier from underlying result. |
| `capacity_assessment_id` | `Optional[str]` | Reference to underlying Capacity assessment ID. |
| `tolerance_assessment_id` | `Optional[str]` | Reference to underlying Tolerance assessment ID. |
| `capacity_confidence_score` | `float` | Preserved Capacity confidence score $[0.0, 1.0]$. |
| `tolerance_confidence_score` | `float` | Preserved Tolerance confidence score $[0.0, 1.0]$. |
| `alignment_confidence_score` | `float` | Derived alignment confidence score $[0.0, 1.0]$. |
| `explanation_tokens` | `List[str]` | Human-readable & machine-parseable explanation codes. |
| `missing_information_tokens` | `List[str]` | Structured codes for any missing underlying attributes. |
| `provenance` | `Optional[ProvenanceMetadata]` | Audit provenance combining inputs. |
| `is_stale_input` | `bool` | True if timestamp gap between inputs exceeds threshold. |
| `methodology_version` | `str` | Semantic methodology version (`1.0.0`). |
| `rule_version` | `str` | Semantic rule configuration version (`1.0.0`). |

---

## 5. Lower-of-Two Constraint Matrix

Ordinal Value Mapping:
- `VERY_LOW` = 1
- `LOW` = 2
- `MODERATE` = 3
- `HIGH` = 4
- `VERY_HIGH` = 5

### Alignment Matrix

| Capacity Level | Tolerance Level | Aligned Risk Level | Limiting Constraint | Alignment Status |
|---|---|---|---|---|
| `MODERATE` (3) | `MODERATE` (3) | `MODERATE` (3) | `NONE` | `FULLY_ALIGNED` |
| `LOW` (2) | `HIGH` (4) | `LOW` (2) | `RISK_CAPACITY` | `CAPACITY_CONSTRAINED` |
| `VERY_HIGH` (5) | `LOW` (2) | `LOW` (2) | `RISK_TOLERANCE` | `TOLERANCE_CONSTRAINED` |
| `HIGH` (4) | `HIGH` (4) | `HIGH` (4) | `NONE` | `FULLY_ALIGNED` |
| `VERY_LOW` (1) | `VERY_HIGH` (5) | `VERY_LOW` (1) | `RISK_CAPACITY` | `CAPACITY_CONSTRAINED` |
| `MODERATE` (3) | `VERY_LOW` (1) | `VERY_LOW` (1) | `RISK_TOLERANCE` | `TOLERANCE_CONSTRAINED` |

---

## 6. Complete Controlled Alignment States

1. **`FULLY_ALIGNED`**: Capacity Level == Tolerance Level. Both inputs are complete or partial valid assessments.
2. **`CAPACITY_CONSTRAINED`**: Capacity Level < Tolerance Level. Investor behavioral appetite exceeds financial capacity; financial capacity strictly limits exposure.
3. **`TOLERANCE_CONSTRAINED`**: Tolerance Level < Capacity Level. Investor financial resilience exceeds psychological comfort; behavioral preference strictly limits exposure.
4. **`PARTIAL_ALIGNMENT`**: One or both underlying assessments are `PARTIAL`, but valid ordinal tiers exist for both. An aligned level is calculated provisionally with a confidence penalty.
5. **`INSUFFICIENT_INFORMATION`**: One or both underlying assessments are `INSUFFICIENT_INFORMATION` or lack an ordinal tier (`None`). `aligned_risk_level` defaults to `None`.
6. **`INVALID_ASSESSMENT`**: Underlying inputs are corrupted, missing mandatory provenance, or contain incompatible data definitions. Halts execution safely.

---

## 7. Partial & Missing Data Handling Rules

| Input State Scenario | Aligned Risk Level | Alignment Status | Explanation Token Emitted |
|---|---|---|---|
| Complete Capacity + Complete Tolerance | Calculated $\min(C, T)$ | `FULLY_ALIGNED` / `CONSTRAINED` | `COMPLETE_ALIGNMENT_EVALUATED` |
| Partial Capacity + Complete Tolerance | Calculated $\min(C, T)$ | `PARTIAL_ALIGNMENT` | `PARTIAL_ALIGNMENT_CAPACITY_PARTIAL` |
| Complete Capacity + Partial Tolerance | Calculated $\min(C, T)$ | `PARTIAL_ALIGNMENT` | `PARTIAL_ALIGNMENT_TOLERANCE_PARTIAL` |
| Partial Capacity + Partial Tolerance | Calculated $\min(C, T)$ | `PARTIAL_ALIGNMENT` | `PARTIAL_ALIGNMENT_BOTH_INPUTS_PARTIAL` |
| Insufficient Capacity + Any Tolerance | `None` | `INSUFFICIENT_INFORMATION` | `INSUFFICIENT_DATA_CAPACITY_MISSING` |
| Any Capacity + Insufficient Tolerance | `None` | `INSUFFICIENT_INFORMATION` | `INSUFFICIENT_DATA_TOLERANCE_MISSING` |
| Both Insufficient | `None` | `INSUFFICIENT_INFORMATION` | `INSUFFICIENT_DATA_BOTH_MISSING` |

*Governance Rule:* Missing inputs **never** convert to zero, average, or conservative default risk tiers.

---

## 8. Confidence Methodology

### Derived Confidence Rationale
Alignment confidence reflects the weakest link in the underlying inputs. The formula is:

$$\text{Base Confidence} = \min(\text{Capacity Confidence Score}, \text{Tolerance Confidence Score})$$

If either underlying assessment status is `PARTIAL`:
$$\text{Alignment Confidence} = \min(\text{Base Confidence}, \text{partial\_alignment\_confidence\_cap})$$

### Fundamental Governance Rule
Confidence deductions **only** reduce `alignment_confidence_score`. Confidence **never** alters the ordinal `aligned_risk_level`.

---

## 9. Construct Isolation Verification

The Risk Alignment Engine evaluates **only** the outputs of the Risk Capacity and Risk Tolerance engines.

### Isolated Parameters (0 Direct Influence on Alignment)
- Age, gender, marital status, dependents.
- Raw income rupees, debt rupees, expense rupees (processed strictly via Capacity Engine).
- Investment horizon years, goal target date.
- Fund NAVs, fund returns, fund volatility, Sharpe ratio, Fund Quality Score.
- Macroeconomic inflation, interest rates, repo rate.

---

## 10. Suitability Boundary & Downstream Scope Control

```text
    Risk Capacity Engine          Risk Tolerance Engine
             │                             │
             └──────────────┬──────────────┘
                            ▼
                   Risk Alignment Engine
                 [ALIGNED RISK ENVELOPE]
                            │
              ══════════════╪══════════════  SUITABILITY BOUNDARY
                            │
                            ▼
                  Suitability Engine
             [Fund Category Matching]
                            │
                            ▼
               Portfolio / Action Engine
            [Buy / Hold / Sell Decisions]
```

Risk Alignment establishes the **permissible risk envelope**. It **does NOT**:
- Select individual mutual funds.
- Compute Fund Quality scores.
- Determine SIP amounts or goal affordability.
- Recommend Buy, Accumulate, Hold, or Sell actions.
- Perform portfolio rebalancing or tax optimization.

---

## 11. Assessment Versioning & Staleness Governance

### Timestamp Gap Governance
If the timestamp difference between the Risk Capacity assessment and Risk Tolerance assessment exceeds `max_assessment_age_gap_days` (Default: 90 days, PROVISIONAL):
- `is_stale_input` is set to `True`.
- Explanation token `STALE_ASSESSMENT_INPUT_GAP_EXCEEDED` is appended.
- Alignment confidence is multiplied by `stale_input_confidence_penalty` (Default: 0.85, PROVISIONAL).
- The calculated `aligned_risk_level` remains unchanged (no silent level modification).

---

## 12. Provenance & Audit Traceability

The output contract preserves complete lineage from both underlying assessments:
- `capacity_assessment_id`
- `tolerance_assessment_id`
- `capacity_confidence_score`
- `tolerance_confidence_score`
- `profile_version_used`
- `observation_date`
- `methodology_version`
- `rule_version`

This enables complete point-in-time historical reconstruction of any recommendation.

---

## 13. Structured Explainability Specifications

Every alignment result generates human-readable and machine-parseable explanation tokens:

1. **Fully Aligned:** `"Your financial capacity (MODERATE) and behavioral risk tolerance (MODERATE) are fully aligned."` (`FULLY_ALIGNED_CAPACITY_AND_TOLERANCE`)
2. **Capacity Constrained:** `"Your behavioral risk tolerance (HIGH) exceeds your financial capacity (LOW). Your aligned risk level is constrained to LOW by your financial capacity."` (`CONSTRAINED_BY_RISK_CAPACITY`)
3. **Tolerance Constrained:** `"Your financial capacity (VERY_HIGH) supports more risk than your behavioral tolerance (LOW). Your aligned risk level is constrained to LOW by your behavioral risk tolerance."` (`CONSTRAINED_BY_RISK_TOLERANCE`)
4. **Partial Inputs:** `"Aligned risk level is calculated as MODERATE based on partial underlying assessment data."` (`PROVISIONAL_ALIGNMENT_PARTIAL_INPUTS`)
5. **Insufficient Information:** `"Risk alignment cannot be calculated because Risk Capacity assessment is incomplete."` (`INSUFFICIENT_DATA_CAPACITY_MISSING`)

---

## 14. Complete Provisional Parameter Register

| Parameter Name | Purpose | Value | Governance Status | Configuration File |
|---|---|---|---|---|
| `partial_alignment_confidence_cap` | Cap confidence when an input is partial | `0.70` | `PROVISIONAL` | `config/risk/alignment_config.py` |
| `max_assessment_age_gap_days` | Max age difference between inputs | `90` | `PROVISIONAL` | `config/risk/alignment_config.py` |
| `stale_input_confidence_penalty` | Multiplier penalty for stale gap | `0.85` | `PROVISIONAL` | `config/risk/alignment_config.py` |
| `methodology_version` | Semantic methodology version | `"1.0.0"` | `APPROVED` | `config/risk/alignment_config.py` |
| `rule_version` | Semantic rule version | `"1.0.0"` | `APPROVED` | `config/risk/alignment_config.py` |

---

## 15. Comprehensive Test Specification (27 Scenarios)

### Core Lower-of-Two Alignment Tests (1–3)
1. **Capacity == Tolerance:** `MODERATE` & `MODERATE` $\rightarrow$ Aligned `MODERATE`, `FULLY_ALIGNED`, constraint `NONE`.
2. **Capacity < Tolerance:** `LOW` & `HIGH` $\rightarrow$ Aligned `LOW`, `CAPACITY_CONSTRAINED`, constraint `RISK_CAPACITY`.
3. **Tolerance < Capacity:** `VERY_HIGH` & `LOW` $\rightarrow$ Aligned `LOW`, `TOLERANCE_CONSTRAINED`, constraint `RISK_TOLERANCE`.

### Data Completeness & Partial Data Tests (4–10)
4. **Complete + Complete:** Produces `FULLY_ALIGNED` or `CONSTRAINED` with status `COMPLETE`.
5. **Partial Capacity + Complete Tolerance:** Both valid tiers present $\rightarrow$ Aligned tier calculated, status `PARTIAL_ALIGNMENT`, confidence capped at 0.70.
6. **Complete Capacity + Partial Tolerance:** Both valid tiers present $\rightarrow$ Aligned tier calculated, status `PARTIAL_ALIGNMENT`, confidence capped at 0.70.
7. **Partial + Partial:** Both valid tiers present $\rightarrow$ Aligned tier calculated, status `PARTIAL_ALIGNMENT`, confidence capped at 0.70.
8. **Insufficient Capacity + Complete Tolerance:** Capacity tier `None` $\rightarrow$ Aligned level `None`, status `INSUFFICIENT_INFORMATION`.
9. **Complete Capacity + Insufficient Tolerance:** Tolerance tier `None` $\rightarrow$ Aligned level `None`, status `INSUFFICIENT_INFORMATION`.
10. **Both Insufficient:** Both tiers `None` $\rightarrow$ Aligned level `None`, status `INSUFFICIENT_INFORMATION`.

### Confidence & Integrity Tests (11–19)
11. **High Confidence Inputs:** Capacity 1.0, Tolerance 1.0 $\rightarrow$ Alignment confidence 1.0.
12. **Reduced Capacity Confidence:** Capacity 0.60, Tolerance 1.0 $\rightarrow$ Alignment confidence 0.60.
13. **Reduced Tolerance Confidence:** Capacity 1.0, Tolerance 0.50 $\rightarrow$ Alignment confidence 0.50.
14. **Confidence Non-Mutation:** Reduced confidence does NOT alter calculated `aligned_risk_level`.
15. **Invalid Capacity Level:** Invalid enum value triggers `INVALID_ASSESSMENT`.
16. **Invalid Tolerance Level:** Invalid enum value triggers `INVALID_ASSESSMENT`.
17. **Missing Provenance:** Null provenance triggers safe fallback token `MISSING_PROVENANCE_WARNING`.
18. **Incompatible Profile Versions:** Mismatched `profile_version` raises validation warning token.
19. **Stale Assessment Input:** Assessment gap > 90 days flags `is_stale_input = True` and applies penalty.

### Construct Isolation & Determinism Tests (20–27)
20. **Demographic Isolation:** Investor age/income variations do not alter alignment result.
21. **Financial Data Isolation:** Financial changes inside capacity engine do not leak directly into tolerance.
22. **Horizon Isolation:** Goal horizon years do not alter alignment result.
23. **Fund Metrics Isolation:** Fund returns/volatility do not alter alignment result.
24. **Determinism:** Identical inputs produce identical outputs across multiple executions.
25. **Provenance Preservation:** Output retains both underlying assessment IDs and timestamps.
26. **Explainability Tokens:** Every valid state emits correct structured explanation tokens.
27. **Insufficient Explanation:** Insufficient states emit specific missing information tokens.

---

## 16. Scope Control

### In Scope
- Risk Alignment methodology design & specification.
- Lower-of-two constraint definition.
- Alignment states and limiting constraint classification.
- Input & output data contract definitions ([`risk/alignment_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_models.py)).
- Confidence derivation logic.
- Provenance and explainability specifications.
- Complete provisional parameter register.
- Test specification matrix.

### Out of Scope
- Production engine implementation ([`risk/alignment_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_engine.py)).
- Risk Capacity redesign or Risk Tolerance calibration changes.
- Downstream Suitability Engine implementation.
- Goal Engine, Fund Quality scoring, or portfolio allocation rules.
- Transaction execution, SIP calculation, or tax engine rules.

---

## 17. Governance QA Verification Results

| Governance QA Criterion | Status | Verification Summary |
|---|---|---|
| 1. Product & Arch Specs Reviewed | **PASS** | `PRODUCT_SPEC.md` §4, §8–10 & `ARCHITECTURE.md` §4, §11 reviewed. |
| 2. Construct Separation Preserved | **PASS** | Capacity and Tolerance remain 100% independent. |
| 3. Lower-of-Two Explicit | **PASS** | Formula $\min(C, T)$ explicitly governed. |
| 4. No Arbitrary Formulas Invented | **PASS** | Confidence derived strictly via $\min(C_{conf}, T_{conf})$. |
| 5. Zero Hidden Production Defaults | **PASS** | All parameters externalized in parameter inventory. |
| 6. Missing Data Safety | **PASS** | Missing data produces `INSUFFICIENT_INFORMATION`, not default risk. |
| 7. Partial Data Distinction | **PASS** | Partial inputs produce `PARTIAL_ALIGNMENT` with confidence cap. |
| 8. Confidence Separation | **PASS** | Confidence does not alter risk tiers. |
| 9. Construct Isolation Verified | **PASS** | Demographics, fund metrics, and horizon have 0 direct influence. |
| 10. Suitability Boundary Enforced | **PASS** | Alignment produces risk envelope only; no fund recommendations. |
| 11. Provenance Preserved | **PASS** | Preserves both input assessment IDs, timestamps, and versions. |
| 12. Test Coverage Documented | **PASS** | 27 test scenarios specified in detail. |

---

## 18. Changes Made in This Phase

1. **Created Data Contract Artifact:** [`risk/alignment_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_models.py) defining immutable `RiskAlignmentAssessmentResult`, `AlignmentStatus`, `LimitingConstraint`, and `AlignedRiskLevel`.
2. **Created Methodology Specification:** [`docs/phase_f3_3_risk_alignment_specification.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f3_3_risk_alignment_specification.md).
3. **Updated Traceability Matrix:** [`docs/documentation_traceability_matrix.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/documentation_traceability_matrix.md).

---

## 19. Regression Test Results

- **Command Executed:** `python -m pytest tests/ -v --tb=short`
- **Result:** **246 / 246 tests passed cleanly in 2.41 seconds (0 failures, 0 regressions)**.

---

## 20. Explicit Implementation Gate

```text
================================================================================
IMPLICIT EXECUTION GATE ENFORCED
================================================================================
Production Risk Alignment Engine implementation (risk/alignment_engine.py)
and downstream Suitability Engine implementation (Phase F.3.4+) are STRICTLY
BLOCKED in this phase.
================================================================================
```

---

## 21. Final Decision — Exactly One

```text
PHASE F.3.3 SPECIFICATION ACCEPTED WITH PROVISIONAL METHODOLOGY
```

*Note: Phase F.3.3 specification is accepted with provisional methodology. Production Risk Alignment Engine implementation (F.3.4 or subsequent engine phase) may NOT begin automatically.*
