# Phase F.2C — Risk Capacity Parameter Register

**Document Status:** GOVERNED PARAMETER REGISTER  
**Version:** `1.0.0`  
**Phase:** Phase F.2C — Risk Capacity Methodology Design  
**Date:** 2026-09-09 UTC

---

## 1. Governance Overview

This register catalogues every parameter and configurable threshold in the Risk Capacity Engine design. Each entry records its current status, evidence basis, required calibration method, and configuration location.

### Status Legend
- `APPROVED` — Evidence genuinely supports this parameter or principle.
- `PROVISIONAL` — Reasonable hypothesis; requires empirical calibration before production.
- `TBD` — Cannot be responsibly determined without empirical data; must not be invented.
- `NOT APPLICABLE` — Not used in this engine.

### Direct Numerical Support Column
- `YES` — An external source establishes this exact number.
- `CONCEPTUAL` — An external source supports the concept; the number is a product-design inference.
- `NO` — No external source supports this number.

---

## 2. Parameter Register

| Param ID | Parameter Name | Config Key | Current Placeholder | Approval Status | Direct Numerical Support? | Evidence Source | Calibration Method | Validation Status | Config Location | Hard-Coded? |
|---|---|---|---|---|---|---|---|---|---|---|
| **RC-ARCH-01** | Constraint-Based Bottleneck Architecture | (architectural choice) | N/A | `APPROVED` | CONCEPTUAL | FPSB fiduciary standards; Phase F.2B audit | N/A — architectural principle | Validated conceptually | `docs/phase_f2c_risk_capacity_methodology.md` | No |
| **RC-ARCH-02** | Lower-of-the-Two Integration Rule | (architectural choice) | N/A | `APPROVED` | CONCEPTUAL | FPSB standards; SEBI RIA requirements; Phase F specification | N/A — architectural principle | Validated conceptually | `docs/phase_f_suitability_risk_alignment_specification.md` | No |
| **RC-ARCH-03** | Hard Capacity Ceilings for Extreme Conditions | (architectural principle) | N/A | `PROVISIONAL` | CONCEPTUAL | General principle `APPROVED CONCEPT` (FPSB, RBI HFC 2017); specific min() mechanism is a product architecture choice. **Phase F.2C.1 Audit: Status corrected from APPROVED to PROVISIONAL.** | Architectural validation during F.3 calibration | Concept approved; implementation mechanism provisional | `docs/phase_f2c_risk_capacity_methodology.md` | No |
| **RC-ARCH-04** | Missing Input → Reduced Confidence (not zero) | (architectural principle) | N/A | `APPROVED` | YES | PRODUCT_SPEC.md §25; ARCHITECTURE.md §15 | N/A — product principle | Validated | `PRODUCT_SPEC.md §25` | No |
| **RC-ARCH-05** | Five-Level Ordinal Capacity Scale | `capacity_tier` enum | VERY_LOW / LOW / MODERATE / HIGH / VERY_HIGH | `APPROVED` | CONCEPTUAL | Phase F specification; SEBI suitability guidance | N/A — scale level count | Approved by specification | `models/investor_profile.py` | Yes (enum) |
| **RC-D1-01** | Debt Burden Ratio Formulation | `debt_burden_ratio` | `monthly_debt_servicing / monthly_gross_income` | `APPROVED` | CONCEPTUAL | FPSB India; RBI HFC Report 2017 | Formula structure approved; thresholds TBD | Concept approved | `suitability/capacity.py` (Phase F.3) | No |
| **RC-D1-02** | Debt Burden: Use Gross (not Net) Income | (formula decision) | Gross income denominator | `PROVISIONAL` | CONCEPTUAL | FPSB India DTI guidance uses net monthly income as denominator; gross income is a pragmatic product design choice for verifiability. **Phase F.2C.1 Audit: Status corrected from APPROVED to PROVISIONAL.** Requires empirical validation. | Validate gross vs. net denominator choice across Indian household profiles; compare with surplus formula consistency | Provisional product design choice | `docs/phase_f2c_risk_capacity_methodology.md` | No |
| **RC-D1-03** | Debt Burden: Recurring Committed Debt Only | (formula scope) | EMIs, loan repayments only | `APPROVED` | CONCEPTUAL | Financial planning standard — only committed obligations count | Clarified in data collection specs | Approved by methodology | `docs/phase_f2c_risk_capacity_methodology.md` | No |
| **RC-D1-04** | Debt Burden: Low Constraint Threshold | `DEBT_LOW_CONSTRAINT_THRESHOLD` | TBD | `TBD` | NO | No source establishes exact threshold | Calibrate against RBI retail credit data and FPSB DTI recommendations | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D1-05** | Debt Burden: Moderate Constraint Threshold | `DEBT_MODERATE_CONSTRAINT_THRESHOLD` | TBD | `TBD` | NO | Phase F.2B: RBI/FPSB support concept of 40-50% warning; exact threshold unverified | Calibrate against household debt shock survival data | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D1-06** | Debt Burden: High Constraint Threshold | `DEBT_HIGH_CONSTRAINT_THRESHOLD` | TBD | `TBD` | NO | Phase F.2B: RBI notes DSR >50% causes severe vulnerability — concept supported; exact threshold TBD | Calibrate against household default/stress data | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D1-07** | Debt Burden: Capacity Ceiling Mapping | `DEBT_CONSTRAINT_CAPACITY_CEILING` | TBD (dict) | `TBD` | NO | Constraint levels to capacity ceiling mapping | Calibrate after threshold calibration | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D2-01** | Reserve Adequacy Ratio Formulation | `reserve_adequacy_ratio` | `liquid_reserves / (required_monthly_expenses × stability_multiplier)` | `APPROVED` | CONCEPTUAL | FPSB India; RBI household finance analysis | Formula structure approved; thresholds TBD | Concept approved | `suitability/capacity.py` (Phase F.3) | No |
| **RC-D2-02** | Reserve: Salaried Minimum Required Coverage | `RESERVE_SALARIED_MIN_MONTHS` | TBD (FPSB guidance: 3–6 months) | `PROVISIONAL` | YES (for range concept) | FPSB India: "3–6 months for salaried" directly supported | Calibrate against SIP discontinuation / income interruption data | Range approved; exact value provisional | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D2-03** | Reserve: Self-Employed Minimum Required Coverage | `RESERVE_SELF_EMPLOYED_MIN_MONTHS` | TBD (FPSB guidance: 6–12 months) | `PROVISIONAL` | YES (for range concept) | FPSB India: "6–12 months for self-employed" directly supported | Calibrate against self-employed income interruption frequency data | Range approved; exact value provisional | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D2-04** | Reserve: Variable Income Minimum Required Coverage | `RESERVE_VARIABLE_INCOME_MIN_MONTHS` | TBD | `TBD` | NO | No source establishes exact minimum for variable-income category | Calibrate; likely between salaried and self-employed | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D2-05** | Reserve: Dependent Adjustment Formula | `RESERVE_DEPENDENT_ADJUSTMENT` | TBD | `TBD` | NO | No source establishes dependent-count → reserve-multiplier formula | Calibrate against household emergency expense data | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D2-06** | Reserve: Adequacy Ratio → Capacity Ceiling Mapping | `RESERVE_ADEQUACY_CAPACITY_CEILING` | TBD (dict) | `TBD` | NO | Adequacy levels to capacity ceiling mapping | Calibrate after threshold calibration | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D3-01** | Sustainable Surplus Ratio Formulation | `surplus_ratio` | `(gross_income − taxes − fixed_expenses − debt) / gross_income` | `APPROVED` | CONCEPTUAL | FPSB cash-flow standards; SEBI RIA requirements (AF-01) | Formula structure approved; thresholds TBD | Concept approved | `suitability/capacity.py` (Phase F.3) | No |
| **RC-D3-02** | Surplus Ratio: Taxes Treatment | (formula flag) | Accept net income OR gross with tax flag | `APPROVED` | CONCEPTUAL | Taxes are non-discretionary obligations | Missing tax → reduce confidence, don't block | Approved by methodology | `docs/phase_f2c_risk_capacity_methodology.md` | No |
| **RC-D3-03** | Surplus: Adequate Level Threshold | `SURPLUS_ADEQUATE_THRESHOLD` | TBD | `TBD` | NO | No source establishes what surplus ratio represents capacity adequacy | Calibrate against investor financial stress event data | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D3-04** | Surplus: Limited Level Threshold | `SURPLUS_LIMITED_THRESHOLD` | TBD | `TBD` | NO | No source establishes what surplus ratio represents capacity limitation | Calibrate | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-D3-05** | Surplus: Thin/Zero Threshold | `SURPLUS_THIN_THRESHOLD` | TBD | `TBD` | NO | Near-zero surplus → VERY_LOW capacity ceiling concept is supported; exact threshold TBD | Calibrate | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-IS-01** | Income Stability Categories | `income_stability_type` (enum) | STABLE_SALARIED / VARIABLE / SELF_EMPLOYED / IRREGULAR / UNKNOWN | `APPROVED` | CONCEPTUAL | FPSB income stability guidance; Phase F.2B research | Categories defined; multipliers TBD | Categories approved | `models/investor_profile.py` (future) | No |
| **RC-IS-02** | Income Stability → Reserve Multiplier Mapping | `STABILITY_RESERVE_MULTIPLIERS` | TBD (dict) | `TBD` | NO | No source establishes exact per-category multipliers | Calibrate against income interruption frequency data | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-INT-01** | Integration Rule: Min(D1, D2, D3) Constraint | (architectural rule) | `overall_capacity = min(debt_ceiling, reserve_ceiling, surplus_ceiling)` | `APPROVED` | CONCEPTUAL | Fiduciary conservatism principle; bottleneck architecture | N/A — integration principle | Architecture approved | `suitability/capacity.py` (Phase F.3) | No |
| **RC-INT-02** | Confidence Reduction per Missing Input | `CONFIDENCE_PENALTY_PER_MISSING_INPUT` | TBD | `TBD` | NO | Confidence reduction magnitude is a product design choice | Design after Layer 1 testing | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-INT-03** | Confidence Floor for Partial Assessment | `PARTIAL_ASSESSMENT_CONFIDENCE_FLOOR` | TBD | `TBD` | NO | Minimum confidence for a partial assessment to be presented | Design and test | Not calibrated | `config/risk/capacity_config.yaml` (future) | No |
| **RC-OUT-01** | Output: Assessment Status Enum | `assessment_status` | ASSESSED / PARTIAL / INSUFFICIENT_INFORMATION | `APPROVED` | CONCEPTUAL | PRODUCT_SPEC.md §15 — error/uncertainty states | N/A — status enum | Approved by specification | `suitability/capacity.py` (Phase F.3) | Yes (enum) |
| **RC-OUT-02** | Output: Methodology Version | `methodology_version` | `"1.0.0"` to be incremented on changes | `APPROVED` | YES | ARCHITECTURE.md §11 — versioned assessments | Version incremented on methodology changes | Approved by architecture | `suitability/capacity.py` (Phase F.3) | No |
| **RC-OUT-03** | Output: Rule Version | `rule_version` | `"1.0.0"` tied to config file version | `APPROVED` | YES | ARCHITECTURE.md §11 — versioned assessments | Version tracks config changes | Approved by architecture | `config/risk/capacity_config.yaml` (future) | No |
| **RC-CTX-01** | Household Input Convention (V1) | `HOUSEHOLD_INPUT_CONVENTION` | All inputs = household-level aggregates | `PROVISIONAL` | NO | V1 simplification; no external source mandates this convention | Document in F.3 spec and data collection guidelines; revisit in V2 | Phase F.2C.1 Audit — documented as known V1 limitation | `docs/phase_f2c_risk_capacity_methodology.md §22` | No |
| **RC-CTX-02** | F.3 Startup Mode Policy | `STARTUP_MODE` | PRODUCTION \| RESEARCH \| TEST | `APPROVED` | NO | Product safety policy; three modes prevent production misuse while enabling calibration/testing | Document in F.3 spec; enforce in startup validation | Phase F.2C.1 Audit — approved three-mode policy | `docs/phase_f2c_risk_capacity_methodology.md §23` | No |

