# Phase F.11.3.5.2.1 Experiment Manifest

> [!NOTE]
> **Experiment Identification**:
> - **Phase**: F.11.3.5.2.1 OOS Status, Risk-Value & Decision-Simulation Forensic Reconciliation
> - **Execution Timestamp**: 2026-09-15 (Frozen before empirical execution)
> - **Primary Dataset**: `db/backfill_f12_2.db` (F.12.2, read-only)
> - **Scoring Methodology Version**: 1.0.0 (Frozen — zero production changes permitted)

---

## 1. Purpose & Governance

This manifest pre-registers all forensic audit questions, chronology tracking tables, mathematical variance decomposition steps, and claim reconciliation rules for Phase F.11.3.5.2.1.

### 1.1 Central Research & Audit Questions

1. **Chronology & True OOS Classification**: Were the 2021-2023 evaluation dates used in earlier empirical work (F.11.3.4, F.11.3.5)? If so, are they correctly classified as *Replication of Prior Validation Sample* rather than *Independent Unseen OOS*?
2. **Reconciliation of the 2022 $+4.788\%$ Result**: Why did 2022 exhibit a $+4.788\%$ Control incremental $R^2$ compared to $+0.101\%$ in 2021 and $+0.594\%$ in 2023? (Mathematical variance audit).
3. **Reconciliation of Decision Simulation**: Does Control (Strategy C) add decision value beyond the Raw Risk Block (Strategy B)?
4. **Turnover & Churn Clarification**: Is the reported $73.4\%$ turnover figure an annual cohort membership turnover proxy ($100\% - 26.6\%$ Jaccard overlap)?
5. **Causal Wording Audit**: Audit and retire prohibited causal claims ("protects investors", "reduces drawdown") and replace with safe descriptive wording.

### 1.2 Governance Constraints

- **Empirical Validation Only**: Zero tuning, optimization, promotion, or modification of production scoring methodology.
- **Frozen Production Weights**: Return = 25.0%, Consistency = 20.0%, Volatility = 15.0%, Downside Risk = 15.0%, Max Drawdown = 15.0%, Cost Efficiency = 10.0%.
- **Authoritative Baseline Anchor**: $N = 14,356$, Spearman $\rho = +0.3096$ strictly enforced.
- **Real-Data Firewall**: All headline empirical results originate from F.12.2 longitudinal NAV data. No synthetic fixtures contribute.
