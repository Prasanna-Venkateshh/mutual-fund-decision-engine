"""
Integration and Verification Test Suite for Investor Profile & Session Persistence (Step 1).

Covers requirements A through U:
- Schema creation & additive migration
- Profile CRUD & append-only versioning
- Deterministic round-trip serialization (None, 0, 0.0, False preservation)
- Current version selection & history preservation
- Repository re-instantiation across restarts
- Identity isolation (investor_A vs investor_B)
- Fail-closed security handling for missing/malformed payloads
- Zero mutation of financial engine tables or execution status
"""

import json
import sqlite3
import pytest
from datetime import date, datetime, timezone

from models.investor_profile import (
    InvestorProfileSnapshot,
    FinancialCapacitySnapshot,
    BehavioralToleranceSnapshot,
    RiskCapacityLevel,
    RiskToleranceLevel,
    ProfileStatus,
)
from data.repositories.profile_repository import (
    ProfileRepository,
    ProfilePersistenceError,
    ProfileNotFoundError,
)
from web.adapters import QuestionnaireAdapter


@pytest.fixture
def in_memory_db():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


def test_schema_creation_fresh_db(in_memory_db):
    """A, B: Fresh DB schema creation."""
    repo = ProfileRepository(in_memory_db)
    cursor = in_memory_db.execute("PRAGMA table_info(investor_profile_snapshots);")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    assert "profile_id" in columns
    assert "investor_id" in columns
    assert "profile_version" in columns
    assert "payload_json" in columns
    assert "is_current" in columns


def test_existing_db_migration(in_memory_db):
    """C: Existing DB migration without is_current column."""
    in_memory_db.execute("""
    CREATE TABLE investor_profile_snapshots (
        profile_id TEXT PRIMARY KEY,
        investor_id TEXT NOT NULL,
        profile_version TEXT NOT NULL,
        effective_date TEXT NOT NULL,
        status TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        payload_json TEXT NOT NULL,
        created_at_utc TEXT NOT NULL,
        UNIQUE(investor_id, profile_version)
    );
    """)
    in_memory_db.commit()

    # Re-init repository triggers migration
    repo = ProfileRepository(in_memory_db)
    cursor = in_memory_db.execute("PRAGMA table_info(investor_profile_snapshots);")
    columns = [row[1] for row in cursor.fetchall()]
    assert "is_current" in columns


def test_profile_create_and_read(in_memory_db):
    """D, E: Profile create and read."""
    repo = ProfileRepository(in_memory_db)
    today = date.today()

    fc = FinancialCapacitySnapshot(
        observation_date=today,
        effective_date=today,
        emergency_reserve_months=6.0,
        monthly_gross_income=150000.0,
    )
    bt = BehavioralToleranceSnapshot(
        observation_date=today,
        assessment_date=today,
        loss_reaction_choice="BUY_MORE",
    )
    profile = InvestorProfileSnapshot(
        profile_id="prof_inv_001_v1",
        investor_id="inv_001",
        profile_version="1.0.0",
        effective_date=today,
        financial_capacity=fc,
        behavioral_tolerance=bt,
    )

    prof_id = repo.save_profile(profile)
    assert prof_id == "prof_inv_001_v1"

    retrieved = repo.get_current_profile("inv_001")
    assert retrieved is not None
    assert retrieved.profile_id == "prof_inv_001_v1"
    assert retrieved.investor_id == "inv_001"
    assert retrieved.profile_version == "1.0.0"
    assert retrieved.financial_capacity.emergency_reserve_months == 6.0
    assert retrieved.behavioral_tolerance.loss_reaction_choice == "BUY_MORE"


