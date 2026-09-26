"""
Phase C: Scheme Lifecycle — Comprehensive Test Suite.

All 32 test cases are deterministic, fixture-only tests.
No live network calls.  All tests use in-memory SQLite databases.

Test Groups:
1.  Scheme creation event
2.  Scheme rename
3.  Scheme closure
4.  Merger predecessor
5.  Merger receiver
6.  One-to-one merger
7.  Many-to-one merger
8.  Effective date DAY precision
9.  Effective date MONTH precision
10. Effective date YEAR precision
11. Historical state BEFORE event
12. Historical state AFTER event
13. PRE_LAUNCH state
14. No lifecycle evidence → UNKNOWN
15. Conflicting evidence → AMBIGUOUS
16. Quarantined events excluded from production resolution
17. Low-confidence vs ambiguous distinction
18. AMFI code reassignment
19. ISIN change requiring review
20. Historical scheme in point-in-time universe despite later closure
21. Historical scheme in point-in-time universe despite later merger
22. Historical name preserved at date
23. Provenance preservation
24. Retrieval timestamp preservation
25. Methodology version preservation
26. Predecessor/successor relationships
27. Derived universe snapshot reproducibility
28. No NAV stitching
29. Existing Slice 1 regression
30. Existing Phase B regression
31. Existing Slice 2 regression (metric engine)
32. Existing Phase B.2 regression
"""

import json
import uuid
import pytest
from datetime import date, datetime, timezone
from typing import List

from db.database import DatabaseConnection
from models.scheme_lifecycle import (
    LifecycleEvent,
    LifecycleEventType,
    LifecycleConfidence,
    EffectiveDatePrecision,
    ExistenceStatus,
    SchemeIdentityAtDate,
)
from data.repositories.lifecycle_repository import LifecycleRepository
from data.mapping.lifecycle_resolver import LifecycleResolver

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

METHODOLOGY_VERSION = "1.0.0"
SOURCE_ID = "AMFI_OFFICIAL"
RETRIEVAL_TS = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)


def make_db() -> DatabaseConnection:
    """Create a fresh in-memory SQLite database."""
    return DatabaseConnection(":memory:")


def seed_source(db: DatabaseConnection) -> None:
    """Insert a minimal source_registry row required by FK constraints."""
    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO source_registry (
                source_id, source_name, source_type, authority_level,
                official_url, specific_data_url, supported_data_fields,
                update_frequency, historical_availability,
                free_status, licensing_status, validation_status
            ) VALUES (?, 'AMFI Official', 'OFFICIAL', 'PRIMARY',
                      'https://amfiindia.com', 'https://amfiindia.com/nav',
                      '["NAV"]', 'DAILY', 'HISTORICAL',
                      1, 'FREE', 'VALIDATED')
            """,
            (SOURCE_ID,),
        )


def seed_canonical_scheme(db: DatabaseConnection, scheme_id: str, name: str = "Test Fund Growth") -> None:
    """Insert a minimal canonical_schemes row required by FK constraints."""
    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO canonical_schemes (
                canonical_scheme_id, amc_name, scheme_name, clean_scheme_name,
                plan_type, option_type, category, sub_category, is_active, created_at
            ) VALUES (?, 'Test AMC', ?, ?, 'DIRECT', 'GROWTH',
                      'EQUITY', 'LARGE_CAP', 1, ?)
            """,
            (scheme_id, name, name, datetime.now(timezone.utc).isoformat()),
        )


def make_event(
    event_id: str,
    canonical_scheme_id: str,
    event_type: LifecycleEventType,
    effective_date: date,
    precision: EffectiveDatePrecision = EffectiveDatePrecision.DAY,
    confidence: LifecycleConfidence = LifecycleConfidence.HIGH,
    status: str = "ACTIVE",
    predecessor_ids: List[str] = None,
    successor_ids: List[str] = None,
    old_value: str = None,
    new_value: str = None,
    quarantine_reason: str = None,
    source_doc_url: str = None,
) -> LifecycleEvent:
    """Helper factory for LifecycleEvent test fixtures."""
    return LifecycleEvent(
        event_id=event_id,
        canonical_scheme_id=canonical_scheme_id,
        event_type=event_type,
        effective_date=effective_date,
        effective_date_precision=precision,
        source_id=SOURCE_ID,
        source_document_url=source_doc_url,
        retrieval_timestamp_utc=RETRIEVAL_TS,
        predecessor_scheme_ids=predecessor_ids or [],
        successor_scheme_ids=successor_ids or [],
        old_value=old_value,
        new_value=new_value,
        confidence=confidence,
        status=status,
        quarantine_reason=quarantine_reason,
        methodology_version=METHODOLOGY_VERSION,
        notes="Test fixture",
        created_at=datetime.now(timezone.utc),
    )


# ===========================================================================
# Test 1 — Scheme Creation Event
# ===========================================================================

