# Phase F.11.3.5.1.1 -- Forward-Risk Regression, Economic-Magnitude & Quintile Forensic Audit: Comprehensive Report

**Phase**: F.11.3.5.1.1  
**Status**: COMPLETE  
**Date**: 2026-09-15  
**Dataset**: `db/backfill_f12_2.db` (F.12.2, read-only)  
**Production Methodology**: 100% FROZEN -- zero production changes made  
**Experiment Manifest**: [`docs/phase_f11_3_5_1_1_experiment_manifest.md`](phase_f11_3_5_1_1_experiment_manifest.md) (frozen before execution)

---

## 0. Executive Summary & Forensic Audit Verdict

This forensic audit performed an independent mathematical and statistical reconstruction of all empirical forward-risk claims produced in Phase F.11.3.5.1.

### Key Forensic Findings

1. **Independent Reproduction**: All F.11.3.5.1 headline numbers were **100% independently reproduced** from the raw longitudinal NAV dataset (`db/backfill_f12_2.db`, $N = 14,356$).
2. **The 2023 $+9.061\%$ $R^2$ Reconciliation**: The large incremental MDD $R^2$ in 2023 ($+9.061\%$ vs combined $+1.034\%$) is **mathematically verified**. It is driven by cross-sectional outcome variance: total sum of squares (SST) in 2023 was only $7.444$ (variance $= 0.0016$) compared to combined SST of $73.253$ (variance $= 0.0051$). The absolute reduction in residual sum of squares (SSR) contributed by Control was nearly identical ($0.675$ in 2023 vs $0.758$ combined), demonstrating that the higher $R^2$ percentage is a low-variance denominator effect rather than a calculation anomaly.
3. **Coefficient Unit & Magnitude Audit**: Control is measured on a $[0, 100]$ percentile scale (Mean $= 48.95$, SD $= 14.02$).
   - A **10-point Control score increase** is associated with a **$-0.55\%$ reduction in forward max drawdown** ($\beta_2 = -0.000551$) and a **$-0.96\%$ reduction in forward volatility** ($\beta_2 = -0.000958$).
   - A **1-SD (14.0 pt) Control score increase** is associated with a **$-0.77\%$ reduction in forward max drawdown**.
4. **Predictive vs Mechanical Audit**: Control is **partially predictive beyond its raw components**. When controlling for raw historical max drawdown, raw volatility, and raw downside deviation, Control contributes an **incremental $R^2$ of $+1.403\%$** ($t = 15.91$, $p < 0.0001$).
5. **Quintile Reconstruction & Orientation**: $Q_1 = \text{Highest Quality Score}$, $Q_5 = \text{Lowest Quality Score}$. Whether constructed on a pooled sample or within evaluation-date cohorts, $Q_1$ funds exhibit lower median forward max drawdown (**0.24%--0.26% vs 4.86%--5.42%**) and lower median volatility (**0.57%--0.69% vs 6.69%--7.45%**) than $Q_5$ funds.
6. **Outlier & Date Robustness**: Incremental risk explanatory power survives 1%/99% Winsorization ($\Delta R^2 = +0.965\%$, $t_{\text{scheme}} = -7.45$) and date-equalization.

---

## 1. Numerical Reconciliation Matrix

