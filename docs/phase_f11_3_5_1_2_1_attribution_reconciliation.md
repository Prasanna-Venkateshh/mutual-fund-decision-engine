# Phase F.11.3.5.1.2.1 -- Hierarchical R² Attribution & Incremental-Value Reconciliation: Forensic Report

**Phase**: F.11.3.5.1.2.1  
**Status**: COMPLETE  
**Date**: 2026-09-15  
**Dataset**: `db/backfill_f12_2.db` (F.12.2, read-only)  
**Production Methodology**: 100% FROZEN -- zero production changes made  
**Experiment Manifest**: [`docs/phase_f11_3_5_1_2_1_experiment_manifest.md`](phase_f11_3_5_1_2_1_experiment_manifest.md) (frozen before execution)

---

## 0. Executive Summary & Audit Verdict

This phase conducted a narrow, forensic statistical audit of the $R^2$ attribution hierarchy and incremental value claims from Phase F.11.3.5.1.2.

### Key Forensic Audit Results

1. **Exact Reproduction & Reconciliation of $R^2$ Increments**:
   - **Figure 1 ($+1.403\%$)**: Raw Risk Metrics Block $\rightarrow$ Raw Risk Metrics + Control ($18.989\% \rightarrow 20.393\%$). Reconciled as the incremental $R^2$ of Control when Trailing 1Y Return is omitted.
   - **Figure 2 ($+1.034\%$)**: Trailing 1Y Return $\rightarrow$ Trailing 1Y Return + Control ($1.012\% \rightarrow 2.047\%$). Reconciled as the incremental $R^2$ of Control beyond Trailing 1Y Return alone.
   - **Figure 3 ($+0.613\%$)**: Trailing 1Y Return + Raw Risk Block $\rightarrow$ Full Model with Control ($20.365\% \rightarrow 20.978\%$). Reconciled as the true incremental composite contribution of Control beyond BOTH Trailing Return and Raw Risk Metrics.
   - **Verdict**: All three figures are 100% mathematically accurate and reconciled under their respective model design specifications.

2. **Clarification of "97.1%" Claim**:
   - Model 2 $R^2$ (Trailing 1Y + Raw Risk Metrics) $= 20.365\%$.
   - Model 3 $R^2$ (Full Model with Control) $= 20.978\%$.
   - **Ratio**: $20.365 / 20.978 = 97.08\%$.
   - **Correct Interpretation**: Trailing 1Y Return and raw historical risk metrics account for **97.1% of total EXPLAINED model variance** ($20.365\%$ out of $20.978\%$).
   - **Critical Caveat**: **79.022% of total forward max drawdown variance remains completely unexplained** by Model 3.

---

## 1. Complete Hierarchical $R^2$ Attribution Table ($N = 14,356$)

| Risk Outcome | Model 0 (Intercept) | Model 1 (+ Trailing 1Y) | Trailing 1Y Inc ($\Delta R^2$) | Model 2 (+ Raw Risk Block) | Risk Block Inc ($\Delta R^2$) | Model 3 (+ Control) | Control Inc ($\Delta R^2$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Forward 1Y MDD** | 0.000% | 1.012% | $+1.012\%$ | **20.365%** | **$+19.352\%$** | **20.978%** | **$+0.613\%$** |
| **Forward 1Y Volatility** | 0.000% | 0.017% | $+0.017\%$ | **2.620%** | **$+2.603\%$** | **2.679%** | **$+0.059\%$** |
| **Forward 1Y Downside** | 0.000% | 0.300% | $+0.300\%$ | **11.225%** | **$+10.925\%$** | **11.901%** | **$+0.675\%$** |

---

## 2. Shared Variance Breakdown (Forward Max Drawdown)

| Factor Block | Incremental $R^2$ Contribution | Share of Explained Variance (Model 3 $R^2 = 20.978\%$) | Share of Total Forward Risk Variance |
| :--- | :--- | :--- | :--- |
| **Trailing 1Y Return** | $+1.012\%$ | $4.82\%$ | $1.01\%$ |
| **Raw Historical Risk Metrics** | $+19.352\%$ | **$92.25\%$** | **$19.35\%$** |
| **Control Composite Score** | $+0.613\%$ | **$2.92\%$** | **$0.61\%$** |
| **Unexplained Variance** | N/A | N/A | **79.02%** |

---

## 3. Claim Reconciliation Matrix & Safe Investor Wording

| Claim | Previous Wording | Reconciled Forensic Finding | Status | Safe Investor Wording |
| :--- | :--- | :--- | :--- | :--- |
| **"97.1% Persistence"** | "Raw risk metrics explain 97.1% of forward risk." | Model 2 accounts for $97.1\%$ of *explained model variance*, while $79.0\%$ of total variance is unexplained. | **SUPERSEDED — INTERPRETATION TOO STRONG** | "Historical risk metrics represent 97.1% of the total explained model variance, though 79.0% of forward drawdown variance is unexplained." |
| **Incremental Control Gain** | "Control adds +1.403% / +1.034% / +0.613%." | All 3 figures verified: $+1.403\%$ vs raw risk alone; $+1.034\%$ vs trailing return alone; $+0.613\%$ vs full model. | **EMPIRICALLY_SUPPORTED** | "Control composite score adds a $+0.613\%$ incremental $R^2$ beyond trailing return and raw historical risk metrics." |
| **Causal Protection** | "Control protects investors." | Unvalidated. Association only. | **REJECTED / UNVALIDATED** | Do NOT use "guaranteed protection" or "causal drawdown reduction." |

---

## 4. Final Approved Status Selection

```
PHASE F.11.3.5.1.2.1 PASSED WITH LIMITATIONS — RECONCILIATION COMPLETE
```
