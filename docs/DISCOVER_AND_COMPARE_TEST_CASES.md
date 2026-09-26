# Step 6.2 — Discover Fund Universe Audit, Mutual Fund Filters & 10-Fund Comparison Test Specification

## A. Fund Universe Audit & Ingestion Forensic Summary

| Attribute | Count / Finding | Description / Source of Truth |
| :--- | :--- | :--- |
| **Total Canonical Schemes** | `17,507` | Count of records in `db/backfill_f12_2.db` table `canonical_schemes`. |
| **Unique AMCs (Fund Houses)** | `327` | Distinct fund house entities mapped in authoritative metadata. |
| **Plan Types** | `DIRECT`, `REGULAR` | Authoritative plan taxonomy. |
| **Option Types** | `GROWTH`, `IDCW`, `BONUS` | Authoritative dividend/growth option taxonomy. |
| **Data Scope Wording** | "Current Canonical Universe" | All available schemes within the application's current canonical snapshot database. |

---

## B. Nippon India Nifty 50 Direct Growth Forensic Investigation

- **Target Query**: "Nippon India Index Fund Nifty 50 Plan Direct Growth"
- **Canonical Scheme ID**: `CAN_AMFI_118741`
- **Canonical Scheme Name**: `"Nippon India Index Fund - Nifty 50 Plan - Direct Plan Growth Plan - Growth Option"`
- **Primary AMFI Code**: `118741`
- **ISIN (Growth)**: `INF204K01UQ2`
- **Root Cause Analysis**:
  - The fund was present in `canonical_schemes` under `CAN_AMFI_118741`.
  - Single exact substring matching (`LIKE '%Nippon India Index Fund Nifty 50 Plan Direct Growth%'`) failed because the stored scheme name contains punctuation ("-") and extra descriptors ("Plan - Direct Plan Growth Plan - Growth Option").
- **Resolution**:
  - Implemented space-separated multi-token search in `/api/schemes/search`.
  - Splitting search input into tokens (`Nippon`, `India`, `Index`, `Fund`, `Nifty`, `50`, `Direct`, `Growth`) and generating `scheme_name LIKE '%token1%' AND scheme_name LIKE '%token2%' ...` successfully matches `CAN_AMFI_118741`.

---

## C. Discovery & Filtering Test Matrix (DISC-01 to DISC-15)

| Test ID | Objective | Preconditions | Data Source | Action | Expected Result | Database Expectation | UI Expectation | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DISC-01** | Verify total canonical universe count | `db/backfill_f12_2.db` loaded | `canonical_schemes` | Count rows in table | Returns exactly 17,507 schemes | `COUNT(*) == 17507` | Page total shows 17,507 | 🟢 Sound |
| **DISC-02** | Known AMC filter discovery | Server running | `canonical_schemes` | Filter by `amc=HDFC` | Returns matching HDFC schemes | `WHERE amc_name = 'HDFC'` | Results table displays HDFC funds | 🟢 Sound |
| **DISC-03** | Category discovery | Server running | `canonical_schemes` | Filter category or search text | Exposes valid scheme categories | `category IS NOT NULL` | Category options populated | 🟢 Sound |
| **DISC-04** | Sub-category & AMC taxonomy | Server running | `canonical_schemes` | Query distinct AMCs | Returns 327 distinct fund houses | `COUNT(DISTINCT amc_name) == 327` | Dynamic AMC selector loaded | 🟢 Sound |
| **DISC-05** | Plan type filter | Server running | `canonical_schemes` | Filter by `plan=Direct` | Returns only Direct schemes | `plan_type = 'DIRECT'` | Direct badges on result rows | 🟢 Sound |
| **DISC-06** | Option type filter | Server running | `canonical_schemes` | Filter by `option=Growth` | Returns only Growth schemes | `option_type = 'GROWTH'` | Growth badges on result rows | 🟢 Sound |
| **DISC-07** | AMC + Plan combination | Server running | `canonical_schemes` | Filter `amc=HDFC&plan=Direct` | Logical AND of AMC and Plan | `amc_name='HDFC' AND plan_type='DIRECT'` | Exclusively HDFC Direct funds | 🟢 Sound |
| **DISC-08** | Category + Plan + Option combination | Server running | `canonical_schemes` | Filter `plan=Direct&option=Growth` | Logical AND of all filters | All filter WHERE constraints satisfied | Only matching schemes shown | 🟢 Sound |
| **DISC-09** | Pagination beyond 1st page | Server running | `canonical_schemes` | Request `page=2&limit=20` | Retrieves schemes 21-40 | `OFFSET 20 LIMIT 20` | Page 2 loaded without error | 🟢 Sound |
| **DISC-10** | Nippon Nifty 50 Direct Growth discovery | Server running | `canonical_schemes` | Search `Nippon India Nifty 50 Direct Growth` | Finds `CAN_AMFI_118741` | Token AND query matches row | Scheme displayed in table | 🟢 Sound |
| **DISC-11** | Clear filters control | Server running | `canonical_schemes` | Click "Clear Filters" | Resets filters to default | Returns full 17,507 count | Reset inputs, full total | 🟢 Sound |
| **DISC-12** | No duplicate scheme IDs | Server running | `canonical_schemes` | Query search endpoint | All returned canonical_scheme_ids distinct | `COUNT(id) == COUNT(DISTINCT id)` | Unique table rows | 🟢 Sound |
| **DISC-13** | Search does not mutate portfolio | Server running | `portfolio_snapshots` | Execute search API | No portfolio records created or modified | Snapshot count unchanged | Clean exploration state | 🟢 Sound |
| **DISC-14** | Exploration inputs omit dirty guard | Server running | UI HTML | Inspect form elements on `/discover` | Inputs tagged `data-no-dirty="true"` | None | No "unsaved changes" warning | 🟢 Sound |
| **DISC-15** | Complete universe accessibility | Server running | `canonical_schemes` | Paginate to last page | Reaches schemes at end of database | `OFFSET 17487` returns last 20 schemes | Complete universe reachable | 🟢 Sound |

