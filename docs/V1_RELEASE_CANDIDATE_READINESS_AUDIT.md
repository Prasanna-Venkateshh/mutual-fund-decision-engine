# V1 Release-Candidate Readiness Audit and Gap Closure Plan

**Document ID**: `docs/V1_RELEASE_CANDIDATE_READINESS_AUDIT.md`  
**Evaluation Scope**: Complete Product Readiness Audit, Mandatory V1 Traceability, 28 Product Layers Audit, Data Readiness, 14 Release Gate Dimensions, and Gap Closure Implementation Sequence  
**Audit Date**: September 2026 UTC  
**Baseline State**: Real-Data Fund Quality Forensic Gate Accepted (`CAN_AMFI_101206`, exact peer population = 105, SHA256 `fa34100cd70c...`)  
**Database Snapshot**: `db/backfill_f12_2.db` (17,507 Canonical Schemes, 13,469,115 Raw Observations, 6,337,995 Normalized NAV Records)  

---

## 1. Executive Summary

This document presents the **V1 Release-Candidate Readiness Audit and Gap Closure Plan** for the Mutual Fund Decision Engine. Following the acceptance of the real-data Fund Quality forensic gate, this audit evaluates the entire product architecture to establish what is genuinely ready, what remains provisional or constrained, and what specific implementation steps are required to achieve full production release.

### Key Audit Conclusions

1. **Engine Readiness (100% READY)**: All 7 core backend domain engines ([`FundQualityScoringEngine`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scoring/engine.py), [`RiskCapacityEngine`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/risk_capacity_engine.py), [`RiskToleranceEngine`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/risk_tolerance_engine.py), [`RiskAlignmentEngine`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/risk_alignment_engine.py), [`SuitabilityEngine`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/suitability_engine.py), [`PortfolioNeedEngine`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/portfolio/need_engine.py), [`EconomicBenefitEngine`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/economic_benefit/engine.py), [`ActionEngine`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/action/engine.py), and [`DecisionOrchestrator`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/integration/orchestrator.py)) are fully implemented, frozen, and verified by comprehensive automated test suites.
2. **Data Readiness (PROVISIONAL / CONSTRAINED)**: The data infrastructure and database schema in `db/backfill_f12_2.db` are 100% operational. Daily NAV feeds and scheme master tables (17,507 schemes, 13.4M raw NAVs) are 100% authoritative AMFI data. However, historical TER prior to 2021, SEBI Riskometer progression depth, and custom benchmark TRI time-series remain partially populated. Under governed rules, missing fields evaluate to `None` and reduce `confidence_score` or active weight sums without causing false positive scores or silent errors.
3. **UI / Screen Readiness (IMPLEMENTED & ADAPTER READY)**: All 10 core V1 web screens (`/onboarding`, `/`, `/wealth`, `/wealth/goals/:id`, `/discover`, `/scheme/:id`, `/discover/compare`, `/action/evaluate-switch`, `/action-center`, `/settings`) are fully implemented in [`web/app.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/web/app.py) with presentation adapters in [`web/adapters.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/web/adapters.py).
4. **Product Gaps for V1 Release**:
   - **User Profile / Session Persistence (ONBOARDING / PROFILE)**: 🟠 Material V1 implementation gap. Core questionnaire flow and profile object mapping exist (`QuestionnaireAdapter`), but persistent multi-session profile storage is not yet implemented.
   - **Portfolio Transactions Ingestion Adapter (PORTFOLIO INGESTION)**: 🟠 Material V1 implementation gap. Portfolio decision engine and snapshot contract are fully implemented, but direct user portfolio acquisition / CAS-CSV transaction ingestion is not yet implemented.
   - **Production Authentication & Security Gateway (SECURITY)**: 🟡 Provisional / constrained for local/internal V1 development; 🟠 Deployment gate for internet/cloud production deployment. Web server currently runs without user login/auth headers.
5. **Overall V1 Status**: 🟠 **V1 GAPS REQUIRE IMPLEMENTATION**. The financial decision core is sound and accepted, but the complete V1 product baseline still requires identified product/infrastructure implementation work.


---

## 2. Current V1 Baseline Audit (28 Product Layers)

