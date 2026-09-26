"""
Independent Mathematical Test Fixtures for Risk Capacity Engine (Phase F.3.1.2 Safety Correction).

INDEPENDENT EXPECTED-VALUE FIXTURES:
These expected values are hardcoded / independently computed using pure arithmetic
(outside of production code) to verify mathematical correctness.
"""

from datetime import date
import pytest

from config.risk.capacity_config import create_test_config
from models.investor_profile import FinancialCapacitySnapshot, RiskCapacityLevel
from risk.capacity_engine import RiskCapacityEngine
from risk.capacity_models import AssessmentStatus


class TestRiskCapacityIndependentFixtures:

    def test_independent_mathematical_fixture_1(self):
        """
        Independent Math Verification Fixture 1:
        
        Inputs:
          Gross Income = Rs 200,000 / month
          Fixed Expenses = Rs 60,000 / month
          Debt Servicing = Rs 40,000 / month
          Taxes = Rs 20,000 / month
          Reserves = Rs 360,000
          Employment = STABLE_SALARIED (base_months = 3.0)
          Dependents = 1 (dep_adj = 1.0 month)
          
        Independent Arithmetic Calculations:
          1. Debt Burden Ratio = 40,000 / 200,000 = 0.2000 (20.0%)
             - Thresholds: LOW <= 0.30 -> Constraint Level = "LOW"
             - Ceiling Tier = VERY_HIGH
             
          2. Required Coverage Months = 3.0 (salaried) + 0.0 (stability) + 1.0 (1 dep * 1.0) = 4.0 months
             - Required Reserve Pool = 60,000 * 4.0 = Rs 240,000
             - Reserve Adequacy Ratio = 360,000 / 240,000 = 1.5000 (150%)
             - Thresholds: Ratio >= 1.0 -> Constraint Level = "OPTIMAL"
             - Ceiling Tier = VERY_HIGH
             
          3. Surplus Ratio = (200,000 - 20,000 - 60,000 - 40,000) / 200,000 = 80,000 / 200,000 = 0.4000 (40.0%)
             - Thresholds: Ratio >= 0.20 -> Constraint Level = "ADEQUATE"
             - Ceiling Tier = VERY_HIGH
             
          4. Bottleneck Aggregation:
             - min(VERY_HIGH, VERY_HIGH, VERY_HIGH) = VERY_HIGH
             
          5. Assessment Status = COMPLETE, Confidence = 1.0
        """
        cfg = create_test_config(
            debt_low=0.30,
            debt_mod=0.45,
            debt_high=0.60,
            reserve_salaried_months=3.0,
            reserve_dependent_adj=1.0,
            surplus_adequate=0.20,
        )
        engine = RiskCapacityEngine(cfg)

        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=200000.0,
            monthly_fixed_expenses=60000.0,
            monthly_debt_servicing=40000.0,
            liquid_emergency_reserves=360000.0,
        )

        res = engine.assess_capacity(
            snapshot,
            investor_id="MATH_FIXTURE_01",
            employment_type="STABLE_SALARIED",
            dependents_count=1,
            monthly_taxes=20000.0,
        )

        # Independent assertions
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert pytest.approx(res.debt_constraint.calculated_ratio, abs=1e-5) == 0.2000
        assert res.debt_constraint.constraint_level == "LOW"
        assert res.debt_constraint.ceiling_capacity_tier == RiskCapacityLevel.VERY_HIGH

        assert pytest.approx(res.reserve_constraint.calculated_ratio, abs=1e-5) == 1.5000
        assert res.reserve_constraint.constraint_level == "OPTIMAL"
        assert res.reserve_constraint.ceiling_capacity_tier == RiskCapacityLevel.VERY_HIGH

        assert pytest.approx(res.surplus_constraint.calculated_ratio, abs=1e-5) == 0.4000
        assert res.surplus_constraint.constraint_level == "ADEQUATE"
        assert res.surplus_constraint.ceiling_capacity_tier == RiskCapacityLevel.VERY_HIGH

        assert res.overall_capacity_tier == RiskCapacityLevel.VERY_HIGH

    def test_independent_mathematical_fixture_2(self):
        """
        Independent Math Verification Fixture 2 (High Debt Bottleneck):
        
        Inputs:
          Gross Income = Rs 100,000 / month
          Fixed Expenses = Rs 30,000 / month
          Debt Servicing = Rs 50,000 / month
          Taxes = Rs 0 / month
          Reserves = Rs 180,000
          Employment = SELF_EMPLOYED (base_months = 6.0)
          Dependents = 0
          
        Independent Arithmetic Calculations:
          1. Debt Burden Ratio = 50,000 / 100,000 = 0.5000 (50.0%)
             - Thresholds: 0.45 < 0.50 <= 0.60 -> Constraint Level = "HIGH"
             - Ceiling Tier = LOW (per test debt_map: HIGH -> LOW)
             
          2. Required Coverage Months = 6.0 (self-employed) + 2.0 (stability map) + 0 = 8.0 months
             - Required Reserve Pool = 30,000 * 8.0 = Rs 240,000
             - Reserve Adequacy Ratio = 180,000 / 240,000 = 0.7500 (75%)
             - Thresholds: 0.75 >= 0.75 -> Constraint Level = "ADEQUATE"
             - Ceiling Tier = HIGH (per test reserve_map: ADEQUATE -> HIGH)
             
          3. Surplus Ratio = (100,000 - 0 - 30,000 - 50,000) / 100,000 = 20,000 / 100,000 = 0.2000 (20.0%)
             - Thresholds: Ratio >= 0.20 -> Constraint Level = "ADEQUATE"
             - Ceiling Tier = VERY_HIGH
             
          4. Bottleneck Aggregation:
             - min(LOW, HIGH, VERY_HIGH) = LOW
             - Binding Constraint = DEBT_BURDEN
        """
        cfg = create_test_config()
        engine = RiskCapacityEngine(cfg)

        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=50000.0,
            liquid_emergency_reserves=180000.0,
        )

        res = engine.assess_capacity(
            snapshot,
            investor_id="MATH_FIXTURE_02",
            employment_type="SELF_EMPLOYED",
            dependents_count=0,
            monthly_taxes=0.0,
        )

        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert pytest.approx(res.debt_constraint.calculated_ratio, abs=1e-5) == 0.5000
        assert res.debt_constraint.constraint_level == "HIGH"

        assert pytest.approx(res.reserve_constraint.calculated_ratio, abs=1e-5) == 0.7500
        assert res.reserve_constraint.constraint_level == "ADEQUATE"

        assert pytest.approx(res.surplus_constraint.calculated_ratio, abs=1e-5) == 0.2000
        assert res.surplus_constraint.constraint_level == "ADEQUATE"

        assert res.overall_capacity_tier == RiskCapacityLevel.LOW
        assert res.binding_constraint_name == "DEBT_BURDEN"
        assert res.debt_constraint.is_binding is True

    def test_independent_tax_calculation_fixture(self):
        """
        Independent Math Verification Fixture 3 (F.3.1.2 Tax Safety Correction):
        
        Profile:
          Gross Income = Rs 100,000
          Fixed Expenses = Rs 30,000
          Debt Servicing = Rs 10,000
          Reserves = Rs 300,000
          Employment = STABLE_SALARIED
          
        Case A: Explicit Non-Zero Taxes = Rs 20,000
          Expected Surplus Ratio = (100,000 - 20,000 - 30,000 - 10,000) / 100,000 = 40,000 / 100,000 = 0.4000 (40%)
          
        Case B: Missing Taxes (monthly_taxes = None)
          Expected D3 Ratio = None (MISSING_DATA)
          Confirm: Engine does NOT substitute zero taxes or invent a tax rate.
          
        Case C: Explicit Declared Zero Taxes (monthly_taxes = 0.0)
          Expected Surplus Ratio = (100,000 - 0 - 30,000 - 10,000) / 100,000 = 60,000 / 100,000 = 0.6000 (60%)
        """
        cfg = create_test_config()
        engine = RiskCapacityEngine(cfg)

        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=10000.0,
            liquid_emergency_reserves=300000.0,
        )

        # Case A: Explicit Non-Zero Taxes
        res_taxed = engine.assess_capacity(
            snapshot,
            investor_id="TAX_TEST_A",
            employment_type="STABLE_SALARIED",
            monthly_taxes=20000.0,
        )
        assert pytest.approx(res_taxed.surplus_constraint.calculated_ratio, abs=1e-5) == 0.4000
        assert res_taxed.surplus_constraint.status == "ASSESSED"

        # Case B: Missing Taxes (monthly_taxes = None) -> MUST return None / MISSING_DATA
        res_missing = engine.assess_capacity(
            snapshot,
            investor_id="TAX_TEST_B",
            employment_type="STABLE_SALARIED",
            monthly_taxes=None,
        )
        assert res_missing.surplus_constraint.calculated_ratio is None
        assert res_missing.surplus_constraint.status == "MISSING_DATA"

        # Case C: Explicit Declared Zero Taxes
        res_zero = engine.assess_capacity(
            snapshot,
            investor_id="TAX_TEST_C",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert pytest.approx(res_zero.surplus_constraint.calculated_ratio, abs=1e-5) == 0.6000
        assert res_zero.surplus_constraint.status == "ASSESSED"
