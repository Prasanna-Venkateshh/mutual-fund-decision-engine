# Phase F.11.3.5 Experiment Manifest

> [!NOTE]
> **Experiment Identification**:
> - **Phase**: F.11.3.5 Incremental Information & Risk-Value Validation: Control vs Alt A vs Trailing Return
> - **Execution Timestamp**: 2026-09-15 (Frozen before empirical execution)
> - **Primary Dataset**: db/backfill_f12_2.db (F.12.2, read-only)
> - **Scoring Methodology Version**: 1.0.0 (Frozen — zero production changes permitted)

---

## 1. Purpose & Governance

This manifest pre-registers all methodological choices for Phase F.11.3.5 before any
empirical results are examined. No element of this manifest may be modified after
empirical execution begins.

### 1.1 Central Research Questions

1. Does the **Control** (production) Fund Quality Score add statistically and
   economically meaningful information beyond trailing 1Y return?
2. Does **Alternative A** (research-only) add statistically and economically meaningful
   information beyond trailing 1Y return?
3. Does either score add forward-**risk** information that trailing return does not
   capture?
4. Are any observed advantages stable across temporal periods (not regime-specific)?

### 1.2 Governance Constraints

- This is an **empirical validation phase only**.
- Do NOT tune, optimize, promote, replace, or modify production scoring methodology.
- Treat trailing 1Y return as the **principal simple benchmark** throughout.
- Prior erroneous baseline (ρ = -0.3278, N = 8,626 from F.11.3.4) is **superseded**
  and must NOT be used. The authoritative baseline is **N = 14,356, ρ = +0.3096**.
- Do NOT interpret correlation magnitude as investment return superiority.

---

## 2. Frozen Methodologies Under Test

### 2.1 Control (Production) Weights

| Dimension       | Weight |
|----------------|--------|
| Return          | 25.0%  |
| Consistency     | 20.0%  |
| Volatility      | 15.0%  |
| Downside Risk   | 15.0%  |
| Max Drawdown    | 15.0%  |
| Cost Efficiency | 10.0%  |

### 2.2 Alternative A (Research-Only, Redundancy-Reduced) Weights

| Dimension       | Weight |
|----------------|--------|
| Return          | 30.0%  |
| Consistency     | 25.0%  |
| Volatility      | 15.0%  |
| Downside Risk   |  0.0%  |
| Max Drawdown    | 20.0%  |
| Cost Efficiency | 10.0%  |

### 2.3 Baseline: Trailing 1Y Return

Raw CAGR from earliest available PIT NAV to evaluation date T.
Formula: (end_nav/start_nav)^(365.25/days_span) - 1, where days_span >= 365
(authoritative definition per F.11.3.4.1 reconciliation).

---

## 3. Sample Construction (Frozen)

### 3.1 Eligibility Criteria

- Scheme must have >= 20 pre-T point-in-time NAV observations.
- days_span >= 365 (eliminates sub-1Y histories; per F.11.3.4.1 authoritative spec).
- Start NAV and End NAV must both be > 0.
- Forward 1Y NAV window must be non-empty (>= 1 NAV observation in (T, T+365 days]).
- Both 	railing_1y and out_1y must be non-null after all filters.

### 3.2 Score Computation

Scores computed via cross-sectional percentile normalization within each evaluation-date
cohort, as established in F.11.3.3. Cost efficiency is fixed at the 50th percentile.

### 3.3 Temporal Partitioning

| Partition              | Evaluation Dates                       | Role            |
|-----------------------|---------------------------------------|-----------------|
| Development Period     | 2016-01-31, 2018-01-31, 2020-01-31    | Reference/context |
| Validation Period 1    | 2021-01-31                            | Post-COVID Recovery |
| Validation Period 2    | 2022-01-31                            | Inflation/Rate-Hike Sideways |
| Validation Period 3    | 2023-01-31                            | Broad Bull Rally |
| **Combined Validation**| **2021-2023**                         | **PRIMARY OOS** |

### 3.4 Authoritative Baseline Anchors (from F.11.3.4.1)

