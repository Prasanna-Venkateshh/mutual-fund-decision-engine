# Phase F.3.1 — Risk Capacity Engine Implementation Report

**Phase:** Phase F.3.1 — Risk Capacity Engine Implementation  
**Date:** 2026-09-10 UTC  
**Final Status:** `PHASE F.3.1 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Production architecture slice of Risk Capacity Engine, data contracts, configuration framework, 7-layer engine separation, 3 startup modes, missing-data handling, confidence separation, bottleneck aggregation, test suite, and QA review.

---

## 1. Executive Summary

Phase F.3.1 implements the first production architecture slice of the Risk Capacity Engine defined in Phase F.2C and governed by Phase F.2C.1. 

The engine evaluates investor financial capacity through three constraint dimensions (Debt Burden, Reserve Adequacy, Sustainable Surplus Ratio), aggregates them using a bottleneck integration rule, calculates confidence as a separate output indicator, generates structured explanation tokens, and produces fully versioned and reproducible data contracts.

### Key Governance Accomplishments

1. **Zero Financial Parameters Invented:** All 13 TBD calibration parameters remain externalized in configuration. In `PRODUCTION` mode, missing calibration parameters cause the engine to fail safely (`CONFIGURATION_ERROR` status) without calculating an ungrounded capacity tier.
2. **Strict Construct Isolation:** Risk Capacity is evaluated purely from financial resilience inputs. It does NOT consume Risk Tolerance, behavioral questionnaire answers, investment horizon, fund quality scores, or asset returns.
3. **Three Startup Modes Implemented:** `PRODUCTION` (fails safely if calibration is missing), `RESEARCH` (permits provisional parameters, tags outputs `RESEARCH_MODE_NOT_FOR_PRODUCTION`), and `TEST` (uses synthetic parameters, tags outputs `SYNTHETIC_TEST_DATA`).
4. **Provisional Methodology Labels Preserved:**
   - `RC-ARCH-03` (min() bottleneck aggregation) is explicitly marked `PROVISIONAL` and isolated in its own replaceable function (`aggregate_bottleneck_capacity`).
   - `RC-D1-02` (gross income denominator for debt burden) is explicitly marked `PROVISIONAL`.
   - `RC-D3 surplus ratio` is documented in code comments as algebraically dependent on `RC-D1 debt burden`.
5. **Confidence Separation:** Confidence is calculated strictly AFTER capacity tier determination and does not alter capacity tiers or constraint levels.
6. **215/215 Tests Passed:** The complete test suite passes (185 baseline + 30 new targeted Risk Capacity unit, integration, and independent math fixture tests).

---

## 2. Architecture & Responsibilities

The implementation strictly separates engine responsibilities across 7 layers in [`capacity_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_engine.py):

```text
Inputs: FinancialCapacitySnapshot + Household Context
                 ↓
┌─────────────────────────────────────────────────┐
│ A. Input Validation                             │
├─────────────────────────────────────────────────┤
│ B. Financial Calculations                       │
│    - Debt Burden Ratio (Gross income PROVISIONAL)│
│    - Reserve Adequacy Ratio (Additive Modifiers)│
│    - Sustainable Surplus Ratio (D3/D1 Dependency)│
├─────────────────────────────────────────────────┤
│ C. Constraint Evaluation (D1, D2, D3)           │
├─────────────────────────────────────────────────┤
│ D. Bottleneck Aggregation (min() PROVISIONAL)   │
├─────────────────────────────────────────────────┤
│ E. Confidence Calculation (Output-only)         │
├─────────────────────────────────────────────────┤
│ F. Explanation Generation (Structured Tokens)   │
├─────────────────────────────────────────────────┤
│ G. Provenance & Versioning Output              │
└─────────────────────────────────────────────────┘
                 ↓
Output: RiskCapacityAssessmentResult
```

---

## 3. Data Contracts & Configuration

### Files Created/Modified

