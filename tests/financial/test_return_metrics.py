"""
Unit tests for Point-to-Point, CAGR, and Rolling Returns calculations (metrics/returns.py).

Tests financial accuracy, boundary handling, and edge cases as specified in QA_SPEC.md.
"""

import unittest
from datetime import date, timedelta
import math

from metrics.returns import (
    calculate_absolute_return,
    calculate_cagr,
    calculate_rolling_returns
)


class TestReturnMetrics(unittest.TestCase):

    def test_absolute_return_positive(self):
        """Absolute return calculation for positive NAV gain."""
        ret = calculate_absolute_return(100.0, 150.0)
        self.assertAlmostEqual(ret, 0.50, places=6)

    def test_absolute_return_loss(self):
        """Absolute return calculation for NAV loss."""
        ret = calculate_absolute_return(100.0, 80.0)
        self.assertAlmostEqual(ret, -0.20, places=6)

    def test_absolute_return_invalid_nav(self):
        """Zero or negative NAV must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_absolute_return(0.0, 100.0)
        with self.assertRaises(ValueError):
            calculate_absolute_return(100.0, -10.0)

    def test_cagr_two_years(self):
        """CAGR for exactly 2 years doubling (100 -> 121 means 10% CAGR over 2 yrs)."""
        start = date(2022, 1, 1)
        end = date(2024, 1, 1)  # 730 days ~ 2 years
        cagr = calculate_cagr(100.0, 121.0, start, end)
        # (121/100)^(365.25 / 730) - 1 = 1.21^(0.50034) - 1 ~ 0.1000
        self.assertAlmostEqual(cagr, 0.10, delta=0.005)

    def test_cagr_under_one_year_fallback(self):
        """Periods under 1 year return simple absolute return without annualization distortion."""
        start = date(2024, 1, 1)
        end = date(2024, 6, 1)  # ~152 days
        res = calculate_cagr(100.0, 110.0, start, end)
        self.assertEqual(res, 0.10)  # Simple 10% return

    def test_cagr_invalid_dates(self):
        """End date before or equal to start date must raise ValueError."""
        d = date(2024, 1, 1)
        with self.assertRaises(ValueError):
            calculate_cagr(100.0, 110.0, d, d)

    def test_rolling_returns_1year(self):
        """1-Year rolling returns calculation over 3 years of daily NAVs."""
        start_date = date(2021, 1, 1)
        # Create 3 years of daily NAV data with 10% annual steady growth
        nav_records = []
        for i in range(1095):
            current_date = start_date + timedelta(days=i)
            # steady growth formula: 100 * (1.10 ^ (i / 365.25))
            nav_val = 100.0 * math.pow(1.10, i / 365.25)
            nav_records.append({"nav_date": current_date.isoformat(), "nav_value": nav_val})

        res = calculate_rolling_returns(nav_records, window_years=1)
        self.assertEqual(res["status"], "VALID")
        self.assertGreater(res["total_rolling_windows"], 100)
        self.assertAlmostEqual(res["mean_return"], 0.10, delta=0.01)
        self.assertAlmostEqual(res["positive_return_ratio"], 1.0, places=6)

    def test_rolling_returns_insufficient_history(self):
        """Rolling returns over 3 years window with only 1 year history returns INSUFFICIENT_HISTORY."""
        start_date = date(2024, 1, 1)
        nav_records = [
            {"nav_date": (start_date + timedelta(days=i)).isoformat(), "nav_value": 100.0 + i * 0.1}
            for i in range(100)
        ]
        res = calculate_rolling_returns(nav_records, window_years=3)
        self.assertEqual(res["status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(res["total_rolling_windows"], 0)

    def test_rolling_returns_custom_tolerance(self):
        """Verify custom tolerance_days parameter can be supplied to calculate_rolling_returns."""
        start_date = date(2021, 1, 1)
        nav_records = [
            {"nav_date": (start_date + timedelta(days=i)).isoformat(), "nav_value": 100.0 * (1.10 ** (i / 365.25))}
            for i in range(1095)
        ]
        res = calculate_rolling_returns(nav_records, window_years=1, tolerance_days=15)
        self.assertEqual(res["status"], "VALID")
        self.assertGreater(res["total_rolling_windows"], 100)


if __name__ == "__main__":
    unittest.main()
