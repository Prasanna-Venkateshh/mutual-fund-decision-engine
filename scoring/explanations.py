"""
Component Explanation Generator (Phase E).

Generates evidence-grounded, human-readable explanations for dimension scores
and overall Fund Quality Score results.
"""

from typing import Dict, Optional
from scoring.models import DimensionScore


class ScoringExplanationGenerator:
    """Generator for natural language explanations grounded on calculated metric evidence."""

    def generate_dimension_explanation(
        self,
        dimension_name: str,
        raw_value: Optional[float],
        peer_percentile: Optional[float],
        normalized_score: Optional[float],
        weight: float,
        data_available: bool
    ) -> str:
        """Generates explanation text for a single dimension score."""
        if not data_available or normalized_score is None:
            return (
                f"{dimension_name.replace('_', ' ').title()} data was unavailable "
                f"for part of the observation window, reducing dataset completeness."
            )

        formatted_raw = f"{raw_value:.2f}" if raw_value is not None else "N/A"

        if normalized_score >= 75.0:
            rating_text = "significantly outperformed category peers"
        elif normalized_score >= 50.0:
            rating_text = "performed above category median"
        elif normalized_score >= 25.0:
            rating_text = "performed below category median"
        else:
            rating_text = "trailed category peers"

        return (
            f"{dimension_name.replace('_', ' ').title()} {rating_text} "
            f"(raw metric: {formatted_raw}, peer percentile score: {normalized_score:.1f}/100, weight: {weight:.1f}%)."
        )

    def generate_summary_explanation(
        self,
        quality_score: Optional[float],
        confidence_score: float,
        dimension_scores: Dict[str, DimensionScore],
        peer_group_size: int
    ) -> str:
        """Generates overall summary explanation for a Fund Quality Score result."""
        if quality_score is None:
            return (
                f"Fund Quality Score unavailable due to insufficient historical metric evidence. "
                f"Platform confidence is {confidence_score * 100:.0f}%."
            )

        top_drivers = []
        low_drivers = []
        for name, dim in dimension_scores.items():
            if dim.data_available and dim.normalized_score is not None:
                if dim.normalized_score >= 65.0:
                    top_drivers.append(name.replace('_', ' ').title())
                elif dim.normalized_score <= 35.0:
                    low_drivers.append(name.replace('_', ' ').title())

        driver_text = ""
        if top_drivers:
            driver_text += f" Strongest relative performance in {', '.join(top_drivers)}."
        if low_drivers:
            driver_text += f" Relative weakness observed in {', '.join(low_drivers)}."

        conf_text = "High" if confidence_score >= 0.8 else ("Moderate" if confidence_score >= 0.6 else "Low")

        return (
            f"Overall Fund Quality Score of {quality_score:.1f}/100 based on {peer_group_size} category peers."
            f"{driver_text} Platform confidence: {conf_text} ({confidence_score * 100:.0f}%)."
        )
