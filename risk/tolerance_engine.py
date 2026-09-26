"""
Risk Tolerance Assessment Engine (Phase F.3.2).

Implements the governed production architecture slice of the Risk Tolerance Engine.

Governance Rules Enforced:
- Risk Tolerance represents behavioral willingness to accept investment loss, volatility, uncertainty, and drawdowns.
- CONSTRUCT INDEPENDENCE: Risk Tolerance MUST NOT use financial capacity, income, expenses, debt, emergency reserves,
  savings, net worth, portfolio value, losses, dependents, horizon, fund quality, or demographics.
- Multi-scenario design: evaluates loss reaction, stagnation comfort, historical drawdown action, and volatility preference.
- No hardcoded loss aversion multipliers or Cronbach alpha cutoffs.
- Missing responses NEVER silently become zero, low, or high defaults.
- Confidence NEVER alters the behavioral Risk Tolerance score.
- Supports PRODUCTION, RESEARCH, and TEST startup modes.
"""

import math
import uuid
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from config.risk.tolerance_config import RiskToleranceConfig, StartupMode
from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import (
    BehavioralToleranceSnapshot,
    RiskToleranceLevel,
)
from risk.capacity_models import AssessmentStatus
from risk.tolerance_models import (
    BehavioralConsistencyLevel,
    RiskToleranceAssessmentResult,
)


