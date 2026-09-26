"""
Phase D.4.1 — Tier-1 AMC Historical Expansion (2010–Present) Test Suite.

Verifies:
1. Exact reconciliation equation: Total (35) = Active (28) + Quarantined (4) + Rejected (3).
2. Event type distribution breakdown.
3. Date precision distribution accounting (MD-1: DAY, MONTH, YEAR).
4. AMC rebranding events (Morgan Stanley -> HDFC, Reliance -> Nippon India).
5. Historical scheme closures & winding-up events (2010–2017 horizon).
6. AMFI empirical boundary corroboration across 2010–2025 mergers.
7. Quarantine rules enforcement.
8. Point-in-time anti-survivorship protection across historical temporal query windows.
"""

import pytest
from datetime import date
from typing import Dict, List

from data.ingestion.lifecycle_ingestion_pipeline import (
    LifecycleIngestionPipeline,
    AmfiCorroborator,
)
from data.ingestion.sebi_2010_2025_expansion_extractor import (
    execute_tier1_2010_2025_expansion_ingestion,
    PhaseD4ExpansionReconciliationLedger,
)
from models.scheme_lifecycle import (
    LifecycleEventType,
    EffectiveDatePrecision,
    LifecycleConfidence,
    ExistenceStatus,
)
from data.repositories.lifecycle_repository import LifecycleRepository
from db.database import DatabaseConnection


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


def test_01_tier1_expansion_reconciliation_equation(pipeline):
    """1. Test exact batch reconciliation equation: Total (33) = Active (27) + Quarantined (3) + Rejected (3)."""
    events, ledger = execute_tier1_2010_2025_expansion_ingestion(pipeline)

    assert ledger.total_candidates_processed == 33
    assert ledger.validated_active_events == 27
    assert ledger.quarantined_events == 3
    assert ledger.rejected_non_events == 3
    assert ledger.total_candidates_processed == (
        ledger.validated_active_events + ledger.quarantined_events + ledger.rejected_non_events
    )


def test_02_event_type_distribution(pipeline):
    """2. Test event type distribution breakdown across 2010–2025 horizon."""
    events, ledger = execute_tier1_2010_2025_expansion_ingestion(pipeline)

    assert ledger.merger_into_count == 13
    assert ledger.renamed_count == 8
    assert ledger.closed_count == 2
    assert ledger.creation_count == 2
    assert ledger.amc_rebranding_count == 2
    assert ledger.validated_active_events == 27


def test_03_date_precision_distribution_md1(pipeline):
    """3. Test date precision distribution accounting (MD-1)."""
    events, ledger = execute_tier1_2010_2025_expansion_ingestion(pipeline)

    assert ledger.precision_day_count == 25
    assert ledger.precision_month_count == 1
    assert ledger.precision_year_count == 1


def test_04_amc_rebranding_acquisition_events(pipeline):
    """4. Test AMC rebranding & acquisition events (Morgan Stanley -> HDFC, Reliance -> Nippon India)."""
    events, ledger = execute_tier1_2010_2025_expansion_ingestion(pipeline)
    rebrand_events = [e for e in events if e.event_type == LifecycleEventType.AMC_REBRANDING]

    assert len(rebrand_events) == 2
    
    # 2014 Morgan Stanley acquisition by HDFC AMC
    ms_event = [e for e in rebrand_events if "Morgan Stanley" in e.notes or e.canonical_scheme_id == "sch_101111"][0]
    assert ms_event.effective_date == date(2014, 6, 27)

    # 2019 Reliance AMC rebranding to Nippon India AMC
    nippon_event = [e for e in rebrand_events if e.canonical_scheme_id == "sch_100346"][0]
    assert nippon_event.effective_date == date(2019, 9, 28)


def test_05_historical_scheme_closures(pipeline):
    """5. Test historical scheme closures & winding-up events (2010–2017 horizon)."""
    events, ledger = execute_tier1_2010_2025_expansion_ingestion(pipeline)
    closed_events = [e for e in events if e.event_type == LifecycleEventType.SCHEME_CLOSED]

    assert len(closed_events) == 2
    # HDFC FMP Series 18 maturity winding up in 2013
    fmp_event = [e for e in closed_events if e.canonical_scheme_id == "sch_100888"][0]
    assert fmp_event.effective_date == date(2013, 3, 31)
    assert fmp_event.effective_date_precision == EffectiveDatePrecision.DAY


def test_06_amfi_corroboration_results(pipeline):
    """6. Test AMFI empirical corroboration across 2010–2025 mergers."""
    events, ledger = execute_tier1_2010_2025_expansion_ingestion(pipeline)
    merger_events = [e for e in events if e.event_type == LifecycleEventType.SCHEME_MERGED_INTO]

    assert len(merger_events) == 13
    for ev in merger_events:
        assert ev.confidence == LifecycleConfidence.HIGH
        assert ev.source_document_url is not None
        assert ev.retrieval_timestamp_utc is not None


def test_07_quarantine_enforcement_rules(pipeline):
    """7. Test Quarantine Rules 1–6 enforcement."""
    events, ledger = execute_tier1_2010_2025_expansion_ingestion(pipeline)

    assert ledger.quarantined_events == 3
    # Quarantined candidates excluded from active events
    active_scheme_ids = {e.canonical_scheme_id for e in events}
    assert "sch_109999" not in active_scheme_ids
    assert "sch_109998" not in active_scheme_ids
    assert "sch_109997" not in active_scheme_ids


def test_08_point_in_time_anti_survivorship_protection(pipeline):
    """8. Test point-in-time anti-survivorship protection across 2010–2025 temporal query windows."""
    events, ledger = execute_tier1_2010_2025_expansion_ingestion(pipeline)
    repo = pipeline.repository
    from data.mapping.lifecycle_resolver import LifecycleResolver
    resolver = LifecycleResolver(repo, "1.0.0")

    # 1. Post-Creation Window (2022-01-01): SBI Nifty 50 Index Fund active
    res_creation = resolver.resolve_scheme_at_date("sch_149231", date(2022, 1, 1))
    assert res_creation.existence_status == ExistenceStatus.ACTIVE

    # 2. Post-Acquisition Window (2014-07-01): Morgan Stanley India Growth Fund merged
    res_2014_post = resolver.resolve_scheme_at_date("sch_101112", date(2014, 7, 1))
    assert res_2014_post.existence_status == ExistenceStatus.MERGED_PREDECESSOR

    # 3. Post-SEBI 2017 Window (2018-06-01): HDFC Core & Satellite merged into successor
    res_2018 = resolver.resolve_scheme_at_date("sch_100123", date(2018, 6, 1))
    assert res_2018.existence_status == ExistenceStatus.MERGED_PREDECESSOR

    # 4. Post-Closure Window (2013-05-01): HDFC FMP Series 18 closed
    res_fmp = resolver.resolve_scheme_at_date("sch_100888", date(2013, 5, 1))
    assert res_fmp.existence_status == ExistenceStatus.CLOSED
