# Phase F.3.4.1 — Suitability Engine Governance & Methodology Correction Audit Document

**Phase:** Phase F.3.4.1 — Suitability Methodology Governance Correction  
**Date:** 2026-09-10 UTC  
**Status:** Governance Audit Approved  
**Final Decision:** `PHASE F.3.4.1 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Targeted governance correction audit of the proposed Suitability Engine specification against `PRODUCT_SPEC.md`, `ARCHITECTURE.md`, upstream engines (`Risk Capacity`, `Risk Tolerance`, `Risk Alignment`, `Fund Quality`), and project rules.

---

## F.3.4.1 Detailed Rule Corrections Audit Table

| # | Previous Draft Rule | Audit Finding | Correction Applied | Final Governance Status | Evidence Required Before Implementation |
|---|---|---|---|---|---|
| 1 | `Goal Horizon < Category Minimum Required Horizon` (Hard Rejection) | Arbitrary numerical minimums (5 yrs equity, 3 yrs hybrid) lack empirical validation. | Removed as hard rejection. Reclassified category horizon compatibility as a **provisional/TBD framework**. Emits `HORIZON_WARNING` token instead of hard rejection. | `PROVISIONAL / TBD` | Empirical risk/horizon study across market cycles. |
| 2 | `Fund Lock-In Period > Goal Horizon` | Scheme lock-in data was assumed rather than sourced from authoritative data feeds. | Reclassified statutory lock-in as **TBD**. Mandated retrieval from scheme master feeds. Missing lock-in yields `MISSING_DATA`. | `TBD` | Integration with AMFI/SEBI scheme master feed for lock-in metadata. |
| 3 | `Prohibited Fund Category` | Premature creation of a prohibited categories list without user context. | Removed hard-coded prohibited list. Reframed as an extensible user-constraint interface. | `NOT SUPPORTED` | Investor profile constraint preference model. |
| 4 | `Material Overlap (30%-60%) & Excessive Overlap (>60%)` | Arbitrary numerical percentage thresholds introduced without empirical backing. | Removed percentages from hard logic. Reframed as conceptual inputs (`overlap_classification`, `overlap_confidence`). Config thresholds remain provisional. | `PROVISIONAL` | Empirical portfolio overlap diversification study. |
| 5 | `AMC Concentration Limit > 40%` | 40% limit was an arbitrary hardcoded cutoff. | Removed 40% threshold from hard logic. Reframed AMC concentration as a portfolio-context factor. | `PROVISIONAL` | AMC risk concentration audit. |
| 6 | `Young Fund Age < 1 Year` | Risked duplicating Fund Maturity calculation from metrics engine. | Clarified that Suitability **consumes** `FundMaturity` output. Immature funds reduce confidence but are never mechanically rejected. | `APPROVED` | Existing Fund Maturity framework integration. |
| 7 | `Fund Risk > Investor Aligned Risk` | Assumed direct equivalence between ordinal risk ($1-5$) and fund category labels. | Sourced/defined explicit `FundRiskProfile` data contract (SEBI Riskometer). Marked ordinal-to-category mapping as provisional/TBD. | `PROVISIONAL / TBD` | SEBI Riskometer data feed & mapping calibration. |
| 8 | Weighted Suitability Score Formula | Risked creating arbitrary numerical weights to produce a single score. | Re-emphasized **constraint-first + contextual architecture** (`Hard Bounds → Conditionality → Positive Evidence → Confidence → State`). Rejected arbitrary weighted scores. | `APPROVED` | Calibration plan in Phase F.4A. |

---

## 1. Documents Reviewed

1. `PRODUCT_SPEC.md` (§1–2, §4–5, §8–10, §15–18, §23–25)
2. `ARCHITECTURE.md` (§2, §4, §8, §11, §13, §17)
3. `docs/phase_f3_4_suitability_specification.md` (corrected)
4. `docs/phase_f3_3_3_risk_alignment_independent_qa_report.md`
5. [`risk/alignment_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_engine.py), [`risk/alignment_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_models.py)
6. [`scoring/engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scoring/engine.py)
7. `docs/documentation_traceability_matrix.md`

---

## 2. Architecture & Boundary Verification

- **Fund Quality:** Consumed as upstream fact; zero recomputation of returns or risk-adjusted metrics.
- **Risk Alignment:** Consumed as upstream fact (`AlignedRiskLevel`); zero recomputation of Capacity or Tolerance.
- **Portfolio Need:** Separated cleanly. Suitability evaluates fund appropriateness; Portfolio Need evaluates allocation gaps.
- **Actionability:** Separated cleanly. Suitability outputs status and confidence; zero `BUY`/`SELL` actions emitted.

---

## 3. Double-Counting Audit

- **Volatility:** Owned exclusively by Fund Quality & Risk Tolerance. Suitability uses category risk profile only.
- **Horizon Resilience:** Owned exclusively by Risk Capacity. Suitability uses goal-to-fund timeline compatibility only.
- **Overlap:** Owned exclusively by Portfolio Need Engine.

---

## 4. Parameter Governance Register

| Parameter Name | Value | Source | Status | Validation Required |
|---|---|---|---|---|
| `horizon_equity_min_years` | `5.0` | Industry Practice | `PROVISIONAL` | Empirical risk study |
| `horizon_hybrid_min_years` | `3.0` | Industry Practice | `PROVISIONAL` | Empirical risk study |
| `horizon_debt_min_years` | `1.0` | Industry Practice | `PROVISIONAL` | Duration audit |
| `overlap_material_threshold` | `0.30` | Diversification Practice | `PROVISIONAL` | Overlap study |
| `overlap_excessive_threshold` | `0.60` | Diversification Practice | `PROVISIONAL` | Overlap study |
| `amc_concentration_limit` | `0.40` | Portfolio Risk Practice | `PROVISIONAL` | AMC risk audit |

---

## 5. Regression Test Results

- **Command:** `python -m pytest tests/ -v --tb=short`
- **Result:** **286 / 286 passed cleanly in 1.17s**. Zero regressions.

---

## 6. Final Decision — Exactly One

```text
PHASE F.3.4.1 ACCEPTED WITH PROVISIONAL METHODOLOGY
```

---

## 7. Explicit Downstream Gate

```text
================================================================================
IMPLICIT EXECUTION GATE ENFORCED
================================================================================
Production Suitability Engine implementation (risk/suitability_engine.py or similar)
is STRICTLY BLOCKED in this phase.
Requires separate explicit user authorization.
================================================================================
```