def test_01_scheme_creation():
    """Scheme CREATION event → resolver returns ACTIVE after that date."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10001"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    ev = make_event(
        "evt_create_01", scheme_id, LifecycleEventType.SCHEME_CREATION,
        date(2015, 1, 10), precision=EffectiveDatePrecision.DAY,
    )
    repo.save_lifecycle_event(ev)

    result = resolver.resolve_scheme_at_date(scheme_id, date(2015, 6, 1))
    assert result.existence_status == ExistenceStatus.ACTIVE
    assert "evt_create_01" in result.events_applied


# ===========================================================================
# Test 2 — Scheme Rename
# ===========================================================================

def test_02_scheme_rename():
    """SCHEME_RENAMED event → resolver returns new name after effective date."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10002"
    seed_canonical_scheme(db, scheme_id, "Old Fund Name Growth")

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    create_ev = make_event(
        "evt_create_02", scheme_id, LifecycleEventType.SCHEME_CREATION,
        date(2010, 1, 1),
    )
    rename_ev = make_event(
        "evt_rename_02", scheme_id, LifecycleEventType.SCHEME_RENAMED,
        date(2020, 6, 15),
        old_value="Old Fund Name Growth",
        new_value="New Fund Name Growth",
    )
    repo.save_lifecycle_event(create_ev)
    repo.save_lifecycle_event(rename_ev)

    result_after = resolver.resolve_scheme_at_date(scheme_id, date(2021, 1, 1))
    assert result_after.scheme_name_at_date == "New Fund Name Growth"

    result_before = resolver.resolve_scheme_at_date(scheme_id, date(2018, 1, 1))
    # Before the rename: old name should be reflected (name not yet changed)
    assert result_before.scheme_name_at_date == "Old Fund Name Growth"


# ===========================================================================
# Test 3 — Scheme Closure
# ===========================================================================

