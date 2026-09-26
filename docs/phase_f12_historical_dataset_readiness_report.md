# Phase F.12 — Real Longitudinal Historical Dataset Readiness & Coverage Audit Report

---

### Executive Governance Status

```
FINAL DECLARED STATUS: PHASE F.12 PASSED WITH LIMITATIONS
— The historical NAV ingestion engine is verified as ready, idempotent, and operational. The historical database contains 37,528 raw observations across 6 isolated snapshot dates (2010-01-15, 2015-01-15, 2020-01-15, 2024-01-14, 2024-01-15, 2025-01-15). However, 0 schemes currently have continuous longitudinal daily time series (>755 dates). Full real-market F.11.3 longitudinal backtesting requires executing a multi-year daily/monthly backfill, and production metadata (TER, Riskometer, Benchmark) remains unpopulated per F.10.3.
```

---

### 1. Direct Answers to Governed Questions

1. **How much real longitudinal historical NAV data actually exists?**  
   **37,528 raw observations** / **27,358 normalized NAV records** covering 14,048 unique canonical schemes across **6 isolated snapshot dates** (`2010-01-15`, `2015-01-15`, `2020-01-15`, `2024-01-14`, `2024-01-15`, `2025-01-15`).

2. **How many schemes have sufficient history for 1Y, 3Y and 5Y validation?**  
   - **1-Year Continuous Daily History**: **0 schemes**.
   - **3-Year Continuous Daily History**: **0 schemes**.
   - **5-Year Continuous Daily History**: **0 schemes**.  
   *(Existing history consists of isolated point-in-time snapshots, not daily continuous series).*

3. **How many genuine historical decision dates are available?**  
   **6 snapshot dates** in the current database.

4. **Whether PIT category data is sufficient?**  
   **Partially.** Category mapping for SEBI 2017 circular schemes is supported, but pre-2017 category history is unpopulated.

5. **Whether lifecycle/survivorship coverage is sufficient?**  
   **Yes.** Closed and merged schemes (e.g. `SCHEME_CLOSED_9999`) remain preserved in historical snapshots without survivorship filtering or NAV stitching.

6. **Whether TER/Riskometer/Benchmark historical data is sufficient?**  
   **No.** Per Phase F.10.3 findings, TER, Riskometer, and Benchmark fields are unpopulated in the live feed ($TER=\text{None}, \text{Riskometer}=\text{None}, \text{Benchmark}=\text{None}$).

7. **Whether cost/tax validation is possible?**  
   **No.** Historical fund-level exit loads and tax rules are unpopulated. Status: `NOT READY`.

8. **Whether the current dataset can support genuine F.11.3 real-market backtesting?**  
   **No.** Real-market longitudinal backtesting requires continuous daily/monthly NAV trajectories before and after decision date $T$.

9. **If not, the exact minimum backfill/data work required?**  
   Ingest continuous daily/monthly AMFI historical NAVs from 2015-01-01 to 2025-01-15 (~2,500 daily windows, ~18M raw observations).

10. **The recommended next engineering phase?**  
    **PHASE F.12.1 — LONGITUDINAL DAILY HISTORICAL NAV BACKFILL & PRODUCTION DATASET EXPANSION**.

---

### 2. Historical NAV Reconciliation Table

| Evaluation Date | Raw Observations | Normalized Records | NAV Quarantine | Mapping Quarantine | Source Status |
|-----------------|------------------|--------------------|----------------|--------------------|---------------|
| **2005-01-15**  | 0                | 0                  | 0              | 0                  | `SUCCESS_EMPTY` |
| **2010-01-15**  | 2,726            | 1,123              | 148            | 1,455              | `COMPLETED` |
| **2015-01-15**  | 9,399            | 6,347              | 53             | 2,999              | `COMPLETED` |
| **2020-01-15**  | 9,425            | 7,124              | 0              | 2,301              | `COMPLETED` |
| **2024-01-14**  | 814              | 625                | 0              | 189                | `COMPLETED` |
| **2024-01-15**  | 7,194            | 5,722              | 108            | 1,364              | `COMPLETED` |
| **2025-01-15**  | 7,970            | 6,417              | 108            | 1,445              | `COMPLETED` |
| **AGGREGATE**   | **37,528**       | **27,358**         | **417**        | **9,753**          | `VERIFIED` |

---

### 3. Scheme Longitudinal Depth Distribution

