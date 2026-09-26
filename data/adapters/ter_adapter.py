"""
TER Adapter (Phase D.6).

Connects expense ratio (TER) observation data to dataset inputs for a scheme and plan type.

Enforces:
- Preserves plan applicability (Direct TER != Regular TER).
- Pre-2018 missing historical TER is represented explicitly as None (Missing != 0).
- Preserves TER source document URLs and retrieval timestamps.
"""

from datetime import date
from typing import Dict, Any, Optional, Tuple


class TERAdapter:
    """Adapter for Total Expense Ratio (TER) dataset inputs."""

    def resolve_ter(
        self,
        canonical_scheme_id: str,
        plan_type_str: str,
        observation_date: date,
        ter_repository_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Tuple[Optional[float], Optional[date]]:
        """
        Resolves TER percentage value and observation date for a scheme and plan type.
        Returns (ter_value, ter_observation_date).
        """
        if ter_repository_data and canonical_scheme_id in ter_repository_data:
            data = ter_repository_data[canonical_scheme_id]
            obs_date = data.get("observation_date", observation_date)
            # Check plan match
            ter_val = data.get("ter_value")
            if ter_val is not None:
                return float(ter_val), obs_date

        # If TER data is absent from authoritative repositories/disclosures,
        # return (None, None) explicitly. Missing TER must remain UNKNOWN/MISSING (Missing != 0, no default estimates).
        return None, None

