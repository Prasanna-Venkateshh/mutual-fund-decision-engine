# Investor Profile & Session Persistence Specification V1

**Document ID**: `docs/INVESTOR_PROFILE_PERSISTENCE_V1.md`  
**Feature Scope**: V1 Step 1 — Persistent Investor Profile Storage & Session Integration  
**Governance Standard**: Governed Product Infrastructure  
**Date**: September 2026 UTC  

---

## 1. Purpose

This document defines the technical specification for **Investor Profile & Session Persistence (V1 Step 1)** in the Mutual Fund Decision Engine. Prior to this implementation, onboarding questionnaire responses instantiated in-memory `InvestorProfileSnapshot` objects that were lost upon application restart. This feature provides durable, privacy-conscious, deterministic persistence so that an investor's governed profile survives application and session restarts.

---

## 2. Scope & Boundaries

### IN SCOPE (V1 Step 1)
- Persistent SQLite storage for `InvestorProfileSnapshot` objects.
- Repository layer (`ProfileRepository` in `data/repositories/profile_repository.py`).
- Deterministic JSON round-trip serialization preserving `None`, `0`, `0.0`, and `False` semantics.
- Append-only version history (`profile_version`, `is_current`, `created_at_utc`).
- Onboarding integration in web presentation layer (`web/adapters.py` and `web/app.py`).
- Explicit investor identity isolation (`investor_id`).
- Migration and schema compatibility.
- Comprehensive test suite and forensic verification.

### OUT OF SCOPE (Deferred to Subsequent Steps / V2)
- Production authentication / password login / JWT tokens (Authentication is NOT implemented by this feature).
- Portfolio transaction CSV/CAS ingestion (V1 Step 2).
- Cloud production security gateway (V1 Step 3).
- Automated trade execution or broker integration (Strictly prohibited).
- Financial calculation logic changes (Strictly frozen).

---

## 3. Profile Data Contract

