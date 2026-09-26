# Mutual Fund Decision Engine — Product Changelog

All notable changes, architectural refinements, and milestone acceptances for the `mutual-fund-decision-engine` project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned
- **Slice 2:** Historical NAV Time-Series Storage & SEBI Scheme Categorization Engine.
- **Slice 3:** Category-Aware Fund Performance & Risk Metrics Engine.

---

## [0.1.1] - Documentation Foundation & Slice 1 Close

### Added
- **[`FEATURE_CATALOG.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/FEATURE_CATALOG.md):** Comprehensive investor-facing product feature catalogue organized by the investor journey.
- **[`QA_SPEC.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/QA_SPEC.md):** Complete Quality Assurance framework covering functional, financial, data quality, explainability, provenance, and historical reproducibility QA.
- **[`DATA_SOURCES.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/DATA_SOURCES.md):** Authoritative data sources catalogue detailing AMFI, SEBI, RBI, CBDT, AMC Official, and Exchange sources with authority priority rankings.
- **[`DECISION_RULES.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/DECISION_RULES.md):** Framework for financial and product decision rules, defining score vs confidence separation, action definitions, net after-tax benefit math, winner protection, and goal trade-off engines.
- **[`CHANGELOG.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/CHANGELOG.md):** Formal product change history tracking milestones.

### Verified & Accepted
- **Slice 1 QA Acceptance Conditions Fulfilled:**
  - Added ISIN metadata preservation test in `tests/data_quality/test_scheme_master.py`.
  - Documented dataset reconciliation in `README.md` (4,046 raw, 207 validation quarantined, 3,839 validated, 786 mapping quarantined, 3,053 normalized).
  - Test suite: **15/15 unit & integration tests passing (0 errors, 0 failures, 0 warnings).**
  - **Slice 1 Status:** **ACCEPTED**.

---

## [0.1.0] - Slice 1 Data Foundation & Architectural Refinements

### Added
- **Source Registry (`data/ingestion/source_registry.py`):** Config-driven source catalog (`sources.json`) tracking authority levels, official URLs, update frequencies, and retrieval status.
- **Data Validation Gate (`data/validation/nav_validator.py`):** Technical validation gate enforcing $NAV > 0.0$, parseable date strings, and quarantine isolation (`quarantine_records`).
- **Scheme Master Boundary (`data/mapping/scheme_master.py`):** Canonical entity resolution module resolving raw scheme codes, ISINs, AMC names, Direct vs Regular plan types, and Growth vs IDCW option types with 4 confidence states (`EXACT_MATCH`, `HIGH_CONFIDENCE`, `AMBIGUOUS`, `UNMAPPED`).
- **NAV Normalization Engine (`data/normalization/nav_normalizer.py`):** Normalizes validated observations and quarantines ambiguous schemes.
- **SQLite Database Persistence (`db/database.py`, `db/schema.py`, `data/repositories/nav_repository.py`):** Relational tables enforcing raw data immutability (`INSERT OR IGNORE`) and complete provenance traceability.
- **Test Harness (`tests/`):** 14 initial automated unit and integration tests.

### Refactored
- **[`ARCHITECTURE.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/ARCHITECTURE.md):** Added explicit boundaries for Scheme Master (`data/mapping/`), Windfall Capital Allocation (`portfolio/allocation/`), and Immutable Assessment Audit Records (Section 11).
- **[`data/fetch_amfi.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/data/fetch_amfi.py):** Updated to execute official Slice 1 data pipeline.
- **[`metrics/returns.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/metrics/returns.py):** Refactored to serve as a pure mathematical module boundary placeholder.

---

## [0.0.1] - Project Initialisation

### Added
- **[`PRODUCT_SPEC.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/PRODUCT_SPEC.md):** Draft v0.1 Product Specification defining vision, principles, investor profile, goals, fund scoring, tax rules, and QA guidelines.
- **[`ARCHITECTURE.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/ARCHITECTURE.md):** Technical Blueprint v0.1 establishing 14 decoupled architectural layers.
- **Initial Prototype:** `amfi_data.csv`, `fetch_amfi.py` experimental script.