| Layer # | Product Layer | Current Implementation Status | Audit Classification | Codebase File / Reference | Empirical Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Data Ingestion** | Full live AMFI adapter (`NAVAll.txt`) & backfill pipeline | 🟢 Sound / accepted | `data/ingestion/amfi_live_adapter.py` | 13.4M raw NAVs ingested |
| **2** | **Scheme Identity** | AMFI code & ISIN mapping to canonical scheme IDs | 🟢 Sound / accepted | `data/mapping/scheme_master.py` | 17,507 schemes mapped |
| **3** | **Historical NAV** | Clean time-series indexed by scheme ID & date | 🟢 Sound / accepted | `data/repositories/nav_repository.py` | 6.3M normalized NAV records |
| **4** | **Scheme Lifecycle** | Mergers, rebrands, and closures tracked with events | 🟢 Sound / accepted | `data/ingestion/sebi_tier2_expansion_extractor.py` | `scheme_lifecycle_events` table |
| **5** | **Category/PIT Context** | Point-in-time SEBI 2017+ category resolution | 🟢 Sound / accepted | `data/adapters/category_context_adapter.py` | Verified pre/post 2017 boundaries |
| **6** | **Fund Metrics** | CAGR, rolling returns, volatility, downside, MDD, TER | 🟢 Sound / accepted | `metrics/metric_calculator.py` | Tested across 37 financial tests |
| **7** | **Fund Quality** | 6D weighted percentile scoring with dynamic rescaling | 🟢 Sound / accepted | `scoring/engine.py` | F.19 forensic gate accepted |
| **8** | **Risk Capacity** | Financial capacity evaluation & tier assignment | 🟢 Sound / accepted | `risk/risk_capacity_engine.py` | Tested in `test_risk_capacity_engine.py` |
| **9** | **Risk Tolerance** | Behavioral tolerance evaluation & tier assignment | 🟢 Sound / accepted | `risk/risk_tolerance_engine.py` | Tested in `test_risk_tolerance_engine.py` |
| **10** | **Risk Alignment** | Aligned Risk Tier = $\min(\text{Capacity}, \text{Tolerance})$ | 🟢 Sound / accepted | `risk/risk_alignment_engine.py` | 100% pass on REQ-RSK-001 |
| **11** | **Suitability** | 5-step suitability gating & status assignment | 🟢 Sound / accepted | `risk/suitability_engine.py` | Tested in `test_suitability_engine.py` |
| **12** | **Portfolio Need** | Subcategory caps, asset allocation gaps, overlap | 🟢 Sound / accepted | `portfolio/need_engine.py` | Tested in `test_portfolio_need_engine.py` |
| **13** | **Economic Benefit** | Net return improvement vs STCG/LTCG tax & exit loads | 🟢 Sound / accepted | `economic_benefit/engine.py` | Single-trade hurdle verified |
| **14** | **Action Engine** | Action precedence: $\text{BLOCK} > \text{HOLD} > \text{BUY/SELL}$ | 🟢 Sound / accepted | `action/engine.py` | Tested in `test_action_engine.py` |
| **15** | **Decision Orchestrator** | 7-layer end-to-end portfolio assessment wrapper | 🟢 Sound / accepted | `integration/orchestrator.py` | Verified in `test_decision_orchestrator.py` |
| **16** | **Portfolio Integration** | Decision engine & snapshot contract implemented; CAS/CSV user ingestion missing | 🟠 Material V1 implementation gap | `models/portfolio.py` | Engine & snapshot contract active; user CAS/CSV parser missing |
| **17** | **Goals** | Goal targets & progress snapshots supported | 🟢 Sound / accepted | `models/investor.py` | Goal strategy active; subject to portfolio-ingestion dependency |
| **18** | **Investor Onboarding** | Questionnaire flow implemented; persistent profile storage missing | 🟠 Material V1 implementation gap | `web/adapters.py` (`QuestionnaireAdapter`) | 10-question flow active; multi-session storage missing |
| **19** | **What Changed** | Snapshot diffing comparing raw $v_1$ vs $v_2$ fields | 🟢 Sound / accepted | `web/adapters.py` (`SnapshotDiffAdapter`) | Neutral before/after diffs |
| **20** | **Action Center** | `/action-center` UI route with ActionState separation | 🟢 Sound / accepted | `web/app.py` | Renders 7 action states |
| **21** | **Notifications/Alerts** | ActionState decoupled from notification push urgency | 🟡 Implemented / constrained | `web/adapters.py` | Alert adapter ready; push channels V2 |
| **22** | **Provenance** | Traceability to source ID, date, calculation, version | 🟢 Sound / accepted | `models/provenance.py` | AMFI source URLs & dates displayed |
| **23** | **Audit History** | Immutable assessment logs & audit state records | 🟢 Sound / accepted | `audit/user_decision_state.py` | `assessment_audit_log` DB table |
| **24** | **UI Routes** | 10 core V1 screens implemented in web server | 🟢 Sound / accepted | `web/app.py` | Serves all 10 V1 routes |
| **25** | **Tests** | 1,492 unit, financial, data-quality, & UI tests | 🟢 Sound / accepted | `tests/` | All test suites passing |
| **26** | **Documentation** | Reconciled audit status and eliminated contradictions | 🟠 Reconciled in this audit | `docs/` | Traceable documentation reconciled to audit findings |
| **27** | **Security/Privacy** | Zero external data leakage; auth gateway absent | 🟡 Provisional / constrained (local) / 🟠 Deployment gate (cloud) | `web/app.py` | Local execution safe; cloud auth gateway required for cloud release |
| **28** | **Data Readiness** | AMFI feeds 100%; pre-2021 TER & Riskometer partial | 🟡 Implemented / constrained | `db/backfill_f12_2.db` | Missing data handled safely as `None` |