| Claim / Metric | F.11.3.5.1 Reported | F.11.3.5.1.1 Reconstructed | Match Status | Forensic Finding |
| :--- | :--- | :--- | :--- | :--- |
| **Combined Validation Sample $N$** | 14,356 | 14,356 | **EXACT MATCH** | Authoritative sample verified |
| **Trailing 1Y Forward Return $\rho$** | +0.3096 | +0.3096 | **EXACT MATCH** | F.11.3.4.1 baseline anchor verified |
| **Control Forward MDD $\rho$** | -0.1730 | -0.1730 | **EXACT MATCH** | Correlation verified |
| **Control Forward Volatility $\rho$** | -0.1969 | -0.1969 | **EXACT MATCH** | Correlation verified |
| **Combined MDD Base $R^2$** | 1.012% | 1.012% | **EXACT MATCH** | Model A verified |
| **Combined MDD Full $R^2$** | 2.047% | 2.047% | **EXACT MATCH** | Model B verified |
| **Combined MDD Incremental $R^2$** | +1.034% | +1.034% | **EXACT MATCH** | $\Delta R^2$ verified ($t = -7.11$) |
| **2021 MDD Incremental $R^2$** | +3.065% | +3.065% | **EXACT MATCH** | 2021 date model verified |
| **2022 MDD Incremental $R^2$** | +0.216% | +0.216% | **EXACT MATCH** | 2022 date model verified |
| **2023 MDD Incremental $R^2$** | +9.061% | +9.061% | **EXACT MATCH** | 2023 date model verified |
| **$Q_1$ Median Forward MDD (Pooled)** | 0.24% | 0.2377% | **EXACT MATCH** | Rounded in prior text |
| **$Q_5$ Median Forward MDD (Pooled)** | 5.42% | 5.4178% | **EXACT MATCH** | Rounded in prior text |

---

## 2. Mathematical Breakdown of the 2023 $+9.061\%$ Result

The 2023 evaluation date exhibited an incremental $R^2$ of $+9.061\%$, whereas the combined 3-year validation sample showed $+1.034\%$. Forensic decomposition confirms this is mathematically consistent:

$$\text{SST}_{2023} = \sum (Y_{2023} - \bar{Y}_{2023})^2 = 7.4441 \quad (\text{Variance} = 0.001637)$$
$$\text{SST}_{\text{Combined}} = \sum (Y_{\text{Combined}} - \bar{Y}_{\text{Combined}})^2 = 73.2530 \quad (\text{Variance} = 0.005103)$$

$$\Delta \text{SSR}_{2023} = \text{SSR}_{\text{Base}} - \text{SSR}_{\text{Full}} = 0.6745$$
$$\Delta \text{SSR}_{\text{Combined}} = \text{SSR}_{\text{Base}} - \text{SSR}_{\text{Full}} = 0.7577$$

- **Conclusion**: The absolute variance reduction provided by Control in 2023 ($0.6745$) is comparable to the combined sample ($0.7577$). However, because 2023 was a low-volatility market environment with a tiny denominator ($\text{SST} = 7.444$), the ratio $\Delta \text{SSR} / \text{SST}$ scales to $+9.061\%$. The combined sample includes 2021 and 2022 where total risk variance was substantially higher ($\text{SST} = 73.253$).

---

## 3. Coefficient Unit & Practical Economic-Magnitude Audit

Control score is expressed on a scale of $0.0$ to $100.0$ (Percentile Rank Composite).

| Change in Control Score | Forward MDD Change ($\beta_2 = -0.000551$) | Forward Volatility Change ($\beta_2 = -0.000958$) | Economic Practical Impact |
| :--- | :--- | :--- | :--- |
| **+1 Point** | **$-0.0551\%$** | **$-0.0958\%$** | Small individual shift |
| **+10 Points** | **$-0.551\%$** | **$-0.958\%$** | Moderate risk reduction |
| **+1 SD (+14.0 Points)** | **$-0.772\%$** | **$-1.343\%$** | Material risk reduction |
| **Quintile Spread ($Q_1$ vs $Q_5$)** | **$-5.18\%$ (Median)** | **$-6.88\%$ (Median)** | Substantial distributional separation |

- **Investor-Facing Translation**: Moving up 10 percentile points in Control score reduces expected forward 1Y maximum drawdown by approximately $0.55\%$ percentage points and forward annualized volatility by $0.96\%$ percentage points.

---

## 4. Mechanical vs Predictive Construction Audit

Does Control add genuine forward-risk information beyond its raw component inputs (raw historical MDD, Volatility, Downside Deviation)?

- **Model A (Raw Historical Risk Metrics)**: $Y_{\text{FwdMDD}} \sim \text{Intercept} + \text{RawMDD} + \text{RawVol} + \text{RawDownside}$  
  $\longrightarrow R^2 = 18.989\%$
