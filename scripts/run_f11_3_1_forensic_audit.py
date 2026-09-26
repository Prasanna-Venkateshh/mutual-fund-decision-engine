"""
Phase F.11.3.1 — Empirical Result Forensic & Robustness Audit Script

Independently reproduces and audits all empirical headline findings reported by Phase F.11.3
on the real ~10-year historical NAV dataset (db/backfill_f12_2.db).

Strictly enforces Point-in-Time information barriers, zero-synthetic-data firewall,
and locked financial methodology.
"""

import sys, os, sqlite3, math, bisect
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, '.')

from metrics.returns import calculate_absolute_return, calculate_cagr


def load_in_memory_nav_history(db_path: str = 'db/backfill_f12_2.db') -> Tuple[Dict[str, List[Tuple[date, float]]], Dict[str, List[date]], Dict[str, bool], Dict[str, str]]:
    """Loads all normalized NAV observations into memory as (date_obj, nav_float) tuples and date lists."""
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA journal_mode = WAL")

    print("[1/6] Loading normalized NAV records & canonical scheme metadata...", flush=True)
    cur = conn.cursor()

    # Load canonical scheme category/name mapping if available
    cur.execute("SELECT canonical_scheme_id, scheme_name, category, sub_category FROM canonical_schemes")
    scheme_metadata: Dict[str, str] = {}
    for cid, sname, cat, scat in cur.fetchall():
        cat_label = cat if cat and cat.strip() else (scat if scat and scat.strip() else 'Unclassified')
        scheme_metadata[cid] = cat_label

    cur.execute("SELECT canonical_scheme_id, nav_date, nav_value FROM normalized_nav_records ORDER BY canonical_scheme_id, nav_date ASC")

    scheme_navs: Dict[str, List[Tuple[date, float]]] = {}
    scheme_dates: Dict[str, List[date]] = {}
    survived_2024: Dict[str, bool] = {}

    for cid, d_str, n_val in cur.fetchall():
        d_obj = date.fromisoformat(d_str[:10])
        n_float = float(n_val)
        if cid not in scheme_navs:
            scheme_navs[cid] = []
            scheme_dates[cid] = []
            survived_2024[cid] = False
        scheme_navs[cid].append((d_obj, n_float))
        scheme_dates[cid].append(d_obj)
        if d_obj >= date(2024, 1, 1):
            survived_2024[cid] = True

    conn.close()
    print(f"  Loaded {len(scheme_navs)} canonical schemes.", flush=True)
    return scheme_navs, scheme_dates, survived_2024, scheme_metadata


def compute_metrics_at_date(nav_tuples: List[Tuple[date, float]], eval_date: date) -> Optional[Dict[str, Any]]:
    """Computes PIT metrics for a scheme using only observations with date <= eval_date."""
    # Filter observations <= eval_date
    history = [t for t in nav_tuples if t[0] <= eval_date]
    if len(history) < 20:
        return None

    obs_count = len(history)
    start_date = history[0][0]
    end_date = history[-1][0]
    days_span = (end_date - start_date).days

    start_nav = history[0][1]
    end_nav = history[-1][1]

    if days_span < 365 or start_nav <= 0 or end_nav <= 0:
        cagr = None
    else:
        cagr = (end_nav / start_nav) ** (365.0 / days_span) - 1.0

    # Calculate trailing 1Y return (using last 365 days before eval_date)
    hist_1y = [t for t in history if (eval_date - t[0]).days <= 365]
    if len(hist_1y) >= 2 and hist_1y[0][1] > 0:
        trailing_1y = (hist_1y[-1][1] / hist_1y[0][1]) - 1.0
    else:
        trailing_1y = cagr

    # Daily returns for volatility, downside dev, max drawdown
    daily_rets = []
    for i in range(1, len(history)):
        p0, p1 = history[i-1][1], history[i][1]
        if p0 > 0:
            daily_rets.append((p1 - p0) / p0)

    if not daily_rets:
        return None

    mean_ret = sum(daily_rets) / len(daily_rets)
    var = sum((r - mean_ret) ** 2 for r in daily_rets) / max(1, len(daily_rets) - 1)
    volatility = math.sqrt(var) * math.sqrt(252)

    downside_rets = [min(0.0, r) for r in daily_rets]
    downside_var = sum(r ** 2 for r in downside_rets) / max(1, len(daily_rets))
    downside_dev = math.sqrt(downside_var) * math.sqrt(252)

    peak = history[0][1]
    max_dd = 0.0
    for d, val in history:
        if val > peak:
            peak = val
        elif peak > 0:
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd

    # Confidence calculation
    completeness = min(1.0, obs_count / 252.0)
    history_conf = min(1.0, days_span / 1095.0)
    confidence = round(0.5 * completeness + 0.5 * history_conf, 2)

    return {
        'obs_count': obs_count,
        'days_span': days_span,
        'cagr': cagr,
        'trailing_1y': trailing_1y,
        'volatility': volatility,
        'downside_dev': downside_dev,
        'max_dd': max_dd,
        'confidence': confidence
    }


