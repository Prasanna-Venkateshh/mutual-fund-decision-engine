# Phase F.3.4.2 — Suitability Input Architecture & Data Flow Document

**Phase:** Phase F.3.4.2 — Suitability Data Contracts, Input Architecture & Ownership Governance  
**Date:** 2026-09-10 UTC  
**Status:** Approved Input Architecture  
**Final Decision:** `PHASE F.3.4.2 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Architectural blueprint of data flows, dependency graphs, missing-data propagation, and boundary enforcement for the future Suitability Engine.

---

## 1. Architectural Position & Dependency Graph

The Suitability Engine operates as a read-only evaluation layer downstream of Fund Quality and Risk Alignment, and upstream of Portfolio Need and Economic Action:

```text
┌───────────────────────────┐     ┌───────────────────────────┐
│     Investor Profile      │     │       Goal Profile        │
└─────────────┬─────────────┘     └─────────────┬─────────────┘
              │                                 │
              │ InvestorProfileSnapshot         │ GoalProfileSnapshot
              ▼                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Risk Alignment Engine                    │
│   (Consumes Risk Capacity & Risk Tolerance Outputs)         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ RiskAlignmentAssessmentResult
                               ▼
┌─────────────────────────────────────────────────────────────┐     ┌───────────────────────────┐
│                     Fund Quality Engine                     │     │  Fund Risk Profile / SEBI │
│      (Produces Category Merit & Evidence Confidence)        │     │         Riskometer        │
└──────────────────────────────┬──────────────────────────────┘     └─────────────┬─────────────┘
                               │                                                  │
                               │ FundQualityAssessmentResult                      │ FundRiskProfile
                               ▼                                                  ▼
                  ===================================================================== SUITABILITY BOUNDARY
                  ┌───────────────────────────────────────────────────────────────────┐
                  │                        Suitability Engine                         │
                  │        (Evaluates Contextual Appropriateness & Confidence)        │
                  └─────────────────────────────────┬─────────────────────────────────┘
                                                    │
                                                    │ SuitabilityAssessmentResult
                                                    ▼
                  ┌───────────────────────────────────────────────────────────────────┐
                  │                       Portfolio Need Engine                       │
                  │               (Evaluates Gap Reduction & Allocation)              │
                  └─────────────────────────────────┬─────────────────────────────────┘
                                                    │
                                                    ▼
                  ┌───────────────────────────────────────────────────────────────────┐
                  │                 Economic Benefit / Action Engine                  │
                  │             [Buy / Accumulate / Hold / Sell Decisions]            │
                  └───────────────────────────────────────────────────────────────────┘
```

---

## 2. Upstream Data Flow Contracts

1. **Risk Data Flow:** `RiskCapacityEngine` & `RiskToleranceEngine` $\rightarrow$ `RiskAlignmentEngine` $\rightarrow$ `RiskAlignmentAssessmentResult` $\rightarrow$ `SuitabilityEngine`. Suitability receives a pre-aligned supportable risk envelope (`aligned_risk_level`).
2. **Fund Data Flow:** Raw NAV Observations $\rightarrow$ `MetricsEngine` $\rightarrow$ `FundQualityEngine` $\rightarrow$ `FundQualityAssessmentResult` $\rightarrow$ `SuitabilityEngine`. Suitability receives pre-scored category merit and confidence.
3. **Goal Data Flow:** User Input $\rightarrow$ `GoalRepository` $\rightarrow$ `GoalProfileSnapshot` $\rightarrow$ `SuitabilityEngine`. Suitability receives goal horizon, target date, and liquidity requirements.
4. **Portfolio Data Flow:** User Holdings / CAS Ingestion $\rightarrow$ `PortfolioRepository` $\rightarrow$ `PortfolioHoldingContext` $\rightarrow$ `SuitabilityEngine`. Suitability receives category breakdowns and security overlap metrics in read-only mode.

---

## 3. Context Selection Architecture

The engine selects its evaluation context dynamically based on input availability:

```text
                                ┌───────────────────────────┐
                                │     Input Request Data    │
                                └─────────────┬─────────────┘
                                              │
                                   Is goal_id provided?
                                   /                 \
                             YES  /                   \  NO
                                 ▼                     ▼
                   ┌───────────────────────────┐ ┌───────────────────────────┐
                   │   Goal-Linked Assessment  │ │  General Wealth Assessment│
                   │   - Uses Goal Horizon     │ │   - Uses Profile Horizon  │
                   │   - Scoped by goal_id     │ │   - Default: LONG (5+ yrs)│
                   └─────────────┬─────────────┘ └─────────────┬─────────────┘
                                 │                             │
                                 └──────────────┬──────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │ Portfolio Holding Context State │
                               └────────────────┬────────────────┘
                                                │
                                 Is portfolio context available?
                                 /                               \
                           YES  /                                 \  NO / ABSENT
                               ▼                                   ▼
                 ┌───────────────────────────┐       ┌───────────────────────────┐
                 │ Portfolio-Aware Filtering │       │   Standalone Suitability  │
                 │ - Evaluates Overlap       │       │   - Overlap: UNKNOWN      │
                 │ - Evaluates Concentration │       │   - AMC Limit: UNKNOWN    │
                 └─────────────┬─────────────┘       └─────────────┬─────────────┘
                               │                                   │
                               └────────────────┬──────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │  Emit SuitabilityAssessmentResult│
                               └─────────────────────────────────┘
```

---

## 4. Missing & Stale Data Flow Handling

1. **Missing Risk Alignment:** Halts evaluation immediately; emits `INSUFFICIENT_INFORMATION` and token `MISSING_RISK_ALIGNMENT`.
2. **Missing Fund Quality:** Continues evaluation under constraint-first logic; emits `CONDITIONALLY_SUITABLE` or `INSUFFICIENT_INFORMATION` with token `MISSING_FUND_QUALITY_SCORE`.
3. **Stale Risk Alignment ($> 90$ Days Gap):** Consumes `is_stale_input = True` flag; reduces suitability confidence score, appends `STALE_RISK_ALIGNMENT_INPUT` token, but leaves risk tier unchanged.
4. **Absence of Portfolio Data:** Emits `NO_PORTFOLIO_CONTEXT` token; overlap status is set to `UNKNOWN` without penalizing standalone fund suitability.

---

## 5. Construct Isolation & Downstream Boundaries

- **Zero Upstream Recalculation:** Suitability **never** invokes financial calculations for debt ratio, reserve coverage, questionnaire scoring, CAGR, rolling returns, or Sharpe ratios.
- **Zero Downstream Execution:** Suitability outputs suitability status (`SUITABLE`, `NOT_SUITABLE`, etc.) and confidence. It does **not** calculate SIP contribution amounts, after-tax switching benefit, or emit `BUY`/`SELL` actions.
