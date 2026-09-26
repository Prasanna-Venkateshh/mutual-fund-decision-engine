"""
Phase F.14 - Fund Quality Metric Interaction, Redundancy & Information-Content Audit
Script: scripts/run_f14_metric_interaction_audit.py

Executes a comprehensive, reproducible methodology and evidence audit across candidate
Fund Quality metrics using real historical Point-In-Time (PIT) NAV data.

Governed Rules:
- DO NOT modify production Fund Quality Score v1.0 (50% Vol 1Y Reciprocal + 50% Trailing 1Y Return).
- DO NOT change production weights or add candidate factors to production.
- Strictly enforce daily MAR = 0%.
- Category-aware, time-aware analysis across Equity, Debt, and Hybrid categories.
- Produce structured JSON artifacts: docs/phase_f14_metric_inventory.json & docs/phase_f14_pairwise_relationships.json.
"""

import os
import json
import sqlite3
import numpy as np
import pandas as pd
from typing import Dict, List, Any

def pearsonr(x, y):
    x = np.asarray(x)
    y = np.asarray(y)
    mx, my = np.mean(x), np.mean(y)
    xm, ym = x - mx, y - my
    r_num = np.sum(xm * ym)
    r_den = np.sqrt(np.sum(xm ** 2) * np.sum(ym ** 2))
    r = r_num / r_den if r_den != 0 else 0.0
    return r, 0.0

def spearmanr(x, y):
    x = np.asarray(x)
    y = np.asarray(y)
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    return pearsonr(rx, ry)


DB_PATH = "db/backfill_f12_2.db"
OUTPUT_DIR = "docs"

