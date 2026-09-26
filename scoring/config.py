"""
Fund Quality Scoring Configuration (Phase E).

Defines externalized, versioned V1 scoring configuration, category-family
weight profiles, dynamic downside importance bounds, and normalization constants.

Governance Status: PROVISIONAL — REQUIRES VALIDATION.
"""

from typing import Dict, Any

SCORING_METHODOLOGY_VERSION = "1.0.0"
WEIGHT_CONFIG_VERSION = "1.0.0"
NORMALIZATION_METHOD_VERSION = "1.0.0"

SCORE_MIN = 0.0
SCORE_MAX = 100.0
MIN_PEER_COUNT_PREFERRED = 5  # Below 5 peers, confidence is reduced

# Provisional V1 Category-Family Fixed Weights (Must sum to 100.0)
CATEGORY_FAMILY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "Equity": {
        "return": 25.0,
        "consistency": 20.0,
        "volatility": 15.0,
        "downside_risk": 15.0,
        "max_drawdown": 15.0,
        "cost_efficiency": 10.0
    },
    "Debt": {
        "return": 15.0,
        "consistency": 20.0,
        "volatility": 25.0,
        "downside_risk": 20.0,
        "max_drawdown": 10.0,
        "cost_efficiency": 10.0
    },
    "Hybrid": {
        "return": 20.0,
        "consistency": 20.0,
        "volatility": 20.0,
        "downside_risk": 15.0,
        "max_drawdown": 15.0,
        "cost_efficiency": 10.0
    },
    "Other": {
        "return": 20.0,
        "consistency": 20.0,
        "volatility": 20.0,
        "downside_risk": 15.0,
        "max_drawdown": 15.0,
        "cost_efficiency": 10.0
    }
}

# Dynamic Downside Importance Bounds (Objective category context only)
DYNAMIC_DOWNSIDE_BOUNDS = {
    "min_multiplier": 0.80,
    "max_multiplier": 1.20,
    "high_volatility_multiplier": 1.15  # Applicable for Small Cap / Sectoral subcategories
}
