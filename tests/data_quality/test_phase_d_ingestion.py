"""
Phase D Lifecycle Ingestion Test Suite — Controlled Seed Ingestion.

Verifies the 6-stage lifecycle ingestion pipeline and seed dataset against
governing requirements (MD-1 through MD-5, provenance, confidence, quarantine,
idempotency, and Phase C regression).
"""

import pytest
from datetime import date, datetime, timezone
import json

from db.database import DatabaseConnection
from data.repositories.lifecycle_repository import LifecycleRepository
from data.mapping.lifecycle_resolver import LifecycleResolver
from data.ingestion.lifecycle_ingestion_pipeline import (
    LifecycleIngestionPipeline,
    RawLifecycleDocument,
    CandidateLifecycleEvent,
    AmfiCorroborator,
)
from data.ingestion.seed_lifecycle_data import (
    ingest_phase_d_seed_dataset,
    get_phase_d_seed_documents,
)
from models.scheme_lifecycle import (
    LifecycleEvent,
    LifecycleEventType,
    LifecycleConfidence,
    EffectiveDatePrecision,
    ExistenceStatus,
)


@pytest.fixture
def test_db():
    """In-memory SQLite database fixture initialized with schema and sources."""
    db = DatabaseConnection(":memory:")
    with db.get_conn() as conn:
        for sid, sname, stype, auth in [
            ("AMFI_OFFICIAL", "AMFI Official Portal", "API", "Level 1 (Primary Industry Body)"),
            ("SEBI_OFFICIAL", "SEBI Official Portal", "Regulatory", "Level 2 (Statutory Regulator)"),
            ("AMC_STATUTORY_DISCLOSURE", "AMC Statutory Disclosures", "Statutory Notice", "Level 5 (Issuing AMC)"),
        ]:
            conn.execute(
                """
                INSERT OR IGNORE INTO source_registry (
                    source_id, source_name, source_type, authority_level,
                    official_url, specific_data_url, supported_data_fields,
                    update_frequency, historical_availability, free_status,
                    licensing_status, validation_status
                ) VALUES (?, ?, ?, ?, 'https://example.com', 'https://example.com', '[]', 'Daily', 'High', 1, 'Free', 'VALIDATED')
                """,
                (sid, sname, stype, auth),
            )
    return db


@pytest.fixture
def repository(test_db):
    return LifecycleRepository(test_db)


@pytest.fixture
def pipeline(test_db, repository):
    corroborator = AmfiCorroborator(test_db)
    return LifecycleIngestionPipeline(repository=repository, corroborator=corroborator)


def test_01_merger_extraction(test_db, repository, pipeline):
    """1. Test scheme merger extraction and resolution."""
    events = ingest_phase_d_seed_dataset(pipeline)
    merger_events = [e for e in events if e.event_type == LifecycleEventType.SCHEME_MERGED_INTO]

    assert len(merger_events) == 1
    ev = merger_events[0]
    assert ev.canonical_scheme_id == "sch_102345"
    assert ev.effective_date == date(2018, 5, 18)
    assert ev.effective_date_precision == EffectiveDatePrecision.DAY
    assert ev.confidence == LifecycleConfidence.HIGH
    assert ev.status == "ACTIVE"
    assert "SOURCE-DOCUMENT FACT:" in ev.notes
    assert "EMPIRICAL AMFI OBSERVATION:" in ev.notes
    assert "PLATFORM INFERENCE:" in ev.notes


def test_02_rename_extraction(test_db, repository, pipeline):
    """2. Test scheme rename extraction."""
    events = ingest_phase_d_seed_dataset(pipeline)
    rename_events = [e for e in events if e.event_type == LifecycleEventType.SCHEME_RENAMED]

    assert len(rename_events) == 1
    ev = rename_events[0]
    assert ev.canonical_scheme_id == "sch_100346"
    assert ev.old_value == "Reliance Large Cap Fund"
    assert ev.new_value == "Nippon India Large Cap Fund"
    assert ev.effective_date == date(2019, 9, 28)
    assert ev.confidence == LifecycleConfidence.HIGH


