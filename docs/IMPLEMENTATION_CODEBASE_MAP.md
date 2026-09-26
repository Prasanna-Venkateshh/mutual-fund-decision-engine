# IMPLEMENTATION CODEBASE MAP — MUTUAL FUND DECISION ENGINE

**Document Title:** Implementation Codebase Map & Requirement Traceability Matrix  
**Document Type:** Independent Verification Baseline (Observed Codebase State)  
**Governance Standard:** Factual, Evidence-Grounded Audit Map  
**Date:** September 2026 UTC  

---

## 1. CODEBASE COMPONENT MAP

| Component Domain | Primary Directory / File | Core Classes & Functions | Purpose & Functionality | Dependencies | Tests | Implementation Status |
|---|---|---|---|---|---|---|
| **Data Ingestion** | `data/ingestion/` | `AMFIIngestor`, `AMFILiveAdapter`, `HistoricalNAVPipeline` | Parses raw AMFI JSON/text feeds (`NAVAll.txt`), fetches live snapshots, runs resumable backfill | `requests`, `models/nav_data.py` | `tests/data_quality/` | IMPLEMENTED |
| **Scheme Master & Identity** | `data/mapping/` | `SchemeMaster`, `CanonicalScheme`, `SchemeMapping` | Resolves AMFI scheme codes & ISINs to canonical schemes | `db/database.py`, `models/scheme.py` | `tests/data_quality/` | IMPLEMENTED |
| **Data Repositories** | `data/repositories/` | `NAVRepository` | Database persistence for raw observations, scheme mappings, normalized NAVs, quarantine, and coverage ledger | `db/database.py` | `tests/integration/` | IMPLEMENTED |
| **Metric Engine** | `metrics/` | `MetricCalculator`, `CAGRCalculator`, `VolatilityCalculator` | Computes CAGR, rolling returns, volatility, downside deviation, max drawdown, TER | `numpy`, `pandas`, `models/` | `tests/financial/` | IMPLEMENTED |
| **Fund Quality Engine** | `scoring/` | `FundQualityScorer`, `ScoringEngine`, `NormalizationEngine` | Computes 6-dimension category-family weighted percentile scores with dynamic rescaling | `scoring/config.py`, `scoring/weights.py` | `tests/scoring/` | IMPLEMENTED |
| **Risk & Suitability** | `risk/` | `RiskCapacityEngine`, `RiskToleranceEngine`, `RiskAlignmentEngine`, `SuitabilityEngine` | Evaluates Risk Capacity, Risk Tolerance, Lower-of-Two Alignment, and Horizon/Asset Suitability | `models/risk.py`, `models/investor.py` | `tests/financial/` | IMPLEMENTED |
| **Portfolio Need** | `portfolio/` | `PortfolioNeedEngine` | Detects portfolio asset allocation gaps, subcategory exposure caps, and candidate fulfillment | `models/portfolio.py` | `tests/financial/` | IMPLEMENTED |
| **Economic Benefit** | `economic_benefit/` | `EconomicBenefitEngine` | Evaluates net return improvement vs tax liability (STCG/LTCG), exit loads, and expense friction | `models/economic_benefit.py` | `tests/financial/` | IMPLEMENTED |
| **Action Decision** | `action/` | `ActionEngine` | Orchestrates final recommendations (`BUY`, `ACCUMULATE`, `HOLD`, `MONITOR`, `REVIEW`, `SELL`) | `models/action.py` | `tests/financial/` | IMPLEMENTED |
| **Decision Orchestrator** | `integration/` | `DecisionOrchestrator` | End-to-end integration wrapper connecting layers 1 through 7 into unified portfolio assessment | All domain engines | `tests/integration/` | IMPLEMENTED |
| **User Decision & Audit** | `audit/` | `AuditLogger`, `UserDecisionState` | Maintains immutable assessment logs, audit trails, and user decision state separation | `db/database.py` | `tests/integration/` | IMPLEMENTED |

---

