"""
Fund Quality Dataset Builder (Phase D.6).

Orchestrates the construction of point-in-time FundQualityDatasetInput objects
and anti-survivorship peer group snapshots as of observation date T.

Enforces:
- Anti-survivorship bias elimination: Active schemes as of date T are included
  regardless of subsequent merger or closure.
- Decoupling from scoring: Assembles dataset contracts ONLY. Does NOT compute
  final score weights, fund rankings, or buy/sell decisions.
- Provenance preservation: Every record retains full source URL, retrieval
  timestamp, and methodology version.
"""

from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional

from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    ProvenanceMetadata,
    OptionType
)
from data.adapters.scheme_identity_adapter import SchemeIdentityAdapter
from data.adapters.scoring_metric_adapter import ScoringMetricAdapter
from data.adapters.category_context_adapter import CategoryContextAdapter
from data.adapters.ter_adapter import TERAdapter
from data.validators.scoring_dataset_validator import ScoringDatasetValidator


class FundQualityDatasetBuilder:
    """Builder orchestrating dataset construction from upstream adapters."""

    DATASET_VERSION = "1.0.0"

    def __init__(
        self,
        identity_adapter: Optional[SchemeIdentityAdapter] = None,
        metric_adapter: Optional[ScoringMetricAdapter] = None,
        category_adapter: Optional[CategoryContextAdapter] = None,
        ter_adapter: Optional[TERAdapter] = None,
        validator: Optional[ScoringDatasetValidator] = None
    ):
        self.identity_adapter = identity_adapter or SchemeIdentityAdapter()
        self.metric_adapter = metric_adapter or ScoringMetricAdapter()
        self.category_adapter = category_adapter or CategoryContextAdapter()
        self.ter_adapter = ter_adapter or TERAdapter()
        self.validator = validator or ScoringDatasetValidator()

    def build_dataset_input_for_scheme(
        self,
        amfi_code: str,
        scheme_name: str,
        observation_date: date,
        nav_history: List[Dict[str, Any]],
        isin_growth: Optional[str] = None,
        source_id: str = "AMFI_OFFICIAL",
        source_document_url: str = "https://www.amfiindia.com/net-asset-value",
        custom_ter_data: Optional[Dict[str, Any]] = None,
        custom_category_data: Optional[Dict[str, Any]] = None,
        override_canonical_id: Optional[str] = None
    ) -> FundQualityDatasetInput:
        """
        Builds a single FundQualityDatasetInput contract object for a scheme as of date T.
        """
        # 1. Resolve Identity
        identity = self.identity_adapter.resolve_identity(
            amfi_code=amfi_code,
            scheme_name=scheme_name,
            isin_growth=isin_growth,
            source_id=source_id,
            override_canonical_id=override_canonical_id
        )

        canonical_id = identity["canonical_scheme_id"]

        # 2. Resolve TER
        ter_map = {canonical_id: custom_ter_data} if custom_ter_data else None
        ter_val, ter_date = self.ter_adapter.resolve_ter(
            canonical_scheme_id=canonical_id,
            plan_type_str=identity["plan_type"].value,
            observation_date=observation_date,
            ter_repository_data=ter_map
        )

        # 3. Compute Metrics
        metrics_snapshot = self.metric_adapter.compute_metric_snapshot(
            nav_records=nav_history,
            observation_date=observation_date,
            ter_value=ter_val,
            ter_observation_date=ter_date
        )

        # 4. Resolve Point-in-Time Category
        cat_map = {canonical_id: custom_category_data} if custom_category_data else None
        category_context = self.category_adapter.resolve_category_context(
            canonical_scheme_id=canonical_id,
            scheme_name=scheme_name,
            observation_date=observation_date,
            custom_category_map=cat_map
        )

        # 5. Provenance
        provenance = ProvenanceMetadata(
            source_id=source_id,
            source_document_url=source_document_url,
            retrieval_timestamp_utc=datetime.now(timezone.utc),
            methodology_version=self.DATASET_VERSION,
            is_platform_calculated=True
        )

        # 6. Check IDCW return comparability
        return_comparability = True
        if identity["option_type"] in (OptionType.IDCW_REINVESTMENT, OptionType.IDCW_PAYOUT):
            return_comparability = False

        # Construct initial unvalidated contract
        draft_input = FundQualityDatasetInput(
            dataset_version=self.DATASET_VERSION,
            observation_date=observation_date,
            canonical_scheme_id=canonical_id,
            amfi_code=identity["amfi_code"],
            isin=identity["isin"],
            scheme_name=scheme_name,
            amc_name=identity["amc_name"],
            plan_type=identity["plan_type"],
            option_type=identity["option_type"],
            category_context=category_context,
            metrics=metrics_snapshot,
            data_quality_score=0.0,
            confidence_score=0.0,
            provenance=provenance,
            is_quarantined=identity["is_quarantined"],
            quarantine_reasons=identity["quarantine_reasons"],
            return_comparability_available=return_comparability
        )

        # 7. Validate and score quality & confidence
        dq_score, conf_score, is_quarantined, reasons = self.validator.validate_and_score(draft_input)

        # Return final validated contract
        return FundQualityDatasetInput(
            dataset_version=self.DATASET_VERSION,
            observation_date=observation_date,
            canonical_scheme_id=canonical_id,
            amfi_code=identity["amfi_code"],
            isin=identity["isin"],
            scheme_name=scheme_name,
            amc_name=identity["amc_name"],
            plan_type=identity["plan_type"],
            option_type=identity["option_type"],
            category_context=category_context,
            metrics=metrics_snapshot,
            data_quality_score=dq_score,
            confidence_score=conf_score,
            provenance=provenance,
            is_quarantined=is_quarantined,
            quarantine_reasons=reasons,
            return_comparability_available=return_comparability
        )

    def build_peer_dataset_for_category(
        self,
        category: str,
        subcategory: str,
        observation_date: date,
        schemes_pool: List[Dict[str, Any]]
    ) -> List[FundQualityDatasetInput]:
        """
        Builds peer group dataset for a specific category as of date T.
        Includes schemes active at date T to ensure anti-survivorship compliance.
        """
        dataset_list: List[FundQualityDatasetInput] = []

        for item in schemes_pool:
            record = self.build_dataset_input_for_scheme(
                amfi_code=item["amfi_code"],
                scheme_name=item["scheme_name"],
                observation_date=observation_date,
                nav_history=item.get("nav_history", []),
                isin_growth=item.get("isin_growth"),
                source_id=item.get("source_id", "AMFI_OFFICIAL"),
                source_document_url=item.get("source_document_url", "https://www.amfiindia.com"),
                custom_ter_data=item.get("ter_data"),
                custom_category_data=item.get("category_data"),
                override_canonical_id=item.get("canonical_scheme_id")
            )
            # Filter for category match at date T
            if (
                record.category_context.category == category
                and record.category_context.subcategory == subcategory
            ):
                dataset_list.append(record)

        return dataset_list