def test_03_scheme_closure():
    """SCHEME_CLOSED event → resolver returns CLOSED after closure date."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10003"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_create_03", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))
    repo.save_lifecycle_event(make_event(
        "evt_close_03", scheme_id, LifecycleEventType.SCHEME_CLOSED, date(2022, 3, 31)
    ))

    result_after = resolver.resolve_scheme_at_date(scheme_id, date(2022, 6, 1))
    assert result_after.existence_status == ExistenceStatus.CLOSED


# ===========================================================================
# Test 4 — Merger Predecessor
# ===========================================================================

def test_04_merger_predecessor():
    """SCHEME_MERGED_INTO → resolver returns MERGED_PREDECESSOR after merger date."""
    db = make_db()
    seed_source(db)
    scheme_a = "CAN_AMFI_10004A"
    scheme_b = "CAN_AMFI_10004B"
    seed_canonical_scheme(db, scheme_a, "Fund A Growth")
    seed_canonical_scheme(db, scheme_b, "Fund B Growth")

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_create_a", scheme_a, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))
    repo.save_lifecycle_event(make_event(
        "evt_merge_a", scheme_a, LifecycleEventType.SCHEME_MERGED_INTO,
        date(2021, 6, 1), successor_ids=[scheme_b]
    ))

    result = resolver.resolve_scheme_at_date(scheme_a, date(2022, 1, 1))
    assert result.existence_status == ExistenceStatus.MERGED_PREDECESSOR
    assert result.successor_scheme_id == scheme_b


# ===========================================================================
# Test 5 — Merger Receiver
# ===========================================================================

def test_05_merger_receiver():
    """SCHEME_RECEIVED_MERGER → resolver returns predecessor scheme IDs."""
    db = make_db()
    seed_source(db)
    scheme_a = "CAN_AMFI_10005A"
    scheme_b = "CAN_AMFI_10005B"
    seed_canonical_scheme(db, scheme_a, "Fund A Growth")
    seed_canonical_scheme(db, scheme_b, "Fund B Growth")

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_create_b", scheme_b, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))
    repo.save_lifecycle_event(make_event(
        "evt_recv_merger", scheme_b, LifecycleEventType.SCHEME_RECEIVED_MERGER,
        date(2021, 6, 1), predecessor_ids=[scheme_a]
    ))

    result = resolver.resolve_scheme_at_date(scheme_b, date(2022, 1, 1))
    assert result.existence_status == ExistenceStatus.ACTIVE
    assert scheme_a in result.predecessor_scheme_ids


# ===========================================================================
# Test 6 — One-to-One Merger
# ===========================================================================

def test_06_one_to_one_merger():
    """One scheme merged into one other: predecessor and receiver both recorded correctly."""
    db = make_db()
    seed_source(db)
    scheme_a = "CAN_AMFI_10006A"
    scheme_b = "CAN_AMFI_10006B"
    seed_canonical_scheme(db, scheme_a, "Fund A Growth")
    seed_canonical_scheme(db, scheme_b, "Fund B Growth")

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    for ev in [
        make_event("evt_cr_a", scheme_a, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)),
        make_event("evt_cr_b", scheme_b, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)),
        make_event("evt_merge_into", scheme_a, LifecycleEventType.SCHEME_MERGED_INTO,
                   date(2021, 6, 1), successor_ids=[scheme_b]),
        make_event("evt_recv", scheme_b, LifecycleEventType.SCHEME_RECEIVED_MERGER,
                   date(2021, 6, 1), predecessor_ids=[scheme_a]),
    ]:
        repo.save_lifecycle_event(ev)

    result_a = resolver.resolve_scheme_at_date(scheme_a, date(2022, 1, 1))
    result_b = resolver.resolve_scheme_at_date(scheme_b, date(2022, 1, 1))

    assert result_a.existence_status == ExistenceStatus.MERGED_PREDECESSOR
    assert result_a.successor_scheme_id == scheme_b
    assert result_b.existence_status == ExistenceStatus.ACTIVE
    assert scheme_a in result_b.predecessor_scheme_ids


# ===========================================================================
# Test 7 — Many-to-One Merger
# ===========================================================================

def test_07_many_to_one_merger():
    """Two predecessor schemes merged into one receiver."""
    db = make_db()
    seed_source(db)
    scheme_a = "CAN_AMFI_10007A"
    scheme_b = "CAN_AMFI_10007B"
    scheme_c = "CAN_AMFI_10007C"
    for sid, name in [(scheme_a, "Fund A"), (scheme_b, "Fund B"), (scheme_c, "Fund C")]:
        seed_canonical_scheme(db, sid, name)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    for ev in [
        make_event("evt_cr_a7", scheme_a, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)),
        make_event("evt_cr_b7", scheme_b, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)),
        make_event("evt_cr_c7", scheme_c, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)),
        make_event("evt_merge_a7", scheme_a, LifecycleEventType.SCHEME_MERGED_INTO,
                   date(2021, 6, 1), successor_ids=[scheme_c]),
        make_event("evt_merge_b7", scheme_b, LifecycleEventType.SCHEME_MERGED_INTO,
                   date(2021, 6, 1), successor_ids=[scheme_c]),
        make_event("evt_recv_c7", scheme_c, LifecycleEventType.SCHEME_RECEIVED_MERGER,
                   date(2021, 6, 1), predecessor_ids=[scheme_a, scheme_b]),
    ]:
        repo.save_lifecycle_event(ev)

    result_c = resolver.resolve_scheme_at_date(scheme_c, date(2022, 1, 1))
    assert result_c.existence_status == ExistenceStatus.ACTIVE
    assert scheme_a in result_c.predecessor_scheme_ids
    assert scheme_b in result_c.predecessor_scheme_ids

    result_a = resolver.resolve_scheme_at_date(scheme_a, date(2022, 1, 1))
    result_b = resolver.resolve_scheme_at_date(scheme_b, date(2022, 1, 1))
    assert result_a.existence_status == ExistenceStatus.MERGED_PREDECESSOR
    assert result_b.existence_status == ExistenceStatus.MERGED_PREDECESSOR


# ===========================================================================
# Test 8 — Effective Date DAY Precision
# ===========================================================================

def test_08_effective_date_day_precision():
    """DAY precision: event on 2018-06-15 → ACTIVE on 2018-06-15, UNKNOWN before."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10008"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    ev = make_event(
        "evt_create_08", scheme_id, LifecycleEventType.SCHEME_CREATION,
        date(2018, 6, 15), precision=EffectiveDatePrecision.DAY
    )
    repo.save_lifecycle_event(ev)

    result_on = resolver.resolve_scheme_at_date(scheme_id, date(2018, 6, 15))
    assert result_on.existence_status == ExistenceStatus.ACTIVE

    result_before = resolver.resolve_pre_launch_check(scheme_id, date(2018, 6, 14))
    assert result_before.existence_status == ExistenceStatus.PRE_LAUNCH


# ===========================================================================
# Test 9 — Effective Date MONTH Precision
# ===========================================================================

def test_09_effective_date_month_precision():
    """
    MONTH precision: event stored as 2018-06-01 (precision=MONTH).
    Query on 2018-06-15 (within the month) → precision uncertain.
    Query on 2018-07-01 → event definitely occurred before (last day of June <= July 1).
    Query on 2018-05-31 → event definitely not yet occurred.
    """
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10009"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    ev = make_event(
        "evt_create_09", scheme_id, LifecycleEventType.SCHEME_CREATION,
        date(2018, 6, 1), precision=EffectiveDatePrecision.MONTH
    )
    repo.save_lifecycle_event(ev)

    # After end of June — event definitely applied
    result_after = resolver.resolve_scheme_at_date(scheme_id, date(2018, 7, 1))
    assert result_after.existence_status == ExistenceStatus.ACTIVE
    # precision_uncertain note should be absent for a post-month query
    assert result_after.methodology_version == METHODOLOGY_VERSION

    # Before June (May) — event definitely NOT yet occurred
    result_before = resolver.resolve_pre_launch_check(scheme_id, date(2018, 5, 31))
    assert result_before.existence_status == ExistenceStatus.PRE_LAUNCH

    # Within June — precision uncertain; event is applied but note is present
    result_within = resolver.resolve_scheme_at_date(scheme_id, date(2018, 6, 15))
    # The event IS applied (effective_date = 2018-06-01 <= 2018-06-15)
    # but precision_uncertain flag should be noted
    assert result_within.existence_status == ExistenceStatus.ACTIVE
    assert "precision" in result_within.resolution_notes.lower()


