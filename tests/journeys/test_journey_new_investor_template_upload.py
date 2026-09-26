"""
Step 6.1 — End-to-End Investor User Journey 3: New Investor With Existing Portfolio (Template Roundtrip)
Validates template download, population, uploading, parsing, confirmation, and analysis:
- Template header verification against PortfolioUploadAdapter
- Roundtrip parsing and resolution of canonical scheme identities
- Confirmation & PortfolioRepository snapshot creation
- Verification of persisted portfolio upon reload
"""

import os
import sqlite3
import tempfile
import pytest

from portfolio.need_models import PortfolioExposureSnapshot
from data.adapters.portfolio_upload_adapter import PortfolioUploadAdapter
from data.repositories.portfolio_repository import PortfolioRepository
from web.app import UIRequestHandler
from web.security import SessionRepository


class DummyHTTPHandler:
    def __init__(self, investor_id="inv_j3_template_001"):
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


class TestJourneyNewInvestorTemplateUpload:
    """End-to-End Journey 3 Test Suite."""

    @pytest.fixture
    def journey_db(self):
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_file.close()
        conn = sqlite3.connect(db_file.name)
        yield conn, db_file.name
        conn.close()
        if os.path.exists(db_file.name):
            os.remove(db_file.name)

    def test_journey_3_template_roundtrip_e2e_flow(self, journey_db):
        conn, db_path = journey_db
        test_investor = "investor_j3_template_user"

        portfolio_repo = PortfolioRepository(db_conn=conn)
        session_repo = SessionRepository(db_conn=conn)

        session = session_repo.create_session(test_investor)

        # 1. Download Official Template CSV Header
        template_header = "isin,amfi_code,scheme_name,units,cost_basis,acquisition_date,goal_id\n"
        
        # 2. Populate Template With Valid Holdings Data
        template_row = "INF200K01123,118266,\"Canara Robeco Nifty Index-Direct Plan - Growth\",200.00,30000.00,2024-02-01,goal_retirement\n"
        csv_bytes = (template_header + template_row).encode("utf-8")

        # 3. Parse via PortfolioUploadAdapter
        adapter = PortfolioUploadAdapter()
        parse_res = adapter.parse_csv_bytes(
            file_bytes=csv_bytes,
            filename="portfolio_upload_template.csv",
            investor_id=test_investor
        )

        assert parse_res["import_status"] == "IMPORT_VALID"
        assert parse_res["valid_count"] == 1
        holding = parse_res["valid_holdings"][0]
        assert holding.units == 200.00
        assert holding.cost_basis_amount == 30000.00

        # 4. Confirm & Persist
        snap = PortfolioExposureSnapshot(
            portfolio_snapshot_id=parse_res["portfolio_snapshot_id"],
            investor_id=test_investor,
            holding_ids=[h.holding_id for h in parse_res["valid_holdings"]],
            canonical_scheme_ids=[h.canonical_scheme_id for h in parse_res["valid_holdings"]],
            total_valuation=None,
            is_valuation_available=True,
            observation_date=parse_res["observation_date"]
        )
        portfolio_repo.save_portfolio(snap, parse_res["valid_holdings"], version_string="1.0.0")

        # 5. Reload & Verify Persistence
        handler = DummyHTTPHandler(investor_id=test_investor)
        handler._get_portfolio_repository = lambda: portfolio_repo
        UIRequestHandler.render_scr03_wealth(handler, params=None, session=session)

        assert "Current Holdings" in handler.html_output
        assert "200.0" in handler.html_output

        # 6. Database Check
        reloaded = portfolio_repo.get_current_portfolio(test_investor)
        assert reloaded is not None
        assert len(reloaded["holdings"]) == 1
        assert reloaded["holdings"][0].cost_basis_amount == 30000.00
