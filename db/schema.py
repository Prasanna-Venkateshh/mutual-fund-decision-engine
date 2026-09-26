"""
SQLite DDL Schema definition for Mutual Fund Decision Engine database.

Implements normalized tables for source metadata, raw observations, canonical schemes,
mappings, normalized NAV records, quarantine records, and (Phase C) scheme lifecycle events
as specified in ARCHITECTURE.md Section 10.

Phase C Additions (2026-09-08):
- scheme_lifecycle_events: Immutable append-only source of truth for lifecycle events.
- scheme_universe_snapshots: DERIVED/REBUILDABLE data — not source truth.
  If methodology version changes, snapshots must be recomputed from lifecycle events.
- canonical_schemes: Extended with lifecycle state columns (scheme_start_date,
  scheme_end_date, lifecycle_status, last_lifecycle_event_id, last_lifecycle_updated_at)
  using DEFAULT values for backward compatibility with existing rows/code.

Schema Design Principles:
- scheme_lifecycle_events and canonical_schemes are SOURCE DATA.
- scheme_universe_snapshots is DERIVED DATA, keyed on
  (canonical_scheme_id, snapshot_date, methodology_version) so snapshots from
  different methodology versions can coexist and be rebuilt without losing source truth.
- The existing is_active column on canonical_schemes is retained for Slice 1/2 backward
  compatibility. lifecycle_status provides finer-grained Phase C state.
"""

