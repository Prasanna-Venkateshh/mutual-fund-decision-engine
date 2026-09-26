# Phase F.3.4.1 — Suitability Engine Methodology & Architectural Specification Document (Governance Corrected)

**Phase:** Phase F.3.4.1 — Suitability Methodology Governance Correction  
**Date:** 2026-09-10 UTC  
**Status:** Approved Specification  
**Final Decision:** `PHASE F.3.4.1 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Governance audit and methodology correction of the Suitability Engine specification (`Fund Quality + Risk Alignment + Goal Context + Portfolio Context → Contextual Suitability`).

---

## F.3.4.1 Governance Corrections Summary

In accordance with Phase F.3.4.1 governance requirements, the previous Phase F.3.4 draft specification was audited to remove or reclassify unvalidated numerical thresholds, arbitrary percentage cutoffs, and premature hard constraints.

### Key Corrections Applied:
1. **Horizon Governance:** Removed unsupported hard numerical category minimums (e.g. 5 yrs equity, 3 yrs hybrid, 1 yr debt). Reclassified category-to-horizon matching as a **TBD/Provisional framework** requiring empirical calibration. Horizon mismatches now emit conditional warnings/reduced confidence rather than hard rejections unless a legal/contractual constraint exists.
2. **Lock-In Governance:** Reclassified `Fund Lock-In Period > Goal Horizon` as **TBD**. Mandated that lock-in data must be sourced from authoritative scheme master feeds rather than inferred from category labels. Missing lock-in data yields `MISSING_DATA`, never default 0.
3. **Category Incompatibility:** Removed premature "prohibited fund category" list. Reframed as an extensible interface for future investor-defined preference constraints.
4. **Portfolio Overlap Governance:** Removed arbitrary numerical thresholds ($30\% - 60\%$ material, $>60\%$ excessive). Reframed overlap evaluation as a **conceptual portfolio-context input** (`overlap_classification`, `overlap_confidence`) requiring future empirical validation.
5. **AMC Concentration Governance:** Removed arbitrary $40\%$ AMC threshold. Reframed AMC concentration as a portfolio-context factor requiring explicit user/governance threshold approval.
6. **Young Fund Governance:** Clarified that Suitability **consumes** upstream `FundMaturity` output from the Fund Quality/Metrics engine. Immature funds reduce evidence confidence/yield `CONDITIONALLY_SUITABLE`, but are never mechanically rejected for age alone.
7. **Risk Compatibility Mapping:** Identified that ordinal investor Risk Alignment ($1-5$) cannot be directly compared to raw fund category labels without an approved mapping. Sourced/defined a required `FundRiskProfile` contract and marked the mapping as **TBD/Provisional**.
8. **Constraint-First Architecture:** Preserved constraint-first evaluation (`Hard Incompatibility → Conditional Concern → Positive Evidence → Confidence → Final State`). Explicitly rejected arbitrary weighted scoring formulas.

---

## 1. Purpose

The purpose of Phase F.3.4.1 is to establish a financially defensible, explainable, and context-aware specification and software contract for the **Suitability Engine**.

The Suitability Engine determines:
> *Whether a mutual fund or investment strategy is appropriate for a specific investor within their unique goal, timeline, risk, and portfolio context.*

Suitability is context-aware. A fund with an exceptional Fund Quality Score is not universally suitable for every investor, nor is a risk-compatible fund suitable for every financial goal or timeline.

---

## 2. Scope & Non-Scope

### In Scope
- Architectural definition of the Suitability boundary.
- Integration specifications with upstream components (`Fund Quality Engine`, `Risk Alignment Engine`, `Investor Profile`, `Goal Profile`).
- Design of goal-linked suitability, general-wealth suitability, and portfolio-context suitability.
- Design of hard suitability constraints vs. soft contextual factors under governed classification.
- Design of the Suitability Output Model contract (`SuitabilityAssessmentResult`).
- Data sufficiency, missing data safety rules, and error state handling.
- Strict separation of `Fund Quality Score`, `Risk Alignment`, `Suitability Status`, `Suitability Confidence`, `Actionability`, and `Downstream Action`.
- Numerical parameter register with explicit governance classifications.

### Out of Scope
- Production implementation code (`risk/suitability_engine.py` or similar).
- Scoring calculations or production execution code.
- Modification of upstream Risk Capacity, Risk Tolerance, Risk Alignment, or Fund Quality logic.
- Portfolio Need Engine, Portfolio Optimization, Rebalancing, or Tax Engine calculations.
- Execution of Buy, Accumulate, Hold, or Sell transaction actions.

---

## 3. Required Architectural Position

The Suitability Engine occupies a precise downstream position in the mutual fund decision pipeline:

```text
┌───────────────────────────┐
│    Fund Quality Engine    │  (Evaluates category-relative fund merit & confidence)
└─────────────┬─────────────┘
              │
              │  FundQualityScore & Confidence
              ▼