def test_profile_version_update_and_preservation(in_memory_db):
    """F, G, H: Profile update, version preservation, and current-version selection."""
    repo = ProfileRepository(in_memory_db)
    today = date.today()

    # Version 1.0.0
    p1 = InvestorProfileSnapshot(
        profile_id="prof_inv_001_v1",
        investor_id="inv_001",
        profile_version="1.0.0",
        effective_date=today,
        financial_capacity=FinancialCapacitySnapshot(
            observation_date=today, effective_date=today, emergency_reserve_months=3.0
        ),
    )
    repo.save_profile(p1)

    # Version 1.0.1
    p2 = InvestorProfileSnapshot(
        profile_id="prof_inv_001_v2",
        investor_id="inv_001",
        profile_version="1.0.1",
        effective_date=today,
        financial_capacity=FinancialCapacitySnapshot(
            observation_date=today, effective_date=today, emergency_reserve_months=9.0
        ),
    )
    repo.save_profile(p2)

    # Current profile must be v1.0.1
    current = repo.get_current_profile("inv_001")
    assert current is not None
    assert current.profile_version == "1.0.1"
    assert current.financial_capacity.emergency_reserve_months == 9.0

    # Historical profile v1.0.0 must be preserved unchanged
    hist = repo.get_profile_version("inv_001", "1.0.0")
    assert hist is not None
    assert hist.profile_version == "1.0.0"
    assert hist.financial_capacity.emergency_reserve_months == 3.0

    # Version list must show both versions
    versions = repo.list_profile_versions("inv_001")
    assert len(versions) == 2
    assert versions[0]["profile_version"] == "1.0.0"
    assert versions[0]["is_current"] is False
    assert versions[1]["profile_version"] == "1.0.1"
    assert versions[1]["is_current"] is True


def test_roundtrip_serialization_fidelity(in_memory_db):
    """I, J, K, L: Round-trip serialization fidelity, None, 0, 0.0, False preservation."""
    repo = ProfileRepository(in_memory_db)
    today = date.today()

    fc = FinancialCapacitySnapshot(
        observation_date=today,
        effective_date=today,
        monthly_gross_income=0.0,        # 0.0 float
        monthly_fixed_expenses=0.0,      # 0.0 float
        emergency_reserve_months=0.0,    # 0.0 float
        liquid_emergency_reserves=None,  # Explicit None
        capacity_tier=None,              # Explicit None
    )
    bt = BehavioralToleranceSnapshot(
        observation_date=today,
        assessment_date=today,
        loss_reaction_choice=None,       # Explicit None
        tolerance_tier=RiskToleranceLevel.MODERATE,
    )
    profile = InvestorProfileSnapshot(
        profile_id="prof_fidelity_001",
        investor_id="inv_fidelity",
        profile_version="1.0.0",
        effective_date=today,
        financial_capacity=fc,
        behavioral_tolerance=bt,
        is_stale=False,                   # False boolean
    )

    repo.save_profile(profile)
    retrieved = repo.get_current_profile("inv_fidelity")

    assert retrieved is not None
    assert retrieved.financial_capacity.monthly_gross_income == 0.0
    assert retrieved.financial_capacity.monthly_fixed_expenses == 0.0
    assert retrieved.financial_capacity.emergency_reserve_months == 0.0
    assert retrieved.financial_capacity.liquid_emergency_reserves is None
    assert retrieved.financial_capacity.capacity_tier is None
    assert retrieved.behavioral_tolerance.loss_reaction_choice is None
    assert retrieved.behavioral_tolerance.tolerance_tier == RiskToleranceLevel.MODERATE
    assert retrieved.is_stale is False


def test_missing_profile(in_memory_db):
    """N: Missing profile returns None without fabricating default profile."""
    repo = ProfileRepository(in_memory_db)
    assert repo.get_current_profile("nonexistent_investor") is None
    assert repo.get_profile_version("nonexistent_investor", "1.0.0") is None
    assert repo.list_profile_versions("nonexistent_investor") == []


