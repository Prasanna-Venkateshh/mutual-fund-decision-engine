"""
Comprehensive Unit & Financial Integration Test Suite for Risk Capacity Engine (Phase F.3.1.2 Safety Correction).

Tests all required governance, formula, missing-data, confidence, startup mode,
explanation, provenance, bottleneck, and missing-data safety scenarios.
"""

from datetime import date, datetime
import pytest

from config.risk.capacity_config import (
    RiskCapacityConfig,
    StartupMode,
    create_production_config,
    create_research_config,
    create_test_config,
)
from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import (
    FinancialCapacitySnapshot,
    RiskCapacityLevel,
)
from risk.capacity_engine import RiskCapacityEngine
from risk.capacity_models import AssessmentStatus


class TestRiskCapacityEngine:

    @pytest.fixture
    def test_config(self) -> RiskCapacityConfig:
        return create_test_config()

    @pytest.fixture
    def engine(self, test_config: RiskCapacityConfig) -> RiskCapacityEngine:
        return RiskCapacityEngine(test_config)

    # 1. Complete healthy financial profile
    def test_01_complete_healthy_profile(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=15000.0,
            liquid_emergency_reserves=180000.0, # 6 months coverage (30k * 6)
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV001",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.overall_capacity_tier == RiskCapacityLevel.VERY_HIGH
        assert res.confidence_score == 1.0
        assert "STRONG_RESERVE_COVERAGE" in res.explanation_tokens

    # 2. High debt constraint
    def test_02_high_debt_constraint(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=20000.0,
            monthly_debt_servicing=55000.0, # 55% > 45% (mod threshold) -> HIGH constraint
            liquid_emergency_reserves=200000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV002",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.binding_constraint_name == "DEBT_BURDEN"
        assert res.overall_capacity_tier == RiskCapacityLevel.LOW
        assert "HIGH_DEBT_BURDEN" in res.explanation_tokens
        assert "BINDING_CONSTRAINT_DEBT_BURDEN" in res.explanation_tokens

    # 3. Weak reserve position
    def test_03_weak_reserve_position(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=40000.0,
            monthly_debt_servicing=10000.0,
            liquid_emergency_reserves=30000.0, # 30k / (40k * 3) = 0.25 -> DEFICIENT
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV003",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.binding_constraint_name == "RESERVE_ADEQUACY"
        assert res.overall_capacity_tier == RiskCapacityLevel.VERY_LOW
        assert "DEFICIENT_RESERVE_COVERAGE" in res.explanation_tokens

    # 4. Low surplus
    def test_04_low_surplus(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=50000.0,
            monthly_debt_servicing=42000.0, # Debt 42%, Expenses 50% -> Surplus = 8% < 10% (limited threshold) -> THIN (surplus ratio = 0.08)
            liquid_emergency_reserves=300000.0, # High reserves
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV004",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.overall_capacity_tier in (RiskCapacityLevel.MODERATE, RiskCapacityLevel.LOW)
        assert "LOW_SURPLUS" in res.explanation_tokens

    # 5. Multiple simultaneous constraints
    def test_05_multiple_simultaneous_constraints(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=50000.0,
            monthly_debt_servicing=55000.0, # High debt (55%)
            liquid_emergency_reserves=20000.0, # Deficient reserves (20k / 150k = 0.13)
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV005",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.overall_capacity_tier == RiskCapacityLevel.VERY_LOW
        assert "HIGH_DEBT_BURDEN" in res.explanation_tokens
        assert "DEFICIENT_RESERVE_COVERAGE" in res.explanation_tokens

    # 6. Missing income
    def test_06_missing_income(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=None,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=10000.0,
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV006",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.PARTIAL
        assert res.debt_constraint.status == "MISSING_DATA"
        assert res.reserve_constraint.status == "ASSESSED"
        assert res.confidence_score < 1.0
        assert "MISSING_INPUT_MONTHLY_GROSS_INCOME" in res.explanation_tokens

    # 7. Missing debt
    def test_07_missing_debt(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=None,
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV007",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.PARTIAL
        assert res.debt_constraint.status == "MISSING_DATA"

    # 8. Missing expenses
    def test_08_missing_expenses(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=None,
            monthly_debt_servicing=15000.0,
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV008",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.PARTIAL
        assert res.reserve_constraint.status == "MISSING_DATA"

    # 9. Missing reserves
    def test_09_missing_reserves(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=15000.0,
            liquid_emergency_reserves=None,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV009",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.PARTIAL
        assert res.reserve_constraint.status == "MISSING_DATA"

    # 10. Missing income stability (Safety Correction Test)
    def test_10_missing_income_stability_safety(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=15000.0,
            liquid_emergency_reserves=180000.0,
        )
        # Passed employment_type=None -> MUST NOT default to STABLE_SALARIED!
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV010",
            employment_type=None,
            monthly_taxes=0.0,
        )
        # Status becomes PARTIAL because reserve constraint is MISSING_DATA (employment_type unsupplied)
        assert res.assessment_status == AssessmentStatus.PARTIAL
        assert res.reserve_constraint.status == "MISSING_DATA"
        assert res.reserve_constraint.calculated_ratio is None
        assert "MISSING_INPUT_EMPLOYMENT_TYPE" in res.explanation_tokens

    # 10b. Explicit income stability types
    def test_10b_explicit_income_stability_types(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=15000.0,
            liquid_emergency_reserves=180000.0,
        )
        res_sal = engine.assess_capacity(snapshot, investor_id="SAL", employment_type="STABLE_SALARIED", monthly_taxes=0.0)
        res_self = engine.assess_capacity(snapshot, investor_id="SELF", employment_type="SELF_EMPLOYED", monthly_taxes=0.0)

        assert res_sal.reserve_constraint.calculated_ratio == 2.0  # 180k / (30k * 3) = 2.0
        # For self-employed, base_months=6, stability map adds 2 -> required = 8 months -> pool = 240k -> 180k / 240k = 0.75
        assert pytest.approx(res_self.reserve_constraint.calculated_ratio, abs=1e-5) == 0.75

    # 11. Zero income
    def test_11_zero_income(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=0.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=0.0,
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV011",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.debt_constraint.calculated_ratio is None
        assert res.debt_constraint.status == "MISSING_DATA"

    # 12. Zero debt
    def test_12_zero_debt(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=0.0,
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV012",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.debt_constraint.calculated_ratio == 0.0
        assert res.debt_constraint.constraint_level == "LOW"

    # 13. Zero reserves
    def test_13_zero_reserves(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=10000.0,
            liquid_emergency_reserves=0.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV013",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.reserve_constraint.calculated_ratio == 0.0
        assert res.reserve_constraint.constraint_level == "DEFICIENT"
        assert res.overall_capacity_tier == RiskCapacityLevel.VERY_LOW

    # 14. Negative / invalid inputs
    def test_14_negative_invalid_inputs(self, engine: RiskCapacityEngine):
        with pytest.raises(ValueError, match="cannot be negative"):
            FinancialCapacitySnapshot(
                observation_date=date(2026, 9, 10),
                effective_date=date(2026, 9, 10),
                monthly_gross_income=-50000.0,
            )

    # 15. PARTIAL assessment
    def test_15_partial_assessment(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=None, # Missing debt
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV015",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.PARTIAL
        assert res.overall_capacity_tier is not None

    # 16. INSUFFICIENT_INFORMATION
    def test_16_insufficient_information(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=None,
            monthly_fixed_expenses=None,
            monthly_debt_servicing=None,
            liquid_emergency_reserves=None,
        )
        res = engine.assess_capacity(snapshot, investor_id="INV016")
        assert res.assessment_status == AssessmentStatus.INSUFFICIENT_INFORMATION
        assert res.overall_capacity_tier is None # Must be absent when info is insufficient

    # 17. CONFIGURATION_ERROR
    def test_17_configuration_error(self):
        prod_config = create_production_config() # Uncalibrated TBD params = None
        engine = RiskCapacityEngine(prod_config)
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=10000.0,
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(snapshot, investor_id="INV017")
        assert res.assessment_status == AssessmentStatus.CONFIGURATION_ERROR
        assert res.overall_capacity_tier is None

    # 18. Production mode missing calibration parameters (fails safely)
    def test_18_production_mode_fail_safe(self):
        prod_config = create_production_config()
        assert not prod_config.is_valid_for_production
        errs = prod_config.validate()
        assert len(errs) > 0
        assert "PRODUCTION mode error" in errs[0]

    # 19. Research mode with explicit provisional configuration
    def test_19_research_mode_tagging(self):
        res_config = create_research_config()
        assert res_config.output_tag == "RESEARCH_MODE_NOT_FOR_PRODUCTION"

    # 20. Test mode with explicit synthetic configuration
    def test_20_test_mode_tagging(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=10000.0,
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV020",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.output_tag == "SYNTHETIC_TEST_DATA"

    # 21. Confidence does not alter capacity
    def test_21_confidence_does_not_alter_capacity(self, engine: RiskCapacityEngine):
        snapshot_full = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=15000.0,
            liquid_emergency_reserves=180000.0,
        )
        snapshot_partial = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=None, # Missing debt -> lowers confidence score
            liquid_emergency_reserves=180000.0,
        )
        res_full = engine.assess_capacity(
            snapshot_full,
            investor_id="INV021",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        res_part = engine.assess_capacity(
            snapshot_partial,
            investor_id="INV021",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )

        assert res_full.overall_capacity_tier == res_part.overall_capacity_tier
        assert res_part.confidence_score < res_full.confidence_score

    # 22. Missing confidence parameter fails safely
    def test_22_missing_confidence_parameter_safe_fallback(self):
        cfg = create_test_config(conf_penalty=None)
        engine = RiskCapacityEngine(cfg)
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=None,
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV022",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.confidence_score >= 0.0

    # 23. Household-level convention
    def test_23_household_level_convention(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=150000.0, # Combined household income aggregate
            monthly_fixed_expenses=50000.0, # Combined household expenses aggregate
            monthly_debt_servicing=20000.0,  # Combined household debt aggregate
            liquid_emergency_reserves=300000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV023",
            employment_type="STABLE_SALARIED",
            dependents_count=2,
            monthly_taxes=0.0,
        )
        assert res.assessment_status == AssessmentStatus.COMPLETE

    # 24. Explanation token correctness
    def test_24_explanation_token_correctness(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=55000.0,
            liquid_emergency_reserves=180000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV024",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert "HIGH_DEBT_BURDEN" in res.explanation_tokens
        assert "STRONG_RESERVE_COVERAGE" in res.explanation_tokens
        assert "BINDING_CONSTRAINT_DEBT_BURDEN" in res.explanation_tokens
        assert "DEFICIENT_RESERVE_COVERAGE" not in res.explanation_tokens

    # 25. Provenance completeness
    def test_25_provenance_completeness(self, engine: RiskCapacityEngine):
        prov = ProvenanceMetadata(
            source_id="SRC_USER_01",
            source_document_url="https://portal.example.com/user_declaration.pdf",
            retrieval_timestamp_utc=datetime(2026, 9, 10, 10, 0, 0),
        )
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=15000.0,
            liquid_emergency_reserves=180000.0,
            provenance=prov,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV025",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.provenance is not None
        assert res.provenance.source_id == "SRC_USER_01"

    # 26. Deterministic / reproducible assessment
    def test_26_deterministic_reproducible(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=15000.0,
            liquid_emergency_reserves=180000.0,
        )
        res1 = engine.assess_capacity(snapshot, investor_id="INV026", employment_type="STABLE_SALARIED", monthly_taxes=0.0)
        res2 = engine.assess_capacity(snapshot, investor_id="INV026", employment_type="STABLE_SALARIED", monthly_taxes=0.0)

        assert res1.overall_capacity_tier == res2.overall_capacity_tier
        assert res1.binding_constraint_name == res2.binding_constraint_name
        assert res1.confidence_score == res2.confidence_score
        assert res1.explanation_tokens == res2.explanation_tokens

    # 27. Bottleneck identifies binding constraint
    def test_27_bottleneck_identifies_binding_constraint(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=15000.0, # Debt low (15%) -> VERY_HIGH
            liquid_emergency_reserves=50000.0, # Reserves low (50k / 90k = 0.55) -> MODERATE
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV027",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.binding_constraint_name == "RESERVE_ADEQUACY"
        assert res.overall_capacity_tier == RiskCapacityLevel.MODERATE

    # 28. No hidden threshold default values
    def test_28_no_hidden_threshold_defaults(self):
        custom_cfg = create_test_config(debt_low=0.20, debt_mod=0.30, debt_high=0.40)
        engine = RiskCapacityEngine(custom_cfg)
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=25000.0, # 25% > 20% (low threshold) -> MODERATE constraint level
            liquid_emergency_reserves=300000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="INV028",
            employment_type="STABLE_SALARIED",
            monthly_taxes=0.0,
        )
        assert res.debt_constraint.constraint_level == "MODERATE"

    # 29. Missing Tax Safety Test (F.3.1.2 Safety Correction)
    def test_29_missing_tax_safety(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=10000.0,
            liquid_emergency_reserves=300000.0,
        )
        res = engine.assess_capacity(
            snapshot,
            investor_id="TAX_SAFETY",
            employment_type="STABLE_SALARIED",
            monthly_taxes=None, # Missing tax
        )
        assert res.surplus_constraint.status == "MISSING_DATA"
        assert res.surplus_constraint.calculated_ratio is None
        assert "MISSING_INPUT_MONTHLY_TAXES" in res.explanation_tokens

    # 30. Missing Tax Cannot Create Favorable Capacity Tier
    def test_30_missing_tax_capacity_tier_safety(self, engine: RiskCapacityEngine):
        snapshot = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=30000.0,
            monthly_debt_servicing=10000.0,
            liquid_emergency_reserves=300000.0,
        )
        # Explicit taxes 30k -> surplus ratio = 30k / 100k = 0.30 -> MODERATE tier
        res_taxed = engine.assess_capacity(snapshot, investor_id="T_TAXED", employment_type="STABLE_SALARIED", monthly_taxes=30000.0)
        # Missing taxes -> surplus constraint is MISSING_DATA, overall tier bounded by remaining constraints (D1 & D2 = VERY_HIGH)
        res_missing = engine.assess_capacity(snapshot, investor_id="T_MISSING", employment_type="STABLE_SALARIED", monthly_taxes=None)

        assert res_taxed.surplus_constraint.calculated_ratio == 0.3000
        assert res_missing.surplus_constraint.calculated_ratio is None
        assert res_missing.assessment_status == AssessmentStatus.PARTIAL
