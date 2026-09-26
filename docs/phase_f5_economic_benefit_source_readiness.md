# Phase F.5 Economic Benefit Source Readiness (Verified - F.5.2)

## 1. Domain Data Ownership & Source Readiness Assessment

| Data Domain | Required Attributes | Authoritative Source / Owner | Implementation Status | Source Readiness Status |
| :--- | :--- | :--- | :--- | :--- |
| **Capital Gains Tax Rules** | STCG/LTCG rates, holding period cutoffs (12m/36m), indexation rules, grandfathering | Proposed Income Tax Module / Config (Proposed path: `tax/rules.py`) | Statutory schema defined in spec; module code does NOT exist on disk | 🟡 SOURCE IDENTIFIED (Proposed Target) |
| **Exit Load Structure** | Exit load slab percentages, holding period thresholds, scheme-specific exceptions | AMFI Scheme Master / Fund Factsheets | Partial NAV/Scheme data in DB; load slab parser pending | 🟡 SOURCE IDENTIFIED |
| **Transaction Costs** | STT rates, stamp duty (0.005%), AMC transaction charges | SEBI / Statutory Fee Schedule | Statutory rates specified; platform fee schema pending | 🟡 SOURCE IDENTIFIED |
| **Tax Lot History** | Acquisition date, acquisition cost basis, unit quantity, folio identifier | Investor Portfolio / Depository Ledger | External dependency; user input / CAS parser pending | 🔴 SOURCE PENDING |
| **Expected Improvement Model** | Forward-looking expected return difference, risk-adjusted alpha expectation | Metric Engine / Forward Return Model | Historical metrics available; forward return model undefined | 🔴 NOT IMPLEMENTED |
| **Candidate Scheme Metadata** | Asset class, sub-category, TER, benchmark | AMFI / NAV Ingestion Pipeline | Active in database via `source_registry.py` | 🟢 SOURCE INTEGRATED |

---

## 2. Provenance Audit of Tax Module (`tax/rules.py`)
- **Existence Verification:** `tax/rules.py` **does NOT exist** in the repository filesystem.
- **Historical Provenance:** Zero files or commits in `tax/` were created or modified during F.5, F.5.1, or prior phases.
- **Specification Role:** In F.5/F.5.1/F.5.2 documentation, `tax/rules.py` is cited strictly as an example target path for a future dedicated Tax Engine module.
- **Scope Compliance:** Neither F.5, F.5.1, nor F.5.2 implemented, modified, or executed any tax calculation code.

---

## 3. Distinction of Source Readiness States
- **SOURCE INTEGRATED:** Operational in production codebase and active database.
- **SOURCE IDENTIFIED:** Authoritative regulatory or statutory owner established, but ingestion/parsing pipeline is pending.
- **SOURCE PENDING:** External dependency not yet available in platform architecture.
- **NOT IMPLEMENTED:** Financial methodology or model not yet created.

---

## 4. Dependency Remediation Plan
1. **Tax Engine Contract:** Establish formal versioned interface with a dedicated `TaxEngine` before attempting production Economic Benefit code.
2. **Exit Load Parser:** Extend scheme metadata ingestion to capture structured exit load schedules from AMFI or fund house factsheets.
3. **Forward Improvement Model:** Develop an explicit, governed methodology for expected return differences rather than relying on raw trailing CAGR.