---

## 3. Summary: Parameters by Status

| Status | Count | Parameters |
|---|---|---|
| `APPROVED` | 15 | RC-ARCH-01, RC-ARCH-02, RC-ARCH-04, RC-ARCH-05, RC-D1-01, RC-D1-03, RC-D2-01, RC-D3-01, RC-D3-02, RC-IS-01, RC-INT-01, RC-OUT-01, RC-OUT-02, RC-OUT-03, RC-CTX-02 |
| `PROVISIONAL` | 5 | RC-ARCH-03 (**corrected from APPROVED** — F.2C.1 audit), RC-D1-02 (**corrected from APPROVED** — F.2C.1 audit), RC-D2-02, RC-D2-03, RC-CTX-01 |
| `TBD` | 13 | All numerical constraint thresholds; stability multipliers; dependent adjustment; confidence penalty factors |
| `NOT APPLICABLE` | 0 | — |

> [!IMPORTANT]
> **13 parameters are currently TBD.** Phase F.3 must be implemented with all TBD parameters as externalized configurable stubs that reject engine startup if not provided. F.3 must not invent or hard-code any TBD value.

---

## 4. Parameters Explicitly Excluded From This Engine

The following were evaluated and explicitly excluded from the Risk Capacity Engine:

| Excluded Factor | Reason | Correct Location |
|---|---|---|
| Raw gross income (as standalone factor) | Double-counts with derived ratios; income already serves as normalizing denominator | Used as denominator only |
| Total net wealth / total assets | Illiquid assets do not extend capacity; liquid assets captured in reserve adequacy | Portfolio Context engine |
| Investment horizon / goal date | Separate construct; horizon ceiling applied downstream | Phase F.6 Horizon Engine |
| Current portfolio composition | Belongs to Portfolio Need assessment | Portfolio Context engine |
| Behavioral risk tolerance | Separate behavioral construct | Risk Tolerance Engine (Phase F.4) |
| Fund Quality assessment | Fund-quality is investor-independent | Scoring Engine (Phase E) |
| Per-dependent monetary deduction | Introduces arbitrary financial assumptions | Dependents modify reserve requirement only |
| Savings tiers as discrete buckets | Discontinuous; replaced by continuous surplus ratio | RC-D3 surplus ratio |