---

## D. 10-Fund Comparison Test Matrix (COMP-01 to COMP-12)

| Test ID | Objective | Preconditions | Data Source | Action | Expected Result | Database Expectation | UI Expectation | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **COMP-01** | Compare 1 fund | Server running | `canonical_schemes` | View `/discover/compare?ids=CAN_AMFI_118266` | Renders single-fund column | Scheme lookup successful | Badge shows "1 / 10 Funds Selected" | 🟢 Sound |
| **COMP-02** | Compare 2 funds | Server running | `canonical_schemes` | Select 2 funds for compare | Renders 2-column matrix | 2 schemes fetched | "2 / 10 Funds Selected" | 🟢 Sound |
| **COMP-03** | Compare 3 funds | Server running | `canonical_schemes` | Select 3 funds for compare | Renders 3-column matrix | 3 schemes fetched | "3 / 10 Funds Selected" | 🟢 Sound |
| **COMP-04** | Compare 5 funds | Server running | `canonical_schemes` | Select 5 funds for compare | Renders 5-column matrix | 5 schemes fetched | "5 / 10 Funds Selected" | 🟢 Sound |
| **COMP-05** | Compare 10 funds | Server running | `canonical_schemes` | Select 10 funds for compare | Renders 10-column matrix | 10 schemes fetched | "10 / 10 Funds Selected" | 🟢 Sound |
| **COMP-06** | Prevent 11th fund selection | Server running | UI JavaScript | Attempt adding 11th scheme | Triggers limit warning modal / alert | Server limits to top 10 IDs | 11th scheme rejected | 🟢 Sound |
| **COMP-07** | Duplicate selection prevention | Server running | UI JavaScript | Select same scheme twice | Only single instance added to queue | Distinct ID set enforced | Single column rendered | 🟢 Sound |
| **COMP-08** | Remove fund from queue | Server running | UI JavaScript | Click "✕" on compare pill | Scheme removed from queue | Queue updated in localStorage | Pill removed, count updated | 🟢 Sound |
| **COMP-09** | Identity consistency | Server running | `canonical_schemes` | Compare fund `CAN_AMFI_118741` | Name, AMC, AMFI, ISIN match canonical record | Exact matching | Identical labels across views | 🟢 Sound |
| **COMP-10** | Metric mapping & zero-winner policy | Server running | `canonical_schemes` | View compare matrix | Metrics mapped per column; no "winner" generated | Factual metric presentation only | No "winner" or ranking badge | 🟢 Sound |
| **COMP-11** | Compare does not mutate portfolio | Server running | `portfolio_snapshots` | Navigate `/discover/compare` | Portfolio state untouched | Database state unchanged | Read-only presentation | 🟢 Sound |
| **COMP-12** | Compare omits dirty guard | Server running | UI HTML | Navigate away from Compare page | Navigation proceeds without prompt | None | No "unsaved changes" modal | 🟢 Sound |

---

## E. Verification Execution & Automated Results

- **Governed Suite**: `python -m pytest tests/journeys tests/ui tests/integration tests/scoring`
- **Passed**: `167 / 167` passed in `1.44s`.
- **Status**: 🟢 Clean run with 100% pass rate.
