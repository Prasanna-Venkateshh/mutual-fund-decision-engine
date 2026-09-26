"""
Step 6.1 — End-to-End Investor User Journey 4: Exploration-Only Investor
Validates exploration flows without portfolio requirement or false dirty warnings:
- Fund Discovery & Scheme Master Search
- Fund Detail hero presentation (Scheme Name as h1, Canonical ID as secondary)
- Analytical performance and 6-dimension breakdown tables
- Data quality & missing value integrity ('Not available' vs zero-filling)
- Provenance & Evidence & Methodology box
- Read-only dirty-guard exclusion across navigation
"""

import sqlite3
import pytest

from web.app import UIRequestHandler, render_html_page


class DummyHTTPHandler:
    def __init__(self, investor_id=None):
        self.investor_id = investor_id
        self.html_output = ""
        self.json_output = {}

    def send_html(self, html_str: str):
        self.html_output = html_str

    def send_json(self, data: dict):
        self.json_output = data


class TestJourneyExplorationOnly:
    """End-to-End Journey 4 Test Suite."""

    def test_journey_4_fund_discovery_and_search(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr05_discover(handler)

        assert "Explore Mutual Funds" in handler.html_output
        assert 'id="discover_search_input"' in handler.html_output
        assert 'data-no-dirty="true"' in handler.html_output

    def test_journey_4_fund_detail_presentation_hierarchy(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_118266")

        output = handler.html_output

        # 1. Scheme name MUST be the primary heading
        assert '<h1 style="font-size: 2.2rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; line-height: 1.25;">Canara Robeco Nifty Index-Direct Plan - Growth</h1>' in output
        assert '<h1>Scheme Code CAN_AMFI_118266</h1>' not in output

        # 2. Canonical Scheme ID is secondary metadata
        assert 'Canonical ID: <code>CAN_AMFI_118266</code>' in output
        assert 'AMFI Code: <code>118266</code>' in output

        # 3. Analytical tables rendered
        assert 'Performance & Risk Metrics' in output
        assert 'Fund Quality 6-Dimension Score Breakdown' in output

        # 4. Missing values display 'Not available' without zero-filling
        assert 'Not available' in output
        assert '0.00%' not in output

    def test_journey_4_dirty_guard_exclusion(self):
        content = """
        <input type="text" id="discover_search_input" data-no-dirty="true" placeholder="Search...">
        """
        html = render_html_page("Discover", content, "/discover")

        # Verify JavaScript contains GET form & data-no-dirty exclusion check
        assert 'form && (form.getAttribute(\'method\') || \'GET\').toUpperCase() !== \'POST\'' in html
        assert 'el.getAttribute(\'data-no-dirty\') === \'true\'' in html