## 2. REQUIREMENT TRACEABILITY MATRIX

| Requirement ID | Intended Classification | Intended Requirement | Current Implementation | Exact Files | Tests | Implementation Status | Validation Status | Evidence | Discrepancy |
|---|---|---|---|---|---|---|---|---|---|
| `REQ-FQ-001` | `INTENDED V1 CAPABILITY` | 6-Dimension Fund Quality Scoring | 6-dimension weighted percentile ranking | `scoring/engine.py` | `tests/scoring/` | IMPLEMENTED | Class B (F.16 2-Dim Historical Snapshot) | `scoring/config.py` | `DISC-001` (Degraded-data validation) |
| `REQ-FQ-002` | `INTENDED V1 CAPABILITY` | Dynamic Weight Rescaling | Dynamic rescaling for missing metric inputs | `scoring/engine.py` | `tests/scoring/` | IMPLEMENTED | Verified Mathematically | `scoring/engine.py` | `DISC-004` (Unvalidated long OOS) |
| `REQ-FQ-003` | `MANDATORY V1 REQUIREMENT` | Zero-Return Non-None Retainment | Retention of 0.0% numerical return observations | `scoring/engine.py` | `tests/scoring/` | IMPLEMENTED | Verified FIXED (F.19.2) | L81 & L89 `(cagr_overall if ...)` | None (`DEFECT-FQ-2026-001` resolved) |
| `REQ-RSK-001` | `MANDATORY V1 REQUIREMENT` | Lower-of-Two Risk Alignment | Aligned Risk = min(Capacity, Tolerance) | `risk/risk_alignment_engine.py` | `tests/financial/` | IMPLEMENTED | Verified 100% Pass | `risk/risk_alignment_engine.py` | None |
| `REQ-SUT-001` | `MANDATORY V1 REQUIREMENT` | 5-Step Suitability Gating | Hard constraint > Conditional > Positive evidence | `risk/suitability_engine.py` | `tests/financial/` | IMPLEMENTED | Verified 100% Pass | `risk/suitability_engine.py` | None |
| `REQ-ACT-001` | `MANDATORY V1 REQUIREMENT` | Action Precedence & Deterioration | Action gating: BLOCK > HOLD > BUY/SELL | `action/engine.py` | `tests/financial/` | IMPLEMENTED | Verified 100% Pass | `action/engine.py` | None |
| `REQ-ECO-001` | `MANDATORY V1 REQUIREMENT` | Tax & Exit Load Hurdle Check | Single-trade net return improvement vs STCG/LTCG & exit loads | `economic_benefit/engine.py` | `tests/financial/` | IMPLEMENTED | Verified Single-Period Hurdle | `economic_benefit/engine.py` | `DISC-002` (Multi-year tax harvest out of scope) |
| `REQ-USR-001` | `MANDATORY V1 REQUIREMENT` | User Decision State Separation | System Rec != User Decision != Execution Status | `audit/user_decision_state.py` | `tests/integration/` | IMPLEMENTED | Verified 100% Pass | `audit/user_decision_state.py` | None |

---

## 3. INTENDED vs IMPLEMENTED DISCREPANCY REGISTER

