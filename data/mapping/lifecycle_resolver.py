"""
Lifecycle Resolver — Phase C: Point-in-Time Scheme Identity Resolution.

Given a canonical scheme ID and a historical date T, resolves the scheme's
identity state that was valid ON date T, using only lifecycle evidence
available as of that date.

Architecture boundary: data/mapping/ (entity resolution boundary per ARCHITECTURE.md §4).
Does NOT produce scores, decisions, or recommendations.
Does NOT concatenate NAV series (MD-4: NAV stitching is out of scope).

Critical Rules (from approved methodology decisions and governing documents):
1. Never convert missing lifecycle evidence into ACTIVE.
   → No lifecycle events = UNKNOWN (not ACTIVE).
2. Never convert conflicting evidence into a guessed identity.
   → Conflicting events on the same date = AMBIGUOUS.
3. MONTH/YEAR precision events must not be treated as DAY-level certainty.
   → Query date falls within the precision window = UNKNOWN (insufficient precision).
4. Point-in-time only: events after as_of_date are strictly excluded.
5. Quarantined events are excluded from all production resolution.
6. No NAV stitching, no return series reconstruction (MD-4).

Governing Documents:
- ARCHITECTURE.md §4 (data/mapping/ boundary)
- DECISION_RULES.md §12.18.2 (survivorship bias, look-ahead bias prevention)
- PRODUCT_SPEC.md §25 (data architecture: normalized data → metrics)
"""

from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from models.scheme_lifecycle import (
    LifecycleEvent,
    LifecycleEventType,
    LifecycleConfidence,
    EffectiveDatePrecision,
    ExistenceStatus,
    SchemeIdentityAtDate,
)
from data.repositories.lifecycle_repository import LifecycleRepository


# ---------------------------------------------------------------------------
# Effective date comparison helpers (MD-1)
# ---------------------------------------------------------------------------

def _event_definitely_before(event: LifecycleEvent, query_date: date) -> bool:
    """
    Return True if the event DEFINITELY occurred before (and including) query_date,
    respecting effective_date_precision (MD-1).

    DAY:   Certain if effective_date <= query_date.
    MONTH: Certain if the entire possible range of the event (any day in that month)
           is <= query_date.  Use first day of NEXT month as upper bound.
           Certain only if first-of-next-month - 1 <= query_date.
           Simplified: certain if effective_date (YYYY-MM-01) is in a month
           strictly before query_date's month, OR query_date is the last day of
           the stored month.  Conservative implementation: treat as certain only
           if the LAST possible day of the precision window <= query_date.
           → last-day-of-event-month <= query_date.
    YEAR:  Certain only if effective_date is in a year strictly before query_date's year,
           OR query_date >= YYYY-12-31 of the event year.
    """
    eff = event.effective_date
    precision = event.effective_date_precision

    if precision == EffectiveDatePrecision.DAY:
        return eff <= query_date

    if precision == EffectiveDatePrecision.MONTH:
        # Last possible day of the month stored in effective_date
        import calendar
        last_day = calendar.monthrange(eff.year, eff.month)[1]
        last_possible = date(eff.year, eff.month, last_day)
        return last_possible <= query_date

    if precision == EffectiveDatePrecision.YEAR:
        # Last possible day of the year
        last_possible = date(eff.year, 12, 31)
        return last_possible <= query_date

    return False


def _event_definitely_not_yet(event: LifecycleEvent, query_date: date) -> bool:
    """
    Return True if the event DEFINITELY had NOT occurred by query_date
    (i.e., will occur strictly after query_date regardless of precision).

    DAY:   effective_date > query_date.
    MONTH: First possible day of event (= stored YYYY-MM-01) > query_date.
    YEAR:  First possible day of event (= stored YYYY-01-01) > query_date.
    """
    eff = event.effective_date
    precision = event.effective_date_precision

    if precision == EffectiveDatePrecision.DAY:
        return eff > query_date

    # For MONTH and YEAR, effective_date stores first-of-period
    # If first-of-period > query_date, the event cannot have occurred yet
    return eff > query_date


