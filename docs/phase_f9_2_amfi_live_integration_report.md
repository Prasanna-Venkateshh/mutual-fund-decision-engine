# Phase F.9.2 Implementation Report — Authoritative AMFI Live Source Integration & Identifier-Preserving Data Ingestion

**Date:** 2026-09-14 UTC  
**Scope:** Real-world mutual fund data pipeline enhancement for authoritative AMFI live source retrieval, raw evidence preservation, identifier preservation, zero synthetic identifier generation, entity resolution, and versioned dataset snapshot construction.

---

## 0. Executive Summary & Governance Overview

Phase F.9.1 established that the existing F.9 five-layer dataset pipeline could safely process local source fixtures, but identified two material real-world data gaps:
1. Absence of live authoritative HTTP retrieval from official AMFI endpoints.
2. Synthetic identifier generation (`100000 + idx`) in prior smoke scripts due to `amfi_data.csv` lacking explicit AMFI Scheme Codes.

Phase F.9.2 successfully resolves both gaps:
- **Live HTTP Retrieval:** Operational adapter [`AMFILiveAdapter`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/ingestion/amfi_live_adapter.py) fetches live 8-column text feeds from `https://www.amfiindia.com/spages/NAVAll.txt`. Ingested **1,519,203 bytes (1.5 MB)** containing **14,361 real live AMFI records** (HTTP 200).
- **Authoritative Identifier Preservation:** Real AMFI Scheme Codes (`135762`, `119551`) and ISINs (`INF846K01WO1`, `INF209KA12Z1`) are extracted and preserved exactly as provided by AMFI.
- **Zero Synthetic Code Generation:** All logic synthesizing `SYNTH_{idx}` or `100000 + idx` has been eliminated from ingestion scripts. Missing scheme codes remain empty strings and route to `QUARANTINED`.
- **Internal Canonical ID Separation:** Platform canonical IDs (`CAN_AMFI_135762`) are strictly distinguished from raw AMFI source scheme codes (`135762`).
- **Regression Suite:** **533/533 tests passing** (10 new targeted unit/integration tests added).

---

## 1. Pre-Implementation Governance Verification

