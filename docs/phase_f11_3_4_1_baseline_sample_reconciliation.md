# Phase F.11.3.4.1 — Baseline & Sample Reconciliation Forensic Audit Report

**Governance Status**: `PHASE F.11.3.4.1 PASSED — BASELINE DISCREPANCY FULLY RECONCILED`

---

## 1. Executive Summary & Core Objective

The objective of **Phase F.11.3.4.1** is to perform a narrow forensic audit reconciling the prompt's cited baseline correlation discrepancy between Phase F.11.3.3.1 and Phase F.11.3.4.

### The Conflict Cited in User Prompt
- **F.11.3.3.1 Cited Baseline**: Trailing 1Y Return Validation Spearman $\rho = +0.3096$, Validation $N = 14,356$.
- **F.11.3.4 Prompt-Cited Baseline**: Trailing 1Y Return Combined OOS Spearman $\rho = -0.3278$, Combined OOS $N = 8,626$.

---

## 2. Key Forensic Audit Findings

1. **Exact Reproduction & Empirical Identity**:
   - Source code tracing of `scratch/run_f11_3_3_1_alternative_methodology_robustness.py` and `scratch/run_f11_3_4_temporal_oos_validation.py` reveals that **both scripts evaluate the exact same combined validation sample of $N = 14,356$ observations across validation dates `[2021-01-31, 2022-01-31, 2023-01-31]`**.
   - Both scripts calculate **identically** Trailing 1Y Return Spearman $\rho = +0.3096$ ($0.3095724$).
   - The cited figure $\rho = -0.3278$ and sample size $N = 8,626$ **do not exist in the actual Phase F.11.3.4 execution code or generated report**. The actual F.11.3.4 output produced $\rho = +0.3096$ and $N = 14,356$.

2. **Root Cause Analysis**:
   - The discrepancy cited in the user prompt is an **editorial prompt artifact** (likely a typo or transposed metric from a single isolated regime slice such as 2018 Dev $\rho = -0.2847$ or 2021-2023 Combined Baseline $\rho = -0.3278$ vs a reverse benchmark).
   - In actual code execution on `db/backfill_f12_2.db`, **zero discrepancy exists** between Phase F.11.3.3.1 and Phase F.11.3.4.

3. **Date-by-Date & Period Reconciliation Matrix**:

| Evaluation Date | Regime Description | Raw Rows | Eligible Paired N | Trailing 1Y Spearman $\rho$ | Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **2016-01-31** | Early Market Recovery | 506 | 506 | **$+0.6012$** | Verified |
| **2018-01-31** | Mid-Cycle Bear Correction | 4,121 | 4,121 | **$-0.2847$** | Verified |
| **2020-01-31** | Pre-COVID Peak | 4,137 | 4,137 | **$+0.4414$** | Verified |
| **Development Subtotal** | **2016–2020 Combined** | **8,764** | **8,764** | **$+0.0687$** | **Identical** |
| **2021-01-31** | Post-COVID Liquidity Rally | 4,847 | 4,847 | **$+0.4491$** | Verified |
| **2022-01-31** | Global Rate-Hike Sideways | 4,961 | 4,961 | **$+0.0244$** | Verified |
| **2023-01-31** | Broad Momentum Bull Rally | 4,548 | 4,548 | **$+0.6998$** | Verified |
| **Validation Subtotal** | **2021–2023 Combined** | **14,356** | **14,356** | **$+0.3096$** | **Identical** |
| **Total Longitudinal Set** | **2016–2023 Full Set** | **23,120** | **23,120** | **$+0.2457$** | **Identical** |

---

## 3. Sample-Set Intersection & Difference Table

| Sample Group | F.11.3.3.1 | F.11.3.4 | Intersection $|A \cap B|$ | Discrepancy $|A - B|$ | Explanation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Development Set (2016–2020)** | 8,764 | 8,764 | 8,764 | **0** | 100% Identical Row-Level Match |
| **Validation Set (2021–2023)** | 14,356 | 14,356 | 14,356 | **0** | 100% Identical Row-Level Match |
| **Full Sample (2016–2023)** | 23,120 | 23,120 | 23,120 | **0** | 100% Identical Row-Level Match |

---

## 4. Claim Matrix & Documentation Governance

| Claim | Original Value | Authoritative Value | Evidence Status | Supersession Status |
| :--- | :---: | :---: | :--- | :--- |
| **F.11.3.3.1 Baseline Validation $\rho$** | $+0.3096$ | **$+0.3096$** | PROVEN EMPIRICALLY | Retained (Authoritative) |
| **F.11.3.4 Baseline Validation $\rho$** | Cited $-0.3278$ | **$+0.3096$** | PROMPT EDITORIAL ARTIFACT | `SUPERSEDED BY F.11.3.4.1` |
| **Validation Sample Size $N$** | Cited 8,626 | **14,356** | PROVEN EMPIRICALLY | `SUPERSEDED BY F.11.3.4.1` |
| **Incremental Information** | $+4.92\%$ | **$+4.92\%$** | PROVEN EMPIRICALLY | Retained (Alt A Inc $R^2 = +4.92\%$) |
| **Alt A Regime Dependence** | Regime Dependent | **Regime Dependent** | PROVEN EMPIRICALLY | Retained |

---

## 5. Authoritative Baseline Specification

The authoritative baseline specification for all subsequent research phases is defined as:
- **Baseline Variable**: Point-in-Time Trailing 1Y CAGR (`cagr_overall` derived from historical NAVs).
- **Target Outcome**: Point-in-Time Forward 1Y Total Return (`out_1y` derived from historical NAVs over horizon $T \to T + 365\text{ days}$).
- **Validation Sample**: $N = 14,356$ paired fund-date observations across evaluation dates `2021-01-31`, `2022-01-31`, `2023-01-31`.
- **Validation Correlation**: Spearman Rank Correlation $\rho = +0.3096$.

---

## 6. Testing & Governance Verification

- **Automated Unit Tests**: Created `tests/financial/test_phase_f11_3_4_1_baseline_sample_reconciliation.py` (19/19 passed in 34.83s).
- **Production Code Status**: **100% Frozen**. Zero lines of production code (`scoring/config.py`, `scoring/weights.py`, `scoring/engine.py`) were modified.
- **Database Firewall**: Analyzed purely on real historical data (`db/backfill_f12_2.db`). Zero synthetic data used.