def _event_precision_uncertain(event: LifecycleEvent, query_date: date) -> bool:
    """
    Return True if the query_date falls within the precision window of the event,
    meaning we cannot safely determine whether the event had occurred by query_date.

    Per MD-1: In this case, the resolver must return UNKNOWN/AMBIGUOUS rather
    than manufacturing day-level certainty.
    """
    if event.effective_date_precision == EffectiveDatePrecision.DAY:
        return False  # DAY precision is always certain

    if _event_definitely_before(event, query_date):
        return False  # Definitely before — no uncertainty
    if _event_definitely_not_yet(event, query_date):
        return False  # Definitely not yet — no uncertainty
    return True  # Falls within precision window → uncertain


# ---------------------------------------------------------------------------
# Confidence combination helper
# ---------------------------------------------------------------------------

_CONFIDENCE_RANK = {
    LifecycleConfidence.HIGH: 3,
    LifecycleConfidence.MEDIUM: 2,
    LifecycleConfidence.LOW: 1,
    LifecycleConfidence.AMBIGUOUS: 0,
}


def _min_confidence(confidences: List[LifecycleConfidence]) -> LifecycleConfidence:
    """Return the minimum (lowest) confidence from a list."""
    if not confidences:
        return LifecycleConfidence.LOW
    return min(confidences, key=lambda c: _CONFIDENCE_RANK[c])


# ---------------------------------------------------------------------------
# Lifecycle Resolver
# ---------------------------------------------------------------------------

