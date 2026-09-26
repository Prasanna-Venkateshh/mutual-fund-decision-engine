"""
Scheme Identity Adapter (Phase D.6).

Adapts upstream scheme master and lifecycle resolution records into dataset
identity attributes (canonical_scheme_id, AMFI code, ISIN, plan, option).

Enforces:
- Canonical UUID identification.
- PlanType (Direct vs Regular) and OptionType (Growth vs IDCW) parsing.
- Ambiguous or unmapped identity quarantine.
- Preservation of AMFI codes and ISINs without merging separate economic entities.
"""

from typing import Dict, Any, Tuple, Optional
from models.fund_quality_dataset import PlanType, OptionType
from data.mapping.scheme_master import SchemeMaster
from models.scheme import PlanType as OldPlanType, OptionType as OldOptionType


class SchemeIdentityAdapter:
    """Adapter for canonical scheme identity resolution and plan/option classification."""

    def __init__(self, scheme_master: Optional[SchemeMaster] = None):
        self.scheme_master = scheme_master or SchemeMaster()

    def resolve_identity(
        self,
        amfi_code: str,
        scheme_name: str,
        isin_growth: Optional[str] = None,
        source_id: str = "AMFI_OFFICIAL",
        override_canonical_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolves identity metadata for a scheme.
        Returns a dictionary with canonical_scheme_id, amfi_code, isin, scheme_name,
        amc_name, plan_type, option_type, and quarantine flags.
        """
        canonical, mapping = self.scheme_master.resolve_or_create_canonical_scheme(
            source_id=source_id,
            source_scheme_code=amfi_code,
            source_scheme_name=scheme_name,
            isin_growth=isin_growth
        )

        canonical_id = override_canonical_id or canonical.canonical_scheme_id
        plan_raw, option_raw = self.scheme_master.parse_plan_and_option(scheme_name)
        amc_name = self.scheme_master.extract_amc_name(scheme_name)

        # Map to D.6 PlanType
        if plan_raw == OldPlanType.DIRECT:
            plan = PlanType.DIRECT
        elif plan_raw == OldPlanType.REGULAR:
            plan = PlanType.REGULAR
        else:
            plan = PlanType.UNKNOWN

        # Map to D.6 OptionType
        if option_raw == OldOptionType.GROWTH:
            option = OptionType.GROWTH
        elif option_raw in (OldOptionType.IDCW, OldOptionType.BONUS):
            option = OptionType.IDCW_REINVESTMENT
        else:
            option = OptionType.UNKNOWN

        # Quarantine check for ambiguous identity
        is_quarantined = False
        quarantine_reasons = []

        if plan == PlanType.UNKNOWN or option == OptionType.UNKNOWN:
            is_quarantined = True
            quarantine_reasons.append(
                f"Ambiguous identity classification: plan={plan.value}, option={option.value}"
            )

        if not amfi_code or amfi_code == "0":
            is_quarantined = True
            quarantine_reasons.append("Invalid or missing AMFI scheme code.")

        return {
            "canonical_scheme_id": canonical_id,
            "amfi_code": str(amfi_code),
            "isin": isin_growth or canonical.isin_growth,
            "scheme_name": scheme_name,
            "amc_name": amc_name,
            "plan_type": plan,
            "option_type": option,
            "is_quarantined": is_quarantined,
            "quarantine_reasons": quarantine_reasons
        }
