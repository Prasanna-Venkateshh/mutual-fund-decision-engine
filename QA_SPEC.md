# Mutual Fund Decision Engine — Quality Assurance Framework (QA Spec)

**Project:** `mutual-fund-decision-engine`  
**Version:** 1.0  
**Related Documents:** [`PRODUCT_SPEC.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/PRODUCT_SPEC.md), [`ARCHITECTURE.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/ARCHITECTURE.md), [`FEATURE_CATALOG.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/FEATURE_CATALOG.md)

---

## 1. Quality Assurance Philosophy

Quality assurance in the **Mutual Fund Decision Engine** extends far beyond traditional software unit testing. Because the platform impacts real investor decisions, QA must independently verify:
1. **Software correctness** (APIs, schemas, database operations, error handling).
2. **Financial correctness** (mathematical accuracy of returns, CAGR, downside deviation, tax math, exit load calculations).
3. **Data quality & integrity** (missing values, malformed dates, duplicate detection, quarantine isolation).
4. **Explainability & Provenance** (every output backed by verifiable evidence objects and authoritative source links).
5. **Historical Reproducibility** (ability to reconstruct past decisions without silently overwriting state).

---

## 2. QA Traceability Chain

Every product feature must maintain an unbroken end-to-end traceability chain before it is marked complete:

$$\text{Investor Requirement} \rightarrow \text{Financial Rule} \rightarrow \text{Feature Behavior} \rightarrow \text{Acceptance Criteria} \rightarrow \text{QA Test Case} \rightarrow \text{Test Execution} \rightarrow \text{Evidence} \rightarrow \text{Result} \rightarrow \text{Defect/Fix} \rightarrow \text{Regression}$$

---

## 3. Core QA Dimensions & Expectations

### 3.1 Functional QA
- Verifies that features perform as specified in [`FEATURE_CATALOG.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/FEATURE_CATALOG.md).
- Test cases verify profile updates, reverse onboarding countdown, goal setup, trade-off selections, and notification pause settings.

### 3.2 Financial & Business-Rule QA
- Independently verifies mathematical calculations against authoritative financial formulas.
- Test cases verify:
  - CAGR, rolling returns, XIRR calculations.
  - Capital gains tax computations (STCG/LTCG holding period boundaries).
  - Exit load penalty deductions.
  - Net after-tax switch benefit inequality:
    $$\text{Net Benefit} = \text{Expected Benefit of Switch} - \text{Capital Gains Tax} - \text{Exit Load} - \text{Transaction Fees} > 0$$

### 3.3 Data Quality QA
- Tests system behavior against corrupted, missing, stale, duplicate, or unvalidated input data.
- Test cases verify:
  - Non-positive NAV rejection ($NAV \le 0.0$).
  - Malformed date string rejection.
  - Quarantine isolation (`quarantine_records`) preventing invalid data from flowing downstream.
  - Idempotency (`INSERT OR IGNORE`) preventing raw observation duplication.

### 3.4 Explainability QA
- Verifies that every material score change, goal status update, or recommendation provides a structured evidence payload.
- Test cases verify:
  - Presence of material drivers in status changes (e.g., `On Track` $\rightarrow$ `Needs Attention`).
  - Absence of manufactured or unsupported factual claims.
  - Availability of 5 progressive disclosure levels (Default, Why, Detailed, Sources, Methodology).

### 3.5 Source Integrity & Provenance QA
- Verifies that factual assertions link directly to verified authoritative sources (AMFI, SEBI, RBI, Income Tax, AMC official).
- Test cases verify:
  - End-to-end relational join:
    $$\text{Normalized Record} \rightarrow \text{Canonical Scheme} \rightarrow \text{Mapping} \rightarrow \text{Raw Observation} \rightarrow \text{Source Registry}$$
  - Correct observation dates, retrieval timestamps, and source URLs.

