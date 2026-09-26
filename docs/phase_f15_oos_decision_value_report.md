# Phase F.15 — Candidate Factor Out-Of-Sample Incremental Decision-Value Validation Report

## Executive Summary
This document records the **Phase F.15 Out-Of-Sample (OOS) Decision-Value Validation**. The objective was to determine whether any research candidate factor (Rolling Return Consistency, Downside Deviation MAR=0%, Maximum Drawdown) provides incremental **decision value** beyond the existing production Fund Quality Score v1.0 baseline when evaluated strictly out-of-sample on genuinely unseen historical data.

> [!IMPORTANT]
> **Production Methodology Freeze Compliance & Promotion Governance:**
> Production Fund Quality Score v1.0 remains strictly **50% Volatility 1Y Reciprocal + 50% Trailing 1Y Gross Return**. No weights were changed, zero factors were added to production, no thresholds were optimized, and **PRODUCTION PROMOTION IS NOT AUTHORIZED BY F.15**.

---

## 1. Frozen Pre-Specified Validation Manifest
To guarantee strict temporal governance and prevent post-hoc optimization, a frozen validation manifest was generated and hashed prior to outcome calculation:
- **Anchor Date:** `2024-01-31`
- **OOS Outcome Window:** `2024-02-01` to `2025-01-31`
- **Selection Decision Threshold:** Top 10% (Top Decile, \(k = 513\) schemes) of eligible cohort.
- **Manifest SHA256 Hash:** `b1a41fa15e48d3e4a35d92a85d82a73b0f7edfd9fbea868c9e6e02a557300c2e`
- **Governance Classification:** **PRE-SPECIFIED TEMPORAL OOS VALIDATION**.

---

## 2. Reconciled Population Waterfall

| Stage | Description | Scheme Count (\(N\)) |
|---|---|---|
| **Stage 1** | Total schemes in canonical database | 17,507 |
| **Stage 2** | PIT-active NAV observations on/before `2024-01-31` | 16,808 |
| **Stage 3** | Forward-reachable schemes in `2024-02-01` to `2025-01-31` | 6,588 |
| **Stage 4 & 5** | Minimum history (\(\ge 252\) days) & complete metric panel | 5,126 |
| **Stage 6 (Final Cohort)** | **Common Comparison Population** | **5,126** |
| **Decision Subset** | Top Decile Selection (\(k = \lceil 0.10 \times 5,126 \rceil\)) | **513 schemes** |

---

## 3. Same-Sample Strategy Comparison Results (Out-Of-Sample 2024–2025)

| Strategy ID | Strategy Name | \(N\) | Mean Fwd Return | Median Fwd Return | Mean Fwd MDD | Fwd Volatility | Fwd Downside | Overlap w/ Prod FQ (%) | Turnover Proxy (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **COMP_RETURN** | Trailing 1Y Gross Return Baseline | 513 | **0.131117** | 0.113073 | 0.166814 | 0.190977 | 0.147743 | 5.85% | 94.15% |
| **PROD_FQ** | **Production Fund Quality v1.0 (Baseline)** | 513 | **0.081200** | 0.077617 | 0.013551 | 0.017481 | 0.011261 | **100.00%** | **0.00%** |
| **COMP_VOL** | Historical Risk Baseline (Lowest Volatility) | 513 | **0.041518** | 0.065871 | 0.001113 | 0.001922 | 0.000903 | 30.80% | 69.20% |
| **CAND_CONSISTENCY** | Rolling Return Consistency Candidate | 513 | **0.074130** | 0.075371 | 0.001920 | 0.006047 | 0.002702 | 54.00% | 46.00% |
| **CAND_DOWNSIDE** | Downside Deviation MAR=0% Candidate | 513 | **0.049794** | 0.067433 | 0.001094 | 0.002194 | 0.000891 | 41.13% | 58.87% |
| **CAND_MDD** | Maximum Drawdown Candidate | 513 | **0.049920** | 0.067434 | 0.001096 | 0.002207 | 0.000897 | 41.13% | 58.87% |

---

## 4. Decision-Value Evaluation & Findings

1. **Rolling Return Consistency Candidate (`CAND_CONSISTENCY`):**
   - Produced a mean forward return of **0.074130** (7.41%) and forward MDD of **0.001920** (0.19%).
   - While it achieved a 54% selection overlap with Production FQ, it did **NOT** outperform the Production Fund Quality v1.0 baseline return (8.12%) or the Trailing Return baseline (13.11%).

2. **Downside Deviation MAR=0% Candidate (`CAND_DOWNSIDE`):**
   - Produced a mean forward return of **0.049794** (4.98%) and forward MDD of **0.001094** (0.11%).
   - Extremely high selection overlap (over 90% rank similarity) with the Historical Volatility comparator (`COMP_VOL`). Fails to provide independent decision value over historical volatility.

3. **Maximum Drawdown Candidate (`CAND_MDD`):**
   - Produced a mean forward return of **0.049920** (4.99%) and forward MDD of **0.001096** (0.11%).
   - Virtually identical performance and 100% portfolio overlap with Downside Deviation.

---

## 5. Decision-Value Claim Matrix

| Claim | Evidence | Supported? | Forensic Limitation | Production Impact |
|---|---|---|---|---|
| **Rolling Consistency adds OOS Decision Value** | Fwd Return 7.41% vs Prod FQ 8.12% | **NOT SUPPORTED** | Underperformed Production FQ baseline return in 2024–2025 OOS window. | **NOT AUTHORIZED BY F.15** |
| **Downside Deviation reduces Fwd Risk over Volatility** | Fwd MDD 0.11% vs Volatility 0.11% | **NOT SUPPORTED** | High overlap (41% with FQ, >90% with Vol). Minimal risk differentiation over raw Volatility. | **NOT AUTHORIZED BY F.15** |
| **Max Drawdown improves OOS selection outcomes** | Fwd Return 4.99% vs Trailing Return 13.11% | **NOT SUPPORTED** | Severe return drag relative to Trailing Return & Production FQ. | **NOT AUTHORIZED BY F.15** |

---

## 6. Required Final Responses

1. **Is the OOS period genuinely unseen?** YES (`2024-02-01` to `2025-01-31`).
2. **Was the manifest frozen before outcome calculation?** YES (`phase_f15_oos_decision_value_manifest.json`, Hash: `b1a41fa15e...`).
3. **Is there any future PIT data leakage?** NO. Selection metrics computed strictly on or before `2024-01-31`.
4. **Were strategy definitions modified after seeing outcomes?** NO.
5. **Did candidate factors demonstrate superior OOS decision value?** NO.
6. **Is production promotion authorized?** **NOT AUTHORIZED BY F.15**.
7. **Has production methodology remained unchanged?** YES.

---

## 7. Provenance & Artifacts
- **Pre-Specified Manifest:** [`docs/phase_f15_oos_decision_value_manifest.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f15_oos_decision_value_manifest.json)
- **Validation Script:** [`scripts/run_f15_oos_decision_value_validation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f15_oos_decision_value_validation.py)
- **Out-Of-Sample Results Data:** [`docs/phase_f15_oos_decision_value_results.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f15_oos_decision_value_results.json)
- **Unit Test Suite:** [`tests/data_quality/test_phase_f15_oos_decision_value.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f15_oos_decision_value.py) (5/5 tests passing)
