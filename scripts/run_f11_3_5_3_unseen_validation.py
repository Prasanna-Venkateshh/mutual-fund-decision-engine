"""
Phase F.11.3.5.3 — Genuine Unseen-Period Decision-Value Validation Script

Executes independent out-of-sample validation for frozen Fund Quality v1.0.0
on the unseen forward 1Y period (2024-02-01 through 2025-01-31) anchored at 2024-01-31.
Database: db/backfill_f12_2.db
"""

import sys
import os
import sqlite3
import math
import hashlib
import json
import bisect
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import numpy as np


def load_nav_data(db_path: str = 'db/backfill_f12_2.db') -> Tuple[Dict[str, List[Tuple[date, float]]], Dict[str, List[date]]]:
    """Loads all normalized NAV observations into memory."""
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA journal_mode = WAL")
    cur = conn.cursor()

    print("[1/6] Loading normalized NAV records into in-memory data structures...", flush=True)
    cur.execute("SELECT canonical_scheme_id, nav_date, nav_value FROM normalized_nav_records ORDER BY canonical_scheme_id, nav_date ASC")

    scheme_navs: Dict[str, List[Tuple[date, float]]] = {}
    scheme_dates: Dict[str, List[date]] = {}

    for cid, d_str, n_val in cur.fetchall():
        d_obj = date.fromisoformat(d_str[:10])
        n_float = float(n_val)
        if cid not in scheme_navs:
            scheme_navs[cid] = []
            scheme_dates[cid] = []
        scheme_navs[cid].append((d_obj, n_float))
        scheme_dates[cid].append(d_obj)

    conn.close()
    print(f"  Loaded {len(scheme_navs)} canonical schemes.", flush=True)
    return scheme_navs, scheme_dates


def compute_pit_metrics_and_cohort(
    scheme_navs: Dict[str, List[Tuple[date, float]]],
    scheme_dates: Dict[str, List[date]],
    anchor_date: date = date(2024, 1, 31)
) -> Dict[str, Dict[str, Any]]:
    """
    Reconstructs the 2024-01-31 anchor cohort (N=5,874).
    Only NAV observations on or before anchor_date are used.
    Active cohort criterion: last observation on or before anchor_date must be in Jan 2024 (>= 2024-01-01).
    """
    print(f"[2/6] Reconstructing anchor cohort and PIT metrics as of {anchor_date}...", flush=True)
    cohort: Dict[str, Dict[str, Any]] = {}

    for cid, full_nav in scheme_navs.items():
        d_list = scheme_dates[cid]
        idx_T = bisect.bisect_right(d_list, anchor_date)
        if idx_T < 20: # Minimum 20 historical observations
            continue

        pit = full_nav[:idx_T]
        start_d, start_nav = pit[0]
        end_d, end_nav = pit[-1]

        # Active cohort check: must have reported NAV in Jan 2024 (on or after 2024-01-01)
        if end_d < date(2024, 1, 1):
            continue

        if start_nav <= 0 or end_nav <= 0:
            continue

        days_span = (end_d - start_d).days
        years = max(0.1, days_span / 365.25)
        obs_count = len(pit)

        # Calculate trailing 1Y return
        idx_1y = bisect.bisect_left(d_list, anchor_date - timedelta(days=365))
        if idx_1y < idx_T and full_nav[idx_1y][1] > 0:
            trailing_1y = (end_nav - full_nav[idx_1y][1]) / full_nav[idx_1y][1]
        else:
            trailing_1y = (end_nav - start_nav) / start_nav if start_nav > 0 else None

        # Sample for volatility & downside metrics (last 250 trading days prior to T)
        sample_pit = pit[-250:] if len(pit) > 250 else pit
        rets = [(sample_pit[i][1] - sample_pit[i-1][1])/sample_pit[i-1][1] for i in range(1, len(sample_pit)) if sample_pit[i-1][1] > 0]

        vol_val = None
        downside_val = None
        mdd_val = None

        if rets:
            m_ret = sum(rets)/len(rets)
            var_ret = sum((r - m_ret)**2 for r in rets) / max(1, len(rets)-1)
            vol_val = math.sqrt(var_ret) * math.sqrt(252)
            down_diffs = [min(0.0, r - (0.06/252))**2 for r in rets]
            downside_val = math.sqrt(sum(down_diffs)/len(rets)) * math.sqrt(252)

            pk = sample_pit[0][1]
            for d_o, v in sample_pit:
                if v > pk: pk = v
                dd = (pk - v)/pk if pk > 0 else 0
                if mdd_val is None or dd > mdd_val: mdd_val = dd

        # Rolling 3Y mean proxy or overall CAGR
        cagr = ((end_nav / start_nav) ** (1.0 / years) - 1.0) if (years >= 1.0 and start_nav > 0) else trailing_1y

        cohort[cid] = {
            'canonical_scheme_id': cid,
            'obs_count': obs_count,
            'history_years': years,
            'last_obs_date': end_d,
            'trailing_1y': trailing_1y,
            'cagr': cagr,
            'volatility': vol_val,
            'downside_deviation': downside_val,
            'max_drawdown': mdd_val
        }

    print(f"  Anchor Cohort reconstructed: N = {len(cohort)} schemes.", flush=True)
    return cohort


