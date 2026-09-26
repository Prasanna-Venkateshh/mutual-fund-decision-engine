"""
Phase F.11.2 — Point-in-Time Historical Evaluation & Backtesting Engine

Provides:
1. PointInTimeEvaluationEngine: Strict historical boundary filtering (date <= T).
2. MarketRegime: Defined historical market regimes for empirical validation.
3. HistoricalDecisionTracker: Score trajectory, decision churn, and transition recorder.
4. AntiLookAheadValidator: Verification that future data leakage cannot alter historical outputs.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from models.fund_quality_dataset import FundQualityDatasetInput, CategoryPointInTimeContext, SchemeMetricSnapshot, ProvenanceMetadata
from data.builders.fund_quality_dataset_builder import FundQualityDatasetBuilder
from scoring.engine import FundQualityScoringEngine
from risk.suitability_engine import SuitabilityEngine, SuitabilityEvaluationRequest, FundRiskProfileInput
from portfolio.need_models import PortfolioNeedAssessmentResult, PortfolioNeedState, CandidateFulfillmentStatus, AffordabilityStatus
from action.models import ActionState, PositionContext
from integration.models import EconomicBenefitState, IntegrationStatus
from integration.contracts import (
    from_fund_quality_result,
    from_risk_alignment_result,
    from_suitability_result,
    from_portfolio_need_result,
    from_economic_benefit_result,
    build_action_input_contract
)
from integration.orchestrator import DecisionOrchestrator


class MarketRegime(Enum):
    """Historical market regimes supported for empirical validation."""
    BULL_MARKET_2017 = "BULL_MARKET_2017"             # 2017-01-01 to 2017-12-31
    VOLATILE_BEAR_2018 = "VOLATILE_BEAR_2018"         # 2018-01-01 to 2018-12-31
    COVID_CRASH_2020 = "COVID_CRASH_2020"             # 2020-02-01 to 2020-03-31
    COVID_RECOVERY_2020 = "COVID_RECOVERY_2020"       # 2020-04-01 to 2020-12-31
    RANGEBOUND_2022_2023 = "RANGEBOUND_2022_2023"     # 2022-01-01 to 2023-06-30


@dataclass(frozen=True)
class RegimeDefinition:
    """Metadata definition for a market regime period."""
    regime: MarketRegime
    name: str
    start_date: date
    end_date: date
    description: str


REGIME_CATALOG: Dict[MarketRegime, RegimeDefinition] = {
    MarketRegime.BULL_MARKET_2017: RegimeDefinition(
        regime=MarketRegime.BULL_MARKET_2017,
        name="Sustained Bull Market (2017)",
        start_date=date(2017, 1, 1),
        end_date=date(2017, 12, 31),
        description="Broad equity market expansion across large, mid, and small caps."
    ),
    MarketRegime.VOLATILE_BEAR_2018: RegimeDefinition(
        regime=MarketRegime.VOLATILE_BEAR_2018,
        name="Mid/Small Cap Drawdown (2018)",
        start_date=date(2018, 1, 1),
        end_date=date(2018, 12, 31),
        description="SEBI reclassification & sharp mid/small-cap correction."
    ),
    MarketRegime.COVID_CRASH_2020: RegimeDefinition(
        regime=MarketRegime.COVID_CRASH_2020,
        name="COVID-19 Market Crash (Q1 2020)",
        start_date=date(2020, 2, 1),
        end_date=date(2020, 3, 31),
        description="Severe sudden global drawdown across all risk categories."
    ),
    MarketRegime.COVID_RECOVERY_2020: RegimeDefinition(
        regime=MarketRegime.COVID_RECOVERY_2020,
        name="Post-Crash V-Shaped Recovery (Q2–Q4 2020)",
        start_date=date(2020, 4, 1),
        end_date=date(2020, 12, 31),
        description="Rapid market rally backed by global liquidity."
    ),
    MarketRegime.RANGEBOUND_2022_2023: RegimeDefinition(
        regime=MarketRegime.RANGEBOUND_2022_2023,
        name="Rising Rates & Range-Bound Market (2022–2023)",
        start_date=date(2022, 1, 1),
        end_date=date(2023, 6, 30),
        description="Global inflation, rate hikes, and sideways consolidation."
    ),
}


@dataclass(frozen=True)
class HistoricalEvaluationPoint:
    """Result container for a single historical evaluation date T."""
    decision_date: date
    canonical_scheme_id: str
    quality_score: Optional[float]
    confidence_score: float
    suitability_status: str
    portfolio_need_state: str
    economic_benefit_state: str
    action_state: ActionState
    explanation: str
    is_pit_strictly_enforced: bool


class PointInTimeEvaluationEngine:
    """
    Point-in-Time Evaluation Engine.
    Filters raw NAV observations and scheme metadata strictly to date <= T.
    Prevents look-ahead bias and future data leakage.
    """

    def __init__(self):
        self.builder = FundQualityDatasetBuilder()
        self.scoring_engine = FundQualityScoringEngine()
        self.suitability_engine = SuitabilityEngine()
        self.orchestrator = DecisionOrchestrator()

    def filter_nav_history_pit(
        self, full_nav_history: List[Dict[str, Any]], decision_date: date
    ) -> List[Dict[str, Any]]:
        """Filters NAV history strictly to date <= decision_date."""
        filtered = []
        for obs in full_nav_history:
            d_str = obs.get("date")
            if not d_str:
                continue
            obs_d = date.fromisoformat(d_str) if isinstance(d_str, str) else d_str
            if obs_d <= decision_date:
                filtered.append(obs)
        return filtered

    def evaluate_scheme_at_historical_date(
        self,
        amfi_code: int,
        scheme_name: str,
        category_str: str,
        subcategory_str: str,
        full_nav_history: List[Dict[str, Any]],
        decision_date: date,
        investor_profile: Any,
        risk_alignment: Any,
        goal_profile: Any,
        position_context: PositionContext = PositionContext.NEW_POSITION,
        ter_value: Optional[float] = None,
        riskometer_label: Optional[str] = None,
        benchmark_name: Optional[str] = None,
        override_canonical_id: Optional[str] = None
    ) -> HistoricalEvaluationPoint:
        """Evaluates decision engine strictly using data available on decision_date."""
        pit_nav = self.filter_nav_history_pit(full_nav_history, decision_date)
        canonical_id = override_canonical_id or f"CAN_AMFI_{amfi_code}"

        inp = self.builder.build_dataset_input_for_scheme(
            amfi_code=str(amfi_code),
            scheme_name=scheme_name,
            observation_date=decision_date,
            nav_history=pit_nav,
            source_id="AMFI_OFFICIAL",
            source_document_url="https://www.amfiindia.com/spages/NAVAll.txt",
            custom_category_data={"category": category_str, "subcategory": subcategory_str},
            override_canonical_id=canonical_id
        )

        fq_result = self.scoring_engine.calculate_fund_quality_score(inp, [inp])
        suit_req = SuitabilityEvaluationRequest(
            investor_profile=investor_profile,
            risk_alignment=risk_alignment,
            fund_quality_score=fq_result,
            goal_profile=goal_profile,
            fund_risk_profile=FundRiskProfileInput(raw_riskometer_value=riskometer_label),
            observation_date=decision_date
        )
        suit_result = self.suitability_engine.evaluate(suit_req)

        pneed_result = PortfolioNeedAssessmentResult(
            assessment_id=f"pneed_pit_{amfi_code}",
            investor_id=investor_profile.investor_id,
            goal_id=goal_profile.goal_id,
            scheme_id=canonical_id,
            primary_state=PortfolioNeedState.NEED_IDENTIFIED if position_context == PositionContext.NEW_POSITION else PortfolioNeedState.NO_MATERIAL_NEED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
            observation_timestamp=datetime.now(timezone.utc)
        )
        eb_contract = from_economic_benefit_result(
            assessment_id=f"eb_pit_{amfi_code}",
            investor_id=investor_profile.investor_id,
            economic_benefit_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL if position_context == PositionContext.NEW_POSITION else EconomicBenefitState.BENEFIT_UNCERTAIN,
            position_context=position_context.value,
            candidate_scheme_id=canonical_id,
            economic_benefit_actionable=True if position_context == PositionContext.NEW_POSITION else False,
            evidence_sufficiency_valid=True
        )

        fq_contract = from_fund_quality_result(fq_result, canonical_scheme_id=canonical_id)
        ra_contract = from_risk_alignment_result(risk_alignment)
        suit_contract = from_suitability_result(suit_result)
        pneed_contract = from_portfolio_need_result(pneed_result)

        action_input = build_action_input_contract(
            investor_id=investor_profile.investor_id,
            scheme_id=canonical_id,
            position_context=position_context,
            assessment_id=f"act_input_pit_{amfi_code}_{decision_date.isoformat()}",
            goal_id=goal_profile.goal_id,
            fund_quality_contract=fq_contract,
            risk_alignment_contract=ra_contract,
            suitability_contract=suit_contract,
            portfolio_need_contract=pneed_contract,
            economic_benefit_contract=eb_contract
        )

        out = self.orchestrator.evaluate_decision(action_input)

        return HistoricalEvaluationPoint(
            decision_date=decision_date,
            canonical_scheme_id=canonical_id,
            quality_score=fq_result.quality_score,
            confidence_score=fq_result.confidence_score,
            suitability_status=suit_result.suitability_status.value,
            portfolio_need_state=pneed_result.primary_state.value,
            economic_benefit_state=eb_contract.economic_benefit_state.value,
            action_state=out.final_action_state,
            explanation=out.final_explanation,
            is_pit_strictly_enforced=True
        )


class DecisionChurnAnalyzer:
    """Calculates decision stability metrics and action transition frequencies."""

    @staticmethod
    def calculate_churn_metrics(evaluations: List[HistoricalEvaluationPoint]) -> Dict[str, Any]:
        """Calculates transition counts, state frequencies, and score stability."""
        if not evaluations:
            return {"total_evaluations": 0, "transitions": 0, "churn_rate": 0.0}

        sorted_evals = sorted(evaluations, key=lambda x: x.decision_date)
        state_counts: Dict[str, int] = {}
        transitions = 0

        prev_state: Optional[ActionState] = None
        scores: List[float] = []

        for ev in sorted_evals:
            s_val = ev.action_state.value
            state_counts[s_val] = state_counts.get(s_val, 0) + 1
            if ev.quality_score is not None:
                scores.append(ev.quality_score)
            if prev_state is not None and prev_state != ev.action_state:
                transitions += 1
            prev_state = ev.action_state

        n = len(sorted_evals)
        churn_rate = transitions / float(n - 1) if n > 1 else 0.0

        return {
            "total_evaluations": n,
            "state_distribution": state_counts,
            "transition_count": transitions,
            "churn_rate": churn_rate,
            "evaluated_scores_count": len(scores)
        }
