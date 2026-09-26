# PHASE F.8 — PRODUCTION ELIGIBILITY GATE SPECIFICATION

## Executive Summary

This specification defines the explicit production eligibility gates governing transaction recommendations (`BUY`, `ACCUMULATE`, `SELL`) and non-transactional assessments (`HOLD`, `MONITOR`, `REVIEW`, `NO_ACTION`).

> [!IMPORTANT]
> Passing unit, integration, or adversarial software tests does **NOT** constitute production authorization. A recommendation can be emitted for live execution **ONLY** when all required Tier 1–7 evidence prerequisites are fully satisfied.

---

## 1. Multi-Tier Decision Engine Alignment

The production eligibility gates strictly enforce the 7-tier decision architecture:

```
TIER 1: INPUT VALIDITY & COMPLEATNESS (Identity, Snapshot, Schema)
   │
   ▼
TIER 2: SUITABILITY & RISK ALIGNMENT (Profile, Capacity, Tolerance, Limits)
   │
   ▼
TIER 3: STALENESS & FRESHNESS GATING (Observation Date, Staleness Flags)
   │
   ▼
TIER 4: PORTFOLIO NEED & FULFILLMENT (Need State, Candidate Fulfillment)
   │
   ▼
TIER 5: ECONOMIC BENEFIT ACTIONABILITY (Net Benefit, Tax/Cost Integration)
   │
   ▼
TIER 6: FUND QUALITY EVIDENCE VALIDITY (Quality Score, Evidence Validity)
   │
   ▼
TIER 7: ACTION PRECEDENCE & LOW-TURNOVER GUARDRAILS (Final Action State)
```

---

## 2. Gate A: New BUY Transaction Eligibility

To issue a production `BUY` recommendation, every decision prerequisite that is applicable and required for the specific decision path must satisfy its governed validity condition (`True` / `VALID`):

| Prerequisites # | Field / Condition | Required State | Failure Consequence |
| :--- | :--- | :--- | :--- |
| **A-01** | Investor Profile | `VALID` (Non-stale) | Blocks BUY -> `NO_ACTION` / `INSUFFICIENT_INPUT` |
| **A-02** | Risk Alignment | `ALIGNED` / `SUITABLE` | Blocks BUY -> `CANDIDATE_NOT_SUITABLE` |
| **A-03** | Suitability Status | `SUITABLE` | Blocks BUY -> `CANDIDATE_NOT_SUITABLE` |
| **A-04** | Portfolio Need State | `NEED_IDENTIFIED` | Blocks BUY -> `NO_PORTFOLIO_NEED` |
| **A-05** | Candidate Fulfillment | `CANDIDATE_CAN_FULFILL_NEED` | Blocks BUY -> `CANDIDATE_CANNOT_FULFILL_NEED` |
| **A-06** | Fund Quality Evidence | `fund_quality_evidence_valid == True` | Blocks BUY -> `INSUFFICIENT_EVIDENCE` |
| **A-07** | Scheme Identity | `canonical_scheme_id` Valid (Unambiguous) | Blocks BUY -> `INVALID_INPUT` / `QUARANTINED` |
| **A-08** | Category & PIT Context | Valid SEBI Category at Date $T$ | Blocks BUY -> `INVALID_INPUT` |
| **A-09** | Economic Benefit | `ECONOMICALLY_BENEFICIAL` | Blocks BUY -> `ECONOMIC_BENEFIT_UNKNOWN` |
| **A-10** | Affordability Status | `AFFORDABLE` | Constrains BUY -> `ACCUMULATE` |
| **A-11** | Freshness Flag | `is_stale_input == False` | Blocks BUY -> `STALE_INPUT` (`NO_ACTION`) |
| **A-12** | Methodology Integrity | Matching approved versions | Blocks BUY -> `VERSION_MISMATCH` |
| **A-13** | Provenance | Complete traceable lineage | Blocks BUY -> `INSUFFICIENT_EVIDENCE` |

> [!CAUTION]
> If any required prerequisite A-01 through A-13 for the decision path is `False`, `None`, `UNKNOWN`, or `INVALID`, a `BUY` transaction **MUST NOT BE AUTHORIZED**. Non-applicable fields (e.g. IDCW reconstruction for Growth schemes) do not block eligibility.