┌───────────────────────────┐     ┌───────────────────────────┐
│   Risk Capacity Engine    │     │   Risk Tolerance Engine   │
└─────────────┬─────────────┘     └─────────────┬─────────────┘
              │                                 │
              └────────────────┬────────────────┘
                               ▼
                  ┌───────────────────────────┐
                  │   Risk Alignment Engine   │  (Establishes supportable risk envelope)
                  └─────────────┬─────────────┘
                                │
                                │  AlignedRiskLevel & Status
                                ▼
                  ================================= SUITABILITY BOUNDARY
                  ┌───────────────────────────┐
                  │    Suitability Engine     │  (Evaluates context-aware appropriateness)
                  └─────────────┬─────────────┘
                                │
                                │  SuitabilityAssessmentResult
                                ▼
                  ┌───────────────────────────┐
                  │    Portfolio Need Engine  │  (Gap reduction & allocation need)
                  └─────────────┬─────────────┘
                                │
                                ▼
                  ┌───────────────────────────┐
                  │    Economic Benefit /     │  (After-tax/after-cost decision)
                  │       Action Engine       │  [Buy / Accumulate / Hold / Sell]
                  └───────────────────────────┘
```

---

## 4. Definitions

- **Fund Quality:** Category-relative evaluation of a fund's risk-adjusted return, consistency, downside protection, drawdown, cost, and historical data completeness.
- **Risk Alignment:** The investor's overall supportable risk envelope, derived as the strict lower-of-two bound between financial Risk Capacity and psychological Risk Tolerance.
- **Goal Context:** Specific financial objective parameters including target horizon, target date, target amount, liquidity requirements, and funding gap.
- **Portfolio Context:** The existing holding structure of the investor, including asset allocation, category exposure, sector concentration, and fund overlap.
- **Suitability:** Contextual evaluation of whether a fund's structural characteristics, risk profile, horizon requirements, and quality align with an investor's specific goal and portfolio envelope.
- **Suitability Confidence:** The strength of evidence supporting the suitability evaluation, derived from upstream data completeness and input confidence scores.
- **Actionability:** Determination of whether suitability evidence is sufficient to justify presenting an actionable recommendation to the user.

---

## 5. Fund Quality Boundary

Fund Quality answers: *"How good is this fund relative to its appropriate category peers?"*
Suitability answers: *"Given this investor's risk alignment, goal horizon, liquidity needs, and existing portfolio, is this fund appropriate?"*

### Integration Rules
1. Fund Quality is consumed as an upstream input; Suitability **never** recalculates returns, volatility, Sharpe ratio, or downside capture metrics.
2. High Fund Quality does **not** override a Risk Alignment constraint or verified Horizon mismatch.
3. Low Fund Quality is a soft suitability factor or conditional concern, but does not automatically make a fund physically incompatible if no better category alternative exists and risk is aligned.

---

## 6. Risk Alignment Boundary

Risk Alignment answers: *"What is the maximum risk tier the investor can financially absorb and psychologically endure?"*

### Integration Rules
1. Suitability consumes `AlignedRiskLevel`, `AlignmentStatus`, and `LimitingConstraint` from [`risk/alignment_models.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/alignment_models.py).
2. Suitability **never** recomputes Risk Capacity, Risk Tolerance, debt ratios, reserve coverage, or questionnaire scores.
3. If Risk Alignment status is `INSUFFICIENT_INFORMATION` or `INVALID_ASSESSMENT`, Suitability **must** immediately yield `INSUFFICIENT_INFORMATION` or `INVALID_ASSESSMENT`.

---

## 7. Goal Context

Suitability supports two explicit assessment modes:
1. **Goal-Linked Assessment:** Evaluates fund suitability for a specific, named financial goal (e.g. Retirement, Education, Home Purchase).
2. **General Wealth Assessment:** Evaluates fund suitability for general wealth accumulation without a specific target date or amount.

### Goal-Linked Parameters
- **Goal Type & Priority:** Critical vs. discretionary goal.
- **Time Horizon (Years):** Time remaining until target date.
- **Target Date & Target Amount:** Optional fields; skipping does not invalidate suitability.
- **Required Liquidity:** Date-bound liquidity constraints.

---

## 8. Horizon Governance (Corrected)

Horizon evaluation compares the **Goal Time Horizon** against the **Fund Category Recommended Horizon**.

*Correction:* Hard numerical category minimums (e.g. 5 yrs equity, 3 yrs hybrid) have been **reclassified as TBD/Provisional**.

