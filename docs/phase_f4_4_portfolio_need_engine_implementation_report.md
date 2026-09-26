# Phase F.4.4 — Portfolio Need Engine Implementation Report

**Phase Status:** ACCEPTED WITH PROVISIONAL METHODOLOGY  
**Component:** Portfolio Need / Goal Need Decision Engine (`portfolio/need_engine.py`)  
**Data Contracts:** `portfolio/need_models.py` (re-exported via `risk/need_models.py`)  
**Test Suite:** `tests/financial/test_portfolio_need_engine.py`  
**Execution Timestamp:** 2026-09-11 UTC  

---

## 1. Executive Summary

Phase F.4.4 implements the production Portfolio Need / Goal Need decision engine in `portfolio/need_engine.py` strictly according to the governed F.4 specifications and governance corrections.

The Portfolio Need engine operates strictly downstream of Suitability and upstream of Economic Benefit/Action:
`DATA -> METRIC ENGINE -> FUND QUALITY -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION`

The implementation confirms and enforces all ten governance principles:
1. Portfolio Need does not calculate Fund Quality.
2. Portfolio Need does not calculate Suitability.
3. Portfolio Need does not calculate Risk Alignment.
4. Portfolio Need does not calculate Risk Capacity.
5. Portfolio Need does not calculate Risk Tolerance.
6. Portfolio Need does not create Economic Benefit.
7. Portfolio Need does not create Buy/Sell/Accumulate/Hold actions.
8. Portfolio Need determines whether an underlying goal/portfolio requirement exists.
9. Candidate Fulfillment determines whether a specific candidate can satisfy that requirement.
10. Suitability and Candidate Fulfillment remain separate concepts.

---

## 2. Decision Pipeline & Precedence

The decision pipeline is executed in exact deterministic order:

1. **Step 1 — Input Validity Gate (`INVALID_ASSESSMENT`)**: Validates input types, non-empty investor IDs, ID consistency across goal and portfolio snapshots, and non-empty candidate scheme IDs. Invalid inputs immediately return `INVALID_ASSESSMENT` with `confidence_score = 0.0`.
2. **Step 2 — Information Sufficiency Gate (`INSUFFICIENT_INFORMATION`)**: Verifies presence of mandatory goal context (or general wealth context) and allocation context (or portfolio snapshot). Missing mandatory input returns `INSUFFICIENT_INFORMATION` without substituting zero, false, or default values.
3. **Step 3 — Primary Need State Determination**:
   - `NEGATIVE_GAP` -> `EXCESS_EXPOSURE` (The only condition creating primary excess exposure).
   - `POSITIVE_GAP` -> `NEED_IDENTIFIED`.
   - `BALANCED_EXPOSURE` -> `NO_MATERIAL_NEED`.
   - Fallback for underfunded goals without explicit exposure gaps -> `NEED_IDENTIFIED`.
4. **Step 4 — Candidate Fulfillment Status Determination**:
   - Evaluates upstream `SuitabilityAssessmentResult`. `NOT_SUITABLE` returns `CANDIDATE_CANNOT_FULFILL_NEED` with `CANDIDATE_UNSUITABLE` flag (preserving the underlying Need State).
   - Evaluates asset class/category capability (`is_capable_of_fulfilling_need`). Inability returns `CANDIDATE_CANNOT_FULFILL_NEED` with `CANDIDATE_NOT_CAPABLE_OF_FULFILLING_NEED` flag.
   - If suitable and capable when `NEED_IDENTIFIED` exists -> `CANDIDATE_CAN_FULFILL_NEED`.
   - If capability is missing -> `CANDIDATE_FULFILLMENT_UNKNOWN`.
5. **Step 5 — Affordability & Contextual Modifiers**:
   - `AFFORDABILITY_CONSTRAINED` adds a contextual constraint flag without erasing underlying Need.
   - Look-through category concentration (`CATEGORY_OVEREXPOSED`) and security overlap (`SECURITY_OVERLAP_CONCERN`) emit contextual flags without overriding primary Need state (e.g. concentration alone cannot force `EXCESS_EXPOSURE`).
