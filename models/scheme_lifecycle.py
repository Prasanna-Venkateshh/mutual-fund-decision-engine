"""
Scheme Lifecycle Data Models — Phase C: Point-in-Time Scheme Identity.

Provides the canonical data model for historical scheme lifecycle events
and point-in-time identity resolution outputs.

Governing Documents:
- ARCHITECTURE.md §4 (data/mapping/ boundary), §11 (Historical State & Immutable Audit Records)
- PRODUCT_SPEC.md §24 (Evidence / Source Provenance Layer), §25 (Data Architecture)
- DECISION_RULES.md §12.18.2 (Bias Prevention Safeguards)
- DATA_SOURCES.md fields J–N (Lifecycle Status, Merger, Closure, Rename, Plan/Option Changes)

Phase C Scope Boundary:
- INCLUDES: point-in-time scheme identity, lifecycle events, relationships, provenance,
  confidence, quarantine, historical universe membership.
- EXCLUDES: Fund Quality Scoring, suitability, portfolio allocation, Buy/Hold/Sell,
  tax, TER, benchmarks, backtesting, UI, NAV stitching.

Methodology Decisions (approved 2026-09-08):
- MD-1: Effective date stored as YYYY-MM-01 (MONTH precision) or YYYY-01-01 (YEAR precision).
  The stored date is a storage representation only; downstream resolution must respect precision.
- MD-2: AMFI scheme code reuse always creates a new canonical_scheme_id when evidence establishes
  that the economic entity genuinely differs.
- MD-3: ISIN change triggers investigation; does not automatically create or continue a canonical ID.
- MD-4: NAV stitching across mergers is explicitly out of scope.
- MD-5: data/ingestion/historical_nav_pipeline.py is not modified by Phase C.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List


# ---------------------------------------------------------------------------
# Lifecycle Event Types
# ---------------------------------------------------------------------------

class LifecycleEventType(Enum):
    """
    Supported scheme lifecycle event types.

    Each type has distinct identity implications and must NOT be collapsed
    into a generic 'change' event.  The system must not manufacture events
    without verified evidence from authoritative sources (AMFI, SEBI, AMC).

    Reference: DATA_SOURCES.md fields J (lifecycle status), K (mergers),
    L (closures), M (renames), N (plan/option changes).
    All fields are classified 'DATA SOURCE TO BE VALIDATED' — no event
    should be stored without a traceable source reference.
    """

    SCHEME_CREATION = "SCHEME_CREATION"
    """Scheme first appeared / came into existence.
    NAV implication: new independent NAV series begins."""

    SCHEME_RENAMED = "SCHEME_RENAMED"
    """Name changed; economic identity continues under same canonical ID.
    NAV implication: same NAV series continues; no discontinuity."""

    SCHEME_MERGED_INTO = "SCHEME_MERGED_INTO"
    """This scheme was absorbed into a successor scheme.
    NAV implication: this scheme's NAV records are preserved up to effective_date.
    NO automatic stitching to successor NAV series (MD-4)."""

    SCHEME_RECEIVED_MERGER = "SCHEME_RECEIVED_MERGER"
    """This scheme absorbed one or more predecessor schemes.
    NAV implication: this scheme's own NAV series continues from its own start date.
    Predecessor NAV series remain under their own canonical IDs (MD-4)."""

    SCHEME_CLOSED = "SCHEME_CLOSED"
    """Scheme wound up; no successor.  canonical_schemes.lifecycle_status → CLOSED.
    NAV implication: NAV records are preserved up to closure date."""

    PLAN_TYPE_CHANGED = "PLAN_TYPE_CHANGED"
    """Direct/Regular plan type changed on same economic fund.
    NAV implication: NAV series continues under same canonical ID; plan_type metadata updated."""

    OPTION_TYPE_CHANGED = "OPTION_TYPE_CHANGED"
    """Growth/IDCW option changed on same economic fund.
    NAV implication: NAV series continues under same canonical ID; option_type metadata updated."""

    AMC_REBRANDING = "AMC_REBRANDING"
    """AMC name changed (e.g. merger/acquisition of AMC); underlying fund unchanged.
    NAV implication: NAV series continues; amc_name metadata updated."""

    AMFI_CODE_REASSIGNED = "AMFI_CODE_REASSIGNED"
    """AMFI scheme code was reused or reassigned to a genuinely different economic scheme.
    Per MD-2: a NEW canonical_scheme_id must be created for the new scheme.
    Historical observations under the old canonical ID are preserved without modification.
    This event records the relationship between old and new canonical IDs."""

    ISIN_CHANGED = "ISIN_CHANGED"
    """ISIN changed on a scheme.  Per MD-3:
    - Does not automatically create a new canonical ID.
    - Does not automatically confirm identity continuity.
    - Triggers investigation; confidence reflects the actual evidence.
    - Conflicting evidence → AMBIGUOUS / quarantined."""


# ---------------------------------------------------------------------------
# Confidence States
# ---------------------------------------------------------------------------

class LifecycleConfidence(Enum):
    """
    Confidence in a lifecycle event record.

    Mirrors the spirit of MappingConfidence (models/scheme.py) but is distinct
    because lifecycle events have different evidence requirements.

    LOW confidence ≠ AMBIGUOUS.
    - LOW means evidence is weak but directionally consistent (single uncontested source).
    - AMBIGUOUS means evidence conflicts or identity cannot safely be resolved.

    Per ARCHITECTURE.md §4: ambiguous/quarantined records cannot silently flow
    downstream into metrics, scoring, or recommendation engines.
    """

    HIGH = "HIGH"
    """Multi-attribute corroboration from independent authoritative sources
    (e.g., AMFI gazette notice + ISIN change + scheme code change all consistent)."""

    MEDIUM = "MEDIUM"
    """Single authoritative source with at least one supporting attribute."""

    LOW = "LOW"
    """Single source, no corroboration.  Stored but must be manually reviewed
    before being promoted and used in point-in-time universe construction."""

    AMBIGUOUS = "AMBIGUOUS"
    """Conflicting evidence from multiple sources, or identity cannot be safely
    resolved.  Events with this confidence are automatically quarantined and
    must never be used in production resolution without explicit human review."""


# ---------------------------------------------------------------------------
# Effective Date Precision (MD-1)
# ---------------------------------------------------------------------------

class EffectiveDatePrecision(Enum):
    """
    Precision of the stored effective_date field.

    Per MD-1 (approved 2026-09-08):
    - DAY:   Exact date known from authoritative source document.
    - MONTH: Only month/year known; effective_date stored as YYYY-MM-01.
             The '01' is a storage representation, NOT a claim the event occurred on the 1st.
    - YEAR:  Only year known; effective_date stored as YYYY-01-01.
             The '01-01' is a storage representation, NOT a claim the event occurred on Jan 1.

    Downstream resolution MUST NOT convert MONTH or YEAR precision events to DAY-level
    certainty.  If the precision is insufficient to safely determine historical state
    for a specific query date, the resolver must return UNKNOWN or AMBIGUOUS.
    """

    DAY = "DAY"
    MONTH = "MONTH"
    YEAR = "YEAR"


# ---------------------------------------------------------------------------
# Existence Status (used in identity resolution output)
# ---------------------------------------------------------------------------

class ExistenceStatus(Enum):
    """
    Point-in-time existence state of a scheme at a specific historical date.

    Used in SchemeIdentityAtDate (resolver output) and scheme_universe_snapshots.

    Per the approved critical rule:
    - Never convert missing lifecycle evidence into ACTIVE.
    - Never convert conflicting evidence into a guessed identity.
    - UNKNOWN and AMBIGUOUS are explicit, legitimate output states.
    """

    ACTIVE = "ACTIVE"
    """Scheme was trading and receiving subscriptions on this date."""

    MERGED_PREDECESSOR = "MERGED_PREDECESSOR"
    """Scheme had been absorbed into a successor scheme by this date."""

    CLOSED = "CLOSED"
    """Scheme had been wound up by this date; no successor."""

    PRE_LAUNCH = "PRE_LAUNCH"
    """Scheme had not yet launched / come into existence by this date."""

    UNKNOWN = "UNKNOWN"
    """Insufficient lifecycle evidence to determine state.
    No lifecycle events recorded, or evidence precision too coarse for the query date.
    This is a conservative, safe state — never assume ACTIVE when UNKNOWN."""

    AMBIGUOUS = "AMBIGUOUS"
    """Lifecycle evidence exists but conflicts; identity cannot safely be resolved.
    Distinct from UNKNOWN: UNKNOWN means no evidence; AMBIGUOUS means conflicting evidence."""


# ---------------------------------------------------------------------------
# Core Lifecycle Event Dataclass
# ---------------------------------------------------------------------------

@dataclass
class LifecycleEvent:
    """
    A single point-in-time lifecycle event for a canonical mutual fund scheme.

    Provenance requirements (ARCHITECTURE.md §11, PRODUCT_SPEC.md §24):
    - source_id, source_document_url, retrieval_timestamp_utc must be populated.
    - methodology_version must identify the extraction logic version.
    - Missing provenance means the event cannot be used in production resolution.

    Identity key: canonical_scheme_id (NOT ISIN — ISINs are optional and not universally assigned).

    Merger relationship encoding:
    - For SCHEME_MERGED_INTO events: predecessor_scheme_ids=[], successor_scheme_ids=[successor]
    - For SCHEME_RECEIVED_MERGER events: predecessor_scheme_ids=[p1, p2...], successor_scheme_ids=[]
    - Supports both 1:1 and N:1 mergers via list fields.

    NAV stitching (MD-4): This class records the identity relationship only.
    It does NOT imply any concatenation of NAV series across predecessor/successor boundaries.
    """

    # --- Identity ---
    event_id: str
    """Unique surrogate key (UUID or deterministic hash). Idempotent on re-insert."""

    canonical_scheme_id: str
    """FK → canonical_schemes.canonical_scheme_id. NOT ISIN."""

    # --- Event Semantics ---
    event_type: LifecycleEventType

    # --- Effective Date (MD-1) ---
    effective_date: date
    """Date the event took effect.
    Storage convention per MD-1:
    - DAY precision: actual date.
    - MONTH precision: YYYY-MM-01 (first of month as storage representation).
    - YEAR precision:  YYYY-01-01 (first of year as storage representation).
    The stored date is NOT a claim of day-level accuracy."""

    effective_date_precision: EffectiveDatePrecision
    """Mandatory.  Callers must check this before performing day-level comparisons."""

    # --- Provenance (ARCHITECTURE.md §11 mandatory fields) ---
    source_id: str
    """FK → source_registry.source_id."""

    retrieval_timestamp_utc: datetime
    """UTC timestamp when the authoritative source document was fetched."""

    methodology_version: str
    """Version of the lifecycle extraction/recording methodology (e.g. '1.0.0')."""

    # --- Confidence & Status ---
    confidence: LifecycleConfidence

    status: str
    """'ACTIVE' or 'QUARANTINED'.
    AMBIGUOUS confidence → automatically quarantined on creation.
    Only ACTIVE events are used in production resolution."""

    # --- Optional Provenance ---
    source_document_url: Optional[str] = None
    """Direct URL to the authoritative source document (AMFI gazette, AMC notice, SEBI circular).
    Required for HIGH and MEDIUM confidence events where a URL is available."""

    # --- Relationship Fields (Merger/Rename) ---
    predecessor_scheme_ids: List[str] = field(default_factory=list)
    """canonical_scheme_ids of schemes that fed into this scheme (for SCHEME_RECEIVED_MERGER).
    Empty list for all other event types."""

    successor_scheme_ids: List[str] = field(default_factory=list)
    """canonical_scheme_ids of schemes this scheme was absorbed into (for SCHEME_MERGED_INTO).
    Empty list for all other event types."""

    old_value: Optional[str] = None
    """Previous value for SCHEME_RENAMED, PLAN_TYPE_CHANGED, OPTION_TYPE_CHANGED,
    AMC_REBRANDING, AMFI_CODE_REASSIGNED, ISIN_CHANGED events."""

    new_value: Optional[str] = None
    """New value for same event types listed above."""

    # --- Quarantine ---
    quarantine_reason: Optional[str] = None
    """Populated when status = 'QUARANTINED'.  Documents why the event cannot be used."""

    # --- Audit ---
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    """UTC timestamp of DB insertion."""

    def __post_init__(self):
        """Validate mandatory provenance fields on construction."""
        if not self.source_id:
            raise ValueError(
                f"LifecycleEvent {self.event_id}: source_id is required for provenance. "
                "An event without a verified source cannot be used in production."
            )
        if not self.methodology_version:
            raise ValueError(
                f"LifecycleEvent {self.event_id}: methodology_version is required. "
                "Every event must carry the version of the extraction methodology."
            )
        # Enforce: AMBIGUOUS confidence → quarantined
        if self.confidence == LifecycleConfidence.AMBIGUOUS and self.status != "QUARANTINED":
            raise ValueError(
                f"LifecycleEvent {self.event_id}: confidence=AMBIGUOUS requires status='QUARANTINED'. "
                "Ambiguous events must never silently enter production resolution."
            )


# ---------------------------------------------------------------------------
# Identity Resolution Output
# ---------------------------------------------------------------------------

@dataclass
class SchemeIdentityAtDate:
    """
    The resolved point-in-time identity state of a scheme as of a specific historical date.

    Output of LifecycleResolver.resolve_scheme_at_date().

    This is a read-only snapshot of what was true about the scheme on as_of_date.
    It does NOT contain any NAV series, return calculations, or metrics.

    Critical point-in-time rule: this object must only contain information that
    was valid on as_of_date, never information from after that date.
    """

    canonical_scheme_id: str
    as_of_date: date

    # --- Resolved State ---
    existence_status: ExistenceStatus
    """The scheme's existence state on as_of_date.
    UNKNOWN means insufficient evidence — never assume ACTIVE."""

    scheme_name_at_date: Optional[str] = None
    """Name valid on as_of_date, reflecting any renames before that date."""

    amc_name_at_date: Optional[str] = None
    """AMC name valid on as_of_date, reflecting any AMC rebranding before that date."""

    plan_type_at_date: Optional[str] = None
    """Plan type (DIRECT/REGULAR/UNKNOWN) valid on as_of_date."""

    option_type_at_date: Optional[str] = None
    """Option type (GROWTH/IDCW/UNKNOWN) valid on as_of_date."""

    # --- Relationships ---
    predecessor_scheme_ids: List[str] = field(default_factory=list)
    """Schemes merged INTO this scheme as of as_of_date (populated for SCHEME_RECEIVED_MERGER)."""

    successor_scheme_id: Optional[str] = None
    """The scheme this scheme was merged into, if applicable and known by as_of_date."""

    # --- Resolution Metadata ---
    resolution_confidence: LifecycleConfidence = LifecycleConfidence.LOW
    """Lowest confidence level among applied events.  HIGH only if all events are HIGH."""

    resolution_notes: str = ""
    """Human-readable explanation of how the state was determined."""

    events_applied: List[str] = field(default_factory=list)
    """event_ids that contributed to this resolved state (for provenance/audit)."""

    methodology_version: str = "1.0.0"
    """Version of the lifecycle resolution methodology used."""