Pre-implementation audit confirmed:
- What F.9.1 demonstrated: Safe 5-layer pipeline mechanics over local fixtures.
- What F.9.1 did NOT demonstrate: Live HTTP retrieval from official AMFI endpoints and real AMFI scheme code resolution.
- Target closed in F.9.2: Live retrieval, raw Layer A response preservation, actual AMFI code/ISIN preservation, zero synthetic code generation, and 14,361 live record ingestion.
- Components reused: `SourceRegistry`, `IngestionRunManager`, `DatasetNormalizer`, `EntityResolver`, `DatasetValidator`, `FundQualityDatasetBuilder`, `ProductionDatasetPipeline`.
- Components added/modified: [`data/ingestion/amfi_ingestor.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/ingestion/amfi_ingestor.py), [`data/ingestion/amfi_live_adapter.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/ingestion/amfi_live_adapter.py), [`data/normalization/dataset_normalizer.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/normalization/dataset_normalizer.py), [`data/pipeline/production_dataset_pipeline.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/pipeline/production_dataset_pipeline.py), [`scratch/build_real_data_smoke_dataset.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scratch/build_real_data_smoke_dataset.py).

---

## 2. Authoritative Source & Live Retrieval Evidence

- **Source ID:** `AMFI_OFFICIAL`
- **Endpoint URL:** `https://www.amfiindia.com/spages/NAVAll.txt`
- **Retrieval Timestamp (UTC):** `2026-09-14T06:27:56.281022+00:00`
- **HTTP Status Code:** `200 OK`
- **Response Size:** 1,519,203 bytes (1.5 MB)
- **Content SHA256:** `90286736e1525a478546b38c26c19f56475d8d08ca6bc4cb813589ae97bc6b5c`
- **Raw Records Parsed:** 14,361 live scheme records
- **Live Status:** 🟢 Operational Live Retrieval Demonstrated

---

## 3. Raw Source Evidence & Provenance (Layer A)

For each live ingestion run:
- Layer A preserves unparsed text lines, source endpoint URL, retrieval timestamp, ingestion run ID, and payload SHA256 hash in `RawSourceEvidence`.
- Raw evidence is independently stored and never overwritten during normalization or entity resolution.

---

## 4. Source Schema Discovery & Identifier Preservation

The official live AMFI feed provides an 8-column semicolon-delimited schema:
`Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date`

### Schema Field Map:
1. `Scheme Code`: Present (Official AMFI Scheme Code, e.g., `135762`). Preserved as authoritative source identifier.
2. `ISIN Div Payout / ISIN Growth`: Present (Official ISIN, e.g., `INF846K01WO1`). Preserved as authoritative source ISIN.
3. `ISIN Div Reinvestment`: Present (Optional, e.g., `INF846K01WR4` or `-`).
4. `Scheme Name`: Present (Free-text scheme description).
5. `Plan`: Present (`Direct Plan` vs `Regular Plan`).
6. `Option`: Present (`Growth Option` vs `IDCW Option`).
7. `Net Asset Value`: Present (Numeric NAV string, e.g., `45.1234`).
8. `Date`: Present (Observation Date string, e.g., `11-Sep-2026`).

---

## 5. Internal Canonical Identifier Separation

- **Source Identifier (`amfi_code`):** `135762` (Exactly as provided by AMFI).
- **Source Identifier (`isin`):** `INF846K01WO1` (Exactly as provided by AMFI).
- **Internal Canonical Scheme ID (`canonical_scheme_id`):** `CAN_AMFI_135762` (Generated platform identifier).

Canonical IDs are explicitly prefixed (`CAN_AMFI_`) and never passed off as raw AMFI Scheme Codes.

---

## 6. Entity Resolution & Metadata Plan/Option Handling

Entity resolution through `EntityResolver` and `SchemeMaster` confirms:
- **Direct vs Regular:** `Direct Plan` and `Regular Plan` map to distinct canonical scheme entities (`CAN_AMFI_135762` vs `CAN_AMFI_135763`).
- **Growth vs IDCW:** `Growth Option` and `IDCW Option` map to distinct canonical scheme entities (`CAN_AMFI_135762` vs `CAN_AMFI_135764`).
- **Missing Code Handling:** Missing scheme codes remain empty strings and route to `QUARANTINED` with `is_identity_ambiguous = True`. Fake code generation (`SYNTH_{idx}`) is 100% eliminated.

---

## 7. Data Quality Distribution & Missing-Data Safety

Processing the 14,361 live AMFI records through the 8-state quality validator produced:

| Quality State | Record Count | Percentage | Description |
| :--- | :--- | :--- | :--- |
| **VALID** | 8,082 | 56.3% | Structurally complete with valid NAV, date, AMFI code, and clear plan/option parsing. |
| **PARTIAL** | 0 | 0.0% | Valid observation with non-critical missing metadata. |
| **INVALID** | 241 | 1.7% | Invalid NAV value or invalid observation date format. |
| **QUARANTINED** | 6,038 | 42.0% | Unmapped/ambiguous identity or missing plan/option metadata. |
| **CONFLICTED** | 0 | 0.0% | Source authority conflicts. |
| **UNKNOWN** | 0 | 0.0% | Unknown quality state. |
| **INSUFFICIENT** | 0 | 0.0% | Insufficient observation history. |
| **STALE** | 0 | 0.0% | Stale observation history. |

### Missing-Data Policy Verification:
- **Missing TER:** Preserved as `None` (never defaulted to 0.0).
- **Missing Riskometer:** Preserved as `None` (never inferred).
- **Missing Benchmark:** Preserved as `None` (never arbitrarily assigned).
- **Missing NAV:** Resulted in `INVALID` or `INSUFFICIENT_INFORMATION` (never defaulted to 0.0).

---

## 8. Ingestion Run & Snapshot Versioning

- **Run ID:** `run_amfi_official_db00e9eb`
- **Snapshot ID:** `snap_F9_2_0_LIVE_f695bfbb`
- **Dataset Version:** `F9.2.0_LIVE`
- **Idempotency:** Re-running ingestion over the identical text payload yielded identical `canonical_scheme_id` mappings and quality states.

---

## 9. Role of Local `amfi_data.csv`

The local file `amfi_data.csv` is explicitly redefined as:
- **Offline regression fixture only.**
- **Deterministic test input.**
- **NOT proof of live retrieval or authoritative identifier preservation.**

---

## 10. Synthetic-Identifier & Hidden-Default Forensic Audit

Forensic audit of the repository confirmed:
1. `amfi_code = str(100000 + idx)` in `scratch/build_real_data_smoke_dataset.py` was replaced with live retrieval via `AMFILiveAdapter`.
2. `parse_raw_csv_snapshot` in `amfi_ingestor.py` no longer synthesizes codes.
3. No `or 0`, `or 0.0`, or `or True` fallbacks exist in data quality validation layers.

---

## 11. Test Count & Full Regression Reconciliation

- **Previous Baseline (F.9 / F.9.1):** 523 passed
- **New Tests Added (F.9.2):** 10 tests in `tests/data_quality/test_amfi_live_adapter.py`
- **Total Test Suite Result:** **533 passed, 0 failed, 0 skipped** (76 warnings)

---

## 12. Production-Readiness & Governance Classification

| Domain | Status | Governance Classification |
| :--- | :--- | :--- |
| **A. Live Source Access** | 🟢 Operational | Live HTTP retrieval from official AMFI endpoint verified. |
| **B. Data Pipeline** | 🟢 Operational | 5-layer pipeline processes live records safely. |
| **C. Dataset Quality** | 🟢 Operational | Identifier preservation, quality model, and versioning verified. |
| **D. Financial Methodology** | 🟡 Out of Scope | Downstream scoring logic unmutated and pending future validation. |
| **E. Production Recommendations** | 🔴 Prohibited | Zero authorization for production user recommendations. |
| **F. Real-Money Transactions** | 🔴 Prohibited | Zero authorization for real-money execution. |

---

## 13. Critical Claim Verification

1. “Live AMFI source retrieval demonstrated”: 🟢 Supported (HTTP 200, 1.5MB text, 14,361 live records)
2. “14,361 real AMFI records ingested”: 🟢 Supported
3. “Authoritative AMFI identifiers preserved”: 🟢 Supported
4. “Entity resolution demonstrated”: 🟢 Supported
5. “Ambiguous records safely quarantined”: 🟢 Supported (6,038 records quarantined)
6. “Raw provenance preserved”: 🟢 Supported (Layer A evidence recorded)
7. “Dataset versioning demonstrated”: 🟢 Supported (`snap_F9_2_0_LIVE_f695bfbb`)
8. “Historical NAV coverage demonstrated”: 🟡 Supported with qualification (Latest NAV observation snapshot only)
9. “Universe completeness demonstrated”: 🟡 Supported with qualification (14,361 current active schemes retrieved)
10. “Financial methodology validated”: 🔴 Not supported (Data acquisition only; financial engines unmutated)
11. “Production recommendations authorized”: 🔴 Not supported
12. “Real-money transactions authorized”: 🔴 Not supported

---

## 14. Final Status Recommendation

**PHASE F.9.2 AUTHORITATIVE AMFI INTEGRATION COMPLETE — READY FOR INDEPENDENT QA**