def test_03_closure_extraction(test_db, repository, pipeline):
    """3. Test scheme closure extraction."""
    events = ingest_phase_d_seed_dataset(pipeline)
    closure_events = [e for e in events if e.event_type == LifecycleEventType.SCHEME_CLOSED]

    assert len(closure_events) == 1
    ev = closure_events[0]
    assert ev.canonical_scheme_id == "sch_105894"
    assert ev.effective_date == date(2020, 4, 24)
    assert ev.confidence == LifecycleConfidence.HIGH


def test_04_creation_extraction(test_db, repository, pipeline):
    """4. Test scheme creation / NFO extraction."""
    events = ingest_phase_d_seed_dataset(pipeline)
    creation_events = [e for e in events if e.event_type == LifecycleEventType.SCHEME_CREATION]

    assert len(creation_events) == 2
    ev = [e for e in creation_events if e.canonical_scheme_id == "sch_149231"][0]
    assert ev.effective_date == date(2021, 12, 20)
    assert ev.confidence == LifecycleConfidence.HIGH


def test_05_plan_option_change_extraction(test_db, repository, pipeline):
    """5. Test plan/option change extraction."""
    events = ingest_phase_d_seed_dataset(pipeline)
    plan_events = [e for e in events if e.event_type == LifecycleEventType.PLAN_TYPE_CHANGED]

    assert len(plan_events) == 1
    ev = plan_events[0]
    assert ev.canonical_scheme_id == "sch_119061"
    assert ev.effective_date == date(2013, 1, 1)
    assert ev.old_value == "REGULAR"
    assert ev.new_value == "DIRECT"


def test_06_effective_date_precision_md1(test_db, repository, pipeline):
    """6. Test MD-1 effective date precision storage rules."""
    doc = RawLifecycleDocument(
        document_id="doc_month_precision",
        source_id="SEBI_OFFICIAL",
        source_document_url="https://www.sebi.gov.in",
        retrieval_timestamp_utc=datetime.now(timezone.utc),
        raw_content="Scheme merger effective March 2018.",
    )
    candidate = CandidateLifecycleEvent(
        source_document_id="doc_month_precision",
        raw_amfi_code="101111",
        event_type_str="SCHEME_MERGED_INTO",
        effective_date_str="2018-03-15",  # Raw text date in mid-month
        effective_date_precision_str="MONTH",
        source_document_fact="Merger effective March 2018.",
    )
    events = pipeline.process_document(doc, [candidate])
    ev = events[0]

    assert ev.effective_date_precision == EffectiveDatePrecision.MONTH
    # MD-1 requirement: Month precision must store YYYY-MM-01 representation
    assert ev.effective_date == date(2018, 3, 1)


def test_07_source_provenance(test_db, repository, pipeline):
    """7. Test mandatory source provenance parameters."""
    events = ingest_phase_d_seed_dataset(pipeline)
    for ev in events:
        assert ev.source_id is not None and len(ev.source_id) > 0
        assert ev.retrieval_timestamp_utc is not None
        assert ev.methodology_version == "1.0.0"


