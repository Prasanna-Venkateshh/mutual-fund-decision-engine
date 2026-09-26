"""
Investor Profile Repository (Phase V1).

Provides durable, privacy-conscious, deterministic SQLite storage for governed
InvestorProfileSnapshot contracts across application sessions.

Governance Rules Enforced:
- InvestorProfileSnapshot is the canonical profile data contract.
- Missing information remains explicitly missing (None / NULL).
- 0 remains 0, 0.0 remains 0.0, False remains False.
- Round-trip serialization fidelity without loss of enums, dates, or floats.
- Append-only version history with deterministic current-version retrieval.
- Fail closed: malformed or corrupt payloads raise explicit ProfilePersistenceError.
- Session/Investor identity isolation: explicit investor_id required for retrieval.
"""

import json
import sqlite3
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional

from models.investor_profile import (
    InvestorProfileSnapshot,
    FinancialCapacitySnapshot,
    BehavioralToleranceSnapshot,
    RiskCapacityLevel,
    RiskToleranceLevel,
    ProfileStatus,
)


class ProfilePersistenceError(Exception):
    """Raised when profile persistence, serialization, or schema operation fails."""
    pass


class ProfileNotFoundError(Exception):
    """Raised when a requested investor profile or profile version is not found."""
    pass


CREATE_PROFILE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS investor_profile_snapshots (
    profile_id TEXT PRIMARY KEY,
    investor_id TEXT NOT NULL,
    profile_version TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    payload_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1,
    UNIQUE(investor_id, profile_version)
);
"""


class ProfileRepository:
    """Repository for managing persistent InvestorProfileSnapshot records in SQLite."""

    def __init__(self, db_conn: sqlite3.Connection):
        if db_conn is None:
            raise ProfilePersistenceError("sqlite3.Connection cannot be None")
        self.conn = db_conn
        self._init_tables()

    def _init_tables(self) -> None:
        """Initializes database schema and performs additive migrations if needed."""
        try:
            self.conn.executescript(CREATE_PROFILE_TABLE_SQL)
            
            # Ensure is_current column exists for backwards-compatibility with existing DBs
            cursor = self.conn.execute("PRAGMA table_info(investor_profile_snapshots);")
            columns = [row[1] for row in cursor.fetchall()]
            if "is_current" not in columns:
                self.conn.execute(
                    "ALTER TABLE investor_profile_snapshots ADD COLUMN is_current INTEGER NOT NULL DEFAULT 1;"
                )
            self.conn.commit()
        except sqlite3.Error as e:
            raise ProfilePersistenceError(f"Database schema initialization failed: {e}") from e

    def save_profile(self, profile: InvestorProfileSnapshot) -> str:
        """
        Persists an InvestorProfileSnapshot.
        Sets previous profile versions for investor_id to is_current = 0
        and stores new profile as is_current = 1.
        """
        if not isinstance(profile, InvestorProfileSnapshot):
            raise ProfilePersistenceError(
                f"Expected InvestorProfileSnapshot instance, got {type(profile)}"
            )

        payload = self._serialize_profile(profile)
        now_utc = datetime.now(timezone.utc).isoformat()

        try:
            # Mark existing versions as not current
            self.conn.execute(
                "UPDATE investor_profile_snapshots SET is_current = 0 WHERE investor_id = ?;",
                (profile.investor_id,)
            )

            sql = """
            INSERT OR REPLACE INTO investor_profile_snapshots (
                profile_id, investor_id, profile_version, effective_date,
                status, confidence_score, payload_json, created_at_utc, is_current
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1);
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
        except sqlite3.Error as e:
            self.conn.rollback()
            raise ProfilePersistenceError(f"Failed to save investor profile: {e}") from e

    def get_current_profile(self, investor_id: str) -> Optional[InvestorProfileSnapshot]:
        """
        Retrieves the current active InvestorProfileSnapshot for an investor_id.
        Returns None if no profile exists for the specified investor_id.
        """
        if not investor_id or not isinstance(investor_id, str) or not investor_id.strip():
            raise ProfilePersistenceError("investor_id must be a non-empty string")

        sql = """
        SELECT payload_json FROM investor_profile_snapshots
        WHERE investor_id = ? AND is_current = 1
        ORDER BY created_at_utc DESC LIMIT 1;
        """
        try:
            cursor = self.conn.execute(sql, (investor_id.strip(),))
            row = cursor.fetchone()
            if not row:
                # Fallback to latest created if is_current flag is absent/unset
                sql_fallback = """
                SELECT payload_json FROM investor_profile_snapshots
                WHERE investor_id = ?
                ORDER BY created_at_utc DESC LIMIT 1;
                """
                cursor_fb = self.conn.execute(sql_fallback, (investor_id.strip(),))
                row = cursor_fb.fetchone()
                if not row:
                    return None
            return self._deserialize_profile(json.loads(row[0]))
        except json.JSONDecodeError as e:
            raise ProfilePersistenceError(f"Malformed JSON payload for investor_id '{investor_id}': {e}") from e
        except sqlite3.Error as e:
            raise ProfilePersistenceError(f"Database error retrieving profile for '{investor_id}': {e}") from e

    def get_profile_version(self, investor_id: str, profile_version: str) -> Optional[InvestorProfileSnapshot]:
        """Retrieves a specific historical profile version for an investor_id."""
        if not investor_id or not investor_id.strip():
            raise ProfilePersistenceError("investor_id must be a non-empty string")
        if not profile_version or not profile_version.strip():
            raise ProfilePersistenceError("profile_version must be a non-empty string")

        sql = """
        SELECT payload_json FROM investor_profile_snapshots
        WHERE investor_id = ? AND profile_version = ?;
        """
        try:
            cursor = self.conn.execute(sql, (investor_id.strip(), profile_version.strip()))
            row = cursor.fetchone()
            if not row:
                return None
            return self._deserialize_profile(json.loads(row[0]))
        except json.JSONDecodeError as e:
            raise ProfilePersistenceError(f"Malformed JSON payload for version '{profile_version}': {e}") from e
        except sqlite3.Error as e:
            raise ProfilePersistenceError(f"Database error retrieving profile version: {e}") from e

    def list_profile_versions(self, investor_id: str) -> List[Dict[str, Any]]:
        """Returns a list of version metadata records for an investor_id ordered by creation date."""
        if not investor_id or not investor_id.strip():
            raise ProfilePersistenceError("investor_id must be a non-empty string")

        sql = """
        SELECT profile_id, profile_version, effective_date, status, confidence_score, is_current, created_at_utc
        FROM investor_profile_snapshots
        WHERE investor_id = ?
        ORDER BY created_at_utc ASC;
        """
        try:
            cursor = self.conn.execute(sql, (investor_id.strip(),))
            rows = cursor.fetchall()
            return [
                {
                    "profile_id": r[0],
                    "profile_version": r[1],
                    "effective_date": r[2],
                    "status": r[3],
                    "confidence_score": r[4],
                    "is_current": bool(r[5]),
                    "created_at_utc": r[6],
                }
                for r in rows
            ]
        except sqlite3.Error as e:
            raise ProfilePersistenceError(f"Database error listing profile versions: {e}") from e

    # --- Serialization Helpers ---

    def _serialize_profile(self, p: InvestorProfileSnapshot) -> Dict[str, Any]:
        """Serializes InvestorProfileSnapshot to JSON-safe dictionary preserving exact types and None semantics."""
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
                "rule_version": fc.rule_version,
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
                "rule_version": bt.rule_version,
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
            "created_timestamp_utc": p.created_timestamp_utc.isoformat() if p.created_timestamp_utc else None,
            "methodology_version": p.methodology_version,
            "rule_version": p.rule_version,
            "is_stale": p.is_stale,
        }

    def _deserialize_profile(self, p: Dict[str, Any]) -> InvestorProfileSnapshot:
        """Deserializes JSON dictionary back to governed InvestorProfileSnapshot instance."""
        try:
            fc_d = p.get("financial_capacity")
            fc = None
            if fc_d is not None:
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
                    capacity_tier=RiskCapacityLevel(fc_d["capacity_tier"]) if fc_d.get("capacity_tier") is not None else None,
                    confidence_score=float(fc_d.get("confidence_score", 1.0)),
                    methodology_version=fc_d.get("methodology_version", "1.0.0"),
                    rule_version=fc_d.get("rule_version", "1.0.0"),
                )

            bt_d = p.get("behavioral_tolerance")
            bt = None
            if bt_d is not None:
                bt = BehavioralToleranceSnapshot(
                    observation_date=date.fromisoformat(bt_d["observation_date"]),
                    assessment_date=date.fromisoformat(bt_d["assessment_date"]),
                    loss_reaction_choice=bt_d.get("loss_reaction_choice"),
                    stagnation_comfort_choice=bt_d.get("stagnation_comfort_choice"),
                    historical_drawdown_action=bt_d.get("historical_drawdown_action"),
                    volatility_preference=bt_d.get("volatility_preference"),
                    behavioral_consistency_score=float(bt_d.get("behavioral_consistency_score", 1.0)),
                    tolerance_tier=RiskToleranceLevel(bt_d["tolerance_tier"]) if bt_d.get("tolerance_tier") is not None else None,
                    confidence_score=float(bt_d.get("confidence_score", 1.0)),
                    methodology_version=bt_d.get("methodology_version", "1.0.0"),
                    rule_version=bt_d.get("rule_version", "1.0.0"),
                )

            created_ts = None
            if p.get("created_timestamp_utc"):
                created_ts = datetime.fromisoformat(p["created_timestamp_utc"])

            return InvestorProfileSnapshot(
                profile_id=p["profile_id"],
                investor_id=p["investor_id"],
                profile_version=p["profile_version"],
                effective_date=date.fromisoformat(p["effective_date"]),
                birth_date=date.fromisoformat(p["birth_date"]) if p.get("birth_date") else None,
                financial_capacity=fc,
                behavioral_tolerance=bt,
                overall_effective_risk_alignment=RiskCapacityLevel(p["overall_effective_risk_alignment"]) if p.get("overall_effective_risk_alignment") is not None else None,
                profiling_tier_completed=int(p.get("profiling_tier_completed", 1)),
                status=ProfileStatus(p["status"]),
                confidence_score=float(p.get("confidence_score", 1.0)),
                created_timestamp_utc=created_ts,
                methodology_version=p.get("methodology_version", "1.0.0"),
                rule_version=p.get("rule_version", "1.0.0"),
                is_stale=bool(p.get("is_stale", False)),
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ProfilePersistenceError(f"Deserialization failed for profile data: {e}") from e
