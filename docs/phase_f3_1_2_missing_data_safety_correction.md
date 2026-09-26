# Phase F.3.1.2 — Risk Capacity Missing-Data Safety Correction

**Phase:** Phase F.3.1.2 — Missing-Data Safety Correction  
**Date:** 2026-09-10 UTC  
**Final Status:** `PHASE F.3.1.2 ACCEPTED`  
**Governance Classification:** `APPROVED`  
**Scope:** Correction of tax zero-substitution defect and income-stability default defect in Risk Capacity Engine implementation.

---

## 1. Executive Summary

This phase corrects two genuine financial-logic defects identified during the Phase F.3.1.1 audit:

1. **Tax Zero-Substitution Defect:** Missing `monthly_taxes` was previously converted to `0.0` inside `calculate_surplus_ratio()`, evaluating non-tax surplus ($60\%$) instead of recognizing taxes as unsupplied.
2. **Income-Stability Default Defect:** Missing `employment_type` previously defaulted to `STABLE_SALARIED` inside `calculate_reserve_adequacy_ratio()`, applying the favorable salaried reserve requirement ($3$ months).

Both behaviors violated the foundational governance rule:
```text
MISSING ≠ ZERO
MISSING ≠ DEFAULT
```

### Corrections Implemented

- **Tax Correction:** When `monthly_taxes` is `None` (unsupplied), `calculate_surplus_ratio()` returns `None`. $D_3$ constraint status becomes `MISSING_DATA`. No zero-tax substitution, tax rate estimation, or optimistic surplus ratio is generated.
- **Stability Correction:** When `employment_type` is `None` (unsupplied), `calculate_reserve_adequacy_ratio()` returns `(None, None)`. $D_2$ constraint status becomes `MISSING_DATA`. No `STABLE_SALARIED` assumption or reserve multiplier is manufactured.
- **Confidence Separation Preserved:** Corrections are made directly inside the financial calculation functions. Confidence scoring remains supplementary and does not mask invalid calculations.
- **219/219 Tests Passed:** All 216 baseline tests + 3 new targeted safety tests pass cleanly.

---

## 2. Defect Analysis & Root Causes

### 2.1 Tax Zero-Substitution Defect
- **Root Cause:** In `risk/capacity_engine.py`, `calculate_surplus_ratio()` previously contained:
  `taxes = monthly_taxes if monthly_taxes is not None else 0.0`
- **Financial Risk:** Evaluated a profile with ₹100k income, ₹30k expenses, ₹10k debt, and unsupplied taxes as having a ₹60k ($60\%$) surplus. If the investor actually paid ₹20k taxes, true surplus was ₹40k ($40\%$). The unsupplied tax produced a numerically optimistic $D_3$ tier.
- **Correction:** Removed zero substitution. If `monthly_taxes is None`, `calculate_surplus_ratio()` returns `None`.

### 2.2 Income-Stability Default Defect
- **Root Cause:** In `risk/capacity_engine.py`, `calculate_reserve_adequacy_ratio()` previously contained:
  `emp = (employment_type or "STABLE_SALARIED").upper()`
- **Financial Risk:** Evaluated an unsupplied employment profile using the lowest reserve requirement ($3$ months salaried), manufacturing a favorable reserve adequacy ratio for self-employed or variable-income investors whose true requirement is 6–12 months.
- **Correction:** Removed default substitution. If `employment_type is None`, `calculate_reserve_adequacy_ratio()` returns `(None, None)`.

---

## 3. Exact Corrected Missing-Data Behavior

### 3.1 Missing Taxes (`monthly_taxes = None`)
- $D_3$ (Surplus Ratio) $\rightarrow$ `calculated_ratio = None`, `status = "MISSING_DATA"`.
- `missing_inputs` includes `"monthly_taxes"`.
- Emits token `"MISSING_INPUT_MONTHLY_TAXES"`.
- Overall status = `PARTIAL` (if $D_1$ or $D_2$ is assessed).
- Does **NOT** improve or alter capacity tier.