| Module | File Path | Responsibilities |
|---|---|---|
| Configuration | [`config/risk/capacity_config.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/risk/capacity_config.py) | Externalized config, 13 TBD parameters, startup modes (`PRODUCTION`, `RESEARCH`, `TEST`), `validate()`, mode factories. |
| Models | [`risk/capacity_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_models.py) | `AssessmentStatus`, `ConstraintLevel`, `ConstraintResult`, `RiskCapacityAssessmentResult` data contracts. |
| Engine | [`risk/capacity_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_engine.py) | 7-layer Risk Capacity assessment pipeline execution. |
| Test Suite | [`tests/financial/test_risk_capacity_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_risk_capacity_engine.py) | 28 targeted unit & integration tests. |
| Math Fixtures | [`tests/financial/test_risk_capacity_independent_fixtures.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/financial/test_risk_capacity_independent_fixtures.py) | Independent expected-value test fixtures. |

---

## 4. Financial Formulas Implemented

### 4.1 Debt Burden Ratio (Dimension 1)
$$\text{Debt Burden Ratio} = \frac{\text{Monthly Debt Servicing}}{\text{Monthly Gross Income}}$$
- *Governance Status:* `PROVISIONAL` denominator (RC-D1-02).
- *Safe Handling:* If gross income $\le 0$ or debt is missing, returns `None` (`MISSING_DATA` constraint status). Never divides by zero or substitutes zero for missing values.

### 4.2 Reserve Adequacy Ratio (Dimension 2)
$$\text{Reserve Adequacy Ratio} = \frac{\text{Liquid Emergency Reserves}}{\text{Monthly Fixed Expenses} \times \text{Required Coverage Months}}$$
$$\text{Required Coverage Months} = \text{Base Months} + \text{Stability Additive Months} + (\text{Dependents Count} \times \text{Dependent Adjustment Months})$$
- *Governance Status:* Stability + Dependent adjustments are **additive** on required coverage months per Phase F.2C.1 Audit §5.

### 4.3 Sustainable Surplus Ratio (Dimension 3)
$$\text{Surplus Ratio} = \frac{\text{Monthly Gross Income} - \text{Taxes} - \text{Fixed Expenses} - \text{Debt Servicing}}{\text{Monthly Gross Income}}$$
- *Governance Status:* Documented as algebraically dependent on Debt Burden ($D_1$). If taxes are missing, does NOT invent a tax rate.

---

## 5. Startup Mode Behavior

| Startup Mode | Behavior when Calibration Missing | Output Tag |
|---|---|---|
| `PRODUCTION` | Fails safely with `AssessmentStatus.CONFIGURATION_ERROR`; returns no capacity tier (`None`). | `None` |
| `RESEARCH` | Permits provisional parameters. | `RESEARCH_MODE_NOT_FOR_PRODUCTION` |
| `TEST` | Accepts explicit synthetic test parameters. | `SYNTHETIC_TEST_DATA` |

---

## 6. Missing-Data Degradation & Status Rules

- `COMPLETE`: All required inputs and valid configuration present.
- `PARTIAL`: Non-critical fields missing; returns bounded capacity tier with lower confidence score and `PARTIAL_FINANCIAL_INFORMATION` token.
- `INSUFFICIENT_INFORMATION`: Critical fields missing (e.g. both income and reserves missing); capacity tier is `None`.
- `CONFIGURATION_ERROR`: Production calibration parameters absent; capacity tier is `None`.

---

## 7. QA Review Results

| Category | Status | Evaluation Summary |
|---|---|---|
| A. Functional correctness | **PASS** | Complete assessment flow functions predictably across all statuses. |
| B. Financial formula correctness | **PASS** | Formulas strictly match Phase F.2C/F.2C.1 specifications. |
| C. Configuration correctness | **PASS** | All 13 TBD parameters externalized; fail-safe startup enforced. |
| D. Missing-data degradation | **PASS** | Missing values never become zero; PARTIAL vs INSUFFICIENT_INFORMATION correctly distinguished. |
| E. Confidence separation | **PASS** | Confidence calculated strictly AFTER capacity tier; does not alter tier. |
| F. Provenance | **PASS** | Full audit metadata and timestamp preserved in output contract. |
| G. Explainability | **PASS** | Tokens emitted only when underlying conditions occur. |
| H. Startup mode isolation | **PASS** | Production mode refuses uncalibrated execution; Research/Test tag outputs. |
| I. Determinism | **PASS** | 100% reproducible results across multiple executions. |
| J. Regression | **PASS** | 215 / 215 tests passing cleanly. |

---

## 8. Financial Governance Check & Hidden-Threshold Scan

A scan of all newly created production Python code for numerical threshold constants (`30`, `50`, `60`, `3`, `6`, `12`, `0.70`, `0.80`, `40`) confirmed:
- No prohibited hardcoded financial rules exist in `risk/capacity_engine.py` or `config/risk/capacity_config.py`.
- Production parameters default to `None` for all 13 TBD entries.
- Synthetic numbers in `create_test_config()` are strictly isolated to test execution mode.

---

## 9. Test Suite Execution Summary

- **Baseline Test Suite:** 185 / 185 passed.
- **New Targeted Risk Capacity Tests:** 30 / 30 passed.
- **Final Regression Suite:** 215 / 215 passed in 1.97 seconds.

---

## 10. Parameters Remaining Provisional / TBD

### 5 Provisional Parameters:
- `RC-ARCH-03`: min() bottleneck aggregation mechanism.
- `RC-D1-02`: Gross income denominator choice.
- `RC-D2-02`: Salaried reserve requirement (range 3-6 months approved concept; exact value provisional).
- `RC-D2-03`: Self-employed reserve requirement (range 6-12 months approved concept; exact value provisional).
- `RC-CTX-01`: Household aggregate input convention (V1 simplification).

### 13 TBD Parameters (Configurable Stubs):
- `RC-D1-04`, `RC-D1-05`, `RC-D1-06`, `RC-D1-07`
- `RC-D2-04`, `RC-D2-05`, `RC-D2-06`
- `RC-D3-03`, `RC-D3-04`, `RC-D3-05`
- `RC-IS-02`, `RC-INT-02`, `RC-INT-03`

---

## 11. Final Status — Exactly One

```text
PHASE F.3.1 ACCEPTED WITH PROVISIONAL METHODOLOGY
```

*Note: Phase F.3.2 (Risk Tolerance Engine Implementation) may NOT begin automatically.*
