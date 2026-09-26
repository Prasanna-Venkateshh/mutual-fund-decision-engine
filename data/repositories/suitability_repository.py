"""
Suitability & Investor Profile Repository (Phase F.2).

Manages storage and retrieval of InvestorProfileSnapshot, GoalProfile, and
SuitabilityAssessmentResult contracts using SQLite.

Enforces:
- Schema persistence for investor profiles, goals, and assessment records.
- Immutability and historical audit reproducibility (append-only profile versions).
- Query retrieval by investor_id, profile_version, and assessment_id.
"""

import json
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional
import sqlite3

from models.investor_profile import (
    InvestorProfileSnapshot,
    FinancialCapacitySnapshot,
    BehavioralToleranceSnapshot,
    RiskCapacityLevel,
    RiskToleranceLevel,
    ProfileStatus
)
from models.goal_profile import GoalProfile, GoalCategory, GoalPriority
from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus
from models.fund_quality_dataset import ProvenanceMetadata


CREATE_SUITABILITY_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS investor_profile_snapshots (
    profile_id TEXT PRIMARY KEY,
    investor_id TEXT NOT NULL,
    profile_version TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    payload_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    UNIQUE(investor_id, profile_version)
);

CREATE TABLE IF NOT EXISTS goal_profiles (
    goal_id TEXT PRIMARY KEY,
    investor_id TEXT NOT NULL,
    goal_name TEXT NOT NULL,
    goal_category TEXT NOT NULL,
    is_general_wealth INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suitability_assessment_records (
    assessment_id TEXT PRIMARY KEY,
    investor_id TEXT NOT NULL,
    profile_version_used TEXT NOT NULL,
    canonical_scheme_id TEXT NOT NULL,
    observation_date TEXT NOT NULL,
    suitability_status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);
"""


class SuitabilityRepository:
    """Repository for managing Suitability & Investor Profile persistence."""

    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn
        self._init_tables()

    def _init_tables(self) -> None:
        self.conn.executescript(CREATE_SUITABILITY_TABLES_SQL)
        self.conn.commit()

    # --- Investor Profile Methods ---

    def save_profile_snapshot(self, profile: InvestorProfileSnapshot) -> str:
        """Persists an immutable InvestorProfileSnapshot record."""
        payload = self._serialize_profile(profile)
        now_utc = datetime.now(timezone.utc).isoformat()

        sql = """
        INSERT OR REPLACE INTO investor_profile_snapshots (
            profile_id, investor_id, profile_version, effective_date,
            status, confidence_score, payload_json, created_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(
            sql,
            (
                profile.profile_id,
                profile.investor_id,
                profile.profile_version,
                profile.effective_date.isoformat(),
                profile.status.value,
                profile.confidence_score,
                json.dumps(payload),
                now_utc
            )
        )
        self.conn.commit()
        return profile.profile_id

    def get_profile_snapshot(self, investor_id: str, profile_version: str) -> Optional[InvestorProfileSnapshot]:
        """Retrieves a specific versioned InvestorProfileSnapshot."""
        sql = """
        SELECT payload_json FROM investor_profile_snapshots
        WHERE investor_id = ? AND profile_version = ?;
        """
        cursor = self.conn.execute(sql, (investor_id, profile_version))
        row = cursor.fetchone()
        if not row:
            return None
        return self._deserialize_profile(json.loads(row[0]))

    # --- Goal Profile Methods ---

    def save_goal_profile(self, goal: GoalProfile) -> str:
        """Persists a GoalProfile record."""
        payload = self._serialize_goal(goal)
        now_utc = datetime.now(timezone.utc).isoformat()

        sql = """
        INSERT OR REPLACE INTO goal_profiles (
            goal_id, investor_id, goal_name, goal_category,
            is_general_wealth, payload_json, created_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(
            sql,
            (
                goal.goal_id,
                goal.investor_id,
                goal.goal_name,
                goal.goal_category.value,
                1 if goal.is_general_wealth else 0,
                json.dumps(payload),
                now_utc
            )
        )
        self.conn.commit()
        return goal.goal_id

    def get_goal_profiles_for_investor(self, investor_id: str) -> List[GoalProfile]:
        """Retrieves all GoalProfiles for an investor."""
        sql = "SELECT payload_json FROM goal_profiles WHERE investor_id = ?;"
        cursor = self.conn.execute(sql, (investor_id,))
        rows = cursor.fetchall()
        return [self._deserialize_goal(json.loads(r[0])) for r in rows]

    # --- Suitability Assessment Record Methods ---

    def save_assessment_result(self, result: SuitabilityAssessmentResult) -> str:
        """Persists a SuitabilityAssessmentResult output record."""
        payload = self._serialize_assessment(result)
        now_utc = datetime.now(timezone.utc).isoformat()

        sql = """
        INSERT OR REPLACE INTO suitability_assessment_records (
            assessment_id, investor_id, profile_version_used,
            canonical_scheme_id, observation_date, suitability_status,
            payload_json, created_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(
            sql,
            (
                result.assessment_id,
                result.investor_id,
                result.profile_version_used,
                result.canonical_scheme_id,
                result.observation_date.isoformat(),
                result.suitability_status.value,
                json.dumps(payload),
                now_utc
            )
        )
        self.conn.commit()
        return result.assessment_id

    def get_assessment_result(self, assessment_id: str) -> Optional[SuitabilityAssessmentResult]:
        """Retrieves a stored SuitabilityAssessmentResult by ID."""
        sql = "SELECT payload_json FROM suitability_assessment_records WHERE assessment_id = ?;"
        cursor = self.conn.execute(sql, (assessment_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._deserialize_assessment(json.loads(row[0]))

    # --- Serialization Helpers ---

    def _serialize_profile(self, p: InvestorProfileSnapshot) -> Dict[str, Any]:
        fc = p.financial_capacity
        fc_dict = None
        if fc is not None:
            fc_dict = {
                "observation_date": fc.observation_date.isoformat(),
                "effective_date": fc.effective_date.isoformat(),
                "monthly_gross_income": fc.monthly_gross_income,
                "monthly_fixed_expenses": fc.monthly_fixed_expenses,
                "monthly_debt_servicing": fc.monthly_debt_servicing,
                "liquid_emergency_reserves": fc.liquid_emergency_reserves,
                "emergency_reserve_months": fc.emergency_reserve_months,
                "savings_ratio": fc.savings_ratio,
                "sustainable_monthly_capacity": fc.sustainable_monthly_capacity,
                "capacity_tier": fc.capacity_tier.value if fc.capacity_tier else None,
                "confidence_score": fc.confidence_score,
                "methodology_version": fc.methodology_version,
                "rule_version": fc.rule_version
            }

        bt = p.behavioral_tolerance
        bt_dict = None
        if bt is not None:
            bt_dict = {
                "observation_date": bt.observation_date.isoformat(),
                "assessment_date": bt.assessment_date.isoformat(),
                "loss_reaction_choice": bt.loss_reaction_choice,
                "stagnation_comfort_choice": bt.stagnation_comfort_choice,
                "historical_drawdown_action": bt.historical_drawdown_action,
                "volatility_preference": bt.volatility_preference,
                "behavioral_consistency_score": bt.behavioral_consistency_score,
                "tolerance_tier": bt.tolerance_tier.value if bt.tolerance_tier else None,
                "confidence_score": bt.confidence_score,
                "methodology_version": bt.methodology_version,
                "rule_version": bt.rule_version
            }

        return {
            "profile_id": p.profile_id,
            "investor_id": p.investor_id,
            "profile_version": p.profile_version,
            "effective_date": p.effective_date.isoformat(),
            "birth_date": p.birth_date.isoformat() if p.birth_date else None,
            "financial_capacity": fc_dict,
            "behavioral_tolerance": bt_dict,
            "overall_effective_risk_alignment": p.overall_effective_risk_alignment.value if p.overall_effective_risk_alignment else None,
            "profiling_tier_completed": p.profiling_tier_completed,
            "status": p.status.value,
            "confidence_score": p.confidence_score,
            "methodology_version": p.methodology_version,
            "rule_version": p.rule_version,
            "is_stale": p.is_stale
        }

    def _deserialize_profile(self, p: Dict[str, Any]) -> InvestorProfileSnapshot:
        fc_d = p.get("financial_capacity")
        fc = None
        if fc_d:
            fc = FinancialCapacitySnapshot(
                observation_date=date.fromisoformat(fc_d["observation_date"]),
                effective_date=date.fromisoformat(fc_d["effective_date"]),
                monthly_gross_income=fc_d.get("monthly_gross_income"),
                monthly_fixed_expenses=fc_d.get("monthly_fixed_expenses"),
                monthly_debt_servicing=fc_d.get("monthly_debt_servicing"),
                liquid_emergency_reserves=fc_d.get("liquid_emergency_reserves"),
                emergency_reserve_months=fc_d.get("emergency_reserve_months"),
                savings_ratio=fc_d.get("savings_ratio"),
                sustainable_monthly_capacity=fc_d.get("sustainable_monthly_capacity"),
                capacity_tier=RiskCapacityLevel(fc_d["capacity_tier"]) if fc_d.get("capacity_tier") else None,
                confidence_score=float(fc_d.get("confidence_score", 1.0)),
                methodology_version=fc_d.get("methodology_version", "1.0.0"),
                rule_version=fc_d.get("rule_version", "1.0.0")
            )

        bt_d = p.get("behavioral_tolerance")
        bt = None
        if bt_d:
            bt = BehavioralToleranceSnapshot(
                observation_date=date.fromisoformat(bt_d["observation_date"]),
                assessment_date=date.fromisoformat(bt_d["assessment_date"]),
                loss_reaction_choice=bt_d.get("loss_reaction_choice"),
                stagnation_comfort_choice=bt_d.get("stagnation_comfort_choice"),
                historical_drawdown_action=bt_d.get("historical_drawdown_action"),
                volatility_preference=bt_d.get("volatility_preference"),
                behavioral_consistency_score=float(bt_d.get("behavioral_consistency_score", 1.0)),
                tolerance_tier=RiskToleranceLevel(bt_d["tolerance_tier"]) if bt_d.get("tolerance_tier") else None,
                confidence_score=float(bt_d.get("confidence_score", 1.0)),
                methodology_version=bt_d.get("methodology_version", "1.0.0"),
                rule_version=bt_d.get("rule_version", "1.0.0")
            )

        return InvestorProfileSnapshot(
            profile_id=p["profile_id"],
            investor_id=p["investor_id"],
            profile_version=p["profile_version"],
            effective_date=date.fromisoformat(p["effective_date"]),
            birth_date=date.fromisoformat(p["birth_date"]) if p.get("birth_date") else None,
            financial_capacity=fc,
            behavioral_tolerance=bt,
            overall_effective_risk_alignment=RiskCapacityLevel(p["overall_effective_risk_alignment"]) if p.get("overall_effective_risk_alignment") else None,
            profiling_tier_completed=int(p.get("profiling_tier_completed", 1)),
            status=ProfileStatus(p["status"]),
            confidence_score=float(p.get("confidence_score", 1.0)),
            methodology_version=p.get("methodology_version", "1.0.0"),
            rule_version=p.get("rule_version", "1.0.0"),
            is_stale=bool(p.get("is_stale", False))
        )

    def _serialize_goal(self, g: GoalProfile) -> Dict[str, Any]:
        return {
            "goal_id": g.goal_id,
            "investor_id": g.investor_id,
            "goal_name": g.goal_name,
            "goal_category": g.goal_category.value,
            "target_date": g.target_date.isoformat() if g.target_date else None,
            "effective_horizon_years": g.effective_horizon_years,
            "target_amount": g.target_amount,
            "is_target_amount_known": g.is_target_amount_known,
            "is_target_date_known": g.is_target_date_known,
            "priority": g.priority.value,
            "current_funding_amount": g.current_funding_amount,
            "current_monthly_contribution": g.current_monthly_contribution,
            "is_general_wealth": g.is_general_wealth,
            "methodology_version": g.methodology_version,
            "rule_version": g.rule_version
        }

    def _deserialize_goal(self, g: Dict[str, Any]) -> GoalProfile:
        return GoalProfile(
            goal_id=g["goal_id"],
            investor_id=g["investor_id"],
            goal_name=g["goal_name"],
            goal_category=GoalCategory(g["goal_category"]),
            target_date=date.fromisoformat(g["target_date"]) if g.get("target_date") else None,
            effective_horizon_years=g.get("effective_horizon_years"),
            target_amount=g.get("target_amount"),
            is_target_amount_known=bool(g.get("is_target_amount_known", True)),
            is_target_date_known=bool(g.get("is_target_date_known", True)),
            priority=GoalPriority(g.get("priority", 3)),
            current_funding_amount=g.get("current_funding_amount"),
            current_monthly_contribution=g.get("current_monthly_contribution"),
            is_general_wealth=bool(g.get("is_general_wealth", False)),
            methodology_version=g.get("methodology_version", "1.0.0"),
            rule_version=g.get("rule_version", "1.0.0")
        )

    def _serialize_assessment(self, r: SuitabilityAssessmentResult) -> Dict[str, Any]:
        return {
            "assessment_id": r.assessment_id,
            "investor_id": r.investor_id,
            "profile_version_used": r.profile_version_used,
            "canonical_scheme_id": r.canonical_scheme_id,
            "amfi_code": r.amfi_code,
            "scheme_name": r.scheme_name,
            "category": r.category,
            "subcategory": r.subcategory,
            "observation_date": r.observation_date.isoformat(),
            "suitability_status": r.suitability_status.value,
            "goal_id": r.goal_id,
            "effective_risk_alignment": r.effective_risk_alignment,
            "risk_capacity_result": r.risk_capacity_result,
            "risk_tolerance_result": r.risk_tolerance_result,
            "max_permissible_asset_risk": r.max_permissible_asset_risk,
            "effective_horizon_years": r.effective_horizon_years,
            "is_horizon_compatible": r.is_horizon_compatible,
            "is_liquidity_compatible": r.is_liquidity_compatible,
            "affordability_status": r.affordability_status,
            "sustainable_sip_capacity": r.sustainable_sip_capacity,
            "fund_quality_score_consumed": r.fund_quality_score_consumed,
            "fund_quality_confidence_consumed": r.fund_quality_confidence_consumed,
            "suitability_confidence_score": r.suitability_confidence_score,
            "constraints_applied": r.constraints_applied,
            "rejection_reasons": r.rejection_reasons,
            "summary_explanation": r.summary_explanation,
            "methodology_version": r.methodology_version,
            "rule_version": r.rule_version
        }

    def _deserialize_assessment(self, r: Dict[str, Any]) -> SuitabilityAssessmentResult:
        return SuitabilityAssessmentResult(
            assessment_id=r["assessment_id"],
            investor_id=r["investor_id"],
            profile_version_used=r["profile_version_used"],
            canonical_scheme_id=r["canonical_scheme_id"],
            amfi_code=r["amfi_code"],
            scheme_name=r["scheme_name"],
            category=r["category"],
            subcategory=r["subcategory"],
            observation_date=date.fromisoformat(r["observation_date"]),
            suitability_status=SuitabilityStatus(r["suitability_status"]),
            goal_id=r.get("goal_id"),
            effective_risk_alignment=r.get("effective_risk_alignment"),
            risk_capacity_result=r.get("risk_capacity_result"),
            risk_tolerance_result=r.get("risk_tolerance_result"),
            max_permissible_asset_risk=r.get("max_permissible_asset_risk"),
            effective_horizon_years=r.get("effective_horizon_years"),
            is_horizon_compatible=r.get("is_horizon_compatible"),
            is_liquidity_compatible=r.get("is_liquidity_compatible"),
            affordability_status=r.get("affordability_status"),
            sustainable_sip_capacity=r.get("sustainable_sip_capacity"),
            fund_quality_score_consumed=r.get("fund_quality_score_consumed"),
            fund_quality_confidence_consumed=float(r.get("fund_quality_confidence_consumed", 1.0)),
            suitability_confidence_score=float(r.get("suitability_confidence_score", 1.0)),
            constraints_applied=r.get("constraints_applied", []),
            rejection_reasons=r.get("rejection_reasons", []),
            summary_explanation=r.get("summary_explanation", ""),
            methodology_version=r.get("methodology_version", "1.0.0"),
            rule_version=r.get("rule_version", "1.0.0")
        )
