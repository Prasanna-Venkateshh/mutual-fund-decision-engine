# Phase F.2 — Data Contracts & Investor Profile Persistence Implementation Report

**Phase:** Phase F.2 — Data Contracts & Investor Profile Persistence  
**Date:** 2026-09-09 UTC  
**Status:** `PHASE F.2 ACCEPTED`  
**Baseline Test Count:** 170 tests passing  
**Final Test Count:** 185 tests passing (100% pass rate, 0 regressions)

---

## 1. Executive Summary

Phase F.2 successfully implements the data foundation for the future **Suitability & Risk Alignment Engine**.

The implementation establishes frozen, versioned, provenance-preserving data contracts and an SQLite persistence repository for storing investor profiles, investment goals, and suitability assessment output results.

The phase strictly enforces the boundary condition:
> **DATA CONTRACTS ONLY.** No financial calculations (debt servicing caps, capacity tiers, tolerance scoring, lower-of-two rule, time horizon ceilings, affordability gap resolution) are implemented inside the data contracts.

---

## 2. Implemented Data Contracts

### A. Financial Capacity Snapshot (`models/investor_profile.py`)
- **Class:** `FinancialCapacitySnapshot` (frozen=True)
- **Key Fields:** `observation_date`, `effective_date`, `monthly_gross_income`, `monthly_fixed_expenses`, `monthly_debt_servicing`, `liquid_emergency_reserves`, `emergency_reserve_months`, `savings_ratio`, `sustainable_monthly_capacity`, `capacity_tier`, `confidence_score`, `provenance`, `methodology_version`, `rule_version`.
- **Validation:** Non-negative check on monetary inputs; confidence score bounded in `[0.0, 1.0]`. Missing values remain explicitly `None` (Missing != 0).

### B. Behavioral Tolerance Snapshot (`models/investor_profile.py`)
- **Class:** `BehavioralToleranceSnapshot` (frozen=True)
- **Key Fields:** `observation_date`, `assessment_date`, `loss_reaction_choice`, `stagnation_comfort_choice`, `historical_drawdown_action`, `volatility_preference`, `behavioral_consistency_score`, `tolerance_tier`, `confidence_score`, `provenance`, `methodology_version`, `rule_version`.
- **Validation:** Confidence score and consistency score bounded in `[0.0, 1.0]`. Unanswered scenario questions remain explicitly `None`.

### C. Investor Profile Snapshot (`models/investor_profile.py`)
- **Class:** `InvestorProfileSnapshot` (frozen=True)
- **Key Fields:** `profile_id`, `investor_id`, `profile_version`, `effective_date`, `birth_date`, `financial_capacity`, `behavioral_tolerance`, `overall_effective_risk_alignment`, `profiling_tier_completed`, `status`, `confidence_score`, `provenance`, `created_timestamp_utc`, `methodology_version`, `rule_version`, `is_stale`.
- **Validation:** Profile ID & Investor ID non-empty check; profiling tier completed in `[1, 3]`; birth date not in future relative to effective date. Immutable for append-only audit trail.

### D. Goal Profile (`models/goal_profile.py`)
- **Class:** `GoalProfile` (frozen=True)
- **Key Fields:** `goal_id`, `investor_id`, `goal_name`, `goal_category`, `target_date`, `effective_horizon_years`, `target_amount`, `is_target_amount_known`, `is_target_date_known`, `priority`, `current_funding_amount`, `current_monthly_contribution`, `is_general_wealth`, `provenance`, `methodology_version`, `rule_version`.
- **Validation:** Non-negative monetary amounts; positive effective horizon; supports explicit `is_target_amount_known=False` when target amount is unknown/skipped; supports `is_general_wealth=True` for non-goal surplus capital.

### E. Suitability Assessment Result (`models/suitability_assessment.py`)
- **Class:** `SuitabilityAssessmentResult` (frozen=True)
- **Key Fields:** `assessment_id`, `investor_id`, `profile_version_used`, `canonical_scheme_id`, `amfi_code`, `scheme_name`, `category`, `subcategory`, `observation_date`, `suitability_status`, `goal_id`, `effective_risk_alignment`, `risk_capacity_result`, `risk_tolerance_result`, `max_permissible_asset_risk`, `effective_horizon_years`, `is_horizon_compatible`, `is_liquidity_compatible`, `affordability_status`, `sustainable_sip_capacity`, `fund_quality_score_consumed`, `fund_quality_confidence_consumed`, `suitability_confidence_score`, `constraints_applied`, `rejection_reasons`, `summary_explanation`, `provenance`, `methodology_version`, `rule_version`.

---

## 3. Persistence Implementation

- **Module:** `data/repositories/suitability_repository.py`
- **Class:** `SuitabilityRepository`
- **Database Tables Created:**
  - `investor_profile_snapshots` (UNIQUE constraint on `(investor_id, profile_version)`)
  - `goal_profiles` (PRIMARY KEY `goal_id`)
  - `suitability_assessment_records` (PRIMARY KEY `assessment_id`)
- **Serialization & Deserialization:** Full JSON roundtrip serialization preserving date ISO formatting, enums, optional fields, and nested snapshots.

---

## 4. Test Suite Summary

A dedicated test suite was implemented in `tests/financial/test_suitability_contracts.py` (15 passing tests):
- `test_01_valid_financial_capacity_snapshot`: PASSED
- `test_02_missing_financial_inputs_representation`: PASSED
- `test_03_valid_behavioral_tolerance_snapshot`: PASSED
- `test_04_missing_behavioral_responses`: PASSED
- `test_05_investor_profile_snapshot_versioning_and_immutability`: PASSED
- `test_06_multiple_goal_profiles_for_same_investor`: PASSED
- `test_07_goal_profile_without_target_amount`: PASSED
- `test_08_goal_profile_without_target_date`: PASSED
- `test_09_general_wealth_profile_without_goals`: PASSED
- `test_10_valid_suitability_assessment_result`: PASSED
- `test_11_missing_unknown_suitability_output_fields`: PASSED
- `test_12_provenance_and_version_preservation`: PASSED
- `test_13_invalid_values_rejected_by_contract_validation`: PASSED
- `test_14_sqlite_persistence_roundtrip`: PASSED
- `test_15_contracts_contain_no_provisional_calculation_rules`: PASSED

### Full Repository Regression Status
```
185 passed in 1.71s
```

---

## 5. Explicitly Excluded Financial Logic

The following financial calculation rules were **deliberately NOT implemented** in Phase F.2 and remain scheduled for subsequent sub-phases:
- Risk capacity tier calculation / debt servicing cap ($60\%$) (Scheduled for Phase F.3)
- Risk tolerance tier calculation / 20% drawdown scenario scoring (Scheduled for Phase F.4)
- Lower-of-the-two risk alignment rule (Scheduled for Phase F.5)
- Time horizon ceiling rules & risk bounds (Scheduled for Phase F.6)
- Affordability gap resolution pathways & SIP capacity (Scheduled for Phase F.7)
- Material change detection & reassessment triggers (Scheduled for Phase F.9)
