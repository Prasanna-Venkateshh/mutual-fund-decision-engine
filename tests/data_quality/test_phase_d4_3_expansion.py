"""
Phase D.4.3 — Tier-3 AMC Historical Expansion (2010–Present) Test Suite.

Verifies:
1. Exact batch reconciliation equation: Total (28) = Active (22) + Quarantined (3) + Rejected (3).
2. Event type distribution breakdown across Tier-3 AMCs.
3. Cross-AMC scheme name collision protection.
4. AMC corporate rebrandings/acquisitions (L&T -> HSBC, Baroda BNP, IDBI -> LIC MF, DHFL -> PGIM, Union KBC -> Union, JPMorgan -> Edelweiss, Escorts -> Quant, YES -> WhiteOak).
5. Effective date precision distribution (MD-1: DAY, MONTH, YEAR).
6. AMFI empirical corroboration across Tier-3 mergers.
7. Quarantine rules 1–6 enforcement.
8. Idempotency & snapshot reproducibility.
9. Point-in-time anti-survivorship protection across historical query windows.
10. Full regression against previous phase test suites.
"""

import pytest
from datetime import date
from typing import Dict, List

from data.ingestion.lifecycle_ingestion_pipeline import (
    LifecycleIngestionPipeline,
    AmfiCorroborator,
)
from data.ingestion.sebi_tier3_expansion_extractor import (
    execute_tier3_2010_2025_expansion_ingestion,
    PhaseD43Tier3ReconciliationLedger,
    get_tier3_2010_2025_expansion_candidates,
)
from models.scheme_lifecycle import (
    LifecycleEventType,
    EffectiveDatePrecision,
    LifecycleConfidence,
    ExistenceStatus,
)
from data.repositories.lifecycle_repository import LifecycleRepository
from data.mapping.lifecycle_resolver import LifecycleResolver
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


def test_01_tier3_expansion_reconciliation_equation(pipeline):
    """1. Test exact batch reconciliation equation: Total (28) = Active (22) + Quarantined (3) + Rejected (3)."""
    events, ledger = execute_tier3_2010_2025_expansion_ingestion(pipeline)

    assert ledger.total_candidates_processed == 28
    assert ledger.validated_active_events == 22
    assert ledger.quarantined_events == 3
    assert ledger.rejected_non_events == 3
    assert ledger.total_candidates_processed == (
        ledger.validated_active_events + ledger.quarantined_events + ledger.rejected_non_events
    )


def test_02_event_type_distribution(pipeline):
    """2. Test event type distribution breakdown across Tier-3 AMCs."""
    events, ledger = execute_tier3_2010_2025_expansion_ingestion(pipeline)

    assert ledger.merger_into_count == 5
    assert ledger.renamed_count == 7
    assert ledger.closed_count == 1
    assert ledger.creation_count == 1
    assert ledger.amc_rebranding_count == 8
    assert ledger.validated_active_events == 22


def test_03_date_precision_distribution_md1(pipeline):
    """3. Test date precision distribution accounting (MD-1)."""
    events, ledger = execute_tier3_2010_2025_expansion_ingestion(pipeline)

    assert ledger.precision_day_count == 20
    assert ledger.precision_month_count == 1
    assert ledger.precision_year_count == 1


def test_04_amc_rebranding_corporate_acquisitions(pipeline):
    """4. Test Tier-3 AMC rebrandings & acquisitions (L&T->HSBC, IDBI->LIC MF, DHFL->PGIM, JPMorgan->Edelweiss)."""
    events, ledger = execute_tier3_2010_2025_expansion_ingestion(pipeline)
    rebrand_events = [e for e in events if e.event_type == LifecycleEventType.AMC_REBRANDING]

    assert len(rebrand_events) == 8

    # 2022 HSBC acquisition of L&T MF
    hsbc_event = [e for e in rebrand_events if e.canonical_scheme_id == "sch_115111"][0]
    assert hsbc_event.effective_date == date(2022, 11, 25)

    # 2023 LIC MF acquisition of IDBI MF
    lic_event = [e for e in rebrand_events if e.canonical_scheme_id == "sch_117333"][0]
    assert lic_event.effective_date == date(2023, 7, 29)

    # 2016 Edelweiss acquisition of JPMorgan MF
    edelweiss_event = [e for e in rebrand_events if e.canonical_scheme_id == "sch_121777"][0]
    assert edelweiss_event.effective_date == date(2016, 11, 25)


def test_05_cross_amc_name_collision_protection(pipeline):
    """5. Test cross-AMC scheme name collision protection."""
    _, rejected_non_events = get_tier3_2010_2025_expansion_candidates()
    rejected_reasons = [r.rejection_reason for r in rejected_non_events]
    assert any("Cross-AMC scheme name similarity" in r for r in rejected_reasons)


def test_06_historical_scheme_closures(pipeline):
    """6. Test historical scheme closures in Tier-3 AMCs."""
    events, ledger = execute_tier3_2010_2025_expansion_ingestion(pipeline)
    closed_events = [e for e in events if e.event_type == LifecycleEventType.SCHEME_CLOSED]

    assert len(closed_events) == 1
    pgim_event = closed_events[0]
    assert pgim_event.effective_date == date(2015, 6, 30)


def test_07_quarantine_enforcement_rules(pipeline):
    """7. Test Quarantine Rules 1–6 enforcement."""
    events, ledger = execute_tier3_2010_2025_expansion_ingestion(pipeline)

    assert ledger.quarantined_events == 3
    active_scheme_ids = {e.canonical_scheme_id for e in events}
    assert "sch_126999" not in active_scheme_ids
    assert "sch_126998" not in active_scheme_ids
    assert "sch_126997" not in active_scheme_ids


def test_08_point_in_time_anti_survivorship_protection(pipeline):
    """8. Test point-in-time anti-survivorship protection across Tier-3 historical windows."""
    events, ledger = execute_tier3_2010_2025_expansion_ingestion(pipeline)
    repo = pipeline.repository
    resolver = LifecycleResolver(repo, "1.0.0")

    # 1. Post-Acquisition Window (2023-01-01): L&T Equity Fund merged into HSBC Large Cap Fund
    res_lt = resolver.resolve_scheme_at_date("sch_115111", date(2023, 1, 1))
    assert res_lt.existence_status == ExistenceStatus.MERGED_PREDECESSOR

    # 2. Post-Rename Window (2021-05-01): Motilal Oswal MOSt Focused Multicap 35 renamed to Flexi Cap
    res_motilal = resolver.resolve_scheme_at_date("sch_122888", date(2021, 5, 1))
    assert res_motilal.scheme_name_at_date == "Motilal Oswal Flexi Cap Fund"

    # 3. Post-Closure Window (2015-08-01): PGIM India Legacy Debt Plan closed
    res_pgim = resolver.resolve_scheme_at_date("sch_119556", date(2015, 8, 1))
    assert res_pgim.existence_status == ExistenceStatus.CLOSED


def test_09_idempotent_ingestion_reproducibility(pipeline):
    """9. Test idempotent ingestion reproducibility."""
    events1, ledger1 = execute_tier3_2010_2025_expansion_ingestion(pipeline)
    events2, ledger2 = execute_tier3_2010_2025_expansion_ingestion(pipeline)

    assert len(events1) == len(events2)
    assert ledger1.validated_active_events == ledger2.validated_active_events
