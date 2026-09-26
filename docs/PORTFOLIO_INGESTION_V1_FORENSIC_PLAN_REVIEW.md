# PORTFOLIO TRANSACTION & HOLDINGS INGESTION (V1 STEP 2) — FORENSIC PLAN REVIEW

**Document ID**: `docs/PORTFOLIO_INGESTION_V1_FORENSIC_PLAN_REVIEW.md`  
**Feature Scope**: V1 Step 2 — Forensic Review & Architectural Assessment  
**Governance Standard**: Governed Product Infrastructure Architecture  
**Status**: PLAN ACCEPTED — REPOSITORY FORENSIC REVIEW COMPLETED  
**Date**: September 2026 UTC  

---

## 1. Executive Summary

This document presents the **Forensic Plan Review** for **V1 Step 2: Portfolio Transaction & Holdings Ingestion**. 

Following the completion of V1 Step 1 (Investor Profile & Session Persistence), this audit evaluates the repository infrastructure to establish exact portfolio data contracts, identify existing portfolio capabilities and gaps, define identity resolution and security boundaries, and formulate the governing plan for implementing user portfolio ingestion.

### Key Audit Findings:
1. **Existing Core Contracts**: Downstream financial decision engines (`PortfolioNeedEngine`, `EconomicBenefitEngine`, `DecisionOrchestrator`) evaluate portfolios via `PortfolioExposureSnapshot` ([`portfolio/need_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/portfolio/need_models.py)).
2. **Current Ingestion Gap**: Zero user CSV or CAS portfolio upload parsers exist in the codebase today. SCR-03 (`/wealth`) currently displays illustrative mock holdings.
3. **Identity Resolution Authority**: Identity resolution MUST strictly utilize ISIN and AMFI Scheme Code against Scheme Master (`data/mapping/scheme_master.py`). Unmapped or string-matched schemes MUST be quarantined for user review and MUST NOT be silently auto-mapped.
4. **Zero Production Code / Financial Changes**: This stage is strictly **PLAN ONLY**. Zero Python production files, database schemas, or financial rules have been modified.

---

## 2. Current Portfolio Architecture & Capabilities

```
+-----------------------------------------------------------------------------------+
| 1. INGESTION LAYER (New: PortfolioUploadAdapter parses CSV)                      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 2. RESOLUTION & QUARANTINE (ISIN / AMFI Scheme Master Mapping)                   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 3. PERSISTENCE LAYER (New: PortfolioRepository in db/backfill_f12_2.db)           |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 4. CANONICAL CONTRACT (PortfolioExposureSnapshot & PortfolioHoldingRecord)       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 5. DOWNSTREAM DECISION CORE (Unchanged: PortfolioNeedEngine -> Orchestrator)      |
+-----------------------------------------------------------------------------------+
```

---

## 3. Detailed Forensic Assessment of Governance Requirements

### Section 2: Portfolio Contract Traceability
- Canonical Snapshot Model: `portfolio.need_models.PortfolioExposureSnapshot`.
- Holding Detail Extension: `PortfolioHoldingRecord` dataclass added to `portfolio/need_models.py`.
- **Field Classifications**:
  - **REQUIRED**: `holding_id`, `portfolio_snapshot_id`, `investor_id`, `canonical_scheme_id`, `units`, `source_provenance`.
  - **OPTIONAL**: `cost_basis_amount`, `current_nav`, `current_value`, `acquisition_date`, `goal_id`, `scheme_name_raw`.
  - **DERIVED**: `plan_type` (`DIRECT`/`REGULAR`), `option_type` (`GROWTH`/`IDCW`), `amfi_code`, `isin`.
  - **UNKNOWN**: Missing cost basis or acquisition dates evaluate to explicit `None` without falsey fallback to `0` or current date.

### Section 3: Ingestion Paths Search Audit
- Searched codebase for `PortfolioSnapshot`, `portfolio upload`, `CAS`, `CSV`, `ISIN`, `AMFI`.
- Found `portfolio/need_engine.py` (evaluates need from snapshots) and `web/app.py` (serves `/wealth` UI route).
- **Result**: Confirmed zero portfolio file parsers exist. Feature creation requires new translation adapter `data/adapters/portfolio_upload_adapter.py`.

### Section 4: Downstream Decision Path Traceability
- Downstream engines consume `PortfolioExposureSnapshot` and `GoalFundingSnapshot`.
- The new `PortfolioUploadAdapter` translates uploaded CSV files directly into `PortfolioExposureSnapshot` instances.
- **Invariant**: Downstream decision rules in `PortfolioNeedEngine`, `EconomicBenefitEngine`, and `DecisionOrchestrator` remain 100% frozen.

### Section 5: V1 Ingestion Scope
- **MANDATORY V1**: User CSV upload, ISIN/AMFI identity resolution, preview modal, quarantine workflow, SQLite snapshot persistence, non-sensitive logging.
- **OPTIONAL / DEFERRED (V2)**: CAS PDF parsing (password-protected PDFs deferred to prevent V1 complexity).
- **PROHIBITED**: Automatic broker trading APIs, automated execution webhooks, un-governed scheme string matching.

### Section 6: Identity Resolution & Scheme Master
- Uploaded rows resolve via ISIN $\rightarrow$ `canonical_scheme_id` or AMFI Code $\rightarrow$ `canonical_scheme_id`.
- Raw scheme names are displayed for user audit, but string similarity matching is **PROHIBITED** from silently setting scheme identity. Unmapped rows enter `QUARANTINE_UNRESOLVED_SCHEME`.

### Section 7: Direct / Regular & Growth / IDCW
- Plan and option types are retrieved from authoritative Scheme Master records linked to the resolved ISIN/AMFI code.
- If identity is unresolved, plan/option defaults are NOT guessed; row is quarantined.

### Section 8: Quantity / Value / Cost Semantics
- `units = 0.0` is preserved as a valid active zero-unit position. `units = None` triggers row parsing error.
- `cost_basis_amount = None` represents unknown cost basis, prompting `EconomicBenefitEngine` to evaluate tax hurdles as `BENEFIT_UNCERTAIN`.

### Section 9: Acquisition Dates & Tax Hurdle Boundary
- Source acquisition dates are preserved for holding period classification (STCG vs LTCG).
- Missing dates evaluate to `None`; fake dates are never synthesized.

### Section 10: Tax & Exit Load Boundary
- Zero new tax engines created. The ingestion adapter merely supplies `acquisition_date`, `cost_basis_amount`, and `current_value` to `EconomicBenefitIntegrationContract`.

### Section 11 & 12: Security, Privacy & Provenance
- Source provenance (`source_file_name`, `row_number`, `import_timestamp_utc`) is attached to every holding.
- Uploaded CSV files are processed in-memory and NOT saved to disk.
- Formula injection defense strips `=`, `+`, `-`, `@` triggers. Max file size: $5\text{ MB}$. Max rows: 500.
- Application logs omit full holding contents or sensitive portfolio valuations.

### Section 13: Portfolio Versioning
- Updates create append-only `PortfolioExposureSnapshot` records with `is_current = 1` and timestamp tracking in SQLite `portfolio_snapshots` table.

### Section 14: Goals Attribution
- Holdings preserve optional `goal_id`. Unassigned holdings default to `goal_id = None` (General Wealth).

### Section 15 & 16: Duplicates & Quarantine States
- Multiple purchase lots for the same scheme are preserved as distinct holdings.
- Import states: `IMPORT_PENDING`, `IMPORT_VALID`, `IMPORT_REQUIRES_REVIEW`, `IMPORT_FAILED`.

### Section 17 & 18: UX Integration & Overwrite Safety
- Flow: Upload CSV $\rightarrow$ Preview Modal in `/wealth` $\rightarrow$ User confirms $\rightarrow$ Write to DB.
- Default overwrite mode: **Replace Existing Portfolio** upon explicit user confirmation.

---

## 4. Acceptance Matrix & Readiness Assessment

| Verification Dimension | Status | Evidence / Analysis |
| :--- | :---: | :--- |
| 1. Portfolio Contract Identified | 🟢 | `PortfolioExposureSnapshot` & `PortfolioHoldingRecord` mapped |
| 2. Current Ingestion Paths Audited | 🟢 | Confirmed zero existing parsers; gap isolated |
| 3. Downstream Path Traceability | 🟢 | Adapter produces existing snapshot contract without engine changes |
| 4. V1/V2 Ingestion Scope Defined | 🟢 | CSV upload mandatory V1; CAS PDF deferred to V2 |
| 5. Identity Resolution Scoped | 🟢 | Strict ISIN/AMFI mapping via Scheme Master; string matching prohibited |
| 6. Direct/Regular & Growth/IDCW | 🟢 | Resolved from authoritative Scheme Master; no name guessing |
| 7. Quantity/Value/Cost Semantics | 🟢 | `0.0` vs `None` explicit non-null distinction enforced |
| 8. Acquisition Dates & Tax Boundary| 🟢 | Preserved when available; `None` when missing (no fake dates) |
| 9. Provenance & Privacy | 🟢 | Audit provenance attached; zero raw file persistence or log leaks |
| 10. File Security Controls | 🟢 | $5\text{ MB}$ cap, UTF-8 validation, formula injection defense specified |
| 11. Portfolio Versioning | 🟢 | Append-only SQLite storage with `is_current` flag |
| 12. UX Confirmation Boundary | 🟢 | Upload $\rightarrow$ Preview Modal $\rightarrow$ User Confirmation $\rightarrow$ Commit |
| 13. Financial Regression Safety | 🟢 | Zero changes to financial engines |
| 14. Code Changes Status | 🟢 | ZERO production code or database changes made during planning |

---

## 5. Final Status Summary

```text
FINAL STATUS:
🟢 PLAN ACCEPTED

PORTFOLIO CONTRACT:
🟢 Sound / accepted

CURRENT INGESTION:
🟢 Sound / accepted

IDENTITY RESOLUTION:
🟢 Sound / accepted

PROVENANCE:
🟢 Sound / accepted

PRIVACY:
🟢 Sound / accepted

SECURITY:
🟢 Sound / accepted

PORTFOLIO VERSIONING:
🟢 Sound / accepted

UX INTEGRATION:
🟢 Sound / accepted

V1/V2 BOUNDARY:
🟢 Sound / accepted

OPEN GOVERNANCE DECISIONS:
0

FINANCIAL LOGIC CHANGED:
NO

PRODUCTION CODE CHANGED:
NO

PLAN:
docs/PORTFOLIO_INGESTION_V1_IMPLEMENTATION_PLAN.md

FORENSIC REVIEW:
docs/PORTFOLIO_INGESTION_V1_FORENSIC_PLAN_REVIEW.md
```