### 3.6 Historical Reproducibility QA
- Verifies that past decisions can be reconstructed without being corrupted by today's NAV data or modified scoring rules.
- Test cases verify:
  - Preservation of immutable assessment snapshots (Section 11 of `ARCHITECTURE.md`).
  - Reproducibility equation:
    $$\text{Decision State} = \text{Data Snapshot} + \text{Methodology Version} + \text{Rule Version} + \text{Investor Profile Snapshot}$$

### 3.7 Uncertainty & Confidence QA
- Verifies that low data confidence suppresses strong investment recommendations.
- Test cases verify:
  - New funds (<1 year history) default to `Recommendation unavailable / Insufficient evidence`.
  - Ambiguous scheme names (missing plan/option text tokens) trigger `AMBIGUOUS` confidence and quarantine isolation.

---

## 4. Current Test Inventory (Implemented vs Future Slices)

### 4.1 Implemented & Verified Slice 1 Tests (15 Tests Passing)
The following automated tests have been implemented, executed, and verified in the repository:

| Test File | Test Case Name | Verified Behavior |
| :--- | :--- | :--- |
| `test_source_registry.py` | `test_load_sources_from_config` | Validates JSON source catalog loading and AMFI authority ranking. |
| `test_source_registry.py` | `test_authority_level_priority_sorting` | Validates authority priority sorting (AMFI > SEBI > RBI > CBDT). |
| `test_source_registry.py` | `test_update_retrieval_status` | Validates persistence of source retrieval status and timestamp updates in SQLite. |
| `test_nav_validation.py` | `test_valid_record` | Validates valid raw observation parsing ($NAV > 0$, valid date). |
| `test_nav_validation.py` | `test_missing_scheme_name_incomplete` | Rejects missing scheme names with `INCOMPLETE` quality state. |
| `test_nav_validation.py` | `test_negative_or_zero_nav_invalid` | Rejects $NAV \le 0.0$ as `INVALID`. |
| `test_nav_validation.py` | `test_malformed_nav_string_invalid` | Rejects non-numeric NAV strings as `INVALID`. |
| `test_nav_validation.py` | `test_malformed_date_invalid` | Rejects unparseable date strings as `INVALID`. |
| `test_nav_validation.py` | `test_batch_quarantine_isolation` | Verifies invalid raw records are isolated into `quarantine_records`. |
| `test_scheme_master.py` | `test_parse_plan_and_option` | Tests text parsing for `DIRECT`/`REGULAR` and `GROWTH`/`IDCW` tokens. |
| `test_scheme_master.py` | `test_resolve_canonical_scheme_exact_match` | Verifies exact match confidence assignment for numeric AMFI codes. |
| `test_scheme_master.py` | `test_ambiguous_scheme_name_quarantined` | Verifies scheme names lacking plan/option tokens are marked `AMBIGUOUS` and quarantined. |
| `test_scheme_master.py` | `test_isin_attribute_preservation` | Verifies `isin_growth` metadata preservation on `CanonicalScheme`. |
| `test_ingestion_pipeline.py` | `test_end_to_end_amfi_text_ingestion` | Tests full pipeline execution from raw text to database query. |
| `test_ingestion_pipeline.py` | `test_idempotent_raw_observation_persistence` | Verifies re-ingesting raw observations does not overwrite historical raw data (`INSERT OR IGNORE`). |

### 4.2 Planned Future QA Inventories (Slice 2 to Slice 16)
- **Slice 2 (Historical Data & SEBI Categories):** Multi-year NAV time-series completeness, split/merger adjustments, SEBI category mapping.
- **Slice 3 (Metrics Engine):** CAGR, rolling return, XIRR, downside deviation, max drawdown, Sharpe ratio financial test suite.
- **Slice 4 (Fund Scoring):** Composite scoring weights, category-relative peer ranking, dynamic downside weight boundary tests.
- **Slice 5 (Tax & Cost Engine):** STCG/LTCG holding period edge-case matrix, exit load deduction tests, net benefit inequality tests.
- **Slice 6 (Portfolio & Rebalancing):** Multi-level portfolio breakdown, winner protection verification, anti-return-chasing guardrail triggers.
