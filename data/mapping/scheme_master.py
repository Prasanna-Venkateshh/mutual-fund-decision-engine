"""
Scheme Master and Entity Resolution Manager (data/mapping/).

Mandated by ARCHITECTURE.md Section 4 as an explicit boundary responsible for canonical mutual-fund identity.
Ensures that a single mutual fund scheme variant cannot accidentally splinter into multiple entities.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, List

from models.scheme import CanonicalScheme, SchemeMapping, PlanType, OptionType, MappingConfidence


class SchemeMaster:
    """Canonical Entity Resolution and Scheme Master Lookup Service."""

    def __init__(self):
        # In-memory storage for canonical schemes and mappings (backed by DB in repository layer)
        self._canonical_schemes: Dict[str, CanonicalScheme] = {}
        self._mappings: Dict[str, SchemeMapping] = {}  # key: f"{source_id}:{source_scheme_code}"

    def parse_plan_and_option(self, scheme_name: str) -> Tuple[PlanType, OptionType]:
        """
        Analyze scheme name text to extract Plan (Direct vs Regular) and Option (Growth vs IDCW).
        Does not guess if information is contradictory or missing.
        """
        name_upper = scheme_name.upper()

        # Plan parsing
        plan = PlanType.UNKNOWN
        if "DIRECT" in name_upper or "DIR" in name_upper:
            plan = PlanType.DIRECT
        elif "REGULAR" in name_upper or "REG" in name_upper or "RETAIL" in name_upper:
            plan = PlanType.REGULAR

        # Option parsing
        option = OptionType.UNKNOWN
        if "GROWTH" in name_upper or "BONUS" in name_upper:
            if "BONUS" in name_upper:
                option = OptionType.BONUS
            else:
                option = OptionType.GROWTH
        elif "IDCW" in name_upper or "DIVIDEND" in name_upper or "DIV" in name_upper:
            option = OptionType.IDCW

        return plan, option

    def extract_amc_name(self, scheme_name: str) -> str:
        """Extract asset management company (AMC) name prefix from scheme name."""
        common_amcs = [
            "Aditya Birla Sun Life", "Axis", "Bandhan", "Canara Robeco", "DSP",
            "Edelweiss", "Franklin Templeton", "HDFC", "ICICI Prudential", "IDFC",
            "Invesco", "Kotak", "L&T", "Mirae Asset", "Motilal Oswal", "Nippon India",
            "PGIM India", "PPFAS", "Parag Parikh", "SBI", "Sundaram", "Tata", "UTI"
        ]
        for amc in common_amcs:
            if scheme_name.upper().startswith(amc.upper()):
                return amc
        # Fallback: take first two words
        words = scheme_name.split()
        return " ".join(words[:2]) if len(words) >= 2 else scheme_name

    def resolve_or_create_canonical_scheme(
        self,
        source_id: str,
        source_scheme_code: str,
        source_scheme_name: str,
        isin_growth: Optional[str] = None
    ) -> Tuple[CanonicalScheme, SchemeMapping]:
        """
        Resolve raw scheme identifiers to a CanonicalScheme entity and create/retrieve SchemeMapping.
        
        Mapping Confidence Logic:
        - EXACT_MATCH: Source scheme code matches known primary AMFI code AND plan/option parsed clearly.
        - HIGH_CONFIDENCE: Plan and Option parsed cleanly with unambiguous AMC and scheme name.
        - AMBIGUOUS: Missing plan or option classification in scheme name.
        - UNMAPPED: Scheme code or name completely unresolvable.
        """
        mapping_key = f"{source_id}:{source_scheme_code}"
        if mapping_key in self._mappings:
            existing_mapping = self._mappings[mapping_key]
            canonical = self._canonical_schemes.get(existing_mapping.canonical_scheme_id)
            if canonical:
                return canonical, existing_mapping

        plan, option = self.parse_plan_and_option(source_scheme_name)
        amc_name = self.extract_amc_name(source_scheme_name)

        # Determine Mapping Confidence
        confidence = MappingConfidence.HIGH_CONFIDENCE
        notes = "Resolved using scheme code and text analysis."

        if plan == PlanType.UNKNOWN or option == OptionType.UNKNOWN:
            confidence = MappingConfidence.AMBIGUOUS
            notes = "Ambiguous scheme name: plan or option type could not be determined unambiguously."

        if not source_scheme_code or not source_scheme_name:
            confidence = MappingConfidence.UNMAPPED
            notes = "Missing essential scheme code or scheme name."

        # Create Canonical Scheme ID
        if source_id == "AMFI_OFFICIAL" and source_scheme_code.isdigit():
            confidence = MappingConfidence.EXACT_MATCH if confidence != MappingConfidence.AMBIGUOUS else MappingConfidence.AMBIGUOUS
            canonical_id = f"CAN_AMFI_{source_scheme_code}"
        else:
            canonical_id = f"CAN_{uuid.uuid5(uuid.NAMESPACE_DNS, source_scheme_name.upper()).hex[:12]}"

        clean_name = re.sub(r"\s+", " ", source_scheme_name).strip()
        now = datetime.now(timezone.utc)

        canonical_scheme = CanonicalScheme(
            canonical_scheme_id=canonical_id,
            amc_name=amc_name,
            scheme_name=source_scheme_name,
            clean_scheme_name=clean_name,
            plan_type=plan,
            option_type=option,
            category="UNASSIGNED",  # Will be enriched by SEBI categorization engine in later slice
            sub_category="UNASSIGNED",
            primary_amfi_code=source_scheme_code if source_scheme_code.isdigit() else None,
            isin_growth=isin_growth,
            created_at=now
        )
        self._canonical_schemes[canonical_id] = canonical_scheme

        mapping = SchemeMapping(
            mapping_id=f"map_{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            source_scheme_code=source_scheme_code,
            source_scheme_name=source_scheme_name,
            canonical_scheme_id=canonical_id if confidence in (MappingConfidence.EXACT_MATCH, MappingConfidence.HIGH_CONFIDENCE) else None,
            confidence=confidence,
            notes=notes,
            mapped_at=now
        )
        self._mappings[mapping_key] = mapping

        return canonical_scheme, mapping
