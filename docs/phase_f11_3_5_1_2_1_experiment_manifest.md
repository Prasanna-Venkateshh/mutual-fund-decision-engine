# Phase F.11.3.5.1.2.1 Experiment Manifest

> [!NOTE]
> **Experiment Identification**:
> - **Phase**: F.11.3.5.1.2.1 Hierarchical R² Attribution & Incremental-Value Reconciliation
> - **Execution Timestamp**: 2026-09-15 (Frozen before empirical execution)
> - **Primary Dataset**: `db/backfill_f12_2.db` (F.12.2, read-only)
> - **Scoring Methodology Version**: 1.0.0 (Frozen — zero production changes permitted)

---

## 1. Purpose & Governance

This manifest pre-registers all forensic audit questions, model specifications, and reconciliation rules for Phase F.11.3.5.1.2.1 prior to empirical execution and interpretation.

### 1.1 Central Research & Audit Questions

1. **Exact $R^2$ Attribution Reconciliation**: What are the exact $R^2$ contributions of:
   - Trailing 1Y Return ($\text{Model 1} - \text{Model 0}$)
   - Raw Historical Risk Metrics ($\text{Model 2} - \text{Model 1}$)
   - Control Composite Score ($\text{Model 3} - \text{Model 2}$)
2. **Reconciliation of Prior Discrepancies**:
   - Why did Phase F.11.3.5.1.1 report $+1.403\%$ incremental $R^2$ while Phase F.11.3.5.1.2 reported $+0.613\%$?
   - Mathematical proof: Model A in F.11.3.5.1.1 omitted Trailing 1Y Return ($R^2 = 18.989\% \rightarrow 20.393\%$, $\Delta R^2 = +1.403\%$). Model 2 in F.11.3.5.1.2 included Trailing 1Y Return ($R^2 = 20.365\% \rightarrow 20.978\%$, $\Delta R^2 = +0.613\%$).
3. **Clarification of "97.1%" Claim**:
   - $20.365 / 20.978 = 97.08\%$ represents the share of total explainable model $R^2$ captured by Trailing 1Y Return + Raw Risk Metrics.
   - It does NOT mean $97.1\%$ of total future risk is explained (since total $R^2$ is $\sim 21\%$, leaving $\sim 79\%$ unexplained variance).
4. **Dependence-Aware & Robustness Audits**:
   - Scheme-clustered standard error evaluation across all models.
   - Date-equalized weighting sensitivity.
   - 1%/99% Winsorization sensitivity.

### 1.2 Governance Constraints

- **Empirical Validation Only**: No tuning, optimization, promotion, or modification of production scoring methodology.
- **Frozen Production Weights**: Return = 25.0%, Consistency = 20.0%, Volatility = 15.0%, Downside Risk = 15.0%, Max Drawdown = 15.0%, Cost Efficiency = 10.0%.
- **Authoritative Baseline Anchor**: $N = 14,356$, Spearman $\rho = +0.3096$ strictly enforced.
- **No Causal Protection Claims**: Permitted wording restricted to "risk-aware structural sorting."
