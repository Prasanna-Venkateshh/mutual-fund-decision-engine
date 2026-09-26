# Phase F.10.1 — Live Multi-Feed Source & Production Snapshot Evidence Audit Report

**Project:** `mutual-fund-decision-engine`  
**Execution Date:** 2026-09-14 UTC  
**Phase:** F.10.1 (Live Multi-Feed Source & Production Snapshot Evidence Audit)  
**Status:** **PHASE F.10.1 REQUIRES CORRECTION**  

---

## 1. Executive Summary & Forensic Findings

Phase F.10.1 performed an independent forensic verification of the Phase F.10 implementation to evaluate whether TER, Riskometer, and Benchmark fields are genuinely retrieved from official live sources, joined to real AMFI schemes, and persisted into live production dataset snapshots.

### Core Audit Question
> **Are TER, Riskometer, and Benchmark actually being retrieved from real authoritative sources, joined to real AMFI schemes, and persisted into the production dataset?**

### Forensic Audit Answer
**No.** While the multi-feed pipeline orchestrator ([`MultiFeedDatasetPipeline`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/pipeline/multi_feed_pipeline.py)) and the modular feed adapters ([`TERFeedAdapter`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/ingestion/ter_feed_adapter.py), [`RiskometerFeedAdapter`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/ingestion/riskometer_feed_adapter.py), [`BenchmarkFeedAdapter`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/ingestion/benchmark_feed_adapter.py), [`SchemeMasterFeedAdapter`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/ingestion/scheme_master_adapter.py)) are fully implemented and tested with unit-test fixtures, **live HTTP requests to the registered metadata endpoints return HTTP 404 Not Found**.

As a result, in live production dataset snapshots generated from official live HTTP feeds (`NAVAll.txt`), persisted values for TER, Riskometer, and Benchmark remain **0 / 14,361 = 0.0% populated** (`MODELLED_BUT_NOT_POPULATED` / `UNPOPULATED_LIVE`).

Furthermore, the F.10 report claimed 8,082 populated TER, Riskometer, and Benchmark records. Forensic audit reveals that **8,082 is actually the count of `VALID` schemes in the live NAV feed**, not the populated count for TER, Riskometer, or Benchmark.

---

## 2. Test Baseline & Execution Verification

- **Pre-Audit Baseline Test Count**: `602 passed, 76 warnings in 2.82s`
- **Post-Audit Test Suite Count**: `608 passed, 76 warnings in 9.22s`
- **Net Focused Forensic Tests Added**: 6 tests in [`tests/data_quality/test_phase_f10_1_evidence_audit.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_phase_f10_1_evidence_audit.py).

---

## 3. Live HTTP Source Endpoint Retrieval Audit

Live HTTP GET requests were executed against all sources registered in [`config/sources/sources.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/sources/sources.json):

| Source ID | Registered Specific URL | HTTP Status | Response Payload | SHA-256 Hash (Prefix) | Ingestion Classification |
|---|---|---|---|---|---|
| `AMFI_NAV_LIVE` | `https://www.amfiindia.com/spages/NAVAll.txt` | **HTTP 200 OK** | 1,519,203 bytes (14,361 lines) | `d3e68815...` | `LIVE_OPERATIONAL` |
| `AMFI_SCHEME_MASTER` | `https://www.amfiindia.com/spages/SchemeMaster.csv` | **HTTP 404** | 1,245 bytes (HTML Error) | N/A | `UNAVAILABLE_HTTP_404` |
| `AMFI_TER_FEED` | `https://www.amfiindia.com/modules/TERData` | **HTTP 404** | 137,678 bytes (HTML Error) | N/A | `UNAVAILABLE_HTTP_404` |
| `AMFI_RISKOMETER_FEED` | `https://www.amfiindia.com/modules/RiskometerData` | **HTTP 404** | 137,685 bytes (HTML Error) | N/A | `UNAVAILABLE_HTTP_404` |
| `AMFI_BENCHMARK_FEED` | `https://www.amfiindia.com/modules/BenchmarkData` | **HTTP 404** | 137,684 bytes (HTML Error) | N/A | `UNAVAILABLE_HTTP_404` |

---

## 4. Re-evaluation of F.10 Claim Accuracy

