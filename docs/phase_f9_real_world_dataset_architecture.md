# PHASE F.9 — REAL-WORLD MUTUAL FUND DATASET ARCHITECTURE

## Architectural Overview

The Phase F.9 Data Pipeline provides a clean, modular data processing architecture separating raw source ingestion from downstream decision engines.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTHORITATIVE SOURCES                             │
│                  (AMFI, SEBI, AMC/RTA, NSDL/CDSL, Exchanges)                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Raw Payload
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER A: RAW SOURCE EVIDENCE (data/pipeline/ & models/production_dataset.py)│
│ - RawSourceEvidence: Preserves raw text, source URL, timestamp, run_id, hash │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Raw Fields
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER B: DETERMINISTIC NORMALIZATION (data/normalization/dataset_normalizer) │
│ - DatasetNormalizer: Converts dates, floats, plan types, option types       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Normalized Fields
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER C: CANONICAL ENTITY RESOLUTION (data/mapping/entity_resolver.py)      │
│ - EntityResolver & SchemeMaster: Maps AMFI/ISIN; quarantines ambiguous name │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Entity Resolved Records
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER D: DATA QUALITY VALIDATION (data/validation/dataset_validator.py)     │
│ - DatasetValidator: Enforces 8-state DataQualityState Model & bounds        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Validated Records
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER E: VERSIONED DATASET SNAPSHOT (models/production_dataset.py)          │
│ - VersionedDatasetSnapshot: Immutable snapshot, coverage ledger, audit run │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Snapshot Contracts
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ DOWNSTREAM DECISION ENGINE INTEGRATION                                      │
│ - FundQualityDatasetBuilder → MetricEngine → Fund Quality Scoring           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Directory Structure

- [`models/production_dataset.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/models/production_dataset.py): Layer A–E data contracts.
- [`data/ingestion/ingestion_run_manager.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/ingestion/ingestion_run_manager.py): Run execution logger and metrics manager.
- [`data/normalization/dataset_normalizer.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/normalization/dataset_normalizer.py): Layer B normalization logic.
- [`data/mapping/entity_resolver.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/mapping/entity_resolver.py): Layer C entity resolution & identity quarantine.
- [`data/validation/dataset_validator.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/validation/dataset_validator.py): Layer D 8-state validator & conflict handler.
- [`data/pipeline/production_dataset_pipeline.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/pipeline/production_dataset_pipeline.py): Master 5-layer pipeline orchestrator.
- [`data/reporting/dataset_quality_reporter.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/reporting/dataset_quality_reporter.py): Machine/human readable quality report generator.
- [`tests/data_quality/test_production_dataset_pipeline.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_production_dataset_pipeline.py): Pipeline integration tests.
- [`tests/data_quality/test_f9_safety_invariants.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/tests/data_quality/test_f9_safety_invariants.py): 15 Safety Invariants test suite.
