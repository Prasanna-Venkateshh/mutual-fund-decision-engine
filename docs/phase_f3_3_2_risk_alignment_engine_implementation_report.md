# Phase F.3.3.2 — Risk Alignment Engine Implementation Report

**Phase:** Phase F.3.3.2 — Risk Alignment Engine Implementation  
**Date:** 2026-09-10 UTC  
**Status:** Completed  
**Final Decision:** `PHASE F.3.3.2 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Production implementation of the Risk Alignment Engine ([`risk/alignment_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_engine.py)), input validation, lower-of-two ordinal evaluation, state classification, confidence propagation, staleness logic, provenance preservation, structured explanation tokens, test suite, and documentation update.

---

## 1. Executive Summary

Phase F.3.3.2 delivers the production implementation of the **Risk Alignment Engine** (`Risk Capacity + Risk Tolerance → Risk Alignment`).

The engine enforces the approved lower-of-two constraint:
$$\text{Aligned Risk Level} = \min(\text{Risk Capacity Level}, \text{Risk Tolerance Level})$$

The engine preserves the independent visibility of both constructs. It **never** averages Capacity and Tolerance, **never** allows high Risk Tolerance to override inadequate Risk Capacity, and **never** allows high Risk Capacity to force an uncomfortably high Risk Tolerance.

---

## 2. Pre-Implementation Governance Verification

1. **`PRODUCT_SPEC.md` §4, §8–10 & `ARCHITECTURE.md` §4, §11 Verified:** Confirmed that Risk Capacity and Risk Tolerance remain separate constructs and that Risk Alignment establishes the permissible risk envelope.
2. **Prior Phase Decisions Confirmed:** Confirmed F.3.3 specification and F.3.3.1 audit were both accepted with provisional methodology.
3. **No Unjustified Modifications:** Risk Capacity Engine ([`risk/capacity_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_engine.py)) and Risk Tolerance Engine ([`risk/tolerance_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_engine.py)) were untouched.
4. **Scope Control Enforced:** Downstream Phase F.3.4 (Suitability Engine) remains **STRICTLY BLOCKED**.

---

## 3. Implementation Architecture

```text
┌────────────────────────────────────────┐     ┌────────────────────────────────────────┐
│        Risk Capacity Engine            │     │        Risk Tolerance Engine           │
│   (Financial Resilience & Surplus)     │     │   (Behavioral Comfort & Drawdown)      │
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
                       │      (Phase F.3.4+ - BLOCKED)         │
                       └───────────────────────────────────────┘
```

---

## 4. Files Created

