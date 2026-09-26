"""
Unit tests for Risk, Downside Deviation, and Drawdown calculations (metrics/risk.py).

Tests financial risk algorithms against known mathematical expectations as specified in QA_SPEC.md.
"""

import unittest
from datetime import date, timedelta
import math

from metrics.risk import (
    calculate_annualized_volatility,
    calculate_downside_deviation,
    calculate_max_drawdown
)


class TestRiskMetrics(unittest.TestCase):

    def test_annualized_volatility_zero_for_flat_nav(self):
        """Flat constant NAV series must have 0.0 annualized volatility."""
        start = date(2024, 1, 1)
        records = [
            {"nav_date": (start + timedelta(days=i)).isoformat(), "nav_value": 100.0}
            for i in range(100)
        ]
        vol = calculate_annualized_volatility(records)
        self.assertEqual(vol, 0.0)

    def test_annualized_volatility_known_alternating_returns(self):
        """Alternating +1% and -1% daily returns annualized over 252 trading days."""
        start = date(2024, 1, 1)
        nav = 100.0
        records = [{"nav_date": start.isoformat(), "nav_value": nav}]
        for i in range(1, 200):
            multiplier = 1.01 if i % 2 == 1 else 0.99
            nav *= multiplier
            d = start + timedelta(days=i)
            records.append({"nav_date": d.isoformat(), "nav_value": nav})

        vol = calculate_annualized_volatility(records)
        # Daily return is ~ +/- 0.01. Std dev ~ 0.01. Annualized = 0.01 * sqrt(252) ~ 0.1587
        self.assertAlmostEqual(vol, 0.01 * math.sqrt(252), delta=0.02)

    def test_downside_deviation_zero_for_positive_growth(self):
        """Monotonically growing NAV with MAR=0.0 must yield 0.0 downside deviation."""
        start = date(2024, 1, 1)
        records = [
            {"nav_date": (start + timedelta(days=i)).isoformat(), "nav_value": 100.0 + i * 0.5}
            for i in range(50)
        ]
        down_dev = calculate_downside_deviation(records, mar_daily=0.0)
        self.assertEqual(down_dev, 0.0)

    def test_downside_deviation_with_negative_days(self):
        """Series with negative daily returns must calculate non-zero downside deviation."""
        records = [
            {"nav_date": "2024-01-01", "nav_value": 100.0},
            {"nav_date": "2024-01-02", "nav_value": 95.0},   # -5% return
            {"nav_date": "2024-01-03", "nav_value": 90.0},   # -5.26% return
            {"nav_date": "2024-01-04", "nav_value": 95.0},   # +5.55% return
        ]
        down_dev = calculate_downside_deviation(records, mar_daily=0.0)
        self.assertGreater(down_dev, 0.0)

    def test_max_drawdown_peak_to_trough(self):
        """NAV drop from 100 to 75 represents a -25% max drawdown."""
        records = [
            {"nav_date": "2024-01-01", "nav_value": 50.0},
            {"nav_date": "2024-01-02", "nav_value": 100.0},  # Peak
            {"nav_date": "2024-01-03", "nav_value": 90.0},
            {"nav_date": "2024-01-04", "nav_value": 75.0},   # Trough (-25%)
            {"nav_date": "2024-01-05", "nav_value": 85.0},
            {"nav_date": "2024-01-06", "nav_value": 110.0},  # New Peak
        ]
        max_dd, peak_d, trough_d = calculate_max_drawdown(records)
        self.assertAlmostEqual(max_dd, -0.25, places=6)
        self.assertEqual(peak_d, date(2024, 1, 2))
        self.assertEqual(trough_d, date(2024, 1, 4))

    def test_max_drawdown_strictly_increasing(self):
        """Strictly increasing NAV series has 0.0 max drawdown."""
        records = [
            {"nav_date": "2024-01-01", "nav_value": 10.0},
            {"nav_date": "2024-01-02", "nav_value": 12.0},
            {"nav_date": "2024-01-03", "nav_value": 15.0},
        ]
        max_dd, peak_d, trough_d = calculate_max_drawdown(records)
        self.assertEqual(max_dd, 0.0)

    def test_custom_trading_days_parameter(self):
        """Verify custom trading_days_per_year parameter alters annualized volatility scale."""
        start = date(2024, 1, 1)
        nav = 100.0
        records = [{"nav_date": start.isoformat(), "nav_value": nav}]
        for i in range(1, 100):
            multiplier = 1.01 if i % 2 == 1 else 0.99
            nav *= multiplier
            records.append({"nav_date": (start + timedelta(days=i)).isoformat(), "nav_value": nav})

        vol_252 = calculate_annualized_volatility(records, trading_days_per_year=252)
        vol_260 = calculate_annualized_volatility(records, trading_days_per_year=260)
        self.assertGreater(vol_260, vol_252)

    def test_custom_mar_daily_parameter(self):
        """Verify custom mar_daily parameter alters downside deviation threshold."""
        records = [
            {"nav_date": "2024-01-01", "nav_value": 100.0},
            {"nav_date": "2024-01-02", "nav_value": 101.0},  # +1%
            {"nav_date": "2024-01-03", "nav_value": 102.0},  # +0.99%
        ]
        # With MAR = 0.0, no return is below 0.0 -> downside dev = 0.0
        dd_zero = calculate_downside_deviation(records, mar_daily=0.0)
        self.assertEqual(dd_zero, 0.0)

        # With MAR = 0.02 (2% daily target), both returns are below 2% -> downside dev > 0.0
        dd_target = calculate_downside_deviation(records, mar_daily=0.02)
        self.assertGreater(dd_target, 0.0)


if __name__ == "__main__":
    unittest.main()