def fast_batch_scoring(metrics_map: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """Calculates Fund Quality Scores for a pool of dataset inputs."""
    cagrs = [m['cagr'] for m in metrics_map.values() if m['cagr'] is not None]
    vols = [m['volatility'] for m in metrics_map.values() if m['volatility'] is not None]
    downs = [m['downside_dev'] for m in metrics_map.values() if m['downside_dev'] is not None]
    mdds = [m['max_dd'] for m in metrics_map.values() if m['max_dd'] is not None]

    cagrs.sort()
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
    for cid, m in metrics_map.items():
        if m['days_span'] < 365 or m['cagr'] is None:
            scores[cid] = None
            continue
        p_ret = get_pct(cagrs, m['cagr'], True)
        p_vol = get_pct(vols, m['volatility'], False)
        p_down = get_pct(downs, m['downside_dev'], False)
        p_mdd = get_pct(mdds, m['max_dd'], False)

        parts = [p for p in [p_ret, p_vol, p_down, p_mdd] if p is not None]
        if parts:
            scores[cid] = round(sum(parts) / len(parts), 1)
        else:
            scores[cid] = None

    return scores


def compute_forward_return(nav_tuples: List[Tuple[date, float]], eval_date: date, horizon_days: int) -> Optional[float]:
    """Computes forward return strictly using observations > eval_date."""
    fwd_obs = [t for t in nav_tuples if eval_date < t[0] <= eval_date + timedelta(days=horizon_days)]
    if len(fwd_obs) < 2:
        return None
    start_nav = fwd_obs[0][1]
    end_nav = fwd_obs[-1][1]
    if start_nav <= 0 or end_nav <= 0:
        return None

    # Annualize if horizon > 365
    span = (fwd_obs[-1][0] - fwd_obs[0][0]).days
    if span <= 0:
        return None
    total_ret = (end_nav - start_nav) / start_nav

    if horizon_days > 365 and span >= 365:
        return (end_nav / start_nav) ** (365.0 / span) - 1.0
    return total_ret


def spearman_rho(x: List[float], y: List[float]) -> Tuple[float, float]:
    """Calculates Spearman rank correlation coefficient and p-value."""
    n = len(x)
    if n < 2:
        return 0.0, 1.0

    def get_ranks(vals: List[float]) -> List[float]:
        sorted_indices = sorted(range(len(vals)), key=lambda k: vals[k])
        ranks = [0.0] * len(vals)
        i = 0
        while i < len(vals):
            j = i
            while j < len(vals) and vals[sorted_indices[j]] == vals[sorted_indices[i]]:
                j += 1
            avg_rank = (i + j + 1) / 2.0
            for k in range(i, j):
                ranks[sorted_indices[k]] = avg_rank
            i = j
        return ranks

    rx = get_ranks(x)
    ry = get_ranks(y)

    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n

    num = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    den_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    den_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))

    if den_x * den_y == 0:
        return 0.0, 1.0

    rho = num / (den_x * den_y)

    # Approximate t-statistic for p-value
    if abs(rho) >= 1.0:
        p_val = 0.0
    else:
        t_stat = rho * math.sqrt((n - 2) / (1 - rho ** 2))
        # Simple normal approximation for large N
        p_val = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t_stat) / math.sqrt(2))))

    return rho, p_val