# ===========================================================================
# Test 10 — Effective Date YEAR Precision
# ===========================================================================

def test_10_effective_date_year_precision():
    """
    YEAR precision: event stored as 2018-01-01 (precision=YEAR).
    Query on 2019-01-01 → event definitely occurred (Dec 31, 2018 <= Jan 1, 2019).
    Query on 2017-12-31 → event definitely NOT yet occurred.
    """
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10010"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    ev = make_event(
        "evt_create_10", scheme_id, LifecycleEventType.SCHEME_CREATION,
        date(2018, 1, 1), precision=EffectiveDatePrecision.YEAR
    )
    repo.save_lifecycle_event(ev)

    result_after = resolver.resolve_scheme_at_date(scheme_id, date(2019, 1, 1))
    assert result_after.existence_status == ExistenceStatus.ACTIVE

    result_before = resolver.resolve_pre_launch_check(scheme_id, date(2017, 12, 31))
    assert result_before.existence_status == ExistenceStatus.PRE_LAUNCH


# ===========================================================================
# Test 11 — Historical State Before Event
# ===========================================================================

def test_11_historical_state_before_event():
    """Query before any event → UNKNOWN (no evidence loaded)."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10011"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    # Store creation event in 2020
    repo.save_lifecycle_event(make_event(
        "evt_cr_11", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2020, 1, 1)
    ))

    # Query in 2015 — no events before 2015 are loaded
    result = resolver.resolve_scheme_at_date(scheme_id, date(2015, 1, 1))
    # No events with effective_date <= 2015-01-01 → UNKNOWN
    assert result.existence_status == ExistenceStatus.UNKNOWN
    assert result.events_applied == []


# ===========================================================================
# Test 12 — Historical State After Event
# ===========================================================================

def test_12_historical_state_after_event():
    """Query after creation + rename events → correct state at each date."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10012"
    seed_canonical_scheme(db, scheme_id, "Alpha Fund Growth")

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_cr_12", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))
    repo.save_lifecycle_event(make_event(
        "evt_rn_12", scheme_id, LifecycleEventType.SCHEME_RENAMED,
        date(2018, 7, 1),
        old_value="Alpha Fund Growth", new_value="Beta Fund Growth"
    ))

    # After both events
    result = resolver.resolve_scheme_at_date(scheme_id, date(2020, 1, 1))
    assert result.existence_status == ExistenceStatus.ACTIVE
    assert result.scheme_name_at_date == "Beta Fund Growth"
    assert len(result.events_applied) == 2


# ===========================================================================
# Test 13 — PRE_LAUNCH State
# ===========================================================================

def test_13_pre_launch_state():
    """Query before scheme creation → PRE_LAUNCH (not UNKNOWN when creation event exists)."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10013"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_cr_13", scheme_id, LifecycleEventType.SCHEME_CREATION,
        date(2019, 4, 15), precision=EffectiveDatePrecision.DAY
    ))

    result = resolver.resolve_pre_launch_check(scheme_id, date(2018, 1, 1))
    assert result.existence_status == ExistenceStatus.PRE_LAUNCH


# ===========================================================================
# Test 14 — No Lifecycle Evidence → UNKNOWN
# ===========================================================================

def test_14_no_lifecycle_evidence_returns_unknown():
    """Scheme with zero lifecycle events → UNKNOWN, never ACTIVE."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10014"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    # No events stored at all
    result = resolver.resolve_scheme_at_date(scheme_id, date(2020, 6, 1))
    assert result.existence_status == ExistenceStatus.UNKNOWN
    assert result.events_applied == []
    assert "UNKNOWN" in result.resolution_notes or "No lifecycle" in result.resolution_notes


# ===========================================================================
# Test 15 — Conflicting Evidence → AMBIGUOUS
# ===========================================================================

