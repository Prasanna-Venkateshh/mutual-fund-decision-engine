# Phase F.11.3.5.1.2 Experiment Manifest

> [!NOTE]
> **Experiment Identification**:
> - **Phase**: F.11.3.5.1.2 Composite Risk-Value Decomposition & Dependence-Aware Validation
> - **Execution Timestamp**: 2026-09-15 (Frozen before empirical execution)
> - **Primary Dataset**: `db/backfill_f12_2.db` (F.12.2, read-only)
> - **Scoring Methodology Version**: 1.0.0 (Frozen — zero production changes permitted)

---

## 1. Purpose & Governance

This manifest pre-registers the hierarchical model sequence and decomposition framework for Phase F.11.3.5.1.2.

### 1.1 Central Research & Audit Questions

1. **Reconstruction**: Can the prior $+1.403\%$ incremental $R^2$ result (Model B vs Model A) be independently reproduced and reconciled?
2. **Model Definition**: What exact variables were in Model A, and how does adding Trailing 1Y Return alter the model decomposition?
3. **Hierarchical Decomposition**:
   - Model 0: Intercept Only
   - Model 1: Trailing 1Y Return
   - Model 2: Trailing 1Y Return + Historical Risk Components (Raw Vol, Raw Downside, Raw MDD)
   - Model 3: Trailing 1Y Return + Historical Risk Components + Control Composite Score
4. **Multicollinearity & Component Construction**: What is the correlation structure between Control and its inputs, and does multicollinearity impact coefficient stability?
5. **Historical Persistence vs Composite Value**: Is Control's risk association driven primarily by historical risk persistence or by composite score transformation?
6. **Dependence-Aware & Outlier Validation**: Does the incremental value survive scheme-clustered SEs, date-equalization, and 1%/99% Winsorization?

### 1.2 Pre-Registered Hierarchical Models

- **Forward Risk Outcomes ($Y$)**: Forward 1Y MDD, Forward 1Y Volatility, Forward 1Y Downside Deviation.
- **Model 0**: $Y = \beta_0 + \varepsilon$
- **Model 1**: $Y = \beta_0 + \beta_1 \cdot \text{Trailing1Y} + \varepsilon$
- **Model 2**: $Y = \beta_0 + \beta_1 \cdot \text{Trailing1Y} + \beta_2 \cdot \text{RawMDD} + \beta_3 \cdot \text{RawVol} + \beta_4 \cdot \text{RawDownside} + \varepsilon$
- **Model 3**: $Y = \beta_0 + \beta_1 \cdot \text{Trailing1Y} + \beta_2 \cdot \text{RawMDD} + \beta_3 \cdot \text{RawVol} + \beta_4 \cdot \text{RawDownside} + \beta_5 \cdot \text{Control} + \varepsilon$

---

## 2. Governance Constraints

- **Empirical Validation Only**: Zero tuning, optimization, promotion, or modification of production scoring methodology.
- **Frozen Production Weights**: Return = 25.0%, Consistency = 20.0%, Volatility = 15.0%, Downside Risk = 15.0%, Max Drawdown = 15.0%, Cost Efficiency = 10.0%.
- **Authoritative Baseline Anchor**: $N = 14,356$, Spearman $\rho = +0.3096$ strictly enforced.
- **No Causal Protection Claims**: Wording must be restricted to "risk-aware" or "associated with lower subsequent risk."
