# PHASE F.8 — FIELD-LEVEL SOURCE AUTHORITY MATRIX SPECIFICATION

## Executive Summary

This specification establishes the authoritative field-level source hierarchy, third-party source governance, validation requirements, conflict resolution policies, and quarantine triggers across all mutual-fund data domains.

> [!IMPORTANT]
> Authority is assigned **PER FIELD**. There is no universal "one-size-fits-all" source hierarchy. AMFI is primary for scheme codes and EOD NAVs, while SEBI regulatory filings are primary for categorization and Riskometer disclosures, and AMC filings are primary for TER and Exit Load structures.

---

## 1. Field-Level Source Authority Matrix

| Domain | Data Field | Primary Source | Acceptable Secondary Source | Third-Party Vendor Allowed? | Validation Requirement | Conflict Policy | Quarantine Condition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IDENTITY** | `amfi_code` | AMFI Official Portal (`SRC_AMFI`) | CSDL / NSDL Repository | No (Direct Reg/Utility only) | Exact numeric match + Active status check | Primary authority prevails | AMFI code reassigned without scheme continuity proof |
| **IDENTITY** | `isin` | NSDL / CDSL Official Database | AMFI Master Registry | No | 12-char alphanumeric ISO 6166 check | Primary authority prevails | ISIN mapped to multiple distinct AMC schemes |
| **IDENTITY** | `canonical_scheme_id` | Platform Internal Identity Resolver | None | No (Platform Generated) | MD-1..MD-5 compliance verification | Internal Deterministic Hash | Ambiguous name match or identifier collision |
| **IDENTITY** | `amc_name` | SEBI Registered AMC List | AMFI Master Registry | No | SEBI registration lookup | Primary authority prevails | Unregistered AMC or AMC license revocation |
| **IDENTITY** | `scheme_name` | AMC Scheme Information Doc (SID) | AMFI Official Portal | Yes (Formal Validation Required) | Exact String Match | Primary authority prevails | Scheme name mismatch across AMFI & AMC SID |
| **IDENTITY** | `plan_type` | AMC SID / KIM Filing | AMFI Master Registry | No | Must be `DIRECT` or `REGULAR` | Primary authority prevails | Ambiguous plan designation |
| **IDENTITY** | `option_type` | AMC SID / KIM Filing | AMFI Master Registry | No | Must be `GROWTH` or `IDCW` | Primary authority prevails | Ambiguous option designation |
| **NAV** | `current_nav` | AMFI Daily EOD Feed (`SRC_AMFI`) | AMC Direct Website Feed | Yes (Valuation Corroborated) | Non-negative decimal, $T_{\text{obs}} = \text{EOD}$ | Field-specific authority check | Unresolved EOD feed conflict beyond validation tolerance |
| **NAV** | `historical_nav` | AMFI Historical Endpoint | AMC Archive / Regulated Data Repository | Yes (Checksum Validated) | Monotonic observation dates, non-zero values | Primary authority prevails | Unvalidated single-day NAV anomaly without corporate action proof |
| **NAV** | `observation_date` | AMFI Daily EOD Feed | AMC EOD Disclosure | No | Valid business day calendar date | Primary authority prevails | Future date or non-trading day observation |
| **NAV** | `historical_coverage` | Platform Coverage Ledger (`data/repositories`) | None | No (Calculated Internal) | Monotonic ledger date check | Internal Audit | Unexplained historical NAV gap breaching coverage threshold |
| **CLASS** | `category` | SEBI Categorization Circular Filings | AMFI Monthly Classification | No | Must match SEBI 2017 taxonomy | Primary authority prevails | Category mismatch between SEBI filing & AMFI |
| **CLASS** | `subcategory` | SEBI Scheme Approval Filings | AMFI Monthly Classification | No | Must match SEBI 2017 subcategory | Primary authority prevails | Unrecognized subcategory tag |
| **CLASS** | `strategy` | AMC SID / SEBI Filing | AMFI Strategy Tagging | Yes (Formal Validation Required) | Strategy taxonomy validation | Primary authority prevails | Strategy tag contradicts SEBI subcategory |
| **CLASS** | `effective_date` | SEBI Approval Letter / AMC Notice | AMC Press Release | No | Precise ISO Date ($T_{\text{eff}}$) | Primary authority prevails | Category effective date missing or ambiguous |
| **CLASS** | `pit_category` | Platform PIT Database | SEBI Historical Filings | No | Effective-date bounded temporal check | Internal PIT Audit | Retroactive category assignment attempt |
| **LIFECYCLE** | `creation_date` | AMC Scheme Launch Filing | AMFI Earliest NAV Record | No | ISO Date | Primary authority prevails | Inception date after earliest NAV observation |
| **LIFECYCLE** | `scheme_rename` | AMC Addendum Filing | AMFI Notice | No | Effective date + Name mapping proof | Primary authority prevails | Scheme rename without official AMC addendum |
| **LIFECYCLE** | `scheme_merger` | SEBI Approval + AMC Notice | AMFI Merger Disclosure | No | Predecessor & Successor ID mapping | Primary authority prevails | Attempted NAV stitching across merger |
| **LIFECYCLE** | `scheme_closure` | AMC Winding-Up Filing | AMFI De-listing Notice | No | Effective Date + Final NAV | Primary authority prevails | Active NAV reporting after official closure date |
| **COSTS** | `current_ter` | AMC Monthly TER Disclosure | AMFI Monthly TER Portal | Yes (Audit Corroborated) | Valid expense percentage bound | Primary authority prevails | Missing TER or TER breaching regulatory bounds |
| **COSTS** | `historical_ter` | AMC Monthly Disclosures (Post-2018) | Regulated Repository | Yes (Audit Corroborated) | Date-stamped monthly TER series | Primary authority prevails | Pre-2018 missing TER filled with zero |
| **COSTS** | `exit_load` | AMC SID / KIM Disclosure | AMC EOD Feed | No | Percentage + Holding period structure | Primary authority prevails | Missing exit load defaulted to zero |
| **RISK** | `riskometer` | AMC Monthly Riskometer Disclosure | AMFI Monthly Riskometer | No | Must be official SEBI 6-tier string | Primary authority prevails | Riskometer inferred from volatility/category |
| **RISK** | `riskometer_eff_date` | AMC Disclosure Filing | AMFI Portal | No | ISO Month-End Date | Primary authority prevails | Riskometer applied prior to effective disclosure date |
| **BENCHMARK**| `benchmark_id` | AMC SID / KIM Filing | AMFI Benchmark Master | No | Valid Index Symbol | Primary authority prevails | Unregistered or custom unvalidated benchmark |
| **BENCHMARK**| `benchmark_tri_nav` | Official Index Provider (NSE / BSE) | AMC Disclosed Benchmark Series | Yes (Licensing Validated) | TRI Series (Where required by methodology) | Primary authority prevails | PRI used for metric explicitly requiring TRI |