def ols_regression(y: List[float], x1: List[float], x2: List[float]) -> Dict[str, Any]:
    """Fits Y = b0 + b1*X1 + b2*X2 via OLS."""
    n = len(y)
    if n < 5:
        return {}

    # Mean center
    my = sum(y) / n
    mx1 = sum(x1) / n
    mx2 = sum(x2) / n

    y_c = [val - my for val in y]
    x1_c = [val - mx1 for val in x1]
    x2_c = [val - mx2 for val in x2]

    # Matrix (X^T X)^(-1) X^T Y
    s11 = sum(x ** 2 for x in x1_c)
    s22 = sum(x ** 2 for x in x2_c)
    s12 = sum(x1_c[i] * x2_c[i] for i in range(n))
    sy1 = sum(x1_c[i] * y_c[i] for i in range(n))
    sy2 = sum(x2_c[i] * y_c[i] for i in range(n))

    det = s11 * s22 - s12 ** 2
    if abs(det) < 1e-12:
        return {}

    b1 = (s22 * sy1 - s12 * sy2) / det
    b2 = (s11 * sy2 - s12 * sy1) / det
    b0 = my - b1 * mx1 - b2 * mx2

    # Residual variance
    y_pred = [b0 + b1 * x1[i] + b2 * x2[i] for i in range(n)]
    sse = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
    df = max(1, n - 3)
    mse = sse / df

    var_b1 = mse * s22 / det
    var_b2 = mse * s11 / det

    se_b1 = math.sqrt(max(0, var_b1))
    se_b2 = math.sqrt(max(0, var_b2))

    t_b1 = b1 / se_b1 if se_b1 > 0 else 0
    t_b2 = b2 / se_b2 if se_b2 > 0 else 0

    return {
        'b0': b0, 'b1': b1, 'b2': b2,
        'se_b1': se_b1, 'se_b2': se_b2,
        't_b1': t_b1, 't_b2': t_b2,
        'r2': 1.0 - (sse / sum(y_val ** 2 for y_val in y_c)) if sum(y_val ** 2 for y_val in y_c) > 0 else 0
    }


