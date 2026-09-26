"""
NAV Data Repository Layer (data/repositories/).

Provides database access operations for raw observations, scheme mappings,
canonical schemes, normalized NAV records, and quarantine records.
Enforces immutable preservation of raw historical observations.
"""

import json
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from models.nav_data import RawNAVRecord, NormalizedNAVRecord, QuarantineRecord, DataQualityState
from models.scheme import CanonicalScheme, SchemeMapping, PlanType, OptionType, MappingConfidence
from db.database import DatabaseConnection


class NAVRepository:
    """Repository handling database operations for NAV data structures."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def save_window_atomic(
        self,
        raw_records: List[RawNAVRecord],
        canonical_schemes: List[CanonicalScheme],
        mappings: List[SchemeMapping],
        normalized_records: List[NormalizedNAVRecord],
        quarantine_records: List[QuarantineRecord],
        ledger_entry: Dict[str, Any]
    ) -> None:
        """Persist all artifacts for an acquisition window in a single atomic transaction context."""
        with self.db.get_conn() as conn:
            # Write-performance PRAGMAs for bulk inserts (~10K rows/window).
            # FK enforcement is structurally guaranteed by insertion order (raw → canonical → norm).
            conn.execute("PRAGMA foreign_keys = OFF;")
            conn.execute("PRAGMA cache_size = -32000;")   # 32 MB page cache
            conn.execute("PRAGMA temp_store = MEMORY;")

            # 1. Raw Observations
            if raw_records:
                raw_data = [
                    (
                        r.raw_record_id, r.source_id, r.retrieval_timestamp.isoformat(),
                        r.raw_scheme_code, r.raw_scheme_name, r.raw_nav_value,
                        r.raw_date, r.raw_line_number,
                        json.dumps(r.additional_metadata) if r.additional_metadata else None
                    )
                    for r in raw_records
                ]
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO raw_nav_observations (
                        raw_record_id, source_id, retrieval_timestamp,
                        raw_scheme_code, raw_scheme_name, raw_nav_value,
                        raw_date, raw_line_number, additional_metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    raw_data
                )

            # 2. Canonical Schemes
            if canonical_schemes:
                cs_data = [
                    (
                        s.canonical_scheme_id, s.amc_name, s.scheme_name,
                        s.clean_scheme_name, s.plan_type.value, s.option_type.value,
                        s.category, s.sub_category, s.primary_amfi_code,
                        s.isin_growth, s.isin_reinvest, 1 if s.is_active else 0,
                        s.created_at.isoformat() if s.created_at else datetime.utcnow().isoformat()
                    )
                    for s in canonical_schemes
                ]
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO canonical_schemes (
                        canonical_scheme_id, amc_name, scheme_name, clean_scheme_name,
                        plan_type, option_type, category, sub_category,
                        primary_amfi_code, isin_growth, isin_reinvest, is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    cs_data
                )

            # 3. Mappings
            if mappings:
                m_data = [
                    (
                        m.mapping_id, m.source_id, m.source_scheme_code,
                        m.source_scheme_name, m.canonical_scheme_id,
                        m.confidence.value, m.notes,
                        m.mapped_at.isoformat() if m.mapped_at else datetime.utcnow().isoformat()
                    )
                    for m in mappings
                ]
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO scheme_mappings (
                        mapping_id, source_id, source_scheme_code, source_scheme_name,
                        canonical_scheme_id, confidence, notes, mapped_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    m_data
                )

            # 4. Normalized Records
            if normalized_records:
                norm_data = [
                    (
                        r.nav_id, r.canonical_scheme_id, r.nav_date.isoformat(),
                        r.nav_value, r.source_id, r.raw_record_id,
                        r.retrieval_timestamp.isoformat(), r.quality_state.value
                    )
                    for r in normalized_records
                ]
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO normalized_nav_records (
                        nav_id, canonical_scheme_id, nav_date, nav_value,
                        source_id, raw_record_id, retrieval_timestamp, quality_state
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    norm_data
                )

            # 5. Quarantine Records
            if quarantine_records:
                q_data = [
                    (
                        q.quarantine_id, q.raw_record_id, q.source_id,
                        q.reason, q.quarantined_at.isoformat(), q.raw_payload
                    )
                    for q in quarantine_records
                ]
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO quarantine_records (
                        quarantine_id, raw_record_id, source_id, reason,
                        quarantined_at, raw_payload
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    q_data
                )

            # 6. Ledger Entry
            if ledger_entry:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO acquisition_coverage_ledger (
                        window_id, acquisition_run_id, source_id, requested_start_date,
                        requested_end_date, retrieval_timestamp_utc, endpoint_url,
                        http_status, request_status, raw_records_count,
                        nav_valid_records_count, nav_quarantine_count,
                        mapping_quarantine_count, normalized_records_count,
                        earliest_returned_date, latest_returned_date, retry_count,
                        error_info, completion_status, response_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ledger_entry["window_id"], ledger_entry["acquisition_run_id"], ledger_entry["source_id"],
                        ledger_entry["requested_start_date"], ledger_entry["requested_end_date"],
                        ledger_entry["retrieval_timestamp_utc"], ledger_entry["endpoint_url"],
                        ledger_entry["http_status"], ledger_entry["request_status"],
                        ledger_entry["raw_records_count"], ledger_entry["nav_valid_records_count"],
                        ledger_entry["nav_quarantine_count"], ledger_entry["mapping_quarantine_count"],
                        ledger_entry["normalized_records_count"], ledger_entry["earliest_returned_date"],
                        ledger_entry["latest_returned_date"], ledger_entry["retry_count"],
                        ledger_entry["error_info"], ledger_entry["completion_status"],
                        ledger_entry["response_hash"]
                    )
                )


    def save_raw_observations(self, records: List[RawNAVRecord]) -> int:
        """
        Persist raw observations into database using executemany batch insertion.
        Uses INSERT OR IGNORE to guarantee historical raw observations are never silently overwritten.
        """
        if not records:
            return 0
        data = [
            (
                r.raw_record_id, r.source_id, r.retrieval_timestamp.isoformat(),
                r.raw_scheme_code, r.raw_scheme_name, r.raw_nav_value,
                r.raw_date, r.raw_line_number,
                json.dumps(r.additional_metadata) if r.additional_metadata else None
            )
            for r in records
        ]
        with self.db.get_conn() as conn:
            cursor = conn.executemany(
                """
                INSERT OR IGNORE INTO raw_nav_observations (
                    raw_record_id, source_id, retrieval_timestamp,
                    raw_scheme_code, raw_scheme_name, raw_nav_value,
                    raw_date, raw_line_number, additional_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            return cursor.rowcount

    def save_canonical_schemes_batch(self, schemes: List[CanonicalScheme]) -> int:
        """Persist or update multiple CanonicalScheme entities using executemany batch insertion."""
        if not schemes:
            return 0
        data = [
            (
                s.canonical_scheme_id, s.amc_name, s.scheme_name,
                s.clean_scheme_name, s.plan_type.value, s.option_type.value,
                s.category, s.sub_category, s.primary_amfi_code,
                s.isin_growth, s.isin_reinvest, 1 if s.is_active else 0,
                s.created_at.isoformat() if s.created_at else datetime.utcnow().isoformat()
            )
            for s in schemes
        ]
        with self.db.get_conn() as conn:
            cursor = conn.executemany(
                """
                INSERT OR REPLACE INTO canonical_schemes (
                    canonical_scheme_id, amc_name, scheme_name, clean_scheme_name,
                    plan_type, option_type, category, sub_category,
                    primary_amfi_code, isin_growth, isin_reinvest, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            return cursor.rowcount

    def save_scheme_mappings_batch(self, mappings: List[SchemeMapping]) -> int:
        """Persist or update multiple SchemeMapping records using executemany batch insertion."""
        if not mappings:
            return 0
        data = [
            (
                m.mapping_id, m.source_id, m.source_scheme_code,
                m.source_scheme_name, m.canonical_scheme_id,
                m.confidence.value, m.notes,
                m.mapped_at.isoformat() if m.mapped_at else datetime.utcnow().isoformat()
            )
            for m in mappings
        ]
        with self.db.get_conn() as conn:
            cursor = conn.executemany(
                """
                INSERT OR REPLACE INTO scheme_mappings (
                    mapping_id, source_id, source_scheme_code, source_scheme_name,
                    canonical_scheme_id, confidence, notes, mapped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            return cursor.rowcount

    def save_canonical_scheme(self, scheme: CanonicalScheme) -> int:
        """Convenience wrapper to persist a single CanonicalScheme."""
        return self.save_canonical_schemes_batch([scheme])

    def save_scheme_mapping(self, mapping: SchemeMapping) -> int:
        """Convenience wrapper to persist a single SchemeMapping."""
        return self.save_scheme_mappings_batch([mapping])

    def save_normalized_records(self, records: List[NormalizedNAVRecord]) -> int:
        """Persist normalized NAV records into database using executemany."""
        if not records:
            return 0
        data = [
            (
                r.nav_id, r.canonical_scheme_id, r.nav_date.isoformat(),
                r.nav_value, r.source_id, r.raw_record_id,
                r.retrieval_timestamp.isoformat(), r.quality_state.value
            )
            for r in records
        ]
        with self.db.get_conn() as conn:
            cursor = conn.executemany(
                """
                INSERT OR REPLACE INTO normalized_nav_records (
                    nav_id, canonical_scheme_id, nav_date, nav_value,
                    source_id, raw_record_id, retrieval_timestamp, quality_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            return cursor.rowcount

    def save_quarantine_records(self, records: List[QuarantineRecord]) -> int:
        """Persist quarantine records into database using executemany."""
        if not records:
            return 0
        data = [
            (
                q.quarantine_id, q.raw_record_id, q.source_id,
                q.reason, q.quarantined_at.isoformat(), q.raw_payload
            )
            for q in records
        ]
        with self.db.get_conn() as conn:
            cursor = conn.executemany(
                """
                INSERT OR REPLACE INTO quarantine_records (
                    quarantine_id, raw_record_id, source_id, reason,
                    quarantined_at, raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                data
            )
            return cursor.rowcount

    def get_normalized_nav_history(self, canonical_scheme_id: str) -> List[Dict[str, Any]]:
        """Retrieve historical normalized NAV time-series for a canonical scheme, ordered by date ascending."""
        with self.db.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT nav_id, canonical_scheme_id, nav_date, nav_value, source_id, raw_record_id, quality_state
                FROM normalized_nav_records
                WHERE canonical_scheme_id = ?
                ORDER BY nav_date ASC
                """,
                (canonical_scheme_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_quarantine_count(self) -> int:
        """Get total count of quarantined records."""
        with self.db.get_conn() as conn:
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM quarantine_records")
            return cursor.fetchone()["cnt"]

    def save_ledger_entry(self, entry: Dict[str, Any]) -> None:
        """Persist or update an acquisition coverage ledger record."""
        with self.db.get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO acquisition_coverage_ledger (
                    window_id, acquisition_run_id, source_id, requested_start_date,
                    requested_end_date, retrieval_timestamp_utc, endpoint_url, http_status,
                    request_status, raw_records_count, nav_valid_records_count,
                    nav_quarantine_count, mapping_quarantine_count, normalized_records_count,
                    earliest_returned_date, latest_returned_date, retry_count, error_info,
                    completion_status, response_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["window_id"], entry["acquisition_run_id"], entry["source_id"],
                    entry["requested_start_date"], entry["requested_end_date"],
                    entry["retrieval_timestamp_utc"], entry["endpoint_url"],
                    entry["http_status"], entry["request_status"],
                    entry.get("raw_records_count", 0), entry.get("nav_valid_records_count", 0),
                    entry.get("nav_quarantine_count", 0), entry.get("mapping_quarantine_count", 0),
                    entry.get("normalized_records_count", 0), entry.get("earliest_returned_date"),
                    entry.get("latest_returned_date"), entry.get("retry_count", 0),
                    entry.get("error_info"), entry.get("completion_status", "COMPLETED"),
                    entry.get("response_hash")
                )
            )

    def get_ledger_entry(self, window_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a ledger entry by window ID."""
        with self.db.get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM acquisition_coverage_ledger WHERE window_id = ?",
                (window_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_ledger_entries(self, source_id: str = "AMFI_OFFICIAL") -> List[Dict[str, Any]]:
        """List all ledger entries for a given source ordered by requested start date ascending."""
        with self.db.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM acquisition_coverage_ledger 
                WHERE source_id = ? 
                ORDER BY requested_start_date ASC
                """,
                (source_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_raw_observations(self, source_id: str = "AMFI_OFFICIAL", raw_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve raw observations from database."""
        with self.db.get_conn() as conn:
            if raw_date:
                cursor = conn.execute(
                    "SELECT * FROM raw_nav_observations WHERE source_id = ? AND raw_date = ?",
                    (source_id, raw_date)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM raw_nav_observations WHERE source_id = ?",
                    (source_id,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_quarantine_records(self, stage: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve quarantine records from database."""
        with self.db.get_conn() as conn:
            if stage == "NAV_VALIDATION":
                cursor = conn.execute("SELECT * FROM quarantine_records WHERE quarantine_id NOT LIKE 'quarantine_map_%'")
            elif stage == "SCHEME_MAPPING":
                cursor = conn.execute("SELECT * FROM quarantine_records WHERE quarantine_id LIKE 'quarantine_map_%'")
            else:
                cursor = conn.execute("SELECT * FROM quarantine_records")
            return [dict(row) for row in cursor.fetchall()]