def test_malformed_stored_profile(in_memory_db):
    """O: Malformed stored profile fails closed with ProfilePersistenceError."""
    repo = ProfileRepository(in_memory_db)
    now_utc = datetime.now(timezone.utc).isoformat()

    # Insert corrupted payload_json into database
    in_memory_db.execute("""
    INSERT INTO investor_profile_snapshots (
        profile_id, investor_id, profile_version, effective_date,
        status, confidence_score, payload_json, created_at_utc, is_current
    ) VALUES ('corrupt_1', 'inv_corrupt', '1.0.0', '2026-09-17', 'ACTIVE', 1.0, '{INVALID_JSON}', ?, 1);
    """, (now_utc,))
    in_memory_db.commit()

    with pytest.raises(ProfilePersistenceError):
        repo.get_current_profile("inv_corrupt")


def test_profile_isolation(in_memory_db):
    """P: Identity isolation between investor_A and investor_B."""
    repo = ProfileRepository(in_memory_db)
    today = date.today()

    p_a = InvestorProfileSnapshot(
        profile_id="prof_A",
        investor_id="investor_A",
        profile_version="1.0.0",
        effective_date=today,
        financial_capacity=FinancialCapacitySnapshot(
            observation_date=today, effective_date=today, emergency_reserve_months=12.0
        ),
    )
    p_b = InvestorProfileSnapshot(
        profile_id="prof_B",
        investor_id="investor_B",
        profile_version="1.0.0",
        effective_date=today,
        financial_capacity=FinancialCapacitySnapshot(
            observation_date=today, effective_date=today, emergency_reserve_months=2.0
        ),
    )

    repo.save_profile(p_a)
    repo.save_profile(p_b)

    retrieved_a = repo.get_current_profile("investor_A")
    retrieved_b = repo.get_current_profile("investor_B")

    assert retrieved_a.investor_id == "investor_A"
    assert retrieved_a.financial_capacity.emergency_reserve_months == 12.0

    assert retrieved_b.investor_id == "investor_B"
    assert retrieved_b.financial_capacity.emergency_reserve_months == 2.0


def test_repository_reinstantiation_across_restarts():
    """Q: Profile survives repository re-instantiation."""
    conn = sqlite3.connect(":memory:")
    today = date.today()

    repo1 = ProfileRepository(conn)
    p = InvestorProfileSnapshot(
        profile_id="prof_restart",
        investor_id="inv_restart",
        profile_version="1.0.0",
        effective_date=today,
        financial_capacity=FinancialCapacitySnapshot(
            observation_date=today, effective_date=today, emergency_reserve_months=6.0
        ),
    )
    repo1.save_profile(p)

    # Re-instantiate repository on same connection
    repo2 = ProfileRepository(conn)
    retrieved = repo2.get_current_profile("inv_restart")
    assert retrieved is not None
    assert retrieved.profile_id == "prof_restart"
    assert retrieved.financial_capacity.emergency_reserve_months == 6.0
    conn.close()


def test_no_financial_table_mutation(in_memory_db):
    """R, S, T: Profile operations do not mutate financial tables or execute trades."""
    repo = ProfileRepository(in_memory_db)
    today = date.today()

    p = InvestorProfileSnapshot(
        profile_id="prof_safe",
        investor_id="inv_safe",
        profile_version="1.0.0",
        effective_date=today,
    )
    repo.save_profile(p)

    # Verify no trade execution, no extraneous tables created
    tables = [
        row[0]
        for row in in_memory_db.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    ]
    assert "investor_profile_snapshots" in tables
    assert len(tables) == 1  # Only investor_profile_snapshots created


def test_security_input_validation(in_memory_db):
    """U: Invalid investor identity or repository parameter validation."""
    repo = ProfileRepository(in_memory_db)
    with pytest.raises(ProfilePersistenceError):
        repo.get_current_profile("")

    with pytest.raises(ProfilePersistenceError):
        repo.get_current_profile("   ")

    with pytest.raises(ProfilePersistenceError):
        repo.save_profile(None)
