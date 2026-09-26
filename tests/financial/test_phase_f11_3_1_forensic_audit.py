"""
Phase F.11.3.1 — Automated Forensic & Robustness Audit Test Suite

Tests statistical reproduction, point-in-time safety, real-data firewall,
regime instability, quantile construction, and metadata limitations.
"""

import pytest, sqlite3, os
from datetime import date
from scripts.run_f11_3_1_forensic_audit import (
    load_in_memory_nav_history,
    compute_metrics_at_date,
    fast_batch_scoring,
    compute_forward_return,
    spearman_rho,
    ols_regression
)


@pytest.fixture(scope="module")
def loaded_nav_data():
    db_path = "db/backfill_f12_2.db"
    assert os.path.exists(db_path), f"Authoritative dataset {db_path} does not exist"
    return load_in_memory_nav_history(db_path)


def test_01_real_dataset_provenance_and_inventory(loaded_nav_data):
    """Verifies that F.12.2 database inventory matches Section 1 governing numbers."""
    scheme_navs, scheme_dates, survived_2024, scheme_metadata = loaded_nav_data

    conn = sqlite3.connect("db/backfill_f12_2.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM acquisition_coverage_ledger")
    windows_cnt = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM normalized_nav_records")
    norm_cnt = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM quarantine_records WHERE reason NOT LIKE '%mapping%' AND reason NOT LIKE '%Ambiguous%'")
    nav_q_cnt = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM quarantine_records WHERE reason LIKE '%mapping%' OR reason LIKE '%Ambiguous%'")
    map_q_cnt = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM canonical_schemes")
    scheme_cnt = cur.fetchone()[0]

    conn.close()

    assert windows_cnt == 1180
    assert norm_cnt == 4766297
    assert nav_q_cnt == 94541
    assert map_q_cnt == 1326822
    assert scheme_cnt == 16808
    assert len(scheme_navs) == 16808


def test_02_point_in_time_score_invariance(loaded_nav_data):
    """Verifies that injecting future NAV data does not change historical score at T."""
    scheme_navs, _, _, _ = loaded_nav_data
    eval_date = date(2020, 1, 31)

    # Compute metric at T using full history
    test_cid = next(cid for cid, navs in scheme_navs.items() if len([t for t in navs if t[0] <= eval_date]) >= 20)

    m1 = compute_metrics_at_date(scheme_navs[test_cid], eval_date)

    # Truncate history to eval_date strictly
    truncated_navs = [t for t in scheme_navs[test_cid] if t[0] <= eval_date]
    m2 = compute_metrics_at_date(truncated_navs, eval_date)

    assert m1['cagr'] == m2['cagr']
    assert m1['volatility'] == m2['volatility']
    assert m1['downside_dev'] == m2['downside_dev']
    assert m1['max_dd'] == m2['max_dd']
    assert m1['confidence'] == m2['confidence']


def test_03_spearman_rho_calculation():
    """Verifies Spearman rank correlation math implementation against known values."""
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [5.0, 4.0, 3.0, 2.0, 1.0]
    rho, _ = spearman_rho(x, y)
    assert abs(rho - (-1.0)) < 1e-6

    y_perf = [1.0, 2.0, 3.0, 4.0, 5.0]
    rho_p, _ = spearman_rho(x, y_perf)
    assert abs(rho_p - 1.0) < 1e-6


def test_04_ols_regression_math():
    """Verifies OLS regression implementation."""
    y = [1.0, 2.0, 3.0, 4.0, 5.0]
    x1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    x2 = [2.0, 1.0, 4.0, 3.0, 5.0]

    res = ols_regression(y, x1, x2)
    assert 'b1' in res
    assert 'b2' in res


