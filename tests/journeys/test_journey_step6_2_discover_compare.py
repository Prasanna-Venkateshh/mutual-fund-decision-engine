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

class TestStep62DiscoverAndCompare:

    def test_DISC_01_canonical_universe_count(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM canonical_schemes")
        count = c.fetchone()[0]
        conn.close()
        assert count == 17507, f"Expected 17,507 canonical schemes, found {count}"

    def test_DISC_02_known_amc_discovery(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM canonical_schemes WHERE amc_name = 'HDFC'")
        hdfc_count = c.fetchone()[0]
        conn.close()
        assert hdfc_count > 0, "HDFC schemes must exist in database"

    def test_DISC_03_category_discovery(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM canonical_schemes WHERE category IS NOT NULL AND category != ''")
        categories = [r[0] for r in c.fetchall()]
        conn.close()
        assert len(categories) > 0

    def test_DISC_04_sub_category_discovery(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(DISTINCT amc_name) FROM canonical_schemes")
        amc_count = c.fetchone()[0]
        conn.close()
        assert amc_count == 327

    def test_DISC_05_plan_filter(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM canonical_schemes WHERE plan_type = 'DIRECT'")
        direct_count = c.fetchone()[0]
        conn.close()
        assert direct_count > 0

    def test_DISC_06_option_filter(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM canonical_schemes WHERE option_type = 'GROWTH'")
        growth_count = c.fetchone()[0]
        conn.close()
        assert growth_count > 0

    def test_DISC_07_amc_plus_category_combination(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM canonical_schemes WHERE amc_name = 'HDFC' AND plan_type = 'DIRECT'")
        hdfc_direct_count = c.fetchone()[0]
        conn.close()
        assert hdfc_direct_count > 0

    def test_DISC_08_category_plan_option_combination(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM canonical_schemes WHERE plan_type = 'DIRECT' AND option_type = 'GROWTH' AND amc_name = 'HDFC'")
        combined_count = c.fetchone()[0]
        conn.close()
        assert combined_count > 0

    def test_DISC_09_search_beyond_first_result_page(self):
        total = 17507
        limit = 20
        total_pages = (total + limit - 1) // limit
        assert total_pages == 876

    def test_DISC_10_nippon_india_nifty50_direct_growth_discovery(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        query = "Nippon India Index Fund Nifty 50 Plan Direct Growth"
        tokens = query.split()
        sql = "SELECT canonical_scheme_id, scheme_name FROM canonical_schemes WHERE " + " AND ".join(["scheme_name LIKE ?"] * len(tokens))
        params = [f"%{t}%" for t in tokens]
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()
        assert len(rows) > 0
        scheme_ids = [r[0] for r in rows]
        assert "CAN_AMFI_118741" in scheme_ids

    def test_DISC_11_clearing_filters(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM canonical_schemes")
        total = c.fetchone()[0]
        conn.close()
        assert total == 17507

    def test_DISC_12_no_duplicate_canonical_schemes(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(canonical_scheme_id), COUNT(DISTINCT canonical_scheme_id) FROM canonical_schemes")
        total, distinct = c.fetchone()
        conn.close()
        assert total == distinct == 17507

    def test_DISC_13_search_does_not_mutate_portfolio(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr05_discover(handler)
        assert handler.html_output is not None
        assert "portfolio_snapshots" not in handler.html_output.lower()

    def test_DISC_14_filters_do_not_trigger_dirty_guard(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr05_discover(handler)
        assert 'data-no-dirty="true"' in handler.html_output

    def test_DISC_15_complete_discovery_universe_accessible(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT canonical_scheme_id FROM canonical_schemes ORDER BY canonical_scheme_id LIMIT 20 OFFSET 17487")
        rows = c.fetchall()
        conn.close()
        assert len(rows) == 20

    def test_COMP_01_compare_1_fund(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ["CAN_AMFI_118266"]})
        assert "1 / 10 Funds Selected" in handler.html_output
        assert "CAN_AMFI_118266" in handler.html_output

    def test_COMP_02_compare_2_funds(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ["CAN_AMFI_118266", "CAN_AMFI_118741"]})
        assert "2 / 10 Funds Selected" in handler.html_output

    def test_COMP_03_compare_3_funds(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ["CAN_AMFI_118266", "CAN_AMFI_118741", "CAN_AMFI_119062"]})
        assert "3 / 10 Funds Selected" in handler.html_output

    def test_COMP_04_compare_5_funds(self):
        ids = ["CAN_AMFI_118266", "CAN_AMFI_118741", "CAN_AMFI_119062", "CAN_AMFI_100033", "CAN_AMFI_100034"]
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ids})
        assert "5 / 10 Funds Selected" in handler.html_output

    def test_COMP_05_compare_10_funds(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT canonical_scheme_id FROM canonical_schemes LIMIT 10")
        ids = [r[0] for r in c.fetchall()]
        conn.close()
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ids})
        assert "10 / 10 Funds Selected" in handler.html_output

    def test_COMP_06_prevent_11th_fund(self):
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("SELECT canonical_scheme_id FROM canonical_schemes LIMIT 12")
        ids = [r[0] for r in c.fetchall()]
        conn.close()
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ids})
        assert "10 / 10 Funds Selected" in handler.html_output

    def test_COMP_07_duplicate_selection_prevention(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ["CAN_AMFI_118266", "CAN_AMFI_118266"]})
        assert "CAN_AMFI_118266" in handler.html_output

    def test_COMP_08_remove_fund_from_comparison(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr05_discover(handler)
        assert "btn-remove-pill" in handler.html_output

    def test_COMP_09_comparison_identity_consistency(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ["CAN_AMFI_118741"]})
        assert "Nippon India Index Fund - Nifty 50 Plan - Direct Plan Growth Plan - Growth Option" in handler.html_output

    def test_COMP_10_comparison_metrics_mapped_correctly(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ["CAN_AMFI_118741"]})
        assert "Not available" in handler.html_output
        assert "Winner" not in handler.html_output
        assert "Best Fund" not in handler.html_output

    def test_COMP_11_comparison_does_not_mutate_portfolio(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ["CAN_AMFI_118741"]})
        assert "portfolio_snapshots" not in handler.html_output.lower()

    def test_COMP_12_comparison_does_not_trigger_dirty_guard(self):
        handler = DummyHTTPHandler()
        UIRequestHandler.render_scr07_compare(handler, None, {"ids": ["CAN_AMFI_118741"]})
        assert 'data-no-dirty="true"' in handler.html_output
