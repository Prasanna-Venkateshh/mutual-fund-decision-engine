# Phase E — Fund Quality Scoring Methodology

**Document Status:** GOVERNED METHODOLOGY SPECIFICATION  
**Methodology Version:** `1.0.0`  
**Weight Configuration Version:** `1.0.0`  
**Score Range:** `[0.0, 100.0]`  
**Status Marking:** `PROVISIONAL — REQUIRES VALIDATION`

---

## 1. Executive Summary & Architectural Scope

Phase E establishes the first governed version of the **Fund Quality Scoring Engine** for the `mutual-fund-decision-engine`.

### Governing Pipeline Scope

```
DATA
  ↓
METRICS
  ↓
FUND QUALITY DATASET (Phase D.6 Input)
  ↓
FUND QUALITY SCORE (Phase E Engine)
  --------------------------------- [PHASE E BOUNDARY]
  ↓ (DO NOT IMPLEMENT IN PHASE E)
SUITABILITY
  ↓
PORTFOLIO NEED
  ↓
ECONOMIC BENEFIT
  ↓
ACTION (Buy / Accumulate / Hold / Sell)
```

The scoring engine evaluates **FUND QUALITY ONLY**. It does **NOT** generate buy/sell recommendations, portfolio allocations, or tax-aware switches, nor does it consume investor-specific risk profiles or goals.

---

## 2. Core Scoring Principles

1. **Category-Aware:** Evaluated relative to point-in-time category peers.
2. **Explainable:** Every component score retains raw metrics, peer percentiles, active weights, and natural language explanations.
3. **Evidence-Based & Deterministic:** Consumes upstream metric snapshots from Phase D.6 without recalculating financial metrics. Same inputs yield exact identical scores.
4. **Confidence-Aware:** Score ($0.0 - 100.0$) and Confidence ($0.0 - 1.0$) are strictly separate outputs.
5. **Missing-Data Resilient:** Missing dimensions ($\text{metric} = \text{None}$) are **NEVER** treated as zero. Available dimension weights are proportionally re-scaled to sum to 100%.
6. **Anti-Survivorship Safe:** Peer populations are constructed strictly point-in-time as of the observation date.
7. **Bounded:** Component and final scores are clamped to $[0.0, 100.0]$.

---

## 3. Fund Quality Dimensions & Directionality

| Dimension Key | Dimension Name | Primary Metric Input | Directionality | Direction Rationale |
|---|---|---|---|---|
| `return` | Return | Rolling 1Y / 3Y Mean Return, CAGR | Higher is Better | Superior compound wealth generation relative to peers. |
| `consistency` | Consistency | % Positive Rolling Periods | Higher is Better | Higher proportion of profitable rolling holding periods. |
| `volatility` | Volatility | Annualized Volatility | Lower is Better | Lower standard deviation of periodic returns. |
| `downside_risk` | Downside Risk | Downside Deviation (MAR = 0%) | Lower is Better | Lower downside risk below minimum acceptable return. |
| `max_drawdown` | Maximum Drawdown | Maximum Drawdown | Lower is Better | Lower peak-to-trough historical capital loss. |
| `cost_efficiency` | Cost Efficiency | Total Expense Ratio (TER) | Lower is Better | Lower recurring fund expenses. |
| `maturity` | History Longevity | `HistoryMaturityBucket` / Track Record | Informational / Confidence | Longer track record increases evidence confidence. |

---

## 4. Normalization Methodology

Metric values are normalized relative to their eligible point-in-time category peer population using a **Rank-Based Midpoint Percentile** formula:

$$\text{Percentile} = \left( \frac{\text{Rank} - 0.5}{N} \right) \times 100$$

Where:
- $N$ is the total count of valid peer records with non-null values for the metric.
- $\text{Rank}$ is 1-indexed.
- For **Higher-is-Better** metrics (Return, Consistency): $\text{Component Score} = \text{Percentile}$.
- For **Lower-is-Better** metrics (Volatility, Downside Risk, Max Drawdown, Expense Ratio): $\text{Component Score} = 100.0 - \text{Percentile}$.

### Ties & Small Peer Population Rules
- **Ties:** Handled by assigning average mid-rank to equal metric values.
- **Minimum Peer Count:** Minimum default peer count is $N_{\min} = 3$. If $N < 3$, peer-relative normalization falls back to absolute bounds with reduced confidence penalty.

---

## 5. Category-Family Weighting Profiles

Weights are externalized and versioned (`weight_config_version: "1.0.0"`). Weights sum to 1.0 (100%) per category family.

