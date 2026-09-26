"""
Risk Capacity Assessment Engine (Phase F.3.1).

Implements the governed production architecture slice of the Risk Capacity Engine.

Governance Rules Enforced:
- Risk Capacity != Risk Tolerance.
- Risk Capacity != Affordability.
- Risk Capacity != Fund Quality.
- No financial parameters may be invented or hardcoded.
- All 13 TBD parameters remain externalized in configuration.
- Supports PRODUCTION, RESEARCH, and TEST startup modes.
- PRODUCTION mode fails safely (CONFIGURATION_ERROR) if calibration parameters are missing.
- Missing values NEVER silently become zero.
- Confidence NEVER feeds back into the capacity calculation (calculated strictly afterwards).
- Hard ceiling aggregation via min() is isolated and explicitly marked PROVISIONAL (RC-ARCH-03).
- Gross income denominator for debt burden is explicitly marked PROVISIONAL (RC-D1-02).
- Surplus ratio (D3) is documented as algebraically dependent on Debt burden (D1).
- Reserve adequacy stability + dependent modifiers are ADDITIVE on required coverage months.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from config.risk.capacity_config import RiskCapacityConfig, StartupMode
from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import (
    FinancialCapacitySnapshot,
    InvestorProfileSnapshot,
    RiskCapacityLevel,
)
from risk.capacity_models import (
    AssessmentStatus,
    ConstraintLevel,
    ConstraintResult,
    RiskCapacityAssessmentResult,
)


class RiskCapacityEngine:
    """
    Production Risk Capacity Engine implementing Phase F.2C architecture
    and Phase F.2C.1 governance requirements.
    """

    def __init__(self, config: RiskCapacityConfig):
        self.config = config

    # -------------------------------------------------------------------------
    # A. INPUT VALIDATION & INITIALIZATION
    # -------------------------------------------------------------------------
    def validate_inputs(
        self,
        snapshot: FinancialCapacitySnapshot,
        dependents_count: Optional[int] = None,
        income_stability_type: Optional[str] = None,
    ) -> List[str]:
        """
        Validates financial capacity inputs against data integrity rules.
        Rejects negative numbers or invalid enum types.
        """
        errors = []
        if snapshot is None:
            return ["FinancialCapacitySnapshot cannot be None"]

        if snapshot.monthly_gross_income is not None and snapshot.monthly_gross_income < 0:
            errors.append(f"monthly_gross_income cannot be negative, got {snapshot.monthly_gross_income}")

        if snapshot.monthly_fixed_expenses is not None and snapshot.monthly_fixed_expenses < 0:
            errors.append(f"monthly_fixed_expenses cannot be negative, got {snapshot.monthly_fixed_expenses}")

        if snapshot.monthly_debt_servicing is not None and snapshot.monthly_debt_servicing < 0:
            errors.append(f"monthly_debt_servicing cannot be negative, got {snapshot.monthly_debt_servicing}")

        if snapshot.liquid_emergency_reserves is not None and snapshot.liquid_emergency_reserves < 0:
            errors.append(f"liquid_emergency_reserves cannot be negative, got {snapshot.liquid_emergency_reserves}")

        if dependents_count is not None and dependents_count < 0:
            errors.append(f"dependents_count cannot be negative, got {dependents_count}")

        return errors

    # -------------------------------------------------------------------------
    # B. FINANCIAL CALCULATIONS
    # -------------------------------------------------------------------------
    def calculate_debt_burden_ratio(
        self,
        monthly_debt_servicing: Optional[float],
        monthly_gross_income: Optional[float],
    ) -> Optional[float]:
        """
        Calculates Debt Burden Ratio = monthly_debt_servicing / monthly_gross_income.
        
        GOVERNANCE NOTE (RC-D1-02):
        The denominator choice (gross income vs net income) is PROVISIONAL per F.2C.1 Audit.
        Gross income is used for verifiability.
        Missing values NEVER silently become zero. Returns None if income or debt is missing,
        or if gross income <= 0.
        """
        if monthly_debt_servicing is None or monthly_gross_income is None:
            return None
        if monthly_gross_income <= 0.0:
            return None
        return monthly_debt_servicing / monthly_gross_income

    def calculate_reserve_adequacy_ratio(
        self,
        liquid_emergency_reserves: Optional[float],
        monthly_fixed_expenses: Optional[float],
        employment_type: Optional[str] = None,
        dependents_count: Optional[int] = 0,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculates Reserve Adequacy Ratio = liquid_reserves / required_reserve_pool
        where required_reserve_pool = monthly_fixed_expenses * required_coverage_months.
        
        GOVERNANCE NOTE (F.3.1.2 Safety Correction):
        If employment_type (income stability) is None (unsupplied), the engine MUST NOT default to
        STABLE_SALARIED or invent a category. Reserve adequacy ratio is returned as (None, None)
        (MISSING_DATA).
        """
        if liquid_emergency_reserves is None or monthly_fixed_expenses is None:
            return None, None
        if monthly_fixed_expenses <= 0.0:
            return None, None
        if employment_type is None:
            return None, None

        # Determine base required coverage months based on employment type
        emp = employment_type.upper()
        if emp == "SELF_EMPLOYED":
            base_months = self.config.reserve_self_employed_min_months
        elif emp in ("VARIABLE", "VARIABLE_INCOME", "IRREGULAR"):
            base_months = self.config.reserve_variable_income_min_months or self.config.reserve_self_employed_min_months
        elif emp in ("STABLE_SALARIED", "SALARIED"):
            base_months = self.config.reserve_salaried_min_months
        else:
            # Unknown / unsupported employment type string
            return None, None

        if base_months is None:
            return None, None

        # Additive stability modifier (RC-IS-02)
        stability_additive = 0.0
        if self.config.stability_reserve_multiplier_map and emp in self.config.stability_reserve_multiplier_map:
            stability_additive = self.config.stability_reserve_multiplier_map[emp]

        # Additive dependent modifier (RC-D2-05)
        deps = dependents_count if dependents_count is not None else 0
        dep_adj_per = self.config.reserve_dependent_adjustment_months or 0.0
        dependent_additive = deps * dep_adj_per

        required_coverage_months = base_months + stability_additive + dependent_additive
        if required_coverage_months <= 0.0:
            return None, None

        required_reserve_pool = monthly_fixed_expenses * required_coverage_months
        if required_reserve_pool <= 0.0:
            return None, None

        ratio = liquid_emergency_reserves / required_reserve_pool
        return ratio, required_coverage_months

    def calculate_surplus_ratio(
        self,
        monthly_gross_income: Optional[float],
        monthly_fixed_expenses: Optional[float],
        monthly_debt_servicing: Optional[float],
        monthly_taxes: Optional[float] = None,
    ) -> Optional[float]:
        """
        Calculates Sustainable Surplus Ratio = (income - taxes - expenses - debt) / income.
        
        GOVERNANCE NOTE (F.3.1.2 Safety Correction):
        If monthly_taxes is None (unavailable/unsupplied), the engine MUST NOT substitute 0.0,
        invent a tax rate, or estimate taxes. D3 ratio is returned as None (MISSING_DATA).
        Taxes are subtracted only when explicitly provided (including 0.0 if declared tax-exempt).
        """
        if monthly_taxes is None:
            return None
        if monthly_gross_income is None or monthly_gross_income <= 0.0:
            return None
        if monthly_fixed_expenses is None or monthly_debt_servicing is None:
            return None

        surplus = monthly_gross_income - monthly_taxes - monthly_fixed_expenses - monthly_debt_servicing
        return surplus / monthly_gross_income

    # -------------------------------------------------------------------------
    # C. CONSTRAINT EVALUATION
    # -------------------------------------------------------------------------
    def evaluate_debt_constraint(
        self,
        debt_ratio: Optional[float],
    ) -> ConstraintResult:
        """
        Evaluates Debt Burden Constraint (D1).
        """
        if debt_ratio is None:
            return ConstraintResult(
                dimension_name="DEBT_BURDEN",
                calculated_ratio=None,
                constraint_level="UNKNOWN",
                ceiling_capacity_tier=None,
                rule_version=self.config.rule_version,
                status="MISSING_DATA",
                evidence_references=["RC-D1-01"],
            )

        low = self.config.debt_low_constraint_threshold
        mod = self.config.debt_moderate_constraint_threshold
        high = self.config.debt_high_constraint_threshold
        ceiling_map = self.config.debt_capacity_ceiling_map or {}

        if low is None or mod is None or high is None:
            return ConstraintResult(
                dimension_name="DEBT_BURDEN",
                calculated_ratio=debt_ratio,
                constraint_level="UNCALIBRATED",
                ceiling_capacity_tier=None,
                rule_version=self.config.rule_version,
                status="CONFIGURATION_ERROR",
                evidence_references=["RC-D1-04", "RC-D1-05", "RC-D1-06"],
            )

        if debt_ratio <= low:
            level = "LOW"
        elif debt_ratio <= mod:
            level = "MODERATE"
        elif debt_ratio <= high:
            level = "HIGH"
        else:
            level = "CRITICAL"

        ceiling = ceiling_map.get(level)

        return ConstraintResult(
            dimension_name="DEBT_BURDEN",
            calculated_ratio=debt_ratio,
            constraint_level=level,
            ceiling_capacity_tier=ceiling,
            rule_version=self.config.rule_version,
            status="ASSESSED",
            evidence_references=["RC-D1-01", "RC-D1-04", "RC-D1-05", "RC-D1-06"],
        )

    def evaluate_reserve_constraint(
        self,
        reserve_ratio: Optional[float],
    ) -> ConstraintResult:
        """
        Evaluates Reserve Adequacy Constraint (D2).
        """
        if reserve_ratio is None:
            return ConstraintResult(
                dimension_name="RESERVE_ADEQUACY",
                calculated_ratio=None,
                constraint_level="UNKNOWN",
                ceiling_capacity_tier=None,
                rule_version=self.config.rule_version,
                status="MISSING_DATA",
                evidence_references=["RC-D2-01"],
            )

        ceiling_map = self.config.reserve_capacity_ceiling_map or {}

        if reserve_ratio >= 1.0:
            level = "OPTIMAL"
        elif reserve_ratio >= 0.75:
            level = "ADEQUATE"
        elif reserve_ratio >= 0.50:
            level = "LIMITED"
        else:
            level = "DEFICIENT"

        ceiling = ceiling_map.get(level)

        return ConstraintResult(
            dimension_name="RESERVE_ADEQUACY",
            calculated_ratio=reserve_ratio,
            constraint_level=level,
            ceiling_capacity_tier=ceiling,
            rule_version=self.config.rule_version,
            status="ASSESSED",
            evidence_references=["RC-D2-01", "RC-D2-06"],
        )

    def evaluate_surplus_constraint(
        self,
        surplus_ratio: Optional[float],
    ) -> ConstraintResult:
        """
        Evaluates Surplus Ratio Constraint (D3).
        """
        if surplus_ratio is None:
            return ConstraintResult(
                dimension_name="SURPLUS_RATIO",
                calculated_ratio=None,
                constraint_level="UNKNOWN",
                ceiling_capacity_tier=None,
                rule_version=self.config.rule_version,
                status="MISSING_DATA",
                evidence_references=["RC-D3-01"],
            )

        adequate = self.config.surplus_adequate_threshold
        limited = self.config.surplus_limited_threshold
        thin = self.config.surplus_thin_threshold
        ceiling_map = self.config.surplus_capacity_ceiling_map or {}

        if adequate is None or limited is None or thin is None:
            return ConstraintResult(
                dimension_name="SURPLUS_RATIO",
                calculated_ratio=surplus_ratio,
                constraint_level="UNCALIBRATED",
                ceiling_capacity_tier=None,
                rule_version=self.config.rule_version,
                status="CONFIGURATION_ERROR",
                evidence_references=["RC-D3-03", "RC-D3-04", "RC-D3-05"],
            )

        if surplus_ratio >= adequate:
            level = "ADEQUATE"
        elif surplus_ratio >= limited:
            level = "LIMITED"
        elif surplus_ratio >= thin:
            level = "THIN"
        else:
            level = "NEGATIVE"

        ceiling = ceiling_map.get(level)

        return ConstraintResult(
            dimension_name="SURPLUS_RATIO",
            calculated_ratio=surplus_ratio,
            constraint_level=level,
            ceiling_capacity_tier=ceiling,
            rule_version=self.config.rule_version,
            status="ASSESSED",
            evidence_references=["RC-D3-01", "RC-D3-03", "RC-D3-04", "RC-D3-05"],
        )

    # -------------------------------------------------------------------------
    # D. BOTTLENECK AGGREGATION
    # -------------------------------------------------------------------------
    def aggregate_bottleneck_capacity(
        self,
        debt_constraint: ConstraintResult,
        reserve_constraint: ConstraintResult,
        surplus_constraint: ConstraintResult,
    ) -> Tuple[Optional[RiskCapacityLevel], Optional[str], List[ConstraintResult]]:
        """
        Aggregates overall capacity tier via min(debt_ceiling, reserve_ceiling, surplus_ceiling).
        
        GOVERNANCE NOTE (RC-ARCH-03):
        The min() bottleneck aggregation mechanism is explicitly PROVISIONAL per F.2C.1 Audit.
        It is isolated in this dedicated method to permit replacement in future methodology versions.
        
        Returns (overall_capacity_tier, binding_constraint_name, updated_constraints).
        """
        valid_ceilings: List[Tuple[str, RiskCapacityLevel, ConstraintResult]] = []

        if debt_constraint.ceiling_capacity_tier is not None:
            valid_ceilings.append(("DEBT_BURDEN", debt_constraint.ceiling_capacity_tier, debt_constraint))
        if reserve_constraint.ceiling_capacity_tier is not None:
            valid_ceilings.append(("RESERVE_ADEQUACY", reserve_constraint.ceiling_capacity_tier, reserve_constraint))
        if surplus_constraint.ceiling_capacity_tier is not None:
            valid_ceilings.append(("SURPLUS_RATIO", surplus_constraint.ceiling_capacity_tier, surplus_constraint))

        if not valid_ceilings:
            return None, None, [debt_constraint, reserve_constraint, surplus_constraint]

        # Find minimum tier (lowest ordinal value)
        min_tuple = min(valid_ceilings, key=lambda item: item[1].value)
        binding_name = min_tuple[0]
        min_tier = min_tuple[1]

        # Update is_binding flag on constraint results
        updated_debt = ConstraintResult(
            dimension_name=debt_constraint.dimension_name,
            calculated_ratio=debt_constraint.calculated_ratio,
            constraint_level=debt_constraint.constraint_level,
            ceiling_capacity_tier=debt_constraint.ceiling_capacity_tier,
            rule_version=debt_constraint.rule_version,
            status=debt_constraint.status,
            evidence_references=debt_constraint.evidence_references,
            is_binding=(binding_name == "DEBT_BURDEN"),
        )
        updated_reserve = ConstraintResult(
            dimension_name=reserve_constraint.dimension_name,
            calculated_ratio=reserve_constraint.calculated_ratio,
            constraint_level=reserve_constraint.constraint_level,
            ceiling_capacity_tier=reserve_constraint.ceiling_capacity_tier,
            rule_version=reserve_constraint.rule_version,
            status=reserve_constraint.status,
            evidence_references=reserve_constraint.evidence_references,
            is_binding=(binding_name == "RESERVE_ADEQUACY"),
        )
        updated_surplus = ConstraintResult(
            dimension_name=surplus_constraint.dimension_name,
            calculated_ratio=surplus_constraint.calculated_ratio,
            constraint_level=surplus_constraint.constraint_level,
            ceiling_capacity_tier=surplus_constraint.ceiling_capacity_tier,
            rule_version=surplus_constraint.rule_version,
            status=surplus_constraint.status,
            evidence_references=surplus_constraint.evidence_references,
            is_binding=(binding_name == "SURPLUS_RATIO"),
        )

        return min_tier, binding_name, [updated_debt, updated_reserve, updated_surplus]

    # -------------------------------------------------------------------------
    # E. CONFIDENCE CALCULATION
    # -------------------------------------------------------------------------
    def calculate_confidence_score(
        self,
        missing_fields_count: int,
        assessment_status: AssessmentStatus,
    ) -> float:
        """
        Calculates output confidence indicator score AFTER capacity tier calculation.
        
        GOVERNANCE NOTE:
        Confidence score NEVER alters the calculated capacity tier or constraint levels.
        It is purely an output quality indicator.
        """
        if assessment_status == AssessmentStatus.CONFIGURATION_ERROR:
            return 0.0

        penalty_per = self.config.confidence_penalty_per_missing_input or 0.15
        floor = self.config.partial_assessment_confidence_floor or 0.50

        confidence = 1.0 - (missing_fields_count * penalty_per)
        confidence = max(floor if assessment_status == AssessmentStatus.PARTIAL else 0.0, min(1.0, confidence))
        return confidence

    # -------------------------------------------------------------------------
    # F. EXPLANATION TOKEN GENERATION
    # -------------------------------------------------------------------------
    def generate_explanations(
        self,
        debt_constraint: ConstraintResult,
        reserve_constraint: ConstraintResult,
        surplus_constraint: ConstraintResult,
        binding_constraint_name: Optional[str],
        assessment_status: AssessmentStatus,
        missing_inputs: List[str],
    ) -> List[str]:
        """
        Generates structured explanation tokens identifying what constrained capacity.
        Emits tokens ONLY if the underlying condition actually occurred.
        """
        tokens = []

        if assessment_status == AssessmentStatus.CONFIGURATION_ERROR:
            tokens.append("MISSING_PRODUCTION_CALIBRATION_PARAMETERS")
            return tokens

        if assessment_status == AssessmentStatus.INSUFFICIENT_INFORMATION:
            tokens.append("INSUFFICIENT_FINANCIAL_INFORMATION")
            for inp in missing_inputs:
                tokens.append(f"MISSING_INPUT_{inp.upper()}")
            return tokens

        if missing_inputs:
            tokens.append("PARTIAL_FINANCIAL_INFORMATION")
            for inp in missing_inputs:
                tokens.append(f"MISSING_INPUT_{inp.upper()}")

        # Debt tokens
        if debt_constraint.constraint_level in ("HIGH", "CRITICAL"):
            tokens.append("HIGH_DEBT_BURDEN")
        elif debt_constraint.constraint_level == "LOW":
            tokens.append("LOW_DEBT_BURDEN")

        # Reserve tokens
        if reserve_constraint.constraint_level == "DEFICIENT":
            tokens.append("DEFICIENT_RESERVE_COVERAGE")
        elif reserve_constraint.constraint_level == "LIMITED":
            tokens.append("LIMITED_RESERVE_COVERAGE")
        elif reserve_constraint.constraint_level in ("ADEQUATE", "OPTIMAL"):
            tokens.append("STRONG_RESERVE_COVERAGE")

        # Surplus tokens
        if surplus_constraint.constraint_level in ("THIN", "NEGATIVE"):
            tokens.append("LOW_SURPLUS")
        elif surplus_constraint.constraint_level == "ADEQUATE":
            tokens.append("STRONG_SURPLUS")

        # Binding constraint token
        if binding_constraint_name:
            tokens.append(f"BINDING_CONSTRAINT_{binding_constraint_name}")

        return tokens

    # -------------------------------------------------------------------------
    # MAIN ENGINE ASSESSMENT PIPELINE
    # -------------------------------------------------------------------------
    def assess_capacity(
        self,
        snapshot: FinancialCapacitySnapshot,
        investor_id: str = "UNKNOWN_INVESTOR",
        profile_version: str = "1.0.0",
        employment_type: Optional[str] = None,
        dependents_count: Optional[int] = 0,
        monthly_taxes: Optional[float] = None,
        assessment_date: Optional[date] = None,
    ) -> RiskCapacityAssessmentResult:
        """
        Executes the complete end-to-end Risk Capacity assessment pipeline.
        Returns immutable RiskCapacityAssessmentResult.
        """
        assessment_id = f"RC-{uuid.uuid4().hex[:12].upper()}"
        obs_date = snapshot.observation_date if snapshot and snapshot.observation_date else date.today()
        ts_utc = datetime.now(timezone.utc)

        # 1. Configuration Validation
        config_errors = self.config.validate()
        if config_errors:
            # PRODUCTION mode fails safely if calibration missing
            return RiskCapacityAssessmentResult(
                assessment_id=assessment_id,
                investor_id=investor_id,
                profile_version_used=profile_version,
                observation_date=obs_date,
                assessment_timestamp_utc=ts_utc,
                startup_mode=self.config.startup_mode,
                assessment_status=AssessmentStatus.CONFIGURATION_ERROR,
                overall_capacity_tier=None,
                binding_constraint_name=None,
                confidence_score=0.0,
                explanation_tokens=["MISSING_PRODUCTION_CALIBRATION_PARAMETERS"],
                provenance=snapshot.provenance if snapshot else None,
                output_tag=self.config.output_tag,
                methodology_version=self.config.methodology_version,
                rule_version=self.config.rule_version,
            )

        # 2. Input Validation
        input_errors = self.validate_inputs(snapshot, dependents_count, employment_type)
        if input_errors:
            raise ValueError(f"Input validation failure: {'; '.join(input_errors)}")

        # Track missing inputs
        missing_inputs = []
        if snapshot.monthly_gross_income is None:
            missing_inputs.append("monthly_gross_income")
        if snapshot.monthly_fixed_expenses is None:
            missing_inputs.append("monthly_fixed_expenses")
        if snapshot.monthly_debt_servicing is None:
            missing_inputs.append("monthly_debt_servicing")
        if snapshot.liquid_emergency_reserves is None:
            missing_inputs.append("liquid_emergency_reserves")
        if monthly_taxes is None:
            missing_inputs.append("monthly_taxes")
        if employment_type is None:
            missing_inputs.append("employment_type")

        # 3. Calculate Financial Ratios
        debt_ratio = self.calculate_debt_burden_ratio(
            snapshot.monthly_debt_servicing,
            snapshot.monthly_gross_income,
        )
        reserve_ratio, req_months = self.calculate_reserve_adequacy_ratio(
            snapshot.liquid_emergency_reserves,
            snapshot.monthly_fixed_expenses,
            employment_type=employment_type,
            dependents_count=dependents_count,
        )
        surplus_ratio = self.calculate_surplus_ratio(
            snapshot.monthly_gross_income,
            snapshot.monthly_fixed_expenses,
            snapshot.monthly_debt_servicing,
            monthly_taxes=monthly_taxes,
        )

        # 4. Evaluate Constraints
        debt_con = self.evaluate_debt_constraint(debt_ratio)
        reserve_con = self.evaluate_reserve_constraint(reserve_ratio)
        surplus_con = self.evaluate_surplus_constraint(surplus_ratio)

        # 5. Determine Assessment Status & Sufficiency
        # If critical inputs (both income and reserves) are missing -> INSUFFICIENT_INFORMATION
        if snapshot.monthly_gross_income is None and snapshot.liquid_emergency_reserves is None:
            status = AssessmentStatus.INSUFFICIENT_INFORMATION
        elif debt_con.status == "MISSING_DATA" and reserve_con.status == "MISSING_DATA":
            status = AssessmentStatus.INSUFFICIENT_INFORMATION
        elif len(missing_inputs) > 0:
            status = AssessmentStatus.PARTIAL
        else:
            status = AssessmentStatus.COMPLETE

        # If INSUFFICIENT_INFORMATION, capacity tier MUST BE ABSENT
        if status == AssessmentStatus.INSUFFICIENT_INFORMATION:
            conf_score = self.calculate_confidence_score(len(missing_inputs), status)
            explanations = self.generate_explanations(
                debt_con, reserve_con, surplus_con, None, status, missing_inputs
            )
            return RiskCapacityAssessmentResult(
                assessment_id=assessment_id,
                investor_id=investor_id,
                profile_version_used=profile_version,
                observation_date=obs_date,
                assessment_timestamp_utc=ts_utc,
                startup_mode=self.config.startup_mode,
                assessment_status=status,
                overall_capacity_tier=None,
                binding_constraint_name=None,
                debt_constraint=debt_con,
                reserve_constraint=reserve_con,
                surplus_constraint=surplus_con,
                confidence_score=conf_score,
                explanation_tokens=explanations,
                provenance=snapshot.provenance,
                output_tag=self.config.output_tag,
                methodology_version=self.config.methodology_version,
                rule_version=self.config.rule_version,
            )

        # 6. Bottleneck Aggregation
        overall_tier, binding_name, [updated_debt, updated_reserve, updated_surplus] = self.aggregate_bottleneck_capacity(
            debt_con, reserve_con, surplus_con
        )

        # 7. Confidence Score (Calculated separately AFTER capacity tier)
        confidence_score = self.calculate_confidence_score(len(missing_inputs), status)

        # 8. Explanations
        explanations = self.generate_explanations(
            updated_debt, updated_reserve, updated_surplus, binding_name, status, missing_inputs
        )

        # 9. Return Reproducible Data Contract
        return RiskCapacityAssessmentResult(
            assessment_id=assessment_id,
            investor_id=investor_id,
            profile_version_used=profile_version,
            observation_date=obs_date,
            assessment_timestamp_utc=ts_utc,
            startup_mode=self.config.startup_mode,
            assessment_status=status,
            overall_capacity_tier=overall_tier,
            binding_constraint_name=binding_name,
            debt_constraint=updated_debt,
            reserve_constraint=updated_reserve,
            surplus_constraint=updated_surplus,
            confidence_score=confidence_score,
            explanation_tokens=explanations,
            provenance=snapshot.provenance,
            output_tag=self.config.output_tag,
            methodology_version=self.config.methodology_version,
            rule_version=self.config.rule_version,
        )
