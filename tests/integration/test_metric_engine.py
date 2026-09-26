"""
Integration test for Fund Metric Engine (metrics/engine.py).

Tests end-to-end pipeline execution:
Normalized NAV database storage -> FundMetricEngine calculation -> MetricRepository SQLite persistence -> Provenance verification.
"""

import unittest
from datetime import date, timedelta, datetime, timezone
import math

from db.database import DatabaseConnection
from data.repositories.nav_repository import NAVRepository
from data.repositories.metric_repository import MetricRepository
from metrics.engine import FundMetricEngine
from models.nav_data import NormalizedNAVRecord, RawNAVRecord, DataQualityState
from models.scheme import CanonicalScheme, PlanType, OptionType


class TestMetricEngineIntegration(unittest.TestCase):

    def setUp(self):
        """Set up in-memory SQLite database and test repositories."""
        self.db = DatabaseConnection(":memory:")
        self.nav_repo = NAVRepository(self.db)
        self.metric_repo = MetricRepository(self.db)
        self.engine = FundMetricEngine(self.nav_repo, self.metric_repo)
        self.scheme_id = "SCHEME_TEST_001"
        self.source_id = "AMFI_OFFICIAL_DAILY"

        # Seed Source Registry
        with self.db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO source_registry (
                    source_id, source_name, source_type, authority_level, official_url,
                    specific_data_url, supported_data_fields, update_frequency,
                    historical_availability, free_status, licensing_status, validation_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.source_id, "AMFI Official", "REGULATOR", "PRIMARY_AUTHORITATIVE",
                    "https://amfiindia.com", "https://amfiindia.com/nav", "[]", "DAILY",
                    "FULL", 1, "FREE", "VALIDATED"
                )
            )

        # Seed Canonical Scheme
        canonical = CanonicalScheme(
            canonical_scheme_id=self.scheme_id,
            amc_name="Test AMC",
            scheme_name="Test Fund - Direct - Growth",
            clean_scheme_name="test fund direct growth",
            plan_type=PlanType.DIRECT,
            option_type=OptionType.GROWTH,
            category="Equity",
            sub_category="Large Cap",
            primary_amfi_code="123456",
            isin_growth="INF123456789",
            isin_reinvest=None,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        self.nav_repo.save_canonical_scheme(canonical)

    def _seed_nav_history(self, num_days: int, start_nav: float = 100.0, annual_growth: float = 0.12):
        """Helper to seed daily normalized NAV records in SQLite database."""
        start_date = date(2021, 1, 1)
        raw_records = []
        norm_records = []
        for i in range(num_days):
            current_date = start_date + timedelta(days=i)
            nav_val = start_nav * math.pow(1.0 + annual_growth, i / 365.25) + math.sin(i / 10.0) * 2.0
            raw_id = f"raw_{self.scheme_id}_{current_date.strftime('%Y%m%d')}"
            
            raw_rec = RawNAVRecord(
                raw_record_id=raw_id,
                source_id=self.source_id,
                retrieval_timestamp=datetime.now(timezone.utc),
                raw_scheme_code="123456",
                raw_scheme_name="Test Fund - Direct - Growth",
                raw_nav_value=str(max(1.0, nav_val)),
                raw_date=current_date.isoformat(),
                raw_line_number=i + 1
            )
            raw_records.append(raw_rec)

            rec = NormalizedNAVRecord(
                nav_id=f"nav_{self.scheme_id}_{current_date.strftime('%Y%m%d')}",
                canonical_scheme_id=self.scheme_id,
                nav_date=current_date,
                nav_value=max(1.0, nav_val),
                source_id=self.source_id,
                raw_record_id=raw_id,
                retrieval_timestamp=datetime.now(timezone.utc),
                quality_state=DataQualityState.VALID
            )
            norm_records.append(rec)

        self.nav_repo.save_raw_observations(raw_records)
        self.nav_repo.save_normalized_records(norm_records)

    def test_compute_metrics_full_history(self):
        """End-to-end test on 2-year NAV history (730 days)."""
        self._seed_nav_history(730)

        # Compute metrics
        computed_metrics = self.engine.compute_metrics_for_scheme(self.scheme_id)
        self.assertGreater(len(computed_metrics), 0)

        metric_names = [m.metric_name for m in computed_metrics]
        self.assertIn("HISTORY_LENGTH_DAYS", metric_names)
        self.assertIn("ABSOLUTE_RETURN", metric_names)
        self.assertIn("CAGR_OVERALL", metric_names)
        self.assertIn("ROLLING_RETURN_MEAN_1Y", metric_names)
        self.assertIn("ANNUALIZED_VOLATILITY", metric_names)
        self.assertIn("DOWNSIDE_DEVIATION", metric_names)
        self.assertIn("MAX_DRAWDOWN", metric_names)

        # Verify DB persistence
        db_metrics = self.metric_repo.get_metrics_for_scheme(self.scheme_id)
        self.assertEqual(len(db_metrics), len(computed_metrics))

        # Verify provenance fields on absolute return metric
        abs_ret_db = self.metric_repo.get_metric_by_name(self.scheme_id, "ABSOLUTE_RETURN")
        self.assertIsNotNone(abs_ret_db)
        self.assertEqual(abs_ret_db["canonical_scheme_id"], self.scheme_id)
        self.assertEqual(abs_ret_db["methodology_version"], "1.0.0")
        self.assertEqual(abs_ret_db["confidence_state"], "VALID")
        self.assertEqual(abs_ret_db["observation_count"], 730)

    def test_compute_metrics_incomplete_history_under_1_year(self):
        """Test pipeline on short history (< 1 year = 180 days)."""
        self._seed_nav_history(180)

        computed_metrics = self.engine.compute_metrics_for_scheme(self.scheme_id)
        self.assertGreater(len(computed_metrics), 0)

        metric_names = [m.metric_name for m in computed_metrics]
        self.assertIn("HISTORY_LENGTH_DAYS", metric_names)
        self.assertIn("ABSOLUTE_RETURN", metric_names)
        # CAGR and Rolling Returns should NOT be present for <365 days history
        self.assertNotIn("CAGR_OVERALL", metric_names)
        self.assertNotIn("ROLLING_RETURN_MEAN_1Y", metric_names)

        # All computed metrics must have confidence_state = INCOMPLETE
        for m in computed_metrics:
            self.assertEqual(m.confidence_state, DataQualityState.INCOMPLETE)


if __name__ == "__main__":
    unittest.main()
