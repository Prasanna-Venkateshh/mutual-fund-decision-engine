# Phase F.11.3.4 Experiment Manifest

> [!NOTE]
> **Experiment Identification**:
> - **Phase**: F.11.3.4 Temporal Out-of-Sample Validation of Fund Quality vs Trailing-Return Baseline
> - **Execution Timestamp**: 2026-09-15
> - **Primary Dataset**: `db/backfill_f12_2.db` ($N = 23,120$ observations)
> - **Scoring Methodology Version**: 1.0.0 (Frozen)

---

## 1. Experimental Design & Temporal Splits

All temporal validation periods are chronologically disjoint and defined prior to empirical evaluation:

| Partition Name | Evaluation Dates | Observation Count ($N$) | Market Regime Description |
| :--- | :--- | :---: | :--- |
| **Development Period** | 2016-01-31, 2018-01-31, 2020-01-31 | 8,764 | Early Expansion, Mid-Cycle Correction, Pre-COVID |
| **Validation Period 1** | 2021-01-31 | 4,847 | Post-COVID Rebound & Liquidity Surge |
| **Validation Period 2** | 2022-01-31 | 4,961 | Global Inflation & Rate Hike Sideways Market |
| **Validation Period 3** | 2023-01-31 | 4,548 | Broad Market Equity Rally |
| **Combined Validation** | 2021-01-31, 2022-01-31, 2023-01-31 | 14,356 | Full Out-of-Sample Horizon |

---

## 2. Frozen Candidate Weight Matrix

All candidate weight configurations were locked before inspecting outcome data:

```python
FROZEN_WEIGHTS = {
    'Control': {
        'return': 25.0,
        'consistency': 20.0,
        'volatility': 15.0,
        'downside_risk': 15.0,
        'max_drawdown': 15.0,
        'cost_efficiency': 10.0
    },
    'Alt_A': {
        'return': 30.0,
        'consistency': 25.0,
        'volatility': 15.0,
        'downside_risk': 0.0,
        'max_drawdown': 20.0,
        'cost_efficiency': 10.0
    },
    'Baseline_1Y': {
        'return': 100.0
    }
}
```

---

## 3. Regression & Statistical Equations

### Baseline Challenge Regressions
- **Model 1**: $\text{Forward 1Y Return}_i = \beta_0 + \beta_1 \cdot \text{Trailing 1Y Return}_i + \epsilon_i$
- **Model 2**: $\text{Forward 1Y Return}_i = \beta_0 + \beta_1 \cdot \text{Trailing 1Y Return}_i + \beta_2 \cdot \text{Control Score}_i + \epsilon_i$
- **Model 3**: $\text{Forward 1Y Return}_i = \beta_0 + \beta_1 \cdot \text{Trailing 1Y Return}_i + \beta_3 \cdot \text{Alt A Score}_i + \epsilon_i$

### Cluster-Robust Standard Errors
Cluster-robust variance-covariance matrix estimated per canonical scheme $c$:
$$V_{\text{clustered}} = \frac{G}{G-1} \frac{N-1}{N-K} (X^T X)^{-1} \left( \sum_{g=1}^G X_g^T \hat{e}_g \hat{e}_g^T X_g \right) (X^T X)^{-1}$$

---

## 4. Verification Checksums & Hashes

- **Data File**: `db/backfill_f12_2.db`
- **Execution Script**: `scratch/run_f11_3_4_temporal_oos_validation.py`
- **Test File**: `tests/financial/test_phase_f11_3_4_temporal_oos_validation.py`
- **Report Document**: `docs/phase_f11_3_4_temporal_out_of_sample_validation.md`
