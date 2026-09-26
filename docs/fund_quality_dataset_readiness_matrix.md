# Fund Quality Dataset Readiness Matrix

**Execution Timestamp:** 2026-09-09 UTC  
**Phase Status:** **PHASE D.5 ACCEPTED**  
**Document Version:** 1.0.0  

---

## Dataset Input Readiness Evaluation

The following matrix documents the current implementation, source authority, historical depth, current availability, validation status, confidence handling, provenance tracking, and gap classification for all candidate inputs to the future Fund Quality Scoring Engine.

| Input Dimension | Implemented Function / Module | Primary Source | Historical Depth | Current Availability | Validation Status | Confidence Handling | Provenance Preserved? | Gap Classification |
|---|---|---|---|---|---|---|---|---|
| **Daily NAV Series** | `data/ingestion/amfi_pipeline.py` | AMFI Official Portal | 2024–Present | High (Daily Updates) | **VALIDATED** | High ($1.0$) | Yes (URL, Timestamp) | **NONE (READY)** |
| **Historical NAV Series** | `data/ingestion/historical_nav_pipeline.py` | AMFI / AMC Archives | Endpoint & Pipeline Validated (2010–Present) | Ingestion & Ledger Validated | **SOURCE/PIPELINE VALIDATED** | High ($0.90$) | Yes (Raw Text Logged) | **PARTIAL (Full Universe Coverage Not Established)** |
| **Canonical Scheme Identity** | `data/mapping/lifecycle_resolver.py` | AMFI / SEBI Master | 2010–Present | Complete Canonical UUID | **VALIDATED** | High ($1.0$) | Yes (Mapping Table) | **NONE (READY)** |
| **Point-in-Time Lifecycle Events** | `data/ingestion/sebi_*_extractor.py` | SEBI Orders & AMC Disclosures | 2010–Present | High (89+ Events Validated) | **VALIDATED** | High ($0.90$) | Yes (Direct URL Link) | **NONE (READY)** |
| **Return Metrics (CAGR, Rolling)** | `metrics/returns.py` | Calculated from NAV | Derived (2010–Present) | Dynamic Calculation | **VALIDATED** | High ($1.0$) | Yes (Platform Calculated) | **NONE (READY)** |
| **Risk Metrics (Volatility, Drawdown)** | `metrics/risk.py` | Calculated from NAV | Derived (2010–Present) | Dynamic Calculation | **VALIDATED** | High ($1.0$) | Yes (Platform Calculated) | **NONE (READY)** |
| **Maturity / History Length** | `metrics/maturity.py` | Calculated from NAV | Derived (2010–Present) | Dynamic Calculation | **VALIDATED** | High ($1.0$) | Yes (Platform Calculated) | **NONE (READY)** |
| **Scheme Category / Subcategory** | `config/lifecycle/lifecycle_config.yaml` | SEBI 2017 Categorization | 2017–Present | High | **VALIDATED** | Medium ($0.85$) | Yes (Config & Circular) | **NONE (READY)** |
| **Plan Type (Direct / Regular)** | `data/mapping/scheme_parser.py` | AMFI Master Text | 2013–Present | High (Parsed from Name) | **VALIDATED** | High ($0.95$) | Yes (Raw Scheme Name) | **NONE (READY)** |
| **Option Type (Growth / IDCW)** | `data/mapping/scheme_parser.py` | AMFI Master Text | 2010–Present | High (Parsed from Name) | **PARTIAL** | Medium ($0.75$) | Yes (Raw Scheme Name) | **NON-BLOCKING (IDCW Total Return Adjustment Pending)** |
| **Total Expense Ratio (TER)** | `data/repositories/ter_repository.py` | AMC Statutory Disclosures | 2018–Present | Current TER Available | **PARTIAL** | Medium ($0.70$) | Yes (AMC Disclosure URL) | **NON-BLOCKING (Pre-2018 Historical TER Absent)** |
| **Benchmark Index Data (TRI)** | *Not Implemented* | NSE / BSE Index Feeds | None | Pending Integration | **NOT IMPLEMENTED** | Low ($0.00$) | No | **NON-BLOCKING (Optional for Initial Quality Scoring)** |
| **AMC Metadata & Ownership** | `config/lifecycle/lifecycle_config.yaml` | SEBI AMC Register | 2010–Present | High | **VALIDATED** | High ($0.95$) | Yes (SEBI Register) | **NONE (READY)** |

---

## Gap Summary Analysis

- **Blocking Gaps:** **0**
- **Non-Blocking Gaps:** **3**
  1. *Universe-Wide Historical NAV Coverage:* While the AMFI historical NAV retrieval endpoint, acquisition pipeline, provenance tracking, and coverage-ledger machinery are fully validated, complete 2010–present historical coverage across the entire eligible scheme universe is not yet established and will be verified dynamically during dataset construction.
  2. *Historical TER Depth (Pre-2018):* TER metrics will default to `None` for historical windows prior to 2018, gracefully handled by dataset confidence scoring without synthetic zero substitution.
  3. *IDCW Total-Return Adjustment:* IDCW NAV series require dividend reinvestment/payout additions for accurate historical CAGR comparison against Growth options. Growth options remain the primary validated dataset input.
