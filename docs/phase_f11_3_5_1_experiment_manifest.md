# Phase F.11.3.5.1 Experiment Manifest

> [!NOTE]
> **Experiment Identification**:
> - **Phase**: F.11.3.5.1 Incremental Forward-Risk Reconciliation & Temporal Risk-Value Validation
> - **Execution Timestamp**: 2026-09-15 (Frozen before empirical execution)
> - **Primary Dataset**: `db/backfill_f12_2.db` (F.12.2, read-only)
> - **Scoring Methodology Version**: 1.0.0 (Frozen — zero production changes permitted)

---

## 1. Purpose & Governance

This manifest pre-registers all methodological choices and model specifications for Phase F.11.3.5.1 prior to final result interpretation.

### 1.1 Central Research Questions

1. Does **Control** contain information about future risk (Forward 1Y MDD, Volatility, Downside Deviation) that is not already represented by trailing 1Y return?
2. Is the observed incremental risk relationship statistically supported under appropriate dependence-aware inference (scheme-clustered and date-clustered standard errors)?
3. Is the risk relationship temporally consistent across 2021-01-31, 2022-01-31, and 2023-01-31?
4. Is the risk relationship robust to date-equalization, maturity partitioning, and category stratification?
5. Does Control provide genuine risk-protective value or merely risk-aware structural association?

### 1.2 Governance Constraints

- **Empirical Validation Only**: No tuning, optimization, promotion, or modification of production scoring methodology.
- **Frozen Production Weights**: Equity Return = 25.0%, Consistency = 20.0%, Volatility = 15.0%, Downside Risk = 15.0%, Max Drawdown = 15.0%, Cost Efficiency = 10.0%.
- **Authoritative Baseline Anchor**: F.11.3.4.1 baseline ($N = 14,356$, Spearman $\rho = +0.3096$) is strictly enforced.
- **Real-Data Firewall**: All headline empirical results must originate from F.12.2 longitudinal NAV data. No synthetic fixtures contribute to headline results.
- **No Actionability Claims**: No evaluation or claim regarding BUY, HOLD, SELL, transaction costs, tax, or exit loads.

---

## 2. Frozen Methodologies & Outcomes

### 2.1 Score Methodologies Under Test

1. **Control (Production)**: Exact v1.0.0 production weights and formulas.
2. **Trailing 1Y Return**: Authoritative baseline (raw CAGR over trailing $\ge 365$ days).
3. **Alt A (Secondary Diagnostic)**: Research-only redundancy-reduced weights (Return=30%, Consistency=25%, Vol=15%, MDD=20%, Cost=10%).

### 2.2 Primary Risk Outcomes

1. **Forward 1Y Maximum Drawdown (Forward MDD)**: Peak-to-trough decline over $[T, T + 365\text{ days}]$.
2. **Forward 1Y Volatility (Forward Vol)**: Annualized standard deviation of daily NAV returns over $[T, T + 365\text{ days}]$.

### 2.3 Secondary Risk Outcomes

1. **Forward 1Y Downside Deviation (Forward Downside)**: Annualized downside deviation relative to a 6% hurdle rate over $[T, T + 365\text{ days}]$.
2. **Forward 3Y Maximum Drawdown & Volatility**: Calculated for evaluation dates where 3Y forward data exists ($T = 2021\text{-}01\text{-}31, 2022\text{-}01\text{-}31$).

---

## 3. Model Specifications & Statistical Inference

### 3.1 Incremental Risk Models

For each risk outcome $Y \in \{\text{Forward MDD}, \text{Forward Volatility}, \text{Forward Downside}\}$:

- **Baseline Model (Model A)**:
  $$Y_i = \beta_0 + \beta_1 \cdot \text{Trailing1Y}_i + \varepsilon_i$$

- **Full Model (Model B)**:
  $$Y_i = \beta_0 + \beta_1 \cdot \text{Trailing1Y}_i + \beta_2 \cdot \text{ControlScore}_i + \varepsilon_i$$

### 3.2 Key Statistical Metrics

- Baseline $R^2$, Full $R^2$, and Incremental $R^2 = R^2_{\text{Full}} - R^2_{\text{Baseline}}$.
- OLS Standard Errors, Scheme-Clustered Standard Errors (Liang-Zeger), and Date-Clustered Standard Errors (with explicit caveat regarding $G=3$ date clusters).
- Spearman Rank Correlation ($\rho$) between score/baseline and forward risk outcomes.

---

## 4. Primary Validation Sample

- **Evaluation Dates**: 2021-01-31, 2022-01-31, 2023-01-31.
- **Combined Validation Sample**: $N = 14,356$ paired scheme-date observations.
- **Development Dates (Reference)**: 2016-01-31 ($N=506$), 2018-01-31 ($N=4,121$), 2020-01-31 ($N=4,137$).

---

## 5. Pre-Registered Decision Grid & Claim Classifications

| Metric / Test | Criteria for EMPIRICALLY_SUPPORTED | Criteria for PARTIALLY_SUPPORTED / REGIME_DEPENDENT |
| :--- | :--- | :--- |
| Incremental $R^2$ (Risk) | $> +0.10\%$ | $> +0.01\%$ |
| Incremental $\beta_2$ (Control) | Statistically significant ($p < 0.05$) with negative sign | Negative sign, but date-clustered $t$ degenerate |
| Forward Risk Correlation | $\rho < -0.10$ across combined validation | $\rho < 0.0$ overall |
| Temporal Consistency | Negative in $3/3$ validation dates | Negative in $2/3$ validation dates |
| Quintile Risk Ordering | Monotonic decrease in risk from $Q_1$ to $Q_5$ | Partially monotonic or weak spread |
