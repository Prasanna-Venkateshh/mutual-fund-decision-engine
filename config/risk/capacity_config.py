"""
Risk Capacity Configuration & Parameter Register (Phase F.3.1).

Defines externalized, versioned configuration contracts for the Risk Capacity Engine.

Governance Rules Enforced:
- No financial parameters may be hardcoded inside engine logic.
- All 13 TBD parameters from Phase F.2C remain externalized as configurable stubs.
- Supports three startup modes: PRODUCTION, RESEARCH, TEST.
- PRODUCTION mode refuses startup if any required calibration parameter is missing.
- RESEARCH mode requires explicit provisional parameters and tags outputs.
- TEST mode uses synthetic test parameters and tags outputs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any, List

from models.investor_profile import RiskCapacityLevel


class StartupMode(Enum):
    PRODUCTION = "PRODUCTION"
    RESEARCH = "RESEARCH"
    TEST = "TEST"


@dataclass(frozen=True)
class RiskCapacityConfig:
    """
    Externalized Risk Capacity Configuration contract.
    Tracks methodology version, rule version, startup mode, and all 13 TBD parameters.
    """
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"
    startup_mode: StartupMode = StartupMode.PRODUCTION

    # --- 13 TBD Externalized Calibration Parameters ---
    # Dimension 1: Debt Burden (RC-D1-04 to RC-D1-07)
    debt_low_constraint_threshold: Optional[float] = None
    debt_moderate_constraint_threshold: Optional[float] = None
    debt_high_constraint_threshold: Optional[float] = None
    debt_capacity_ceiling_map: Optional[Dict[str, RiskCapacityLevel]] = None

    # Dimension 2: Reserve Adequacy (RC-D2-02 to RC-D2-06, IS-02)
    reserve_salaried_min_months: Optional[float] = None       # RC-D2-02 (Provisional range: 3-6)
    reserve_self_employed_min_months: Optional[float] = None  # RC-D2-03 (Provisional range: 6-12)
    reserve_variable_income_min_months: Optional[float] = None# RC-D2-04 (TBD)
    reserve_dependent_adjustment_months: Optional[float] = None# RC-D2-05 (TBD)
    reserve_capacity_ceiling_map: Optional[Dict[str, RiskCapacityLevel]] = None # RC-D2-06 (TBD)
    stability_reserve_multiplier_map: Optional[Dict[str, float]] = None # RC-IS-02 (TBD)

    # Dimension 3: Surplus Ratio (RC-D3-03 to RC-D3-05)
    surplus_adequate_threshold: Optional[float] = None
    surplus_limited_threshold: Optional[float] = None
    surplus_thin_threshold: Optional[float] = None
    surplus_capacity_ceiling_map: Optional[Dict[str, RiskCapacityLevel]] = None

    # Confidence Parameters (RC-INT-02, RC-INT-03)
    confidence_penalty_per_missing_input: Optional[float] = None
    partial_assessment_confidence_floor: Optional[float] = None

    def validate(self) -> List[str]:
        """
        Validates configuration completeness and safety for the active startup mode.
        Returns a list of validation error messages. If empty, config is valid.
        """
        errors = []

        if self.startup_mode == StartupMode.PRODUCTION:
            # Check all 13 TBD parameters exist
            tbd_fields = [
                ("debt_low_constraint_threshold", self.debt_low_constraint_threshold),
                ("debt_moderate_constraint_threshold", self.debt_moderate_constraint_threshold),
                ("debt_high_constraint_threshold", self.debt_high_constraint_threshold),
                ("debt_capacity_ceiling_map", self.debt_capacity_ceiling_map),
                ("reserve_salaried_min_months", self.reserve_salaried_min_months),
                ("reserve_self_employed_min_months", self.reserve_self_employed_min_months),
                ("reserve_variable_income_min_months", self.reserve_variable_income_min_months),
                ("reserve_dependent_adjustment_months", self.reserve_dependent_adjustment_months),
                ("reserve_capacity_ceiling_map", self.reserve_capacity_ceiling_map),
                ("surplus_adequate_threshold", self.surplus_adequate_threshold),
                ("surplus_limited_threshold", self.surplus_limited_threshold),
                ("surplus_thin_threshold", self.surplus_thin_threshold),
                ("confidence_penalty_per_missing_input", self.confidence_penalty_per_missing_input),
                ("partial_assessment_confidence_floor", self.partial_assessment_confidence_floor),
            ]
            for field_name, value in tbd_fields:
                if value is None:
                    errors.append(f"PRODUCTION mode error: Parameter '{field_name}' is missing/uncalibrated (TBD).")

        return errors

    @property
    def is_valid_for_production(self) -> bool:
        return len(self.validate()) == 0

    @property
    def output_tag(self) -> Optional[str]:
        if self.startup_mode == StartupMode.RESEARCH:
            return "RESEARCH_MODE_NOT_FOR_PRODUCTION"
        elif self.startup_mode == StartupMode.TEST:
            return "SYNTHETIC_TEST_DATA"
        return None


def create_production_config(
    **custom_params: Any
) -> RiskCapacityConfig:
    """
    Creates a PRODUCTION mode configuration.
    Defaults to uncalibrated None for TBD parameters unless explicitly provided.
    """
    return RiskCapacityConfig(
        startup_mode=StartupMode.PRODUCTION,
        **custom_params
    )


def create_research_config(
    **custom_params: Any
) -> RiskCapacityConfig:
    """
    Creates a RESEARCH mode configuration.
    Permits provisional parameters, tags outputs with RESEARCH_MODE_NOT_FOR_PRODUCTION.
    """
    return RiskCapacityConfig(
        startup_mode=StartupMode.RESEARCH,
        **custom_params
    )


def create_test_config(
    debt_low: float = 0.30,
    debt_mod: float = 0.45,
    debt_high: float = 0.60,
    reserve_salaried_months: float = 3.0,
    reserve_self_employed_months: float = 6.0,
    reserve_variable_months: float = 6.0,
    reserve_dependent_adj: float = 1.0,
    surplus_adequate: float = 0.20,
    surplus_limited: float = 0.10,
    surplus_thin: float = 0.0,
    conf_penalty: float = 0.15,
    conf_floor: float = 0.50,
    **overrides: Any
) -> RiskCapacityConfig:
    """
    Creates a TEST mode configuration using explicit synthetic test thresholds.
    Tags outputs with SYNTHETIC_TEST_DATA.
    """
    debt_map = {
        "LOW": RiskCapacityLevel.VERY_HIGH,
        "MODERATE": RiskCapacityLevel.MODERATE,
        "HIGH": RiskCapacityLevel.LOW,
        "CRITICAL": RiskCapacityLevel.VERY_LOW,
    }
    reserve_map = {
        "OPTIMAL": RiskCapacityLevel.VERY_HIGH,
        "ADEQUATE": RiskCapacityLevel.HIGH,
        "LIMITED": RiskCapacityLevel.MODERATE,
        "DEFICIENT": RiskCapacityLevel.VERY_LOW,
    }
    surplus_map = {
        "ADEQUATE": RiskCapacityLevel.VERY_HIGH,
        "LIMITED": RiskCapacityLevel.MODERATE,
        "THIN": RiskCapacityLevel.LOW,
        "NEGATIVE": RiskCapacityLevel.VERY_LOW,
    }
    stability_map = {
        "STABLE_SALARIED": 0.0,
        "VARIABLE": 1.0,
        "SELF_EMPLOYED": 2.0,
        "IRREGULAR": 3.0,
        "UNKNOWN": 2.0,
    }

    params = {
        "startup_mode": StartupMode.TEST,
        "debt_low_constraint_threshold": debt_low,
        "debt_moderate_constraint_threshold": debt_mod,
        "debt_high_constraint_threshold": debt_high,
        "debt_capacity_ceiling_map": debt_map,
        "reserve_salaried_min_months": reserve_salaried_months,
        "reserve_self_employed_min_months": reserve_self_employed_months,
        "reserve_variable_income_min_months": reserve_variable_months,
        "reserve_dependent_adjustment_months": reserve_dependent_adj,
        "reserve_capacity_ceiling_map": reserve_map,
        "stability_reserve_multiplier_map": stability_map,
        "surplus_adequate_threshold": surplus_adequate,
        "surplus_limited_threshold": surplus_limited,
        "surplus_thin_threshold": surplus_thin,
        "surplus_capacity_ceiling_map": surplus_map,
        "confidence_penalty_per_missing_input": conf_penalty,
        "partial_assessment_confidence_floor": conf_floor,
    }
    params.update(overrides)
    return RiskCapacityConfig(**params)