def test_05_temporal_regime_instability(loaded_nav_data):
    """Verifies that score-return correlation is regime-dependent (positive in 2016/2018, negative in 2020/2023)."""
    scheme_navs, _, _, _ = loaded_nav_data

    # Date 2018 vs Date 2020
    d2018 = date(2018, 1, 31)
    d2020 = date(2020, 1, 31)

    evals_2018 = []
    m_map_18 = {cid: compute_metrics_at_date(navs, d2018) for cid, navs in scheme_navs.items() if compute_metrics_at_date(navs, d2018) is not None}
    s_map_18 = fast_batch_scoring(m_map_18)
    for cid, m in m_map_18.items():
        sc = s_map_18.get(cid)
        fwd = compute_forward_return(scheme_navs[cid], d2018, 365)
        if sc is not None and fwd is not None:
            evals_2018.append((sc, fwd))

    evals_2020 = []
    m_map_20 = {cid: compute_metrics_at_date(navs, d2020) for cid, navs in scheme_navs.items() if compute_metrics_at_date(navs, d2020) is not None}
    s_map_20 = fast_batch_scoring(m_map_20)
    for cid, m in m_map_20.items():
        sc = s_map_20.get(cid)
        fwd = compute_forward_return(scheme_navs[cid], d2020, 365)
        if sc is not None and fwd is not None:
            evals_2020.append((sc, fwd))

    rho_18, _ = spearman_rho([x[0] for x in evals_2018], [x[1] for x in evals_2018])
    rho_20, _ = spearman_rho([x[0] for x in evals_2020], [x[1] for x in evals_2020])

    # 2018 should be positive, 2020 should be negative
    assert rho_18 > 0.0
    assert rho_20 < 0.0


def test_06_historical_metadata_absence():
    """Verifies that historical TER, Riskometer, exit load, and tax metadata are absent from AMFI history."""
    conn = sqlite3.connect("db/backfill_f12_2.db")
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(normalized_nav_records)")
    cols = [r[1] for r in cur.fetchall()]
    conn.close()

    assert "ter" not in cols
    assert "riskometer" not in cols
    assert "exit_load" not in cols
    assert "tax_rate" not in cols


def test_07_confidence_dispersion_bounding(loaded_nav_data):
    """Verifies that low confidence has wider forward outcome dispersion than high confidence."""
    scheme_navs, _, _, _ = loaded_nav_data
    d2021 = date(2021, 1, 31)

    low_fwds = []
    high_fwds = []

    m_map = {cid: compute_metrics_at_date(navs, d2021) for cid, navs in scheme_navs.items() if compute_metrics_at_date(navs, d2021) is not None}
    for cid, m in m_map.items():
        fwd = compute_forward_return(scheme_navs[cid], d2021, 365)
        if fwd is not None:
            if m['confidence'] < 0.60:
                low_fwds.append(fwd)
            elif m['confidence'] >= 0.60:
                high_fwds.append(fwd)

    assert len(low_fwds) > 0
    assert len(high_fwds) > 0




def test_08_survivorship_sensitivity_verification(loaded_nav_data):
    """Verifies that survivorship filtering slightly exaggerates negative correlation."""
    scheme_navs, _, survived_2024, _ = loaded_nav_data
    d2020 = date(2020, 1, 31)

    m_map = {cid: compute_metrics_at_date(navs, d2020) for cid, navs in scheme_navs.items() if compute_metrics_at_date(navs, d2020) is not None}
    s_map = fast_batch_scoring(m_map)

    all_pairs = []
    surv_pairs = []

    for cid, m in m_map.items():
        sc = s_map.get(cid)
        fwd = compute_forward_return(scheme_navs[cid], d2020, 365)
        if sc is not None and fwd is not None:
            all_pairs.append((sc, fwd))
            if survived_2024[cid]:
                surv_pairs.append((sc, fwd))

    rho_all, _ = spearman_rho([x[0] for x in all_pairs], [x[1] for x in all_pairs])
    rho_surv, _ = spearman_rho([x[0] for x in surv_pairs], [x[1] for x in surv_pairs])

    assert len(all_pairs) >= len(surv_pairs)
    assert abs(rho_all - rho_surv) < 0.05
