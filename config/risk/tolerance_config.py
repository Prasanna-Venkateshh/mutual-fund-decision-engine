"""
Risk Tolerance Configuration & Parameter Register (Phase F.3.2).

Defines externalized, versioned configuration contracts for the Risk Tolerance Engine.

Governance Rules Enforced:
- No behavioral parameters may be hardcoded inside engine logic.
- All calibration thresholds remain externalized as configurable stubs.
- Supports three startup modes: PRODUCTION, RESEARCH, TEST.
- PRODUCTION mode refuses startup if any required calibration parameter is missing.
- RESEARCH mode requires explicit provisional parameters and tags outputs.
- TEST mode uses synthetic test parameters and tags outputs.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List

from models.investor_profile import RiskToleranceLevel
from config.risk.capacity_config import StartupMode


@dataclass(frozen=True)
class RiskToleranceConfig:
    """
    Externalized Risk Tolerance Configuration contract.
    Tracks methodology version, rule version, startup mode, and externalized behavioral parameters.
    """
    questionnaire_version: str = "1.0.0"
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"
    startup_mode: StartupMode = StartupMode.PRODUCTION


    # --- Questionnaire Scenario Choice Weight Mappings ---
    loss_reaction_weight_map: Optional[Dict[str, float]] = None
    stagnation_comfort_weight_map: Optional[Dict[str, float]] = None
    drawdown_action_weight_map: Optional[Dict[str, float]] = None
    volatility_preference_weight_map: Optional[Dict[str, float]] = None

    # --- Ordinal Classification Score Boundaries ---
    very_low_upper_threshold: Optional[float] = None   # Score < threshold -> VERY_LOW
    low_upper_threshold: Optional[float] = None        # threshold <= Score < threshold -> LOW
    moderate_upper_threshold: Optional[float] = None   # threshold <= Score < threshold -> MODERATE
    high_upper_threshold: Optional[float] = None       # threshold <= Score < threshold -> HIGH (>= high -> VERY_HIGH)

    # --- Response Consistency Thresholds ---
    consistency_std_dev_threshold_moderate: Optional[float] = None # StdDev >= threshold -> MODERATELY_INCONSISTENT
    consistency_std_dev_threshold_material: Optional[float] = None # StdDev >= threshold -> MATERIALLY_INCONSISTENT

    # --- Confidence Parameters ---
    confidence_penalty_per_missing_response: Optional[float] = None
    confidence_penalty_inconsistent_responses: Optional[float] = None
    partial_assessment_confidence_cap: Optional[float] = None
    insufficient_info_confidence_cap: Optional[float] = None
    min_required_responses_count: int = 2

    # --- Explanation Token Thresholds ---
    explanation_strong_threshold: float = 0.75
    explanation_low_threshold: float = 0.25


    def validate(self) -> List[str]:
        """
        Validates configuration completeness and safety for the active startup mode.
        Returns a list of validation error messages. If empty, config is valid.
        """
        errors = []

        if self.startup_mode == StartupMode.PRODUCTION:
            required_fields = [
                ("loss_reaction_weight_map", self.loss_reaction_weight_map),
                ("stagnation_comfort_weight_map", self.stagnation_comfort_weight_map),
                ("drawdown_action_weight_map", self.drawdown_action_weight_map),
                ("volatility_preference_weight_map", self.volatility_preference_weight_map),
                ("very_low_upper_threshold", self.very_low_upper_threshold),
                ("low_upper_threshold", self.low_upper_threshold),
                ("moderate_upper_threshold", self.moderate_upper_threshold),
                ("high_upper_threshold", self.high_upper_threshold),
                ("consistency_std_dev_threshold_moderate", self.consistency_std_dev_threshold_moderate),
                ("consistency_std_dev_threshold_material", self.consistency_std_dev_threshold_material),
                ("confidence_penalty_per_missing_response", self.confidence_penalty_per_missing_response),
                ("confidence_penalty_inconsistent_responses", self.confidence_penalty_inconsistent_responses),
                ("partial_assessment_confidence_cap", self.partial_assessment_confidence_cap),
                ("insufficient_info_confidence_cap", self.insufficient_info_confidence_cap),
            ]
            for field_name, value in required_fields:
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
) -> RiskToleranceConfig:
    """
    Creates a PRODUCTION mode Risk Tolerance configuration.
    Defaults to uncalibrated None for TBD parameters unless explicitly provided.
    """
    return RiskToleranceConfig(
        startup_mode=StartupMode.PRODUCTION,
        **custom_params
    )


def create_research_config(
    **custom_params: Any
) -> RiskToleranceConfig:
    """
    Creates a RESEARCH mode Risk Tolerance configuration.
    Permits provisional parameters, tags outputs with RESEARCH_MODE_NOT_FOR_PRODUCTION.
    """
    return RiskToleranceConfig(
        startup_mode=StartupMode.RESEARCH,
        **custom_params
    )


def create_test_config(
    vl_thresh: float = 0.20,
    l_thresh: float = 0.40,
    m_thresh: float = 0.60,
    h_thresh: float = 0.80,
    std_mod: float = 0.25,
    std_mat: float = 0.40,
    conf_missing: float = 0.20,
    conf_inconsistent: float = 0.20,
    **overrides: Any
) -> RiskToleranceConfig:
    """
    Creates a TEST mode Risk Tolerance configuration using synthetic test thresholds.
    Tags outputs with SYNTHETIC_TEST_DATA.
    """
    loss_map = {
        "SELL_ALL": 0.00,
        "SELL_SOME": 0.30,
        "HOLD": 0.50,
        "BUY_MORE": 1.00,
    }
    stagnation_map = {
        "EXIT": 0.00,
        "SWITCH_DEBT": 0.30,
        "WAIT_PATIENTLY": 0.50,
        "INCREASE_EQUITY": 1.00,
    }
    drawdown_map = {
        "PANIC_SOLD": 0.00,
        "REDUCED_RISK": 0.30,
        "STAYED_INVESTED": 0.50,
        "INVESTED_MORE": 1.00,
    }
    volatility_map = {
        "AVOID_VOLATILITY": 0.00,
        "ACCEPT_LOW_VOLATILITY": 0.30,
        "ACCEPT_MODERATE_VOLATILITY": 0.50,
        "ACCEPT_HIGH_VOLATILITY": 1.00,
    }

    params = {
        "startup_mode": StartupMode.TEST,
        "loss_reaction_weight_map": loss_map,
        "stagnation_comfort_weight_map": stagnation_map,
        "drawdown_action_weight_map": drawdown_map,
        "volatility_preference_weight_map": volatility_map,
        "very_low_upper_threshold": vl_thresh,
        "low_upper_threshold": l_thresh,
        "moderate_upper_threshold": m_thresh,
        "high_upper_threshold": h_thresh,
        "consistency_std_dev_threshold_moderate": std_mod,
        "consistency_std_dev_threshold_material": std_mat,
        "confidence_penalty_per_missing_response": conf_missing,
        "confidence_penalty_inconsistent_responses": conf_inconsistent,
        "partial_assessment_confidence_cap": 0.70,
        "insufficient_info_confidence_cap": 0.20,
        "min_required_responses_count": 2,
    }

    params.update(overrides)
    return RiskToleranceConfig(**params)
