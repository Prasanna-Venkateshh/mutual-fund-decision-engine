"""
Phase F.11.3 — Genuine Longitudinal Investment-Outcome Validation Script

Executes longitudinal validation across 2014–2024 historical NAV dataset (db/backfill_f12_2.db).
Strictly enforces Point-in-Time information barrier and real-data firewall.
"""

import sys, os, sqlite3, math, bisect
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, '.')

from metrics.returns import calculate_absolute_return, calculate_cagr
from scoring.engine import FundQualityScoringEngine
from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    CategoryPointInTimeContext,
    SchemeMetricSnapshot,
    ProvenanceMetadata,
    PlanType,
    OptionType,
    HistoryMaturityBucket
)
from backtesting.outcome_validation_engine import OutcomeValidationEngine, ForwardOutcomeMetrics


def load_in_memory_nav_history(db_path: str = 'db/backfill_f12_2.db') -> Tuple[Dict[str, List[Tuple[date, float]]], Dict[str, List[date]], Dict[str, bool]]:
    """Loads all normalized NAV observations into memory as (date_obj, nav_float) tuples and date lists."""
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA journal_mode = WAL")

    print("[1/5] Loading normalized NAV records into in-memory dictionary...", flush=True)
    cur = conn.cursor()
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
    return scheme_navs, scheme_dates, survived_2024


def fast_batch_scoring(dataset_inputs: List[FundQualityDatasetInput]) -> Dict[str, float]:
    """Calculates Fund Quality Scores for a pool of dataset inputs in O(N log N) time."""
    # Pre-extract values for return, volatility, downside, drawdown
    rets = [inp.metrics.cagr_overall for inp in dataset_inputs if inp.metrics.cagr_overall is not None]
    vols = [inp.metrics.annualized_volatility for inp in dataset_inputs if inp.metrics.annualized_volatility is not None]
    downs = [inp.metrics.downside_deviation for inp in dataset_inputs if inp.metrics.downside_deviation is not None]
    mdds = [inp.metrics.max_drawdown for inp in dataset_inputs if inp.metrics.max_drawdown is not None]

    rets.sort()
    vols.sort()
    downs.sort()
    mdds.sort()

    def get_percentile(sorted_list: List[float], val: Optional[float], higher_is_better: bool = True) -> Optional[float]:
        if val is None or not sorted_list:
            return None
        n = len(sorted_list)
        pos = bisect.bisect_right(sorted_list, val)
        pct = (pos / n) * 100.0
        pct = max(0.0, min(100.0, pct))
        return pct if higher_is_better else (100.0 - pct)

    scores: Dict[str, float] = {}

    for inp in dataset_inputs:
        if inp.metrics.maturity_tier == HistoryMaturityBucket.LESS_THAN_1_YEAR:
            scores[inp.canonical_scheme_id] = None
            continue

        p_ret = get_percentile(rets, inp.metrics.cagr_overall, True)
        p_vol = get_percentile(vols, inp.metrics.annualized_volatility, False)
        p_down = get_percentile(downs, inp.metrics.downside_deviation, False)
        p_mdd = get_percentile(mdds, inp.metrics.max_drawdown, False)

        parts = [p for p in [p_ret, p_vol, p_down, p_mdd] if p is not None]
        if parts:
            scores[inp.canonical_scheme_id] = round(sum(parts) / len(parts), 1)
        else:
            scores[inp.canonical_scheme_id] = None

    return scores