- [`risk/alignment_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_engine.py): Production Risk Alignment Engine implementation.
- [`tests/financial/test_risk_alignment_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_risk_alignment_engine.py): 40 comprehensive unit and integration test scenarios.
- [`docs/phase_f3_3_2_risk_alignment_engine_implementation_report.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f3_3_2_risk_alignment_engine_implementation_report.md): Implementation report.

---

## 5. Files Modified

- [`risk/alignment_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_models.py): Fixed Enum classmethod syntax.
- [`docs/documentation_traceability_matrix.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/documentation_traceability_matrix.md): Added Phase F.3.3.2 entry.

---

## 6. Input Contract

Consumes `RiskCapacityAssessmentResult` ([`risk/capacity_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_models.py#L55)) and `RiskToleranceAssessmentResult` ([`risk/tolerance_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_models.py#L34)).

---

## 7. Output Contract

Produces immutable `RiskAlignmentAssessmentResult` ([`risk/alignment_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_models.py#L61)):
- `assessment_id`, `investor_id`, `profile_version_used`, `observation_date`, `assessment_timestamp_utc`, `startup_mode`
- `alignment_status`, `limiting_constraint`, `aligned_risk_level`, `risk_capacity_level`, `risk_tolerance_level`
- `capacity_assessment_id`, `tolerance_assessment_id`, `capacity_confidence_score`, `tolerance_confidence_score`, `alignment_confidence_score`
- `explanation_tokens`, `missing_information_tokens`, `provenance`, `output_tag`, `is_stale_input`, `methodology_version`, `rule_version`

---

## 8. Lower-of-Two Logic

Mapped to integer values ($1 \dots 5$):
- `VERY_LOW` = 1, `LOW` = 2, `MODERATE` = 3, `HIGH` = 4, `VERY_HIGH` = 5

$$\text{min\_val} = \min(\text{cap\_val}, \text{tol\_val})$$
$$\text{aligned\_risk\_level} = \text{AlignedRiskLevel}(\text{min\_val})$$

Comparisons utilize integer `.value` attributes, eliminating string comparison bugs (`"HIGH" < "LOW"`).

---

## 9. Alignment-State Implementation

- `FULLY_ALIGNED`: $C = T$, both inputs `COMPLETE`.
- `CAPACITY_CONSTRAINED`: $C < T$, both inputs valid. `limiting_constraint = RISK_CAPACITY`.
- `TOLERANCE_CONSTRAINED`: $T < C$, both inputs valid. `limiting_constraint = RISK_TOLERANCE`.
- `PARTIAL_ALIGNMENT`: $C, T$ valid, $\ge 1$ input `PARTIAL`.
- `INSUFFICIENT_INFORMATION`: $C$ or $T$ missing valid tier (`None`). `aligned_risk_level = None`.
- `INVALID_ASSESSMENT`: Input null or configuration error.

---

## 10. Partial-Assessment Implementation

If inputs are partial but contain valid tiers:
1. `aligned_risk_level = min(C, T)`.
2. `alignment_status = AlignmentStatus.PARTIAL_ALIGNMENT`.
3. `alignment_confidence_score` is capped at `partial_alignment_confidence_cap` (0.70).
4. Emits `PROVISIONAL_ALIGNMENT_PARTIAL_INPUTS` token.

---

## 11. Insufficient-Information Implementation

If Capacity or Tolerance tier is missing (`None`) or status is `INSUFFICIENT_INFORMATION`:
1. `aligned_risk_level = None`.
2. `alignment_status = AlignmentStatus.INSUFFICIENT_INFORMATION`.
3. `limiting_constraint = BOTH_INSUFFICIENT` (if both missing) or `UNCLASSIFIED`.
4. Emits `INSUFFICIENT_DATA_CAPACITY_MISSING` and/or `INSUFFICIENT_DATA_TOLERANCE_MISSING`.

---

## 12. Confidence Implementation

Order of operations:
1. $\text{base\_confidence} = \min(\text{cap\_conf}, \text{tol\_conf})$.
2. If status is `PARTIAL_ALIGNMENT`: $\text{conf} = \min(\text{base\_confidence}, \text{partial\_cap})$.
3. If gap > `max_assessment_age_gap_days` (90 days): $\text{conf} = \text{conf} \times \text{stale\_penalty}$ (0.85).
4. Clamp $\text{conf} \in [0.0, 1.0]$.

Confidence scores **never** alter ordinal risk tiers.

---

## 13. Staleness Implementation

$$\text{gap\_days} = | \text{Date}_{\text{cap}} - \text{Date}_{\text{tol}} |$$
If $\text{gap\_days} > 90$ (configured):
- `is_stale_input = True`
- `explanation_tokens.append("STALE_ASSESSMENT_INPUT_GAP_EXCEEDED")`
- Applies `stale_input_confidence_penalty` (0.85 multiplier) to confidence score.

---

## 14. Configuration Governance

Driven by [`config/risk/alignment_config.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/risk/alignment_config.py):
- `PRODUCTION` mode requires non-None calibration values.
- `RESEARCH` mode tags outputs with `RESEARCH_MODE_NOT_FOR_PRODUCTION`.
- `TEST` mode uses synthetic defaults and tags outputs with `SYNTHETIC_TEST_DATA`.

---

## 15. Provenance

Merges `capacity_assessment.provenance` and `tolerance_assessment.provenance` into `ProvenanceMetadata` preserving combined source IDs, URLs, and UTC timestamps.

---

## 16. Versioning

Preserves `methodology_version = "1.0.0"` and `rule_version = "1.0.0"`.

---

## 17. Explainability

Emits truthful explanation tokens for every outcome:
- `FULLY_ALIGNED_CAPACITY_AND_TOLERANCE`
- `CONSTRAINED_BY_RISK_CAPACITY`
- `CONSTRAINED_BY_RISK_TOLERANCE`
- `PROVISIONAL_ALIGNMENT_PARTIAL_INPUTS`
- `INSUFFICIENT_DATA_CAPACITY_MISSING`
- `INSUFFICIENT_DATA_TOLERANCE_MISSING`
- `STALE_ASSESSMENT_INPUT_GAP_EXCEEDED`

---

## 18. Data-Quality Rules

- Missing data $\rightarrow$ `INSUFFICIENT_INFORMATION` (`aligned_risk_level = None`).
- No zero substitution or conservative guessing.
- Configuration errors in `PRODUCTION` mode halt execution safely with `INVALID_ASSESSMENT`.

---

## 19. Test Coverage

40 test scenarios implemented in [`tests/financial/test_risk_alignment_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_risk_alignment_engine.py).

---

## 20. Targeted Test Results

- **Command:** `python -m pytest tests/financial/test_risk_alignment_engine.py -v`
- **Result:** **40 / 40 passed cleanly in 0.28 seconds**.

---

## 21. Full Regression Results

- **Command:** `python -m pytest tests/ -v --tb=short`
- **Baseline:** 246 tests passed.
- **Final Result:** **286 / 286 passed cleanly in 1.22 seconds (0 failures, 0 regressions)**.

---

## 22. Documentation Changes

- Created [`docs/phase_f3_3_2_risk_alignment_engine_implementation_report.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f3_3_2_risk_alignment_engine_implementation_report.md).
- Updated [`docs/documentation_traceability_matrix.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/documentation_traceability_matrix.md).

---

## 23. Provisional Parameter Register

| Parameter | Value | Governance Status |
|---|---:|---|
| `partial_alignment_confidence_cap` | 0.70 | `PROVISIONAL` |
| `max_assessment_age_gap_days` | 90 | `PROVISIONAL` |
| `stale_input_confidence_penalty` | 0.85 | `PROVISIONAL` |

---

## 24. Genuine Issues Discovered

1. `AlignedRiskLevel` enum syntax missing `def` keyword in `@classmethod`. Fixed in [`risk/alignment_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_models.py).
2. `ProvenanceMetadata` test fixtures updated to match canonical constructor fields.

---

## 25. Corrections Applied

- Fixed classmethod syntax in [`risk/alignment_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_models.py).
- Fixed test fixture provenance initialization in [`tests/financial/test_risk_alignment_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_risk_alignment_engine.py).

---

## 26. Known Limitations

- The three calibration parameters remain provisional and require future empirical validation before production deployment.

---

## 27. Scope Verification

- Zero suitability matching logic.
- Zero goal engine, portfolio allocation, rebalancing, or fund quality modifications.
- Zero tax optimization or transaction execution code.

---

## 28. Downstream Implementation Gate

```text
================================================================================
IMPLICIT EXECUTION GATE ENFORCED
================================================================================
Phase F.3.4 (Suitability Engine Implementation) is STRICTLY BLOCKED in this phase.
Requires explicit user authorization and pre-implementation governance verification.
================================================================================
```

---

## 29. Final Decision — Exactly One

```text
PHASE F.3.3.2 ACCEPTED WITH PROVISIONAL METHODOLOGY
```

*Note: Phase F.3.3.2 Risk Alignment Engine implementation is accepted with provisional methodology. Phase F.3.4 will NOT begin automatically.*
