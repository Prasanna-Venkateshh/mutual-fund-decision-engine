"""
Unit tests for Fund History & Data Maturity evaluation (metrics/maturity.py).

Tests maturity bucket classification across history lengths as specified in PRODUCT_SPEC.md Section 7.
"""

import unittest
from datetime import date, timedelta
from metrics.maturity import calculate_fund_history_maturity
from models.metric_data import HistoryMaturityBucket
from models.nav_data import DataQualityState


class TestMaturityMetrics(unittest.TestCase):

    def test_empty_nav_records(self):
        """Empty NAV list must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_fund_history_maturity([])

    def test_less_than_1_year_maturity(self):
        """History under 365 days must map to LESS_THAN_1_YEAR and INCOMPLETE state."""
        start = date(2025, 1, 1)
        records = [
            {"nav_date": (start + timedelta(days=i)).isoformat(), "nav_value": 10.0 + i * 0.01}
            for i in range(180)
        ]
        days, bucket, quality, s_date, e_date, count = calculate_fund_history_maturity(records)
        self.assertEqual(days, 179)
        self.assertEqual(bucket, HistoryMaturityBucket.LESS_THAN_1_YEAR)
        self.assertEqual(quality, DataQualityState.INCOMPLETE)
        self.assertEqual(s_date, date(2025, 1, 1))
        self.assertEqual(e_date, start + timedelta(days=179))
        self.assertEqual(count, 180)

    def test_one_to_three_years_maturity(self):
        """History between 365 and 1094 days must map to ONE_TO_THREE_YEARS and VALID state."""
        start = date(2023, 1, 1)
        records = [
            {"nav_date": (start + timedelta(days=i)).isoformat(), "nav_value": 10.0}
            for i in range(500)
        ]
        days, bucket, quality, s_date, e_date, count = calculate_fund_history_maturity(records)
        self.assertEqual(days, 499)
        self.assertEqual(bucket, HistoryMaturityBucket.ONE_TO_THREE_YEARS)
        self.assertEqual(quality, DataQualityState.VALID)

    def test_three_to_five_years_maturity(self):
        """History between 1095 and 1824 days must map to THREE_TO_FIVE_YEARS."""
        start = date(2020, 1, 1)
        records = [
            {"nav_date": (start + timedelta(days=i)).isoformat(), "nav_value": 10.0}
            for i in range(1200)
        ]
        days, bucket, quality, s_date, e_date, count = calculate_fund_history_maturity(records)
        self.assertEqual(days, 1199)
        self.assertEqual(bucket, HistoryMaturityBucket.THREE_TO_FIVE_YEARS)
        self.assertEqual(quality, DataQualityState.VALID)

    def test_five_to_ten_years_maturity(self):
        """History between 1825 and 3651 days must map to FIVE_TO_TEN_YEARS."""
        start = date(2015, 1, 1)
        records = [
            {"nav_date": (start + timedelta(days=i)).isoformat(), "nav_value": 10.0}
            for i in range(2500)
        ]
        days, bucket, quality, s_date, e_date, count = calculate_fund_history_maturity(records)
        self.assertEqual(days, 2499)
        self.assertEqual(bucket, HistoryMaturityBucket.FIVE_TO_TEN_YEARS)
        self.assertEqual(quality, DataQualityState.VALID)

    def test_ten_plus_years_maturity(self):
        """History >= 3652 days must map to TEN_PLUS_YEARS."""
        start = date(2010, 1, 1)
        records = [
            {"nav_date": (start + timedelta(days=i)).isoformat(), "nav_value": 10.0}
            for i in range(4000)
        ]
        days, bucket, quality, s_date, e_date, count = calculate_fund_history_maturity(records)
        self.assertEqual(days, 3999)
        self.assertEqual(bucket, HistoryMaturityBucket.TEN_PLUS_YEARS)
        self.assertEqual(quality, DataQualityState.VALID)

    def test_unsorted_records_handling(self):
        """Input records out of order must be sorted correctly by date."""
        records = [
            {"nav_date": "2024-06-01", "nav_value": 15.0},
            {"nav_date": "2024-01-01", "nav_value": 10.0},
            {"nav_date": "2024-03-01", "nav_value": 12.0},
        ]
        days, bucket, quality, s_date, e_date, count = calculate_fund_history_maturity(records)
        self.assertEqual(s_date, date(2024, 1, 1))
        self.assertEqual(e_date, date(2024, 6, 1))
        self.assertEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