The canonical data contract for investor profile persistence is **`InvestorProfileSnapshot`** ([`models/investor_profile.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/models/investor_profile.py)):

```python
@dataclass(frozen=True)
class InvestorProfileSnapshot:
    profile_id: str
    investor_id: str
    profile_version: str
    effective_date: date
    birth_date: Optional[date] = None
    financial_capacity: Optional[FinancialCapacitySnapshot] = None
    behavioral_tolerance: Optional[BehavioralToleranceSnapshot] = None
    overall_effective_risk_alignment: Optional[RiskCapacityLevel] = None
    profiling_tier_completed: int = 1
    status: ProfileStatus = ProfileStatus.ACTIVE
    confidence_score: float = 1.0
    provenance: Optional[ProvenanceMetadata] = None
    created_timestamp_utc: Optional[datetime] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"
    is_stale: bool = False
```

- **Immutability**: `frozen=True` ensures profile snapshots cannot be mutated in place. Updates construct a new versioned instance.
- **Nullability Governance**: Missing inputs remain explicitly `None` (never defaulted to 0 or False).

---

## 4. Storage Model & Database Schema

Profiles are stored in SQLite database file `db/backfill_f12_2.db` under table `investor_profile_snapshots`:

```sql
CREATE TABLE IF NOT EXISTS investor_profile_snapshots (
    profile_id TEXT PRIMARY KEY,
    investor_id TEXT NOT NULL,
    profile_version TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    payload_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1,
    UNIQUE(investor_id, profile_version)
);
```

### Migration Safety
- Schema initialization in `ProfileRepository._init_tables()` performs additive migration, checking `PRAGMA table_info` and adding `is_current` if missing.
- Zero existing financial tables (`canonical_schemes`, `normalized_nav_records`, etc.) are modified or deleted.

---

## 5. Versioning & Living Profile Architecture

To preserve historical assessment reproducibility, updating an investor profile does not overwrite historical records:

1. **Current Profile Selection**: The active version has `is_current = 1`.
2. **Append-Only History**: When a profile is updated, all previous snapshots for `investor_id` are set to `is_current = 0`, and the new snapshot is stored with `is_current = 1`.
3. **Version String**: Initial version defaults to `"1.0.0"`. Subsequent updates increment patch versions (`"1.0.1"`, `"1.0.2"`).

---

## 6. Repository API (`ProfileRepository`)

Location: [`data/repositories/profile_repository.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/repositories/profile_repository.py)

| Method | Parameters | Return Type | Description |
| :--- | :--- | :--- | :--- |
| `save_profile` | `profile: InvestorProfileSnapshot` | `str` | Persists snapshot, updates `is_current` flags, returns `profile_id`. |
| `get_current_profile` | `investor_id: str` | `Optional[InvestorProfileSnapshot]` | Retrieves latest active profile for `investor_id` or `None`. |
| `get_profile_version` | `investor_id: str, profile_version: str` | `Optional[InvestorProfileSnapshot]` | Retrieves specific historical version or `None`. |
| `list_profile_versions` | `investor_id: str` | `List[Dict[str, Any]]` | Lists all version metadata ordered by creation timestamp. |

---

## 7. Round-Trip Serialization Rules

- **`None` Preservation**: `None` values serialize to JSON `null` and deserialize back to `None`.
- **Numeric Fidelity**: `0` remains integer `0`, `0.0` remains float `0.0`.
- **Boolean Fidelity**: `False` remains boolean `False`.
- **Enum Preservation**: `RiskCapacityLevel`, `RiskToleranceLevel`, and `ProfileStatus` serialize as `.value` strings and deserialize back to exact Enum members.
- **ISO Dates**: `date` and `datetime` serialize to ISO format strings (`YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SS.mmmmmm+00:00`).

---

## 8. Privacy & Data Minimization

- Profile payloads contain sensitive financial information (income, emergency reserve months).
- General application logs log ONLY: `investor_id`, `profile_id`, `profile_version`, and non-sensitive operation status.
- Complete profile payloads are NEVER emitted to standard application log streams or unhandled exception traces.

---

## 9. Error Handling

- **`ProfilePersistenceError`**: Raised on database locking, corrupt JSON payloads, or invalid input types.
- **Fail Closed**: Corrupted or malformed stored payloads raise explicit exceptions instead of fabricating default or empty profiles.

---

## 10. Session & Investor Identity Boundary

- Authentication is **NOT** part of this step.
- The repository API requires an explicit `investor_id` parameter (`get_current_profile(investor_id)`). Un-parameterized global retrieval is prohibited to prevent accidental data cross-talk.
- In local development web execution (`web/app.py`), a deterministic session identifier (`investor_dev_default`) is passed.

---

## 11. Onboarding Integration

- Onboarding screen `/onboarding` (SCR-01) submits responses via `POST /onboarding`.
- [`web/adapters.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/web/adapters.py) (`QuestionnaireAdapter`) converts responses to `InvestorProfileSnapshot`.
- Profile is saved to database via `ProfileRepository`.
- Returning to `/onboarding` or `/settings` (SCR-10) retrieves the persisted snapshot and renders saved profile attributes and version audit trail.

---

## 12. Material Change Safety

- Profile persistence stores user questionnaire inputs ONLY.
- Saving a profile does NOT automatically trigger trade execution, portfolio mutation, or silent acceptance of recommendations.
- Downstream decision engines (`RiskAlignmentEngine`, `SuitabilityEngine`, `DecisionOrchestrator`) evaluate profiles dynamically upon assessment request.

---

## 13. Audit Trail Interaction

- Profile snapshots preserve point-in-time state for auditability.
- Decision assessment audit log (`assessment_audit_log` in `audit/user_decision_state.py`) references `profile_version_used`, establishing 100% historical decision reproducibility.

---

## 14. Test Suite & Verification

- Unit & integration suite: [`tests/integration/test_investor_profile_persistence.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/integration/test_investor_profile_persistence.py) (11 tests, 100% passing).
- Covers all 21 test requirements (A through U).
- Zero regression on existing 1,492 financial and data quality tests.

---

## 15. Authentication Boundary Statement

> [!WARNING]
> **Authentication is NOT implemented by this feature.**
> Session investor identifiers (`investor_id`) provide identity boundary scoping within the repository API, but DO NOT constitute production user authentication, password verification, or access control. Production authentication will be implemented in Step 3.
