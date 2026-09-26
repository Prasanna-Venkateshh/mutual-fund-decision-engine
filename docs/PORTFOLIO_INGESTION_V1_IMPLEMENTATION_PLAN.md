# PORTFOLIO TRANSACTION & HOLDINGS INGESTION (V1 STEP 2) — IMPLEMENTATION PLAN

**Document ID**: `docs/PORTFOLIO_INGESTION_V1_IMPLEMENTATION_PLAN.md`  
**Feature Scope**: V1 Step 2 — Portfolio Transaction & Holdings Ingestion  
**Governance Standard**: Governed Product Infrastructure Architecture  
**Status**: PLAN ONLY — REPOSITORY FORENSIC REVIEW COMPLETED  
**Date**: September 2026 UTC  

---

## 1. Current Architecture

The Mutual Fund Decision Engine operates on a 7-layer decoupled decision chain:
`DATA -> METRIC ENGINE -> FUND QUALITY -> RISK & SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION`.

Downstream engines (`PortfolioNeedEngine`, `EconomicBenefitEngine`, `DecisionOrchestrator`) evaluate investor portfolios via governed snapshots. Currently, `portfolio/need_models.py` defines the canonical model `PortfolioExposureSnapshot`, and `web/app.py` renders holding mocks or in-memory structures.

---

## 2. Existing Portfolio Contract