---

## 2. Third-Party Vendor Data Governance Rules

Third-party vendor data sources (e.g., commercial market data aggregators) may be consumed **ONLY** if all of the following conditions are satisfied:
1. **Formal Vendor Registration**: The vendor is registered in the Source Registry with `source_type=THIRD_PARTY_VENDOR`.
2. **Audit Corroboration**: Vendor data values are corroborated against primary regulator/utility feeds (AMFI/SEBI) for a formal validation period.
3. **No Authority Override**: A third-party vendor feed can **NEVER** override a primary regulator/utility feed on disagreement.
4. **Licensing Compliance**: Redistribution and processing terms are verified and documented.

---

## 3. Conflict Resolution Policies

When a conflict is detected between two data streams:
- **Rule 1 (Primary Prevails)**: If one source is `PRIMARY` and the other is `SECONDARY` or `THIRD_PARTY`, the `PRIMARY` value is automatically selected.
- **Rule 2 (Equal Authority Disagreement)**: If two `PRIMARY` sources report contradictory values for the same field, the field state is set to `CONFLICTED`. Exact numerical conflict tolerances (if required in future implementation) remain **`TBD — REQUIRES FIELD-SPECIFIC VALIDATION`**.
- **Rule 3 (Corroboration Fallback)**: If a third independent verified source corroborates one value, the corroborated value is selected.
- **Rule 4 (Quarantine Trigger)**: If an equal-authority conflict cannot be resolved prior to evaluation, the scheme identity or affected field is marked `QUARANTINED`. Downstream transaction evaluations for `BUY`/`SELL` are strictly blocked.

---

## 4. Quarantine Triggers & Governance Workflow

A scheme or dataset is automatically routed to `QUARANTINED` status under any of the following conditions:
1. **Ambiguous Identity**: Multiple active AMFI codes or ISINs map to a single candidate scheme name without clear plan/option separation.
2. **Attempted NAV Stitching**: Ingestion pipeline attempts to combine predecessor scheme NAV with successor scheme NAV post-merger.
3. **Severe NAV Discrepancy**: Unvalidated single-day NAV anomaly occurs without documented corporate action (stock split, bonus, IDCW payout).
4. **Unresolved Primary Conflict**: Persistent EOD conflict between AMFI and AMC feed.
5. **Data Corruption / Schema Failure**: Ingestion payload fails parser validation or contains corrupted binary/HTML payloads.

While in `QUARANTINED` state:
- All automated `BUY` and `SELL` recommendations are **PROHIBITED**.
- Quality Engine and Suitability Engine evaluations route to `INSUFFICIENT_INFORMATION` or `INVALID_ASSESSMENT`.
- Manual data governance review and written audit sign-off are required to release quarantine.
