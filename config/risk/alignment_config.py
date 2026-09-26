"""
Risk Alignment Configuration & Parameter Register (Phase F.3.3 Specification).

Defines externalized, versioned configuration contracts for the Risk Alignment Engine.

Governance Rules Enforced:
- No alignment parameters may be hardcoded inside engine logic.
- Externalizes provisional parameters: partial_alignment_confidence_cap, max_assessment_age_gap_days, stale_input_confidence_penalty.
- Supports three startup modes: PRODUCTION, RESEARCH, TEST.
- PRODUCTION mode refuses startup if any required calibration parameter is missing.
- RESEARCH mode requires explicit provisional parameters and tags outputs.
- TEST mode uses synthetic test parameters and tags outputs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, List

from config.risk.capacity_config import StartupMode


@dataclass(frozen=True)
class RiskAlignmentConfig:
    """
    Externalized Risk Alignment Configuration contract.
    Tracks methodology version, rule version, startup mode, and externalized calibration parameters.
    """
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"
    startup_mode: StartupMode = StartupMode.PRODUCTION

    # --- Provisional Externalized Calibration Parameters ---
    partial_alignment_confidence_cap: Optional[float] = None
    max_assessment_age_gap_days: Optional[int] = None
    stale_input_confidence_penalty: Optional[float] = None

    def validate(self) -> List[str]:
        """
        Validates configuration completeness and safety for the active startup mode.
        Returns a list of validation error messages. If empty, config is valid.
        """
        errors = []

        if self.startup_mode == StartupMode.PRODUCTION:
            provisional_fields = [
                ("partial_alignment_confidence_cap", self.partial_alignment_confidence_cap),
                ("max_assessment_age_gap_days", self.max_assessment_age_gap_days),
                ("stale_input_confidence_penalty", self.stale_input_confidence_penalty),
            ]
            for field_name, value in provisional_fields:
                if value is None:
                    errors.append(f"PRODUCTION mode error: Parameter '{field_name}' is missing/uncalibrated.")

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
) -> RiskAlignmentConfig:
    """
    Creates a PRODUCTION mode configuration.
    Defaults to uncalibrated None for provisional parameters unless explicitly provided.
    """
    return RiskAlignmentConfig(
        startup_mode=StartupMode.PRODUCTION,
        **custom_params
    )


def create_research_config(
    partial_cap: float = 0.70,
    max_age_gap: int = 90,
    stale_penalty: float = 0.85,
    **custom_params: Any
) -> RiskAlignmentConfig:
    """
    Creates a RESEARCH mode configuration.
    Permits provisional parameters, tags outputs with RESEARCH_MODE_NOT_FOR_PRODUCTION.
    """
    params = {
        "startup_mode": StartupMode.RESEARCH,
        "partial_alignment_confidence_cap": partial_cap,
        "max_assessment_age_gap_days": max_age_gap,
        "stale_input_confidence_penalty": stale_penalty,
    }
    params.update(custom_params)
    return RiskAlignmentConfig(**params)


def create_test_config(
    partial_cap: float = 0.70,
    max_age_gap: int = 90,
    stale_penalty: float = 0.85,
    **overrides: Any
) -> RiskAlignmentConfig:
    """
    Creates a TEST mode configuration using explicit synthetic test thresholds.
    Tags outputs with SYNTHETIC_TEST_DATA.
    """
    params = {
        "startup_mode": StartupMode.TEST,
        "partial_alignment_confidence_cap": partial_cap,
        "max_assessment_age_gap_days": max_age_gap,
        "stale_input_confidence_penalty": stale_penalty,
    }
    params.update(overrides)
    return RiskAlignmentConfig(**params)
