"""
Phase D.3 SEBI 2017 Scale-Up Ingestion & Point-in-Time Test Suite.

Verifies the expanded SEBI 2017 scale-up dataset ingestion, exact reconciliation
accounting, provenance traceability, AMFI corroboration, quarantine handling,
and point-in-time anti-survivorship bias protection.
"""

import pytest
from datetime import date, datetime, timezone

from db.database import DatabaseConnection
from data.repositories.lifecycle_repository import LifecycleRepository
from data.mapping.lifecycle_resolver import LifecycleResolver
from data.ingestion.lifecycle_ingestion_pipeline import (
    LifecycleIngestionPipeline,
    RawLifecycleDocument,
    CandidateLifecycleEvent,
    AmfiCorroborator,
)
from data.ingestion.sebi_2017_scaleup_extractor import (
    execute_sebi_2017_scaleup_ingestion,
    get_sebi_2017_scaleup_candidates,
    SEBI_2017_SCALEUP_SOURCE_METADATA,
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


def test_01_sebi_2017_scaleup_reconciliation_equation(pipeline):
    """1. Test exact batch reconciliation equation: Total = Active + Quarantined + Rejected."""
    events, ledger = execute_sebi_2017_scaleup_ingestion(pipeline)

    assert ledger.total_candidates_processed == 30
    assert ledger.validated_active_events == 25
    assert ledger.quarantined_events == 3
    assert ledger.rejected_non_events == 2
    assert ledger.total_candidates_processed == (
        ledger.validated_active_events + ledger.quarantined_events + ledger.rejected_non_events
    )


def test_02_event_type_distribution(pipeline):
    """2. Test event type distribution breakdown."""
    events, ledger = execute_sebi_2017_scaleup_ingestion(pipeline)

    assert ledger.merger_into_count == 13
    assert ledger.renamed_count == 8
    assert ledger.closed_count == 1
    assert ledger.creation_count == 1
    assert ledger.amc_rebranding_count == 2


def test_03_date_precision_distribution_md1(pipeline):
    """3. Test date precision distribution accounting (MD-1)."""
    events, ledger = execute_sebi_2017_scaleup_ingestion(pipeline)

    assert ledger.precision_day_count == 26
    assert ledger.precision_month_count == 1
    assert ledger.precision_year_count == 1


def test_04_amc_rebranding_event_processing(pipeline):
    """4. Test AMC rebranding event handling (Reliance -> Nippon, DSP BlackRock -> DSP)."""
    events, ledger = execute_sebi_2017_scaleup_ingestion(pipeline)
    rebrand_events = [e for e in events if e.event_type == LifecycleEventType.AMC_REBRANDING]

    assert len(rebrand_events) == 2
    ev = rebrand_events[0]
    assert ev.canonical_scheme_id == "sch_100346"
    assert ev.old_value == "Reliance Mutual Fund"
    assert ev.new_value == "Nippon India Mutual Fund"


def test_05_quarantine_reasons_and_isolation(pipeline):
    """5. Test quarantined events preservation and reason documentation."""
    events, ledger = execute_sebi_2017_scaleup_ingestion(pipeline)
    quarantined = [e for e in events if e.status == "QUARANTINED"]

    assert len(quarantined) == 3
    reasons = [q.quarantine_reason for q in quarantined]
    assert any("missing" in r.lower() for r in reasons)
    assert any("reassignment" in r.lower() or "unverified" in r.lower() for r in reasons)
    assert any("discrepancy" in r.lower() or "conflict" in r.lower() for r in reasons)


def test_06_idempotent_scaleup_reingestion(pipeline, test_db):
    """6. Test idempotent re-ingestion of scale-up batch."""
    events1, rec1 = execute_sebi_2017_scaleup_ingestion(pipeline)
    events2, rec2 = execute_sebi_2017_scaleup_ingestion(pipeline)

    assert rec1.total_candidates_processed == rec2.total_candidates_processed

    with test_db.get_conn() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM scheme_lifecycle_events WHERE methodology_version = '1.0.0'")
        count = cursor.fetchone()[0]

    # Exactly 28 stored rows (25 active + 3 quarantined)
    assert count == 28


def test_07_point_in_time_anti_survivorship_resolution(test_db, repository, pipeline):
    """7. Test point-in-time resolution across pre-merger and post-merger dates."""
    # Seed creation for ICICI Prudential Top 100 Fund (101234)
    creation_doc = RawLifecycleDocument(
        document_id="doc_creation_icici_top100",
        source_id="SEBI_OFFICIAL",
        source_document_url="https://www.sebi.gov.in",
        retrieval_timestamp_utc=datetime.now(timezone.utc),
        raw_content="Inception notice",
    )
    creation_cand = CandidateLifecycleEvent(
        source_document_id="doc_creation_icici_top100",
        raw_scheme_name="ICICI Prudential Top 100 Fund",
        raw_amfi_code="101234",
        event_type_str="SCHEME_CREATION",
        effective_date_str="2010-01-01",
    )
    pipeline.process_document(creation_doc, [creation_cand])

    # Execute scale-up batch ingestion (merger effective 2018-05-28)
    execute_sebi_2017_scaleup_ingestion(pipeline)
    resolver = LifecycleResolver(repository)

    # Resolution BEFORE merger (2017-01-01) -> ACTIVE
    identity_before = resolver.resolve_scheme_at_date("sch_101234", date(2017, 1, 1))
    assert identity_before.existence_status == ExistenceStatus.ACTIVE

    # Resolution AFTER merger (2019-01-01) -> MERGED_PREDECESSOR
    identity_after = resolver.resolve_scheme_at_date("sch_101234", date(2019, 1, 1))
    assert identity_after.existence_status == ExistenceStatus.MERGED_PREDECESSOR


def test_08_provenance_chain_auditability(pipeline):
    """8. Test full provenance chain auditability for scaled events."""
    events, _ = execute_sebi_2017_scaleup_ingestion(pipeline)
    for ev in events:
        assert ev.source_id in ("SEBI_OFFICIAL", "AMC_STATUTORY_DISCLOSURE", "AMFI_OFFICIAL")
        assert ev.methodology_version == "1.0.0"
        assert "SOURCE-DOCUMENT FACT:" in ev.notes
        assert "EMPIRICAL AMFI OBSERVATION:" in ev.notes
        assert "PLATFORM INFERENCE:" in ev.notes
