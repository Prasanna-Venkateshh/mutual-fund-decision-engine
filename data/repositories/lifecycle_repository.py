"""
Lifecycle Repository — Phase C: Point-in-Time Scheme Identity.

Provides all database persistence and retrieval operations for:
- scheme_lifecycle_events (source of truth)
- scheme_universe_snapshots (derived/rebuildable data)
- canonical_schemes lifecycle state updates

Architecture boundary: data/repositories/ — pure persistence, no business logic.
Does not import from metrics/, scoring/, or recommendations/.

Governing Documents:
- ARCHITECTURE.md §4 (data/mapping/ boundary), §11 (Historical State)
- PRODUCT_SPEC.md §24 (Provenance Layer)
- DECISION_RULES.md §12.18.2 (Bias Prevention)
"""

import json
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any

from db.database import DatabaseConnection
from models.scheme_lifecycle import (
    LifecycleEvent,
    LifecycleEventType,
    LifecycleConfidence,
    EffectiveDatePrecision,
)


class LifecycleRepository:
    """
    Repository for scheme lifecycle events and universe snapshots.

    All write operations are idempotent on the primary key (event_id / snapshot key).
    Quarantined events are stored but excluded from production queries by default.
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # ------------------------------------------------------------------
    # Lifecycle Event Persistence
    # ------------------------------------------------------------------

    def save_lifecycle_event(self, event: LifecycleEvent) -> None:
        """
        Persist a lifecycle event.  Idempotent on event_id (INSERT OR IGNORE).

        Raises ValueError if mandatory provenance fields are missing.
        The LifecycleEvent __post_init__ already validates source_id and
        methodology_version; this adds a DB-layer guard for safety.
        """
        if not event.source_id:
            raise ValueError(
                f"Cannot persist LifecycleEvent {event.event_id}: source_id is required."
            )
        if not event.methodology_version:
            raise ValueError(
                f"Cannot persist LifecycleEvent {event.event_id}: methodology_version is required."
            )

        created_at = (event.created_at or datetime.now(timezone.utc)).isoformat()

        with self.db.get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO scheme_lifecycle_events (
                    event_id, canonical_scheme_id, event_type,
                    effective_date, effective_date_precision,
                    source_id, source_document_url, retrieval_timestamp_utc,
                    predecessor_scheme_ids, successor_scheme_ids,
                    old_value, new_value,
                    confidence, status, quarantine_reason,
                    methodology_version, notes, created_at
                ) VALUES (
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?
                )
                """,
                (
                    event.event_id,
                    event.canonical_scheme_id,
                    event.event_type.value,
                    event.effective_date.isoformat(),
                    event.effective_date_precision.value,
                    event.source_id,
                    event.source_document_url,
                    event.retrieval_timestamp_utc.isoformat(),
                    json.dumps(event.predecessor_scheme_ids),
                    json.dumps(event.successor_scheme_ids),
                    event.old_value,
                    event.new_value,
                    event.confidence.value,
                    event.status,
                    event.quarantine_reason,
                    event.methodology_version,
                    event.notes,
                    created_at,
                ),
            )

    def get_events_for_scheme(
        self,
        canonical_scheme_id: str,
        as_of_date: Optional[date] = None,
        include_quarantined: bool = False,
    ) -> List[LifecycleEvent]:
        """
        Return lifecycle events for a scheme.

        If as_of_date is set, only returns events with effective_date <= as_of_date.
        By default excludes QUARANTINED events (include_quarantined=False).

        Ordering: chronological by effective_date ASC, then created_at ASC.
        """
        params: list = [canonical_scheme_id]
        sql = """
            SELECT * FROM scheme_lifecycle_events
            WHERE canonical_scheme_id = ?
        """

        if not include_quarantined:
            sql += " AND status = 'ACTIVE'"

        if as_of_date is not None:
            sql += " AND effective_date <= ?"
            params.append(as_of_date.isoformat())

        sql += " ORDER BY effective_date ASC, created_at ASC"

        with self.db.get_conn() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

        return [self._row_to_event(dict(row)) for row in rows]

    def get_event_by_id(self, event_id: str) -> Optional[LifecycleEvent]:
        """Retrieve a single lifecycle event by its event_id."""
        with self.db.get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM scheme_lifecycle_events WHERE event_id = ?",
                (event_id,),
            )
            row = cursor.fetchone()
        return self._row_to_event(dict(row)) if row else None

    def quarantine_event(self, event_id: str, reason: str) -> None:
        """
        Update a lifecycle event status to QUARANTINED with documented reason.
        Quarantined events are excluded from production resolution queries.
        """
        if not reason:
            raise ValueError("quarantine_reason must be provided when quarantining an event.")

        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE scheme_lifecycle_events
                SET status = 'QUARANTINED', quarantine_reason = ?
                WHERE event_id = ?
                """,
                (reason, event_id),
            )

    def get_predecessor_schemes(
        self,
        canonical_scheme_id: str,
        as_of_date: date,
    ) -> List[str]:
        """
        Return canonical_scheme_ids of schemes that were merged INTO this scheme
        as of as_of_date.  Based on SCHEME_RECEIVED_MERGER events.
        Returns empty list if no merger relationships found.
        """
        events = self.get_events_for_scheme(
            canonical_scheme_id=canonical_scheme_id,
            as_of_date=as_of_date,
            include_quarantined=False,
        )
        predecessors: List[str] = []
        for ev in events:
            if ev.event_type == LifecycleEventType.SCHEME_RECEIVED_MERGER:
                predecessors.extend(ev.predecessor_scheme_ids)
        return list(set(predecessors))

    def get_successor_scheme(
        self,
        canonical_scheme_id: str,
        as_of_date: date,
    ) -> Optional[str]:
        """
        Return the canonical_scheme_id this scheme was merged into as of as_of_date.
        Based on SCHEME_MERGED_INTO events.  Returns None if no merger found.
        If multiple successor events found (data anomaly), returns the first by effective_date.
        """
        events = self.get_events_for_scheme(
            canonical_scheme_id=canonical_scheme_id,
            as_of_date=as_of_date,
            include_quarantined=False,
        )
        for ev in events:
            if ev.event_type == LifecycleEventType.SCHEME_MERGED_INTO and ev.successor_scheme_ids:
                return ev.successor_scheme_ids[0]
        return None

    # ------------------------------------------------------------------
    # Universe Snapshot Persistence (DERIVED DATA)
    # ------------------------------------------------------------------

    def save_universe_snapshot(
        self,
        canonical_scheme_id: str,
        snapshot_date: date,
        existence_status: str,
        confidence: str,
        derived_from_events: List[str],
        methodology_version: str,
    ) -> None:
        """
        Persist a point-in-time universe snapshot.
        UPSERT on (canonical_scheme_id, snapshot_date, methodology_version).

        This is DERIVED data — it must be rebuildable from lifecycle events.
        Do not treat snapshots as authoritative source truth.
        """
        snapshot_id = f"snap_{uuid.uuid5(uuid.NAMESPACE_DNS, f'{canonical_scheme_id}:{snapshot_date.isoformat()}:{methodology_version}').hex}"
        created_at = datetime.now(timezone.utc).isoformat()

        with self.db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO scheme_universe_snapshots (
                    snapshot_id, canonical_scheme_id, snapshot_date,
                    existence_status, confidence, derived_from_events,
                    methodology_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_scheme_id, snapshot_date, methodology_version)
                DO UPDATE SET
                    existence_status = excluded.existence_status,
                    confidence = excluded.confidence,
                    derived_from_events = excluded.derived_from_events,
                    created_at = excluded.created_at
                """,
                (
                    snapshot_id,
                    canonical_scheme_id,
                    snapshot_date.isoformat(),
                    existence_status,
                    confidence,
                    json.dumps(derived_from_events),
                    methodology_version,
                    created_at,
                ),
            )

    def get_universe_snapshot(
        self,
        canonical_scheme_id: str,
        snapshot_date: date,
        methodology_version: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a derived universe snapshot by key."""
        with self.db.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM scheme_universe_snapshots
                WHERE canonical_scheme_id = ? AND snapshot_date = ? AND methodology_version = ?
                """,
                (canonical_scheme_id, snapshot_date.isoformat(), methodology_version),
            )
            row = cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        result["derived_from_events"] = json.loads(result.get("derived_from_events", "[]"))
        return result

    def get_active_universe_for_date(
        self,
        snapshot_date: date,
        methodology_version: str,
        minimum_confidence: str = "LOW",
    ) -> List[Dict[str, Any]]:
        """
        Return all schemes with existence_status = 'ACTIVE' as of snapshot_date,
        for a given methodology version.

        This is the anti-survivorship-bias query.  It returns schemes that
        EXISTED on snapshot_date including those later merged or closed.

        minimum_confidence filters out snapshots below the requested quality threshold.
        Confidence ordering: HIGH > MEDIUM > LOW.
        """
        confidence_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_level = confidence_order.get(minimum_confidence, 1)

        with self.db.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM scheme_universe_snapshots
                WHERE snapshot_date = ?
                  AND existence_status = 'ACTIVE'
                  AND methodology_version = ?
                ORDER BY canonical_scheme_id
                """,
                (snapshot_date.isoformat(), methodology_version),
            )
            rows = cursor.fetchall()

        results = []
        for row in rows:
            d = dict(row)
            conf_level = confidence_order.get(d.get("confidence", "LOW"), 1)
            if conf_level >= min_level:
                d["derived_from_events"] = json.loads(d.get("derived_from_events", "[]"))
                results.append(d)
        return results

    def delete_snapshots_for_methodology(self, methodology_version: str) -> int:
        """
        Delete all derived universe snapshots for a methodology version.
        Use when rebuilding snapshots after a methodology version update.
        Source lifecycle events are NOT affected.
        """
        with self.db.get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM scheme_universe_snapshots WHERE methodology_version = ?",
                (methodology_version,),
            )
            return cursor.rowcount

    # ------------------------------------------------------------------
    # Canonical Scheme Lifecycle State Updates
    # ------------------------------------------------------------------

    def update_canonical_scheme_lifecycle_state(
        self,
        canonical_scheme_id: str,
        lifecycle_status: str,
        scheme_start_date: Optional[str],
        scheme_end_date: Optional[str],
        last_lifecycle_event_id: str,
    ) -> None:
        """
        Update the lifecycle state columns on canonical_schemes.
        Also updates is_active for backward compatibility with Slice 1/2 code.
        """
        is_active = 1 if lifecycle_status == "ACTIVE" else 0
        updated_at = datetime.now(timezone.utc).isoformat()

        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE canonical_schemes
                SET lifecycle_status = ?,
                    scheme_start_date = ?,
                    scheme_end_date = ?,
                    is_active = ?,
                    last_lifecycle_event_id = ?,
                    last_lifecycle_updated_at = ?
                WHERE canonical_scheme_id = ?
                """,
                (
                    lifecycle_status,
                    scheme_start_date,
                    scheme_end_date,
                    is_active,
                    last_lifecycle_event_id,
                    updated_at,
                    canonical_scheme_id,
                ),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_to_event(self, row: Dict[str, Any]) -> LifecycleEvent:
        """Deserialize a database row into a LifecycleEvent dataclass."""
        return LifecycleEvent(
            event_id=row["event_id"],
            canonical_scheme_id=row["canonical_scheme_id"],
            event_type=LifecycleEventType(row["event_type"]),
            effective_date=date.fromisoformat(row["effective_date"]),
            effective_date_precision=EffectiveDatePrecision(row["effective_date_precision"]),
            source_id=row["source_id"],
            source_document_url=row.get("source_document_url"),
            retrieval_timestamp_utc=datetime.fromisoformat(row["retrieval_timestamp_utc"]),
            predecessor_scheme_ids=json.loads(row.get("predecessor_scheme_ids", "[]")),
            successor_scheme_ids=json.loads(row.get("successor_scheme_ids", "[]")),
            old_value=row.get("old_value"),
            new_value=row.get("new_value"),
            confidence=LifecycleConfidence(row["confidence"]),
            status=row["status"],
            quarantine_reason=row.get("quarantine_reason"),
            methodology_version=row["methodology_version"],
            notes=row.get("notes"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
        )