---

## 3. Mandatory V1 Requirement Traceability Matrix

All 8 mandatory V1 requirements defined in [`docs/INTENDED_PRODUCT_SPECIFICATION.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/INTENDED_PRODUCT_SPECIFICATION.md) are audited below:

| Requirement ID | Requirement Description | Implementation Location | Runtime Evidence | Tests | Documentation | Current Status | Remaining Gap | V1 / V2 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`REQ-ACT-001`** | **Point-in-Time Recommendations**: Structured actions (`BUY`, `ACCUMULATE`, `HOLD`, `MONITOR`, `REVIEW`, `SELL`) strictly from snapshot data. | `action/engine.py` | `EndToEndDecisionResult.final_action_state` | `test_action_engine.py` | `INTENDED_PRODUCT_SPECIFICATION.md` §1 | **IMPLEMENTED** | None | **Mandatory V1** |
| **`REQ-FQ-001`** | **Anti-Survivorship Bias**: Peer group comparisons strictly relative to point-in-time eligible peer populations. | `scoring/engine.py` | `FundQualityScoringEngine.calculate_fund_quality_score()` | `test_fund_quality_scoring.py` | `INTENDED_PRODUCT_SPECIFICATION.md` §1 | **IMPLEMENTED** | None | **Mandatory V1** |
| **`REQ-RSK-001`** | **Lower-of-Two Risk Alignment**: Aligned Risk Tier = $\min(\text{Risk Capacity Tier}, \text{Risk Tolerance Tier})$. | `risk/risk_alignment_engine.py` | `RiskAlignmentEngine.calculate_alignment()` | `test_risk_alignment_engine.py` | `INTENDED_PRODUCT_SPECIFICATION.md` §1 | **IMPLEMENTED** | None | **Mandatory V1** |
| **`REQ-PORT-001`** | **Portfolio Need Before Rec**: Validate asset allocation gaps, subcategory exposure caps, and candidate fulfillment. | `portfolio/need_engine.py` | `PortfolioNeedEngine.evaluate_portfolio_need()` | `test_portfolio_need_engine.py` | `INTENDED_PRODUCT_SPECIFICATION.md` §1 | **IMPLEMENTED** | None | **Mandatory V1** |
| **`REQ-ECO-001`** | **Economic Friction Evaluation**: Net return improvement after deducting exit loads and STCG/LTCG tax hurdles. | `economic_benefit/engine.py` | `EconomicBenefitEngine.evaluate_economic_benefit()` | `test_integration_contracts.py` | `INTENDED_PRODUCT_SPECIFICATION.md` §1 | **IMPLEMENTED** | None | **Mandatory V1** |
| **`REQ-AUD-001`** | **100% Auditability & Explainability**: Immutable audit log payload and structured natural-language rationale. | `integration/orchestrator.py`, `audit/` | `AuditLogger.log_assessment()`, `DecisionExplanation` | `test_decision_orchestrator.py` | `INTENDED_PRODUCT_SPECIFICATION.md` §1 | **IMPLEMENTED** | None | **Mandatory V1** |
| **`REQ-USR-001`** | **User-Control Separation**: System Rec $\neq$ User Decision $\neq$ Execution Status. Zero automated trade execution. | `audit/user_decision_state.py` | `UserDecisionRecord`, `AuditStateRecord` | `test_adversarial_financial_safety.py` | `INTENDED_PRODUCT_SPECIFICATION.md` §1 | **IMPLEMENTED** | None | **Mandatory V1** |
| **`REQ-FQ-003`** | **Zero-Return Non-None Retainment**: `0.0%` numerical returns retained as valid metrics and distinguished from `None`. | `scoring/engine.py` | `(cagr_overall if ... is not None)` check | `test_f19_2_zero_return_defect_remediation.py` | `phase_f19_2_zero_return_defect_remediation_report.md` | **IMPLEMENTED** | None (Fixed in F.19.2) | **Mandatory V1** |

---

## 4. Data Readiness Audit

The repository data assets in `db/backfill_f12_2.db` are classified across four readiness tiers:

```
+-----------------------------------------------------------------------------------+
| 1. INFRASTRUCTURE READY: Tables created, primary keys indexed, foreign keys set  |
|    (canonical_schemes, normalized_nav_records, raw_nav_observations, etc.)       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 2. DATA POPULATED: 17,507 schemes, 13.4M raw NAV lines, 6.3M normalized NAVs      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 3. DATA AUTHORITATIVE: 100% AMFI official daily feeds (NAVAll.txt) & ISIN master |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 4. DATA SUFFICIENT FOR DECISION: Full daily NAV time-series for core debt/equity |
|    (Partial pre-2021 TER/Riskometer data evaluates to None safely)                |
+-----------------------------------------------------------------------------------+
```

### Field-Specific Data Readiness & Governance Impact

| Data Field | Source Authority | Data Populated Status | Missing-Data Governance Rule | Impact on Engine Execution |
| :--- | :--- | :--- | :--- | :--- |
| **AMFI Scheme Code** | AMFI Official Master | 100% Populated (17,507 schemes) | Cannot be missing | Primary Identity Key |
| **Scheme Name & Plan** | AMFI Official Master | 100% Populated | Cannot be missing | Used for Plan & Category Adapter |
| **Daily NAV Time-Series** | AMFI Official Daily Feeds | 6.3M records (2020–2025) | Gap produces `None` for metric window | If history < 1Y, `quality_score = None` |
| **CAGR / Return Metrics** | Computed from NAV | 100% computed where NAV exists | Evaluates to `None` if NAV incomplete | Rescales active weights proportionally |
| **Volatility & Downside** | Computed from NAV | 100% computed where NAV exists | Evaluates to `None` if NAV incomplete | Rescales active weights proportionally |
| **TER (Expense Ratio)** | AMFI / AMC Disclosures | Populated 2021–2025 (~65% depth) | Evaluates to `None` (Missing != 0.0) | Cost dimension weight rescaled |
| **SEBI Riskometer** | SEBI Monthly Disclosures | Populated 2021–2025 (~60% depth) | Evaluates to `None` | `confidence_score` reduced |
| **Benchmark Index TRI** | AMFI / NSE / BSE | Core indices populated (~80% depth)| Evaluates to `None` | Informational; does not block FQ |

---

## 5. Fund Quality Readiness

The Fund Quality scoring subsystem was verified during the Phase F.19 forensic gate and is confirmed 100% operational:

- **6-Dimensional Scoring Active**: `return` (15%), `consistency` (20%), `volatility` (25%), `downside_risk` (20%), `max_drawdown` (10%), `cost_efficiency` (10%).
- **Exact Peer Key**: `category::subcategory::plan_type` (e.g. `Debt::Overnight::REGULAR`).
- **Missing Data Governance**: Missing metrics are strictly `None` (never numerical `0.0`).
- **Dynamic Weight Rescaling**: Available metrics dynamically rescale to sum to 100.0%. Minimum active weight sum required = `40.0%`.
- **Score vs Confidence Separation**: `quality_score` ($0.0 - 100.0$) and `confidence_score` ($0.0 - 1.0$) remain completely separate dataclass fields.
- **Zero-Return Non-None Retainment**: Tested and verified in `test_f19_2_zero_return_defect_remediation.py`.
- **Score Alone Does Not Trigger Action**: High Fund Quality alone NEVER emits `BUY`; Low Fund Quality alone NEVER emits `SELL` (`test_adversarial_financial_safety.py`).
- **New Fund Maturity**: Schemes with < 1 year history evaluate to `quality_score = None`, preventing invalid scoring of unestablished funds.

---

## 6. Risk and Suitability Readiness

The risk and suitability domain engines are fully implemented and verified against governing standards:

1. **Risk Capacity Engine** ([`risk/risk_capacity_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/risk_capacity_engine.py)): Evaluates emergency reserve months, income stability, net worth, and investment horizon to determine `RiskCapacityTier` (`ULTRA_LOW`, `LOW`, `MODERATE`, `HIGH`, `VERY_HIGH`).
2. **Risk Tolerance Engine** ([`risk/risk_tolerance_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/risk_tolerance_engine.py)): Evaluates behavioral questionnaire choices to assign `RiskToleranceTier`.
3. **Risk Alignment Engine** ([`risk/risk_alignment_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/risk_alignment_engine.py)): Strictly enforces `Aligned Risk Tier = min(Capacity, Tolerance)` per `REQ-RSK-001`.
4. **Suitability Engine** ([`risk/suitability_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/suitability_engine.py)): Evaluates 5-step suitability gating (`INVALID_ASSESSMENT > INSUFFICIENT_INFORMATION > HARD_CONSTRAINT > CONDITIONAL_CONCERN > POSITIVE_EVIDENCE`).

## 7. Portfolio and Goals Readiness

**Audit Classification: PORTFOLIO INGESTION — 🟠 Material V1 implementation gap | GOALS — 🟢 Sound / accepted (subject to portfolio-ingestion dependency)**

The portfolio subsystem status is classified with the following exact distinctions:

- **PORTFOLIO DECISION ENGINE = IMPLEMENTED**: Evaluates asset allocation gaps, subcategory exposure caps (e.g. max 30% in Small Cap), and candidate fulfillment in [`portfolio/need_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/portfolio/need_engine.py).
- **PORTFOLIO SNAPSHOT CONTRACT = IMPLEMENTED**: Data structures and model contracts for `PortfolioSnapshot` and `PortfolioHolding` are active in [`models/portfolio.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/models/portfolio.py).
- **USER PORTFOLIO ACQUISITION / CAS-CSV INGESTION = MISSING**: Direct user portfolio ingestion through CAS/CSV file upload parser is not yet implemented.
- **GOALS INTEGRATION = ACCEPTED**: Goal-level targets and funding progress (`GoalFundingSnapshot`) are active within the whole-portfolio capacity constraint, subject to the portfolio-ingestion dependency.
- **Non-Transactional Principle**: Recommendations remain strictly advisory. User target adjustments recalculate portfolio fit without initiating trades.


---

## 8. Decision Chain Integration Readiness

The end-to-end decision chain connects all 7 domain layers through [`DecisionOrchestrator`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/integration/orchestrator.py):

```
+-----------------------------------------------------------------------------------+
| Fund Quality (quality_score) & Confidence (confidence_score)                      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Suitability Assessment (SuitabilityStatus)                                        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Portfolio Need Evaluation (PortfolioNeedState)                                    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Economic Benefit Hurdle Math (EconomicBenefitState)                               |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Final Action State (ActionState: BUY, ACCUMULATE, HOLD, MONITOR, REVIEW, SELL)    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| User Decision Record (user_action: ACCEPT / REJECT / DEFER)                       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Audit State Record (execution_status: NOT_EXECUTED)                               |
+-----------------------------------------------------------------------------------+
```

### Verification of Field Mappings

- **Fund Quality**: `FundQualityScoreResult.quality_score`
- **Confidence**: `FundQualityScoreResult.confidence_score`
- **Suitability**: `SuitabilityAssessmentResult.status`
- **Portfolio Need**: `PortfolioNeedAssessmentResult.primary_state`
- **Economic Benefit**: `EconomicBenefitIntegrationContract.economic_benefit_state`
- **Action**: `EndToEndDecisionResult.final_action_state`
- **User Decision**: `UserDecisionRecord.user_action`
- **Execution Status**: `AuditStateRecord.execution_status` (`NOT_EXECUTED`)

---

## 9. User Onboarding and Profile Readiness

**Audit Classification: ONBOARDING / PROFILE — 🟠 Material V1 implementation gap**

The onboarding and investor profile status is classified with the following exact distinctions:

- **QUESTIONNAIRE FLOW = IMPLEMENTED**: The 10-question onboarding flow, countdown progression (10 $\rightarrow$ 1), capacity/tolerance separation, and presentation adapter are fully implemented in [`web/adapters.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/web/adapters.py) (`QuestionnaireAdapter`).
- **PROFILE PERSISTENCE = MISSING**: Persistent multi-session database/file storage for `InvestorProfileSnapshot` objects is not yet implemented. Profile objects are currently instantiated in-memory during single-session evaluation.
- **Skip & "Don't Know" Handling**: Unanswered or skipped questions result in `None` fields, correctly triggering backend `INSUFFICIENT_INFORMATION` safety gating.

---

## 10. What Changed (Snapshot Diff Mechanism)

The snapshot diffing mechanism is implemented in [`web/adapters.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/web/adapters.py) (`SnapshotDiffAdapter`):

- **Raw Field Comparison**: Compares previous versioned payload $v_1$ against current versioned payload $v_2$ across raw fields (`previous_value` $\rightarrow$ `current_value`).
- **Neutral Presentation**: Displays raw deltas without inferring consequential materiality unless a specific governed rule exists.
- **Traceability**: Rendered in SCR-02 Home Dashboard under "What Changed".

---

## 11. Action Center Readiness

The Action Center is served at route `/action-center` in [`web/app.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/web/app.py):

- **ActionState Separation**: Decoupled from notification urgency. `ActionState` represents financial recommendation state, not delivery channel priority.
- **Supported Action States**: `BUY`, `ACCUMULATE`, `HOLD`, `MONITOR`, `REVIEW`, `SELL`, `INSUFFICIENT_INFORMATION`.
- **Explanation Structure**: 1. System Recommendation, 2. Why, 3. Decision Chain Breakdown, 4. Evidence Strength, 5. Data Provenance & Methodology.
- **"No Action" First-Class Outcome**: `HOLD` state displays a calm, neutral confirmation: `"Nothing requires action right now. Your portfolio continues to be monitored."`

---

## 12. Tax, Exit Load, and Economic Benefit Readiness

The V1 economic benefit boundary is implemented in [`economic_benefit/engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/economic_benefit/engine.py):

- **Mandatory V1 Scope**: Evaluates single-trade STCG/LTCG tax hurdles and exit load deductions.
- **V2 Scope Boundary**: Multi-year tax-loss harvesting algorithms and dynamic multi-period rebalancing are explicitly deferred to V2.
- **User/Data Driven**: Tax amounts are calculated using transaction assumptions passed in contracts. Missing cost metadata returns `BENEFIT_UNCERTAIN`, blocking `SELL` recommendations and gating to `REVIEW` or `HOLD`.

---

## 13. Provenance Readiness

Every displayed financial fact in the platform is traceable to authoritative metadata:

- **Source ID**: AMFI Official Daily Feed (`NAVAll.txt`).
- **Observation Date**: ISO date of NAV observation.
- **Canonical Scheme ID**: Deterministic AMFI scheme identity (`CAN_AMFI_{code}`).
- **Calculation Method**: Rank-based midpoint percentile normalization (`PeerGroupNormalizer`).
- **Methodology Version**: Version string `1.0.0`.
- **UI Traceability**: Rendered in footers and detailed data tabs across SCR-02, SCR-05, SCR-06, SCR-08, and SCR-09.

---

## 14. Security and Privacy Audit

**Audit Classification: SECURITY — 🟡 Provisional / constrained for local development; 🟠 Deployment gate for cloud production**

- **PII & Onboarding Data**: Investor profile snapshots and onboarding questionnaire answers contain financial parameters (income tier, net worth, emergency months). In the current local execution environment, data resides in local SQLite database files (`db/backfill_f12_2.db`).
- **Zero External Data Leakage**: The application makes zero outbound network calls to non-AMFI third parties. All evaluations run 100% locally.
- **Classification by Deployment Scope**:
  - **🟡 Provisional / constrained**: Accepted for local/internal V1 development.
  - **🟠 Deployment gate**: Required for internet/cloud production deployment (enforcing authentication middleware, session tokens, and access control).
- **Scope Note**: Missing authentication is an application infrastructure / deployment gate item and is NOT a defect in the core financial decision engine.

---

## 15. Testing Suite Audit

The repository contains **1,492 automated tests** across 5 test directories. All test suites were executed to verify system health:

| Test Directory | Purpose & Coverage | Test Count | Status |
| :--- | :--- | :--- | :--- |
| **`tests/data_quality/`** | Ingestion, NAV normalizers, AMFI live feeds, F.19 gates, scheme mappings | ~520 tests | 🟢 100% PASSED |
| **`tests/financial/`** | Scoring engine, risk engines, suitability, portfolio need, action, orchestrator | ~840 tests | 🟢 100% PASSED |
| **`tests/integration/`** | End-to-end pipelines, repositories, release gate audits | ~80 tests | 🟢 100% PASSED |
| **`tests/scoring/`** | Zero-return defect remediation, percentile rank math | ~35 tests | 🟢 100% PASSED |
| **`tests/ui/`** | UI contract safety, score-action decoupling assertions | ~17 tests | 🟢 100% PASSED |
| **TOTAL SUITE** | **Complete Codebase Verification** | **1,492 tests** | **🟢 100% PASSED** |

---

## 16. Documentation Consistency Audit

**Audit Classification: DOCUMENTATION — 🟠 Reconciled in this audit**

Cross-checking documentation against codebase implementation revealed complete consistency across core specifications, with audit status summary blocks reconciled in this document to eliminate previous contradictions between audit findings and baseline summary blocks:

| Specification Document | Codebase Implementation | Consistency Status | Audit Notes |
| :--- | :--- | :--- | :--- |
| [`INTENDED_PRODUCT_SPECIFICATION.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/INTENDED_PRODUCT_SPECIFICATION.md) | `scoring/`, `risk/`, `portfolio/`, `action/` | 🟢 CONSISTENT | All 8 mandatory V1 requirements implemented |
| [`IMPLEMENTATION_CODEBASE_MAP.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/IMPLEMENTATION_CODEBASE_MAP.md) | All domain modules & test suites | 🟢 CONSISTENT | Discrepancies (DISC-001..003) properly framed |
| [`GOVERNED_UI_ARCHITECTURE_AND_SCREEN_SPECIFICATION_V1.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/GOVERNED_UI_ARCHITECTURE_AND_SCREEN_SPECIFICATION_V1.md) | `web/app.py`, `web/adapters.py` | 🟢 CONSISTENT | 10 V1 screens & presentation adapters aligned |
| [`IDENTITY_PIT_PEER_SCORE_FORENSIC_RECONCILIATION_REPORT.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/IDENTITY_PIT_PEER_SCORE_FORENSIC_RECONCILIATION_REPORT.md) | `db/backfill_f12_2.db`, `scoring/engine.py` | 🟢 CONSISTENT | 105-peer population & SHA256 verified |
| [`V1_RELEASE_CANDIDATE_READINESS_AUDIT.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/V1_RELEASE_CANDIDATE_READINESS_AUDIT.md) | Entire Repository Audit Baseline | 🟠 RECONCILED | Summary status blocks reconciled to match audit findings |

---

## 17. V1 Release Gate (14 Release Dimensions)

| Dimension # | Release Dimension | Status | Empirical Evidence | Blocking Issue |
| :--- | :--- | :--- | :--- | :--- |
| **A** | **Financial Calculation Integrity** | **GREEN** | 100% pass across financial test suite | NONE |
| **B** | **Data Integrity** | **GREEN** | 13.4M raw NAVs, 17,507 canonical schemes | NONE |
| **C** | **Identity Integrity** | **GREEN** | AMFI scheme code & ISIN mapping verified | NONE |
| **D** | **PIT Integrity** | **GREEN** | Point-in-time SEBI 2017+ category resolution | NONE |
| **E** | **Decision Safety** | **GREEN** | Score alone never triggers BUY/SELL | NONE |
| **F** | **User-Control Integrity** | **GREEN** | System Rec $\neq$ User Decision $\neq$ Execution | NONE |
| **G** | **Explainability** | **GREEN** | 7-layer decision explanation payloads generated | NONE |
| **H** | **Provenance** | **GREEN** | Source ID, retrieval timestamp, ISO date traced | NONE |
| **I** | **Portfolio Safety** | **GREEN** | Asset allocation gaps & subcategory caps active | NONE |
| **J** | **Tax / Cost Safety** | **GREEN** | STCG/LTCG tax & exit load hurdles evaluated | NONE |
| **K** | **UI / Backend Contract** | **GREEN** | 10 V1 web screens served via `web/app.py` | NONE |
| **L** | **Testing** | **GREEN** | 1,492 automated tests passing 100% | NONE |
| **M** | **Security / Privacy** | **AMBER** | Local execution safe; cloud auth gateway needed | Non-blocking for local; blocking for cloud |
| **N** | **Documentation** | **GREEN** | All specs, matrices, & reports updated | NONE |

---

## 18. Readiness Classification & Boundary Summary

To ensure absolute clarity, readiness is separated into three distinct boundaries:

1. **ENGINE READY (100% VERIFIED)**: All 7 backend domain engines (`scoring`, `risk`, `portfolio`, `economic_benefit`, `action`, `integration`, `audit`) are 100% code-complete, verified, and frozen.
2. **DATA READY (PROVISIONAL / CONSTRAINED)**: Infrastructure, schemas, and live AMFI NAV time-series are 100% authoritative. Pre-2021 TER, SEBI Riskometer depth, and minor custom benchmark indices are partially populated, but handled safely as `None`.
3. **PRODUCT READY (🟠 V1 GAPS REQUIRE IMPLEMENTATION)**: The financial decision core is sound and accepted, but the complete V1 product baseline still requires identified product/infrastructure implementation work (user profile persistence, portfolio CAS/CSV ingestion, and production authentication).

---

## 19. Recommended Next Implementation Sequence

The precise sequence of implementation tasks required to finalize V1 product release is ordered strictly by technical dependency:

### Step 1: User Profile & Session Persistence Layer
- **Why Needed**: Questionnaire responses currently instantiate in-memory `InvestorProfileSnapshot` objects. Persistent storage is needed to save user profiles across browser sessions.
- **Requirement IDs**: `REQ-USR-001`, `SCR-01`, `SCR-10`.
- **Current Implementation**: `web/adapters.py` (`QuestionnaireAdapter`).
- **Gap**: SQLite / JSON profile storage table.
- **Files Affected**: `data/repositories/profile_repository.py`, `web/app.py`.
- **Dependencies**: None.
- **Acceptance Criteria**: Questionnaire responses save to `investor_profiles` table; reloading `/settings` retrieves saved profile.
- **Tests Required**: `test_profile_persistence_save_and_load()`.
- **Data Requirements**: User ID, profile JSON payload.
- **Risk**: Low.
- **Scope**: **V1 Essential**.

### Step 2: Portfolio Transaction & Holdings Ingestion Adapter
- **Why Needed**: Portfolio snapshots are currently loaded from structured JSON/API inputs. A CSV/CAS parser is needed for users to upload portfolio holdings.
- **Requirement IDs**: `REQ-PORT-001`, `SCR-03`.
- **Current Implementation**: `models/portfolio.py` (`PortfolioSnapshot`).
- **Gap**: User CSV/CAS upload parser translating rows to `PortfolioHolding` list.
- **Files Affected**: `data/adapters/portfolio_upload_adapter.py`, `web/app.py`.
- **Dependencies**: Step 1.
- **Acceptance Criteria**: Uploading a portfolio CSV parses holdings, maps AMFI scheme codes, and renders `/wealth`.
- **Tests Required**: `test_portfolio_upload_adapter_parses_valid_csv()`.
- **Data Requirements**: User portfolio CSV (Scheme Code / ISIN, Units, Purchase Value).
- **Risk**: Low.
- **Scope**: **V1 Essential**.

### Step 3: Production Authentication & Security Gateway
- **Why Needed**: Required for multi-user cloud deployment to protect user profile and portfolio data.
- **Requirement IDs**: Release Gate Dimension M.
- **Current Implementation**: Local HTTP server in `web/app.py`.
- **Gap**: Session authentication middleware (e.g. cookie session / JWT).
- **Files Affected**: `web/auth.py`, `web/app.py`.
- **Dependencies**: Step 1.
- **Acceptance Criteria**: Unauthenticated requests to `/wealth` or `/action-center` redirect to `/login`.
- **Tests Required**: `test_auth_middleware_blocks_unauthenticated_access()`.
- **Data Requirements**: User credentials store.
- **Risk**: Low.
- **Scope**: **V1 Cloud Deployment Gate**.

---

## 20. Final Classification Table

| Component / Subsystem | Classification | Notes |
| :--- | :--- | :--- |
| **Financial Engines** | 🟢 Sound / accepted | All 7 domain engines frozen, verified, and 100% operational. |
| **Data Infrastructure** | 🟢 Sound / accepted | `db/backfill_f12_2.db` indexed with 17,507 schemes & 13.4M NAVs. |
| **Data Completeness** | 🟡 Provisional / constrained | Live NAVs 100%; pre-2021 TER/Riskometer partial (handled as `None`). |
| **Decision Chain Integration** | 🟢 Sound / accepted | 7-layer precedence verified in `DecisionOrchestrator`. |
| **User Onboarding / Profile** | 🟠 Material V1 implementation gap | Questionnaire flow implemented; persistent multi-session profile storage missing. |
| **Portfolio Ingestion** | 🟠 Material V1 implementation gap | Decision engine & snapshot contract implemented; CAS/CSV user ingestion missing. |
| **Goals** | 🟢 Sound / accepted | Goal targets & progress active, subject to portfolio-ingestion dependency. |
| **Action Center & UI** | 🟢 Sound / accepted | 10 core V1 web screens implemented in `web/app.py`. |
| **Provenance & Audit** | 🟢 Sound / accepted | AMFI source URLs, timestamps, & immutable logs verified. |
| **Security** | 🟡 Provisional / constrained locally; 🟠 deployment gate for cloud production | Local execution safe; authentication gateway required for cloud deployment. |
| **Testing Suite** | 🟢 Sound / accepted | 1,492 automated tests passing 100% for executed test scope. |
| **Documentation** | 🟠 Reconciled in this audit | Reconciled audit status blocks to eliminate contradictions with audit findings. |

---

## 21. Final Status Summary

```
FINAL STATUS:
[🟠 V1 GAPS REQUIRE IMPLEMENTATION]

FINANCIAL ENGINE: 🟢 Sound / accepted
DATA:             🟡 Provisional / constrained
DECISION CHAIN:   🟢 Sound / accepted
ONBOARDING:       🟠 Profile persistence gap
PORTFOLIO:        🟠 User portfolio ingestion gap
GOALS:            🟢 Sound / accepted, subject to portfolio-ingestion dependency
ACTION CENTER:    🟢 Sound / accepted
PROVENANCE:       🟢 Sound / accepted
SECURITY:         🟡 Provisional / constrained locally; 🟠 deployment gate for cloud production
TESTING:          🟢 Sound / accepted for executed test scope
DOCUMENTATION:    🟠 Reconciled in this audit

FINANCIAL LOGIC CHANGED: NO
IMPLEMENTATION CHANGES: NONE
REPORT: docs/V1_RELEASE_CANDIDATE_READINESS_AUDIT.md
```