6. **Step 6 — Confidence Calculation & Provenance Assembly**:
   - Confidence reflects evidence strength and never acts as a hidden decision gate or state converter.
   - Preserves timestamps, input references, upstream assessment IDs, methodology versions (`F.4.4-PROVISIONAL`), and rule version (`1.0.0`).
   - Appends explicit disclaimer: "This assessment identifies portfolio/goal exposure need only and does not constitute a transaction recommendation (Buy/Sell/Switch)."

---

## 3. Test Suite & Verification Results

### Unit Tests Created (`tests/financial/test_portfolio_need_engine.py`)

- **Primary States (Tests 1–5):** Positive gap, Negative gap, Balanced exposure, Missing inputs, Invalid inputs.
- **Candidate Fulfillment (Tests 6–10):** Suitable & capable, Unsuitable, Suitable but wrong asset class, Unknown capability, No default to capable.
- **Affordability Semantics (Tests 11–12):** Need + constrained affordability, Need + unknown affordability context.
- **Concentration & Overlap (Tests 13–15):** Balanced + concentration (never Excess Exposure), Positive gap + concentration, Negative gap + concentration.
- **Separation Invariants (Tests 16–25):** High Fund Quality cannot create Need, Low Fund Quality cannot create Need, Suitability cannot erase Need, Candidate inability cannot erase Need, Candidate fulfillment cannot create Buy, Portfolio Need cannot create Action enum, Confidence score does not silently flip state, Funding status vs Allocation status separation, General wealth alone cannot manufacture Need, Multi-goal non-double-counting.
- **Provenance & Explainability (Tests 26–30):** Complete provenance metadata, Specific explanation matching inputs, Candidate fulfillment rationale distinct from Suitability, Platform-calculated labels, Methodology & Rule versions.

### Execution Summary

- **Targeted Portfolio Need Engine Tests:** 33 passed / 33 total (`tests/financial/test_portfolio_need_engine.py`)
- **Full Regression Test Suite:** 329 passed / 329 total (True pre-F.4.4 baseline of 329 tests fully preserved and reconciled in Phase F.4.4.2 Audit)
- **Failures:** 0
- **Execution Time:** ~0.33s

---

## 4. Key Files Changed / Created

1. [`portfolio/need_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/portfolio/need_models.py) — Canonical Portfolio Need data contracts and enums.
2. [`portfolio/need_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/portfolio/need_engine.py) — Production Portfolio Need decision engine implementation.
3. [`risk/need_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/need_models.py) — Thin re-export module for backwards compatibility across risk and portfolio packages.
4. [`risk/need_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/need_engine.py) — Thin re-export module for `PortfolioNeedEngine`.
5. [`tests/financial/test_portfolio_need_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_portfolio_need_engine.py) — Complete 33-scenario unit test suite.
6. [`docs/phase_f4_4_1_regression_and_scope_audit.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f4_4_1_regression_and_scope_audit.md) — Phase F.4.4.1 audit report.
7. [`docs/documentation_traceability_matrix.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/documentation_traceability_matrix.md) — Updated traceability matrix with Phase F.4.4/F.4.4.1 status.
8. [`docs/phase_f4_4_portfolio_need_engine_implementation_report.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f4_4_portfolio_need_engine_implementation_report.md) — Phase F.4.4 implementation report.

---

## 5. Governance Final Check

- [x] Positive gap → Need Identified.
- [x] Negative gap → Excess Exposure.
- [x] Balanced exposure → No Material Need.
- [x] Concentration alone cannot create Excess Exposure.
- [x] Suitability and Candidate Fulfillment remain separate.
- [x] Suitable + wrong asset class = suitable but cannot fulfill.
- [x] Unknown capability never defaults to capable.
- [x] Affordability never erases Need.
- [x] Funding and allocation remain separate.
- [x] Fund Quality cannot create Need.
- [x] Low confidence does not silently change Need State.
- [x] No hidden numerical thresholds introduced.
- [x] Zero Action generated.
- [x] Full provenance preserved.
- [x] Explanations are deterministic and input-specific.
- [x] Existing architecture remains intact.
- [x] 100% test regression green (329/329).

---

# FINAL STATUS — USE EXACTLY ONE

PHASE F.4.4 ACCEPTED WITH PROVISIONAL METHODOLOGY
