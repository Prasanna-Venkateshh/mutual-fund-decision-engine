"""
Fund Quality Dataset Repository (Phase D.6).

Manages storage and query retrieval of FundQualityDatasetInput contracts.

Enforces:
- Schema persistence for dataset records.
- Unique constraints on (canonical_scheme_id, observation_date, dataset_version).
- Retrieval of point-in-time peer group datasets.
"""

import json
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional
import sqlite3

from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    PlanType,
    OptionType,
    FundMaturityTier,
    CategoryPointInTimeContext,
    SchemeMetricSnapshot,
    ProvenanceMetadata
)


CREATE_DATASET_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fund_quality_dataset_records (
    record_id TEXT PRIMARY KEY,
    dataset_version TEXT NOT NULL,
    observation_date TEXT NOT NULL,
    canonical_scheme_id TEXT NOT NULL,
    amfi_code TEXT NOT NULL,
    scheme_name TEXT NOT NULL,
    amc_name TEXT NOT NULL,
    plan_type TEXT NOT NULL,
    option_type TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    data_quality_score REAL NOT NULL,
    confidence_score REAL NOT NULL,
    is_quarantined INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    UNIQUE(canonical_scheme_id, observation_date, dataset_version)
);
"""


class FundQualityDatasetRepository:
    """Repository for Fund Quality Dataset storage and query access."""

    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn
        self._init_table()

    def _init_table(self) -> None:
        self.conn.execute(CREATE_DATASET_TABLE_SQL)
        self.conn.commit()

    def save_dataset_record(self, dataset_input: FundQualityDatasetInput) -> str:
        """
        Persists a FundQualityDatasetInput contract record.
        """
        record_id = (
            f"fq_{dataset_input.canonical_scheme_id}_"
            f"{dataset_input.observation_date.strftime('%Y%m%d')}_"
            f"{dataset_input.dataset_version}"
        )
        max_dd = dataset_input.metrics.max_drawdown
        max_dd_data = None
        if max_dd is not None:
            if isinstance(max_dd, (list, tuple)):
                max_dd_data = [
                    float(max_dd[0]),
                    max_dd[1].isoformat() if hasattr(max_dd[1], "isoformat") else str(max_dd[1]),
                    max_dd[2].isoformat() if hasattr(max_dd[2], "isoformat") else str(max_dd[2])
                ]
            else:
                max_dd_data = float(max_dd)

        payload = {
            "dataset_version": dataset_input.dataset_version,
            "observation_date": dataset_input.observation_date.isoformat(),
            "canonical_scheme_id": dataset_input.canonical_scheme_id,
            "amfi_code": dataset_input.amfi_code,
            "isin": dataset_input.isin,
            "scheme_name": dataset_input.scheme_name,
            "amc_name": dataset_input.amc_name,
            "plan_type": dataset_input.plan_type.value,
            "option_type": dataset_input.option_type.value,
            "category_context": {
                "category": dataset_input.category_context.category,
                "subcategory": dataset_input.category_context.subcategory,
                "effective_date": dataset_input.category_context.effective_date.isoformat(),
                "source": dataset_input.category_context.source,
                "source_precision": dataset_input.category_context.source_precision,
                "confidence_score": dataset_input.category_context.confidence_score
            },
            "metrics": {
                "observation_date": dataset_input.metrics.observation_date.isoformat(),
                "history_length_years": dataset_input.metrics.history_length_years,
                "maturity_tier": dataset_input.metrics.maturity_tier.value,
                "cagr_overall": dataset_input.metrics.cagr_overall,
                "cagr_3y": dataset_input.metrics.cagr_3y,
                "cagr_5y": dataset_input.metrics.cagr_5y,
                "rolling_1y_mean": dataset_input.metrics.rolling_1y_mean,
                "rolling_3y_mean": dataset_input.metrics.rolling_3y_mean,
                "annualized_volatility": dataset_input.metrics.annualized_volatility,
                "downside_deviation": dataset_input.metrics.downside_deviation,
                "max_drawdown": max_dd_data,
                "total_expense_ratio": dataset_input.metrics.total_expense_ratio
            },
            "data_quality_score": dataset_input.data_quality_score,
            "confidence_score": dataset_input.confidence_score,
            "provenance": {
                "source_id": dataset_input.provenance.source_id,
                "source_document_url": dataset_input.provenance.source_document_url,
                "retrieval_timestamp_utc": dataset_input.provenance.retrieval_timestamp_utc.isoformat(),
                "methodology_version": dataset_input.provenance.methodology_version,
                "is_platform_calculated": dataset_input.provenance.is_platform_calculated
            },
            "is_quarantined": dataset_input.is_quarantined,
            "quarantine_reasons": dataset_input.quarantine_reasons,
            "return_comparability_available": dataset_input.return_comparability_available
        }

        now_utc = datetime.now(timezone.utc).isoformat()

        sql = """
        INSERT OR REPLACE INTO fund_quality_dataset_records (
            record_id, dataset_version, observation_date, canonical_scheme_id,
            amfi_code, scheme_name, amc_name, plan_type, option_type,
            category, subcategory, data_quality_score, confidence_score,
            is_quarantined, payload_json, created_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        self.conn.execute(
            sql,
            (
                record_id,
                dataset_input.dataset_version,
                dataset_input.observation_date.isoformat(),
                dataset_input.canonical_scheme_id,
                dataset_input.amfi_code,
                dataset_input.scheme_name,
                dataset_input.amc_name,
                dataset_input.plan_type.value,
                dataset_input.option_type.value,
                dataset_input.category_context.category,
                dataset_input.category_context.subcategory,
                dataset_input.data_quality_score,
                dataset_input.confidence_score,
                1 if dataset_input.is_quarantined else 0,
                json.dumps(payload),
                now_utc
            )
        )
        self.conn.commit()
        return record_id

    def get_dataset_record(
        self,
        canonical_scheme_id: str,
        observation_date: date,
        dataset_version: str = "1.0.0"
    ) -> Optional[FundQualityDatasetInput]:
        """
        Retrieves a stored dataset input record.
        """
        sql = """
        SELECT payload_json FROM fund_quality_dataset_records
        WHERE canonical_scheme_id = ? AND observation_date = ? AND dataset_version = ?;
        """
        cursor = self.conn.execute(sql, (canonical_scheme_id, observation_date.isoformat(), dataset_version))
        row = cursor.fetchone()
        if not row:
            return None

        payload = json.loads(row[0])
        return self._deserialize_payload(payload)

    def _deserialize_payload(self, p: Dict[str, Any]) -> FundQualityDatasetInput:
        cat_p = p["category_context"]
        cat_ctx = CategoryPointInTimeContext(
            category=cat_p["category"],
            subcategory=cat_p["subcategory"],
            effective_date=date.fromisoformat(cat_p["effective_date"]),
            source=cat_p.get("source", "SEBI_2017_CIRCULAR"),
            source_precision=cat_p.get("source_precision", "DAY"),
            confidence_score=float(cat_p.get("confidence_score", 1.0))
        )

        m_p = p["metrics"]
        raw_dd = m_p.get("max_drawdown")
        deserialized_dd = None
        if raw_dd is not None:
            if isinstance(raw_dd, list) and len(raw_dd) == 3:
                deserialized_dd = (
                    float(raw_dd[0]),
                    date.fromisoformat(raw_dd[1]) if isinstance(raw_dd[1], str) else raw_dd[1],
                    date.fromisoformat(raw_dd[2]) if isinstance(raw_dd[2], str) else raw_dd[2]
                )
            else:
                deserialized_dd = float(raw_dd)

        m_snapshot = SchemeMetricSnapshot(
            observation_date=date.fromisoformat(m_p["observation_date"]),
            history_length_years=float(m_p["history_length_years"]),
            maturity_tier=FundMaturityTier(m_p["maturity_tier"]),
            cagr_overall=m_p.get("cagr_overall"),
            cagr_3y=m_p.get("cagr_3y"),
            cagr_5y=m_p.get("cagr_5y"),
            rolling_1y_mean=m_p.get("rolling_1y_mean"),
            rolling_3y_mean=m_p.get("rolling_3y_mean"),
            annualized_volatility=m_p.get("annualized_volatility"),
            downside_deviation=m_p.get("downside_deviation"),
            max_drawdown=deserialized_dd,
            total_expense_ratio=m_p.get("total_expense_ratio")
        )

        prov_p = p["provenance"]
        prov = ProvenanceMetadata(
            source_id=prov_p["source_id"],
            source_document_url=prov_p["source_document_url"],
            retrieval_timestamp_utc=datetime.fromisoformat(prov_p["retrieval_timestamp_utc"]),
            methodology_version=prov_p.get("methodology_version", "1.0.0"),
            is_platform_calculated=prov_p.get("is_platform_calculated", True)
        )

        return FundQualityDatasetInput(
            dataset_version=p["dataset_version"],
            observation_date=date.fromisoformat(p["observation_date"]),
            canonical_scheme_id=p["canonical_scheme_id"],
            amfi_code=p["amfi_code"],
            isin=p.get("isin"),
            scheme_name=p["scheme_name"],
            amc_name=p["amc_name"],
            plan_type=PlanType(p["plan_type"]),
            option_type=OptionType(p["option_type"]),
            category_context=cat_ctx,
            metrics=m_snapshot,
            data_quality_score=float(p["data_quality_score"]),
            confidence_score=float(p["confidence_score"]),
            provenance=prov,
            is_quarantined=bool(p["is_quarantined"]),
            quarantine_reasons=p.get("quarantine_reasons", []),
            return_comparability_available=p.get("return_comparability_available", True)
        )
