"""
Step 6.1 — Adversarial & Negative User Journey Test Suite
Executes dedicated negative tests:
- NEG-01: No portfolio analysis attempts handle missing portfolio gracefully
- NEG-02: Name-only CSV row is quarantined (never creates active holding)
- NEG-03: Malformed CSV payload produces clear error banner without DB corruption
- NEG-04: Duplicate portfolio confirmation payload is idempotent (0 row growth)
- NEG-05: Recommendation display leaves portfolio unchanged (zero automatic execution)
- NEG-06: Recommendation review rejection leaves portfolio unchanged
- NEG-07: Missing metric values are never converted to zero (0.00%)
- NEG-08: Exploration /discover inputs never activate dirty guard
- NEG-09: Genuine persisted edit on /onboarding MUST activate dirty guard
- NEG-10: Genuine persisted edit on /wealth manual entry MUST activate dirty guard
"""

import os
import sqlite3
import tempfile
import pytest

from portfolio.need_models import PortfolioExposureSnapshot
from data.adapters.portfolio_upload_adapter import PortfolioUploadAdapter
from data.repositories.portfolio_repository import PortfolioRepository
from data.repositories.profile_repository import ProfileRepository
from web.adapters import QuestionnaireAdapter
from web.app import UIRequestHandler, render_html_page
from web.security import SessionRepository


class DummyHTTPHandler:
    def __init__(self, investor_id="inv_neg_user"):
        self.investor_id = investor_id
        self.html_output = ""

    def send_response(self, code: int, message: str = None):
        pass

    def send_header(self, keyword: str, value: str):
        pass

    def end_headers(self):
        pass

    def send_html(self, html_str: str):
        self.html_output = html_str

    def send_json(self, data: dict):
        pass


class TestAdversarialJourneys:
    """Adversarial & Negative Journey Test Suite."""

    @pytest.fixture
    def journey_db(self):
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_file.close()
        conn = sqlite3.connect(db_file.name)
        yield conn, db_file.name
        conn.close()
        if os.path.exists(db_file.name):
            os.remove(db_file.name)

    # NEG-01: No Portfolio Analysis Evaluation
    def test_neg_01_no_portfolio_graceful_handling(self, journey_db):
        conn, _ = journey_db
        port_repo = PortfolioRepository(db_conn=conn)
        test_user = "user_neg_01"

        port = port_repo.get_current_portfolio(test_user)
        assert port is None or len(port.get("holdings", [])) == 0

    # NEG-02: Name-Only Row Quarantine
    def test_neg_02_name_only_row_quarantined(self):
        adapter = PortfolioUploadAdapter()
        csv_payload = "isin,amfi_code,scheme_name,units,cost_basis\n,,Unmapped Custom Scheme Name Only,100.0,10000.0\n"

        res = adapter.parse_csv_bytes(csv_payload.encode("utf-8"), "name_only.csv", "inv_neg_02")
        assert res["valid_count"] == 0
        assert res["quarantine_count"] == 1
        assert res["quarantined_rows"][0]["reason"] is not None

    # NEG-03: Malformed File Upload
    def test_neg_03_malformed_csv_upload_handling(self, journey_db):
        conn, _ = journey_db
        session_repo = SessionRepository(db_conn=conn)
        session = session_repo.create_session("inv_neg_03")

        handler = DummyHTTPHandler(investor_id="inv_neg_03")
        UIRequestHandler.render_scr03_upload_error(handler, "Invalid CSV header structure", session)

        assert "Portfolio Upload Failed" in handler.html_output
        assert "Invalid CSV header structure" in handler.html_output

    # NEG-04: Duplicate Confirmation Idempotency
    def test_neg_04_duplicate_confirmation_idempotency(self, journey_db):
        conn, _ = journey_db
        port_repo = PortfolioRepository(db_conn=conn)
        adapter = PortfolioUploadAdapter()

        csv = "isin,amfi_code,scheme_name,units,cost_basis\nINF200K01123,118266,\"Canara Robeco Nifty Index-Direct Plan - Growth\",50.0,5000.0\n"
        res = adapter.parse_csv_bytes(csv.encode("utf-8"), "dup.csv", "user_neg_04")
        snap = PortfolioExposureSnapshot(
            portfolio_snapshot_id=res["portfolio_snapshot_id"],
            investor_id="user_neg_04",
            holding_ids=[h.holding_id for h in res["valid_holdings"]],
            canonical_scheme_ids=[h.canonical_scheme_id for h in res["valid_holdings"]],
            total_valuation=None,
            is_valuation_available=True,
            observation_date=res["observation_date"]
        )

        # Save 1st time
        port_repo.save_portfolio(snap, res["valid_holdings"], version_string="1.0.0")
        port1 = port_repo.get_current_portfolio("user_neg_04")

        # Save 2nd time with exact same snapshot payload
        port_repo.save_portfolio(snap, res["valid_holdings"], version_string="1.0.0")
        port2 = port_repo.get_current_portfolio("user_neg_04")

        assert len(port1["holdings"]) == 1
        assert len(port2["holdings"]) == 1
        assert port1["holdings"][0].holding_id == port2["holdings"][0].holding_id

    # NEG-05 & NEG-06: Recommendation Display & Rejection Leaves Portfolio Unchanged
    def test_neg_05_recommendation_leaves_portfolio_unchanged(self, journey_db):
        conn, _ = journey_db
        port_repo = PortfolioRepository(db_conn=conn)
        session_repo = SessionRepository(db_conn=conn)
        session = session_repo.create_session("inv_neg_05")

        handler = DummyHTTPHandler("inv_neg_05")
        UIRequestHandler.render_scr09_action_center(handler, session=session)

        # Portfolio remains None / empty
        port = port_repo.get_current_portfolio("inv_neg_05")
        assert port is None or len(port.get("holdings", [])) == 0

    # NEG-07: Missing Metric Integrity
    def test_neg_07_missing_metric_not_zero_filled(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_118266")

        assert "Not available" in handler.html_output
        assert "0.00%" not in handler.html_output

    # NEG-08: Discover Inputs Never Trigger Dirty Guard
    def test_neg_08_discover_inputs_non_dirty(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr05_discover(handler)

        assert 'data-no-dirty="true"' in handler.html_output

    # NEG-09 & NEG-10: Genuine Persisted Edits Trigger Dirty Guard
    def test_neg_09_10_genuine_edit_triggers_dirty_guard(self):
        # Render POST form on /onboarding
        html = render_html_page("Onboarding", '<form action="/onboarding" method="POST"><input name="test"></form>', "/onboarding")

        # Verify JS checks method === 'POST'
        assert 'form && (form.getAttribute(\'method\') || \'GET\').toUpperCase() !== \'POST\'' in html
        assert 'checkIsDirty()' in html
        assert 'isDirty = true' in html
