"""
Presentation Adapters (Phase 2 — Governed Correction Pass)
Translates backend domain contracts into UI-safe presentation structures
WITHOUT duplicating financial logic or inventing rules.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timezone

from integration.models import (
    EndToEndDecisionResult,
    FundQualityIntegrationContract,
    SuitabilityIntegrationContract,
    PortfolioNeedIntegrationContract,
    EconomicBenefitIntegrationContract,
    EconomicBenefitState,
    IntegrationStatus,
    ActionState,
)
from models.investor_profile import (
    InvestorProfileSnapshot,
    FinancialCapacitySnapshot,
    BehavioralToleranceSnapshot,
    RiskCapacityLevel,
    RiskToleranceLevel,
    ProfileStatus,
)


class QuestionnaireAdapter:
    """
    Translates raw 10-question UI onboarding responses into governed InvestorProfileSnapshot.
    
    Rules:
    - Exactly 10 core onboarding questions.
    - Risk capacity and risk tolerance remain strictly separate.
    - No frontend hidden risk scoring.
    - Optional/skip responses preserve backend insufficient-information behavior.
    """

    @staticmethod
    def responses_to_profile_snapshot(
        user_id: str,
        responses: Dict[int, Any],
        profile_id: Optional[str] = None
    ) -> InvestorProfileSnapshot:
        """
        Maps user answers (question_id 1..10) to InvestorProfileSnapshot fields.
        """
        today = date.today()
        now = datetime.now(timezone.utc)

        # Financial Capacity Inputs
        emergency_months = responses.get(2)
        if emergency_months is not None:
            try:
                emergency_months = float(emergency_months)
            except (ValueError, TypeError):
                emergency_months = None

        fin_capacity = FinancialCapacitySnapshot(
            observation_date=today,
            effective_date=today,
            emergency_reserve_months=emergency_months,
        )

        # Behavioral Tolerance Inputs
        loss_reaction = responses.get(5)
        if loss_reaction is not None:
            loss_reaction = str(loss_reaction)

        beh_tolerance = BehavioralToleranceSnapshot(
            observation_date=today,
            assessment_date=today,
            loss_reaction_choice=loss_reaction,
        )

        snapshot_id = profile_id or f"prof_{user_id}_{int(now.timestamp())}"
        version = responses.get("profile_version", "1.0.0")

        return InvestorProfileSnapshot(
            profile_id=snapshot_id,
            investor_id=user_id,
            profile_version=version,
            effective_date=today,
            financial_capacity=fin_capacity,
            behavioral_tolerance=beh_tolerance,
            created_timestamp_utc=now,
        )

    @staticmethod
    def profile_snapshot_to_responses(profile: InvestorProfileSnapshot) -> Dict[int, Any]:
        """
        Extracts raw question responses (question_id 1..10) from an InvestorProfileSnapshot.
        """
        responses: Dict[int, Any] = {}
        if profile.financial_capacity:
            if profile.financial_capacity.emergency_reserve_months is not None:
                responses[2] = profile.financial_capacity.emergency_reserve_months
        if profile.behavioral_tolerance:
            if profile.behavioral_tolerance.loss_reaction_choice is not None:
                responses[5] = profile.behavioral_tolerance.loss_reaction_choice
        return responses

    @staticmethod
    def increment_version(version_str: str) -> str:
        """Helper to increment patch version string (e.g. 1.0.0 -> 1.0.1)."""
        try:
            parts = version_str.split(".")
            if len(parts) == 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                return f"{major}.{minor}.{patch + 1}"
        except Exception:
            pass
        return "1.0.1"



@dataclass(frozen=True)
class RawFieldDiff:
    field_name: str
    previous_value: Any
    current_value: Any
    display_label: str


class SnapshotDiffAdapter:
    """
    Compares versioned assessment/audit records and returns neutral before/after diffs.
    
    Rules:
    - Raw field comparison (previous_value -> current_value).
    - Neutral wording: "Changed" or "Previous value -> Current value".
    - Does NOT claim every numerical delta is a "material change" unless governed rule exists.
    """

    @staticmethod
    def compare_snapshots(
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> List[RawFieldDiff]:
        diffs: List[RawFieldDiff] = []
        all_keys = sorted(set(list(previous.keys()) + list(current.keys())))
        
        for k in all_keys:
            prev_val = previous.get(k)
            curr_val = current.get(k)
            if prev_val != curr_val:
                label = k.replace("_", " ").title()
                diffs.append(RawFieldDiff(
                    field_name=k,
                    previous_value=prev_val,
                    current_value=curr_val,
                    display_label=label,
                ))
        return diffs


class ConfidenceLabelAdapter:
    """
    Presents continuous float confidence_score (0.0 - 1.0) numerically.
    
    Governance Correction:
    - HARD-CODED QUALITATIVE THRESHOLDS (>=0.85 -> Strong, >=0.60 -> Moderate, <0.60 -> Limited) ARE PROHIBITED AND REMOVED.
    - Continuous numerical presentation is primary.
    - Never calls confidence "probability".
    """

    @staticmethod
    def format_confidence(confidence_score: Optional[float]) -> Dict[str, Any]:
        if confidence_score is None:
            return {
                "numeric_score": None,
                "display_text": "Data Not Available",
                "label": "Evidence Strength: Data Not Available",
                "is_available": False,
            }
        
        score_pct = round(confidence_score * 100, 1)
        
        return {
            "numeric_score": confidence_score,
            "percentage_text": f"{score_pct}%",
            "display_text": f"Evidence Strength Score: {confidence_score:.2f}",
            "label": f"Evidence Strength: {confidence_score:.2f}",
            "is_available": True,
        }