# 1. CANONICAL METRIC INVENTORY
METRIC_INVENTORY = [
    {
        "metric_id": "FQ_F01",
        "name": "Trailing 1Y Gross Return",
        "financial_definition": "Measures total percentage capital growth of a fund over a 1-year (252 trading days) historical window without adjusting for risk or cost.",
        "mathematical_formula": "R_1Y = (NAV_t / NAV_{t-252}) - 1",
        "input_fields": ["normalized_nav", "nav_date"],
        "input_frequency": "Daily",
        "observation_window": "1 Year (252 trading days)",
        "annualization": "None (Direct 1Y compounding)",
        "mar_assumption": "N/A",
        "unit": "Percentage (%)",
        "directionality": "Higher is Better",
        "category_applicability": "All Categories (Equity, Debt, Hybrid, Other)",
        "minimum_history_requirement": "252 trading days (~1 year)",
        "source": "db/backfill_f12_2.db (normalized_nav_records)",
        "pit_requirement": "Strict PIT cutoff at Anchor Date t",
        "current_implementation_status": "Fully Implemented",
        "validation_status": "Validated (F.11.3.5 / F.11.3.5.5)",
        "production_status": "PRODUCTION (50% weight in Fund Quality Score v1.0)",
        "question_answered": "How much has the fund grown over the selected 1-year historical period?"
    },
    {
        "metric_id": "FQ_F02",
        "name": "Annualized Volatility 1Y",
        "financial_definition": "Measures total return variability (dispersion of daily logarithmic returns around their mean) over 1 year.",
        "mathematical_formula": "Sigma_1Y = std(ln(NAV_t / NAV_{t-1})) * sqrt(252)",
        "input_fields": ["normalized_nav", "nav_date"],
        "input_frequency": "Daily",
        "observation_window": "1 Year (252 trading days)",
        "annualization": "Annualized using sqrt(252)",
        "mar_assumption": "N/A",
        "unit": "Percentage (%)",
        "directionality": "Lower is Better (Score uses Reciprocal)",
        "category_applicability": "All Categories",
        "minimum_history_requirement": "252 trading days (~1 year)",
        "source": "db/backfill_f12_2.db (normalized_nav_records)",
        "pit_requirement": "Strict PIT cutoff at Anchor Date t",
        "current_implementation_status": "Fully Implemented",
        "validation_status": "Validated (F.11.3.5 / F.11.3.5.5)",
        "production_status": "PRODUCTION (50% weight in Fund Quality Score v1.0)",
        "question_answered": "How much have the fund's returns moved around their average over the past year?"
    },
    {
        "metric_id": "FQ_F03",
        "name": "Downside Deviation (MAR=0%)",
        "financial_definition": "Measures variability of daily returns specifically on the downside below the governed Minimum Acceptable Return of MAR=0%.",
        "mathematical_formula": "DD_0 = sqrt( (1/N) * sum( min(0, r_t - 0)^2 ) ) * sqrt(252)",
        "input_fields": ["normalized_nav", "nav_date"],
        "input_frequency": "Daily",
        "observation_window": "1 Year (252 trading days)",
        "annualization": "Annualized using sqrt(252)",
        "mar_assumption": "MAR = 0.0% Daily",
        "unit": "Percentage (%)",
        "directionality": "Lower is Better",
        "category_applicability": "All Categories",
        "minimum_history_requirement": "252 trading days (~1 year)",
        "source": "db/backfill_f12_2.db (normalized_nav_records)",
        "pit_requirement": "Strict PIT cutoff at Anchor Date t",
        "current_implementation_status": "Fully Implemented (Metric Engine)",
        "validation_status": "Validated in F.13 Factor Registry",
        "production_status": "RESEARCH-ONLY (Not in Production Score)",
        "question_answered": "How much variability occurred specifically on the downside relative to a zero-loss threshold?"
    },
    {
        "metric_id": "FQ_F04",
        "name": "Maximum Drawdown 1Y",
        "financial_definition": "Measures the largest single peak-to-trough percentage decline observed over the 1-year historical window.",
        "mathematical_formula": "MDD_1Y = max_{t} ( (Peak_t - NAV_t) / Peak_t ) where Peak_t = max_{s <= t} (NAV_s)",
        "input_fields": ["normalized_nav", "nav_date"],
        "input_frequency": "Daily",
        "observation_window": "1 Year (252 trading days)",
        "annualization": "None",
        "mar_assumption": "N/A",
        "unit": "Percentage (%)",
        "directionality": "Lower Peak-to-Trough Decline is Better",
        "category_applicability": "All Categories",
        "minimum_history_requirement": "252 trading days (~1 year)",
        "source": "db/backfill_f12_2.db (normalized_nav_records)",
        "pit_requirement": "Strict PIT cutoff at Anchor Date t",
        "current_implementation_status": "Fully Implemented (Metric Engine)",
        "validation_status": "Validated in F.13 Factor Registry",
        "production_status": "RESEARCH-ONLY (Not in Production Score)",
        "question_answered": "How large was the worst peak-to-trough loss during the measurement period?"
    },
    {
        "metric_id": "FQ_F05",
        "name": "Fund Age / Track Record Depth",
        "financial_definition": "Measures total historical longevity / depth of available daily NAV observations for a fund scheme.",
        "mathematical_formula": "Age_years = (Anchor_Date - Inception_Date) / 365.25",
        "input_fields": ["first_nav_date", "anchor_date"],
        "input_frequency": "Static / Daily Update",
        "observation_window": "Full Inception History",
        "annualization": "Years",
        "mar_assumption": "N/A",
        "unit": "Years",
        "directionality": "Higher is Better (More Evidence Depth)",
        "category_applicability": "All Categories",
        "minimum_history_requirement": "None (Continuous Variable)",
        "source": "db/backfill_f12_2.db (canonical_schemes / normalized_nav_records)",
        "pit_requirement": "Strict PIT cutoff (Inception to Anchor Date)",
        "current_implementation_status": "Fully Implemented (Engine Metadata)",
        "validation_status": "Governed in F.13 (Maturity / Evidence Layer)",
        "production_status": "RESEARCH-ONLY / GOVERNANCE (Used for Eligibility Gate, not Scoring Weight)",
        "question_answered": "How much historical track record exists to evaluate this fund?"
    },
    {
        "metric_id": "FQ_F08",
        "name": "Sharpe Ratio 1Y",
        "financial_definition": "Measures return generated per unit of total risk (volatility) over 1 year, assuming zero risk-free rate per governed benchmark baseline.",
        "mathematical_formula": "Sharpe_1Y = Annualized_Return_1Y / Annualized_Volatility_1Y",
        "input_fields": ["normalized_nav", "nav_date"],
        "input_frequency": "Daily",
        "observation_window": "1 Year (252 trading days)",
        "annualization": "Annualized Return / Annualized Volatility",
        "mar_assumption": "Rf = 0.0%",
        "unit": "Ratio (Dimensionless)",
        "directionality": "Higher is Better",
        "category_applicability": "All Categories",
        "minimum_history_requirement": "252 trading days (~1 year)",
        "source": "db/backfill_f12_2.db (normalized_nav_records)",
        "pit_requirement": "Strict PIT cutoff at Anchor Date t",
        "current_implementation_status": "Fully Implemented (Metric Engine)",
        "validation_status": "Governed in F.13 Factor Registry",
        "production_status": "RESEARCH-ONLY (Not in Production Score)",
        "question_answered": "How much return was generated relative to total return variability?"
    },
    {
        "metric_id": "FQ_F09",
        "name": "Sortino Ratio 1Y (MAR=0%)",
        "financial_definition": "Measures return generated per unit of downside risk (downside deviation below MAR=0%) over 1 year.",
        "mathematical_formula": "Sortino_1Y = Annualized_Return_1Y / Downside_Deviation_0%",
        "input_fields": ["normalized_nav", "nav_date"],
        "input_frequency": "Daily",
        "observation_window": "1 Year (252 trading days)",
        "annualization": "Annualized Return / Downside Deviation",
        "mar_assumption": "MAR = 0.0% Daily",
        "unit": "Ratio (Dimensionless)",
        "directionality": "Higher is Better",
        "category_applicability": "All Categories",
        "minimum_history_requirement": "252 trading days (~1 year)",
        "source": "db/backfill_f12_2.db (normalized_nav_records)",
        "pit_requirement": "Strict PIT cutoff at Anchor Date t",
        "current_implementation_status": "Fully Implemented (Metric Engine)",
        "validation_status": "Governed in F.13 Factor Registry",
        "production_status": "RESEARCH-ONLY (Not in Production Score)",
        "question_answered": "How much return was generated relative to downside variability below MAR=0%?"
    },
    {
        "metric_id": "FQ_F13",
        "name": "Rolling Return Consistency 1Y (1M Windows)",
        "financial_definition": "Measures the percentage of 1-month rolling windows over a 1-year historical period that yielded positive returns.",
        "mathematical_formula": "Consistency_1Y = Count(Rolling_1M_Return > 0) / Total_1M_Rolling_Windows",
        "input_fields": ["normalized_nav", "nav_date"],
        "input_frequency": "Daily NAV (21-day rolling windows)",
        "observation_window": "1 Year (252 trading days)",
        "annualization": "N/A",
        "mar_assumption": "MAR = 0.0% per rolling period",
        "unit": "Percentage (%)",
        "directionality": "Higher is Better",
        "category_applicability": "All Categories",
        "minimum_history_requirement": "252 trading days (~1 year)",
        "source": "db/backfill_f12_2.db (normalized_nav_records)",
        "pit_requirement": "Strict PIT cutoff at Anchor Date t",
        "current_implementation_status": "Fully Implemented (Metric Engine)",
        "validation_status": "Governed in F.13 Factor Registry",
        "production_status": "RESEARCH-ONLY (Not in Production Score)",
        "question_answered": "How consistently did the fund produce positive returns across repeated 1-month rolling windows?"
    }
]

