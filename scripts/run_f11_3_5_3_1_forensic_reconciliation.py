"""
Phase F.11.3.5.3.1 — OOS Validation Forensic Reconciliation Script

Performs forensic reconciliation of Phase F.11.3.5.3 cohort discrepancy (5,874 vs 5,832)
and audits statistical, risk, strategy, and category composition findings.
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

    print("[1/7] Loading normalized NAV records into in-memory data structures...", flush=True)
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


def get_f12_3_1_2_cohort_5874(db_path: str = 'db/backfill_f12_2.db') -> set:
    """Fetches exact 5,874 schemes from F.12.3.1.2 query (nav_date = '2024-01-31')."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT canonical_scheme_id FROM normalized_nav_records WHERE nav_date = '2024-01-31'")
    cids = {r[0] for r in cur.fetchall()}
    conn.close()
    return cids


def compute_cohort_metrics(
    scheme_cids: set,
    scheme_navs: Dict[str, List[Tuple[date, float]]],
    scheme_dates: Dict[str, List[date]],
    anchor_date: date = date(2024, 1, 31)
) -> Dict[str, Dict[str, Any]]:
    """Computes PIT metrics for a specific set of canonical scheme IDs."""
    cohort: Dict[str, Dict[str, Any]] = {}

    for cid in scheme_cids:
        if cid not in scheme_navs:
            continue
        d_list = scheme_dates[cid]
        full_nav = scheme_navs[cid]

        idx_T = bisect.bisect_right(d_list, anchor_date)
        if idx_T < 1:
            continue

        pit = full_nav[:idx_T]
        start_d, start_nav = pit[0]
        end_d, end_nav = pit[-1]

        obs_count = len(pit)
        days_span = (end_d - start_d).days
        years = max(0.1, days_span / 365.25)

        idx_1y = bisect.bisect_left(d_list, anchor_date - timedelta(days=365))
        if idx_1y < idx_T and full_nav[idx_1y][1] > 0:
            trailing_1y = (end_nav - full_nav[idx_1y][1]) / full_nav[idx_1y][1]
        else:
            trailing_1y = (end_nav - start_nav) / start_nav if start_nav > 0 else None

        sample_pit = pit[-250:] if len(pit) > 250 else pit
        rets = [(sample_pit[i][1] - sample_pit[i-1][1])/sample_pit[i-1][1] for i in range(1, len(sample_pit)) if sample_pit[i-1][1] > 0]

        vol_val = None
        downside_val = None
        mdd_val = None

        if len(rets) >= 2:
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

        cagr = ((end_nav / start_nav) ** (1.0 / years) - 1.0) if (years >= 1.0 and start_nav > 0) else trailing_1y

        cohort[cid] = {
            'canonical_scheme_id': cid,
            'obs_count': obs_count,
            'history_years': years,
            'last_obs_date': end_d,
            'start_obs_date': start_d,
            'trailing_1y': trailing_1y,
            'cagr': cagr,
            'volatility': vol_val,
            'downside_deviation': downside_val,
            'max_drawdown': mdd_val
        }

    return cohort


