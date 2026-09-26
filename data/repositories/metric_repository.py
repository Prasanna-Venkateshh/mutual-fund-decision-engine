"""
Metric Observation Repository Layer (data/repositories/).

Provides database access operations for persisting and querying calculated MetricObservation objects
in SQLite.
"""

import json
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any

from models.metric_data import MetricObservation
from models.nav_data import DataQualityState
from db.database import DatabaseConnection


class MetricRepository:
    """Repository handling database operations for calculated metric observations."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def save_metric_observations(self, metrics: List[MetricObservation]) -> int:
        """
        Persist a list of MetricObservation records into fund_metric_observations table.
        Uses INSERT OR REPLACE on UNIQUE(canonical_scheme_id, metric_name, start_date, end_date).
        """
        inserted_count = 0
        with self.db.get_conn() as conn:
            for m in metrics:
                calc_ts = m.calculation_timestamp.isoformat() if m.calculation_timestamp else datetime.now(timezone.utc).isoformat()
                cursor = conn.execute(
                    """
                    INSERT OR REPLACE INTO fund_metric_observations (
                        metric_id, canonical_scheme_id, metric_name, metric_value,
                        start_date, end_date, observation_count, confidence_state,
                        calculation_timestamp, methodology_version, notes, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        m.metric_id, m.canonical_scheme_id, m.metric_name, m.metric_value,
                        m.start_date.isoformat(), m.end_date.isoformat(), m.observation_count,
                        m.confidence_state.value, calc_ts, m.methodology_version,
                        m.notes, json.dumps(m.metadata_json) if m.metadata_json else None
                    )
                )
                inserted_count += cursor.rowcount
        return inserted_count

    def get_metrics_for_scheme(self, canonical_scheme_id: str) -> List[Dict[str, Any]]:
        """Retrieve all metric observations for a given canonical scheme ID."""
        with self.db.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT metric_id, canonical_scheme_id, metric_name, metric_value,
                       start_date, end_date, observation_count, confidence_state,
                       calculation_timestamp, methodology_version, notes, metadata_json
                FROM fund_metric_observations
                WHERE canonical_scheme_id = ?
                ORDER BY metric_name ASC, start_date ASC
                """,
                (canonical_scheme_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_metric_by_name(self, canonical_scheme_id: str, metric_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve the latest calculation of a specific metric by name for a scheme."""
        with self.db.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT metric_id, canonical_scheme_id, metric_name, metric_value,
                       start_date, end_date, observation_count, confidence_state,
                       calculation_timestamp, methodology_version, notes, metadata_json
                FROM fund_metric_observations
                WHERE canonical_scheme_id = ? AND metric_name = ?
                ORDER BY calculation_timestamp DESC LIMIT 1
                """,
                (canonical_scheme_id, metric_name)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
