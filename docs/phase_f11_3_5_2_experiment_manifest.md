# Phase F.11.3.5.2 Experiment Manifest

> [!NOTE]
> **Experiment Identification**:
> - **Phase**: F.11.3.5.2 Out-of-Sample Control Incremental Value & Economic Decision Validation
> - **Execution Timestamp**: 2026-09-15 (Frozen before empirical execution)
> - **Primary Dataset**: `db/backfill_f12_2.db` (F.12.2, read-only)
> - **Scoring Methodology Version**: 1.0.0 (Frozen — zero production changes permitted)

---

## 1. Purpose & Governance

This manifest pre-registers all out-of-sample evaluation partitions, primary hierarchical model specifications, economic decision simulation rules, and decision gates for Phase F.11.3.5.2 prior to empirical execution and interpretation.

### 1.1 Central Research Questions

1. **OOS Replicability**: Does the $+0.613\%$ incremental $R^2$ contribution of Control beyond Trailing 1Y Return and raw historical risk metrics persist across individual out-of-sample evaluation dates (2021, 2022, 2023)?
2. **Economic Decision Value**: Does selecting top-quartile funds using Control improve forward risk outcomes (reducing max drawdown / volatility) relative to a simple Trailing 1Y Return ranking or raw historical risk ranking?
3. **Turnover / Churn**: Does a decision rule based on Control produce acceptable portfolio churn across consecutive evaluation dates compared to Trailing 1Y Return?
4. **Regime & Robustness**: Is the incremental value stable under date-equalized weighting, 1%/99% Winsorization, category family stratification, and maturity partitioning?

### 1.2 Governance Constraints

- **Empirical Validation Only**: Zero tuning, optimization, promotion, or modification of production scoring methodology.
- **Frozen Production Weights**: Return = 25.0%, Consistency = 20.0%, Volatility = 15.0%, Downside Risk = 15.0%, Max Drawdown = 15.0%, Cost Efficiency = 10.0%.
- **Authoritative Baseline Anchor**: $N = 14,356$, Spearman $\rho = +0.3096$ strictly enforced.
- **Real-Data Firewall**: All headline empirical results originate from F.12.2 longitudinal NAV data. No synthetic fixtures contribute.
- **No Causal Protection Claims**: Wording restricted to "risk-aware structural sorting" or "associated with lower subsequent risk."

---

## 2. Frozen Methodologies & Models

### 2.1 Score Methodologies Under Test

1. **Control (Production)**: Exact v1.0.0 production weights and formulas.
2. **Trailing 1Y Return**: Authoritative baseline (raw CAGR over trailing $\ge 365$ days).
3. **Historical Risk Block**: Raw Volatility, Raw Downside Deviation, Raw Max Drawdown.

### 2.2 Hierarchical 4-Stage Models

- **Model 0**: $Y = \beta_0 + \varepsilon$
- **Model 1**: $Y = \beta_0 + \beta_1 \cdot \text{Trailing1Y} + \varepsilon$
- **Model 2**: $Y = \beta_0 + \beta_1 \cdot \text{Trailing1Y} + \beta_2 \cdot \text{RawMDD} + \beta_3 \cdot \text{RawVol} + \beta_4 \cdot \text{RawDownside} + \varepsilon$
- **Model 3**: $Y = \beta_0 + \beta_1 \cdot \text{Trailing1Y} + \beta_2 \cdot \text{RawMDD} + \beta_3 \cdot \text{RawVol} + \beta_4 \cdot \text{RawDownside} + \beta_5 \cdot \text{Control} + \varepsilon$

### 2.3 Economic Decision Simulation Protocol

- **Selection Rule**: Top-quartile (Top 25%) selection by:
  - Strategy A: Trailing 1Y Return
  - Strategy B: Raw Risk Block (Lowest Vol/MDD)
  - Strategy C: Control Composite Score
- **Outcomes Evaluated**: Forward 1Y Max Drawdown, Forward 1Y Volatility, Forward 1Y Return.
- **Turnover Measurement**: Jaccard similarity and overlap stability between selected cohorts across consecutive evaluation dates (2021 $\rightarrow$ 2022 and 2022 $\rightarrow$ 2023).

---

## 3. Pre-Registered Decision & Classification Matrix

| Metric / Audit Test | Criteria for EMPIRICALLY_SUPPORTED | Criteria for PARTIALLY_SUPPORTED / REGIME_DEPENDENT | Criteria for INCREMENTAL_VALUE_NOT_DEMONSTRATED |
| :--- | :--- | :--- | :--- |
| **OOS $\Delta R^2$ Persistence** | Control $\Delta R^2 > +0.10\%$ in $3/3$ dates | Control $\Delta R^2 > +0.10\%$ in $2/3$ dates | Control $\Delta R^2 \le 0$ or unstable sign |
| **Decision Risk Reduction** | Control Top 25% Forward MDD < Trailing 1Y Top 25% | Control Top 25% Forward MDD $\le$ Trailing 1Y Top 25% | Control Top 25% Forward MDD > Trailing 1Y Top 25% |
| **Turnover Stability** | Overlap $> 50\%$ across dates | Overlap $30\% - 50\%$ across dates | Overlap $< 30\%$ (excessive churn) |