def compute_fund_quality_scores(cohort: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """Computes Fund Quality v1.0.0 composite scores across cohort."""
    cids = list(cohort.keys())

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
        if val is None or not sorted_list: return None
        pos = bisect.bisect_right(sorted_list, val)
        pct = (pos / len(sorted_list)) * 100.0
        return pct if higher_is_better else (100.0 - pct)

    scores: Dict[str, float] = {}
    w_ret, w_con, w_vol, w_down, w_mdd = 0.25, 0.20, 0.15, 0.15, 0.15

    for c in cids:
        # Minimum 20 observations for valid score calculation
        if cohort[c]['obs_count'] < 20:
            scores[c] = None
            continue

        p_ret = get_pct(rets, cohort[c]['trailing_1y'], True)
        p_con = get_pct(cons, cohort[c]['cagr'], True)
        p_vol = get_pct(vols, cohort[c]['volatility'], False)
        p_down = get_pct(downs, cohort[c]['downside_deviation'], False)
        p_mdd = get_pct(mdds, cohort[c]['max_drawdown'], False)

        parts, weights = [], []
        if p_ret is not None: parts.append(p_ret); weights.append(w_ret)
        if p_con is not None: parts.append(p_con); weights.append(w_con)
        if p_vol is not None: parts.append(p_vol); weights.append(w_vol)
        if p_down is not None: parts.append(p_down); weights.append(w_down)
        if p_mdd is not None: parts.append(p_mdd); weights.append(w_mdd)

        if parts and sum(weights) > 0:
            scores[c] = round(sum(p * w for p, w in zip(parts, weights)) / sum(weights), 2)
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
    """Computes 1Y forward outcomes and separates eligible from unavailable."""
    eligible: Dict[str, Dict[str, Any]] = {}
    unavailable: Dict[str, Dict[str, Any]] = {}

    for cid, data in cohort.items():
        d_list = scheme_dates[cid]
        nav_list = scheme_navs[cid]

        idx_anchor = bisect.bisect_right(d_list, anchor_date) - 1
        if idx_anchor < 0:
            unavailable[cid] = {**data, 'reason': 'No anchor NAV'}
            continue
        anchor_nav_d, anchor_nav_v = nav_list[idx_anchor]

        idx_fwd = bisect.bisect_right(d_list, forward_end_date) - 1
        if idx_fwd <= idx_anchor:
            unavailable[cid] = {**data, 'reason': 'No forward NAV observations'}
            continue

        fwd_nav_d, fwd_nav_v = nav_list[idx_fwd]

        if (forward_end_date - fwd_nav_d).days > 15:
            unavailable[cid] = {**data, 'reason': 'Matured/Closed before end date', 'last_forward_date': fwd_nav_d}
            continue

        if anchor_nav_v <= 0 or fwd_nav_v <= 0:
            unavailable[cid] = {**data, 'reason': 'Non-positive NAV'}
            continue

        fwd_return = (fwd_nav_v - anchor_nav_v) / anchor_nav_v

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

    return eligible, unavailable


def calc_pearson(x: np.ndarray, y: np.ndarray) -> float:
    x_m, y_m = np.mean(x), np.mean(y)
    num = np.sum((x - x_m) * (y - y_m))
    den = np.sqrt(np.sum((x - x_m)**2) * np.sum((y - y_m)**2))
    return float(num / den) if den > 0 else 0.0


def calc_spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return calc_pearson(rx.astype(float), ry.astype(float))


def compute_nested_r2(y: np.ndarray, x_tr: np.ndarray, x_risk: np.ndarray, x_fq: np.ndarray) -> Dict[str, float]:
    ss_tot = np.sum((y - np.mean(y))**2)
    def r2(X):
        Xd = np.column_stack([np.ones(len(y)), X])
        b, res, _, _ = np.linalg.lstsq(Xd, y, rcond=None)
        return float(1.0 - (np.sum((y - Xd @ b)**2) / ss_tot))

    r1 = r2(x_tr)
    r2_m2 = r2(np.column_stack([x_tr, x_risk]))
    r3 = r2(np.column_stack([x_tr, x_risk, x_fq]))
    return {'r2_m1': r1, 'r2_m2': r2_m2, 'r2_m3': r3, 'fq_increment': r3 - r2_m2}


def run_full_validation_on_cohort(
    cids: set,
    scheme_navs: Dict[str, List[Tuple[date, float]]],
    scheme_dates: Dict[str, List[date]],
    name: str
) -> Dict[str, Any]:
    """Runs complete OOS validation pipeline on a specific cohort."""
    cohort = compute_cohort_metrics(cids, scheme_navs, scheme_dates)
    scores = compute_fund_quality_scores(cohort)
    for c in cohort: cohort[c]['fund_quality_score'] = scores.get(c)

    eligible, unavailable = compute_forward_outcomes(cohort, scheme_navs, scheme_dates)

    valid_records = [
        v for v in eligible.values()
        if v['fund_quality_score'] is not None
        and v['trailing_1y'] is not None
        and v['volatility'] is not None
        and v['fwd_return'] is not None
        and v['fwd_mdd'] is not None
        and v['fwd_volatility'] is not None
    ]

    fq = np.array([r['fund_quality_score'] for r in valid_records])
    tr = np.array([r['trailing_1y'] for r in valid_records])
    vol = np.array([r['volatility'] for r in valid_records])
    down = np.array([r['downside_deviation'] for r in valid_records])
    mdd = np.array([r['max_drawdown'] for r in valid_records])

    fwd_ret = np.array([r['fwd_return'] for r in valid_records])
    fwd_mdd = np.array([r['fwd_mdd'] for r in valid_records])
    fwd_vol = np.array([r['fwd_volatility'] for r in valid_records])

    s_fq_ret = calc_spearman(fq, fwd_ret)
    s_tr_ret = calc_spearman(tr, fwd_ret)
    p_fq_ret = calc_pearson(fq, fwd_ret)
    p_tr_ret = calc_pearson(tr, fwd_ret)

    risk_matrix = np.column_stack([vol, down, mdd])
    reg_ret = compute_nested_r2(fwd_ret, tr, risk_matrix, fq)

    # Quintiles
    fq_sort = np.argsort(-fq)
    nq = len(fq) // 5
    q1_ret = np.mean(fwd_ret[fq_sort[:nq]])
    q5_ret = np.mean(fwd_ret[fq_sort[-nq:]])
    fq_spread = q1_ret - q5_ret

    tr_sort = np.argsort(-tr)
    tr_q1_ret = np.mean(fwd_ret[tr_sort[:nq]])
    tr_q5_ret = np.mean(fwd_ret[tr_sort[-nq:]])
    tr_spread = tr_q1_ret - tr_q5_ret

    # Strategies
    ntop = len(fq) // 10
    strat_a_recs = sorted(valid_records, key=lambda x: x['trailing_1y'], reverse=True)[:ntop]
    strat_b_recs = sorted(valid_records, key=lambda x: x['volatility'])[:ntop]
    strat_c_recs = sorted(valid_records, key=lambda x: x['fund_quality_score'], reverse=True)[:ntop]

    return {
        'name': name,
        'anchor_n': len(cohort),
        'eligible_n': len(eligible),
        'unavailable_n': len(unavailable),
        'valid_scored_n': len(valid_records),
        'spearman_fq_ret': round(float(s_fq_ret), 4),
        'spearman_tr_ret': round(float(s_tr_ret), 4),
        'pearson_fq_ret': round(float(p_fq_ret), 4),
        'pearson_tr_ret': round(float(p_tr_ret), 4),
        'inc_r2_ret': round(float(reg_ret['fq_increment']), 6),
        'q1_q5_fq_spread': round(float(fq_spread), 4),
        'q1_q5_tr_spread': round(float(tr_spread), 4),
        'strat_a_ret': round(float(np.mean([r['fwd_return'] for r in strat_a_recs])), 4),
        'strat_a_mdd': round(float(np.mean([r['fwd_mdd'] for r in strat_a_recs])), 4),
        'strat_b_ret': round(float(np.mean([r['fwd_return'] for r in strat_b_recs])), 4),
        'strat_b_mdd': round(float(np.mean([r['fwd_mdd'] for r in strat_b_recs])), 4),
        'strat_c_ret': round(float(np.mean([r['fwd_return'] for r in strat_c_recs])), 4),
        'strat_c_mdd': round(float(np.mean([r['fwd_mdd'] for r in strat_c_recs])), 4),
    }


def run_forensic_reconciliation():
    db_path = 'db/backfill_f12_2.db'
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found!")
        sys.exit(1)

    scheme_navs, scheme_dates = load_nav_data(db_path)

    set_5874 = get_f12_3_1_2_cohort_5874(db_path)

    # 5,832 cohort filter
    set_5832 = set()
    for cid in set_5874:
        d_list = scheme_dates[cid]
        idx_T = bisect.bisect_right(d_list, date(2024, 1, 31))
        if idx_T >= 20:
            set_5832.add(cid)

    print("\n[2/7] Running validation on Governed 5,874 Anchor Cohort...", flush=True)
    res_5874 = run_full_validation_on_cohort(set_5874, scheme_navs, scheme_dates, "Governed 5,874 Cohort")

    print("\n[3/7] Running validation on F.11.3.5.3 5,832 Anchor Cohort...", flush=True)
    res_5832 = run_full_validation_on_cohort(set_5832, scheme_navs, scheme_dates, "F.11.3.5.3 5,832 Cohort")

    diff_cids = sorted(list(set_5874 - set_5832))

    reconciliation_results = {
        'governed_5874_results': res_5874,
        'f11_3_5_3_5832_results': res_5832,
        'cohort_diff_count': len(diff_cids),
        'sample_42_diff': diff_cids[:10]
    }

    out_json = 'docs/phase_f11_3_5_3_1_results.json'
    with open(out_json, 'w') as f:
        json.dump(reconciliation_results, f, indent=2)

    print("\n======================================================================")
    print("PHASE F.11.3.5.3.1 SIDE-BY-SIDE FORENSIC RECONCILIATION")
    print("======================================================================")
    print(f"Metric                          | Governed (5,874) | F.11.3.5.3 (5,832) | Diff")
    print("----------------------------------------------------------------------")
    print(f"Anchor Cohort N                 | {res_5874['anchor_n']:>16} | {res_5832['anchor_n']:>18} | {res_5874['anchor_n'] - res_5832['anchor_n']}")
    print(f"Outcome-Eligible N              | {res_5874['eligible_n']:>16} | {res_5832['eligible_n']:>18} | {res_5874['eligible_n'] - res_5832['eligible_n']}")
    print(f"Outcome-Unavailable N           | {res_5874['unavailable_n']:>16} | {res_5832['unavailable_n']:>18} | {res_5874['unavailable_n'] - res_5832['unavailable_n']}")
    print(f"Valid Scored N                  | {res_5874['valid_scored_n']:>16} | {res_5832['valid_scored_n']:>18} | {res_5874['valid_scored_n'] - res_5832['valid_scored_n']}")
    print(f"Fund Quality Spearman (rho)     | {res_5874['spearman_fq_ret']:>16.4f} | {res_5832['spearman_fq_ret']:>18.4f} | {res_5874['spearman_fq_ret'] - res_5832['spearman_fq_ret']:.4f}")
    print(f"Trailing 1Y Spearman (rho)      | {res_5874['spearman_tr_ret']:>16.4f} | {res_5832['spearman_tr_ret']:>18.4f} | {res_5874['spearman_tr_ret'] - res_5832['spearman_tr_ret']:.4f}")
    print(f"Incremental R2 (FQ over Risk)   | {res_5874['inc_r2_ret']:>16.6f} | {res_5832['inc_r2_ret']:>18.6f} | {res_5874['inc_r2_ret'] - res_5832['inc_r2_ret']:.6f}")
    print(f"Q1-Q5 FQ Return Spread          | {res_5874['q1_q5_fq_spread']*100:>15.2f}% | {res_5832['q1_q5_fq_spread']*100:>17.2f}% | {(res_5874['q1_q5_fq_spread'] - res_5832['q1_q5_fq_spread'])*100:.2f}%")
    print(f"Strategy C (FQ) Return          | {res_5874['strat_c_ret']*100:>15.2f}% | {res_5832['strat_c_ret']*100:>17.2f}% | {(res_5874['strat_c_ret'] - res_5832['strat_c_ret'])*100:.2f}%")
    print(f"Strategy C (FQ) MDD             | {res_5874['strat_c_mdd']*100:>15.2f}% | {res_5832['strat_c_mdd']*100:>17.2f}% | {(res_5874['strat_c_mdd'] - res_5832['strat_c_mdd'])*100:.2f}%")
    print("======================================================================")
    print(f"Saved JSON results to {out_json}")

    return reconciliation_results


if __name__ == '__main__':
    run_forensic_reconciliation()
