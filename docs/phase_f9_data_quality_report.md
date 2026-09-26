# Phase F.9 Dataset Quality Report — Version F9.2.0_LIVE

**Snapshot ID:** `snap_F9_2_0_LIVE_23e08268`  
**Creation Timestamp (UTC):** `2026-09-14T08:18:50.158225+00:00`  
**Production Recommendation Eligible:** `NO`

## 1. Executive Summary & Pipeline Metrics

| Metric | Count | Percentage | Description |
| :--- | :--- | :--- | :--- |
| **Total Schemes Count** | 14361 | 100.0% | Active schemes in snapshot |
| **Total Records Processed** | 14361 | 100.0% | Mutually exclusive primary state sum |
| **Valid Records** | 8082 | 56.3% | Complete & unambiguous records |
| **Partial Records** | 0 | 0.0% | Valid with non-critical missing fields |
| **Invalid Records** | 241 | 1.7% | Structural errors / non-positive NAV |
| **Quarantined Records** | 6038 | 42.0% | Ambiguous textual plan/option parsing |
| **Conflicted Records** | 0 | 0.0% | Source authority conflicts |
| **Flagged Quarantine Occurrences** | 6279 | N/A | Diagnostic boolean flag (6,038 Quarantined + 241 Invalid) |

## 2. Missing-Field Uncertainty Distribution

| Field | Missing Count | Handling Policy |
| :--- | :--- | :--- |
| **NAV Value** | 0 | Explicit `None` (Yields `INSUFFICIENT_INFORMATION`) |
| **Total Expense Ratio (TER)** | 14361 | Explicit `None` (Never defaults to 0.0) |
| **SEBI Riskometer Label** | 14361 | Explicit `None` (Never inferred) |
| **Benchmark Index Name** | 14361 | Explicit `None` (Never assigned arbitrarily) |

## 3. Ingestion Runs Audit

| Run ID | Source ID | Status | Total Processed | Valid | Quarantined |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `run_amfi_official_d039ecbe` | `AMFI_OFFICIAL` | `SUCCESS` | 14361 | 8082 | 6038 |

## 4. Production Readiness Interpretation

> [!NOTE]
> **Pipeline Operational Status**: Successful pipeline execution demonstrates data infrastructure correctness.  
> **Financial Recommendation Status**: Data availability does NOT constitute authorization for live production recommendations or real-money execution.