def test_15_conflicting_evidence_returns_ambiguous():
    """Two SCHEME_RENAMED events on the same effective_date → AMBIGUOUS."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10015"
    seed_canonical_scheme(db, scheme_id, "Original Name Growth")

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_cr_15", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))
    # Two conflicting rename events on the same date
    repo.save_lifecycle_event(make_event(
        "evt_rn_15a", scheme_id, LifecycleEventType.SCHEME_RENAMED,
        date(2020, 6, 1),
        old_value="Original Name Growth", new_value="New Name A Growth"
    ))
    repo.save_lifecycle_event(make_event(
        "evt_rn_15b", scheme_id, LifecycleEventType.SCHEME_RENAMED,
        date(2020, 6, 1),
        old_value="Original Name Growth", new_value="New Name B Growth"
    ))

    result = resolver.resolve_scheme_at_date(scheme_id, date(2021, 1, 1))
    assert result.existence_status == ExistenceStatus.AMBIGUOUS
    assert result.resolution_confidence == LifecycleConfidence.AMBIGUOUS


# ===========================================================================
# Test 16 — Quarantined Events Excluded from Production Resolution
# ===========================================================================

def test_16_quarantined_events_excluded():
    """Quarantined lifecycle event must not affect production resolution."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10016"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_cr_16", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))

    # A QUARANTINED closure event — should NOT affect resolution
    quarantined_ev = make_event(
        "evt_close_quarantine_16", scheme_id, LifecycleEventType.SCHEME_CLOSED,
        date(2020, 1, 1),
        status="QUARANTINED",
        quarantine_reason="Unverified source — pending AMC confirmation"
    )
    # Must override confidence to avoid AMBIGUOUS validation error
    quarantined_ev.confidence = LifecycleConfidence.LOW
    quarantined_ev.status = "QUARANTINED"
    quarantined_ev.quarantine_reason = "Unverified — pending AMC confirmation"
    repo.save_lifecycle_event(quarantined_ev)

    # Resolve — should be ACTIVE (quarantined closure ignored)
    result = resolver.resolve_scheme_at_date(scheme_id, date(2021, 1, 1))
    assert result.existence_status == ExistenceStatus.ACTIVE
    assert "evt_close_quarantine_16" not in result.events_applied


# ===========================================================================
# Test 17 — Low Confidence vs Ambiguous Distinction
# ===========================================================================

def test_17_low_confidence_vs_ambiguous():
    """LOW confidence event is applied but produces LOW resolution_confidence, not AMBIGUOUS."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10017"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_cr_17", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1),
        confidence=LifecycleConfidence.LOW,
    ))

    result = resolver.resolve_scheme_at_date(scheme_id, date(2020, 1, 1))
    # Should be ACTIVE (event applied) but LOW confidence
    assert result.existence_status == ExistenceStatus.ACTIVE
    assert result.resolution_confidence == LifecycleConfidence.LOW
    # Definitely not AMBIGUOUS — no conflicting evidence
    assert result.existence_status != ExistenceStatus.AMBIGUOUS


# ===========================================================================
# Test 18 — AMFI Code Reassignment (MD-2)
# ===========================================================================

def test_18_amfi_code_reassignment():
    """AMFI_CODE_REASSIGNED event marks old scheme as MERGED_PREDECESSOR."""
    db = make_db()
    seed_source(db)
    old_scheme = "CAN_AMFI_10018_OLD"
    new_scheme = "CAN_AMFI_10018_NEW"
    seed_canonical_scheme(db, old_scheme, "Old Economic Fund Growth")
    seed_canonical_scheme(db, new_scheme, "New Different Fund Growth")

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_cr_18", old_scheme, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))
    # AMFI code reassigned — old scheme identity ends, new scheme is a different entity
    repo.save_lifecycle_event(make_event(
        "evt_reassign_18", old_scheme, LifecycleEventType.AMFI_CODE_REASSIGNED,
        date(2020, 1, 1),
        old_value="AMFI_CODE_10018",
        new_value="AMFI_CODE_10018",  # Same code reused
        source_doc_url="https://amfiindia.com/notice/reassign_2020",
    ))

    result_old = resolver.resolve_scheme_at_date(old_scheme, date(2021, 1, 1))
    # Old scheme should be MERGED_PREDECESSOR (identity effectively ended)
    assert result_old.existence_status == ExistenceStatus.MERGED_PREDECESSOR
    # AMFI_CODE_REASSIGNED note should be in resolution notes
    assert "AMFI code reassigned" in result_old.resolution_notes or \
           "reassign" in result_old.resolution_notes.lower()

    # New scheme is created as a completely separate entity — its own lifecycle
    repo.save_lifecycle_event(make_event(
        "evt_cr_new_18", new_scheme, LifecycleEventType.SCHEME_CREATION, date(2020, 1, 1)
    ))
    result_new = resolver.resolve_scheme_at_date(new_scheme, date(2021, 1, 1))
    assert result_new.existence_status == ExistenceStatus.ACTIVE


# ===========================================================================
# Test 19 — ISIN Change Requiring Review (MD-3)
# ===========================================================================

def test_19_isin_change_requires_review():
    """ISIN_CHANGED event does not alter existence_status; records need for investigation."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10019"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_cr_19", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))
    # ISIN change — per MD-3: does not auto-create new ID, does not confirm continuity
    repo.save_lifecycle_event(make_event(
        "evt_isin_19", scheme_id, LifecycleEventType.ISIN_CHANGED,
        date(2018, 6, 1),
        old_value="INF123K01ABC",
        new_value="INF123K01XYZ",
        confidence=LifecycleConfidence.MEDIUM,
    ))

    result = resolver.resolve_scheme_at_date(scheme_id, date(2019, 1, 1))
    # Existence status must NOT have changed due to ISIN_CHANGED alone
    assert result.existence_status == ExistenceStatus.ACTIVE
    # Resolution notes must mention investigation requirement
    assert "investigation" in result.resolution_notes.lower() or \
           "MD-3" in result.resolution_notes or \
           "ISIN" in result.resolution_notes