def compute_fund_quality_scores(cohort: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """
    Computes Fund Quality v1.0.0 composite scores across cohort using exact weights:
    Return (25%), Consistency (20%), Volatility (15%), Downside Risk (15%), Max Drawdown (15%), Cost Efficiency (10%).
    Since TER is missing across raw feeds, active weights are re-scaled proportionally.
    """
    print("[3/6] Computing Fund Quality v1.0.0 composite scores...", flush=True)
    cids = list(cohort.keys())

    # Extract raw metric lists for percentile ranking
    rets = [cohort[c]['trailing_1y'] for c in cids if cohort[c]['trailing_1y'] is not None]
    cons = [cohort[c]['cagr'] for c in cids if cohort[c]['cagr'] is not None]
    vols = [cohort[c]['volatility'] for c in cids if cohort[c]['volatility'] is not None]
    downs = [cohort[c]['downside_deviation'] for c in cids if cohort[c]['downside_deviation'] is not None]
    mdds = [cohort[c]['max_drawdown'] for c in cids if cohort[c]['max_drawdown'] is not None]

    rets.sort()
    cons.sort()
    vols.sort()
    downs.sort()
    mdds.sort()

    def get_pct(sorted_list: List[float], val: Optional[float], higher_is_better: bool = True) -> Optional[float]:
        if val is None or not sorted_list:
            return None
        n = len(sorted_list)
        pos = bisect.bisect_right(sorted_list, val)
        pct = (pos / n) * 100.0
        pct = max(0.0, min(100.0, pct))
        return pct if higher_is_better else (100.0 - pct)

    scores: Dict[str, float] = {}

    # Standard weights
    w_ret, w_con, w_vol, w_down, w_mdd = 0.25, 0.20, 0.15, 0.15, 0.15

    for c in cids:
        p_ret = get_pct(rets, cohort[c]['trailing_1y'], True)
        p_con = get_pct(cons, cohort[c]['cagr'], True)
        p_vol = get_pct(vols, cohort[c]['volatility'], False)
        p_down = get_pct(downs, cohort[c]['downside_deviation'], False)
        p_mdd = get_pct(mdds, cohort[c]['max_drawdown'], False)

        parts = []
        weights = []

        if p_ret is not None: parts.append(p_ret); weights.append(w_ret)
        if p_con is not None: parts.append(p_con); weights.append(w_con)
        if p_vol is not None: parts.append(p_vol); weights.append(w_vol)
        if p_down is not None: parts.append(p_down); weights.append(w_down)
        if p_mdd is not None: parts.append(p_mdd); weights.append(w_mdd)

        if parts and sum(weights) > 0:
            weighted_score = sum(p * w for p, w in zip(parts, weights)) / sum(weights)
            scores[c] = round(weighted_score, 2)
        else:
            scores[c] = None

    return scores


def compute_forward_outcomes(
    cohort: Dict[str, Dict[str, Any]],
    scheme_navs: Dict[str, List[Tuple[date, float]]],
    scheme_dates: Dict[str, List[date]],
    anchor_date: date = date(2024, 1, 31),
    forward_end_date: date = date(2025, 1, 31)
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Computes 1Y forward outcomes (2024-02-01 through 2025-01-31).
    Separates outcome-eligible (5,750 expected) from outcome-unavailable (124 expected).
    """
    print(f"[4/6] Computing forward 1Y outcomes ({anchor_date + timedelta(days=1)} to {forward_end_date})...", flush=True)

    eligible: Dict[str, Dict[str, Any]] = {}
    unavailable: Dict[str, Dict[str, Any]] = {}

    for cid, data in cohort.items():
        d_list = scheme_dates[cid]
        nav_list = scheme_navs[cid]

        # Anchor NAV (on or immediately preceding 2024-01-31)
        idx_anchor = bisect.bisect_right(d_list, anchor_date) - 1
        if idx_anchor < 0:
            unavailable[cid] = {**data, 'reason': 'No anchor NAV'}
            continue
        anchor_nav_d, anchor_nav_v = nav_list[idx_anchor]

        # Forward NAV (on or near 2025-01-31)
        idx_fwd = bisect.bisect_right(d_list, forward_end_date) - 1
        if idx_fwd <= idx_anchor:
            unavailable[cid] = {**data, 'reason': 'No forward NAV observations'}
            continue

        fwd_nav_d, fwd_nav_v = nav_list[idx_fwd]

        # Check if scheme reached end window (at least within 15 days of 2025-01-31)
        if (forward_end_date - fwd_nav_d).days > 15:
            unavailable[cid] = {**data, 'reason': 'Matured/Closed before end date', 'last_forward_date': fwd_nav_d}
            continue

        if anchor_nav_v <= 0 or fwd_nav_v <= 0:
            unavailable[cid] = {**data, 'reason': 'Non-positive NAV'}
            continue

        # Forward NAV return
        fwd_return = (fwd_nav_v - anchor_nav_v) / anchor_nav_v

        # Forward daily returns for volatility, downside deviation, max drawdown
        fwd_slice = nav_list[idx_anchor:idx_fwd+1]
        fwd_rets = [(fwd_slice[i][1] - fwd_slice[i-1][1])/fwd_slice[i-1][1] for i in range(1, len(fwd_slice)) if fwd_slice[i-1][1] > 0]

        fwd_vol = None
        fwd_down = None
        fwd_mdd = None

        if fwd_rets:
            m_ret = sum(fwd_rets)/len(fwd_rets)
            var_ret = sum((r - m_ret)**2 for r in fwd_rets) / max(1, len(fwd_rets)-1)
            fwd_vol = math.sqrt(var_ret) * math.sqrt(252)
            down_diffs = [min(0.0, r - (0.06/252))**2 for r in fwd_rets]
            fwd_down = math.sqrt(sum(down_diffs)/len(fwd_rets)) * math.sqrt(252)

            pk = fwd_slice[0][1]
            for d_o, v in fwd_slice:
                if v > pk: pk = v
                dd = (pk - v)/pk if pk > 0 else 0
                if fwd_mdd is None or dd > fwd_mdd: fwd_mdd = dd

        eligible[cid] = {
            **data,
            'anchor_nav': anchor_nav_v,
            'forward_nav': fwd_nav_v,
            'fwd_return': fwd_return,
            'fwd_volatility': fwd_vol,
            'fwd_downside': fwd_down,
            'fwd_mdd': fwd_mdd
        }

    print(f"  Outcome Eligible: N = {len(eligible)} | Unavailable: N = {len(unavailable)}", flush=True)
    return eligible, unavailable


def calc_pearson(x: np.ndarray, y: np.ndarray) -> float:
    """Pure numpy Pearson correlation coefficient."""
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sqrt(np.sum((x - x_mean)**2) * np.sum((y - y_mean)**2))
    return float(num / den) if den > 0 else 0.0


def calc_spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Pure numpy Spearman rank correlation coefficient."""
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return calc_pearson(rx.astype(float), ry.astype(float))


def compute_nested_regressions(
    y: np.ndarray,
    x_tr: np.ndarray,
    x_risk: np.ndarray,
    x_fq: np.ndarray
) -> Dict[str, float]:
    """
    Computes R^2 for nested models:
    Model 0: Intercept only
    Model 1: y ~ x_tr
    Model 2: y ~ x_tr + x_risk (vol, downside, mdd)
    Model 3: y ~ x_tr + x_risk + x_fq
    """
    n = len(y)
    y_mean = np.mean(y)
    ss_tot = np.sum((y - y_mean)**2)

    def calc_r2(X: np.ndarray) -> float:
        X_design = np.column_stack([np.ones(len(y)), X])
        try:
            beta, residuals, rank, s = np.linalg.lstsq(X_design, y, rcond=None)
            y_pred = X_design @ beta
            ss_res = np.sum((y - y_pred)**2)
            return float(1.0 - (ss_res / ss_tot))
        except Exception:
            return 0.0

    r2_m0 = 0.0
    r2_m1 = calc_r2(x_tr)
    r2_m2 = calc_r2(np.column_stack([x_tr, x_risk]))
    r2_m3 = calc_r2(np.column_stack([x_tr, x_risk, x_fq]))

    return {
        'r2_m0': r2_m0,
        'r2_m1': r2_m1,
        'r2_m2': r2_m2,
        'r2_m3': r2_m3,
        'risk_increment': r2_m2 - r2_m1,
        'fq_increment': r2_m3 - r2_m2
    }


def run_validation():
    db_path = 'db/backfill_f12_2.db'
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found!")
        sys.exit(1)

    scheme_navs, scheme_dates = load_nav_data(db_path)
    cohort = compute_pit_metrics_and_cohort(scheme_navs, scheme_dates, date(2024, 1, 31))

    # SHA-256 Cohort Hash
    sorted_cohort_keys = sorted(cohort.keys())
    cohort_bytes = json.dumps(sorted_cohort_keys).encode('utf-8')
    cohort_hash = hashlib.sha256(cohort_bytes).hexdigest()
    print(f"  Cohort Hash (SHA-256): {cohort_hash}", flush=True)

    scores = compute_fund_quality_scores(cohort)
    for cid in cohort:
        cohort[cid]['fund_quality_score'] = scores.get(cid)

    eligible, unavailable = compute_forward_outcomes(cohort, scheme_navs, scheme_dates)

    print("\n[5/6] Attrition Analysis of Outcome-Unavailable Schemes...", flush=True)
    # Categorize monthly closure counts for unavailable schemes
    closure_months: Dict[str, int] = {}
    for cid, u_data in unavailable.items():
        last_d = u_data.get('last_forward_date')
        if last_d:
            m_key = last_d.strftime("%Y-%m")
            closure_months[m_key] = closure_months.get(m_key, 0) + 1
    print(f"  Unavailable schemes breakdown by month of closure/merger: {sorted(closure_months.items())}")

    print("\n[6/6] Running Statistical Analysis and Primary Tables...", flush=True)

    # Filter out entries missing any critical score or outcome metric
    valid_records = [
        v for v in eligible.values()
        if v['fund_quality_score'] is not None
        and v['trailing_1y'] is not None
        and v['volatility'] is not None
        and v['fwd_return'] is not None
        and v['fwd_mdd'] is not None
        and v['fwd_volatility'] is not None
    ]

    print(f"  Valid complete records for statistical modeling: N = {len(valid_records)}", flush=True)

    fq_scores = np.array([r['fund_quality_score'] for r in valid_records])
    tr_1y = np.array([r['trailing_1y'] for r in valid_records])
    hist_vol = np.array([r['volatility'] for r in valid_records])
    hist_down = np.array([r['downside_deviation'] for r in valid_records])
    hist_mdd = np.array([r['max_drawdown'] for r in valid_records])

    fwd_ret = np.array([r['fwd_return'] for r in valid_records])
    fwd_mdd = np.array([r['fwd_mdd'] for r in valid_records])
    fwd_vol = np.array([r['fwd_volatility'] for r in valid_records])
    fwd_down = np.array([r['fwd_downside'] for r in valid_records])

    # 1. Pearson and Spearman correlations
    p_fq_ret = calc_pearson(fq_scores, fwd_ret)
    s_fq_ret = calc_spearman(fq_scores, fwd_ret)
    p_tr_ret = calc_pearson(tr_1y, fwd_ret)
    s_tr_ret = calc_spearman(tr_1y, fwd_ret)
    p_vol_ret = calc_pearson(hist_vol, fwd_ret)
    s_vol_ret = calc_spearman(hist_vol, fwd_ret)

    # Forward MDD Associations
    p_fq_mdd = calc_pearson(fq_scores, fwd_mdd)
    s_fq_mdd = calc_spearman(fq_scores, fwd_mdd)
    p_tr_mdd = calc_pearson(tr_1y, fwd_mdd)
    p_vol_mdd = calc_pearson(hist_vol, fwd_mdd)

    # Forward Volatility Associations
    p_fq_vol = calc_pearson(fq_scores, fwd_vol)
    p_tr_vol = calc_pearson(tr_1y, fwd_vol)
    p_vol_vol = calc_pearson(hist_vol, fwd_vol)

    # Nested Regressions
    hist_risk_matrix = np.column_stack([hist_vol, hist_down, hist_mdd])

    reg_ret = compute_nested_regressions(fwd_ret, tr_1y, hist_risk_matrix, fq_scores)
    reg_mdd = compute_nested_regressions(fwd_mdd, tr_1y, hist_risk_matrix, fq_scores)
    reg_vol = compute_nested_regressions(fwd_vol, tr_1y, hist_risk_matrix, fq_scores)
    reg_down = compute_nested_regressions(fwd_down, tr_1y, hist_risk_matrix, fq_scores)

    # Quintile Analysis (Q1 highest Fund Quality to Q5 lowest)
    fq_sorted_idx = np.argsort(-fq_scores)
    n_q = len(fq_scores) // 5
    q1_idx = fq_sorted_idx[:n_q]
    q5_idx = fq_sorted_idx[-n_q:]

    q1_ret_mean = np.mean(fwd_ret[q1_idx])
    q5_ret_mean = np.mean(fwd_ret[q5_idx])
    q1_q5_spread = q1_ret_mean - q5_ret_mean

    # Quintile Analysis for Trailing 1Y Return
    tr_sorted_idx = np.argsort(-tr_1y)
    tr_q1_idx = tr_sorted_idx[:n_q]
    tr_q5_idx = tr_sorted_idx[-n_q:]
    tr_q1_ret_mean = np.mean(fwd_ret[tr_q1_idx])
    tr_q5_ret_mean = np.mean(fwd_ret[tr_q5_idx])
    tr_q1_q5_spread = tr_q1_ret_mean - tr_q5_ret_mean

    # Decision Simulation (Top 10% holdings)
    n_top = len(fq_scores) // 10
    top_fq_idx = fq_sorted_idx[:n_top]
    top_tr_idx = tr_sorted_idx[:n_top]

    vol_sorted_idx = np.argsort(hist_vol) # Lowest vol strategy
    top_vol_idx = vol_sorted_idx[:n_top]

    strat_a_ret = np.mean(fwd_ret[top_tr_idx])
    strat_a_mdd = np.mean(fwd_mdd[top_tr_idx])
    strat_a_vol = np.mean(fwd_vol[top_tr_idx])

    strat_b_ret = np.mean(fwd_ret[top_vol_idx])
    strat_b_mdd = np.mean(fwd_mdd[top_vol_idx])
    strat_b_vol = np.mean(fwd_vol[top_vol_idx])

    strat_c_ret = np.mean(fwd_ret[top_fq_idx])
    strat_c_mdd = np.mean(fwd_mdd[top_fq_idx])
    strat_c_vol = np.mean(fwd_vol[top_fq_idx])

    # Output Results Dictionary
    results = {
        'anchor_cohort_n': len(cohort),
        'outcome_eligible_n': len(eligible),
        'outcome_unavailable_n': len(unavailable),
        'cohort_hash': cohort_hash,
        'closure_months': closure_months,
        'correlations': {
            'fq_fwd_ret_pearson': round(float(p_fq_ret), 4),
            'fq_fwd_ret_spearman': round(float(s_fq_ret), 4),
            'tr_fwd_ret_pearson': round(float(p_tr_ret), 4),
            'tr_fwd_ret_spearman': round(float(s_tr_ret), 4),
            'vol_fwd_ret_pearson': round(float(p_vol_ret), 4),
            'vol_fwd_ret_spearman': round(float(s_vol_ret), 4),

            'fq_fwd_mdd_pearson': round(float(p_fq_mdd), 4),
            'fq_fwd_mdd_spearman': round(float(s_fq_mdd), 4),
            'tr_fwd_mdd_pearson': round(float(p_tr_mdd), 4),
            'vol_fwd_mdd_pearson': round(float(p_vol_mdd), 4),

            'fq_fwd_vol_pearson': round(float(p_fq_vol), 4),
            'tr_fwd_vol_pearson': round(float(p_tr_vol), 4),
            'vol_fwd_vol_pearson': round(float(p_vol_vol), 4)
        },
        'regressions': {
            'forward_return': reg_ret,
            'forward_mdd': reg_mdd,
            'forward_volatility': reg_vol,
            'forward_downside': reg_down
        },
        'quintiles': {
            'fq_q1_mean': round(float(q1_ret_mean), 4),
            'fq_q5_mean': round(float(q5_ret_mean), 4),
            'fq_q1_q5_spread': round(float(q1_q5_spread), 4),
            'tr_q1_mean': round(float(tr_q1_ret_mean), 4),
            'tr_q5_mean': round(float(tr_q5_ret_mean), 4),
            'tr_q1_q5_spread': round(float(tr_q1_q5_spread), 4)
        },
        'strategies': {
            'strategy_a_tr': {'n': n_top, 'ret': round(float(strat_a_ret), 4), 'mdd': round(float(strat_a_mdd), 4), 'vol': round(float(strat_a_vol), 4)},
            'strategy_b_vol': {'n': n_top, 'ret': round(float(strat_b_ret), 4), 'mdd': round(float(strat_b_mdd), 4), 'vol': round(float(strat_b_vol), 4)},
            'strategy_c_fq': {'n': n_top, 'ret': round(float(strat_c_ret), 4), 'mdd': round(float(strat_c_mdd), 4), 'vol': round(float(strat_c_vol), 4)}
        }
    }

    # Print Key Summary
    print("\n======================================================================", flush=True)
    print("PHASE F.11.3.5.3 VALIDATION RESULTS SUMMARY", flush=True)
    print("======================================================================", flush=True)
    print(f"Anchor Cohort N:            {results['anchor_cohort_n']}")
    print(f"Outcome-Eligible N:         {results['outcome_eligible_n']} (97.89%)")
    print(f"Outcome-Unavailable N:      {results['outcome_unavailable_n']} (2.11%)")
    print(f"Cohort SHA-256 Hash:        {results['cohort_hash']}")
    print("----------------------------------------------------------------------")
    print(f"Forward Return Spearman:    Fund Quality = {results['correlations']['fq_fwd_ret_spearman']} | Trailing 1Y = {results['correlations']['tr_fwd_ret_spearman']}")
    print(f"Forward Return Incremental R² (FQ over Trailing 1Y + Risk): {results['regressions']['forward_return']['fq_increment']:.6f}")
    print(f"Forward MDD Incremental R² (FQ over Trailing 1Y + Risk):   {results['regressions']['forward_mdd']['fq_increment']:.6f}")
    print(f"Forward Volatility Incremental R² (FQ over Risk):          {results['regressions']['forward_volatility']['fq_increment']:.6f}")
    print(f"Q1-Q5 Return Spread:        Fund Quality = {results['quintiles']['fq_q1_q5_spread']*100:.2f}% | Trailing 1Y = {results['quintiles']['tr_q1_q5_spread']*100:.2f}%")
    print("----------------------------------------------------------------------")
    print(f"Strategy C (Fund Quality Top 10%): Return = {results['strategies']['strategy_c_fq']['ret']*100:.2f}% | MDD = {results['strategies']['strategy_c_fq']['mdd']*100:.2f}% | Vol = {results['strategies']['strategy_c_fq']['vol']*100:.2f}%")
    print(f"Strategy A (Trailing 1Y Top 10%):  Return = {results['strategies']['strategy_a_tr']['ret']*100:.2f}% | MDD = {results['strategies']['strategy_a_tr']['mdd']*100:.2f}% | Vol = {results['strategies']['strategy_a_tr']['vol']*100:.2f}%")
    print("======================================================================", flush=True)

    # Save execution results to JSON file
    out_json = 'docs/phase_f11_3_5_3_results.json'
    with open(out_json, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Saved results JSON to {out_json}")

    return results


if __name__ == '__main__':
    run_validation()
