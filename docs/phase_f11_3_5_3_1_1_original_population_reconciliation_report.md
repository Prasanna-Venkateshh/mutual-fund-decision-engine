# Phase F.11.3.5.3.1.1 — Original Scoring Population Reconciliation Report

**Document ID**: `docs/phase_f11_3_5_3_1_1_original_population_reconciliation_report.md`  
**Dataset Version**: `f12_3_1_2_v1.0.0`  
**Database**: `db/backfill_f12_2.db`  
**Anchor Date**: `2024-01-31`  
**Unseen Horizon**: `2024-02-01` through `2025-01-31`  
**Methodology Version**: `1.0.0` (Return 25%, Consistency 20%, Volatility 15%, Downside Risk 15%, Max Drawdown 15%, Cost Efficiency 10%)  
**Execution Timestamp**: `2026-09-15T21:43:55Z`  
**Governance Status**: **`PHASE F.11.3.5.3.1.1 PASSED`**

---

## 1. Objective & Governance Assertions

Phase F.11.3.5.3.1.1 performs a narrow forensic reconciliation to establish the exact population that generated the original F.11.3.5.3 statistical results, resolving the exact 8-scheme anchor discrepancy ($5,832 \text{ vs } 5,824$), 1-scheme forward-eligible discrepancy ($5,713 \text{ vs } 5,712$), and 7-scheme unavailable discrepancy ($119 \text{ vs } 112$).

### Bounded Language & Immutability Compliance
- **No Production Methodology Modification**: Production weights, scoring formulas, suitability rules, and action semantics remain 100% frozen.
- **No Post-Hoc Optimization**: Strategy selection rules and thresholds remain strictly frozen.
- **Conservative Wording**: Observed statistical relationships are described as *observed associations* or *reproduced statistics* without making causal claims or unvalidated economic benefit statements.

---

## 2. Reconstructed Population Definitions

| Set Identifier | Description | Predicate / Query | Population N |
|---|---|---|---:|
| **`SET_G`** | Governed Anchor Cohort (F.12.3.1.2) | `WHERE nav_date = '2024-01-31'` | **5,874** |
| **`SET_A`** | Original F.11.3.5.3 Anchor Cohort | `last_obs_date >= '2024-01-01' AND obs_count >= 20` | **5,832** |
| **`SET_B`** | Reconstructed F.11.3.5.3.1 Cohort | `SET_G AND obs_count >= 20` | **5,824** |

---

## 3. Set-Level Comparisons & Exact Arithmetic

- $SET\_A \cap SET\_B = 5,824$ schemes
- $SET\_A - SET\_B = 8$ schemes (**The exact 8-scheme anchor discrepancy**)
- $SET\_B - SET\_A = 0$ schemes (Zero unexpected additions)
- $SET\_A \cap SET\_G = 5,824$ schemes ($= SET\_B$)
- $SET\_G - SET\_A = 50$ schemes (Newly launched schemes in Jan 2024 with $1 \le N \le 19$ observations)
- $SET\_A - SET\_G = 8$ schemes (Active schemes in Jan 2024 whose last pre-Feb 2024 NAV occurred before Jan 31)

---

## 4. The Eight-Scheme Discrepancy Breakdown ($5,832 - 5,824 = 8$)

Every single scheme responsible for the $5,832 - 5,824 = 8$ discrepancy has been 100% identified and audited:

| # | Canonical Scheme ID | Last NAV Date $\le \text{2024-01-31}$ | Pre-Anchor Obs Count | `SET_A` Status | `SET_B` Status | Jan 2025 Forward State | Exact Cause |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| 1 | `CAN_AMFI_144681` | 2024-01-19 | 752 | Included | Excluded | Unavailable | Last Jan 2024 NAV on Jan 19; missed exact Jan 31 query |
| 2 | `CAN_AMFI_144730` | 2024-01-19 | 752 | Included | Excluded | Unavailable | Last Jan 2024 NAV on Jan 19; missed exact Jan 31 query |
| 3 | `CAN_AMFI_147164` | 2024-01-29 | 1,103 | Included | Excluded | **Reachable** | Last Jan 2024 NAV on Jan 29; missed exact Jan 31 query |
| 4 | `CAN_AMFI_147707` | 2024-01-15 | 1,093 | Included | Excluded | Unavailable | Last Jan 2024 NAV on Jan 15; missed exact Jan 31 query |
| 5 | `CAN_AMFI_149349` | 2024-01-12 | 520 | Included | Excluded | Unavailable | Last Jan 2024 NAV on Jan 12; missed exact Jan 31 query |
| 6 | `CAN_AMFI_149350` | 2024-01-12 | 520 | Included | Excluded | Unavailable | Last Jan 2024 NAV on Jan 12; missed exact Jan 31 query |
| 7 | `CAN_AMFI_151269` | 2024-01-10 | 359 | Included | Excluded | Unavailable | Last Jan 2024 NAV on Jan 10; missed exact Jan 31 query |
| 8 | `CAN_AMFI_151271` | 2024-01-10 | 359 | Included | Excluded | Unavailable | Last Jan 2024 NAV on Jan 10; missed exact Jan 31 query |