class RiskToleranceEngine:
    """
    Production Risk Tolerance Engine implementing Phase F suitability architecture.
    Calculates behavioral risk tolerance strictly independently of financial capacity.
    """

    def __init__(self, config: RiskToleranceConfig):
        self.config = config

    # -------------------------------------------------------------------------
    # A. INPUT VALIDATION & INITIALIZATION
    # -------------------------------------------------------------------------
    def validate_inputs(
        self,
        snapshot: Optional[BehavioralToleranceSnapshot],
    ) -> List[str]:
        """
        Validates behavioral tolerance snapshot choices against allowed questionnaire parameters.
        Returns list of validation error messages.
        """
        errors = []
        if snapshot is None:
            return ["BehavioralToleranceSnapshot cannot be None"]

        valid_choices = set()
        for m in [
            self.config.loss_reaction_weight_map,
            self.config.stagnation_comfort_weight_map,
            self.config.drawdown_action_weight_map,
            self.config.volatility_preference_weight_map,
        ]:
            if m:
                valid_choices.update(m.keys())

        for field_name, choice_val, m in [
            ("loss_reaction_choice", snapshot.loss_reaction_choice, self.config.loss_reaction_weight_map),
            ("stagnation_comfort_choice", snapshot.stagnation_comfort_choice, self.config.stagnation_comfort_weight_map),
            ("historical_drawdown_action", snapshot.historical_drawdown_action, self.config.drawdown_action_weight_map),
            ("volatility_preference", snapshot.volatility_preference, self.config.volatility_preference_weight_map),
        ]:
            if choice_val is not None and m is not None and choice_val not in m:
                errors.append(f"Invalid choice '{choice_val}' for field {field_name}")

        return errors

    # -------------------------------------------------------------------------
    # B. RESPONSE NORMALIZATION & SCORING
    # -------------------------------------------------------------------------
    def normalize_choices(
        self,
        snapshot: BehavioralToleranceSnapshot,
    ) -> Dict[str, float]:
        """
        Normalizes explicit scenario choices into continuous numerical signals [0.0, 1.0].
        Directionality: higher value = higher behavioral risk acceptance.
        """
        signals = {}
        if snapshot.loss_reaction_choice is not None and self.config.loss_reaction_weight_map:
            if snapshot.loss_reaction_choice in self.config.loss_reaction_weight_map:
                signals["loss_reaction"] = self.config.loss_reaction_weight_map[snapshot.loss_reaction_choice]

        if snapshot.stagnation_comfort_choice is not None and self.config.stagnation_comfort_weight_map:
            if snapshot.stagnation_comfort_choice in self.config.stagnation_comfort_weight_map:
                signals["stagnation_comfort"] = self.config.stagnation_comfort_weight_map[snapshot.stagnation_comfort_choice]

        if snapshot.historical_drawdown_action is not None and self.config.drawdown_action_weight_map:
            if snapshot.historical_drawdown_action in self.config.drawdown_action_weight_map:
                signals["historical_drawdown"] = self.config.drawdown_action_weight_map[snapshot.historical_drawdown_action]

        if snapshot.volatility_preference is not None and self.config.volatility_preference_weight_map:
            if snapshot.volatility_preference in self.config.volatility_preference_weight_map:
                signals["volatility_preference"] = self.config.volatility_preference_weight_map[snapshot.volatility_preference]

        return signals


    def calculate_raw_tolerance_score(
        self,
        normalized_signals: Dict[str, float],
    ) -> Optional[float]:
        """
        Calculates raw continuous behavioral tolerance score [0.0, 1.0]
        as the arithmetic mean of available normalized scenario responses.
        
        Returns None if no responses are supplied.
        """
        if not normalized_signals:
            return None
        return sum(normalized_signals.values()) / len(normalized_signals)

    # -------------------------------------------------------------------------
    # C. RESPONSE CONSISTENCY ANALYSIS
    # -------------------------------------------------------------------------
    def analyze_consistency(
        self,
        normalized_signals: Dict[str, float],
    ) -> Tuple[float, BehavioralConsistencyLevel]:
        """
        Evaluates intra-respondent behavioral consistency across multi-scenario choices.
        
        GOVERNANCE NOTE:
        Uses sample standard deviation across normalized responses [0.0, 1.0].
        Does NOT use Cronbach's alpha = 0.70 as an individual cutoff (per F.2B audit).
        Inconsistent responses do NOT change raw tolerance score, but lower confidence.
        
        Returns (consistency_score [0.0, 1.0], BehavioralConsistencyLevel).
        """
        if len(normalized_signals) < 2:
            return 1.0, BehavioralConsistencyLevel.HIGHLY_CONSISTENT

        values = list(normalized_signals.values())
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / (len(values) - 1)
        sample_stddev = math.sqrt(variance)

        # Consistency score: 1.0 - sample_stddev (clamped to [0.0, 1.0])
        consistency_score = max(0.0, min(1.0, 1.0 - sample_stddev))

        mod_thresh = self.config.consistency_std_dev_threshold_moderate or 0.25
        mat_thresh = self.config.consistency_std_dev_threshold_material or 0.40

        if sample_stddev >= mat_thresh:
            level = BehavioralConsistencyLevel.MATERIALLY_INCONSISTENT
        elif sample_stddev >= mod_thresh:
            level = BehavioralConsistencyLevel.MODERATELY_INCONSISTENT
        else:
            level = BehavioralConsistencyLevel.HIGHLY_CONSISTENT

        return consistency_score, level

    # -------------------------------------------------------------------------
    # D. ORDINAL TIER MAPPING
    # -------------------------------------------------------------------------
    def map_ordinal_tier(
        self,
        raw_score: Optional[float],
    ) -> Optional[RiskToleranceLevel]:
        """
        Maps raw continuous behavioral score [0.0, 1.0] to 5-level ordinal RiskToleranceLevel.
        Uses externalized threshold mapping from configuration.
        
        Returns None if raw_score is None.
        """
        if raw_score is None:
            return None

        vl = self.config.very_low_upper_threshold or 0.20
        l = self.config.low_upper_threshold or 0.40
        m = self.config.moderate_upper_threshold or 0.60
        h = self.config.high_upper_threshold or 0.80

        if raw_score < vl:
            return RiskToleranceLevel.VERY_LOW
        elif raw_score < l:
            return RiskToleranceLevel.LOW
        elif raw_score < m:
            return RiskToleranceLevel.MODERATE
        elif raw_score < h:
            return RiskToleranceLevel.HIGH
        else:
            return RiskToleranceLevel.VERY_HIGH

    # -------------------------------------------------------------------------
    # E. CONFIDENCE CALCULATION
    # -------------------------------------------------------------------------
    def calculate_confidence_score(
        self,
        missing_count: int,
        consistency_level: BehavioralConsistencyLevel,
        status: AssessmentStatus,
    ) -> float:
        """
        Calculates Risk Tolerance confidence indicator score strictly AFTER score calculation.
        
        GOVERNANCE NOTE:
        Confidence score MUST NOT alter the behavioral Risk Tolerance score or ordinal tier.
        Reflects response completeness and intra-respondent consistency.
        """
        if status == AssessmentStatus.CONFIGURATION_ERROR:
            return 0.0

        if status == AssessmentStatus.INSUFFICIENT_INFORMATION:
            return self.config.insufficient_info_confidence_cap if self.config.insufficient_info_confidence_cap is not None else 0.20

        base_confidence = 1.0
        missing_penalty = missing_count * (self.config.confidence_penalty_per_missing_response or 0.20)
        
        inconsistency_penalty = 0.0
        if consistency_level == BehavioralConsistencyLevel.MODERATELY_INCONSISTENT:
            inconsistency_penalty = self.config.confidence_penalty_inconsistent_responses or 0.15
        elif consistency_level == BehavioralConsistencyLevel.MATERIALLY_INCONSISTENT:
            inconsistency_penalty = (self.config.confidence_penalty_inconsistent_responses or 0.15) * 2.0

        confidence = base_confidence - missing_penalty - inconsistency_penalty
        
        if status == AssessmentStatus.PARTIAL and self.config.partial_assessment_confidence_cap is not None:
            confidence = min(confidence, self.config.partial_assessment_confidence_cap)

        return max(0.0, min(1.0, confidence))

    # -------------------------------------------------------------------------
    # F. EXPLANATION GENERATION
    # -------------------------------------------------------------------------
    def generate_explanations(
        self,
        normalized_signals: Dict[str, float],
        consistency_level: BehavioralConsistencyLevel,
        status: AssessmentStatus,
        missing_count: int,
    ) -> List[str]:
        """
        Generates structured explanation tokens describing behavioral evidence.
        Emits tokens ONLY when supported by actual responses.
        """
        tokens = []

        if status == AssessmentStatus.CONFIGURATION_ERROR:
            tokens.append("MISSING_PRODUCTION_CALIBRATION_PARAMETERS")
            return tokens

        if status == AssessmentStatus.INSUFFICIENT_INFORMATION:
            tokens.append("INSUFFICIENT_BEHAVIORAL_RESPONSES")
            return tokens

        if status == AssessmentStatus.PARTIAL:
            tokens.append("PARTIAL_BEHAVIORAL_RESPONSES")

        high_t = self.config.explanation_strong_threshold
        low_t = self.config.explanation_low_threshold

        # Behavioral evidence tokens
        if "loss_reaction" in normalized_signals:
            val = normalized_signals["loss_reaction"]
            if val >= high_t:
                tokens.append("STRONG_LOSS_ACCEPTANCE")
            elif val <= low_t:
                tokens.append("LOW_LOSS_ACCEPTANCE")

        if "volatility_preference" in normalized_signals:
            val = normalized_signals["volatility_preference"]
            if val >= high_t:
                tokens.append("HIGH_VOLATILITY_TOLERANCE")
            elif val <= low_t:
                tokens.append("LOW_VOLATILITY_TOLERANCE")

        if "stagnation_comfort" in normalized_signals:
            val = normalized_signals["stagnation_comfort"]
            if val >= high_t:
                tokens.append("HIGH_STAGNATION_COMFORT")
            elif val <= low_t:
                tokens.append("LOW_STAGNATION_COMFORT")

        if "historical_drawdown" in normalized_signals:
            val = normalized_signals["historical_drawdown"]
            if val >= high_t:
                tokens.append("PROLONGED_DRAWDOWN_PATIENCE")
            elif val <= low_t:
                tokens.append("DRAWDOWN_PANIC_REACTION")

        # Consistency tokens
        if len(normalized_signals) >= 2:
            if consistency_level == BehavioralConsistencyLevel.HIGHLY_CONSISTENT:
                tokens.append("CONSISTENT_BEHAVIORAL_RESPONSES")
            else:
                tokens.append("INCONSISTENT_BEHAVIORAL_RESPONSES")

        return tokens


    # -------------------------------------------------------------------------
    # MAIN ENGINE ASSESSMENT PIPELINE
    # -------------------------------------------------------------------------
    def assess_tolerance(
        self,
        snapshot: Optional[BehavioralToleranceSnapshot],
        investor_id: str = "UNKNOWN_INVESTOR",
        profile_version: str = "1.0.0",
        assessment_date: Optional[date] = None,
    ) -> RiskToleranceAssessmentResult:
        """
        Executes the complete end-to-end Risk Tolerance assessment pipeline.
        Returns immutable RiskToleranceAssessmentResult.
        """
        assessment_id = f"RT-{uuid.uuid4().hex[:12].upper()}"
        obs_date = snapshot.observation_date if snapshot and snapshot.observation_date else date.today()
        ts_utc = datetime.now(timezone.utc)

        # 1. Startup Mode & Calibration Config Validation
        config_errors = self.config.validate()
        if config_errors:
            return RiskToleranceAssessmentResult(
                assessment_id=assessment_id,
                investor_id=investor_id,
                profile_version_used=profile_version,
                observation_date=obs_date,
                assessment_timestamp_utc=ts_utc,
                startup_mode=self.config.startup_mode,
                assessment_status=AssessmentStatus.CONFIGURATION_ERROR,
                overall_tolerance_tier=None,
                raw_tolerance_score=None,
                behavioral_consistency_score=1.0,
                consistency_level=BehavioralConsistencyLevel.HIGHLY_CONSISTENT,
                confidence_score=0.0,
                explanation_tokens=["MISSING_PRODUCTION_CALIBRATION_PARAMETERS"],
                provenance=snapshot.provenance if snapshot else None,
                output_tag=self.config.output_tag,
                questionnaire_version=self.config.questionnaire_version,
                methodology_version=self.config.methodology_version,
                rule_version=self.config.rule_version,
            )

        # 2. Input Validation
        input_errors = self.validate_inputs(snapshot)
        if input_errors:
            raise ValueError(f"Input validation failure: {'; '.join(input_errors)}")

        # 3. Response Normalization
        normalized_signals = self.normalize_choices(snapshot)
        total_questions = 4
        supplied_count = len(normalized_signals)
        missing_count = total_questions - supplied_count

        # 4. Assessment Status & Minimum Response Verification
        min_required = self.config.min_required_responses_count or 2

        if supplied_count < min_required:
            status = AssessmentStatus.INSUFFICIENT_INFORMATION
        elif missing_count > 0:
            status = AssessmentStatus.PARTIAL
        else:
            status = AssessmentStatus.COMPLETE

        # If INSUFFICIENT_INFORMATION, return unclassified assessment without guessing
        if status == AssessmentStatus.INSUFFICIENT_INFORMATION:
            conf_score = self.calculate_confidence_score(missing_count, BehavioralConsistencyLevel.HIGHLY_CONSISTENT, status)
            explanations = self.generate_explanations(
                normalized_signals,
                BehavioralConsistencyLevel.HIGHLY_CONSISTENT,
                status,
                missing_count,
            )
            raw_score = self.calculate_raw_tolerance_score(normalized_signals)
            return RiskToleranceAssessmentResult(
                assessment_id=assessment_id,
                investor_id=investor_id,
                profile_version_used=profile_version,
                observation_date=obs_date,
                assessment_timestamp_utc=ts_utc,
                startup_mode=self.config.startup_mode,
                assessment_status=status,
                overall_tolerance_tier=None,  # MISSING != ZERO / LOWEST
                raw_tolerance_score=raw_score,
                loss_acceptance_score=normalized_signals.get("loss_reaction"),
                stagnation_patience_score=normalized_signals.get("stagnation_comfort"),
                drawdown_behavior_score=normalized_signals.get("historical_drawdown"),
                volatility_tolerance_score=normalized_signals.get("volatility_preference"),
                behavioral_consistency_score=1.0,
                consistency_level=BehavioralConsistencyLevel.HIGHLY_CONSISTENT,
                confidence_score=conf_score,
                explanation_tokens=explanations,
                provenance=snapshot.provenance if snapshot else None,
                output_tag=self.config.output_tag,
                questionnaire_version=self.config.questionnaire_version,
                methodology_version=self.config.methodology_version,
                rule_version=self.config.rule_version,
            )

        # 5. Raw Score & Consistency Calculation
        raw_score = self.calculate_raw_tolerance_score(normalized_signals)
        consistency_score, consistency_level = self.analyze_consistency(normalized_signals)

        # 6. Ordinal Tier Mapping
        overall_tier = self.map_ordinal_tier(raw_score)

        # 7. Confidence Score (Calculated separately AFTER score calculation)
        confidence_score = self.calculate_confidence_score(missing_count, consistency_level, status)

        # 8. Explanation Tokens
        explanations = self.generate_explanations(
            normalized_signals,
            consistency_level,
            status,
            missing_count,
        )

        # 9. Return Reproducible Data Contract
        return RiskToleranceAssessmentResult(
            assessment_id=assessment_id,
            investor_id=investor_id,
            profile_version_used=profile_version,
            observation_date=obs_date,
            assessment_timestamp_utc=ts_utc,
            startup_mode=self.config.startup_mode,
            assessment_status=status,
            overall_tolerance_tier=overall_tier,
            raw_tolerance_score=raw_score,
            loss_acceptance_score=normalized_signals.get("loss_reaction"),
            stagnation_patience_score=normalized_signals.get("stagnation_comfort"),
            drawdown_behavior_score=normalized_signals.get("historical_drawdown"),
            volatility_tolerance_score=normalized_signals.get("volatility_preference"),
            behavioral_consistency_score=consistency_score,
            consistency_level=consistency_level,
            confidence_score=confidence_score,
            explanation_tokens=explanations,
            provenance=snapshot.provenance if snapshot else None,
            output_tag=self.config.output_tag,
            questionnaire_version=self.config.questionnaire_version,
            methodology_version=self.config.methodology_version,
            rule_version=self.config.rule_version,
        )

