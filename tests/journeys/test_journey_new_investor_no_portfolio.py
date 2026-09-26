"""
Step 6.1 — End-to-End Investor User Journey 1: New Investor With No Portfolio
Validates complete user journey for a new investor with no existing portfolio:
- Isolated authentication & session handling
- Onboarding & profile snapshot persistence
- Non-blocking zero-portfolio state
- Recommendation & investment guidance display
- Strict zero automatic execution invariant (holdings remain empty)
"""

import os
import sqlite3
import tempfile
import pytest
from datetime import date

from data.repositories.profile_repository import ProfileRepository
from data.repositories.portfolio_repository import PortfolioRepository
from web.adapters import QuestionnaireAdapter
from web.app import UIRequestHandler, render_html_page
from web.security import SessionRepository, SecurityManager, SessionRecord


class DummyHTTPHandler:
    """Mock HTTP handler to capture HTML/JSON outputs from UIRequestHandler methods."""
    def __init__(self, investor_id="inv_j1_nop_001"):
        self.investor_id = investor_id
        self.html_output = ""
        self.json_output = {}
        self.status_code = 200

    def send_response(self, code: int, message: str = None):
        self.status_code = code

    def send_header(self, keyword: str, value: str):
        pass

    def end_headers(self):
        pass

    def send_html(self, html_str: str):
        self.html_output = html_str

    def send_json(self, data: dict):
        self.json_output = data

    def send_error(self, code: int, message: str = ""):
        self.status_code = code
        self.html_output = message


class TestJourneyNewInvestorNoPortfolio:
    """End-to-End Journey 1 Test Suite."""

    @pytest.fixture
    def journey_db(self):
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_file.close()
        conn = sqlite3.connect(db_file.name)
        yield conn, db_file.name
        conn.close()
        if os.path.exists(db_file.name):
            os.remove(db_file.name)

    def test_journey_1_full_e2e_flow(self, journey_db):
        conn, db_path = journey_db
        test_investor = "investor_j1_e2e_nop"

        # Initialize repositories
        profile_repo = ProfileRepository(db_conn=conn)
        portfolio_repo = PortfolioRepository(db_conn=conn)
        session_repo = SessionRepository(db_conn=conn)

        # 1. Step 1: Authentication & Session Creation
        session = session_repo.create_session(test_investor)
        assert session is not None
        assert session.investor_id == test_investor

        # 2. Step 2 & 3: Onboarding & Profile Persistence
        responses = {
            1: "WEALTH_ACCUMULATION",
            2: "6.0",
            5: "HOLD_STEADY",
            "profile_version": "1.0.0"
        }
        profile_snap = QuestionnaireAdapter.responses_to_profile_snapshot(
            user_id=test_investor,
            responses=responses
        )
        saved_id = profile_repo.save_profile(profile_snap)
        assert saved_id is not None

        # Verify Profile Persistence
        loaded_profile = profile_repo.get_current_profile(test_investor)
        assert loaded_profile is not None
        assert loaded_profile.financial_capacity.emergency_reserve_months == 6.0
        assert loaded_profile.behavioral_tolerance.loss_reaction_choice == "HOLD_STEADY"

        # 4. Step 4 & 5: Verify Zero Portfolio State Is Non-Blocking
        portfolio = portfolio_repo.get_current_portfolio(test_investor)
        assert portfolio is None or len(portfolio.get("holdings", [])) == 0

        # Render My Wealth for User with No Holdings
        handler = DummyHTTPHandler(investor_id=test_investor)
        handler._get_portfolio_repository = lambda: portfolio_repo
        UIRequestHandler.render_scr03_wealth(handler, params=None, session=session)

        # Assert UI contains options to upload, download template, enter manually, or explore
        assert "Upload a CSV" in handler.html_output
        assert "Download Template ↓" in handler.html_output
        assert "Enter Holding Manually" in handler.html_output
        assert "No Portfolio Imported" in handler.html_output

        # 5. Step 6 & 7: Recommendation & Action Center Review
        UIRequestHandler.render_scr09_action_center(handler, session=session)

        assert "Actions & Recommendations" in handler.html_output
        assert "0 Pending Review" in handler.html_output

        # 6. Step 8: Strict Zero Automatic Execution Invariant
        post_portfolio = portfolio_repo.get_current_portfolio(test_investor)
        assert post_portfolio is None or len(post_portfolio.get("holdings", [])) == 0
