"""
Action Decision Engine Implementation (Phase F.6.2)

Implements the decision orchestration pipeline for evaluating investor actions (BUY, ACCUMULATE, HOLD, MONITOR, REVIEW, SELL).

Architecture:
DATA -> METRIC ENGINE -> FUND QUALITY -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION

Governance Rules Enforced:
- Low-turnover principle: DEFAULT ACTION = HOLD / DO NOTHING UNLESS EVIDENCE JUSTIFIES CHANGE.
- 7-Tier Precedence Hierarchy: INVALID > INSUFFICIENT > NOT_SUITABLE > REVIEW_SIGNAL > ECONOMIC_ACTIONABILITY > POSITIVE_OPPORTUNITY > HOLD.
- High Fund Quality alone NEVER creates BUY or SELL.
- Historical returns / rank alone NEVER creates BUY or SELL.
- Action consumes Tax/Cost assessment; Action does NOT calculate statutory tax, exit loads, or transaction fees.
- Missing tax/cost metadata prevents SELL/SWITCH recommendations.
- Zero transaction execution; read-only recommendation layer.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from action.models import (
    ActionState,
    PositionContext,
    InformationSufficiency,
    ReasonCode,
    ActionEvaluationContext,
    ActionAssessmentResult,
)
from models.suitability_assessment import SuitabilityStatus
from portfolio.need_models import (
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
)


def assess_action(context: ActionEvaluationContext) -> ActionAssessmentResult:
    """
    Evaluates investor action for a given candidate or existing scheme position context.
    """
    now_utc = context.observation_timestamp or datetime.now(timezone.utc)
    assessment_id = f"act_{uuid.uuid4().hex[:12]}"

    # Map upstream assessment IDs
    upstream_ids: Dict[str, str] = {}
    if context.fund_quality_assessment_id:
        upstream_ids["fund_quality_assessment_id"] = context.fund_quality_assessment_id
    if context.suitability_result and context.suitability_result.assessment_id:
        upstream_ids["suitability_assessment_id"] = context.suitability_result.assessment_id
    if context.portfolio_need_result and context.portfolio_need_result.assessment_id:
        upstream_ids["portfolio_need_assessment_id"] = context.portfolio_need_result.assessment_id

    # -------------------------------------------------------------------------
    # STAGE 1: VALIDITY & STRUCTURAL SOUNDNESS CHECK (Tier 1 - INVALID / UNSAFE)
    # -------------------------------------------------------------------------
    if not context or not context.investor_id or not context.scheme_id or not context.position_context:
        return ActionAssessmentResult(
            assessment_id=assessment_id,
            investor_id=context.investor_id if context else "",
            scheme_id=context.scheme_id if context else "",
            position_context=context.position_context if context and context.position_context else PositionContext.NEW_POSITION,
            action_state=ActionState.INVALID_ASSESSMENT,
            information_sufficiency=InformationSufficiency.INSUFFICIENT,
            actionability_status="UNACTIONABLE",
            action_confidence=0.0,
            primary_reason_code=ReasonCode.INVALID_INPUT.value,
            reason_codes=[ReasonCode.INVALID_INPUT.value],
            explanation="Invalid context: investor_id, scheme_id, or position_context is empty/missing.",
            warnings=["Structural non-nullness violation in Action evaluation context."],
            goal_id=context.goal_id if context else None,
            portfolio_id=context.portfolio_id if context else None,
            upstream_assessment_ids=upstream_ids,
            observation_timestamp=now_utc,
        )

    # Check for invalid upstream assessment states
    if context.suitability_result and (not context.suitability_result.assessment_id or not context.suitability_result.investor_id):
        return ActionAssessmentResult(
            assessment_id=assessment_id,
            investor_id=context.investor_id,
            scheme_id=context.scheme_id,
            position_context=context.position_context,
            action_state=ActionState.INVALID_ASSESSMENT,
            information_sufficiency=InformationSufficiency.INSUFFICIENT,
            actionability_status="UNACTIONABLE",
            action_confidence=0.0,
            primary_reason_code=ReasonCode.INVALID_INPUT.value,
            reason_codes=[ReasonCode.INVALID_INPUT.value],
            explanation="Upstream Suitability assessment is invalid.",
            warnings=["Tier 1 Precedence: Upstream Suitability assessment reported negative confidence score."],
            goal_id=context.goal_id,
            portfolio_id=context.portfolio_id,
            upstream_assessment_ids=upstream_ids,
            observation_timestamp=now_utc,
        )

    if context.portfolio_need_result and context.portfolio_need_result.primary_state == PortfolioNeedState.INVALID_ASSESSMENT:
        return ActionAssessmentResult(
            assessment_id=assessment_id,
            investor_id=context.investor_id,
            scheme_id=context.scheme_id,
            position_context=context.position_context,
            action_state=ActionState.INVALID_ASSESSMENT,
            information_sufficiency=InformationSufficiency.INSUFFICIENT,
            actionability_status="UNACTIONABLE",
            action_confidence=0.0,
            primary_reason_code=ReasonCode.INVALID_INPUT.value,
            reason_codes=[ReasonCode.INVALID_INPUT.value],
            explanation="Upstream Portfolio Need assessment is invalid.",
            warnings=["Tier 1 Precedence: Upstream Portfolio Need assessment reported INVALID_ASSESSMENT."],
            goal_id=context.goal_id,
            portfolio_id=context.portfolio_id,
            upstream_assessment_ids=upstream_ids,
            observation_timestamp=now_utc,
        )

    # -------------------------------------------------------------------------
    # STAGE 2: INFORMATION SUFFICIENCY CHECK (Tier 2 - INSUFFICIENT INFORMATION)
    # -------------------------------------------------------------------------
    if not context.suitability_result or not context.portfolio_need_result:
        return ActionAssessmentResult(
            assessment_id=assessment_id,
            investor_id=context.investor_id,
            scheme_id=context.scheme_id,
            position_context=context.position_context,
            action_state=ActionState.INSUFFICIENT_INFORMATION,
            information_sufficiency=InformationSufficiency.INSUFFICIENT,
            actionability_status="UNACTIONABLE",
            action_confidence=0.0,
            primary_reason_code=ReasonCode.INSUFFICIENT_INPUT.value,
            reason_codes=[ReasonCode.INSUFFICIENT_INPUT.value],
            explanation="Missing mandatory upstream assessment result (Suitability or Portfolio Need).",
            warnings=["Tier 2 Precedence: Required upstream assessments are absent."],
            goal_id=context.goal_id,
            portfolio_id=context.portfolio_id,
            upstream_assessment_ids=upstream_ids,
            observation_timestamp=now_utc,
        )

    if context.suitability_result.suitability_status == SuitabilityStatus.INSUFFICIENT_INFORMATION or \
       context.portfolio_need_result.primary_state == PortfolioNeedState.INSUFFICIENT_INFORMATION:
        return ActionAssessmentResult(
            assessment_id=assessment_id,
            investor_id=context.investor_id,
            scheme_id=context.scheme_id,
            position_context=context.position_context,
            action_state=ActionState.INSUFFICIENT_INFORMATION,
            information_sufficiency=InformationSufficiency.INSUFFICIENT,
            actionability_status="UNACTIONABLE",
            action_confidence=0.0,
            primary_reason_code=ReasonCode.INSUFFICIENT_INPUT.value,
            reason_codes=[ReasonCode.INSUFFICIENT_INPUT.value],
            explanation="Upstream assessment reports insufficient information.",
            warnings=["Tier 2 Precedence: Upstream Suitability or Portfolio Need reported INSUFFICIENT_INFORMATION."],
            goal_id=context.goal_id,
            portfolio_id=context.portfolio_id,
            upstream_assessment_ids=upstream_ids,
            observation_timestamp=now_utc,
        )

    if context.is_stale_input:
        if context.position_context == PositionContext.EXISTING_POSITION:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.REVIEW,
                information_sufficiency=InformationSufficiency.PARTIAL,
                actionability_status="CONSTRAINED",
                action_confidence=0.5,
                primary_reason_code=ReasonCode.STALE_INPUT.value,
                reason_codes=[ReasonCode.STALE_INPUT.value],
                explanation="Upstream assessment data is stale per governed freshness criteria. Explicit position review required.",
                warnings=["Tier 2 Precedence: Stale assessment input detected for existing position."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )
        else:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.INSUFFICIENT_INFORMATION,
                information_sufficiency=InformationSufficiency.INSUFFICIENT,
                actionability_status="UNACTIONABLE",
                action_confidence=0.0,
                primary_reason_code=ReasonCode.STALE_INPUT.value,
                reason_codes=[ReasonCode.STALE_INPUT.value],
                explanation="Upstream assessment data is stale per governed freshness criteria. Cannot evaluate new position.",
                warnings=["Tier 2 Precedence: Stale assessment input detected for new candidate."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )

    # -------------------------------------------------------------------------
    # STAGE 3: SUITABILITY & HARD CONSTRAINTS (Tier 3 - NOT SUITABLE / HARD CONSTRAINT)
    # -------------------------------------------------------------------------
    has_lock_in_conflict = "LOCK_IN_CONFLICT" in context.suitability_result.constraints_applied if context.suitability_result.constraints_applied else False
    if context.suitability_result.suitability_status == SuitabilityStatus.NOT_SUITABLE or has_lock_in_conflict:
        if context.position_context == PositionContext.NEW_POSITION:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.NO_ACTION,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="UNACTIONABLE",
                action_confidence=1.0,
                primary_reason_code=ReasonCode.CANDIDATE_NOT_SUITABLE.value,
                reason_codes=[ReasonCode.CANDIDATE_NOT_SUITABLE.value],
                explanation="Candidate scheme is not suitable for the investor profile. Purchase prohibited.",
                warnings=["Tier 3 Precedence: Suitability status is NOT_SUITABLE or lock-in conflict present."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )
        else:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.REVIEW,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="CONSTRAINED",
                action_confidence=1.0,
                primary_reason_code=ReasonCode.CANDIDATE_NOT_SUITABLE.value,
                reason_codes=[ReasonCode.CANDIDATE_NOT_SUITABLE.value],
                explanation="Existing holding fails current suitability requirements. Position review required.",
                warnings=["Tier 3 Precedence: Existing position suitability status is NOT_SUITABLE."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )

    # -------------------------------------------------------------------------
    # STAGE 4: DETERIORATION & REVIEW SIGNALS (Tier 4 - MATERIAL REVIEW SIGNAL)
    # -------------------------------------------------------------------------
    if context.position_context == PositionContext.EXISTING_POSITION and context.deterioration_signal:
        if context.deterioration_signal == "TEMPORARY_UNDERPERFORMANCE":
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.HOLD,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="ACTIONABLE",
                action_confidence=1.0,
                primary_reason_code=ReasonCode.TEMPORARY_UNDERPERFORMANCE.value,
                reason_codes=[ReasonCode.TEMPORARY_UNDERPERFORMANCE.value],
                explanation="Short-term volatility or temporary underperformance does not justify position liquidation.",
                warnings=["Low-turnover rule: Temporary drawdowns do not trigger transactions."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )
        elif context.deterioration_signal == "MILD_DETERIORATION":
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.MONITOR,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="ACTIONABLE",
                action_confidence=0.9,
                primary_reason_code=ReasonCode.MATERIAL_REVIEW_SIGNAL.value,
                reason_codes=[ReasonCode.MATERIAL_REVIEW_SIGNAL.value],
                explanation="Mild performance decay observed; position flagged for ongoing monitoring.",
                warnings=["Tier 4 Precedence: Mild deterioration signal assigned to MONITOR."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )
        elif context.deterioration_signal == "MATERIAL_DETERIORATION":
            # Check 14-point switch guardrails
            if context.deterioration_validated is not True:
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.REVIEW,
                    information_sufficiency=InformationSufficiency.PARTIAL,
                    actionability_status="CONSTRAINED",
                    action_confidence=0.5,
                    primary_reason_code=ReasonCode.UNVALIDATED_DETERIORATION.value,
                    reason_codes=[ReasonCode.UNVALIDATED_DETERIORATION.value],
                    explanation="Deterioration signal relies on unvalidated methodology or thresholds. Liquidation prohibited.",
                    warnings=["Switch Guardrail: Unvalidated deterioration methodology prevents SELL."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )
            if context.has_suitable_replacement is not True:
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.REVIEW,
                    information_sufficiency=InformationSufficiency.SUFFICIENT,
                    actionability_status="CONSTRAINED",
                    action_confidence=0.8,
                    primary_reason_code=ReasonCode.NO_SUITABLE_REPLACEMENT.value,
                    reason_codes=[ReasonCode.NO_SUITABLE_REPLACEMENT.value],
                    explanation="Holding exhibits material deterioration, but no suitable category replacement is currently available.",
                    warnings=["Switch Guardrail: No suitable category replacement available."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )
            if context.fund_quality_comparison_valid is not True:
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.REVIEW,
                    information_sufficiency=InformationSufficiency.PARTIAL,
                    actionability_status="CONSTRAINED",
                    action_confidence=0.5,
                    primary_reason_code=ReasonCode.INSUFFICIENT_EVIDENCE.value,
                    reason_codes=[ReasonCode.INSUFFICIENT_EVIDENCE.value],
                    explanation="Fund Quality comparison between holding and replacement candidate is unavailable or invalid; replacement cannot be justified on that evidence.",
                    warnings=["Switch Guardrail: Fund Quality comparison is invalid or unknown."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )
            if context.tax_liability_known is not True:
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.REVIEW,
                    information_sufficiency=InformationSufficiency.PARTIAL,
                    actionability_status="CONSTRAINED",
                    action_confidence=0.5,
                    primary_reason_code=ReasonCode.TAX_COST_INFORMATION_MISSING.value,
                    reason_codes=[ReasonCode.TAX_COST_INFORMATION_MISSING.value],
                    explanation="Holding exhibits deterioration, but tax cost information is missing. Liquidation prohibited.",
                    warnings=["Switch Guardrail: Missing tax liability metadata prevents SELL/SWITCH."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )
            if context.exit_load_known is not True:
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.REVIEW,
                    information_sufficiency=InformationSufficiency.PARTIAL,
                    actionability_status="CONSTRAINED",
                    action_confidence=0.5,
                    primary_reason_code=ReasonCode.EXIT_LOAD_INFORMATION_MISSING.value,
                    reason_codes=[ReasonCode.EXIT_LOAD_INFORMATION_MISSING.value],
                    explanation="Holding exhibits deterioration, but exit load schedule is missing. Liquidation prohibited.",
                    warnings=["Switch Guardrail: Missing exit load schedule prevents SELL/SWITCH."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )
            if context.economic_benefit_state != "ECONOMICALLY_BENEFICIAL":
                reason = ReasonCode.SWITCH_NOT_JUSTIFIED.value if context.economic_benefit_state == "ECONOMICALLY_NOT_BENEFICIAL" else ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.REVIEW,
                    information_sufficiency=InformationSufficiency.SUFFICIENT,
                    actionability_status="CONSTRAINED",
                    action_confidence=0.7,
                    primary_reason_code=reason,
                    reason_codes=[reason],
                    explanation="Holding exhibits deterioration, but after-tax/after-cost switching economics do not justify liquidation.",
                    warnings=["Switch Guardrail: After-tax switching economics are negative or unproven."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )
            
            # All switch guardrails satisfied
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.SELL,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="ACTIONABLE",
                action_confidence=1.0,
                primary_reason_code=ReasonCode.MATERIAL_REVIEW_SIGNAL.value,
                reason_codes=[ReasonCode.MATERIAL_REVIEW_SIGNAL.value],
                explanation="Material deterioration confirmed, suitable replacement available, candidate Fund Quality comparison is valid, and net economic benefit is verified. Recommended SELL.",
                warnings=[],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )

    # -------------------------------------------------------------------------
    # STAGE 5: ECONOMIC & PORTFOLIO ACTIONABILITY (Tier 5 - ECONOMIC / PORTFOLIO ACTIONABILITY)
    # -------------------------------------------------------------------------
    need_res = context.portfolio_need_result
    if need_res.candidate_fulfillment_status == CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED:
        if context.position_context == PositionContext.NEW_POSITION:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.NO_ACTION,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="UNACTIONABLE",
                action_confidence=1.0,
                primary_reason_code=ReasonCode.CANDIDATE_CANNOT_FULFILL_NEED.value,
                reason_codes=[ReasonCode.CANDIDATE_CANNOT_FULFILL_NEED.value],
                explanation="Candidate scheme cannot fulfill the identified portfolio requirement.",
                warnings=["Tier 5 Precedence: Candidate cannot fulfill need."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )
        else:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.HOLD,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="ACTIONABLE",
                action_confidence=1.0,
                primary_reason_code=ReasonCode.CANDIDATE_CANNOT_FULFILL_NEED.value,
                reason_codes=[ReasonCode.CANDIDATE_CANNOT_FULFILL_NEED.value],
                explanation="Candidate scheme cannot fulfill need; maintaining existing position.",
                warnings=["Tier 5 Precedence: Candidate cannot fulfill need."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )

    if need_res.candidate_fulfillment_status == CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN:
        if context.position_context == PositionContext.NEW_POSITION:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.NO_ACTION,
                information_sufficiency=InformationSufficiency.PARTIAL,
                actionability_status="UNACTIONABLE",
                action_confidence=0.5,
                primary_reason_code=ReasonCode.CANDIDATE_FULFILLMENT_UNKNOWN.value,
                reason_codes=[ReasonCode.CANDIDATE_FULFILLMENT_UNKNOWN.value],
                explanation="Candidate fulfillment capability is unknown. Purchase prohibited.",
                warnings=["Tier 5 Precedence: Candidate fulfillment capability is unknown."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )
        else:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.MONITOR,
                information_sufficiency=InformationSufficiency.PARTIAL,
                actionability_status="CONSTRAINED",
                action_confidence=0.5,
                primary_reason_code=ReasonCode.CANDIDATE_FULFILLMENT_UNKNOWN.value,
                reason_codes=[ReasonCode.CANDIDATE_FULFILLMENT_UNKNOWN.value],
                explanation="Candidate fulfillment capability is unknown; monitoring existing position.",
                warnings=["Tier 5 Precedence: Candidate fulfillment capability is unknown."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )

    # Check look-through concentration & overlap constraints
    if "CATEGORY_OVEREXPOSED" in need_res.contextual_flags:
        if context.position_context == PositionContext.NEW_POSITION and need_res.primary_state == PortfolioNeedState.NEED_IDENTIFIED:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.ACCUMULATE,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="CONSTRAINED",
                action_confidence=0.8,
                primary_reason_code=ReasonCode.CATEGORY_CONCENTRATION_EXCEEDED.value,
                reason_codes=[ReasonCode.CATEGORY_CONCENTRATION_EXCEEDED.value],
                explanation="Portfolio gap exists, but category exposure is concentrated. Recommended staged entry (ACCUMULATE) rather than lump sum.",
                warnings=["Concentration Warning: Category exposure is high."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )
        elif context.position_context == PositionContext.EXISTING_POSITION:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.HOLD,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="ACTIONABLE",
                action_confidence=0.9,
                primary_reason_code=ReasonCode.CATEGORY_CONCENTRATION_EXCEEDED.value,
                reason_codes=[ReasonCode.CATEGORY_CONCENTRATION_EXCEEDED.value],
                explanation="Category exposure is concentrated; additional allocation deferred.",
                warnings=["Concentration Warning: Category exposure is high."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )

    if "HIGH_SECURITY_OVERLAP" in need_res.contextual_flags:
        if context.position_context == PositionContext.NEW_POSITION and need_res.primary_state == PortfolioNeedState.NEED_IDENTIFIED:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.ACCUMULATE,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="CONSTRAINED",
                action_confidence=0.8,
                primary_reason_code=ReasonCode.HIGH_SECURITY_OVERLAP.value,
                reason_codes=[ReasonCode.HIGH_SECURITY_OVERLAP.value],
                explanation="Portfolio gap exists, but high security overlap detected with existing holdings. Recommended staged entry.",
                warnings=["Overlap Warning: High security overlap detected."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )

    # -------------------------------------------------------------------------
    # STAGE 6: POSITIVE OPPORTUNITY EVALUATION (Tier 6 - POSITIVE OPPORTUNITY)
    # -------------------------------------------------------------------------
    if need_res.primary_state == PortfolioNeedState.NEED_IDENTIFIED:
        # Resolve Fund Quality score and confidence from context or suitability_result
        fq_score = context.fund_quality_score
        if fq_score is None and context.suitability_result:
            fq_score = context.suitability_result.fund_quality_score_consumed

        fq_conf = context.fund_quality_confidence
        if fq_conf is None and context.suitability_result:
            fq_conf = context.suitability_result.fund_quality_confidence_consumed

        # Fund Quality Evidence Guardrail (if fq_score is explicitly None and suitability consumed score is also None, or fund_quality_evidence_valid is not True)
        fq_ev_valid = getattr(context, "fund_quality_evidence_valid", None)
        if (fq_score is None and getattr(context, "fund_quality_assessment_id", None) is not None) or (fq_ev_valid is not True):
            if context.position_context == PositionContext.NEW_POSITION:
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.NO_ACTION,
                    information_sufficiency=InformationSufficiency.PARTIAL,
                    actionability_status="UNACTIONABLE",
                    action_confidence=0.5,
                    primary_reason_code=ReasonCode.INSUFFICIENT_EVIDENCE.value,
                    reason_codes=[ReasonCode.INSUFFICIENT_EVIDENCE.value],
                    explanation="Fund Quality score or evidence is invalid or missing. Purchase prohibited.",
                    warnings=["Fund Quality Guardrail: Invalid or missing Fund Quality evidence."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )
            else:
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.HOLD,
                    information_sufficiency=InformationSufficiency.SUFFICIENT,
                    actionability_status="ACTIONABLE",
                    action_confidence=0.9,
                    primary_reason_code=ReasonCode.INSUFFICIENT_EVIDENCE.value,
                    reason_codes=[ReasonCode.INSUFFICIENT_EVIDENCE.value],
                    explanation="Fund Quality score or evidence is invalid or missing. Maintaining existing position.",
                    warnings=["Fund Quality Guardrail: Invalid or missing Fund Quality evidence."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )

        # Economic Benefit Guardrail
        if context.economic_benefit_state != "ECONOMICALLY_BENEFICIAL":
            if context.position_context == PositionContext.NEW_POSITION:
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.NO_ACTION,
                    information_sufficiency=InformationSufficiency.PARTIAL,
                    actionability_status="UNACTIONABLE",
                    action_confidence=0.5,
                    primary_reason_code=ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value,
                    reason_codes=[ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value],
                    explanation="Portfolio need identified, but economic benefit is uncertain or unproven.",
                    warnings=["Economic Benefit Guardrail: Net economic benefit is unproven."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )
            else:
                return ActionAssessmentResult(
                    assessment_id=assessment_id,
                    investor_id=context.investor_id,
                    scheme_id=context.scheme_id,
                    position_context=context.position_context,
                    action_state=ActionState.HOLD,
                    information_sufficiency=InformationSufficiency.SUFFICIENT,
                    actionability_status="ACTIONABLE",
                    action_confidence=0.9,
                    primary_reason_code=ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value,
                    reason_codes=[ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value],
                    explanation="Portfolio need identified, but economic benefit of changing position is uncertain or negative; maintaining existing position.",
                    warnings=["Economic Benefit Guardrail: Net economic benefit is unproven."],
                    goal_id=context.goal_id,
                    portfolio_id=context.portfolio_id,
                    upstream_assessment_ids=upstream_ids,
                    observation_timestamp=now_utc,
                )

        # Affordability Constraint Check
        if need_res.affordability_status == AffordabilityStatus.AFFORDABILITY_CONSTRAINED or \
           context.suitability_result.affordability_status == "AFFORDABILITY_CONSTRAINED":
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.ACCUMULATE,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="CONSTRAINED",
                action_confidence=0.9,
                primary_reason_code=ReasonCode.AFFORDABILITY_CONSTRAINED.value,
                reason_codes=[ReasonCode.AFFORDABILITY_CONSTRAINED.value],
                explanation="Portfolio need identified and candidate is suitable, but investor contribution capacity is constrained. Recommended staged accumulation (SIP).",
                warnings=["Affordability Constraint: Recommended contribution is constrained by capacity."],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )

        # Fully Unconstrained Positive Opportunity
        if context.position_context == PositionContext.NEW_POSITION:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.BUY,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="ACTIONABLE",
                action_confidence=1.0,
                primary_reason_code=ReasonCode.NEED_IDENTIFIED.value,
                reason_codes=[ReasonCode.NEED_IDENTIFIED.value, ReasonCode.POSITIVE_PORTFOLIO_NEED.value],
                explanation="Portfolio need identified, candidate is suitable and capable, and economic benefit is verified. Recommended BUY.",
                warnings=[],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )
        else:
            return ActionAssessmentResult(
                assessment_id=assessment_id,
                investor_id=context.investor_id,
                scheme_id=context.scheme_id,
                position_context=context.position_context,
                action_state=ActionState.ACCUMULATE,
                information_sufficiency=InformationSufficiency.SUFFICIENT,
                actionability_status="ACTIONABLE",
                action_confidence=1.0,
                primary_reason_code=ReasonCode.NEED_IDENTIFIED.value,
                reason_codes=[ReasonCode.NEED_IDENTIFIED.value, ReasonCode.POSITIVE_PORTFOLIO_NEED.value],
                explanation="Portfolio need identified and candidate is suitable. Recommended additional exposure (ACCUMULATE).",
                warnings=[],
                goal_id=context.goal_id,
                portfolio_id=context.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                observation_timestamp=now_utc,
            )

    # -------------------------------------------------------------------------
    # STAGE 7: DEFAULT BASELINE ACTION (Tier 7 - HOLD / NO CHANGE)
    # -------------------------------------------------------------------------
    if context.position_context == PositionContext.NEW_POSITION:
        return ActionAssessmentResult(
            assessment_id=assessment_id,
            investor_id=context.investor_id,
            scheme_id=context.scheme_id,
            position_context=context.position_context,
            action_state=ActionState.NO_ACTION,
            information_sufficiency=InformationSufficiency.SUFFICIENT,
            actionability_status="UNACTIONABLE",
            action_confidence=1.0,
            primary_reason_code=ReasonCode.NO_PORTFOLIO_NEED.value if need_res.primary_state == PortfolioNeedState.NO_MATERIAL_NEED else ReasonCode.HOLD_DEFAULT.value,
            reason_codes=[ReasonCode.NO_PORTFOLIO_NEED.value if need_res.primary_state == PortfolioNeedState.NO_MATERIAL_NEED else ReasonCode.HOLD_DEFAULT.value],
            explanation="No portfolio need exists for candidate scheme. No transaction recommended.",
            warnings=[],
            goal_id=context.goal_id,
            portfolio_id=context.portfolio_id,
            upstream_assessment_ids=upstream_ids,
            observation_timestamp=now_utc,
        )
    else:
        return ActionAssessmentResult(
            assessment_id=assessment_id,
            investor_id=context.investor_id,
            scheme_id=context.scheme_id,
            position_context=context.position_context,
            action_state=ActionState.HOLD,
            information_sufficiency=InformationSufficiency.SUFFICIENT,
            actionability_status="ACTIONABLE",
            action_confidence=1.0,
            primary_reason_code=ReasonCode.HOLD_DEFAULT.value,
            reason_codes=[ReasonCode.HOLD_DEFAULT.value],
            explanation="Existing holding remains appropriate; no material need for position change.",
            warnings=[],
            goal_id=context.goal_id,
            portfolio_id=context.portfolio_id,
            upstream_assessment_ids=upstream_ids,
            observation_timestamp=now_utc,
        )