| Horizon Framework Concept | Purpose | Governance Status | Mitigation / Default Behavior |
|---|---|---|---|
| Goal Time Horizon | Time remaining until goal target date | `APPROVED` | Sourced from `GoalProfile` |
| Fund Category Horizon Band | Expected holding period for fund category | `PROVISIONAL` | Sourced from config; subject to empirical study |
| Hard Horizon Rejection | Immediate `NOT_SUITABLE` on horizon gap | `NOT SUPPORTED` | Replaced by `CONDITIONALLY_SUITABLE` + warning token |
| Lock-In Horizon Conflict | Rejection when goal horizon < legal lock-in | `TBD` | Requires authoritative lock-in data feed |

---

## 9. Lock-In Governance (Corrected)

- Fund lock-in (e.g., 3-year statutory ELSS lock-in) is a contractual constraint.
- *Correction:* Statutory lock-in must be retrieved from authoritative scheme metadata (e.g., Scheme Master feed), **not** inferred from category names.
- If lock-in data is unavailable, the system treats lock-in as `MISSING_DATA` (never assumed 0 or assumed non-existent).

---

## 10. Portfolio Context (Corrected)

When an existing portfolio is supplied, Suitability evaluates portfolio-context factors:
- **Category Over-concentration:** Tracked conceptually as a portfolio-context factor.
- **AMC Concentration:** Tracked conceptually as a portfolio-context factor (no hard 40% threshold).
- **Security Overlap:** Tracked as `overlap_classification` (`HEALTHY`, `MATERIAL`, `EXCESSIVE`) without hard-coded numerical percentages in core logic. Numerical parameters in config remain `PROVISIONAL`.

---

## 11. Multiple Goals & General Wealth Integration

- **Multiple Goals:** Evaluates fund suitability **per goal context** (scoped by `goal_id`).
- **General Wealth:** Evaluates suitability using investor's overall horizon preference or `LONG` fallback.

---

## 12. Young Fund Handling (Corrected)

- Suitability **consumes** `FundMaturity` output from the Fund Quality/Metrics engine.
- Young funds ($< 1$ year of history) yield low evidence confidence or `CONDITIONALLY_SUITABLE` with a `NEW_FUND_LIMITED_HISTORY` token.
- Young funds are **never** mechanically rated `NOT_SUITABLE` solely due to age.

---

## 13. Risk Mapping Governance (Corrected)

*Correction:* Comparing `Fund Risk > Investor Aligned Risk Level` requires a verified mapping between ordinal investor risk ($1-5$) and fund risk characteristics.
- Defined `FundRiskProfile` contract (SEBI Riskometer or category volatility rating).
- Mapping rule is classified as **PROVISIONAL/TBD** pending SEBI Riskometer integration.

---

## 14. Data Sufficiency & Missing Data Rules

| Data Input State | Suitability Action | Resulting Status | Missing Token Emitted |
|---|---|---|---|
| Risk Alignment Missing | Halt evaluation | `INSUFFICIENT_INFORMATION` | `MISSING_RISK_ALIGNMENT` |
| Fund Quality Missing | Evaluate constraints | `CONDITIONALLY_SUITABLE` / `INSUFFICIENT` | `MISSING_FUND_QUALITY_SCORE` |
| Goal Horizon Missing | Use General Wealth mode | `SUITABLE` / `CONDITIONALLY_SUITABLE` | `GENERAL_WEALTH_MODE_APPLIED` |
| Fund Category Missing | Halt evaluation | `INVALID_ASSESSMENT` | `UNMAPPED_FUND_CATEGORY` |

*Governance Rule:* Missing inputs **never** default to zero, average, or arbitrary hardcoded fallbacks.

---

## 15. Suitability State Taxonomy

The engine output uses a 5-state controlled taxonomy:
1. **`SUITABLE`**: Fund satisfies governed constraints, matches risk alignment and goal horizon, and has adequate Fund Quality.
2. **`CONDITIONALLY_SUITABLE`**: Fund is acceptable but has contextual concerns (e.g. portfolio overlap, limited fund history, lower Fund Quality score).
3. **`NOT_SUITABLE`**: Fund violates an approved hard constraint (e.g. verified over-risk alignment violation or contractual lock-in conflict).
4. **`INSUFFICIENT_INFORMATION`**: Critical upstream data (Risk Alignment, Fund Category) is missing or unverified.
5. **`INVALID_ASSESSMENT`**: Inputs are malformed, corrupted, or violate contract schemas.

---

## 16. Constraint-First Decision Architecture

Suitability uses a **constraint-first + contextual assessment** model (no arbitrary weighted scoring formula):