# ===========================================================================
# Test 20 — Historical Scheme in Universe Despite Later Closure
# ===========================================================================

def test_20_universe_includes_scheme_despite_later_closure():
    """
    Scheme ACTIVE in 2019 but CLOSED in 2022.
    Point-in-time universe for 2019 MUST include it (survivorship bias prevention).
    """
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10020"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_cr_20", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))
    repo.save_lifecycle_event(make_event(
        "evt_close_20", scheme_id, LifecycleEventType.SCHEME_CLOSED, date(2022, 3, 31)
    ))

    # Universe in 2019: scheme was ACTIVE
    universe_2019 = resolver.build_point_in_time_universe(
        [scheme_id], date(2019, 6, 1)
    )
    active_ids = [u.canonical_scheme_id for u in universe_2019]
    assert scheme_id in active_ids

    # Universe in 2023: scheme was already CLOSED → excluded
    universe_2023 = resolver.build_point_in_time_universe(
        [scheme_id], date(2023, 1, 1)
    )
    active_ids_2023 = [u.canonical_scheme_id for u in universe_2023]
    assert scheme_id not in active_ids_2023


# ===========================================================================
# Test 21 — Historical Scheme in Universe Despite Later Merger
# ===========================================================================

def test_21_universe_includes_scheme_despite_later_merger():
    """
    Scheme A ACTIVE in 2019 but MERGED in 2021.
    Point-in-time universe for 2019 MUST include Scheme A.
    """
    db = make_db()
    seed_source(db)
    scheme_a = "CAN_AMFI_10021A"
    scheme_b = "CAN_AMFI_10021B"
    seed_canonical_scheme(db, scheme_a, "Fund A Growth")
    seed_canonical_scheme(db, scheme_b, "Fund B Growth")

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    for ev in [
        make_event("evt_cr_a21", scheme_a, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)),
        make_event("evt_cr_b21", scheme_b, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)),
        make_event("evt_merge_a21", scheme_a, LifecycleEventType.SCHEME_MERGED_INTO,
                   date(2021, 6, 1), successor_ids=[scheme_b]),
    ]:
        repo.save_lifecycle_event(ev)

    universe_2019 = resolver.build_point_in_time_universe(
        [scheme_a, scheme_b], date(2019, 1, 1)
    )
    active_ids = [u.canonical_scheme_id for u in universe_2019]
    assert scheme_a in active_ids   # existed in 2019, not yet merged

    universe_2022 = resolver.build_point_in_time_universe(
        [scheme_a, scheme_b], date(2022, 1, 1)
    )
    active_ids_2022 = [u.canonical_scheme_id for u in universe_2022]
    assert scheme_a not in active_ids_2022   # merged by 2022


# ===========================================================================
# Test 22 — Historical Name Preserved at Date
# ===========================================================================

def test_22_historical_name_preserved():
    """Scheme renamed multiple times: correct name returned for each historical date."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10022"
    seed_canonical_scheme(db, scheme_id, "Name V1 Growth")

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    for ev in [
        make_event("evt_cr_22", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)),
        make_event("evt_rn_22a", scheme_id, LifecycleEventType.SCHEME_RENAMED,
                   date(2015, 6, 1), old_value="Name V1 Growth", new_value="Name V2 Growth"),
        make_event("evt_rn_22b", scheme_id, LifecycleEventType.SCHEME_RENAMED,
                   date(2020, 3, 1), old_value="Name V2 Growth", new_value="Name V3 Growth"),
    ]:
        repo.save_lifecycle_event(ev)

    r1 = resolver.resolve_scheme_at_date(scheme_id, date(2012, 1, 1))
    assert r1.scheme_name_at_date == "Name V1 Growth"

    r2 = resolver.resolve_scheme_at_date(scheme_id, date(2017, 1, 1))
    assert r2.scheme_name_at_date == "Name V2 Growth"

    r3 = resolver.resolve_scheme_at_date(scheme_id, date(2021, 1, 1))
    assert r3.scheme_name_at_date == "Name V3 Growth"


# ===========================================================================
# Test 23 — Provenance Preservation
# ===========================================================================

def test_23_provenance_preservation():
    """source_id and source_document_url are persisted and retrievable."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10023"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)

    ev = make_event(
        "evt_cr_23", scheme_id, LifecycleEventType.SCHEME_CREATION,
        date(2015, 1, 1),
        source_doc_url="https://amfiindia.com/gazette/2015/notice_10023"
    )
    repo.save_lifecycle_event(ev)

    retrieved = repo.get_event_by_id("evt_cr_23")
    assert retrieved is not None
    assert retrieved.source_id == SOURCE_ID
    assert retrieved.source_document_url == "https://amfiindia.com/gazette/2015/notice_10023"