| Date       | Paired N | Trailing 1Y Spearman ρ |
|------------|----------|------------------------|
| 2021-01-31 | ~4,847   | +0.4491               |
| 2022-01-31 | ~4,961   | +0.0244               |
| 2023-01-31 | ~4,548   | +0.6998               |
| Combined   | 14,356   | +0.3096               |

---

## 4. Statistical Framework

### 4.1 Primary Metrics

**A. Spearman Rank Correlation vs Forward 1Y Return**
Computed per evaluation date and pooled for combined validation.

**B. Incremental R² (Regression Decomposition)**
- Model 1 (Baseline):  Forward 1Y ~ Intercept + Trailing 1Y
- Model 2 (Control):   Forward 1Y ~ Intercept + Trailing 1Y + Control Score
- Model 3 (Alt A):     Forward 1Y ~ Intercept + Trailing 1Y + Alt A Score
- Incremental R²(Control) = R²(Model 2) - R²(Model 1)
- Incremental R²(Alt A)   = R²(Model 3) - R²(Model 1)

**C. Clustered Standard Errors (Dependence-Aware Inference)**
- OLS standard errors (benchmark).
- Scheme-clustered SE (within-scheme correlation across dates).
- Date-clustered SE (cross-sectional dependence within date).

**D. Forward Risk Discipline**
- Spearman ρ of each score vs Forward 1Y Max Drawdown (negative = risk-reducing).
- Spearman ρ of each score vs Forward 1Y Annualized Volatility.

### 4.2 Secondary Metrics

**E. Quantile Monotonicity (Q1-Q5):** Mean forward 1Y return per quintile.
**F. Regime Stability (Date-by-Date):** Per-date Spearman ρ for all 3 models.
**G. Score Rank Stability:** Alt A vs Control Spearman rank correlation & top-quintile overlap.

### 4.3 Economic Significance Thresholds (Pre-registered)

| Test                          | Threshold for Economically Meaningful |
|-------------------------------|--------------------------------------|
| Incremental R²                | > 0.10% (>= 1 bp explanatory power)  |
| Spearman ρ (vs baseline excess) | > +0.02 in combined validation        |
| Date-Clustered t-stat (score) | > 1.65 (one-tailed, 5%)              |
| Forward MDD ρ (Control)       | < -0.10 (protective / risk-reducing)  |
| Forward MDD ρ (Alt A)         | < 0.0 (neutral; must not be exposing) |

---

## 5. Pre-registered Interpretation Grid

| Outcome                                              | Interpretation |
|------------------------------------------------------|----------------|
| Control Inc R² > 0.10% AND Date-Cluster t > 1.65   | Control adds meaningful incremental information |
| Control Inc R² <= 0.10% OR Date-Cluster t <= 1.65  | Control does not add meaningful incremental info |
| Alt A Inc R² > 0.10% AND Date-Cluster t > 1.65     | Alt A adds meaningful incremental information |
| Alt A Inc R² <= 0.10% OR Date-Cluster t <= 1.65    | Alt A does not add meaningful incremental info |
| Control Forward MDD ρ < -0.10                      | Control demonstrates risk-protective selection |
| Alt A Forward MDD ρ < 0.0                          | Alt A is risk-neutral (acceptable candidate) |
| Alt A Forward MDD ρ >= 0.0                         | Alt A may be risk-exposing (requires further review) |
| Neither score beats baseline in >= 2 of 3 val dates | Insufficient temporal stability |

---

## 6. Deliverables

| Deliverable | Path |
|------------|------|
| Experiment Manifest (this doc) | docs/phase_f11_3_5_experiment_manifest.md |
| Analysis Script | scratch/run_f11_3_5_incremental_validation.py |
| Forensic Report | docs/phase_f11_3_5_incremental_information_risk_value_validation.md |
| Test Suite | 	ests/financial/test_phase_f11_3_5_incremental_validation.py |

---

## 7. Superseded Results Reference

The following prior results are explicitly superseded and must NOT be used in
F.11.3.5 interpretation:

- F.11.3.4 combined OOS Trailing 1Y ρ = -0.3278, N = 8,626: Identified in F.11.3.4.1
  as an editorial artifact. Replaced by ρ = +0.3096, N = 14,356.
