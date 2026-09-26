# Phase F.11.3.5.1.1 Experiment Manifest

> [!NOTE]
> **Experiment Identification**:
> - **Phase**: F.11.3.5.1.1 Forward-Risk Regression, Economic-Magnitude & Quintile Forensic Audit
> - **Execution Timestamp**: 2026-09-15 (Frozen before empirical execution)
> - **Primary Dataset**: `db/backfill_f12_2.db` (F.12.2, read-only)
> - **Scoring Methodology Version**: 1.0.0 (Frozen — zero production changes permitted)

---

## 1. Purpose & Governance

This manifest pre-registers all forensic audit questions, model specifications, and decision criteria for Phase F.11.3.5.1.1 prior to final result interpretation.

### 1.1 Central Research & Forensic Audit Questions

1. **Reconstruction**: Are all reported F.11.3.5.1 headline correlations, $R^2$ values, and quintile figures 100% independently reproducible?
2. **The 2023 +9.061% Audit**: Why does the 2023 evaluation date exhibit a $+9.061\%$ incremental MDD $R^2$ while the combined 3-year sample exhibits $+1.034\%$? Is this mathematically consistent or a calculation artifact?
3. **Unit & Magnitude Audit**: What is the exact economic magnitude of a 1-point, 10-point, or 1-SD change in Control score on forward MDD, Volatility, and Downside Deviation?
4. **Quintile Forensic Audit**: How are $Q_1$ vs $Q_5$ constructed (pooled vs date-level), what are their exact orientations (highest quality vs lowest quality), and are the extreme risk differences ($0.24\%$ vs $5.42\%$ median MDD) predictive or mechanical?
5. **Predictive vs Mechanical Construction**: Is Control's observed negative association with forward risk a genuine predictive signal or a mechanical reflection of historical risk components (Volatility, Downside, MDD) embedded in its construction?
6. **Date-Equalization & Outlier Robustness**: Does the risk association survive equal-weighting across dates and winsorization/trimming of extreme risk outcomes?

### 1.2 Governance Constraints

- **Empirical Validation Only**: No tuning, optimization, promotion, or modification of production scoring methodology.
- **Frozen Production Weights**: Equity Return = 25.0%, Consistency = 20.0%, Volatility = 15.0%, Downside Risk = 15.0%, Max Drawdown = 15.0%, Cost Efficiency = 10.0%.
- **Authoritative Baseline Anchor**: F.11.3.4.1 baseline ($N = 14,356$, Spearman $\rho = +0.3096$) is strictly enforced.
- **Real-Data Firewall**: All headline empirical results originate from F.12.2 longitudinal NAV data. No synthetic fixtures contribute.
- **No Actionability / Protection Claims**: No investor protection or transaction actionability claims permitted without explicit evidence.

---

## 2. Frozen Methodologies & Outcomes

### 2.1 Score Methodologies Under Test

1. **Control (Production)**: Exact v1.0.0 production weights and formulas.
2. **Trailing 1Y Return**: Authoritative baseline (raw CAGR over trailing $\ge 365$ days).
3. **Historical Risk Components**: Historical Volatility, Downside Deviation, Max Drawdown percentiles.

### 2.2 Forensic Risk Outcomes

1. **Forward 1Y Maximum Drawdown (Forward MDD)**
2. **Forward 1Y Volatility (Forward Vol)**
3. **Forward 1Y Downside Deviation (Forward Downside)**

---

## 3. Pre-Registered Decision & Classification Matrix

| Metric / Audit Test | Criteria for EMPIRICALLY_SUPPORTED | Criteria for PARTIALLY_SUPPORTED / REGIME_DEPENDENT | Criteria for MECHANICALLY_VALIDATED / REJECTED |
| :--- | :--- | :--- | :--- |
| **Independent Reconstruction** | 100% exact numerical match across all metrics | Minor numerical rounding differences | Material unexplained discrepancies |
| **2023 $R^2$ Explanation** | Mathematically verified cross-sectional variance effect | Variance effect confirmed with regime dependency | Calculation error / bug |
| **Incremental Information** | $\Delta R^2 > +0.10\%$, scheme $t < -2.0$ | $\Delta R^2 > +0.01\%$, weak $t$ | $\Delta R^2 \le 0$ or positive beta |
| **Predictive vs Mechanical** | Adds info beyond historical risk components | Partial incremental info beyond components | Entirely explained by historical risk components |
| **Temporal Consistency** | Negative risk association in $3/3$ dates | Negative risk association in $2/3$ dates | Negative in $< 2/3$ dates |