def main():
    print("=" * 80)
    print("PHASE F.11.3.1 — EMPIRICAL RESULT FORENSIC & ROBUSTNESS AUDIT")
    print("=" * 80)

    # Step 1: Database Inventory Verification
    scheme_navs, scheme_dates, survived_2024, scheme_metadata = load_in_memory_nav_history()

    eval_dates = [
        date(2016, 1, 31),
        date(2018, 1, 31),
        date(2020, 1, 31),
        date(2021, 1, 31),
        date(2022, 1, 31),
        date(2023, 1, 31)
    ]

    print("\n[2/6] Reconstructing Point-in-Time Evaluations across 6 Dates...")
    all_evals = []

    for ed in eval_dates:
        metrics_map = {}
        for cid, nav_tuples in scheme_navs.items():
            m = compute_metrics_at_date(nav_tuples, ed)
            if m is not None:
                metrics_map[cid] = m

        scores_map = fast_batch_scoring(metrics_map)

        for cid, m in metrics_map.items():
            sc = scores_map.get(cid)
            if sc is None:
                continue

            fwd_1y = compute_forward_return(scheme_navs[cid], ed, 365)
            fwd_3y = compute_forward_return(scheme_navs[cid], ed, 1095)
            fwd_5y = compute_forward_return(scheme_navs[cid], ed, 1825)

            cat_label = scheme_metadata.get(cid, 'Unclassified')

            all_evals.append({
                'eval_date': ed,
                'canonical_scheme_id': cid,
                'category': cat_label,
                'survived_2024': survived_2024[cid],
                'score': sc,
                'trailing_1y': m['trailing_1y'],
                'cagr': m['cagr'],
                'volatility': m['volatility'],
                'downside_dev': m['downside_dev'],
                'confidence': m['confidence'],
                'fwd_1y': fwd_1y,
                'fwd_3y': fwd_3y,
                'fwd_5y': fwd_5y
            })

    print(f"  Total fund-date evaluation points reconstructed: {len(all_evals)}")

    # Step 3: Headline Correlation Reproduction & Uncertainty Assessment
    print("\n[3/6] Headline Correlation Reproduction & Dependence Audit...")

    def get_pairs(fwd_key: str):
        valid = [e for e in all_evals if e[fwd_key] is not None]
        scores = [e['score'] for e in valid]
        fwds = [e[fwd_key] for e in valid]
        return valid, scores, fwds

    v1, s1, f1 = get_pairs('fwd_1y')
    v3, s3, f3 = get_pairs('fwd_3y')
    v5, s5, f5 = get_pairs('fwd_5y')

    rho_1y, p_1y = spearman_rho(s1, f1)
    rho_3y, p_3y = spearman_rho(s3, f3)
    rho_5y, p_5y = spearman_rho(s5, f5)

    print(f"  1Y Score vs Forward Return: Rho = {rho_1y:.4f} (N = {len(v1)}, p = {p_1y:.4e})")
    print(f"  3Y Score vs Forward Return: Rho = {rho_3y:.4f} (N = {len(v3)}, p = {p_3y:.4e})")
    print(f"  5Y Score vs Forward Return: Rho = {rho_5y:.4f} (N = {len(v5)}, p = {p_5y:.4e})")

    # Baseline comparison (Naive Trailing 1Y Return vs 1Y Forward Return)
    tr_1y = [e['trailing_1y'] for e in v1]
    rho_tr_1y, p_tr_1y = spearman_rho(tr_1y, f1)
    print(f"  Naive Trailing 1Y Return vs 1Y Forward Return: Rho = {rho_tr_1y:.4f} (N = {len(v1)})")

    # Equal-weighting robustness
    # A. Date-equal-weighted
    date_rhos = []
    for ed in eval_dates:
        sub = [e for e in v1 if e['eval_date'] == ed]
        if len(sub) >= 10:
            r_d, _ = spearman_rho([e['score'] for e in sub], [e['fwd_1y'] for e in sub])
            date_rhos.append(r_d)
    date_eq_rho = sum(date_rhos) / len(date_rhos) if date_rhos else rho_1y
    print(f"  Date-Equal-Weighted 1Y Rho: {date_eq_rho:.4f} (across {len(date_rhos)} dates)")

    # B. Scheme-equal-weighted
    scheme_groups: Dict[str, List[Dict[str, Any]]] = {}
    for e in v1:
        cid = e['canonical_scheme_id']
        if cid not in scheme_groups:
            scheme_groups[cid] = []
        scheme_groups[cid].append(e)

    scheme_avg_scores = [sum(e['score'] for e in group)/len(group) for group in scheme_groups.values()]
    scheme_avg_fwds = [sum(e['fwd_1y'] for e in group)/len(group) for group in scheme_groups.values()]
    scheme_eq_rho, _ = spearman_rho(scheme_avg_scores, scheme_avg_fwds)
    print(f"  Scheme-Equal-Weighted 1Y Rho: {scheme_eq_rho:.4f} (across {len(scheme_groups)} unique schemes)")

    # Step 4: Quantile Analysis (Q1 - Q5) Mean vs Median vs Winsorized
    print("\n[4/6] Quantile Q1-Q5 Construction Audit & Mean vs Median Robustness...")
    v1_sorted = sorted(v1, key=lambda e: e['score'])
    n_total = len(v1_sorted)
    q_size = n_total // 5

    q_data = []
    for q in range(5):
        start_idx = q * q_size
        end_idx = n_total if q == 4 else (q + 1) * q_size
        chunk = v1_sorted[start_idx:end_idx]

        scores = [e['score'] for e in chunk]
        fwds = [e['fwd_1y'] * 100.0 for e in chunk]  # in percentage

        avg_sc = sum(scores) / len(scores)
        mean_fwd = sum(fwds) / len(fwds)

        fwds_sorted = sorted(fwds)
        mid = len(fwds_sorted) // 2
        median_fwd = fwds_sorted[mid] if len(fwds_sorted) % 2 != 0 else (fwds_sorted[mid-1] + fwds_sorted[mid]) / 2.0
        p25 = fwds_sorted[int(len(fwds_sorted) * 0.25)]
        p75 = fwds_sorted[int(len(fwds_sorted) * 0.75)]

        # Winsorized mean (5% trimming)
        trim_cnt = int(len(fwds_sorted) * 0.05)
        trimmed = fwds_sorted[trim_cnt: len(fwds_sorted) - trim_cnt]
        win_mean = sum(trimmed) / len(trimmed) if trimmed else mean_fwd

        var_fwd = sum((f - mean_fwd) ** 2 for f in fwds) / len(fwds)
        std_fwd = math.sqrt(var_fwd)

        q_data.append({
            'q': q + 1,
            'count': len(chunk),
            'avg_score': avg_sc,
            'mean_fwd': mean_fwd,
            'median_fwd': median_fwd,
            'p25': p25,
            'p75': p75,
            'win_mean': win_mean,
            'std_fwd': std_fwd
        })

    print("  Q | Count | Avg Score | Mean 1Y Ret | Median 1Y Ret | P25 | P75 | Winsorized Mean | Std Dev")
    for qd in q_data:
        print(f"  Q{qd['q']} | {qd['count']} | {qd['avg_score']:.2f} | {qd['mean_fwd']:.2f}% | {qd['median_fwd']:.2f}% | {qd['p25']:.2f}% | {qd['p75']:.2f}% | {qd['win_mean']:.2f}% | {qd['std_fwd']:.2f}%")

    # Step 5: Incremental Information & Multivariate Regression Audit
    print("\n[5/6] Incremental Information Audit (Regression: Fwd_1Y ~ Trailing_1Y + Score)...")
    reg_y = [e['fwd_1y'] for e in v1]
    reg_x1 = [e['trailing_1y'] for e in v1]
    reg_x2 = [e['score'] for e in v1]

    reg_res = ols_regression(reg_y, reg_x1, reg_x2)
    print(f"  OLS Intercept (b0): {reg_res.get('b0', 0):.4f}")
    print(f"  b1 (Trailing 1Y Coeff): {reg_res.get('b1', 0):.4f} (t = {reg_res.get('t_b1', 0):.2f})")
    print(f"  b2 (Quality Score Coeff): {reg_res.get('b2', 0):.4f} (t = {reg_res.get('t_b2', 0):.2f})")
    print(f"  R-Squared: {reg_res.get('r2', 0):.4f}")

    # Step 6: Confidence Audit & Dispersion Bounding
    print("\n[6/6] Confidence Construct & Dispersion Audit...")
    low_conf = [e['fwd_1y'] * 100.0 for e in v1 if e['confidence'] < 0.50]
    med_conf = [e['fwd_1y'] * 100.0 for e in v1 if 0.50 <= e['confidence'] < 0.80]
    high_conf = [e['fwd_1y'] * 100.0 for e in v1 if e['confidence'] >= 0.80]

    def get_disp(arr: List[float]) -> float:
        if not arr:
            return 0.0
        m = sum(arr) / len(arr)
        return math.sqrt(sum((x - m) ** 2 for x in arr) / len(arr))

    std_low = get_disp(low_conf)
    std_med = get_disp(med_conf)
    std_high = get_disp(high_conf)

    print(f"  Low Confidence (<0.50): N = {len(low_conf)}, Std Dev = {std_low:.2f}%")
    print(f"  Med Confidence (0.50-0.80): N = {len(med_conf)}, Std Dev = {std_med:.2f}%")
    print(f"  High Confidence (>=0.80): N = {len(high_conf)}, Std Dev = {std_high:.2f}%")

    # Step 7: Temporal & Regime Sensitivity Audit
    print("\n[7/7] Temporal & Regime Sensitivity Audit...")
    for ed in eval_dates:
        sub = [e for e in v1 if e['eval_date'] == ed]
        if sub:
            r_ed, p_ed = spearman_rho([e['score'] for e in sub], [e['fwd_1y'] for e in sub])
            print(f"  Date {ed.isoformat()}: N = {len(sub)}, Rho = {r_ed:.4f} (p = {p_ed:.4e})")

    # Step 8: Survivorship Sensitivity Audit
    surv_v1 = [e for e in v1 if e['survived_2024']]
    rho_surv, _ = spearman_rho([e['score'] for e in surv_v1], [e['fwd_1y'] for e in surv_v1])
    print(f"\n  Survivorship Sensitivity (Surviving-only schemes): N = {len(surv_v1)}, Rho = {rho_surv:.4f} (vs All {len(v1)} Rho = {rho_1y:.4f})")

    # Step 9: Category Breakdown Audit
    print("\n  Category Breakdown (1Y Forward Return Correlation):")
    cat_groups: Dict[str, List[Dict[str, Any]]] = {}
    for e in v1:
        cat = e['category']
        if cat not in cat_groups:
            cat_groups[cat] = []
        cat_groups[cat].append(e)

    for cat, items in sorted(cat_groups.items(), key=lambda t: len(t[1]), reverse=True):
        if len(items) >= 20:
            c_rho, c_p = spearman_rho([e['score'] for e in items], [e['fwd_1y'] for e in items])
            print(f"    Category '{cat}': N = {len(items)}, Rho = {c_rho:.4f}")

    print("\n" + "=" * 80)
    print("PHASE F.11.3.1 FORENSIC REPRODUCTION SUMMARY COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()