| Discrepancy ID | Intended Specification & Classification | Current Codebase Implementation | Source of Specification | Source of Implementation | Severity | Financial Significance | Notes |
|---|---|---|---|---|---|---|---|
| `DISC-001` | **Intended:** Multi-dimensional Fund Quality methodology requires empirical validation (`RESEARCH / VALIDATION OBJECTIVE`).<br>**Classification:** Empirical validation objective. | F.16 evaluated 2 non-None dimensions (Return & Volatility) on a 1-year historical snapshot (`2024-01-31`). | `phase_e_fund_quality_scoring_methodology.md` | `docs/phase_f16_exact_production_oos_validation_report.md` | MEDIUM | High (Full 6-dimension empirical validation across multi-decade cycles remains a future validation goal) | Classified as Class B validation under degraded historical data in F.19.1. |
| `DISC-002` | **Intended:** Switching recommendations evaluate after-tax/after-cost net economic benefit (`MANDATORY V1 REQUIREMENT`).<br>**Classification:** Mandatory V1 single-trade hurdle; multi-year tax harvesting is `FUTURE / V2 / EXTENSION`. | Single-period STCG/LTCG tax and exit-load hurdle evaluation (`ECONOMICALLY_BENEFICIAL`). | `phase_f5_economic_benefit_specification.md` | `economic_benefit/engine.py` | LOW | Low (Mandatory V1 single-trade tax friction hurdle is fully implemented) | Multi-year tax-loss harvesting algorithms are documented as future V2 scope. |
| `DISC-003` | **Intended:** Prefer free & authoritative AMFI/SEBI data sources (`MANDATORY V1 REQUIREMENT`).<br>**Classification:** Mandatory V1 data preference. | Core NAV & CAGR feeds are 100% authoritative AMFI live feeds (`NAVAll.txt`); historical TER & Riskometer depth prior to 2021 is partial. | `phase_f10_2_authoritative_metadata...md` | `data/ingestion/ter_feed_adapter.py` | LOW | Low (Core NAV time-series and scheme mappings remain 100% authoritative) | Documented non-blocking limitation. |

---

## 4. DATABASE SCHEMA MAP

1. `raw_nav_observations`: Stores immutable unparsed raw AMFI NAV lines, source ID, retrieval timestamp, line number, and raw metadata.
2. `canonical_schemes`: Stores canonical scheme identity, AMC name, clean scheme name, plan type, option type, category, subcategory, primary AMFI code, ISINs, and active status.
3. `scheme_mappings`: Maps raw source scheme codes and names to `canonical_scheme_id` with mapping confidence scores and notes.
4. `normalized_nav_records`: Stores clean normalized NAV time-series indexed by `canonical_scheme_id` and `nav_date`.
5. `quarantine_records`: Stores quarantined unparseable or unmapped raw records with failure stage and reason.
6. `acquisition_coverage_ledger`: Tracks historical backfill windows, retrieval HTTP status, record counts, response hash, and completion status.
7. `assessment_audit_log`: Immutably logs full `DecisionOrchestrator` evaluation payloads, investor profile state, portfolio snapshot, and generated recommendations.

---

## 5. UI READINESS MAP

| UI View | Backend Engine / Contract | Backend Contract Status | Missing / Unresolved Gaps | Frontend Build Readiness |
|---|---|---|---|---|
| **Dashboard** | `integration/orchestrator.py` | **STABLE** (`DecisionOrchestrator.evaluate_portfolio()`) | None | **READY** |
| **Investor Profile** | `risk/risk_capacity_engine.py`, `risk_tolerance_engine.py` | **STABLE** (`InvestorProfile` dataclass) | None | **READY** |
| **Fund Scanner** | `scoring/engine.py` | **STABLE** (`FundQualityScorer.calculate_score()`) | None | **READY** |
| **Fund Detail** | `metrics/`, `scoring/` | **STABLE** (Metrics & FQ Score decomposition) | None | **READY** |
| **Portfolio Assessment** | `portfolio/need_engine.py`, `action/engine.py` | **STABLE** (`PortfolioAssessmentPayload`) | None | **READY** |
| **Decision Detail** | `integration/orchestrator.py` | **STABLE** (`DecisionExplanation` output) | None | **READY** |

---

## DOCUMENT SCOPE

This document establishes the **Implementation Codebase Map & Traceability Matrix** for the `mutual-fund-decision-engine`.

**What it DOES establish:**
- Verified map of files, classes, functions, databases, and test suites in the repository.
- Objective requirement traceability matrix with governed requirement classifications and implementation statuses.
- Discrepancy register accurately framing intended goals vs codebase reality.

**What it DOES NOT establish:**
- Endorsement or subjective judgment of whether the financial methodology is superior (see independent audit report).