---

## 5. Forward Eligibility & Unavailable Reconciliation

The forward eligibility and unavailability counts reconcile mathematically:

- **Original `SET_A` (5,832 Anchor)**:
  - Forward-Eligible = **5,713** ($5,712 \text{ in } SET\_B + 1 \text{ reachable from 8: } \text{CAN\_AMFI\_147164}$)
  - Forward-Unavailable = **119** ($112 \text{ in } SET\_B + 7 \text{ unreachable from 8}$)
  - **Identity Check**: $5,713 + 119 = 5,832$ (**100% EXACT MATCH TO REPORTED F.11.3.5.3**)

- **Reconstructed `SET_B` (5,824 Anchor)**:
  - Forward-Eligible = **5,712**
  - Forward-Unavailable = **112**
  - **Identity Check**: $5,712 + 112 = 5,824$ (**100% EXACT MATCH**)

- **Governed `SET_G` (5,874 Anchor)**:
  - Forward-Eligible = **5,750**
  - Forward-Unavailable = **124**
  - **Identity Check**: $5,750 + 124 = 5,874$ (**100% EXACT MATCH TO REPORTED F.12.3.1.2**)

---

## 6. Cohort SHA-256 Hash Reproduction

The original SHA-256 cohort hash reported in Phase F.11.3.5.3 was recalculated over the sorted canonical scheme IDs of `SET_A` (5,832 schemes):

- **Original F.11.3.5.3 Hash**: `e2c8c732520891c2a2fcb24ebd3acfe77b6f88e228a90fa31d41e6de986062e5`
- **Re-calculated `SET_A` Hash**: `e2c8c732520891c2a2fcb24ebd3acfe77b6f88e228a90fa31d41e6de986062e5`
- **Match**: **`TRUE` (100% Deterministic Reproduction)**

---

## 7. Statistical Reproduction Matrix

All statistical metrics originally published in Phase F.11.3.5.3 were **100% exactly reproduced** from `SET_A` ($N=5,713$ scored):

| Statistic / Metric | Original F.11.3.5.3 Reported | Re-Calculated `SET_A` (5,832) | Re-Calculated `SET_B` (5,824) | Re-Calculated `SET_G` (5,874) | Reproduction Status |
|---|---:|---:|---:|---:|---|
| **Fund Quality Spearman ($\rho$)** | **0.2991** | **0.2991** | 0.2984 | 0.2969 | **EXACT MATCH** |
| **Trailing 1Y Spearman ($\rho$)** | **0.5882** | **0.5882** | 0.5880 | 0.5880 | **EXACT MATCH** |
| **Historical Risk Spearman ($\rho$)**| **0.4011** | **0.4011** | 0.4011 | 0.4010 | **EXACT MATCH** |
| **Incremental $R^2$ (FQ over Risk)** | **+0.0340 (+3.40%)** | **+0.0340 (+3.40%)** | +0.0340 | +0.0344 | **EXACT MATCH** |
| **Q1-Q5 Return Spread** | **+3.30%** | **+3.30%** | +3.29% | +3.26% | **EXACT MATCH** |
| **Strategy A Return** | **12.23%** | **12.23%** | 12.23% | 12.20% | **EXACT MATCH** |
| **Strategy A MDD** | **16.83%** | **16.83%** | 16.83% | 16.80% | **EXACT MATCH** |
| **Strategy B Return** | **6.82%** | **6.82%** | 6.82% | 6.80% | **EXACT MATCH** |
| **Strategy B MDD** | **0.45%** | **0.45%** | 0.45% | 0.45% | **EXACT MATCH** |
| **Strategy C Return** | **7.81%** | **7.81%** | 7.81% | 7.70% | **EXACT MATCH** |
| **Strategy C MDD** | **1.26%** | **1.26%** | 1.26% | 1.07% | **EXACT MATCH** |

---

## 8. Strategy Definition & MDD Math Audit

1. **Pre-Freezing Verification**:
   - Strategy selection rules (Strategy A: Top Decile Trailing 1Y; Strategy B: Lowest Decile Volatility; Strategy C: Top Decile Fund Quality) were pre-frozen in [`docs/phase_f11_3_5_3_validation_manifest.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f11_3_5_3_validation_manifest.json) prior to inspecting forward returns.

2. **MDD Aggregation Math**:
   - In Strategy A, B, and C, "MDD" represents the **equal-weighted average per-fund maximum drawdown** across the selected top decile ($N = 571$ schemes). It is an observational metric of asset-level drawdown behavior, not an aggregated daily portfolio path drawdown.

---

## 9. Automated Test Suite Results

- **Dedicated Test File**: [`tests/data_quality/test_phase_f11_3_5_3_1_1_original_population_reconciliation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f11_3_5_3_1_1_original_population_reconciliation.py)
- **Dedicated Tests Executed**: **30 / 30 tests passed (100%)**.
- **Full Forensic Suite**: **26 / 26 tests passed (100%)**.

---

## 10. Final Governance Status Declaration

```
PHASE F.11.3.5.3.1.1 PASSED
```