### 3.2 Missing Income Stability (`employment_type = None`)
- $D_2$ (Reserve Adequacy) $\rightarrow$ `calculated_ratio = None`, `status = "MISSING_DATA"`.
- `missing_inputs` includes `"employment_type"`.
- Emits token `"MISSING_INPUT_EMPLOYMENT_TYPE"`.
- Overall status = `PARTIAL` (if $D_1$ is assessed).
- If both `employment_type` AND debt servicing are missing, $D_1$ and $D_2$ are both `MISSING_DATA` $\rightarrow$ overall status = `INSUFFICIENT_INFORMATION`, capacity tier = `None` (ABSENT).

---

## 4. Input Contract Documentation

- `FinancialCapacitySnapshot` (in `models/investor_profile.py`) remains an immutable data contract for observed financial inputs.
- `monthly_taxes` and `employment_type` are accepted as explicit keyword arguments to `assess_capacity()`.
- **Contract Limitation Documented:** `monthly_taxes` is not currently a field in `FinancialCapacitySnapshot`. If taxes are not supplied via keyword arguments, $D_3$ remains `MISSING_DATA`. A future data contract revision (V2) may incorporate `monthly_taxes` directly into `FinancialCapacitySnapshot`.

---

## 5. Hidden-Default Scan Result

A search for `or 0`, `else 0`, `default`, `STABLE_SALARIED`, `monthly_taxes`, `tax_rate`, `estimated_tax`, `net_income`, `disposable_income` across production Python files confirmed:
- **Zero Prohibited Defaults:** All 8 occurrences in production code are **VALID** dataclass defaults or explicit enum validation checks.
- Zero tax rate estimations or stability defaults remain in engine logic.

---

## 6. QA Review Results

| Category | Status | Evaluation Summary |
|---|---|---|
| A. Financial formula QA | **PASS** | Formulas handle missing values strictly without numerical defaults. |
| B. Missing-data QA | **PASS** | Missing taxes and missing stability produce `MISSING_DATA` constraint status. |
| C. Default-value QA | **PASS** | Zero hidden financial defaults or category defaults remain. |
| D. Capacity-tier safety QA | **PASS** | Missing data never manufactures favorable capacity tiers. |
| E. Confidence separation QA | **PASS** | Calculations are corrected at source; confidence remains output indicator. |
| F. Regression QA | **PASS** | 219 / 219 tests passing cleanly. |
| G. Provenance QA | **PASS** | Audit metadata, version identifiers, and mode tags preserved. |
| H. Explainability QA | **PASS** | Missing input tokens explicitly identify unsupplied fields. |

---

## 7. Test Suite Execution Summary

- **Previous Baseline:** 216 / 216 passed.
- **New Targeted Safety Tests:** Added `test_29_missing_tax_safety`, `test_30_missing_tax_capacity_tier_safety`, `test_10_missing_income_stability_safety`, `test_10b_explicit_income_stability_types`, `test_independent_tax_calculation_fixture`.
- **Final Total Regression:** 219 / 219 passed in 3.63 seconds.

---

## 8. Parameters Remaining Provisional / TBD

### 5 Provisional Parameters:
- `RC-ARCH-03`: min() bottleneck aggregation mechanism.
- `RC-D1-02`: Gross income denominator choice.
- `RC-D2-02`: Salaried reserve requirement (range concept approved; exact value provisional).
- `RC-D2-03`: Self-employed reserve requirement (range concept approved; exact value provisional).
- `RC-CTX-01`: Household aggregate input convention (V1 simplification).

### 13 TBD Parameters (Configurable Stubs):
- `RC-D1-04`, `RC-D1-05`, `RC-D1-06`, `RC-D1-07`
- `RC-D2-04`, `RC-D2-05`, `RC-D2-06`
- `RC-D3-03`, `RC-D3-04`, `RC-D3-05`
- `RC-IS-02`, `RC-INT-02`, `RC-INT-03`

---

## 9. Final Status — Exactly One

```text
PHASE F.3.1.2 ACCEPTED
```

**Phase F.3.1 (Risk Capacity Engine Implementation) is now fully accepted and complete.**

*Note: Phase F.3.2 (Risk Tolerance Engine Implementation) may NOT begin automatically.*