| Depth Bucket | Scheme Count | Coverage Description | Backtest Eligibility |
|--------------|--------------|----------------------|----------------------|
| **1 date** | 8,421 | Single snapshot observation | `NOT ELIGIBLE` |
| **2–4 dates** | 3,115 | Multi-year snapshot observations | `NOT ELIGIBLE` |
| **5–6 dates** | 2,512 | Full snapshot presence | `EXPLORATORY ONLY` |
| **7–51 dates** | 0 | Monthly series | `NOT INGESTED` |
| **52–251 dates**| 0 | 1Y Daily series | `NOT INGESTED` |
| **252–755 dates**| 0 | 1Y–3Y Daily series | `NOT INGESTED` |
| **>755 dates** | 0 | 3Y+ Continuous daily series | `NOT INGESTED` |

---

### 4. Fund Quality Score Input Availability Matrix

| Score Field | Primary Source | Historical Depth | Coverage Status | Production Usability |
|-------------|----------------|------------------|-----------------|----------------------|
| **Absolute Return** | AMFI NAV | 6 Snapshots | `PARTIAL` | Usable for snapshot return |
| **CAGR (1Y/3Y/5Y)** | AMFI NAV | 6 Snapshots | `PARTIAL` | Requires continuous series |
| **Rolling 1Y Return** | AMFI NAV | 0 Series | `UNAVAILABLE` | Requires daily backfill |
| **Rolling 3Y Return** | AMFI NAV | 0 Series | `UNAVAILABLE` | Requires daily backfill |
| **Volatility** | AMFI NAV | 0 Series | `UNAVAILABLE` | Requires daily backfill |
| **Downside Risk** | AMFI NAV | 0 Series | `UNAVAILABLE` | Requires daily backfill |
| **Max Drawdown** | AMFI NAV | 0 Series | `UNAVAILABLE` | Requires daily backfill |
| **Longevity** | Scheme Master | 14,048 Schemes | `AVAILABLE` | Derived from inception date |
| **TER (Cost Efficiency)**| Official AMC | 0 Records | `UNAVAILABLE` | Unpopulated ($TER=\text{None}$) |
| **Riskometer** | Official AMC | 0 Records | `UNAVAILABLE` | Unpopulated ($\text{Riskometer}=\text{None}$) |
| **Benchmark / TRI** | Index Feed | 0 Records | `UNAVAILABLE` | Unpopulated ($\text{Benchmark}=\text{None}$) |

---

### 5. Backtest Readiness Matrix Across Engine Modules

| Engine Module | Real Data Available? | Historical Depth | Bias Controlled? | Readiness Status |
|---------------|----------------------|------------------|------------------|------------------|
| **NAV-Derived Fund Quality** | Partial | 6 Snapshots | Yes | `PARTIALLY READY` |
| **Category-Relative Ranking** | Partial | 6 Snapshots | Yes | `PARTIALLY READY` |
| **1-Year Outcome Validation** | No | 0 Series | Yes | `NOT READY` (Needs Backfill) |
| **3-Year Outcome Validation** | No | 0 Series | Yes | `NOT READY` (Needs Backfill) |
| **5-Year Outcome Validation** | No | 0 Series | Yes | `NOT READY` (Needs Backfill) |
| **BUY / ACCUMULATE Actions** | Partial | Snapshot Only | Yes | `PARTIALLY READY` |
| **HOLD / MONITOR / REVIEW** | Partial | Snapshot Only | Yes | `PARTIALLY READY` |
| **SELL / Switch Economics** | No | Costs Missing | Yes | `NOT READY` |
| **TER Cost Efficiency** | No | Unpopulated | N/A | `UNVALIDATABLE` |
| **Riskometer Suitability** | No | Unpopulated | N/A | `UNVALIDATABLE` |
| **Benchmark Excess Return** | No | Unpopulated | N/A | `UNVALIDATABLE` |
| **Survivorship & Lifecycle** | Yes | 14,048 Schemes | Yes | `READY` |

---

### 6. Realistic Daily Backfill Requirement Sizing

To support continuous 1Y, 3Y, and 5Y longitudinal outcome backtesting:
- **Target Period**: 2015-01-01 to 2025-01-15 (~10 Years).
- **Target Windows**: ~2,500 daily AMFI API windows.
- **Estimated Raw Volume**: ~18.5 Million raw NAV observations.
- **Estimated Normalized Volume**: ~14.2 Million normalized NAV records.
- **Estimated Database Size**: ~3.2 GB SQLite.
- **Pipeline Runtime**: ~4.2 hours at rate-limit 0.1s delay per window.

---

### 7. Test Suite Summary

- **Test Suite**: [`tests/data_quality/test_phase_f12_historical_dataset_readiness.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f12_historical_dataset_readiness.py)
- **Total Tests**: 8 dedicated tests (100% pass).
- **Full Suite Status**: 666 passed, 0 failed, 0 errors across 25 test files.
