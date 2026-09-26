# PHASE F.9 — REAL-WORLD MUTUAL FUND DATASET CONSTRUCTION & PRODUCTION DATA PIPELINE SPECIFICATION

## Executive Summary

Phase F.9 establishes the production data infrastructure and dataset construction pipeline for the India mutual-fund decision engine. It enforces a controlled 5-layer ingestion data flow (`Layer A` Raw Source Evidence → `Layer B` Normalized Data → `Layer C` Entity-Resolved Data → `Layer D` Validated Dataset → `Layer E` Versioned Dataset Snapshot) to process real-world data from authoritative sources while strictly preserving point-in-time (PIT) isolation, identity resolution, missing-data safety, and provenance lineage.

> [!IMPORTANT]
> **GOVERNANCE BOUNDARY & CONSTRAINTS**:
> - Phase F.9 owns **Data Infrastructure & Dataset Construction ONLY**.
> - **Zero modification** was made to upstream financial methodology, Fund Quality weights, Risk Capacity/Tolerance parameters, Suitability rules, Portfolio Need rules, Economic Benefit logic, or Action Engine semantics.
> - **Zero transaction execution logic or real-money execution authorization** is created.
> - **Missing-data safety is 100% maintained**: Missing fields evaluate to explicit `None` / `UNKNOWN` and **never** default to zero or favorable values.

---

## 1. 5-Layer Dataset Architecture

The pipeline processes raw source feeds through five distinct, deterministic layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER A: RAW SOURCE EVIDENCE (RawSourceEvidence)                            │
│ Immutably preserves source payload, URL, timestamp, run ID, and raw hash.  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER B: NORMALIZED DATA (NormalizedRecord)                                 │
│ Applies deterministic date, float, plan, option, category normalization.    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER C: ENTITY-RESOLVED DATA (EntityResolvedRecord)                        │
│ Maps to canonical scheme ID via AMFI/ISIN; quarantines ambiguous identities.│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER D: VALIDATED DATASET (ValidatedRecord)                                │
│ Enforces 8-state DataQualityState model & field-level conflict handling.    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER E: VERSIONED DATASET SNAPSHOT (VersionedDatasetSnapshot)              │
│ Produces immutable dataset version snapshots & scheme coverage ledger.       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion Run & Historical Coverage Engine

### 2.1 Ingestion Run Manager (`IngestionRunManager`)
Every ingestion execution is tracked as an immutable `IngestionRunRecord` capturing:
- `run_id` & `source_id`
- `start_time_utc` & `end_time_utc`
- `retrieval_status` (`SUCCESS`, `PARTIAL`, `FAILED`, `RETRY_REQUIRED`)
- Metric counts (`total_records_processed`, `valid_record_count`, `partial_record_count`, `invalid_record_count`, `quarantined_record_count`, `conflict_record_count`)
- Error audit log

### 2.2 Historical Scheme Coverage (`SchemeCoverageSnapshot`)
Historical NAV coverage is calculated per canonical scheme:
- `earliest_nav_date` & `latest_nav_date`
- `total_observation_count`
- `coverage_status` (`SUFFICIENT` $\ge 36$ observations, `PARTIAL`, `INSUFFICIENT`, `UNKNOWN`)
- Detectable gap counts

---

## 3. Data Quality State Model & Missing-Data Safety

Phase F.9 strictly enforces the 8-state Data Quality Model from Phase F.8:

1. **`VALID`**: Complete, schema-compliant, temporally consistent record.
2. **`PARTIAL`**: Core valid; secondary optional metrics missing.
3. **`UNKNOWN`**: Default state for missing/un-retrieved fields.
4. **`INSUFFICIENT_INFORMATION`**: Missing mandatory fields (e.g. NAV missing/None).
5. **`INVALID`**: Range bound or temporal violation (e.g. negative NAV, TER > 100%, future date).
6. **`CONFLICTED`**: Primary source disagreement beyond field validation tolerance.
7. **`QUARANTINED`**: Explicitly locked out due to identity ambiguity or corruption.
8. **`STALE`**: Source disclosure update window elapsed.

### Absolute Missing-Data Rules Enforced:
- Missing NAV $\rightarrow$ `None` (`INSUFFICIENT_INFORMATION`)
- Missing TER $\rightarrow$ `None` (Never defaults to `0.0`)
- Missing Exit Load $\rightarrow$ `None` (Never defaults to `0.0`)
- Missing Riskometer $\rightarrow$ `None` (Never inferred)
- Missing Benchmark $\rightarrow$ `None` (Never assigned arbitrarily)
- Missing Identity $\rightarrow$ `QUARANTINED` (Never guessed)

---

## 4. Safety Invariants Verification

All 15 Phase F.9 Safety Invariants were verified via automated unit and integration tests:

1. **Missing Evidence Safety**: Missing mandatory evidence strictly evaluates to `INSUFFICIENT_INFORMATION` or `UNKNOWN`.
2. **Ambiguous Identity Quarantine**: Ambiguous scheme names route to `QUARANTINED`.
3. **Point-in-Time Protection**: Observation dates in the future relative to assessment date $T$ evaluate to `INVALID`.
4. **Data Degradation Monotonicity**: Data quality degradation strictly decreases transaction propensity.
5. **Re-ingestion Idempotency**: Re-ingesting identical raw payloads produces identical deterministic records.
6. **Immutable Dataset Versioning**: Dataset snapshots cannot be modified after creation.
7. **Provenance Preservation**: Source ID, run ID, and raw payload hash are preserved end-to-end.
8. **Plan Isolation**: Direct and Regular plans remain strictly distinct identities.
9. **Option Isolation**: Growth and IDCW options remain strictly distinct identities.
10. **Zero Merger Stitching**: NAV series across merged schemes are never stitched.
11. **Non-Blocking Benchmark Rule**: Benchmark absence does not universally block Fund Quality.
12. **Non-Zero TER/Load Defaults**: Missing TER/exit load evaluates to `None`, never `0.0`.
13. **Non-Inferred Riskometer**: Missing Riskometer evaluates to `None`, never inferred.
14. **No Direct Recommendations**: F.9 pipeline produces dataset snapshots ONLY, not BUY/SELL recommendations.
15. **Methodology Boundary Preservation**: Downstream financial methodology remains 100% untouched.

---

## 5. Downstream Integration

Validated dataset snapshot records are converted to `FundQualityDatasetInput` contracts using `ProductionDatasetPipeline.convert_to_fund_quality_dataset_input()`, seamlessly connecting to `FundQualityDatasetBuilder` and the `MetricEngine` without recreating metric logic.