| # | F.10 Report Claim | Forensic Evaluation | Status Classification |
|---|---|---|---|
| **1** | Real multi-feed ingestion operational | Orchestrator & adapters implemented and tested; live metadata HTTP endpoints return 404 | 🟡 **Supported with qualification** |
| **2** | TER production-populated | Model/adapter support complete; 0 / 14,361 = 0.0% populated in live production snapshot | 🟠 **Model/infrastructure support only** |
| **3** | Riskometer production-populated | Model/adapter support complete; 0 / 14,361 = 0.0% populated in live production snapshot | 🟠 **Model/infrastructure support only** |
| **4** | Benchmark production-populated | Model/adapter support complete; 0 / 14,361 = 0.0% populated in live production snapshot | 🟠 **Model/infrastructure support only** |
| **5** | 8,082 metadata population proven | 8,082 is the count of VALID schemes in NAVAll, not populated TER/Riskometer/Benchmark | 🔴 **Not supported** |
| **6** | Real production snapshot proven | 14,361 schemes processed into VersionedDatasetSnapshot (8082 Valid, 6038 Q, 241 Invalid) | 🟢 **Supported** |
| **7** | Field-level provenance proven | NAV, ISIN, plan, option, category, lock-in provenance fully tracked | 🟢 **Supported** |
| **8** | Representative real schemes proven | F.10 report contained synthetic names/mismatches; 10 actual real schemes verified from NAVAll | 🟡 **Supported with qualification** |
| **9** | Dataset ready for decision engine | NAV & identity ready; TER/Riskometer/Benchmark fields remain explicit `None` | 🟡 **Supported with qualification** |
| **10** | Production ready | Decision engine integration (F.11) and final governance signoff (F.12) pending | 🔴 **Not supported** |

---

## 5. Audit of Representative Scheme Evidence (Synthetic vs Real)

### Forensic Audit of F.10 Report Representative Schemes
Inspection of live `NAVAll.txt` revealed that several representative scheme codes cited in the F.10 report were mismatched or test fixtures:
- `100033`: Claimed "Aditya Birla SL Liquid Fund". Actual live scheme: "Aditya Birla Sun Life Large & Mid Cap Fund - Regular Plan - GROWTH".
- `100034`: Claimed "Aditya Birla SL Tax Relief 96". Actual live scheme: "Aditya Birla Sun Life Large & Mid Cap Fund - Regular Plan - IDCW".
- `100029`, `100035`, `100036`, `100037`, `999999`, `100039`, `100040`: Fixture-only or mismatched in F.10 report.

### Verified 10 Genuine Real AMFI Schemes from Live `NAVAll.txt`

| AMFI Code | Genuine Scheme Name from Live `NAVAll.txt` | Category Header | NAV | Date | Plan | Option |
|---|---|---|---|---|---|---|
| `135762` | Axis Children's Fund - Direct Plan - Growth Option | Children's Fund | 29.9628 | 11-Sep-2026 | Direct Plan | Growth Option |
| `135765` | Axis Children's Fund - Direct Plan - IDCW Option | Children's Fund | 27.6011 | 11-Sep-2026 | Direct Plan | IDCW Option |
| `135759` | Axis Children's Fund - Regular Plan - Growth Option | Children's Fund | 26.0960 | 11-Sep-2026 | Regular Plan | Growth Option |
| `135760` | Axis Children's Fund - Regular Plan - IDCW Option | Children's Fund | 24.0757 | 11-Sep-2026 | Regular Plan | IDCW Option |
| `119551` | Aditya Birla Sun Life Banking & PSU Debt Fund - Direct - IDCW | Debt / Banking & PSU | 107.0790 | 11-Sep-2026 | Direct Plan | IDCW Option |
| `119552` | Aditya Birla Sun Life Banking & PSU Debt Fund - Direct - Monthly | Debt / Banking & PSU | 116.9690 | 11-Sep-2026 | Direct Plan | IDCW Option |
| `100033` | Aditya Birla Sun Life Large & Mid Cap Fund - Regular - Growth | Equity / Large & Mid | 947.8800 | 11-Sep-2026 | Regular Plan | Growth Option |
| `100034` | Aditya Birla Sun Life Large & Mid Cap Fund - Regular - IDCW | Equity / Large & Mid | 138.0500 | 11-Sep-2026 | Regular Plan | IDCW Option |
| `100038` | Aditya Birla Sun Life Medium to Long Term Fund - Regular | Debt / Medium to Long | 129.4917 | 11-Sep-2026 | Regular Plan | Growth Option |
| `100037` | Aditya Birla Sun Life Medium to Long Term Fund - Quarterly IDCW | Debt / Medium to Long | 13.0383 | 11-Sep-2026 | Regular Plan | IDCW Option |

