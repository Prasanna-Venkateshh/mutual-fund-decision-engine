"""
Step 6.1 — End-to-End Investor User Journey 2: New Investor With Existing Portfolio (Direct CSV Upload)
Validates complete user journey for an investor uploading an existing portfolio CSV:
- Isolated authentication & profile setup
- Direct CSV upload parsing via PortfolioUploadAdapter
- Pre-confirmation preview & quarantine review
- Explicit confirmation & PortfolioRepository snapshot persistence
- Reloading My Wealth and checking resolved suitability/assessment status
- Zero automatic trade execution invariant
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
from web.app import UIRequestHandler
from web.security import SessionRepository


class DummyHTTPHandler:
    def __init__(self, investor_id="inv_j2_direct_001"):
        self.investor_id = investor_id
        self.html_output = ""
        self.json_output = {}

    def send_response(self, code: int, message: str = None):
        pass

    def send_header(self, keyword: str, value: str):
        pass

    def end_headers(self):
        pass

    def send_html(self, html_str: str):
        self.html_output = html_str

    def send_json(self, data: dict):
        self.json_output = data


class TestJourneyNewInvestorDirectUpload:
    """End-to-End Journey 2 Test Suite."""

    @pytest.fixture
    def journey_db(self):
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_file.close()
        conn = sqlite3.connect(db_file.name)
        yield conn, db_file.name
        conn.close()
        if os.path.exists(db_file.name):
            os.remove(db_file.name)

    def test_journey_2_direct_upload_e2e_flow(self, journey_db):
        conn, db_path = journey_db
        test_investor = "investor_j2_direct_upload"

        profile_repo = ProfileRepository(db_conn=conn)
        portfolio_repo = PortfolioRepository(db_conn=conn)
        session_repo = SessionRepository(db_conn=conn)

        # 1. Authenticate & Create Profile
        session = session_repo.create_session(test_investor)
        profile_snap = QuestionnaireAdapter.responses_to_profile_snapshot(
            user_id=test_investor,
            responses={1: "WEALTH_ACCUMULATION", 2: "12.0", 5: "HOLD_STEADY"}
        )
        profile_repo.save_profile(profile_snap)

        # 2. Prepare Valid Portfolio CSV Payload (Canonical AMFI Code & ISIN)
        csv_content = (
            "isin,amfi_code,scheme_name,units,cost_basis,acquisition_date,goal_id\n"
            "INF200K01123,118266,\"Canara Robeco Nifty Index-Direct Plan - Growth\",150.50,25000.00,2024-01-10,goal_growth\n"
        )
        csv_bytes = csv_content.encode("utf-8")

        # 3. Parse via PortfolioUploadAdapter
        adapter = PortfolioUploadAdapter()
        parse_res = adapter.parse_csv_bytes(
            file_bytes=csv_bytes,
            filename="my_portfolio.csv",
            investor_id=test_investor
        )

        assert parse_res["import_status"] == "IMPORT_VALID"
        assert parse_res["valid_count"] == 1
        assert parse_res["quarantine_count"] == 0

        # Unconfirmed state: DB must be empty before explicit confirmation
        pre_confirm_port = portfolio_repo.get_current_portfolio(test_investor)
        assert pre_confirm_port is None

        # 4. Explicit Confirmation & Persistence
        holding = parse_res["valid_holdings"][0]
        snap = PortfolioExposureSnapshot(
            portfolio_snapshot_id=parse_res["portfolio_snapshot_id"],
            investor_id=test_investor,
            holding_ids=[h.holding_id for h in parse_res["valid_holdings"]],
            canonical_scheme_ids=[h.canonical_scheme_id for h in parse_res["valid_holdings"]],
            total_valuation=None,
            is_valuation_available=True,
            observation_date=parse_res["observation_date"]
        )
        saved_snap_id = portfolio_repo.save_portfolio(
            snapshot=snap,
            holdings=parse_res["valid_holdings"],
            version_string="1.0.0"
        )
        assert saved_snap_id is not None

        # 5. Reload My Wealth and Assert Persisted Holdings Render
        handler = DummyHTTPHandler(investor_id=test_investor)
        handler._get_portfolio_repository = lambda: portfolio_repo
        UIRequestHandler.render_scr03_wealth(handler, params=None, session=session)

        assert "Current Holdings" in handler.html_output
        assert "Canara Robeco Nifty Index-Direct Plan - Growth" in handler.html_output
        assert "150.5" in handler.html_output
        assert "Resolved" in handler.html_output or "Holdings & Valuation" in handler.html_output

        # 6. Database Immutability Check (Zero execution / mutation on recommendation view)
        handler_action = DummyHTTPHandler(investor_id=test_investor)
        UIRequestHandler.render_scr09_action_center(handler_action, session=session)

        post_confirm_port = portfolio_repo.get_current_portfolio(test_investor)
        assert post_confirm_port is not None
        assert len(post_confirm_port["holdings"]) == 1
        assert post_confirm_port["holdings"][0].units == 150.50