The canonical portfolio model is **`PortfolioExposureSnapshot`** ([`portfolio/need_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/portfolio/need_models.py#L70-L80)):

```python
@dataclass(frozen=True)
class PortfolioExposureSnapshot:
    portfolio_snapshot_id: str
    investor_id: str
    holding_ids: List[str] = field(default_factory=list)
    canonical_scheme_ids: List[str] = field(default_factory=list)
    total_valuation: Optional[float] = None
    is_valuation_available: bool = True
    observation_date: Optional[datetime] = None
```

To support granular holding-level details for ingestion, tax, exit load, and portfolio look-through without creating duplicate snapshot models, an explicit `PortfolioHoldingRecord` structure will be defined in `portfolio/need_models.py` (or `data/repositories/portfolio_repository.py`), storing:

### Field Taxonomy & Requirements:
- **`holding_id`**: REQUIRED (Unique string ID for the holding record).
- **`portfolio_snapshot_id`**: REQUIRED (Foreign key link to parent snapshot).
- **`investor_id`**: REQUIRED (Identity boundary scoping key).
- **`canonical_scheme_id`**: REQUIRED (Resolved canonical scheme ID, e.g. `CAN_AMFI_100044`).
- **`amfi_code`**: DERIVED / OPTIONAL (Resolved AMFI scheme code if available).
- **`isin`**: DERIVED / OPTIONAL (Resolved ISIN if available).
- **`scheme_name_raw`**: OPTIONAL (User/source raw uploaded scheme name string for audit display).
- **`units`**: REQUIRED (Number of units held; float. `0.0` is valid active units, distinct from `None`).
- **`cost_basis_amount`**: OPTIONAL (Total purchase cost basis in INR. `None` = unknown cost basis; `0.0` = zero cost basis).
- **`current_nav`**: OPTIONAL (Latest NAV used for valuation).
- **`current_value`**: OPTIONAL / DERIVED (`units * current_nav` or source provided valuation).
- **`acquisition_date`**: OPTIONAL (ISO Date of purchase. `None` = unknown purchase date).
- **`plan_type`**: DERIVED / OPTIONAL (`DIRECT` vs `REGULAR` resolved via Scheme Master).
- **`option_type`**: DERIVED / OPTIONAL (`GROWTH` vs `IDCW` resolved via Scheme Master).
- **`goal_id`**: OPTIONAL (Associated goal ID; `None` = general wealth / unassigned).
- **`source_provenance`**: REQUIRED (Provenance metadata string/dict documenting import source, file name, timestamp).

---

## 3. Existing Ingestion Paths

Forensic search across the codebase confirms:
- **`models/`**: Defines `investor_profile.py`, `goal_profile.py`, `suitability_assessment.py`, but no portfolio upload parser.
- **`data/adapters/`**: Contains `category_context_adapter.py`, `amfi_live_adapter.py`, but zero user portfolio CSV/CAS upload parsers.
- **`portfolio/`**: `need_engine.py` and `need_models.py` implement `PortfolioNeedEngine` and `PortfolioExposureSnapshot`, which expect pre-constructed snapshots.
- **`web/app.py`**: SCR-03 (`/wealth`) currently renders static HTML placeholder holdings.

**Conclusion**: No user portfolio ingestion parser currently exists. V1 Step 2 will introduce `data/adapters/portfolio_upload_adapter.py` and `data/repositories/portfolio_repository.py` as pure translation & persistence layers without mutating downstream financial logic.

---

## 4. V1 Requirement Boundary

### MANDATORY V1
1. **User-Provided CSV Ingestion**: Support structured CSV file upload via `POST /wealth/upload`.
2. **Identity Resolution**: Resolve rows via ISIN or AMFI Scheme Code to `canonical_scheme_id` using Scheme Master (`data/mapping/scheme_master.py`).
3. **Quarantine / Review Boundary**: Unresolved or ambiguous scheme rows MUST be placed into `QUARANTINE` state for user review and must not silently auto-map to arbitrary schemes.
4. **Preview & Confirmation Boundary**: Parsed CSV results must be presented in a preview UI (`/wealth/upload/preview`) before committing to database.
5. **Persistence**: Store snapshots and holdings in a new `portfolio_snapshots` and `portfolio_holdings` table in `db/backfill_f12_2.db`.
6. **Provenance & Privacy**: Capture source file name, row number, and timestamp without logging raw full portfolio contents or sensitive account numbers.

### OPTIONAL V1 / V2 BOUNDARY
- **CAS PDF Parser (Password-Protected)**: Deferred to V2 (prevents complex PDF parsing and password handling in V1).
- **Automated Broker Sync**: Explicitly PROHIBITED across all versions.

---

## 5. Proposed Input Format (Minimum Safe CSV Contract)

The V1 upload adapter will support standard portfolio CSV exports containing the following mandatory/optional columns:

| CSV Column Header | Standard Aliases | Semantics & Handling |
| :--- | :--- | :--- |
| `ISIN` | `isin`, `ISIN_Code` | **Primary Identity Key** (12-char alphanumeric). |
| `AMFI_Code` | `amfi_code`, `Scheme_Code`, `amfi` | **Secondary Identity Key** (Numeric AMFI scheme code). |
| `Scheme_Name` | `scheme_name`, `Fund_Name` | Display name; used for fallback display/search, **NOT for silent identity matching**. |
| `Units` | `units`, `quantity`, `balance_units` | Required numeric units held (`float`). |
| `Cost_Basis` | `cost_basis`, `purchase_value`, `invested_amount` | Optional purchase cost basis in INR (`float` or `None`). |
| `Acquisition_Date` | `purchase_date`, `acquisition_date`, `trx_date` | Optional purchase date (`YYYY-MM-DD`). |
| `Goal_ID` | `goal_id`, `goal` | Optional goal assignment ID (`str` or `None`). |

---

## 6. Identity Resolution Architecture

Identity resolution MUST follow a strict, governed hierarchy:

```
[ Uploaded CSV Row ]
         |
         v
  Has Valid ISIN? --------(YES)--------> Query Scheme Master by ISIN -------> [ Resolve canonical_scheme_id ]
         | (NO)                                                                             |
         v                                                                                  v
Has Valid AMFI Code? ----(YES)--------> Query Scheme Master by AMFI Code --> [ Check Plan/Option Consistency ]
         | (NO)                                                                             |
         v                                                                                  v
Scheme Name Matching Alone -------------> [ PROHIBITED FROM SILENT COMMIT ] ------> [ QUARANTINE / USER REVIEW ]
```

- **Direct/Regular & Growth/IDCW**: Established strictly from authoritative Scheme Master records tied to the resolved ISIN/AMFI code.
- **Ambiguous Schemes**: Any row where ISIN/AMFI code is missing or unmapped is flagged `QUARANTINE_UNRESOLVED_SCHEME`.

---

## 7. Direct / Regular and Growth / IDCW Handling

- **Authoritative Resolution**: When ISIN or AMFI code resolves via Scheme Master, `plan_type` (`DIRECT` vs `REGULAR`) and `option_type` (`GROWTH` vs `IDCW`) are retrieved from the database record.
- **No Name Guessing**: The system will NOT infer `DIRECT` or `GROWTH` from string matching (e.g. searching for `"Dir"` in scheme name) if authoritative metadata is missing.
- **Fallback**: If unmapped, the row is quarantined as requiring user plan/option confirmation.

---

## 8. Quantity / Value / Cost Semantics

The adapter enforces explicit non-null distinction:
- **`units = 0.0`**: Valid active holding with 0 units (e.g. fully redeemed fund tracked for tax history). Distinct from missing units.
- **`units = None`**: Missing required column or invalid non-numeric parsing. Triggers `IMPORT_FAILED_ROW`.
- **`cost_basis_amount = None`**: Cost basis unknown. Downstream `EconomicBenefitEngine` evaluates tax hurdle as `BENEFIT_UNCERTAIN`.
- **`cost_basis_amount = 0.0`**: Zero cost basis (e.g. 100% taxable gain capital).
- **Valuation**: `current_value` is calculated dynamically as `units * current_nav` using point-in-time NAV from `nav_repository.py`.

---

## 9. Transaction Dates & Tax Boundary

- **Acquisition Dates**: Preserved when provided in source CSV to enable STCG (< 12 months for equity, < 36 months for debt) vs LTCG tax classification in `EconomicBenefitEngine`.
- **Missing Acquisition Date**: Represented as `None`. The ingestion layer does NOT invent fake purchase dates. Downstream engines mark tax friction as `UNCERTAIN` when dates are required.
- **No Tax Engine Redesign**: Ingestion only feeds existing fields into `EconomicBenefitIntegrationContract`.

---

## 10. Portfolio Source Provenance

Every persisted holding row stores an immutable `source_provenance` JSON payload:

```json
{
  "source_type": "USER_CSV_UPLOAD",
  "source_file_name": "my_portfolio_2026.csv",
  "import_timestamp_utc": "2026-09-17T13:30:00Z",
  "row_number": 4,
  "raw_identifier_provided": {"isin": "INF200K01123", "amfi_code": "100044"},
  "resolution_status": "RESOLVED_EXACT_ISIN",
  "canonical_scheme_id": "CAN_AMFI_100044"
}
```

---

## 11. File Security & Validation Controls

The upload endpoint will enforce strict input security controls:
1. **File Size Limit**: Maximum $5 \text{ MB}$ per CSV file upload.
2. **Content Validation**: Must be valid UTF-8 text with MIME type `text/csv` or `text/plain`.
3. **CSV Formula Injection Defense**: Any cell value starting with `=`, `+`, `-`, or `@` is stripped of leading formula triggers prior to parsing to prevent CSV injection.
4. **Path Traversal Defense**: File names are sanitized using `os.path.basename()` and never stored as raw file paths.
5. **Row Count Limit**: Maximum 500 rows per portfolio file upload to prevent CPU/memory exhaust.

---

## 12. Privacy & Sensitive Data Safeguards

- **No Upload Retention**: Uploaded raw CSV files are processed in-memory and discarded. Raw files are NOT saved to disk.
- **Zero Sensitive Logging**: Application logs log ONLY `investor_id`, `portfolio_snapshot_id`, `row_count`, `resolved_count`, and `quarantine_count`. Full holdings or account numbers are NEVER logged.

---

## 13. Portfolio Versioning & Reproducibility

- **Immutable Portfolio Snapshots**: Similar to `InvestorProfileSnapshot`, portfolio updates write a new `PortfolioExposureSnapshot` with an incremented version/timestamp and `is_current = 1`.
- **Historical Assessment Traceability**: Audit state records (`AssessmentAuditLog`) reference `portfolio_snapshot_id`, guaranteeing 100% point-in-time decision reproducibility.

---

## 14. Multiple Goals Attribution

- Holdings can have an explicit `goal_id` assignment if supplied by the CSV or user preview.
- Holdings without `goal_id` default to `goal_id = None` (General Wealth portfolio).
- The engine does NOT force unassigned holdings into specific goals.

---

## 15. Duplicates & Row Scoping

- Multiple CSV rows with the same `canonical_scheme_id` (representing separate transaction lots/purchases) are preserved as distinct `PortfolioHoldingRecord` items under the same snapshot.
- Exact duplicate file rows (identical ISIN, units, cost, date) trigger a `DUPLICATE_ROW_WARNING` in the preview screen for user confirmation.

---

## 16. Import Status States & Quarantine Workflow

An import operation processes through 5 defined lifecycle states:

```
[ Upload CSV ] ---> IMPORT_PENDING ---> [ Parse & Resolve ]
                                                |
              +---------------------------------+---------------------------------+
              |                                 |                                 |
              v                                 v                                 v
    (100% Resolved Rows)              (Some Unresolved Rows)            (Malformed File / 0 Rows)
              |                                 |                                 |
              v                                 v                                 v
       [ IMPORT_VALID ]            [ IMPORT_REQUIRES_REVIEW ]            [ IMPORT_FAILED ]
              |                                 |                                 |
              v                                 v                                 v
    [ User Confirms Preview ]       [ User Resolves Quarantined ]       [ Render Error Notice ]
              |                                 |
              +---------------------------------+
                                |
                                v
                   [ Persist Snapshot to DB ]
```

---

## 17. User Review Before Commit (UX Integration)

- **Flow**: `POST /wealth/upload` parses file $\longrightarrow$ renders `SCR-03` Preview Modal (`/wealth/upload/preview`) showing resolved vs quarantined holdings $\longrightarrow$ User clicks **"Confirm & Persist Portfolio"** $\longrightarrow$ System writes snapshot to database and updates `/wealth`.
- **No Silent Mutate**: Uploading a file NEVER automatically overwrites existing portfolios without explicit confirmation.

---

## 18. Existing Portfolio Overwrite / Merge Policy

When an existing portfolio snapshot exists for `investor_id`:
- User is prompted in preview screen:
  1. **Replace Existing Portfolio** (Deactivates current snapshot, sets new snapshot as `is_current = 1`).
  2. **Append / Merge Holdings** (Constructs new combined snapshot containing previous + new holdings).
- Default selection is **Replace Existing Portfolio** with explicit confirmation.

---

## 19. Broker & CAS Boundary

- **Broker Integration**: 0% broker API code, 0% trade execution, 0% credential collection.
- **CAS PDF Parser**: Excluded from V1.

---

## 20. Test Plan

Comprehensive unit & integration test suite (`tests/integration/test_portfolio_ingestion.py`):
1. `test_csv_upload_valid_isin_resolution()`
2. `test_csv_upload_valid_amfi_code_resolution()`
3. `test_csv_upload_unmapped_scheme_quarantines_row()`
4. `test_csv_formula_injection_sanitization()`
5. `test_csv_units_zero_preserved_distinct_from_none()`
6. `test_portfolio_snapshot_persistence_and_restart()`
7. `test_existing_portfolio_non_destructive_update()`
8. `test_financial_regression_suite_unaffected()`

---

## 21. Financial Regression & Decoupling Boundary

The portfolio ingestion adapter operates strictly as an input converter:
`CSV Upload -> PortfolioUploadAdapter -> PortfolioRepository -> PortfolioExposureSnapshot`.
Zero financial engines (`scoring/`, `risk/`, `portfolio/need_engine.py`, `economic_benefit/`, `action/`, `integration/orchestrator.py`) will be modified.

---

## 22. Proposed File Changes

- **[NEW] `data/adapters/portfolio_upload_adapter.py`**: CSV parsing, identity resolution, formula sanitization, quarantine logic.
- **[NEW] `data/repositories/portfolio_repository.py`**: SQLite CRUD for `portfolio_snapshots` and `portfolio_holdings`.
- **[MODIFY] `portfolio/need_models.py`**: Add `PortfolioHoldingRecord` dataclass.
- **[MODIFY] `web/app.py`**: Add `/wealth/upload` POST handler and preview modal in SCR-03 (`/wealth`).
- **[NEW] `tests/integration/test_portfolio_ingestion.py`**: Integration test suite.

---

## 23. Open Governance Decisions

1. **Default Overwrite Mode**: Confirmed default is **Replace Existing Portfolio** upon explicit user confirmation.
2. **Unresolved Holding Gating**: Confirmed portfolio assessments CAN proceed with partial portfolios, but unmapped quarantined holdings issue a `PARTIAL_PORTFOLIO_CONFIDENCE_PENALTY`.