# 2. MATHEMATICAL DEPENDENCY & CIRCULARITY AUDIT MAP
DEPENDENCY_MAP = {
    "FQ_F01": {
        "dependencies": ["NAV Path"],
        "classification": "NO_DIRECT_DEPENDENCY",
        "explanation": "Primary primitive computed directly from endpoints NAV_t / NAV_{t-252}."
    },
    "FQ_F02": {
        "dependencies": ["NAV Path (Daily Log Returns)"],
        "classification": "NO_DIRECT_DEPENDENCY",
        "explanation": "Primary primitive computed from daily logarithmic return series."
    },
    "FQ_F03": {
        "dependencies": ["NAV Path (Daily Log Returns)", "MAR=0%"],
        "classification": "PARTIAL_DEPENDENCY",
        "explanation": "Shares daily return inputs with Volatility (FQ_F02), but truncates positive returns above MAR=0%."
    },
    "FQ_F04": {
        "dependencies": ["NAV Path"],
        "classification": "NO_DIRECT_DEPENDENCY",
        "explanation": "Non-linear path metric computed from cumulative maximum array and trailing NAV points."
    },
    "FQ_F05": {
        "dependencies": ["Inception Date", "Anchor Date"],
        "classification": "NO_DIRECT_DEPENDENCY",
        "explanation": "Orthogonal metadata attribute measuring observation history depth."
    },
    "FQ_F08": {
        "dependencies": ["FQ_F01 (Return)", "FQ_F02 (Volatility)"],
        "classification": "DIRECT_DEPENDENCY",
        "explanation": "Sharpe is a direct ratio construct: Return / Volatility. Contains zero new raw data inputs."
    },
    "FQ_F09": {
        "dependencies": ["FQ_F01 (Return)", "FQ_F03 (Downside Deviation)"],
        "classification": "DIRECT_DEPENDENCY",
        "explanation": "Sortino is a direct ratio construct: Return / Downside Deviation. Contains zero new raw data inputs."
    },
    "FQ_F13": {
        "dependencies": ["NAV Path (Rolling 21-day Return Windows)"],
        "classification": "PARTIAL_DEPENDENCY",
        "explanation": "Derived from rolling sub-windows of the NAV return series."
    }
}