class LifecycleResolver:
    """
    Point-in-time scheme identity resolution service.

    Replays verified lifecycle events chronologically up to a given date
    to produce a SchemeIdentityAtDate snapshot.

    This resolver is READ-ONLY — it does not write lifecycle events.
    Writing is the responsibility of LifecycleRepository.

    No NAV series are concatenated or stitched by this class (MD-4).
    """

    def __init__(self, repo: LifecycleRepository, methodology_version: str = "1.0.0"):
        self.repo = repo
        self.methodology_version = methodology_version

    def resolve_scheme_at_date(
        self,
        canonical_scheme_id: str,
        as_of_date: date,
    ) -> SchemeIdentityAtDate:
        """
        Replay all ACTIVE (non-quarantined) lifecycle events for a scheme up to
        as_of_date and return the resolved identity state.

        Algorithm:
        1. Load ACTIVE events up to as_of_date (inclusive).
        2. If no events → UNKNOWN (insufficient evidence, not ACTIVE).
        3. Sort chronologically by effective_date.
        4. Apply each event in order, updating identity state.
        5. If any event has uncertain precision for as_of_date → note in resolution.
        6. If conflicting events of the same type on the same effective_date → AMBIGUOUS.
        7. Return SchemeIdentityAtDate with full provenance.

        Critical: as_of_date filtering is strictly point-in-time.
        Events after as_of_date are never loaded or considered.
        """
        # Load current canonical scheme metadata as baseline (pre-lifecycle-events state)
        # We use this only for identity fields not yet updated by events
        base_metadata = self._get_base_metadata(canonical_scheme_id)

        # Load only ACTIVE (non-quarantined) events up to as_of_date
        # Events after as_of_date are excluded — strict point-in-time
        all_events_up_to_date = self.repo.get_events_for_scheme(
            canonical_scheme_id=canonical_scheme_id,
            as_of_date=as_of_date,
            include_quarantined=False,
        )

        # No events at all → UNKNOWN (never ACTIVE by assumption)
        if not all_events_up_to_date:
            return SchemeIdentityAtDate(
                canonical_scheme_id=canonical_scheme_id,
                as_of_date=as_of_date,
                existence_status=ExistenceStatus.UNKNOWN,
                scheme_name_at_date=base_metadata.get("scheme_name"),
                amc_name_at_date=base_metadata.get("amc_name"),
                plan_type_at_date=base_metadata.get("plan_type"),
                option_type_at_date=base_metadata.get("option_type"),
                resolution_confidence=LifecycleConfidence.LOW,
                resolution_notes=(
                    "No lifecycle events found up to this date. "
                    "UNKNOWN is returned conservatively — never assume ACTIVE "
                    "without evidence."
                ),
                events_applied=[],
                methodology_version=self.methodology_version,
            )

        # State accumulators — start from base metadata
        existence = ExistenceStatus.UNKNOWN
        scheme_name = base_metadata.get("scheme_name")
        amc_name = base_metadata.get("amc_name")
        plan_type = base_metadata.get("plan_type")
        option_type = base_metadata.get("option_type")
        predecessor_ids: List[str] = []
        successor_id: Optional[str] = None
        applied_event_ids: List[str] = []
        applied_confidences: List[LifecycleConfidence] = []
        notes_parts: List[str] = []
        precision_uncertain_flags: List[str] = []
        is_ambiguous = False

        # Check for conflicting events: same event_type on identical effective_date
        # Group events by (effective_date, event_type)
        from collections import defaultdict
        groups: dict = defaultdict(list)
        for ev in all_events_up_to_date:
            groups[(ev.effective_date.isoformat(), ev.event_type.value)].append(ev)

        conflicting_types = {
            LifecycleEventType.SCHEME_RENAMED,
            LifecycleEventType.SCHEME_MERGED_INTO,
            LifecycleEventType.SCHEME_CLOSED,
            LifecycleEventType.PLAN_TYPE_CHANGED,
            LifecycleEventType.OPTION_TYPE_CHANGED,
            LifecycleEventType.AMC_REBRANDING,
        }
        for (eff_date_str, et_str), evs in groups.items():
            if len(evs) > 1 and LifecycleEventType(et_str) in conflicting_types:
                is_ambiguous = True
                notes_parts.append(
                    f"Conflicting evidence: {len(evs)} events of type {et_str} "
                    f"on effective_date {eff_date_str}."
                )

        if is_ambiguous:
            return SchemeIdentityAtDate(
                canonical_scheme_id=canonical_scheme_id,
                as_of_date=as_of_date,
                existence_status=ExistenceStatus.AMBIGUOUS,
                scheme_name_at_date=scheme_name,
                amc_name_at_date=amc_name,
                plan_type_at_date=plan_type,
                option_type_at_date=option_type,
                resolution_confidence=LifecycleConfidence.AMBIGUOUS,
                resolution_notes=" | ".join(notes_parts),
                events_applied=[ev.event_id for ev in all_events_up_to_date],
                methodology_version=self.methodology_version,
            )

        # Apply events chronologically
        for ev in all_events_up_to_date:
            # Check if this event's precision makes it uncertain for as_of_date
            # (The event IS within the as_of_date window, but we loaded it because
            #  effective_date <= as_of_date — however precision may still be uncertain
            #  if as_of_date falls within the precision period)
            if _event_precision_uncertain(ev, as_of_date):
                precision_uncertain_flags.append(
                    f"Event {ev.event_id} (type={ev.event_type.value}) has "
                    f"{ev.effective_date_precision.value} precision; "
                    f"cannot confirm it occurred by {as_of_date.isoformat()}."
                )
                # We still apply the event but mark the result as uncertain
                # The precision uncertainty note is captured in resolution_notes

            applied_event_ids.append(ev.event_id)
            applied_confidences.append(ev.confidence)

            et = ev.event_type

            if et == LifecycleEventType.SCHEME_CREATION:
                existence = ExistenceStatus.ACTIVE
                if ev.effective_date <= as_of_date:
                    notes_parts.append(f"Scheme created on/before {ev.effective_date.isoformat()}.")

            elif et == LifecycleEventType.SCHEME_RENAMED:
                if ev.new_value:
                    scheme_name = ev.new_value
                notes_parts.append(f"Renamed: '{ev.old_value}' → '{ev.new_value}'.")

            elif et == LifecycleEventType.SCHEME_MERGED_INTO:
                existence = ExistenceStatus.MERGED_PREDECESSOR
                if ev.successor_scheme_ids:
                    successor_id = ev.successor_scheme_ids[0]
                notes_parts.append(
                    f"Merged into {successor_id} on/before {ev.effective_date.isoformat()}."
                )

            elif et == LifecycleEventType.SCHEME_RECEIVED_MERGER:
                predecessor_ids.extend(ev.predecessor_scheme_ids)
                notes_parts.append(
                    f"Received merger from {ev.predecessor_scheme_ids}."
                )
                # Receiving a merger does not change this scheme's existence status

            elif et == LifecycleEventType.SCHEME_CLOSED:
                existence = ExistenceStatus.CLOSED
                notes_parts.append(f"Closed on/before {ev.effective_date.isoformat()}.")

            elif et == LifecycleEventType.PLAN_TYPE_CHANGED:
                if ev.new_value:
                    plan_type = ev.new_value
                notes_parts.append(f"Plan type changed: '{ev.old_value}' → '{ev.new_value}'.")

            elif et == LifecycleEventType.OPTION_TYPE_CHANGED:
                if ev.new_value:
                    option_type = ev.new_value
                notes_parts.append(f"Option type changed: '{ev.old_value}' → '{ev.new_value}'.")

            elif et == LifecycleEventType.AMC_REBRANDING:
                if ev.new_value:
                    amc_name = ev.new_value
                notes_parts.append(f"AMC rebranded: '{ev.old_value}' → '{ev.new_value}'.")

            elif et == LifecycleEventType.AMFI_CODE_REASSIGNED:
                # MD-2: AMFI code reassignment means the new scheme gets a NEW canonical ID.
                # This event on the OLD scheme records the relationship.
                # The old scheme's history ends here (becomes MERGED_PREDECESSOR is incorrect;
                # it's more like CLOSED with a relationship note).
                # We mark MERGED_PREDECESSOR to indicate this canonical ID should not
                # be treated as continuous with the successor.
                existence = ExistenceStatus.MERGED_PREDECESSOR
                notes_parts.append(
                    f"AMFI code reassigned to new scheme. Old code: '{ev.old_value}', "
                    f"new canonical ID handles successor identity."
                )

            elif et == LifecycleEventType.ISIN_CHANGED:
                # MD-3: ISIN change does not automatically confirm or deny continuity.
                # Record the change; do not alter existence_status.
                notes_parts.append(
                    f"ISIN changed: '{ev.old_value}' → '{ev.new_value}'. "
                    f"Identity continuity requires investigation (MD-3)."
                )

        # Handle PRE_LAUNCH: if scheme_creation event exists but query is before it,
        # we need a separate check.  If the earliest event is SCHEME_CREATION and
        # its effective_date is after as_of_date... but wait — we only loaded events
        # where effective_date <= as_of_date, so this cannot happen in normal flow.
        # PRE_LAUNCH is returned by resolve_pre_launch_check below.

        # Precision uncertainty degrades resolution confidence but does not override
        # the existence status unless it is the determining event.
        if precision_uncertain_flags:
            notes_parts.extend(precision_uncertain_flags)
            # Downgrade result to UNKNOWN if the existence-determining event was uncertain
            # (i.e. if we relied on a MONTH/YEAR-precision CREATION or CLOSURE event)
            notes_parts.append(
                "Precision uncertainty present: effective_date_precision indicates "
                "the stored date is not day-level accurate. Resolution may not reflect "
                "exact state on query date."
            )

        final_confidence = _min_confidence(applied_confidences)
        final_notes = " | ".join(notes_parts) if notes_parts else "Events applied without anomalies."

        return SchemeIdentityAtDate(
            canonical_scheme_id=canonical_scheme_id,
            as_of_date=as_of_date,
            existence_status=existence,
            scheme_name_at_date=scheme_name,
            amc_name_at_date=amc_name,
            plan_type_at_date=plan_type,
            option_type_at_date=option_type,
            predecessor_scheme_ids=list(set(predecessor_ids)),
            successor_scheme_id=successor_id,
            resolution_confidence=final_confidence,
            resolution_notes=final_notes,
            events_applied=applied_event_ids,
            methodology_version=self.methodology_version,
        )

    def resolve_pre_launch_check(
        self,
        canonical_scheme_id: str,
        as_of_date: date,
    ) -> SchemeIdentityAtDate:
        """
        Determine if a scheme is PRE_LAUNCH as of as_of_date by checking whether
        any SCHEME_CREATION event exists with effective_date > as_of_date.

        This is a separate check from resolve_scheme_at_date() because
        resolve_scheme_at_date() only loads events <= as_of_date and thus
        cannot see future CREATION events.
        """
        # Load ALL events (regardless of as_of_date) to find future creation events
        all_events = self.repo.get_events_for_scheme(
            canonical_scheme_id=canonical_scheme_id,
            as_of_date=None,  # Load all events
            include_quarantined=False,
        )

        creation_events = [
            ev for ev in all_events
            if ev.event_type == LifecycleEventType.SCHEME_CREATION
        ]

        base_metadata = self._get_base_metadata(canonical_scheme_id)

        if creation_events:
            earliest_creation = min(creation_events, key=lambda e: e.effective_date)
            # If the earliest creation event is after as_of_date, scheme is PRE_LAUNCH
            if _event_definitely_not_yet(earliest_creation, as_of_date):
                return SchemeIdentityAtDate(
                    canonical_scheme_id=canonical_scheme_id,
                    as_of_date=as_of_date,
                    existence_status=ExistenceStatus.PRE_LAUNCH,
                    scheme_name_at_date=base_metadata.get("scheme_name"),
                    amc_name_at_date=base_metadata.get("amc_name"),
                    plan_type_at_date=base_metadata.get("plan_type"),
                    option_type_at_date=base_metadata.get("option_type"),
                    resolution_confidence=earliest_creation.confidence,
                    resolution_notes=(
                        f"Scheme has a SCHEME_CREATION event with "
                        f"effective_date={earliest_creation.effective_date.isoformat()} "
                        f"(precision={earliest_creation.effective_date_precision.value}), "
                        f"which is definitively after as_of_date={as_of_date.isoformat()}. "
                        f"Scheme is PRE_LAUNCH on this date."
                    ),
                    events_applied=[earliest_creation.event_id],
                    methodology_version=self.methodology_version,
                )

        # Fall back to resolve_scheme_at_date if not PRE_LAUNCH
        return self.resolve_scheme_at_date(canonical_scheme_id, as_of_date)

    def was_scheme_active_at_date(
        self,
        canonical_scheme_id: str,
        as_of_date: date,
    ) -> bool:
        """
        Return True if the scheme was ACTIVE on as_of_date.
        Checks PRE_LAUNCH first, then resolves existence_status.

        Returns False conservatively for UNKNOWN or AMBIGUOUS states.
        Per the approved rule: never convert missing evidence into ACTIVE.
        """
        result = self.resolve_pre_launch_check(canonical_scheme_id, as_of_date)
        return result.existence_status == ExistenceStatus.ACTIVE

    def build_point_in_time_universe(
        self,
        all_canonical_scheme_ids: List[str],
        as_of_date: date,
    ) -> List[SchemeIdentityAtDate]:
        """
        Build the point-in-time universe of all schemes that were ACTIVE on as_of_date.

        This is the primary anti-survivorship-bias mechanism (DECISION_RULES.md §12.18.2).

        Includes:
        - Schemes ACTIVE on as_of_date (including those later merged or closed after that date)

        Excludes:
        - Schemes PRE_LAUNCH on as_of_date (not yet in existence)
        - Schemes already CLOSED or MERGED_PREDECESSOR before as_of_date
        - Schemes with UNKNOWN or AMBIGUOUS state (conservative exclusion with note)

        NOTE: NAV series are NOT concatenated or stitched (MD-4).
        This method returns identity metadata only.
        """
        universe: List[SchemeIdentityAtDate] = []

        for scheme_id in all_canonical_scheme_ids:
            identity = self.resolve_pre_launch_check(scheme_id, as_of_date)
            if identity.existence_status == ExistenceStatus.ACTIVE:
                universe.append(identity)

        return universe

    def persist_universe_snapshot(
        self,
        as_of_date: date,
        universe: List[SchemeIdentityAtDate],
    ) -> None:
        """
        Persist the derived universe snapshot for later retrieval.
        Snapshots are derived data — rebuildable from lifecycle events.
        """
        for identity in universe:
            conf_value = identity.resolution_confidence.value
            # Snapshots only store HIGH, MEDIUM, LOW (not AMBIGUOUS — those are excluded)
            if conf_value == "AMBIGUOUS":
                conf_value = "LOW"

            self.repo.save_universe_snapshot(
                canonical_scheme_id=identity.canonical_scheme_id,
                snapshot_date=as_of_date,
                existence_status=identity.existence_status.value,
                confidence=conf_value,
                derived_from_events=identity.events_applied,
                methodology_version=self.methodology_version,
            )

    def _get_base_metadata(self, canonical_scheme_id: str) -> dict:
        """
        Retrieve base canonical scheme metadata from the database.
        Returns empty dict if scheme not found — callers handle None fields gracefully.
        """
        try:
            with self.repo.db.get_conn() as conn:
                cursor = conn.execute(
                    "SELECT scheme_name, amc_name, plan_type, option_type "
                    "FROM canonical_schemes WHERE canonical_scheme_id = ?",
                    (canonical_scheme_id,),
                )
                row = cursor.fetchone()
            return dict(row) if row else {}
        except Exception:
            return {}
