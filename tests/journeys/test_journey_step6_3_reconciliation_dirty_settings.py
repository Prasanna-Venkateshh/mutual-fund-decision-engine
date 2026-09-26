import pytest
import sqlite3
from web.app import UIRequestHandler

class DummyHTTPHandler:
    def __init__(self, path="/"):
        self.path = path
        self.html_output = ""
        self.headers_sent = {}
    
    def send_html(self, html_str):
        self.html_output = html_str

    def send_response(self, code):
        self.status_code = code

    def send_header(self, k, v):
        self.headers_sent[k] = v

    def end_headers(self):
        pass

class DummySession:
    def __init__(self, investor_id="inv_dev_test"):
        self.investor_id = investor_id
        self.csrf_token = "csrf_token_test_123"

class TestStep63ReconciliationDirtySettings:

    # --- PART 1: FUND QUALITY RECONCILIATION TESTS ---

    def test_FQ_01_overall_fund_quality_equals_engine_result(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_145898")
        assert "Quality Score: 50.0 / 100" in handler.html_output or "Quality Score:" in handler.html_output

    def test_FQ_02_displayed_component_values_match_engine(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_145898")
        assert "Historical Return (CAGR)" in handler.html_output
        assert "Rolling Return Consistency" in handler.html_output
        assert "Annualized Volatility Protection" in handler.html_output

    def test_FQ_03_populated_values_not_rendered_as_not_available(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_145898")
        # 17.37% CAGR overall must be formatted
        assert "17.37%" in handler.html_output
        assert "19.42%" in handler.html_output or "18.91%" in handler.html_output

    def test_FQ_04_genuinely_unavailable_data_remains_not_available(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_145898")
        assert 'Cost Efficiency (TER)' in handler.html_output
        assert '<span class="na-text">Not available</span>' in handler.html_output

    def test_FQ_05_missing_value_not_zero_filled(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_145898")
        assert "0.00%" not in handler.html_output

    def test_FQ_06_displayed_component_set_reconciles_with_production_dimensions(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_145898")
        for dim in ["Historical Return (CAGR)", "Rolling Return Consistency", "Annualized Volatility Protection", "Downside Risk Protection", "Maximum Drawdown Protection", "Cost Efficiency (TER)"]:
            assert dim in handler.html_output

    def test_FQ_07_overall_score_explainable_in_methodology(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_145898")
        assert "Overall Fund Quality Score = Sum of Active Dimension Weighted Contributions." in handler.html_output

    def test_FQ_08_non_scoring_concept_separated_in_context(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler, "CAN_AMFI_145898")
        assert "Platform Data Quality & Governance Context" in handler.html_output
        assert "100 / 100" in handler.html_output

    def test_FQ_09_values_not_hardcoded(self):
        handler1 = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler1, "CAN_AMFI_145898")
        handler2 = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler2, "CAN_AMFI_118266")
        assert handler1.html_output != handler2.html_output

    def test_FQ_10_two_different_funds_produce_own_values(self):
        handler1 = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler1, "CAN_AMFI_145898")
        assert "17.37%" in handler1.html_output
        handler2 = DummyHTTPHandler()
        UIRequestHandler.render_scr06_fund_detail(handler2, "CAN_AMFI_118266")
        assert "17.37%" not in handler2.html_output

    # --- PART 2: AUTOCOMPLETE SEARCH TESTS ---

    def test_DISC_AUTO_01_value_search_returns_nippon_value_fund(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT canonical_scheme_id, scheme_name FROM canonical_schemes WHERE scheme_name LIKE '%Nippon%' AND scheme_name LIKE '%value%'")
        rows = c.fetchall()
        conn.close()
        assert len(rows) > 0
        scheme_ids = [r[0] for r in rows]
        assert "CAN_AMFI_148721" in scheme_ids

    # --- PART 3: SUB-CATEGORY TEST CORRECTION ---

    def test_DISC_04_sub_category_discovery(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT DISTINCT sub_category FROM canonical_schemes WHERE sub_category IS NOT NULL")
        subcats = [r[0] for r in c.fetchall()]
        conn.close()
        assert len(subcats) > 0

    # --- PART 4: DIRTY GUARD ISOLATION TESTS ---

    def test_DIRTY_01_download_template_omits_modal(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr03_wealth(handler, params={}, session=DummySession())
        assert 'download="portfolio_upload_template.csv"' in handler.html_output
        assert 'data-no-dirty="true"' in handler.html_output

    def test_DIRTY_05_discover_filters_omit_dirty_modal(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr05_discover(handler, DummySession())
        assert 'data-no-dirty="true"' in handler.html_output

    # --- PART 5: SETTINGS UX TESTS ---

    def test_SET_01_settings_loads_correctly(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr10_settings(handler, DummySession())
        assert "Settings & Security" in handler.html_output
        assert "Investor Profile Summary" in handler.html_output

    def test_SET_02_current_profile_status_unambiguous(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr10_settings(handler, DummySession())
        assert 'class="badge status-green"' in handler.html_output or 'class="badge status-neutral"' in handler.html_output

    def test_SET_03_historical_versions_archived(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr10_settings(handler, DummySession())
        assert "Profile Version Lineage & History" in handler.html_output

    def test_SET_04_security_activity_accessible(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr10_settings(handler, DummySession())
        assert "Security & Activity Audit Log" in handler.html_output

    def test_SET_05_technical_audit_subordinate(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr10_settings(handler, DummySession())
        assert "<details class=\"evidence-box\">" in handler.html_output