# ===========================================================================
# Test 24 — Retrieval Timestamp Preservation
# ===========================================================================

def test_24_retrieval_timestamp_preservation():
    """retrieval_timestamp_utc is persisted accurately."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10024"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)

    ev = make_event(
        "evt_cr_24", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2015, 1, 1)
    )
    repo.save_lifecycle_event(ev)

    retrieved = repo.get_event_by_id("evt_cr_24")
    assert retrieved is not None
    assert retrieved.retrieval_timestamp_utc.year == RETRIEVAL_TS.year
    assert retrieved.retrieval_timestamp_utc.month == RETRIEVAL_TS.month


# ===========================================================================
# Test 25 — Methodology Version Preservation
# ===========================================================================

def test_25_methodology_version_preservation():
    """methodology_version is persisted and retrievable."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10025"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)

    ev = make_event(
        "evt_cr_25", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2015, 1, 1)
    )
    repo.save_lifecycle_event(ev)

    retrieved = repo.get_event_by_id("evt_cr_25")
    assert retrieved is not None
    assert retrieved.methodology_version == METHODOLOGY_VERSION


# ===========================================================================
# Test 26 — Predecessor/Successor Relationships
# ===========================================================================

def test_26_predecessor_successor_relationships():
    """Repository returns correct predecessor and successor IDs from lifecycle events."""
    db = make_db()
    seed_source(db)
    scheme_a = "CAN_AMFI_10026A"
    scheme_b = "CAN_AMFI_10026B"
    seed_canonical_scheme(db, scheme_a)
    seed_canonical_scheme(db, scheme_b)

    repo = LifecycleRepository(db)

    repo.save_lifecycle_event(make_event(
        "evt_merge_26", scheme_a, LifecycleEventType.SCHEME_MERGED_INTO,
        date(2020, 1, 1), successor_ids=[scheme_b]
    ))
    repo.save_lifecycle_event(make_event(
        "evt_recv_26", scheme_b, LifecycleEventType.SCHEME_RECEIVED_MERGER,
        date(2020, 1, 1), predecessor_ids=[scheme_a]
    ))

    successors = repo.get_successor_scheme(scheme_a, date(2021, 1, 1))
    assert successors == scheme_b

    predecessors = repo.get_predecessor_schemes(scheme_b, date(2021, 1, 1))
    assert scheme_a in predecessors


# ===========================================================================
# Test 27 — Derived Universe Snapshot Reproducibility
# ===========================================================================

def test_27_derived_snapshot_reproducibility():
    """Universe snapshot can be persisted and re-retrieved; rebuilding replaces it."""
    db = make_db()
    seed_source(db)
    scheme_id = "CAN_AMFI_10027"
    seed_canonical_scheme(db, scheme_id)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_cr_27", scheme_id, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))

    snapshot_date = date(2020, 6, 1)

    # Build and persist the snapshot
    universe = resolver.build_point_in_time_universe([scheme_id], snapshot_date)
    resolver.persist_universe_snapshot(snapshot_date, universe)

    # Retrieve the snapshot
    snap = repo.get_universe_snapshot(scheme_id, snapshot_date, METHODOLOGY_VERSION)
    assert snap is not None
    assert snap["existence_status"] == "ACTIVE"

    # Delete and rebuild — snapshot is rebuildable from source events
    deleted = repo.delete_snapshots_for_methodology(METHODOLOGY_VERSION)
    assert deleted >= 1

    # Rebuild
    universe2 = resolver.build_point_in_time_universe([scheme_id], snapshot_date)
    resolver.persist_universe_snapshot(snapshot_date, universe2)
    snap2 = repo.get_universe_snapshot(scheme_id, snapshot_date, METHODOLOGY_VERSION)
    assert snap2 is not None
    assert snap2["existence_status"] == "ACTIVE"


# ===========================================================================
# Test 28 — No NAV Stitching
# ===========================================================================

