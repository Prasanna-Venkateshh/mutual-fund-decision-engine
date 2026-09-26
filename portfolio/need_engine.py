"""
Portfolio Need Engine Implementation (Phase F.4.4).

Executes governed Portfolio Need & Candidate Fulfillment decision logic strictly according to:
- docs/phase_f4_portfolio_need_specification.md
- docs/phase_f4_3_portfolio_need_decision_logic_specification.md
- docs/phase_f4_3_1_portfolio_need_governance_correction.md
- docs/phase_f4_3_2_candidate_fulfillment_semantic_governance_correction.md

Architecture:
DATA -> METRIC ENGINE -> FUND QUALITY -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION

Core Responsibilities:
- Receives GoalFundingSnapshot, PortfolioExposureSnapshot, AllocationContext, AffordabilityContext, FundCandidateContext, etc.
- Determines primary state: NEED_IDENTIFIED, NO_MATERIAL_NEED, EXCESS_EXPOSURE, INSUFFICIENT_INFORMATION, INVALID_ASSESSMENT.
- Determines canonical candidate fulfillment status: CANDIDATE_CAN_FULFILL_NEED, CANDIDATE_CANNOT_FULFILL_NEED, CANDIDATE_FULFILLMENT_UNKNOWN.
- Emits contextual flags without conflating them with primary state.
- Zero Action creation (BUY, SELL, REBALANCE, SWITCH). Zero upstream metric recalculation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from portfolio.need_models import (
    GoalFundingSnapshot,
    PortfolioExposureSnapshot,
    AllocationContext,
    ExposureGap,
    FundingGap,
    AffordabilityContext,
    PortfolioLookThroughContext,
    FundCandidateContext,
    MultiGoalContext,
    GeneralWealthContext,
    PortfolioNeedAssessmentResult,
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
    ExposureGapDirection,
    FundingStatus,
)
from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus


class PortfolioNeedEngine:
    """
    Production Portfolio Need Engine executing governed F.4 decision rules.
    """

    METHODOLOGY_VERSION = "F.4.4-PROVISIONAL"
    RULE_VERSION = "1.0.0"

    def evaluate_need(
        self,
        investor_id: str,
        goal_snapshot: Optional[GoalFundingSnapshot] = None,
        portfolio_snapshot: Optional[PortfolioExposureSnapshot] = None,
        allocation_context: Optional[AllocationContext] = None,
        affordability_context: Optional[AffordabilityContext] = None,
        look_through_context: Optional[PortfolioLookThroughContext] = None,
        candidate_context: Optional[FundCandidateContext] = None,
        multi_goal_context: Optional[MultiGoalContext] = None,
        general_wealth_context: Optional[GeneralWealthContext] = None,
        assessment_id: Optional[str] = None,
    ) -> PortfolioNeedAssessmentResult:
        """
        Main entry point for Portfolio Need evaluation.
        """
        now = datetime.now(timezone.utc)
        eval_id = assessment_id or f"pnd_{investor_id}_{int(now.timestamp())}"

        # Tracking variables
        triggered_rule_ids: List[str] = []
        contextual_flags: List[str] = []
        explanations: List[str] = []
        upstream_assessment_ids: Dict[str, str] = {}

        # Capture upstream assessment references
        if candidate_context:
            if candidate_context.suitability_assessment_id:
                upstream_assessment_ids["suitability"] = candidate_context.suitability_assessment_id
            if candidate_context.fund_quality_assessment_id:
                upstream_assessment_ids["fund_quality"] = candidate_context.fund_quality_assessment_id
            if candidate_context.risk_alignment_assessment_id:
                upstream_assessment_ids["risk_alignment"] = candidate_context.risk_alignment_assessment_id

        if affordability_context and affordability_context.upstream_assessment_id:
            upstream_assessment_ids["affordability"] = affordability_context.upstream_assessment_id

        # STEP 1: VALIDITY GATE
        is_valid, invalid_reason = self._validate_inputs(
            investor_id=investor_id,
            goal_snapshot=goal_snapshot,
            portfolio_snapshot=portfolio_snapshot,
            allocation_context=allocation_context,
            affordability_context=affordability_context,
            candidate_context=candidate_context,
        )
        if not is_valid:
            triggered_rule_ids.append("RN-INV-1")
            explanations.append(f"Assessment invalid: {invalid_reason}")
            return PortfolioNeedAssessmentResult(
                assessment_id=eval_id,
                investor_id=investor_id,
                goal_id=goal_snapshot.goal_id if goal_snapshot else None,
                scheme_id=candidate_context.canonical_scheme_id if candidate_context else None,
                primary_state=PortfolioNeedState.INVALID_ASSESSMENT,
                candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN,
                affordability_status=AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN,
                contextual_flags=contextual_flags,
                confidence_score=0.0,
                triggered_rule_ids=triggered_rule_ids,
                explanation=" ".join(explanations),
                upstream_assessment_ids=upstream_assessment_ids,
                observation_timestamp=now,
                methodology_version=self.METHODOLOGY_VERSION,
                rule_version=self.RULE_VERSION,
            )

        # STEP 2: MANDATORY INFORMATION SUFFICIENCY GATE
        is_sufficient, insufficiency_reason = self._check_information_sufficiency(
            goal_snapshot=goal_snapshot,
            portfolio_snapshot=portfolio_snapshot,
            allocation_context=allocation_context,
            candidate_context=candidate_context,
            general_wealth_context=general_wealth_context,
        )
        if not is_sufficient:
            triggered_rule_ids.append("RN-INF-1")
            explanations.append(f"Insufficient information for assessment: {insufficiency_reason}")
            return PortfolioNeedAssessmentResult(
                assessment_id=eval_id,
                investor_id=investor_id,
                goal_id=goal_snapshot.goal_id if goal_snapshot else None,
                scheme_id=candidate_context.canonical_scheme_id if candidate_context else None,
                primary_state=PortfolioNeedState.INSUFFICIENT_INFORMATION,
                candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN,
                affordability_status=affordability_context.affordability_status if affordability_context else AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN,
                contextual_flags=contextual_flags,
                confidence_score=0.0,
                triggered_rule_ids=triggered_rule_ids,
                explanation=" ".join(explanations),
                upstream_assessment_ids=upstream_assessment_ids,
                observation_timestamp=now,
                methodology_version=self.METHODOLOGY_VERSION,
                rule_version=self.RULE_VERSION,
            )

        # STEP 3: EXPOSURE RELATIONSHIP DETERMINATION (Primary Need State)
        primary_state, exposure_gap, funding_gap = self._determine_primary_need_state(
            goal_snapshot=goal_snapshot,
            allocation_context=allocation_context,
            general_wealth_context=general_wealth_context,
            triggered_rule_ids=triggered_rule_ids,
            contextual_flags=contextual_flags,
            explanations=explanations,
        )

        # STEP 4: CANDIDATE FULFILLMENT DETERMINATION
        fulfillment_status = self._determine_candidate_fulfillment(
            candidate_context=candidate_context,
            primary_state=primary_state,
            triggered_rule_ids=triggered_rule_ids,
            contextual_flags=contextual_flags,
            explanations=explanations,
        )

        # STEP 5: AFFORDABILITY & CONTEXTUAL MODIFIERS
        afford_status = self._process_affordability_and_modifiers(
            affordability_context=affordability_context,
            look_through_context=look_through_context,
            triggered_rule_ids=triggered_rule_ids,
            contextual_flags=contextual_flags,
            explanations=explanations,
        )

        # STEP 6: CONFIDENCE CALCULATION
        confidence = self._calculate_confidence(
            goal_snapshot=goal_snapshot,
            portfolio_snapshot=portfolio_snapshot,
            allocation_context=allocation_context,
            look_through_context=look_through_context,
            candidate_context=candidate_context,
        )

        # Append non-recommendation disclaimers
        explanations.append("This assessment identifies portfolio/goal exposure need only and does not constitute a transaction recommendation (Buy/Sell/Switch).")

        return PortfolioNeedAssessmentResult(
            assessment_id=eval_id,
            investor_id=investor_id,
            goal_id=goal_snapshot.goal_id if goal_snapshot else None,
            scheme_id=candidate_context.canonical_scheme_id if candidate_context else None,
            primary_state=primary_state,
            candidate_fulfillment_status=fulfillment_status,
            affordability_status=afford_status,
            contextual_flags=contextual_flags,
            funding_status=goal_snapshot.funding_status if goal_snapshot else FundingStatus.UNKNOWN_FUNDING,
            allocation_status=allocation_context.exposure_gap.gap_direction if (allocation_context and allocation_context.exposure_gap) else ExposureGapDirection.UNKNOWN_ALLOCATION,
            exposure_gap=exposure_gap,
            funding_gap=funding_gap,
            confidence_score=confidence,
            triggered_rule_ids=triggered_rule_ids,
            explanation=" ".join(explanations),
            upstream_assessment_ids=upstream_assessment_ids,
            observation_timestamp=now,
            methodology_version=self.METHODOLOGY_VERSION,
            rule_version=self.RULE_VERSION,
        )

    def _validate_inputs(
        self,
        investor_id: str,
        goal_snapshot: Optional[GoalFundingSnapshot],
        portfolio_snapshot: Optional[PortfolioExposureSnapshot],
        allocation_context: Optional[AllocationContext],
        affordability_context: Optional[AffordabilityContext],
        candidate_context: Optional[FundCandidateContext],
    ) -> Tuple[bool, Optional[str]]:
        if not investor_id or not isinstance(investor_id, str):
            return False, "Investor ID must be a non-empty string."

        if goal_snapshot and goal_snapshot.investor_id != investor_id:
            return False, "Goal snapshot investor ID mismatch."

        if portfolio_snapshot and portfolio_snapshot.investor_id != investor_id:
            return False, "Portfolio snapshot investor ID mismatch."

        if candidate_context and not candidate_context.canonical_scheme_id:
            return False, "Candidate context missing canonical scheme ID."

        return True, None

    def _check_information_sufficiency(
        self,
        goal_snapshot: Optional[GoalFundingSnapshot],
        portfolio_snapshot: Optional[PortfolioExposureSnapshot],
        allocation_context: Optional[AllocationContext],
        candidate_context: Optional[FundCandidateContext],
        general_wealth_context: Optional[GeneralWealthContext],
    ) -> Tuple[bool, Optional[str]]:
        # Must have either goal context or general wealth context
        if not goal_snapshot and not general_wealth_context:
            return False, "Neither GoalFundingSnapshot nor GeneralWealthContext provided."

        # Must have allocation context or portfolio exposure information
        if not allocation_context and not portfolio_snapshot:
            return False, "Neither AllocationContext nor PortfolioExposureSnapshot provided."

        return True, None

    def _determine_primary_need_state(
        self,
        goal_snapshot: Optional[GoalFundingSnapshot],
        allocation_context: Optional[AllocationContext],
        general_wealth_context: Optional[GeneralWealthContext],
        triggered_rule_ids: List[str],
        contextual_flags: List[str],
        explanations: List[str],
    ) -> Tuple[PortfolioNeedState, Optional[ExposureGap], Optional[FundingGap]]:
        exposure_gap: Optional[ExposureGap] = None
        funding_gap: Optional[FundingGap] = None

        if allocation_context and allocation_context.exposure_gap:
            exposure_gap = allocation_context.exposure_gap

        if goal_snapshot and goal_snapshot.target_amount is not None and goal_snapshot.current_corpus is not None:
            gap_val = max(0.0, goal_snapshot.target_amount - goal_snapshot.current_corpus)
            funding_gap = FundingGap(
                target_amount=goal_snapshot.target_amount,
                current_corpus=goal_snapshot.current_corpus,
                funding_gap_amount=gap_val,
                funding_status=goal_snapshot.funding_status,
                observation_date=goal_snapshot.observation_date,
            )
            if gap_val > 0.0:
                contextual_flags.append("FUNDING_GAP_PRESENT")

        # Evaluate exposure gap direction
        if exposure_gap:
            if exposure_gap.gap_direction == ExposureGapDirection.NEGATIVE_GAP:
                triggered_rule_ids.append("RN-HARD-EXCESS")
                explanations.append("Portfolio has an explicit negative allocation gap (exposure surplus) [platform-calculated].")
                return PortfolioNeedState.EXCESS_EXPOSURE, exposure_gap, funding_gap

            elif exposure_gap.gap_direction == ExposureGapDirection.POSITIVE_GAP:
                triggered_rule_ids.append("RN-POS-1")
                contextual_flags.append("ALLOCATION_GAP_PRESENT")
                explanations.append("Portfolio has a positive allocation gap indicating incremental exposure requirement [platform-calculated].")
                return PortfolioNeedState.NEED_IDENTIFIED, exposure_gap, funding_gap

            elif exposure_gap.gap_direction == ExposureGapDirection.BALANCED_EXPOSURE:
                triggered_rule_ids.append("RN-POS-BALANCED")
                explanations.append("Portfolio exposure is balanced with reference allocation [platform-calculated].")
                return PortfolioNeedState.NO_MATERIAL_NEED, exposure_gap, funding_gap

        # Fallback if exposure gap direction is UNKNOWN or missing
        if goal_snapshot and goal_snapshot.funding_status == FundingStatus.UNDERFUNDED:
            triggered_rule_ids.append("RN-POS-UNDERFUNDED")
            explanations.append("Underfunded goal context indicates potential portfolio need.")
            return PortfolioNeedState.NEED_IDENTIFIED, exposure_gap, funding_gap

        triggered_rule_ids.append("RN-INF-NO-GAP")
        explanations.append("Allocation status is unknown or balanced; no material need identified.")
        return PortfolioNeedState.NO_MATERIAL_NEED, exposure_gap, funding_gap

    def _determine_candidate_fulfillment(
        self,
        candidate_context: Optional[FundCandidateContext],
        primary_state: PortfolioNeedState,
        triggered_rule_ids: List[str],
        contextual_flags: List[str],
        explanations: List[str],
    ) -> CandidateFulfillmentStatus:
        if not candidate_context:
            return CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN

        # 1. Check Suitability
        if candidate_context.suitability_result:
            s_status = candidate_context.suitability_result.suitability_status
            if s_status == SuitabilityStatus.NOT_SUITABLE:
                triggered_rule_ids.append("RN-COND-UNSUITABLE")
                contextual_flags.append("CANDIDATE_UNSUITABLE")
                explanations.append("Candidate fund is unsuitable for the investor context.")
                return CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED
            elif s_status == SuitabilityStatus.INSUFFICIENT_INFORMATION:
                contextual_flags.append("CANDIDATE_SUITABILITY_UNKNOWN")
                return CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN

        # 2. Check Candidate Fulfillment Capability (Asset Class / Category Capability)
        if candidate_context.is_capable_of_fulfilling_need is False:
            triggered_rule_ids.append("RN-COND-INCAPABLE")
            contextual_flags.append("CANDIDATE_NOT_CAPABLE_OF_FULFILLING_NEED")
            explanations.append("Candidate fund asset class or category cannot satisfy the required portfolio exposure.")
            return CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED
        elif candidate_context.is_capable_of_fulfilling_need is None:
            contextual_flags.append("CANDIDATE_CAPABILITY_UNKNOWN")
            return CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN

        # 3. Compatible
        if primary_state == PortfolioNeedState.NEED_IDENTIFIED:
            triggered_rule_ids.append("RN-POS-FULFILL")
            explanations.append("Candidate fund is suitable and capable of satisfying the identified exposure requirement.")
            return CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED

        return CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED

    def _process_affordability_and_modifiers(
        self,
        affordability_context: Optional[AffordabilityContext],
        look_through_context: Optional[PortfolioLookThroughContext],
        triggered_rule_ids: List[str],
        contextual_flags: List[str],
        explanations: List[str],
    ) -> AffordabilityStatus:
        afford_status = AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN

        if affordability_context:
            afford_status = affordability_context.affordability_status
            if afford_status == AffordabilityStatus.AFFORDABILITY_CONSTRAINED:
                triggered_rule_ids.append("RN-COND-AFFORD")
                contextual_flags.append("AFFORDABILITY_CONSTRAINED")
                explanations.append("Investor contribution capacity is constrained relative to required allocation.")
            elif afford_status == AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN:
                contextual_flags.append("AFFORDABILITY_STATUS_UNKNOWN")
        else:
            contextual_flags.append("AFFORDABILITY_STATUS_UNKNOWN")

        if look_through_context:
            if look_through_context.is_category_overexposed:
                triggered_rule_ids.append("RN-COND-CONC")
                contextual_flags.append("CATEGORY_OVEREXPOSED")
                explanations.append("Portfolio has material category concentration risk.")

            if look_through_context.has_high_security_overlap:
                triggered_rule_ids.append("RN-COND-OVERLAP")
                contextual_flags.append("SECURITY_OVERLAP_CONCERN")
                explanations.append("Portfolio has high security overlap with candidate holdings.")

        return afford_status

    def _calculate_confidence(
        self,
        goal_snapshot: Optional[GoalFundingSnapshot],
        portfolio_snapshot: Optional[PortfolioExposureSnapshot],
        allocation_context: Optional[AllocationContext],
        look_through_context: Optional[PortfolioLookThroughContext],
        candidate_context: Optional[FundCandidateContext],
    ) -> float:
        confidence = 1.0

        if not goal_snapshot or goal_snapshot.funding_status == FundingStatus.UNKNOWN_FUNDING:
            confidence -= 0.15

        if not allocation_context or not allocation_context.exposure_gap or allocation_context.exposure_gap.gap_direction == ExposureGapDirection.UNKNOWN_ALLOCATION:
            confidence -= 0.15

        if look_through_context and look_through_context.look_through_confidence < 1.0:
            confidence -= (1.0 - look_through_context.look_through_confidence) * 0.2

        if candidate_context and candidate_context.suitability_result:
            confidence = min(confidence, candidate_context.suitability_result.suitability_confidence_score)

        return max(0.0, min(1.0, round(confidence, 2)))
