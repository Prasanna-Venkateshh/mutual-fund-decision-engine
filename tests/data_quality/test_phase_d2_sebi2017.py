"""
Phase D.2 SEBI 2017 Historical Lifecycle Ingestion & Point-in-Time Test Suite.

Verifies the SEBI 2017 controlled batch lifecycle dataset ingestion,
reconciliation accounting, provenance traceability, AMFI corroboration,
quarantine handling, and point-in-time anti-survivorship bias protection.
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
from data.ingestion.sebi_2017_lifecycle_extractor import (
    ingest_sebi_2017_historical_lifecycle,
    get_sebi_2017_raw_documents,
    SEBI_2017_CIRCULAR_METADATA,
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


def test_01_sebi_2017_source_metadata_verification():
    """1. Test SEBI 2017 circular source metadata and hash verification."""
    meta = SEBI_2017_CIRCULAR_METADATA
    assert meta["circular_number"] == "SEBI/HO/IMD/DF3/CIR/P/2017/114"
    assert meta["issuing_authority"] == "Securities and Exchange Board of India (SEBI)"
    assert meta["checksum_sha256"] is not None and len(meta["checksum_sha256"]) == 64


def test_02_sebi_2017_batch_ingestion_and_reconciliation(pipeline):
    """2. Test batch ingestion and 100% exact reconciliation accounting."""
    events, rec = ingest_sebi_2017_historical_lifecycle(pipeline)

    assert rec.total_candidates_extracted == 9
    assert rec.active_events_inserted == 8
    assert rec.quarantined_events_inserted == 1
    assert rec.date_precision_day_count == 8
    assert rec.date_precision_month_count == 1
    assert rec.total_candidates_extracted == (rec.active_events_inserted + rec.quarantined_events_inserted)


def test_03_hdfc_core_sat_merger_relationships(pipeline):
    """3. Test HDFC Core & Satellite merger relationships."""
    events, _ = ingest_sebi_2017_historical_lifecycle(pipeline)
    mergers = [e for e in events if e.canonical_scheme_id == "sch_102123"]

    assert len(mergers) == 1
    ev = mergers[0]
    assert ev.event_type == LifecycleEventType.SCHEME_MERGED_INTO
    assert ev.effective_date == date(2018, 5, 25)
    assert ev.confidence == LifecycleConfidence.HIGH


def test_04_hdfc_top200_rename_extraction(pipeline):
    """4. Test HDFC Top 200 to Top 100 scheme rename extraction."""
    events, _ = ingest_sebi_2017_historical_lifecycle(pipeline)
    renames = [e for e in events if e.canonical_scheme_id == "sch_100033"]

    assert len(renames) == 1
    ev = renames[0]
    assert ev.event_type == LifecycleEventType.SCHEME_RENAMED
    assert ev.old_value == "HDFC Top 200 Fund"
    assert ev.new_value == "HDFC Top 100 Fund"
    assert ev.effective_date == date(2018, 6, 30)


def test_05_md1_month_precision_enforcement(pipeline):
    """5. Test MD-1 Month precision storage representation."""
    events, _ = ingest_sebi_2017_historical_lifecycle(pipeline)
    month_events = [e for e in events if e.effective_date_precision == EffectiveDatePrecision.MONTH]

    assert len(month_events) == 1
    ev = month_events[0]
    assert ev.canonical_scheme_id == "sch_108888"
    assert ev.effective_date == date(2018, 6, 1)  # Stored as YYYY-MM-01 representation


def test_06_quarantine_handling_for_missing_url(pipeline):
    """6. Test quarantine handling for unverified candidate missing source URL."""
    events, _ = ingest_sebi_2017_historical_lifecycle(pipeline)
    quarantined = [e for e in events if e.status == "QUARANTINED"]

    assert len(quarantined) == 1
    ev = quarantined[0]
    assert ev.canonical_scheme_id == "sch_109999"
    assert ev.confidence == LifecycleConfidence.AMBIGUOUS
    assert "Mandatory source_document_url is missing" in ev.quarantine_reason


def test_07_point_in_time_predecessor_resolution(test_db, repository, pipeline):
    """7. Test point-in-time anti-survivorship bias resolution."""
    # Seed scheme creation for HDFC Core & Satellite on 2010-01-01
    creation_doc = RawLifecycleDocument(
        document_id="doc_creation_hdfc_core",
        source_id="SEBI_OFFICIAL",
        source_document_url="https://www.sebi.gov.in",
        retrieval_timestamp_utc=datetime.now(timezone.utc),
        raw_content="Inception notice",
    )
    creation_cand = CandidateLifecycleEvent(
        source_document_id="doc_creation_hdfc_core",
        raw_scheme_name="HDFC Core & Satellite Fund",
        raw_amfi_code="102123",
        event_type_str="SCHEME_CREATION",
        effective_date_str="2010-01-01",
    )
    pipeline.process_document(creation_doc, [creation_cand])

    # Ingest SEBI 2017 merger dataset (merger effective 2018-05-25)
    ingest_sebi_2017_historical_lifecycle(pipeline)

    resolver = LifecycleResolver(repository)

    # Resolution BEFORE merger (2017-01-01) -> ACTIVE
    identity_before = resolver.resolve_scheme_at_date("sch_102123", date(2017, 1, 1))
    assert identity_before.existence_status == ExistenceStatus.ACTIVE

    # Resolution AFTER merger (2019-01-01) -> MERGED_PREDECESSOR
    identity_after = resolver.resolve_scheme_at_date("sch_102123", date(2019, 1, 1))
    assert identity_after.existence_status == ExistenceStatus.MERGED_PREDECESSOR


def test_08_universe_snapshot_anti_survivorship_protection(test_db, repository, pipeline):
    """8. Test universe snapshot includes predecessor in 2017, excludes in 2019."""
    # Seed creation
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

    ingest_sebi_2017_historical_lifecycle(pipeline)
    resolver = LifecycleResolver(repository)

    # Build 2017-01-01 universe (Pre-merger)
    univ_2017 = resolver.build_point_in_time_universe(["sch_101234"], date(2017, 1, 1))
    assert len(univ_2017) == 1
    assert univ_2017[0].existence_status == ExistenceStatus.ACTIVE

    # Build 2019-01-01 universe (Post-merger) -> Predecessor excluded from active universe
    univ_2019 = resolver.build_point_in_time_universe(["sch_101234"], date(2019, 1, 1))
    assert len(univ_2019) == 0  # Only ACTIVE schemes included in point-in-time universe


def test_09_provenance_chain_reproducibility(pipeline):
    """9. Test complete provenance chain auditability."""
    events, _ = ingest_sebi_2017_historical_lifecycle(pipeline)
    ev = events[0]

    assert ev.source_id == "SEBI_OFFICIAL"
    assert ev.source_document_url == "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&smid=2"
    assert ev.methodology_version == "1.0.0"
    assert "SOURCE-DOCUMENT FACT:" in ev.notes
    assert "EMPIRICAL AMFI OBSERVATION:" in ev.notes
    assert "PLATFORM INFERENCE:" in ev.notes


def test_10_idempotent_sebi2017_reingestion(pipeline, test_db):
    """10. Test idempotent re-execution of SEBI 2017 ingestion."""
    events1, rec1 = ingest_sebi_2017_historical_lifecycle(pipeline)
    events2, rec2 = ingest_sebi_2017_historical_lifecycle(pipeline)

    assert rec1.total_candidates_extracted == rec2.total_candidates_extracted

    with test_db.get_conn() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM scheme_lifecycle_events WHERE methodology_version = '1.0.0'")
        count = cursor.fetchone()[0]

    # Exactly 9 events stored (no duplicates)
    assert count == 9