CREATE_TABLES_SQL = """
-- Central Source Registry Table
CREATE TABLE IF NOT EXISTS source_registry (
    source_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    authority_level TEXT NOT NULL,
    official_url TEXT NOT NULL,
    specific_data_url TEXT NOT NULL,
    supported_data_fields TEXT NOT NULL, -- JSON array
    update_frequency TEXT NOT NULL,
    historical_availability TEXT NOT NULL,
    free_status INTEGER NOT NULL DEFAULT 1,
    licensing_status TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    last_successful_retrieval TEXT,
    last_validation_date TEXT
);

-- Canonical Scheme Master Table
-- Phase C adds lifecycle state columns with DEFAULT values for backward compatibility.
-- is_active (Slice 1, BOOLEAN) is preserved; lifecycle_status (Phase C) provides finer state.
-- lifecycle_status DEFAULT 'UNKNOWN' because newly ingested schemes have no lifecycle
-- evidence yet — conservatively UNKNOWN rather than assuming ACTIVE.
CREATE TABLE IF NOT EXISTS canonical_schemes (
    canonical_scheme_id TEXT PRIMARY KEY,
    amc_name TEXT NOT NULL,
    scheme_name TEXT NOT NULL,
    clean_scheme_name TEXT NOT NULL,
    plan_type TEXT NOT NULL,
    option_type TEXT NOT NULL,
    category TEXT NOT NULL,
    sub_category TEXT NOT NULL,
    primary_amfi_code TEXT,
    isin_growth TEXT,
    isin_reinvest TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    -- Phase C lifecycle columns (all nullable / defaulted for backward compat)
    scheme_start_date TEXT DEFAULT NULL,
    scheme_end_date TEXT DEFAULT NULL,
    lifecycle_status TEXT NOT NULL DEFAULT 'UNKNOWN'
        CHECK(lifecycle_status IN ('ACTIVE','MERGED_PREDECESSOR','CLOSED','UNKNOWN')),
    last_lifecycle_event_id TEXT DEFAULT NULL,
    last_lifecycle_updated_at TEXT DEFAULT NULL
);

-- Scheme Mapping Lookup Table
CREATE TABLE IF NOT EXISTS scheme_mappings (
    mapping_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_scheme_code TEXT NOT NULL,
    source_scheme_name TEXT NOT NULL,
    canonical_scheme_id TEXT,
    confidence TEXT NOT NULL,
    notes TEXT,
    mapped_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES source_registry(source_id),
    FOREIGN KEY (canonical_scheme_id) REFERENCES canonical_schemes(canonical_scheme_id)
);

-- Raw NAV Observations Table (Preserves unparsed historical raw data)
CREATE TABLE IF NOT EXISTS raw_nav_observations (
    raw_record_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    retrieval_timestamp TEXT NOT NULL,
    raw_scheme_code TEXT NOT NULL,
    raw_scheme_name TEXT NOT NULL,
    raw_nav_value TEXT NOT NULL,
    raw_date TEXT NOT NULL,
    raw_line_number INTEGER,
    additional_metadata TEXT, -- JSON
    FOREIGN KEY (source_id) REFERENCES source_registry(source_id)
);

-- Normalized NAV Records Table
CREATE TABLE IF NOT EXISTS normalized_nav_records (
    nav_id TEXT PRIMARY KEY,
    canonical_scheme_id TEXT NOT NULL,
    nav_date TEXT NOT NULL,
    nav_value REAL NOT NULL,
    source_id TEXT NOT NULL,
    raw_record_id TEXT NOT NULL,
    retrieval_timestamp TEXT NOT NULL,
    quality_state TEXT NOT NULL,
    FOREIGN KEY (canonical_scheme_id) REFERENCES canonical_schemes(canonical_scheme_id),
    FOREIGN KEY (source_id) REFERENCES source_registry(source_id),
    FOREIGN KEY (raw_record_id) REFERENCES raw_nav_observations(raw_record_id),
    UNIQUE(canonical_scheme_id, nav_date, source_id)
);

-- Quarantine Table for Malformed / Ambiguous NAV Observations
CREATE TABLE IF NOT EXISTS quarantine_records (
    quarantine_id TEXT PRIMARY KEY,
    raw_record_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    quarantined_at TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    FOREIGN KEY (raw_record_id) REFERENCES raw_nav_observations(raw_record_id),
    FOREIGN KEY (source_id) REFERENCES source_registry(source_id)
);

-- Fund Metric Observations Table (Slice 2 Metric Engine Persistence)
CREATE TABLE IF NOT EXISTS fund_metric_observations (
    metric_id TEXT PRIMARY KEY,
    canonical_scheme_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    observation_count INTEGER NOT NULL,
    confidence_state TEXT NOT NULL,
    calculation_timestamp TEXT NOT NULL,
    methodology_version TEXT NOT NULL,
    notes TEXT,
    metadata_json TEXT, -- JSON
    FOREIGN KEY (canonical_scheme_id) REFERENCES canonical_schemes(canonical_scheme_id),
    UNIQUE(canonical_scheme_id, metric_name, start_date, end_date)
);

-- Acquisition Coverage Ledger Table (Phase B.2 Resumable Historical Pipeline)
CREATE TABLE IF NOT EXISTS acquisition_coverage_ledger (
    window_id TEXT PRIMARY KEY,
    acquisition_run_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    requested_start_date TEXT NOT NULL,
    requested_end_date TEXT NOT NULL,
    retrieval_timestamp_utc TEXT NOT NULL,
    endpoint_url TEXT NOT NULL,
    http_status INTEGER NOT NULL,
    request_status TEXT NOT NULL,
    raw_records_count INTEGER NOT NULL DEFAULT 0,
    nav_valid_records_count INTEGER NOT NULL DEFAULT 0,
    nav_quarantine_count INTEGER NOT NULL DEFAULT 0,
    mapping_quarantine_count INTEGER NOT NULL DEFAULT 0,
    normalized_records_count INTEGER NOT NULL DEFAULT 0,
    earliest_returned_date TEXT,
    latest_returned_date TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_info TEXT,
    completion_status TEXT NOT NULL DEFAULT 'COMPLETED',
    response_hash TEXT,
    FOREIGN KEY (source_id) REFERENCES source_registry(source_id)
);

-- ============================================================
-- Phase C: Scheme Lifecycle Events Table
-- ============================================================
-- Immutable append-only source of truth for lifecycle events.
-- Every event must carry mandatory source provenance and methodology version.
-- Quarantined events (status='QUARANTINED') must never be used in
-- point-in-time universe construction or metric calculations.
--
-- Identity key: canonical_scheme_id (NOT ISIN).
-- Predecessor/successor relationships encoded as JSON arrays to support
-- both 1:1 and N:1 merger scenarios.
--
-- Effective date precision (MD-1):
--   effective_date_precision = DAY   -> actual date stored
--   effective_date_precision = MONTH -> YYYY-MM-01 stored (storage representation only)
--   effective_date_precision = YEAR  -> YYYY-01-01 stored (storage representation only)
--   Downstream callers MUST respect effective_date_precision.
-- ============================================================
CREATE TABLE IF NOT EXISTS scheme_lifecycle_events (
    event_id                TEXT PRIMARY KEY,
    canonical_scheme_id     TEXT NOT NULL,
    event_type              TEXT NOT NULL CHECK(event_type IN (
                                'SCHEME_CREATION', 'SCHEME_RENAMED',
                                'SCHEME_MERGED_INTO', 'SCHEME_RECEIVED_MERGER',
                                'SCHEME_CLOSED', 'PLAN_TYPE_CHANGED',
                                'OPTION_TYPE_CHANGED', 'AMC_REBRANDING',
                                'AMFI_CODE_REASSIGNED', 'ISIN_CHANGED'
                            )),
    effective_date          TEXT NOT NULL,
    effective_date_precision TEXT NOT NULL CHECK(effective_date_precision IN ('DAY','MONTH','YEAR')),
    source_id               TEXT NOT NULL,
    source_document_url     TEXT,
    retrieval_timestamp_utc TEXT NOT NULL,
    predecessor_scheme_ids  TEXT NOT NULL DEFAULT '[]',
    successor_scheme_ids    TEXT NOT NULL DEFAULT '[]',
    old_value               TEXT,
    new_value               TEXT,
    confidence              TEXT NOT NULL CHECK(confidence IN ('HIGH','MEDIUM','LOW','AMBIGUOUS')),
    status                  TEXT NOT NULL CHECK(status IN ('ACTIVE','QUARANTINED')),
    quarantine_reason       TEXT,
    methodology_version     TEXT NOT NULL,
    notes                   TEXT,
    created_at              TEXT NOT NULL,
    FOREIGN KEY (canonical_scheme_id) REFERENCES canonical_schemes(canonical_scheme_id),
    FOREIGN KEY (source_id) REFERENCES source_registry(source_id)
);

-- ============================================================
-- Phase C: Scheme Universe Snapshots Table
-- ============================================================
-- DERIVED / REBUILDABLE data — NOT source truth.
-- Stores point-in-time existence state derived from lifecycle events.
-- If methodology_version changes, snapshots must be recomputed.
-- Unique constraint includes methodology_version so multiple versions coexist.
-- ============================================================
CREATE TABLE IF NOT EXISTS scheme_universe_snapshots (
    snapshot_id             TEXT PRIMARY KEY,
    canonical_scheme_id     TEXT NOT NULL,
    snapshot_date           TEXT NOT NULL,
    existence_status        TEXT NOT NULL CHECK(existence_status IN (
                                'ACTIVE', 'MERGED_PREDECESSOR', 'CLOSED',
                                'PRE_LAUNCH', 'UNKNOWN', 'AMBIGUOUS'
                            )),
    confidence              TEXT NOT NULL CHECK(confidence IN ('HIGH','MEDIUM','LOW')),
    derived_from_events     TEXT NOT NULL DEFAULT '[]',
    methodology_version     TEXT NOT NULL,
    created_at              TEXT NOT NULL,
    FOREIGN KEY (canonical_scheme_id) REFERENCES canonical_schemes(canonical_scheme_id),
    UNIQUE(canonical_scheme_id, snapshot_date, methodology_version)
);

-- ============================================================
-- Indexes — Existing (Slice 1 / Phase B.2)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_raw_nav_source ON raw_nav_observations(source_id, raw_scheme_code);
CREATE INDEX IF NOT EXISTS idx_norm_nav_scheme_date ON normalized_nav_records(canonical_scheme_id, nav_date);
CREATE INDEX IF NOT EXISTS idx_scheme_mapping_lookup ON scheme_mappings(source_id, source_scheme_code);
CREATE INDEX IF NOT EXISTS idx_metric_scheme_name ON fund_metric_observations(canonical_scheme_id, metric_name);
CREATE INDEX IF NOT EXISTS idx_ledger_source_dates ON acquisition_coverage_ledger(source_id, requested_start_date, requested_end_date);
CREATE INDEX IF NOT EXISTS idx_ledger_status ON acquisition_coverage_ledger(request_status);

-- ============================================================
-- Indexes — Phase C
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_lifecycle_scheme_date
    ON scheme_lifecycle_events(canonical_scheme_id, effective_date);
CREATE INDEX IF NOT EXISTS idx_lifecycle_type_status
    ON scheme_lifecycle_events(event_type, status);
CREATE INDEX IF NOT EXISTS idx_lifecycle_confidence_status
    ON scheme_lifecycle_events(confidence, status);
CREATE INDEX IF NOT EXISTS idx_universe_snapshot_date
    ON scheme_universe_snapshots(snapshot_date, existence_status);
CREATE INDEX IF NOT EXISTS idx_universe_snapshot_scheme
    ON scheme_universe_snapshots(canonical_scheme_id, snapshot_date);
"""


# ---------------------------------------------------------------------------
# Phase C migration for EXISTING databases.
# Applied by DatabaseConnection._apply_lifecycle_migration().
# Each ALTER TABLE statement is attempted individually; if the column already
# exists (OperationalError), that statement is silently skipped.
# ---------------------------------------------------------------------------
LIFECYCLE_MIGRATION_SQL_COLUMNS = [
    "ALTER TABLE canonical_schemes ADD COLUMN scheme_start_date TEXT DEFAULT NULL",
    "ALTER TABLE canonical_schemes ADD COLUMN scheme_end_date TEXT DEFAULT NULL",
    "ALTER TABLE canonical_schemes ADD COLUMN lifecycle_status TEXT NOT NULL DEFAULT 'UNKNOWN'",
    "ALTER TABLE canonical_schemes ADD COLUMN last_lifecycle_event_id TEXT DEFAULT NULL",
    "ALTER TABLE canonical_schemes ADD COLUMN last_lifecycle_updated_at TEXT DEFAULT NULL",
]