# 3. METRIC CALCULATION FUNCTIONS (PURE PIT)
def compute_metrics_for_scheme(nav_df: pd.DataFrame) -> Dict[str, float]:
    """Computes all 8 metrics for a single scheme given 252+ daily NAV rows sorted by date."""
    if len(nav_df) < 252:
        return None
    
    # Take trailing 252 trading days up to anchor date
    df_window = nav_df.tail(252).copy()
    navs = df_window['normalized_nav'].values
    
    if np.any(navs <= 0) or np.any(np.isnan(navs)):
        return None

    # FQ_F01: Trailing 1Y Gross Return
    r_1y = (navs[-1] / navs[0]) - 1.0

    # Daily Log Returns
    daily_returns = np.diff(np.log(navs))
    
    # FQ_F02: Annualized Volatility
    vol_1y = np.std(daily_returns, ddof=1) * np.sqrt(252)

    # FQ_F03: Downside Deviation (MAR = 0%)
    downside_returns = np.minimum(daily_returns, 0.0)
    dd_1y = np.sqrt(np.mean(downside_returns ** 2)) * np.sqrt(252)

    # FQ_F04: Maximum Drawdown
    peaks = np.maximum.accumulate(navs)
    drawdowns = (peaks - navs) / peaks
    mdd_1y = np.max(drawdowns)

    # FQ_F05: Fund Age (In years relative to anchor window end)
    # Using total nav_df rows as history depth proxy (days / 252)
    fund_age = len(nav_df) / 252.0

    # FQ_F08: Sharpe Ratio (Rf = 0%)
    sharpe_1y = r_1y / vol_1y if vol_1y > 1e-6 else np.nan

    # FQ_F09: Sortino Ratio (MAR = 0%)
    sortino_1y = r_1y / dd_1y if dd_1y > 1e-6 else np.nan

    # FQ_F13: Rolling 1M (21-day) Return Consistency
    # Compute rolling 21-day returns over the 252 days (231 windows)
    if len(navs) >= 252:
        rolling_returns = (navs[21:] / navs[:-21]) - 1.0
        consistency_1y = np.mean(rolling_returns > 0.0)
    else:
        consistency_1y = np.nan

    return {
        "FQ_F01": float(r_1y),
        "FQ_F02": float(vol_1y),
        "FQ_F03": float(dd_1y),
        "FQ_F04": float(mdd_1y),
        "FQ_F05": float(fund_age),
        "FQ_F08": float(sharpe_1y),
        "FQ_F09": float(sortino_1y),
        "FQ_F13": float(consistency_1y)
    }

