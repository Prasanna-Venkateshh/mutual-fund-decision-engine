"""
Fund Quality Scoring Package (Phase E).
"""

from scoring.config import (
    SCORING_METHODOLOGY_VERSION,
    WEIGHT_CONFIG_VERSION,
    SCORE_MIN,
    SCORE_MAX
)
from scoring.models import DimensionScore, FundQualityScoreResult
from scoring.normalization import PeerGroupNormalizer
from scoring.weights import ScoringWeightManager
from scoring.explanations import ScoringExplanationGenerator
from scoring.engine import FundQualityScoringEngine

__all__ = [
    "SCORING_METHODOLOGY_VERSION",
    "WEIGHT_CONFIG_VERSION",
    "SCORE_MIN",
    "SCORE_MAX",
    "DimensionScore",
    "FundQualityScoreResult",
    "PeerGroupNormalizer",
    "ScoringWeightManager",
    "ScoringExplanationGenerator",
    "FundQualityScoringEngine",
]
