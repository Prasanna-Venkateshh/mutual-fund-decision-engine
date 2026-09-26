"""
Debug script to perform detailed mathematical reconciliation of P3 and P4 correlations
"""

import sqlite3
import math
import bisect
from datetime import date, timedelta
import numpy as np

def rankdata(a: np.ndarray) -> np.ndarray:
    sorter = np.argsort(a)
    ranks = np.empty_like(sorter, dtype=float)
    ranks[sorter] = np.arange(len(a), dtype=float)
    return ranks

def calculate_spearman_rho(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    rx = rankdata(x)
    ry = rankdata(y)
    mean_rx = np.mean(rx)
    mean_ry = np.mean(ry)
    num = np.sum((rx - mean_rx) * (ry - mean_ry))
    den = math.sqrt(np.sum((rx - mean_rx)**2) * np.sum((ry - mean_ry)**2))
    return float(num / den) if den > 0 else 0.0

def debug_p3_p4():
    db_path = 'db/backfill_f12_2.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT canonical_scheme_id, nav_date, nav_value FROM normalized_nav_records ORDER BY canonical_scheme_id, nav_date ASC")

    scheme_navs = {}
    scheme_dates = {}

    for cid, d_str, n_val in cur.fetchall():
        d_obj = date.fromisoformat(d_str[:10])
        n_float = float(n_val)
        if cid not in scheme_navs:
            scheme_navs[cid] = []
            scheme_dates[cid] = []
        scheme_navs[cid].append((d_obj, n_float))
        scheme_dates[cid].append(d_obj)

    conn.close()

    eval_periods = [
        {"period_id": "P3_2022", "anchor_date": "2022-01-31", "fwd_end_date": "2023-01-31"},
        {"period_id": "P4_2023", "anchor_date": "2023-01-31", "fwd_end_date": "2024-01-31"}
    ]

    for p in eval_periods:
        anchor_d = date.fromisoformat(p["anchor_date"])
        fwd_end_d = date.fromisoformat(p["fwd_end_date"])

        eligible = {}
        for cid, full_nav in scheme_navs.items():
            d_list = scheme_dates[cid]
            idx_T = bisect.bisect_right(d_list, anchor_d)
            if idx_T == 0: continue

            pit = full_nav[:idx_T]
            start_d, start_nav = pit[0]
            end_d, end_nav = pit[-1]
            obs_count = len(pit)

            if (anchor_d - end_d).days > 30 or obs_count < 20: continue

            idx_1y = bisect.bisect_left(d_list, anchor_d - timedelta(days=365))
            if idx_1y < idx_T and full_nav[idx_1y][1] > 0:
                tr_1y = (end_nav - full_nav[idx_1y][1]) / full_nav[idx_1y][1]
            else:
                tr_1y = (end_nav - start_nav) / start_nav if start_nav > 0 else 0.0

            sample_pit = pit[-250:] if len(pit) > 250 else pit
            rets = [(sample_pit[i][1] - sample_pit[i-1][1])/sample_pit[i-1][1] for i in range(1, len(sample_pit)) if sample_pit[i-1][1] > 0]

            vol_val, downside_mar0 = 0.0, 0.0
            if rets:
                m_ret = sum(rets)/len(rets)
                var_ret = sum((r - m_ret)**2 for r in rets) / max(1, len(rets)-1)
                vol_val = math.sqrt(var_ret) * math.sqrt(252)
                down_diffs = [min(0.0, r)**2 for r in rets]
                downside_mar0 = math.sqrt(sum(down_diffs)/len(rets)) * math.sqrt(252)

            vol_comp = 1.0 / (1.0 + vol_val)
            tr_comp = min(1.0, max(0.0, tr_1y))
            fq_score = 0.5 * vol_comp + 0.5 * tr_comp
            fq_confidence = min(1.0, obs_count / 250.0)

            idx_fwd = bisect.bisect_right(d_list, fwd_end_d)
            fwd_navs = full_nav[idx_T-1:idx_fwd]
            if len(fwd_navs) < 2 or (fwd_end_d - fwd_navs[-1][0]).days > 20: continue

            fwd_ret = (fwd_navs[-1][1] - fwd_navs[0][1]) / fwd_navs[0][1]
            pk = fwd_navs[0][1]
            dds = []
            for _, v in fwd_navs:
                if v > pk: pk = v
                dds.append((pk - v) / pk if pk > 0 else 0.0)
            fwd_mdd = max(dds) if dds else 0.0

            eligible[cid] = {
                'cid': cid,
                'tr_1y': tr_1y,
                'vol': vol_val,
                'downside_mar0': downside_mar0,
                'vol_comp': vol_comp,
                'tr_comp': tr_comp,
                'fq_score': fq_score,
                'fwd_ret': fwd_ret,
                'fwd_mdd': fwd_mdd
            }

        cids = sorted(list(eligible.keys()))
        N = len(cids)
        tr_arr = np.array([eligible[c]['tr_1y'] for c in cids])
        vol_arr = np.array([eligible[c]['vol'] for c in cids])
        vol_comp_arr = np.array([eligible[c]['vol_comp'] for c in cids])
        tr_comp_arr = np.array([eligible[c]['tr_comp'] for c in cids])
        fq_arr = np.array([eligible[c]['fq_score'] for c in cids])
        fwd_ret_arr = np.array([eligible[c]['fwd_ret'] for c in cids])
        fwd_mdd_arr = np.array([eligible[c]['fwd_mdd'] for c in cids])

        print(f"=== PERIOD {p['period_id']} (N={N}) ===")
        print("FQ vs Fwd Ret:", calculate_spearman_rho(fq_arr, fwd_ret_arr))
        print("TR vs Fwd Ret:", calculate_spearman_rho(tr_arr, fwd_ret_arr))
        print("Vol vs Fwd Ret:", calculate_spearman_rho(vol_arr, fwd_ret_arr))
        print("Vol Comp (recip vol) vs Fwd Ret:", calculate_spearman_rho(vol_comp_arr, fwd_ret_arr))
        print("TR Comp vs Fwd Ret:", calculate_spearman_rho(tr_comp_arr, fwd_ret_arr))
        print("FQ vs Fwd MDD:", calculate_spearman_rho(fq_arr, fwd_mdd_arr))
        print("Raw Volatility vs Fwd Ret:", calculate_spearman_rho(vol_arr, fwd_ret_arr))
        print("-1 * FQ vs Fwd Ret:", calculate_spearman_rho(-fq_arr, fwd_ret_arr))
        print("---------------------------------------------------\n")

if __name__ == '__main__':
    debug_p3_p4()