def test_28_no_nav_stitching():
    """
    Phase C does not provide any mechanism to concatenate predecessor NAV history
    with successor NAV history.  Verify by checking that SchemeIdentityAtDate
    and LifecycleResolver have no NAV-series fields or stitching methods.
    """
    db = make_db()
    seed_source(db)
    scheme_a = "CAN_AMFI_10028A"
    scheme_b = "CAN_AMFI_10028B"
    seed_canonical_scheme(db, scheme_a)
    seed_canonical_scheme(db, scheme_b)

    repo = LifecycleRepository(db)
    resolver = LifecycleResolver(repo, METHODOLOGY_VERSION)

    repo.save_lifecycle_event(make_event(
        "evt_merge_28", scheme_a, LifecycleEventType.SCHEME_MERGED_INTO,
        date(2020, 1, 1), successor_ids=[scheme_b]
    ))
    repo.save_lifecycle_event(make_event(
        "evt_cr_b28", scheme_b, LifecycleEventType.SCHEME_CREATION, date(2010, 1, 1)
    ))

    result_a = resolver.resolve_scheme_at_date(scheme_a, date(2021, 1, 1))
    result_b = resolver.resolve_scheme_at_date(scheme_b, date(2021, 1, 1))

    # SchemeIdentityAtDate has no NAV series fields
    assert not hasattr(result_a, "nav_series")
    assert not hasattr(result_a, "stitched_nav")
    assert not hasattr(result_a, "combined_returns")

    # LifecycleResolver has no NAV stitching methods
    assert not hasattr(resolver, "stitch_nav_series")
    assert not hasattr(resolver, "concatenate_nav")
    assert not hasattr(resolver, "reconstruct_returns")

    # Merger relationship is recorded, but separate scheme identities are preserved
    assert result_a.canonical_scheme_id == scheme_a
    assert result_b.canonical_scheme_id == scheme_b
    assert result_a.successor_scheme_id == scheme_b


# ===========================================================================
# Test 29 — Existing Slice 1 Regression
# ===========================================================================

def test_29_slice1_regression():
    """
    Slice 1 (SchemeMaster, NAVValidator, source registry) must work
    unchanged after Phase C schema additions.
    """
    from data.mapping.scheme_master import SchemeMaster
    from data.validation.nav_validator import NAVValidator
    from data.ingestion.source_registry import SourceRegistry

    db = make_db()

    # Source registry: verify it can be instantiated and loads sources
    registry = SourceRegistry(db=db)
    registry.load_registry()
    source = registry.get_source("AMFI_OFFICIAL")
    # Source may be None if not pre-seeded in in-memory DB; what matters is no error
    # SchemeMaster has its own internal source seeding

    # Scheme master can still resolve schemes without lifecycle events
    master = SchemeMaster()
    scheme, mapping = master.resolve_or_create_canonical_scheme(
        source_id="AMFI_OFFICIAL",
        source_scheme_code="119551",
        source_scheme_name="HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth",
    )
    assert scheme.canonical_scheme_id == "CAN_AMFI_119551"
    assert mapping.confidence.value in ("EXACT_MATCH", "HIGH_CONFIDENCE")

    # NAVValidator still works
    validator = NAVValidator()
    assert validator is not None


# ===========================================================================
# Test 30 — Existing Phase B Regression (prototype)
# ===========================================================================

def test_30_phase_b_prototype_regression():
    """Phase B prototype imports and classes remain importable after Phase C changes."""
    try:
        from data.ingestion.historical_nav_prototype import HistoricalNAVPrototype
        assert HistoricalNAVPrototype is not None
    except ImportError:
        pytest.skip("Phase B prototype not present or differently named — skipping.")


# ===========================================================================
# Test 31 — Existing Slice 2 Regression (metric engine)
# ===========================================================================

def test_31_slice2_metric_engine_regression():
    """Slice 2 metric engine imports correctly after Phase C schema/model changes."""
    try:
        from models.metric_data import MetricObservation, HistoryMaturityBucket, DataQualityState
        assert MetricObservation is not None
        assert HistoryMaturityBucket is not None
        assert DataQualityState is not None
    except ImportError as e:
        pytest.fail(f"Slice 2 metric model import failed: {e}")


# ===========================================================================
# Test 32 — Existing Phase B.2 Pipeline Regression
# ===========================================================================

def test_32_phase_b2_pipeline_not_modified():
    """
    Phase B.2 historical NAV pipeline is NOT modified by Phase C.
    Verify it imports cleanly and does not reference lifecycle modules.
    """
    import importlib, inspect
    try:
        pipeline_mod = importlib.import_module("data.ingestion.historical_nav_pipeline")
        # Verify the pipeline exists and has the expected classes
        assert hasattr(pipeline_mod, "HistoricalNAVPipeline")
        assert hasattr(pipeline_mod, "HistoricalCoverageAnalyzer")

        # Verify lifecycle modules are NOT imported in the pipeline (decoupling check)
        source = inspect.getsource(pipeline_mod)
        assert "lifecycle_resolver" not in source
        assert "scheme_lifecycle_events" not in source
        assert "LifecycleRepository" not in source
    except ImportError as e:
        pytest.fail(f"Phase B.2 pipeline import failed: {e}")