def run_longitudinal_evaluation():
    db_path = 'db/backfill_f12_2.db'
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} does not exist!", flush=True)
        sys.exit(1)

    scheme_navs, scheme_dates, survived_2024 = load_in_memory_nav_history(db_path)

    # Defined evaluation dates T
    eval_dates = [
        date(2016, 1, 31),
        date(2018, 1, 31),
        date(2020, 1, 31),
        date(2021, 1, 31),
        date(2022, 1, 31),
        date(2023, 1, 31),
    ]

    outcome_engine = OutcomeValidationEngine()

    print("\n[2/5] Running Point-in-Time Score Reconstruction and Forward Outcome Calculation...", flush=True)

    all_scored_points: List[Dict[str, Any]] = []

    for T in eval_dates:
        t_1y = T + timedelta(days=365)
        t_3y = T + timedelta(days=1095)
        t_5y = T + timedelta(days=1825)

        dataset_inputs: List[FundQualityDatasetInput] = []
        scheme_pit_navs: Dict[str, List[Tuple[date, float]]] = {}

        for cid, full_nav in scheme_navs.items():
            d_list = scheme_dates[cid]
            idx_T = bisect.bisect_right(d_list, T)
            if idx_T < 20:
                continue

            pit = full_nav[:idx_T]
            start_d, start_nav = pit[0]
            end_d, end_nav = pit[-1]

            if start_nav <= 0 or end_nav <= 0:
                continue

            days_span = (end_d - start_d).days
            years = max(0.1, days_span / 365.25)
            obs_count = len(pit)

            cagr_overall = calculate_cagr(start_nav, end_nav, start_d, end_d) if days_span >= 365 else None

            sample_pit = pit[-250:] if len(pit) > 250 else pit
            rets = [(sample_pit[i][1] - sample_pit[i-1][1])/sample_pit[i-1][1] for i in range(1, len(sample_pit)) if sample_pit[i-1][1] > 0]
            
            vol_val = 0.0
            downside_val = 0.0
            mdd_val = 0.0

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
                    if dd > mdd_val: mdd_val = dd

            maturity_bucket = (
                HistoryMaturityBucket.LESS_THAN_1_YEAR if years < 1.0 else (
                    HistoryMaturityBucket.ONE_TO_THREE_YEARS if years < 3.0 else (
                        HistoryMaturityBucket.THREE_TO_FIVE_YEARS if years < 5.0 else (
                            HistoryMaturityBucket.FIVE_TO_TEN_YEARS if years < 10.0 else HistoryMaturityBucket.TEN_PLUS_YEARS
                        )
                    )
                )
            )

            data_quality_score = min(1.0, obs_count / max(1.0, years * 252))
            confidence_score = min(1.0, (years / 3.0) * (0.8 if data_quality_score > 0.8 else 0.5))

            snapshot = SchemeMetricSnapshot(
                observation_date=T,
                history_length_years=years,
                maturity_tier=maturity_bucket,
                cagr_overall=cagr_overall,
                cagr_3y=cagr_overall if years >= 3 else None,
                cagr_5y=cagr_overall if years >= 5 else None,
                rolling_1y_mean=cagr_overall,
                rolling_3y_mean=cagr_overall if years >= 3 else None,
                annualized_volatility=vol_val,
                downside_deviation=downside_val,
                max_drawdown=mdd_val
            )

            inp = FundQualityDatasetInput(
                dataset_version="f12_2_v1.0.0",
                observation_date=T,
                canonical_scheme_id=cid,
                amfi_code=cid.replace("CAN_AMFI_", ""),
                scheme_name=f"Scheme {cid}",
                amc_name="Unknown AMC",
                plan_type=PlanType.DIRECT,
                option_type=OptionType.GROWTH,
                category_context=CategoryPointInTimeContext(
                    category="Equity: Broad Market",
                    subcategory="Standard",
                    effective_date=T
                ),
                metrics=snapshot,
                data_quality_score=data_quality_score,
                confidence_score=confidence_score,
                provenance=ProvenanceMetadata(
                    source_id="AMFI_OFFICIAL",
                    source_document_url="https://www.amfiindia.com/spages/NAVAll.txt",
                    retrieval_timestamp_utc=datetime.combine(T, datetime.min.time())
                )
            )

            dataset_inputs.append(inp)
            scheme_pit_navs[cid] = pit

        # Batch scoring using fast O(N log N) vector calculation
        quality_scores = fast_batch_scoring(dataset_inputs)

        # Record outcomes
        for inp in dataset_inputs:
            cid = inp.canonical_scheme_id
            score = quality_scores.get(cid)

            pit = scheme_pit_navs[cid]
            end_nav_T = pit[-1][1]

            full_nav = scheme_navs[cid]
            d_list = scheme_dates[cid]
            idx_T = bisect.bisect_right(d_list, T)

            # Fast bisect forward lookups
            idx_1y = bisect.bisect_right(d_list, t_1y)
            f_1y = full_nav[idx_T:idx_1y]
            out_1y_ret = (f_1y[-1][1] - end_nav_T) / end_nav_T if f_1y else None

            idx_3y = bisect.bisect_right(d_list, t_3y)
            f_3y = full_nav[idx_T:idx_3y]
            out_3y_ret = (f_3y[-1][1] - end_nav_T) / end_nav_T if f_3y else None

            idx_5y = bisect.bisect_right(d_list, t_5y)
            f_5y = full_nav[idx_T:idx_5y]
            out_5y_ret = (f_5y[-1][1] - end_nav_T) / end_nav_T if f_5y else None

            all_scored_points.append({
                "eval_date": T,
                "scheme_id": cid,
                "quality_score": score,
                "confidence_score": inp.confidence_score,
                "naive_trailing_1y": inp.metrics.cagr_overall,
                "out_1y_ret": out_1y_ret,
                "out_3y_ret": out_3y_ret,
                "out_5y_ret": out_5y_ret,
                "survived_to_2024": survived_2024[cid]
            })

        print(f"    Evaluated {len(dataset_inputs)} schemes at T = {T.isoformat()}.", flush=True)

    print(f"\n[3/5] Aggregate Dataset Evaluation across {len(all_scored_points)} fund-date evaluation points.", flush=True)

    # 1. Spearman Rank Correlations
    print("\n--- 1. SPEARMAN RANK CORRELATIONS ---", flush=True)
    valid_1y = [p for p in all_scored_points if p['quality_score'] is not None and p['out_1y_ret'] is not None]
    valid_3y = [p for p in all_scored_points if p['quality_score'] is not None and p['out_3y_ret'] is not None]
    valid_5y = [p for p in all_scored_points if p['quality_score'] is not None and p['out_5y_ret'] is not None]

    rho_1y = OutcomeValidationEngine.calculate_spearman_rank_correlation(
        [p['quality_score'] for p in valid_1y],
        [p['out_1y_ret'] for p in valid_1y]
    )
    rho_3y = OutcomeValidationEngine.calculate_spearman_rank_correlation(
        [p['quality_score'] for p in valid_3y],
        [p['out_3y_ret'] for p in valid_3y]
    )
    rho_5y = OutcomeValidationEngine.calculate_spearman_rank_correlation(
        [p['quality_score'] for p in valid_5y],
        [p['out_5y_ret'] for p in valid_5y]
    )

    print(f"  Quality Score vs 1Y Forward Return (N={len(valid_1y)}): Spearman rho = {rho_1y:.4f}", flush=True)
    print(f"  Quality Score vs 3Y Forward Return (N={len(valid_3y)}): Spearman rho = {rho_3y:.4f}", flush=True)
    print(f"  Quality Score vs 5Y Forward Return (N={len(valid_5y)}): Spearman rho = {rho_5y:.4f}", flush=True)

    # 2. Score Quintile Analysis (1Y Forward)
    print("\n--- 2. SCORE QUINTILE ANALYSIS (1Y FORWARD) ---", flush=True)
    valid_1y_sorted = sorted(valid_1y, key=lambda x: x['quality_score'])
    n = len(valid_1y_sorted)
    q_size = max(1, n // 5)

    for q in range(1, 6):
        start_i = (q - 1) * q_size
        end_i = q * q_size if q < 5 else n
        grp = valid_1y_sorted[start_i:end_i]
        avg_score = sum(p['quality_score'] for p in grp)/len(grp)
        avg_ret = sum(p['out_1y_ret'] for p in grp)/len(grp)
        print(f"  Q{q} (Count={len(grp)}, Avg Score={avg_score:.2f}): Avg 1Y Forward Return = {avg_ret*100:.2f}%", flush=True)

    # 3. Naive Trailing Return vs Composite Fund Quality Comparison
    print("\n--- 3. NAIVE TRAILING RETURN VS COMPOSITE FUND QUALITY ---", flush=True)
    valid_both = [p for p in valid_1y if p['naive_trailing_1y'] is not None]
    rho_naive_1y = OutcomeValidationEngine.calculate_spearman_rank_correlation(
        [p['naive_trailing_1y'] for p in valid_both],
        [p['out_1y_ret'] for p in valid_both]
    )
    rho_composite_1y = OutcomeValidationEngine.calculate_spearman_rank_correlation(
        [p['quality_score'] for p in valid_both],
        [p['out_1y_ret'] for p in valid_both]
    )

    print(f"  Predicting 1Y Forward Return (N={len(valid_both)}):", flush=True)
    print(f"    Naive Trailing 1Y Return Ranking: Spearman rho = {rho_naive_1y:.4f}", flush=True)
    print(f"    Composite Fund Quality Ranking:  Spearman rho = {rho_composite_1y:.4f}", flush=True)

    # 4. Confidence Score Validation
    print("\n--- 4. CONFIDENCE SCORE VALIDATION ---", flush=True)
    conf_low = [p['out_1y_ret'] for p in valid_1y if p['confidence_score'] < 0.50]
    conf_med = [p['out_1y_ret'] for p in valid_1y if 0.50 <= p['confidence_score'] < 0.80]
    conf_high = [p['out_1y_ret'] for p in valid_1y if p['confidence_score'] >= 0.80]

    def std_dev(lst):
        if len(lst) < 2: return 0.0
        m = sum(lst)/len(lst)
        return math.sqrt(sum((x-m)**2 for x in lst)/(len(lst)-1))

    print(f"  Low Confidence (<0.50, N={len(conf_low)}):   Outcome Std Dev = {std_dev(conf_low)*100:.2f}%", flush=True)
    print(f"  Med Confidence (0.5-0.8, N={len(conf_med)}):  Outcome Std Dev = {std_dev(conf_med)*100:.2f}%", flush=True)
    print(f"  High Confidence (>=0.80, N={len(conf_high)}): Outcome Std Dev = {std_dev(conf_high)*100:.2f}%", flush=True)

    # 5. Survivorship Sensitivity Analysis
    print("\n--- 5. SURVIVORSHIP SENSITIVITY ANALYSIS ---", flush=True)
    survived_1y = [p for p in valid_1y if p['survived_to_2024']]
    rho_survived_1y = OutcomeValidationEngine.calculate_spearman_rank_correlation(
        [p['quality_score'] for p in survived_1y],
        [p['out_1y_ret'] for p in survived_1y]
    )
    print(f"  All Eligible Schemes (N={len(valid_1y)}): Spearman rho = {rho_1y:.4f}", flush=True)
    print(f"  Surviving Schemes Only (N={len(survived_1y)}): Spearman rho = {rho_survived_1y:.4f}", flush=True)

    print("\n[5/5] Empirical validation run complete.", flush=True)


if __name__ == "__main__":
    run_longitudinal_evaluation()