1. **Step 1 — Hard Incompatibility Check:** Evaluates verified risk bounds & legal lock-in conflicts.
2. **Step 2 — Conditional Concern Evaluation:** Evaluates horizon compatibility, portfolio overlap, AMC exposure, and young fund history.
3. **Step 3 — Positive Evidence Verification:** Verifies Fund Quality score & category consistency.
4. **Step 4 — Evidence Confidence Scoring:** Combines upstream input confidence scores.
5. **Step 5 — Final State Determination:** Emits controlled state (`SUITABLE`, `CONDITIONALLY_SUITABLE`, etc.).

---

## 17. Suitability Output Model Contract (`SuitabilityAssessmentResult`)

```python
class SuitabilityStatus(Enum):
    SUITABLE = "SUITABLE"
    CONDITIONALLY_SUITABLE = "CONDITIONALLY_SUITABLE"
    NOT_SUITABLE = "NOT_SUITABLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"

class SuitabilityAssessmentResult(BaseModel):
    assessment_id: str
    investor_id: str
    scheme_code: int
    goal_id: Optional[str] = None
    observation_date: date
    assessment_timestamp_utc: datetime
    startup_mode: StartupMode
    suitability_status: SuitabilityStatus
    suitability_confidence_score: float        # 0.0 to 1.0
    aligned_risk_level_used: Optional[AlignedRiskLevel] = None
    fund_risk_level: Optional[RiskLevel] = None
    hard_constraint_violations: List[str] = []
    soft_factor_warnings: List[str] = []
    explanation_tokens: List[str] = []
    missing_information_tokens: List[str] = []
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"
```

---

## 18. Double-Counting Controls

| Concept | Owned Exclusively By | Must NOT Be Evaluated In |
|---|---|---|
| Investor Loss Appetite | Risk Tolerance Engine | Suitability Engine |
| Investor Cash Flow Resilience | Risk Capacity Engine | Suitability Engine |
| Fund Risk-Adjusted Returns | Fund Quality Engine | Suitability Engine |
| Category Return Volatility | Fund Metrics Engine | Suitability Engine |
| Tax & Exit Load Calculations | Tax / Cost Engine | Suitability Engine |
| Fund Overlap & Over-concentration | Portfolio Need Engine | Fund Quality Engine |

---

## 19. Complete Parameter & Governance Register

| Parameter Name | Purpose | Current Value | Governance Status | Validation Required |
|---|---|---|---|---|
| `horizon_equity_min_years` | Min goal horizon for equity funds | `5.0` | `PROVISIONAL` | Empirical risk/horizon study |
| `horizon_hybrid_min_years` | Min goal horizon for hybrid funds | `3.0` | `PROVISIONAL` | Empirical risk/horizon study |
| `horizon_debt_min_years` | Min goal horizon for debt funds | `1.0` | `PROVISIONAL` | SEBI debt duration audit |
| `overlap_material_threshold` | Material security overlap cutoff | `0.30` | `PROVISIONAL` | Portfolio diversification analysis |
| `overlap_excessive_threshold` | Excessive security overlap cutoff | `0.60` | `PROVISIONAL` | Portfolio diversification analysis |
| `amc_concentration_limit` | Max AMC allocation threshold | `0.40` | `PROVISIONAL` | AMC risk concentration audit |

---

## 20. Source & Evidence Audit

| Rule / Factor | Authoritative Source | Exact Supported Fact | Governance Classification |
|---|---|---|---|
| Risk Alignment Lower-Bound | Regulatory (SEBI/AMFI) | Investor risk must bound recommendations | `APPROVED` |
| Statutory Lock-In (ELSS) | IT Act / SEBI Regulations | 3-year statutory lock-in required for ELSS | `APPROVED` (Data Feed TBD) |
| Category Horizon Tiers | Industry Practice / AMFI | General holding period guidelines | `PROVISIONAL` |
| Overlap & AMC Percentages | Financial Planning Practice | Diversification principles | `PROVISIONAL` |

---

## 21. Future Test Strategy (25 Scenarios Specified)

Specified 25 test scenarios covering risk matching, horizon compatibility, lock-in, portfolio overlap, missing data, construct isolation, and determinism. Zero test files were created in Phase F.3.4.1.

---

## 22. Regression Verification

- **Command:** `python -m pytest tests/ -v --tb=short`
- **Result:** **286 / 286 passed cleanly in 1.17s**.

---

## 23. Explicit Implementation Gate

```text
================================================================================
IMPLICIT EXECUTION GATE ENFORCED
================================================================================
Production Suitability Engine implementation (risk/suitability_engine.py)
is STRICTLY BLOCKED in this phase.
Requires separate explicit user authorization.
================================================================================
```

---

## 24. Final Status — Exactly One

```text
PHASE F.3.4.1 ACCEPTED WITH PROVISIONAL METHODOLOGY
```