def run_f14_audit():
    print("=" * 80)
    print("STARTING PHASE F.14 — METRIC INTERACTION & REDUNDANCY AUDIT")
    print("=" * 80)

    # Verify DB existence
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database {DB_PATH} not found!")

    conn = sqlite3.connect(DB_PATH)

    # Load Canonical Schemes with Categories
    schemes_df = pd.read_sql_query(
        "SELECT canonical_scheme_id, scheme_name, clean_scheme_name, category, sub_category AS subcategory FROM canonical_schemes", conn
    )
    print(f"Loaded {len(schemes_df)} canonical schemes.")


    # Anchor Date: 2024-03-28 (Historical Anchor Point used in F.11.3.5 / F.11.3.5.5)
    anchor_date = "2024-03-28"
    print(f"Anchor Date for PIT Audit: {anchor_date}")

    # Fetch NAV records up to anchor_date
    nav_query = f"""
        SELECT canonical_scheme_id, nav_date, nav_value AS normalized_nav
        FROM normalized_nav_records
        WHERE nav_date <= '{anchor_date}'
        ORDER BY canonical_scheme_id, nav_date ASC
    """
    print("Querying historical daily NAV records up to anchor date...")
    all_navs = pd.read_sql_query(nav_query, conn)
    conn.close()
    print(f"Retrieved {len(all_navs)} NAV observations.")

    # Group NAVs by scheme
    grouped = all_navs.groupby("canonical_scheme_id")

    metrics_list = []
    for scheme_id, group in grouped:
        m = compute_metrics_for_scheme(group)
        if m is not None:
            m["canonical_scheme_id"] = scheme_id
            metrics_list.append(m)

    df_metrics = pd.DataFrame(metrics_list)
    df_metrics = df_metrics.merge(schemes_df, on="canonical_scheme_id", how="inner")
    print(f"Successfully computed complete 8-metric PIT panel for N = {len(df_metrics)} schemes.")


    # Map broad categories (Equity, Debt, Hybrid, Other)
    def map_broad_category(row):
        name = str(row.get('scheme_name', '')).upper()
        clean = str(row.get('clean_scheme_name', '')).upper()
        cat = str(row.get('category', '')).upper()
        
        full_text = f"{name} {clean} {cat}"

        if any(k in full_text for k in ["EQUITY", "LARGE CAP", "MID CAP", "SMALL CAP", "FLEXI CAP", "ELSS", "INDEX", "SECTORAL", "THEMATIC"]):
            return "Equity"
        elif any(k in full_text for k in ["DEBT", "BOND", "TREASURY", "GILT", "LIQUID", "OVERNIGHT", "FIXED TERM", "FTP", "INCOME", "MONEY MARKET"]):
            return "Debt"
        elif any(k in full_text for k in ["HYBRID", "BALANCED", "ARBITRAGE", "DYNAMIC ASSET", "MULTI ASSET"]):
            return "Hybrid"
        else:
            return "Other"

    df_metrics['broad_category'] = df_metrics.apply(map_broad_category, axis=1)


    # 4. PAIRWISE STATISTICAL RELATIONSHIPS & REDUNDANCY AUDIT
    pairs_to_audit = [
        ("FQ_F01", "FQ_F02", "Return vs Volatility"),
        ("FQ_F01", "FQ_F03", "Return vs Downside Deviation"),
        ("FQ_F01", "FQ_F04", "Return vs MDD"),
        ("FQ_F01", "FQ_F13", "Return vs Consistency"),
        ("FQ_F02", "FQ_F03", "Volatility vs Downside Deviation"),
        ("FQ_F02", "FQ_F04", "Volatility vs MDD"),
        ("FQ_F02", "FQ_F13", "Volatility vs Consistency"),
        ("FQ_F03", "FQ_F04", "Downside Deviation vs MDD"),
        ("FQ_F03", "FQ_F13", "Downside Deviation vs Consistency"),
        ("FQ_F04", "FQ_F13", "MDD vs Consistency"),
        ("FQ_F08", "FQ_F01", "Sharpe vs Return"),
        ("FQ_F08", "FQ_F02", "Sharpe vs Volatility"),
        ("FQ_F09", "FQ_F01", "Sortino vs Return"),
        ("FQ_F09", "FQ_F03", "Sortino vs Downside Deviation"),
        ("FQ_F08", "FQ_F09", "Sharpe vs Sortino"),
        ("FQ_F05", "FQ_F01", "Fund Age vs Return"),
        ("FQ_F05", "FQ_F02", "Fund Age vs Volatility")
    ]

    pairwise_results = []

    for metric_a, metric_b, relationship_label in pairs_to_audit:
        # Full Population Analysis
        valid_df = df_metrics[[metric_a, metric_b, "broad_category"]].dropna()
        N_all = len(valid_df)
        
        if N_all > 10:
            rho_all, _ = spearmanr(valid_df[metric_a], valid_df[metric_b])
            r_all, _ = pearsonr(valid_df[metric_a], valid_df[metric_b])
        else:
            rho_all, r_all = np.nan, np.nan

        # Category-Aware Breakdowns
        cat_correlations = {}
        for cat in ["Equity", "Debt", "Hybrid"]:
            cat_sub = valid_df[valid_df["broad_category"] == cat]
            if len(cat_sub) > 10:
                rho_cat, _ = spearmanr(cat_sub[metric_a], cat_sub[metric_b])
                cat_correlations[cat] = {
                    "N": int(len(cat_sub)),
                    "spearman_rho": float(round(rho_cat, 4))
                }
            else:
                cat_correlations[cat] = {"N": int(len(cat_sub)), "spearman_rho": None}

        # Classify Redundancy
        # Rules:
        # 1. DIRECT_DEPENDENCY if mathematically derived (Sharpe vs Vol/Return, Sortino vs DD/Return)
        # 2. STRONG OVERLAP if |rho| >= 0.85
        # 3. POTENTIAL OVERLAP if 0.65 <= |rho| < 0.85
        # 4. NO EVIDENCE OF REDUNDANCY if |rho| < 0.65
        dep_type = DEPENDENCY_MAP.get(metric_a, {}).get("classification")
        if metric_a in ["FQ_F08", "FQ_F09"] and metric_b in ["FQ_F01", "FQ_F02", "FQ_F03"]:
            redundancy_class = "MATHEMATICAL DEPENDENCY"
        elif metric_a == "FQ_F08" and metric_b == "FQ_F09":
            redundancy_class = "MATHEMATICAL DEPENDENCY"
        elif abs(rho_all) >= 0.85:
            redundancy_class = "STRONG OVERLAP"
        elif abs(rho_all) >= 0.65:
            redundancy_class = "POTENTIAL OVERLAP"
        else:
            redundancy_class = "NO EVIDENCE OF REDUNDANCY"

        # Explainability & Result Object
        explanation_obj = {
            "metric_a": metric_a,
            "metric_b": metric_b,
            "relationship_label": relationship_label,
            "overall_N": int(N_all),
            "spearman_rho": float(round(rho_all, 4)),
            "pearson_r": float(round(r_all, 4)),
            "category_breakdown": cat_correlations,
            "redundancy_classification": redundancy_class,
            "anchor_date": anchor_date,
            "dataset_version": "db/backfill_f12_2.db (canonical_schemes)",
            "interpretation": f"{relationship_label} exhibits a Spearman rank correlation of {rho_all:.4f} across all schemes. Classified as {redundancy_class}.",
            "limitation": "High correlation indicates co-movement but does not prove conceptual redundancy or identical path sensitivity."
        }

        pairwise_results.append(explanation_obj)

    # 5. DEDICATED QUADRANT ANALYSES (Real Data Examples)
    # Downside Deviation (FQ_F03) vs Max Drawdown (FQ_F04)
    # Volatility (FQ_F02) vs Downside Deviation (FQ_F03)
    # Volatility (FQ_F02) vs Max Drawdown (FQ_F04)
    
    def extract_quadrants(df, col1, col2):
        med1 = df[col1].median()
        med2 = df[col2].median()
        
        q_high_high = df[(df[col1] > med1) & (df[col2] > med2)].head(2)
        q_high_low  = df[(df[col1] > med1) & (df[col2] <= med2)].head(2)
        q_low_high  = df[(df[col1] <= med1) & (df[col2] > med2)].head(2)
        q_low_low   = df[(df[col1] <= med1) & (df[col2] <= med2)].head(2)

        return {
            "high_high": q_high_high[["canonical_scheme_id", col1, col2]].to_dict(orient="records"),
            "high_low": q_high_low[["canonical_scheme_id", col1, col2]].to_dict(orient="records"),
            "low_high": q_low_high[["canonical_scheme_id", col1, col2]].to_dict(orient="records"),
            "low_low": q_low_low[["canonical_scheme_id", col1, col2]].to_dict(orient="records")
        }


    quadrants_dd_mdd = extract_quadrants(df_metrics, "FQ_F03", "FQ_F04")
    quadrants_vol_dd = extract_quadrants(df_metrics, "FQ_F02", "FQ_F03")
    quadrants_vol_mdd = extract_quadrants(df_metrics, "FQ_F02", "FQ_F04")

    # Save Output JSON Artifacts
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    inventory_filepath = os.path.join(OUTPUT_DIR, "phase_f14_metric_inventory.json")
    with open(inventory_filepath, "w") as f:
        json.dump({
            "metrics": METRIC_INVENTORY,
            "dependencies": DEPENDENCY_MAP
        }, f, indent=2)
    print(f"Saved Metric Inventory to {inventory_filepath}")

    pairwise_filepath = os.path.join(OUTPUT_DIR, "phase_f14_pairwise_relationships.json")
    with open(pairwise_filepath, "w") as f:
        json.dump({
            "anchor_date": anchor_date,
            "total_schemes_analyzed": len(df_metrics),
            "pairwise_relationships": pairwise_results,
            "quadrant_examples": {
                "downside_vs_mdd": quadrants_dd_mdd,
                "volatility_vs_downside": quadrants_vol_dd,
                "volatility_vs_mdd": quadrants_vol_mdd
            }
        }, f, indent=2)
    print(f"Saved Pairwise Relationships to {pairwise_filepath}")

    print("\n" + "=" * 80)
    print("PHASE F.14 METRIC INTERACTION AUDIT COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_f14_audit()