---

## 3. Gate B: Existing Position HOLD / MONITOR Eligibility

Non-transactional monitoring of existing portfolio holdings does **NOT** require full transactional evidence completeness. Safe holding/monitoring requires only basic safety completeness.

| Assessment State | Minimum Evidence Required | Output State | Rationale |
| :--- | :--- | :--- | :--- |
| **HOLD (Default)** | Valid Position Context (`EXISTING_POSITION`) + No Material Deterioration Signal + No Unsuitable Constraint. | `HOLD` | Preserves low turnover and prevents unnecessary churn. |
| **MONITOR** | Existing Position + Mild Deterioration Signal (`MILD_DETERIORATION`). | `MONITOR` | Flags fund for observation without forcing premature sell. |

- If input evidence is stale (`is_stale_input=True`) or tax/cost info is missing during a review signal, the system routes existing positions to `REVIEW` for manual human evaluation rather than blocking monitoring.

---

## 4. Gate C: SELL Transaction Eligibility

To issue a production `SELL` recommendation for an existing holding, every decision prerequisite that is applicable and required for the specific decision path must satisfy its governed validity condition (`True` / `VALID`):

| Prerequisite # | Field / Condition | Required State | Failure Consequence |
| :--- | :--- | :--- | :--- |
| **C-01** | Position Context | `EXISTING_POSITION` | Blocks SELL -> `INVALID_INPUT` |
| **C-02** | Deterioration Signal | `MATERIAL_DETERIORATION` | Blocks SELL -> `HOLD` / `MONITOR` |
| **C-03** | Deterioration Validated | `deterioration_validated == True` | Blocks SELL -> `REVIEW` (`UNVALIDATED_DETERIORATION`) |
| **C-04** | Suitable Replacement | `has_suitable_replacement == True` | Blocks SELL -> `REVIEW` (`NO_SUITABLE_REPLACEMENT`) |
| **C-05** | Quality Comparability | `fund_quality_comparison_valid == True` | Blocks SELL -> `REVIEW` (`INSUFFICIENT_EVIDENCE`) |
| **C-06** | Economic Benefit | `ECONOMICALLY_BENEFICIAL` | Blocks SELL -> `REVIEW` (`SWITCH_NOT_JUSTIFIED`) |
| **C-07** | Tax Liability Info | `tax_liability_known == True` | Blocks SELL -> `REVIEW` (`TAX_COST_INFORMATION_MISSING`) |
| **C-08** | Exit Load Info | `exit_load_known == True` | Blocks SELL -> `REVIEW` (`EXIT_LOAD_INFORMATION_MISSING`) |
| **C-09** | Transaction Cost Info | `transaction_costs_known == True` | Blocks SELL -> `REVIEW` (`TAX_COST_INFORMATION_MISSING`) |
| **C-10** | Freshness Flag | `is_stale_input == False` | Blocks SELL -> `REVIEW` (`STALE_INPUT`) |

> [!IMPORTANT]
> Action Engine does **NOT** calculate Tax, Exit Load, or Fund Quality scores. It consumes the governed upstream boolean signals (`tax_liability_known`, `exit_load_known`, `fund_quality_comparison_valid`). If any signal is missing or `False`, SELL is prohibited and safely routed to `REVIEW`.

---

## 5. Production Gate Verification Matrix

```
                     ┌──────────────────────────┐
                     │ Incoming Decision Task   │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │ Valid Position Context?  │
                     └─────┬──────────────┬─────┘
                           │              │
                    NEW_POSITION    EXISTING_POSITION
                           │              │
                           ▼              ▼
                 ┌─────────────────┐  ┌──────────────────┐
                 │ Gate A: BUY     │  │ Gate C: SELL     │
                 │ Prerequisites   │  │ Prerequisites    │
                 └────────┬────────┘  └────────┬─────────┘
                          │                    │
                  All Pass?                    All Pass?
                 ┌───┴───┐                    ┌───┴───┐
                 │       │                    │       │
                YES      NO                  YES      NO
                 │       │                    │       │
                 ▼       ▼                    ▼       ▼
              [BUY] [NO_ACTION]            [SELL]  [REVIEW/HOLD]
```