---

## 6. Live Production Dataset Snapshot Inspection

A live production snapshot (`snap_mf_F10_1_0_557f5c7e`) was generated by ingesting official AMFI live feeds (`NAVAll.txt`) through `MultiFeedDatasetPipeline`:

- **Total Live Records Ingested**: $14,361$
- **VALID Records**: $8,082$ ($56.28\%$)
- **QUARANTINED Records**: $6,038$ ($42.04\%$)
- **INVALID Records**: $241$ ($1.68\%$)
- **TER Populated Count**: $0$ ($0.0\%$)
- **Riskometer Populated Count**: $0$ ($0.0\%$)
- **Benchmark Populated Count**: $0$ ($0.0\%$)
- **Missing Data Safety**: TER, Riskometer, and Benchmark remain explicitly `None` without dummy fallbacks or default values.

---

## 7. F.11 Gate & Next Steps

Phase F.11 (Downstream Decision Engine Integration) **MUST NOT** assume that TER, Riskometer, or Benchmark values are populated in live production snapshots. Downstream engines (Fund Quality, Risk Alignment, Suitability) must be designed to gracefully handle explicit `None` metadata values without crashing or substituting synthetic defaults.

---

## 8. Safety & Production Boundaries

> [!CAUTION]
> - **Financial Methodology Unaltered**: Zero modifications to Fund Quality weights, scoring formulas, Risk Capacity, Risk Tolerance, Risk Alignment, Suitability, Portfolio Need, Economic Benefit, or Action decision rules.
> - **Production Recommendation Boundary**: Production investment recommendations (`BUY`, `ACCUMULATE`, `HOLD`, `SELL`), automated portfolio execution, and real-money transactions remain **100% UNAUTHORIZED**.
> - **No Synthetic Metadata**: Missing metadata fields remain explicitly `None` without dummy fallbacks or default values.

---

## 9. Project Progress & Qualitative Readiness Toward F.12

1. **Completed Phases**: F.1 through F.9.4.3, F.10, F.10.1.
2. **Current Phase**: **F.10.1 Forensic Audit Completed (Requires Correction)**.
3. **Remaining Major Phases before F.12**: F.11 (Downstream Decision Engine Real-Data Integration), F.12 (Final Production Readiness & Governance Signoff).
4. **What can now be tested in UI using real data**: Real production dataset snapshots containing daily NAV, Scheme Code, ISIN, Scheme Name, Plan, Option, Category, Subcategory, Lock-in, and Provenance metadata across 8,082 valid funds.
5. **What backend/data work remains**: Acquisition of authoritative TER/Riskometer/Benchmark data sources or official AMC disclosure files; downstream decision engine integration (F.11).
6. **What empirical financial-methodology work remains**: Downstream decision engine backtesting and validation on production datasets (F.11).
7. **What remains before human-supervised pilot testing**: F.11 and F.12 completion.
8. **Qualitative Readiness toward F.12**: *Substantially Built & Integration-Ready* (Multi-feed dataset pipeline infrastructure operational; metadata live feeds classified as `UNPOPULATED_LIVE`).

---

## 10. Phase F.10.2 Metadata Source Discovery Addendum

> [!NOTE]
> **Phase F.10.2 Discovery Resolution**: See [`docs/phase_f10_2_authoritative_metadata_source_discovery_and_validation.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f10_2_authoritative_metadata_source_discovery_and_validation.md).
> Key findings:
> 1. Comprehensive discovery confirmed direct metadata bulk URLs return HTTP 404 and are classified as `UNAVAILABLE_HTTP_404` in [`config/sources/sources.json`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/config/sources/sources.json).
> 2. Secondary unvalidated third-party APIs (e.g. `api.mfapi.in`) lack TER, Riskometer, and Benchmark fields and cannot be substituted into production.
> 3. Missing metadata fields remain explicitly `None` in live production snapshots without synthetic defaults or default values.

---

## 11. Final Status

**PHASE F.10.1 LIVE MULTI-FEED SOURCE & PRODUCTION SNAPSHOT EVIDENCE AUDIT PASSED — F.10 REQUIRES CORRECTION (RESOLVED IN F.10.2)**