def test_08_amfi_corroboration(test_db, repository, pipeline):
    """8. Test AMFI empirical corroborator boundary check."""
    corroborator = AmfiCorroborator(test_db)

    # Insert raw NAV observations into test_db for scheme 102345
    with test_db.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO raw_nav_observations (raw_record_id, source_id, retrieval_timestamp, raw_scheme_code, raw_scheme_name, raw_nav_value, raw_date)
            VALUES ('raw_1', 'AMFI_OFFICIAL', '2026-09-08T00:00:00', '102345', 'SBI Horizon Fund', '10.0', '2018-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO raw_nav_observations (raw_record_id, source_id, retrieval_timestamp, raw_scheme_code, raw_scheme_name, raw_nav_value, raw_date)
            VALUES ('raw_2', 'AMFI_OFFICIAL', '2026-09-08T00:00:00', '102345', 'SBI Horizon Fund', '12.5', '2018-05-17')
            """
        )

    res = corroborator.corroborate_event(
        amfi_code="102345",
        event_type=LifecycleEventType.SCHEME_MERGED_INTO,
        effective_date=date(2018, 5, 18),
        effective_date_precision=EffectiveDatePrecision.DAY,
    )

    assert res.boundary_consistent is True
    assert res.first_observed_nav_date == date(2018, 1, 1)
    assert res.last_observed_nav_date == date(2018, 5, 17)


def test_09_confidence_assignment(test_db, repository, pipeline):
    """9. Test confidence grading logic."""
    events = ingest_phase_d_seed_dataset(pipeline)
    active_events = [e for e in events if e.status == "ACTIVE"]

    for ev in active_events:
        assert ev.confidence in (LifecycleConfidence.HIGH, LifecycleConfidence.MEDIUM, LifecycleConfidence.LOW)


def test_10_quarantine(test_db, repository, pipeline):
    """10. Test quarantine handling for ambiguous / unverified events."""
    events = ingest_phase_d_seed_dataset(pipeline)
    quarantined = [e for e in events if e.status == "QUARANTINED"]

    assert len(quarantined) == 1
    ev = quarantined[0]
    assert ev.confidence == LifecycleConfidence.AMBIGUOUS
    assert ev.quarantine_reason is not None
    assert "Quarantined" in ev.quarantine_reason


def test_11_duplicate_idempotent_ingestion(test_db, repository, pipeline):
    """11. Test idempotent ingestion on repeated execution."""
    events_run1 = ingest_phase_d_seed_dataset(pipeline)

    # Re-run ingestion of same seed documents
    events_run2 = ingest_phase_d_seed_dataset(pipeline)

    assert len(events_run1) == len(events_run2)

    # Verify database table contains exactly 7 unique rows (no duplicates)
    with test_db.get_conn() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM scheme_lifecycle_events")
        count = cursor.fetchone()[0]

    assert count == 7


def test_12_md4_no_stitching(test_db, repository, pipeline):
    """12. Test MD-4 invariant: no NAV stitching methods exist on pipeline."""
    assert not hasattr(pipeline, "stitch_nav_series")
    assert not hasattr(pipeline, "concatenate_nav")


def test_13_ambiguous_identity_handling(test_db, repository, pipeline):
    """13. Test ambiguous candidate without scheme identity is quarantined."""
    doc = RawLifecycleDocument(
        document_id="doc_ambiguous",
        source_id="AMC_STATUTORY_DISCLOSURE",
        source_document_url="https://www.sbimf.com",
        retrieval_timestamp_utc=datetime.now(timezone.utc),
        raw_content="Unclear text",
    )
    candidate = CandidateLifecycleEvent(
        source_document_id="doc_ambiguous",
        raw_scheme_name=None,
        raw_amfi_code=None,
        event_type_str="SCHEME_RENAMED",
        effective_date_str="2020-01-01",
    )

    events = pipeline.process_document(doc, [candidate])
    ev = events[0]

    assert ev.status == "QUARANTINED"
    assert ev.confidence == LifecycleConfidence.AMBIGUOUS


def test_14_phase_c_resolver_regression(test_db, repository, pipeline):
    """14. Test Phase C LifecycleResolver integration and regression safety."""
    ingest_phase_d_seed_dataset(pipeline)
    resolver = LifecycleResolver(repository)

    # Resolve SBI Horizon Fund (102345) before merger (2018-01-01) -> ACTIVE
    identity_before = resolver.resolve_scheme_at_date("sch_102345", date(2018, 1, 1))
    assert identity_before.existence_status == ExistenceStatus.ACTIVE

    # Resolve SBI Horizon Fund (102345) after merger (2018-06-01) -> MERGED_PREDECESSOR
    identity_after = resolver.resolve_scheme_at_date("sch_102345", date(2018, 6, 1))
    assert identity_after.existence_status == ExistenceStatus.MERGED_PREDECESSOR

    # Resolve Franklin India Ultra Short Bond (105894) after closure (2020-05-01) -> CLOSED
    identity_closed = resolver.resolve_scheme_at_date("sch_105894", date(2020, 5, 1))
    assert identity_closed.existence_status == ExistenceStatus.CLOSED
