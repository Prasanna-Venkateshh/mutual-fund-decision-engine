"""
Action Domain Package (Phase F.6 / F.6.1 / F.6.2)

Defines investor-facing action states, models, and the Action Decision Engine.

Architecture:
DATA -> METRIC ENGINE -> FUND QUALITY -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION
"""

from action.models import (
    ActionState,
    PositionContext,
    InformationSufficiency,
    ReasonCode,
    ActionEvaluationContext,
    ActionAssessmentResult,
)
from action.engine import assess_action

__all__ = [
    "ActionState",
    "PositionContext",
    "InformationSufficiency",
    "ReasonCode",
    "ActionEvaluationContext",
    "ActionAssessmentResult",
    "assess_action",
]
