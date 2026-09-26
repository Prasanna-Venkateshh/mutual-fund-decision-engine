# Fund Quality Scoring Configuration Specification

**Configuration Version:** `1.0.0`  
**Methodology Version:** `1.0.0`  
**Status:** `PROVISIONAL — REQUIRES VALIDATION`

---

## 1. Overview

This document specifies the governed configuration parameters for the Fund Quality Scoring Engine. All parameters are externalized in [`scoring/config.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scoring/config.py) and enforce deterministic, versioned, and auditable calculation behavior.

---

## 2. Core Configuration Parameters

```yaml
scoring_methodology_version: "1.0.0"
weight_config_version: "1.0.0"
score_range:
  min: 0.0
  max: 100.0

peer_group_constraints:
  min_peer_count: 3
  small_peer_threshold: 10

dynamic_downside_bounds:
  min_multiplier: 0.80
  max_multiplier: 1.20

coverage_constraints:
  min_active_weight_ratio: 0.40
```

---

## 3. Dimension Weights by Category Family

| Dimension Key | Equity Family | Debt Family | Hybrid Family | Other Family | Directionality |
|---|---|---|---|---|---|
| `return` | 25% | 15% | 20% | 20% | Higher is Better |
| `consistency` | 20% | 15% | 20% | 20% | Higher is Better |
| `volatility` | 15% | 25% | 15% | 15% | Lower is Better |
| `downside_risk` | 15% | 20% | 15% | 15% | Lower is Better |
| `max_drawdown` | 15% | 15% | 15% | 15% | Lower is Better |
| `cost_efficiency` | 10% | 10% | 15% | 15% | Lower is Better |
| **Total** | **100%** | **100%** | **100%** | **100%** | — |

---

## 4. Subcategory Dynamic Downside Adjustments

| Subcategory | Adjustment Trigger | Downside Multiplier ($M_{\text{downside}}$) | Effect |
|---|---|---|---|
| `Small Cap Fund` | High Volatility / High Drawdown Potential | `1.15` | Increases downside risk weight by 15%; re-scales other weights proportionally. |
| `Sectoral/Thematic` | High Volatility Concentration | `1.15` | Increases downside risk weight by 15%; re-scales other weights proportionally. |
| Standard Subcategories | Standard Peer Group | `1.00` | Uses baseline family weight table unchanged. |

---

## 5. Confidence Penalties & Adjustments

| Factor | Condition | Multiplier / Value |
|---|---|---|
| **Maturity Factor ($C_{\text{maturity}}$)** | `TEN_PLUS_YEARS` | 1.00 |
| | `FIVE_TO_TEN_YEARS` | 0.95 |
| | `THREE_TO_FIVE_YEARS` | 0.85 |
| | `ONE_TO_THREE_YEARS` | 0.70 |
| | `LESS_THAN_1_YEAR` | 0.40 (Score = `None`) |
| **Peer Count Factor ($C_{\text{peers}}$)** | $N \ge 10$ | 1.00 |
| | $3 \le N < 10$ | $0.50 + 0.50 \times ((N - 3) / 7)$ |
| | $N < 3$ | 0.40 (Absolute normalization fallback) |
| **Coverage Factor ($C_{\text{coverage}}$)** | $\text{Active Weight Ratio} \ge 0.40$ | $\sum_{d \in \text{Available}} W_d$ |
| | $\text{Active Weight Ratio} < 0.40$ | Score = `None` |
