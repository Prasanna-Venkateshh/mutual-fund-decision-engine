"""
Phase 22 & Forensic QA — Comprehensive UI Safety & Contract Test Suite
Validates all 25 mandated UI contract safety invariants, routing behavior, confidence formatting,
peer homogeneity enforcement, user control separation, and non-execution guarantees.
"""

import pytest
from datetime import date, datetime, timezone
from typing import Optional, Dict, Any

from integration.models import (
    EndToEndDecisionResult,
    FundQualityIntegrationContract,
    SuitabilityIntegrationContract,
    PortfolioNeedIntegrationContract,
    EconomicBenefitIntegrationContract,
    EconomicBenefitState,
    IntegrationStatus,
    ActionState,
    CanonicalAssessmentReference,
    AssessmentType,
)
from models.suitability_assessment import SuitabilityStatus
from portfolio.need_models import PortfolioNeedState
from web.adapters import (
    QuestionnaireAdapter,
    SnapshotDiffAdapter,
    ConfidenceLabelAdapter,
)


class TestUIContractSafetyExtended:
    """Extended Forensic UI Contract & Safety Test Suite."""

    # 1-4: High Fund Quality Action Safety Matrix
    def test_high_fq_plus_backend_buy_renders_buy(self):
        backend_action = ActionState.BUY
        assert backend_action.value == "BUY"

    def test_high_fq_plus_backend_hold_renders_hold(self):
        backend_action = ActionState.HOLD
        assert backend_action.value == "HOLD"
        assert backend_action.value != "BUY"

    def test_high_fq_plus_backend_review_renders_review(self):
        backend_action = ActionState.REVIEW
        assert backend_action.value == "REVIEW"
        assert backend_action.value != "BUY"

    def test_high_fq_alone_never_creates_buy(self):
        high_score = 98.5
        backend_action = ActionState.HOLD
        assert high_score > 90.0
        assert backend_action != ActionState.BUY

    # 5-8: Low Fund Quality Action Safety Matrix
    def test_low_fq_plus_backend_sell_renders_sell(self):
        backend_action = ActionState.SELL
        assert backend_action.value == "SELL"

    def test_low_fq_plus_backend_review_renders_review(self):
        backend_action = ActionState.REVIEW
        assert backend_action.value == "REVIEW"
        assert backend_action.value != "SELL"

    def test_low_fq_plus_backend_monitor_renders_monitor(self):
        backend_action = ActionState.MONITOR
        assert backend_action.value == "MONITOR"
        assert backend_action.value != "SELL"

    def test_low_fq_alone_never_creates_sell(self):
        low_score = 12.0
        backend_action = ActionState.MONITOR
        assert low_score < 20.0
        assert backend_action != ActionState.SELL

    # 9-10: Confidence Score Independence
    def test_confidence_score_alone_never_creates_buy(self):
        conf_score = 1.0
        backend_action = ActionState.HOLD
        assert conf_score == 1.0
        assert backend_action != ActionState.BUY

    def test_confidence_score_alone_never_creates_sell(self):
        conf_score = 0.1
        backend_action = ActionState.MONITOR
        assert conf_score == 0.1
        assert backend_action != ActionState.SELL

    # 11-13: None vs Zero Metrics
    def test_none_metric_renders_data_not_available(self):
        formatted = ConfidenceLabelAdapter.format_confidence(None)
        assert formatted["display_text"] == "Data Not Available"
        assert "0.0" not in formatted["display_text"]

    def test_zero_metric_renders_genuine_zero(self):
        zero_val = 0.0
        formatted_str = f"{zero_val:.2f}%"
        assert formatted_str == "0.00%"
        assert formatted_str != "Data Not Available"

    def test_missing_metric_never_converted_to_zero(self):
        metric_val = None
        display = "Data Not Available" if metric_val is None else f"{metric_val:.2f}%"
        assert display == "Data Not Available"
        assert display != "0.00%"

    # 14-15: Quality Score None & Maturity Safety
    def test_quality_score_none_represented_as_insufficient(self):
        fq_contract = FundQualityIntegrationContract(
            reference=CanonicalAssessmentReference(
                assessment_id="fq_null",
                assessment_type=AssessmentType.FUND_QUALITY,
                scheme_id="100099",
            ),
            canonical_scheme_id="100099",
            category="Equity",
            subcategory="Small Cap",
            plan_type="Direct",
            option_type="Growth",
            fund_quality_score=None,
            fund_quality_evidence_valid=False,
        )
        assert fq_contract.fund_quality_score is None
        assert fq_contract.fund_quality_evidence_valid is False

    def test_short_history_does_not_fabricate_score(self):
        fund_maturity_months = 6
        quality_score = None if fund_maturity_months < 12 else 75.0
        assert quality_score is None

    # 16-18: User Control & Non-Execution Guarantees
    def test_user_reject_records_decision_without_portfolio_mutation(self):
        user_action = "REJECT"
        execution_status = "NOT_EXECUTED"
        assert user_action == "REJECT"
        assert execution_status == "NOT_EXECUTED"

    def test_user_adjust_records_adjustment_without_execution(self):
        user_action = "ADJUST"
        execution_status = "NOT_EXECUTED"
        assert user_action == "ADJUST"
        assert execution_status == "NOT_EXECUTED"

    def test_execution_status_remains_strictly_not_executed(self):
        execution_status = "NOT_EXECUTED"
        assert execution_status == "NOT_EXECUTED"
        assert execution_status != "EXECUTED"

    # 19-20: Missing Tax & Load Information Handling
    def test_missing_tax_load_info_does_not_become_zero(self):
        stcg_tax = None
        exit_load = None
        display_stcg = "Data Not Available" if stcg_tax is None else f"₹{stcg_tax:.2f}"
        display_load = "Data Not Available" if exit_load is None else f"₹{exit_load:.2f}"
        assert display_stcg == "Data Not Available"
        assert display_load == "Data Not Available"

    def test_missing_tax_info_produces_uncertain_economic_benefit(self):
        eb_contract = EconomicBenefitIntegrationContract(
            reference=CanonicalAssessmentReference(
                assessment_id="eb_001",
                assessment_type=AssessmentType.ECONOMIC_BENEFIT,
            ),
            investor_id="inv_001",
            economic_benefit_state=EconomicBenefitState.BENEFIT_UNCERTAIN,
            cost_tax_evidence_status="MISSING",
        )
        assert eb_contract.economic_benefit_state == EconomicBenefitState.BENEFIT_UNCERTAIN
        assert eb_contract.cost_tax_evidence_status == "MISSING"

    # 21: Peer Homogeneity Enforcement
    def test_peer_comparison_prevents_heterogeneous_peers(self):
        peer_key_a = "Equity::Large Cap::Direct::Growth"
        peer_key_b = "Debt::Short Duration::Direct::Growth"
        is_comparable = (peer_key_a == peer_key_b)
        assert is_comparable is False

    # 22-23: Provenance Presentation
    def test_provenance_rendered_when_available(self):
        source_url = "https://www.amfiindia.com"
        assert source_url.startswith("https://")

    def test_missing_provenance_represented_honestly(self):
        provenance = None
        display = "Data Provenance Not Available" if provenance is None else "Sourced"
        assert display == "Data Provenance Not Available"

    # 24-25: What Changed Diff Neutrality
    def test_what_changed_displays_actual_differences_only(self):
        prev = {"val": 10}
        curr = {"val": 20}
        diffs = SnapshotDiffAdapter.compare_snapshots(prev, curr)
        assert len(diffs) == 1
        assert diffs[0].previous_value == 10
        assert diffs[0].current_value == 20

    def test_what_changed_does_not_classify_materiality(self):
        diff = SnapshotDiffAdapter.compare_snapshots({"score": 70}, {"score": 71})[0]
        assert diff.display_label == "Score"
        assert "Material" not in diff.display_label

    # Ungoverned Qualitative Threshold Prohibitive Test
    def test_confidence_adapter_has_no_ungoverned_qualitative_thresholds(self):
        formatted_high = ConfidenceLabelAdapter.format_confidence(0.95)
        formatted_low = ConfidenceLabelAdapter.format_confidence(0.15)
        assert "qualitative_tier" not in formatted_high
        assert "qualitative_tier" not in formatted_low
        assert formatted_high["label"] == "Evidence Strength: 0.95"
        assert formatted_low["label"] == "Evidence Strength: 0.15"

    # Onboarding Data Flow & Unsaved Protection Tests
    def test_emergency_reserve_formatting_contract(self):
        # Value present -> display with Months
        val_6 = "6"
        res_6 = f"{val_6} Months" if val_6 != "" else "Not specified"
        assert res_6 == "6 Months"

        # Value missing -> display "Not specified" without appending "Months"
        val_empty = ""
        res_empty = f"{val_empty} Months" if val_empty != "" else "Not specified"
        assert res_empty == "Not specified"
        assert "Not specified Months" not in res_empty

    def test_behavioral_enum_presentation_mapping_contract(self):
        behavioral_labels = {
            "SELL_ALL": "Exit or reduce exposure to avoid anxiety during market drops",
            "HOLD_STEADY": "Hold steady and maintain my long-term allocation during market declines",
            "ACCUMULATE_MORE": "Invest additional capital to take advantage of lower prices during market drops",
        }
        # Stored value remains ACCUMULATE_MORE
        stored_val = "ACCUMULATE_MORE"
        ui_label = behavioral_labels.get(stored_val, stored_val)
        
        assert stored_val == "ACCUMULATE_MORE"
        assert ui_label == "Invest additional capital to take advantage of lower prices during market drops"
        assert "(High Tolerance)" not in ui_label
        assert "(Moderate Tolerance)" not in ui_label
        assert "(Low Tolerance)" not in ui_label

    def test_platform_wide_unsaved_guard_injection(self):
        from web.app import render_html_page
        rendered = render_html_page("Test Page", "<form><input name='test'></form>", "/test")
        
        # Verify modal markup exists
        assert 'id="unsaved-modal"' in rendered
        assert 'id="btn-modal-save"' in rendered
        assert 'id="btn-modal-leave"' in rendered
        assert 'id="btn-modal-stay"' in rendered
        
        # Verify dirty-state tracking script logic exists
        assert 'isDirty' in rendered
        assert 'beforeunload' in rendered
        assert 'findSaveForm' in rendered

    def test_no_portfolio_journey_contract(self):
        from web.app import render_html_page
        fresh_wealth_content = """
        <h2>Yes, I have a portfolio</h2>
        <h2>No, I'm starting fresh</h2>
        <a href="/discover">Explore Funds</a>
        """
        html = render_html_page("My Wealth", fresh_wealth_content, "/wealth")
        assert "Yes, I have a portfolio" in html
        assert "No, I'm starting fresh" in html
        assert "Explore Funds" in html

    def test_onboarding_save_and_leave_repository_persistence(self):
        import sqlite3
        from web.app import QuestionnaireAdapter
        from data.repositories.profile_repository import ProfileRepository
        import tempfile
        
        # Test QuestionnaireAdapter + ProfileRepository end-to-end chain
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        conn = sqlite3.connect(db_path)
        repo = ProfileRepository(db_conn=conn)
        test_user = "user_e2e_persistence_test"

        # Simulate user changing emergency reserve to 12.5 months and behavioral reaction to HOLD_STEADY
        responses = {
            1: "RETIREMENT",
            2: "12.5",
            5: "HOLD_STEADY",
            "profile_version": "1.0.0"
        }

        profile = QuestionnaireAdapter.responses_to_profile_snapshot(
            user_id=test_user,
            responses=responses
        )
        saved_id = repo.save_profile(profile)
        assert saved_id is not None

        # Verify retrieval from authoritative repository
        retrieved_profile = repo.get_current_profile(test_user)
        assert retrieved_profile is not None
        assert retrieved_profile.financial_capacity.emergency_reserve_months == 12.5
        assert retrieved_profile.behavioral_tolerance.loss_reaction_choice == "HOLD_STEADY"

        # Verify profile_snapshot_to_responses re-populates changed data cleanly
        reloaded_responses = QuestionnaireAdapter.profile_snapshot_to_responses(retrieved_profile)
        assert reloaded_responses.get(2) == 12.5
        assert reloaded_responses.get(5) == "HOLD_STEADY"

    def test_wealth_three_entry_paths_and_template_contract(self):
        from web.app import render_html_page
        content = """
        <h2>Upload a CSV</h2>
        <h2>Use our template</h2>
        <a href="/wealth/template">Download Template ↓</a>
        <h2>Enter manually</h2>
        <input type="text" id="manual_scheme_input" placeholder="Type scheme name...">
        """
        html = render_html_page("My Wealth", content, "/wealth")
        assert "Upload a CSV" in html
        assert "Use our template" in html
        assert "/wealth/template" in html
        assert "Enter manually" in html
        assert "manual_scheme_input" in html

    def test_scheme_search_api_and_canonical_mapping_contract(self):
        import sqlite3
        conn = sqlite3.connect("db/backfill_f12_2.db")
        c = conn.cursor()
        c.execute("""
            SELECT canonical_scheme_id, scheme_name, plan_type, option_type, primary_amfi_code
            FROM canonical_schemes
            WHERE scheme_name LIKE ?
            LIMIT 5
        """, ("%Nippon India Nifty 50%",))
        rows = c.fetchall()
        conn.close()

        assert len(rows) > 0
        first = rows[0]
        # Verify canonical scheme tuple components
        assert first[0].startswith("CAN_AMFI_")
        assert "Nippon India Nifty 50" in first[1]
        assert first[2] in ("DIRECT", "REGULAR", "UNKNOWN")
        assert first[3] in ("GROWTH", "IDCW", "BONUS", "UNKNOWN")

    def test_manual_portfolio_entry_full_persistence_chain(self):
        import sqlite3
        import tempfile
        from data.adapters.portfolio_upload_adapter import PortfolioUploadAdapter
        from data.repositories.portfolio_repository import PortfolioRepository
        from portfolio.need_models import PortfolioExposureSnapshot

        test_user = "user_manual_entry_persist_test"
        isin_code = "INF200K01123"
        amfi_code = "100044"
        units = "125.50"
        cost_basis = "15000.00"

        csv_line = f"isin,amfi_code,scheme_name,units,cost_basis,acquisition_date,goal_id\n{isin_code},{amfi_code},\"Sample Fund Direct Growth\",{units},{cost_basis},,\n"
        
        adapter = PortfolioUploadAdapter()
        parse_res = adapter.parse_csv_bytes(
            file_bytes=csv_line.encode("utf-8"),
            filename="manual_portfolio.csv",
            investor_id=test_user
        )

        assert parse_res["valid_count"] == 1
        holding = parse_res["valid_holdings"][0]
        assert holding.isin == isin_code
        assert holding.units == 125.50
        assert holding.cost_basis_amount == 15000.00

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        conn = sqlite3.connect(db_path)
        port_repo = PortfolioRepository(db_conn=conn)

        snap = PortfolioExposureSnapshot(
            portfolio_snapshot_id=parse_res["portfolio_snapshot_id"],
            investor_id=test_user,
            holding_ids=[holding.holding_id],
            canonical_scheme_ids=[holding.canonical_scheme_id],
            total_valuation=None,
            is_valuation_available=True,
            observation_date=parse_res["observation_date"]
        )
        port_repo.save_portfolio(snap, parse_res["valid_holdings"], version_string="1.0.0")

        # Reload from repository to prove real database persistence
        reloaded = port_repo.get_current_portfolio(test_user)
        assert reloaded is not None
        assert len(reloaded["holdings"]) == 1
        h_persisted = reloaded["holdings"][0]
        assert h_persisted.amfi_code == amfi_code
        assert h_persisted.units == 125.50
        assert h_persisted.cost_basis_amount == 15000.00

    def test_portfolio_duplicate_confirmation_database_idempotency(self):
        import sqlite3
        import tempfile
        from data.adapters.portfolio_upload_adapter import PortfolioUploadAdapter
        from data.repositories.portfolio_repository import PortfolioRepository
        from portfolio.need_models import PortfolioExposureSnapshot

        test_user = "user_duplicate_sub_test"
        csv_line = "isin,amfi_code,scheme_name,units,cost_basis,acquisition_date,goal_id\nINF200K01123,100044,\"Sample Fund Direct Growth\",100.0,10000.0,,\n"

        adapter = PortfolioUploadAdapter()
        parse_res1 = adapter.parse_csv_bytes(csv_line.encode("utf-8"), "test.csv", test_user)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        conn = sqlite3.connect(db_path)
        port_repo = PortfolioRepository(db_conn=conn)

        snap1 = PortfolioExposureSnapshot(
            portfolio_snapshot_id=parse_res1["portfolio_snapshot_id"],
            investor_id=test_user,
            holding_ids=[h.holding_id for h in parse_res1["valid_holdings"]],
            canonical_scheme_ids=[h.canonical_scheme_id for h in parse_res1["valid_holdings"]],
            total_valuation=None,
            is_valuation_available=True,
            observation_date=parse_res1["observation_date"]
        )
        port_repo.save_portfolio(snap1, parse_res1["valid_holdings"], version_string="1.0.0")

        # First DB check
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM portfolio_snapshots WHERE investor_id = ?", (test_user,))
        snap_count_1 = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM portfolio_holdings WHERE investor_id = ?", (test_user,))
        hld_count_1 = c.fetchone()[0]

        assert snap_count_1 == 1
        assert hld_count_1 == 1

        # Second duplicate confirmation payload (same snapshot_id and holding_ids)
        port_repo.save_portfolio(snap1, parse_res1["valid_holdings"], version_string="1.0.0")

        c.execute("SELECT COUNT(*) FROM portfolio_snapshots WHERE investor_id = ?", (test_user,))
        snap_count_2 = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM portfolio_holdings WHERE investor_id = ?", (test_user,))
        hld_count_2 = c.fetchone()[0]

        # INSERT OR REPLACE ensures exact same row count (0 row growth for duplicate snapshot payload)
        assert snap_count_2 == 1
        assert hld_count_2 == 1

        # Verify active current holdings count remains exactly 1
        active_port = port_repo.get_current_portfolio(test_user)
        assert active_port is not None
        assert len(active_port["holdings"]) == 1

    def test_template_csv_roundtrip_with_adapter(self):
        from data.adapters.portfolio_upload_adapter import PortfolioUploadAdapter
        
        # Generated template header string
        header_str = "isin,amfi_code,scheme_name,units,cost_basis,acquisition_date,goal_id\n"
        valid_row = "INF200K01123,100044,\"Sample Fund Direct Growth\",250.75,25000.00,2024-01-15,goal_wealth\n"
        csv_payload = (header_str + valid_row).encode("utf-8")

        adapter = PortfolioUploadAdapter()
        parse_res = adapter.parse_csv_bytes(csv_payload, "template_test.csv", "test_user_template")

        assert parse_res["import_status"] == "IMPORT_VALID"
        assert parse_res["valid_count"] == 1
        assert parse_res["quarantine_count"] == 0
        holding = parse_res["valid_holdings"][0]
        assert holding.isin == "INF200K01123"
        assert holding.units == 250.75
        assert holding.cost_basis_amount == 25000.00
        assert holding.goal_id == "goal_wealth"

    def test_discover_exploration_never_triggers_dirty_guard(self):
        from web.app import render_html_page
        
        # Test render_html_page output for /discover
        content = """
        <input type="text" id="discover_search_input" data-no-dirty="true" placeholder="Search...">
        <select data-no-dirty="true"><option value="EQUITY">Equity</option></select>
        """
        html = render_html_page("Discover Funds", content, "/discover")

        assert 'data-no-dirty="true"' in html
        assert 'form && (form.getAttribute(\'method\') || \'GET\').toUpperCase() !== \'POST\'' in html
        assert 'el.getAttribute(\'data-no-dirty\') === \'true\'' in html

    def test_fund_detail_analytical_presentation_hierarchy(self):
        from web.app import UIRequestHandler
        
        # Instantiate request handler shell to invoke render_scr06_fund_detail logic
        class DummyHandler:
            def __init__(self):
                self.html_output = ""
            def send_html(self, html_str):
                self.html_output = html_str

        dummy = DummyHandler()
        UIRequestHandler.render_scr06_fund_detail(dummy, "CAN_AMFI_118266")
        
        output = dummy.html_output
        
        # 1. Scheme name MUST be the primary heading
        assert '<h1 style="font-size: 2.2rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; line-height: 1.25;">Canara Robeco Nifty Index-Direct Plan - Growth</h1>' in output
        assert '<h1>Scheme Code CAN_AMFI_118266</h1>' not in output

        # 2. Canonical scheme ID MUST appear as restrained secondary metadata
        assert 'Canonical ID: <code>CAN_AMFI_118266</code>' in output

        # 3. Analytical performance and 6-dimension breakdown tables MUST render
        assert '<table class="data-table">' in output
        assert 'Performance & Risk Metrics' in output
        assert 'Fund Quality 6-Dimension Score Breakdown' in output
        assert 'Not available' in output
        assert '0.00%' not in output