- **Model B (Raw Risk Metrics + Control Score)**: $Y_{\text{FwdMDD}} \sim \text{Intercept} + \text{RawMDD} + \text{RawVol} + \text{RawDownside} + \text{Control}$  
  $\longrightarrow R^2 = 20.393\%$  
  $\Delta R^2 = \mathbf{+1.403\%} \quad (t_{\text{OLS}} = 15.91, p < 0.0001)$

- **Conclusion**: Control is **not purely mechanical**. The cross-sectional percentile normalization and multi-dimensional weighting structure provide $+1.403\%$ incremental explanatory value beyond simply using raw historical volatility, downside, and drawdown directly.

---

## 5. Required Explicit Answers (A -- V)

- **A. Were all major F.11.3.5.1 numerical results independently reproduced?**  
  **YES.** 100% exact numerical match across all headline correlations, $R^2$ values, and quintiles.

- **B. Is the +1.034% combined MDD ΔR² correct?** **YES.**

- **C. Is the +0.254% volatility ΔR² correct?** **YES.**

- **D. Is the +0.482% downside ΔR² correct?** **YES.**

- **E. Is the 2023 +9.061% MDD ΔR² correct?** **YES.**

- **F. Why does 2023 differ so dramatically from the combined result?**  
  Driven by low cross-sectional outcome variance ($\text{SST} = 7.44$ in 2023 vs $73.25$ combined). Absolute SSR reduction was nearly equal ($0.675$ vs $0.758$).

- **G. Does Control add forward MDD information beyond trailing 1Y return?** **YES.** ($\Delta R^2 = +1.034\%$, $t_{\text{scheme}} = -7.11$).

- **H. Does Control add forward volatility information beyond trailing 1Y return?** **YES.** ($\Delta R^2 = +0.254\%$, $t_{\text{scheme}} = -6.63$).

- **I. Does Control add forward downside information beyond trailing 1Y return?** **YES.** ($\Delta R^2 = +0.482\%$, $t_{\text{scheme}} = -5.39$).

- **J. Does that incremental information survive dependence-aware inference?** **YES.** Scheme-clustered $t$-stats remain $<-5.0$.

- **K. Does it survive date-equalization?** **YES.** All 3 evaluation dates show negative Control betas.

- **L. Does it survive actual outlier sensitivity?** **YES.** 1%/99% Winsorization yields $\Delta R^2 = +0.965\%$ ($t = -7.45$).

- **M. Does it survive reasonable category/maturity analysis?** **YES.** Holds within Equity schemes and Mature/Young scheme subsets.

- **N. Is the Q1/Q5 MDD difference predictive, mechanical, or mixed?**  
  **MIXED.** Heavy historical risk weighting creates an intentional structural risk filter, which translates into $+1.403\%$ predictive power beyond raw components.

- **O. Is the Q1/Q5 volatility difference predictive, mechanical, or mixed?** **MIXED.** Same multi-dimensional percentile normalization mechanism.

- **P. Is the economic magnitude genuinely meaningful?** **YES.** $-0.55\%$ MDD reduction per 10-point score increase.

- **Q. Is Control demonstrably risk-aware?** **YES.**

- **R. Is Control demonstrably risk-protective?** **PARTIALLY SUPPORTED.** Negative association with forward risk is confirmed, but no causal or action engine intervention claims may be made.

- **S. Does the evidence justify any investor-facing claim about risk reduction?**  
  **YES**, using safe wording: *"Higher Control Fund Quality scores are consistently associated with lower subsequent drawdown and volatility."*

- **T. Does the evidence justify changing production methodology?** **NO.** Production weights remain 100% frozen.

- **U. What remains uncertain?** Longer-horizon (3Y/5Y) risk discipline during extended market panics.

- **V. What is the narrowest next validation, if any?** Multi-year (3Y forward) risk discipline validation on 2021 cohort.

---

## 6. Final Approved Status

```
PHASE F.11.3.5.1.1 PASSED — FORWARD-RISK EVIDENCE VERIFIED
```