### Category Family Assignment

- **Equity Family:** Large Cap, Mid Cap, Small Cap, Flexi Cap, Large & Mid Cap, ELSS, Sectoral/Thematic, Dividend Yield, Value/Contra, Focused.
- **Debt Family:** Liquid, Overnight, Ultra Short Duration, Low Duration, Money Market, Short Duration, Medium Duration, Long Duration, Dynamic Bond, Corporate Bond, Credit Risk, Banking and PSU, Gilt, Floater.
- **Hybrid Family:** Aggressive Hybrid, Balanced Hybrid, Conservative Hybrid, Dynamic Asset Allocation (Balanced Advantage), Multi Asset Allocation, Arbitrage, Equity Savings.
- **Other Family:** Index Funds, ETFs, FoFs, Solution Oriented, Commodity (Gold/Silver).

### Dimension Weights Table

| Dimension | Equity | Debt | Hybrid | Other (Default) |
|---|---|---|---|---|
| `return` | 25% | 15% | 20% | 20% |
| `consistency` | 20% | 15% | 20% | 20% |
| `volatility` | 15% | 25% | 15% | 15% |
| `downside_risk` | 15% | 20% | 15% | 15% |
| `max_drawdown` | 15% | 15% | 15% | 15% |
| `cost_efficiency` | 10% | 10% | 15% | 15% |
| **Total** | **100%** | **100%** | **100%** | **100%** |

---

## 6. Dynamic Downside Importance

Dynamic downside risk adjustment is strictly objective and category/subcategory-driven. It **NEVER** incorporates investor risk tolerance or personal preferences.

- **High-Volatility Subcategories:** (e.g. Small Cap Equity, Sectoral/Thematic Equity).
- **Multiplier:** Multiplier $M_{\text{downside}} = 1.15$, bounded within $[0.80, 1.20]$.
- **Effect:** Downside Risk weight is increased by 15%, while remaining weights are proportionally reduced to maintain a 100% sum.

---

## 7. Score Aggregation & Missing-Data Handling

The Fund Quality Score is aggregated across available dimensions:

$$\text{Quality Score} = \sum_{d \in \text{Available}} \left( \text{Component Score}_d \times \text{Re-scaled Weight}_d \right)$$

Where:

$$\text{Re-scaled Weight}_d = \frac{W_d}{\sum_{k \in \text{Available}} W_k}$$

### Minimum Evidence & Insufficient History Rule
- If the fund has $< 1$ year of track record (`LESS_THAN_1_YEAR`) or total active weight $< 40\%$, the quality score returns `None` (`quality_score = None`).
- Missing metrics (e.g. historical TER missing) exclude `cost_efficiency` from available dimensions, re-scaling remaining weights and applying a data quality penalty to Confidence.

---

## 8. Confidence Calculation Architecture

Score and Confidence are strictly decoupled:

$$\text{Confidence} = \text{Base Confidence} \times C_{\text{maturity}} \times C_{\text{coverage}} \times C_{\text{peers}} \times C_{\text{identity}}$$

Where:
- **Base Confidence:** Default $1.0$.
- **Maturity Factor ($C_{\text{maturity}}$):**
  - $\ge 10$ Years: $1.00$
  - 5–10 Years: $0.95$
  - 3–5 Years: $0.85$
  - 1–3 Years: $0.70$
  - $< 1$ Year: $0.40$
- **Coverage Factor ($C_{\text{coverage}}$):** Ratio of active dimension weight available ($\ge 0.40$).
- **Peer Population Factor ($C_{\text{peers}}$):** $1.0$ if $N \ge 10$, scaled down linearly to $0.5$ for small peer groups.
- **Identity Confidence ($C_{\text{identity}}$):** Passed directly from Phase D.6 dataset input.

---

## 9. Provenance & Versioning

Every `FundQualityScoreResult` records:
- `scheme_code` & `canonical_scheme_id`
- `observation_date`
- `scoring_methodology_version: "1.0.0"`
- `weight_config_version: "1.0.0"`
- `calculation_timestamp_utc`
- `dimensions_available` & `dimensions_unavailable`
- Full breakdown of `DimensionScore` per metric

---

## 10. Status & Provisional Decisions

> [!IMPORTANT]
> **Status:** `PROVISIONAL — REQUIRES VALIDATION`  
> Weights and dynamic downside multipliers are established as an auditable V1 baseline. They must undergo empirical validation before being deployed for live financial decisioning.
