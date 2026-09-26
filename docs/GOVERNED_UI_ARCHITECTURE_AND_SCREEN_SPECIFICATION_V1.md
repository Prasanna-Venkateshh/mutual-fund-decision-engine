# GOVERNED UI ARCHITECTURE & SCREEN SPECIFICATION
## Mutual Fund Decision-Support Platform (Version 1.0 — Governance Corrected)

**Document Title:** Governed UI Architecture & Screen Specification (V1)  
**Document Status:** GOVERNANCE CORRECTED & VERIFIED  
**Governance Standard:** Absolute Decoupling of Financial Logic, Evidence-Grounded Mapping, Strict 7-Layer Precedence  
**Audit Date:** September 2026 UTC  

---

## 1. EXECUTIVE SUMMARY & REPOSITORY VERIFICATION

This document establishes the corrected **Governed UI Architecture & Screen Specification** for the V1 Mutual Fund Decision-Support Platform. 

Following an independent governance review, this specification applies 10 narrow corrections to align all presentation logic strictly with the authoritative repository implementation (`scoring/`, `risk/`, `portfolio/`, `action/`, `integration/`, `audit/`).

### Strict Financial Governance Invariants Preserved
1. **Zero Financial Methodology Changes:** Scoring weights, normalization formulas, suitability gating, risk alignment, portfolio need evaluation, tax friction math, and orchestrator precedence remain 100% frozen.
2. **Zero Code / Schema / API Mutations:** No Python code, database schemas, integration contracts, or backend APIs have been modified.
3. **Zero Synthetic Production Defaults:** Missing metrics (`None`) are never rendered as numerical zeros ($0.0$). Unpopulated metadata fields default to `"Data Not Available"`.
4. **Absolute Decoupling of Action & UI:** System Recommendation $\neq$ User Decision $\neq$ Execution Status. High Fund Quality alone NEVER triggers `BUY`, and low Fund Quality alone NEVER triggers `SELL`.

---

## 2. GOVERNANCE CORRECTIONS SUMMARY

| Correction Area | Original Specification Pattern | Corrected Specification Rule | Repository Grounding & Rationale |
|---|---|---|---|
| **1. Confidence / Evidence Strength** | Hard-coded thresholds ($\ge 0.85 = \text{Strong}, 0.60\text{--}0.84 = \text{Moderate}, < 0.60 = \text{Limited}$). | Removed hard-coded thresholds. UI treats `confidence_score` as a continuous $[0.0, 1.0]$ numerical backend field. Qualitative labels (`"Evidence Strength"`) are presentation-layer options requiring explicit product governance. | `scoring/models.py` (`confidence_score: float`). No qualitative threshold enum exists in backend code. |
| **2. Tax Presentation & Authority** | Attributed tax rules to SEBI and hard-coded rates ($20\%$ STCG, $12.5\%$ LTCG, ₹1.25L exemption) as universal UI rules. | Tax amounts and rules are displayed ONLY when supplied by the governed economic benefit contract (`EconomicBenefitIntegrationContract`). Displayed rates are labelled as transaction assumptions, not universal UI defaults. | `phase_f5_economic_benefit_specification.md` & `integration/models.py`. Tax rules originate from tax legislation, not SEBI regulations. |
| **3. Illustrative Values** | Wireframes used concrete-looking scheme names (`ABSL Frontline Equity Fund`), AMFI codes (`100044`), and exact scores. | Explicitly labelled all wireframe examples as `ILLUSTRATIVE / NON-PRODUCTION EXAMPLE` to prevent implementation agents from treating them as production defaults. | `scoring/models.py` & test fixtures. Real schemes vary dynamically by point-in-time observation date. |
| **4. Predictive Return Implication** | Switch evaluator used *"Expected Quality & Return Improvement"*. | Replaced with `"Evaluated Decision Benefit"` / `"Potential Economic Improvement"`. Strictly prohibited any language implying return forecasts or guaranteed outperformance. | `phase_f5_economic_benefit_specification.md` §6. `EXPECTED_IMPROVEMENT` is unvalidated; system evaluates economic friction and hurdle math. |
| **5. ActionState vs Notification Priority** | Alert adapter mapped `PASSIVE = HOLD`, `ATTENTION = MONITOR/REVIEW`, `CONSEQUENTIAL = BUY/SELL`. | Decoupled `ActionState` from notification urgency. The UI does not treat action recommendations as automatic notification push triggers. | `action/models.py`. `ActionState` represents financial recommendation state, not delivery channel priority. |
| **6. "What Changed?" Materiality** | Inferred that numerical deltas represent "material changes". | Specified that `SnapshotDiffAdapter` compares raw $v_1$ vs $v_2$ fields. Materiality classification requires a separately governed policy; UI displays raw before/after deltas without claiming consequential materiality. | `audit/` & `integration/orchestrator.py`. Reassessment computes new versioned payloads without auto-inferring user materiality. |
| **7. Qualified Readiness Claims** | Stated "All 10 Core V1 Screens are fully supported by existing backend contracts." | Corrected to: "All 10 Core V1 screens have identified backend contracts sufficient for implementation planning, with specified presentation adapters where required." | `IMPLEMENTATION_CODEBASE_MAP.md`. Presentation adapters (e.g. questionnaire mapping) are required. |
| **8. Governed Freshness Thresholds** | Hard-coded 180-day data freshness cutoff badges. | Explicitly stated that freshness thresholds are governed by backend data-source policies and are not defined or invented by the UI layer. | `phase_f7_3_1_governance_correction.md`. Arbitrary 180-day freshness thresholds were explicitly removed from backend code in F.7.3.1. |
| **9. Fund Quality / Action Safety Tests** | Lacked explicit UI contract safety assertions prohibiting score-driven actions. | Added mandatory UI contract tests: High Fund Quality MUST NOT trigger `BUY` badge unless backend `final_action_state == BUY`; Low Quality MUST NOT trigger `SELL` badge unless `final_action_state == SELL`. | `tests/financial/test_adversarial_financial_safety.py` (Adversarial Tests A & B). |
| **10. Explainability Presentation Order** | Displayed explainability layers in technical processing sequence. | Restructured user-facing presentation sequence: 1. Recommendation, 2. Why, 3. Decision Chain, 4. Evidence Strength, 5. Data Provenance & Methodology. (Backend execution sequence remains unchanged). | `integration/orchestrator.py`. Presentation sequence enhances usability without altering backend processing logic. |

---

## 3. GLOBAL INFORMATION ARCHITECTURE

The platform navigation separates analytical concerns to prevent confusing intrinsic quality with investor suitability or transaction placement:

```
+---------------------------------------------------------------------------------------------------------+
|                                        GLOBAL NAVIGATION BAR                                            |
+-------------------++-------------------++-------------------++-------------------++--------------------+
|  1. HOME          ||  2. MY WEALTH     ||  3. DISCOVER      ||  4. ACTION CENTER ||  5. PROFILE &      |
|  (Quiet Dashboard)||  (Holdings &      ||  (Peer Scanner &  ||  (Recommendations ||     SETTINGS          |
|                   ||   Goal Fit)       ||   Comparisons)    ||   & User Control) ||                    |
+-------------------++-------------------++-------------------++-------------------++--------------------+
```

### Navigation & Hierarchy Principles
- **Discover Area:** Answers *"What schemes exist within governed peer categories?"*
- **My Wealth Area:** Answers *"What do I own and how does it align with my goals and risk alignment?"*
- **Action Center:** Answers *"What consequential recommendations has the system emitted, and what is my decision?"*

---

## 4. SCREEN INVENTORY & QUALIFIED READINESS MATRIX

| Screen ID | Screen Name | Route Path | Primary User Question | Readiness Classification | Presentation Adapter Needed? |
|---|---|---|---|---|---|
| **SCR-01** | Onboarding & Profiling | `/onboarding` | *"What is my financial risk capacity and tolerance?"* | 🟡 READY WITH UI ADAPTER | **YES** (Questionnaire flow adapter) |
| **SCR-02** | Home (Quiet Dashboard) | `/` | *"Does anything in my portfolio require attention today?"* | 🟢 READY FOR IMPLEMENTATION PLANNING | **NO** |
| **SCR-03** | Portfolio / My Wealth | `/wealth` | *"What do I own and how is it allocated?"* | 🟢 READY FOR IMPLEMENTATION PLANNING | **NO** |
| **SCR-04** | Goal Detail | `/wealth/goals/:id` | *"Is my specific life goal on track with current assets?"* | 🟢 READY FOR IMPLEMENTATION PLANNING | **NO** |
| **SCR-05** | Fund Discovery & Scanner | `/discover` | *"How do funds compare within their governed peer group?"* | 🟢 READY FOR IMPLEMENTATION PLANNING | **NO** |
| **SCR-06** | Fund Detail | `/scheme/:id` | *"What is the quality, suitability, evidence, and fit for this fund?"* | 🟡 READY WITH UI ADAPTER | **YES** (Confidence label presentation mapping) |
| **SCR-07** | Fund Comparison | `/discover/compare` | *"How do eligible schemes compare on metrics and fit?"* | 🟡 READY WITH UI ADAPTER | **YES** (Peer homogeneity enforcement filter) |
| **SCR-08** | Switch Evaluator | `/action/evaluate-switch` | *"Is switching from Fund A to B economically beneficial?"* | 🟢 READY FOR IMPLEMENTATION PLANNING | **NO** |
| **SCR-09** | Action Center | `/action-center` | *"What system recommendations require my decision?"* | 🟢 READY FOR IMPLEMENTATION PLANNING | **NO** |
| **SCR-10** | Profile & Settings | `/settings` | *"What profile assumptions and defaults are active?"* | 🟢 READY FOR IMPLEMENTATION PLANNING | **NO** |

---

## 5. SCREEN-BY-SCREEN SPECIFICATIONS

### SCR-02: HOME (QUIET DASHBOARD)

1. **Purpose:** Provides a calm, low-turnover overview of portfolio status without emphasizing daily market noise.
2. **Primary User Question:** *"Do I need to do anything right now?"*
3. **User Entry Points:** Default entry route (`/`).
4. **Primary Information Hierarchy:**
   - Top Banner: Overall Action Status (`"Nothing requires action right now"` vs Action Required).
   - Card 1: Consequential Recommendations Summary (`ActionState.BUY` / `SELL` / `REVIEW`).
   - Card 2: Goal On-Track Summary (`GoalFundingSnapshot`).
   - Card 3: What Changed (Snapshot delta between $v_1$ and $v_2$ raw fields).
   - Card 4: Monitoring Ledger (`ActionState.MONITOR` / `HOLD`).
5. **Primary Action:** `Review Recommendations` (navigates to `/action-center`) or `View Portfolio` (`/wealth`).
6. **Secondary Actions:** `Inspect Raw Deltas`, `View Goal Status`.
7. **Backend Source:** `DecisionOrchestrator.evaluate_portfolio()` (`integration/orchestrator.py`).
8. **Exact Backend Fields Consumed:**
   - `EndToEndDecisionResult.final_action_state` (`ActionState`)
   - `EndToEndDecisionResult.decision_explanation` (`DecisionExplanation`)
   - `EndToEndDecisionResult.observation_date` (`date`)
9. **UI Presentation Logic:** If `final_action_state == HOLD`, display green/neutral banner: `"Nothing requires action right now. Your portfolio continues to be monitored."` Prohibited copy: `"Portfolio fully optimized"`.
10. **Loading State:** Skeleton cards matching dashboard layout.
11. **Empty State:** Neutral onboarding prompt if zero holdings exist.
12. **Missing-Data State:** Render `"Data Not Available"` badge if observation date is missing.
13. **Insufficient-Evidence State:** Display `"Insufficient Evidence to Evaluate"` if `IntegrationStatus == INVALID` or `PARTIAL`.
14. **Error State:** Standard fallback error card with retry button.
15. **Stale-Data State:** Orange badge displaying `"Data Observation Date: [date]"`. Freshness thresholds are governed by backend policy, not defined by UI.
16. **User Interaction Behavior:** Clicking any recommendation card opens the Recommendation Detail Drawer.
17. **Navigation Behavior:** Preserves bottom/top global navigation bar.
18. **Provenance Display:** Footer showing `observation_date` and `orchestrator_version`.
19. **Explainability Behavior:** Expands natural-language summary from `decision_explanation.summary`.
20. **User-Control Implications:** Zero trade buttons; explicit disclaimer: *"Recommendations are for decision support only."*
21. **Accessibility Considerations:** Status communicated via text and distinct icons (`aria-live="polite"`).
22. **Mobile Behavior:** Single-column vertical scroll.
23. **Desktop Behavior:** Grid layout with Action Summary on left, Goals on right.
24. **Analytics/Event Logging:** `view_home_dashboard` event.
25. **Tests Required:** `test_home_dashboard_renders_hold_state()`, `test_home_dashboard_displays_observation_date()`.

---

### SCR-06: FUND DETAIL

1. **Purpose:** Displays 7-layer evaluation breakdown for a single mutual fund scheme.
2. **Primary User Question:** *"What is the quality, suitability, evidence strength, and portfolio fit for this fund?"*
3. **User Entry Points:** Link from Discover (`/discover`), Portfolio (`/wealth`), or Action Center (`/action-center`).
4. **Primary Information Hierarchy:**
   - Header: Scheme Name, AMFI Code, ISIN, Plan/Option, Category (`category::subcategory::plan_type`).
   - Section 1: System Recommendation & Rationale (`final_action_state`).
   - Section 2: Fund Quality Score ($0.0 - 100.0$) & Peer Context.
   - Section 3: Evidence Strength (UI label for `confidence_score` $0.0 - 1.0$) + Reasons.
   - Section 4: Investor Suitability (`SuitabilityStatus`).
   - Section 5: Portfolio Need & Exposure Cap (`PortfolioNeedState`).
   - Section 6: Economic Benefit / Hurdle Math (if switch evaluated).
   - Section 7: Raw Metrics & Provenance Table.
5. **Primary Action:** `Check Portfolio Fit` / `Record Decision`.
6. **Secondary Actions:** `View Raw Data & Provenance`, `Compare with Peer`.
7. **Backend Source:** `FundQualityScorer.calculate_score()` (`scoring/engine.py`) and `DecisionOrchestrator`.
8. **Exact Backend Fields Consumed:**
   - `FundQualityScoreResult.quality_score` (`Optional[float]`)
   - `FundQualityScoreResult.confidence_score` (`float`)
   - `FundQualityScoreResult.dimension_scores` (`Dict[str, DimensionScore]`)
   - `SuitabilityAssessmentResult.status` (`SuitabilityStatus`)
   - `PortfolioNeedAssessmentResult.primary_state` (`PortfolioNeedState`)
9. **UI Presentation Logic:**
   - `quality_score` displayed as numeric score out of 100.
   - `confidence_score` displayed as continuous numerical backend value $[0.0, 1.0]$. Qualitative label mapping (e.g. `"Evidence Strength: Strong"`) is a presentation label requiring product governance approval; hard-coded UI thresholds are removed.
   - Dimension scores ($0.0 - 100.0$) displayed in radar or horizontal bar breakdown.
10. **Loading State:** Full-page shimmer placeholder.
11. **Empty State:** N/A (Scheme ID required).
12. **Missing-Data State:** If a dimension score is `None`, render `"Data Not Available"` and re-scale remaining active weights visually. Never display $0.0$ for missing data (`REQ-FQ-003`).
13. **Insufficient-Evidence State:** If `quality_score is None` due to $< 1$ year history or active weight $< 40\%$, display banner: `"Insufficient Historical Track Record to Generate Quality Score"`.
14. **Error State:** "Scheme Not Found" card with search redirect.
15. **Stale-Data State:** Stale badge showing calculation timestamp UTC.
16. **User Interaction Behavior:** Hovering over dimension score reveals peer percentile and raw metric value.
17. **Navigation Behavior:** Deep link supported via `/scheme/:canonical_scheme_id`.
18. **Provenance Display:** Footer displaying AMFI source URL, retrieval timestamp, and methodology version `1.0.0`.
19. **Explainability Behavior:** Expandable accordion for 7-layer decision explanation.
20. **User-Control Implications:** Read-only analysis; no inline buying.
21. **Accessibility Considerations:** High-contrast text, keyboard-navigable accordions (`aria-expanded`).
22. **Mobile Behavior:** Single-column layout with sticky bottom summary bar.
23. **Desktop Behavior:** Two-column layout.
24. **Analytics/Event Logging:** `view_fund_detail`.
25. **Tests Required:** `test_fund_detail_handles_none_quality_score()`, `test_high_fq_score_does_not_render_buy_badge_without_backend_buy()`.

---

### SCR-08: SWITCH & ECONOMIC HURDLE EVALUATOR

1. **Purpose:** Evaluates single-trade switching recommendations against exit loads and capital gains tax hurdles.
2. **Primary User Question:** *"Will switching from Scheme A to Scheme B yield an evaluated economic benefit after tax and loads?"*
3. **User Entry Points:** Action Center (`/action-center`) when evaluating a `SELL` or `REVIEW` state.
4. **Primary Information Hierarchy:**
   - Section 1: Current Holding (Scheme A) vs Proposed Replacement (Scheme B).
   - Section 2: Evaluated Decision Benefit (Evaluated quality & friction differential; strictly prohibited from claiming return forecasts).
   - Section 3: Switching Friction Breakdown (Exit Load ₹, STCG Tax ₹, LTCG Tax ₹ as supplied by backend contract).
   - Section 4: Net Economic Benefit Result (`EconomicBenefitState`).
   - Section 5: System Recommendation (`ActionState.SELL` vs `ActionState.REVIEW` / `HOLD`).
5. **Primary Action:** `Record Decision` (`ACCEPT` / `REJECT`).
6. **Secondary Actions:** `Adjust Investment Amount`, `View Tax Assumptions`.
7. **Backend Source:** `EconomicBenefitIntegrationContract` (`integration/models.py`).
8. **Exact Backend Fields Consumed:**
   - `EconomicBenefitIntegrationContract.economic_benefit_state` (`EconomicBenefitState`)
   - `EconomicBenefitIntegrationContract.net_benefit_amount` (`Optional[float]`)
   - `EconomicBenefitIntegrationContract.stcg_tax_amount` (`Optional[float]`)
   - `EconomicBenefitIntegrationContract.ltcg_tax_amount` (`Optional[float]`)
   - `EconomicBenefitIntegrationContract.exit_load_amount` (`Optional[float]`)
9. **UI Presentation Logic:**
   - Display: Gross Differential $\longrightarrow$ Friction Deductions $\longrightarrow$ Net Benefit.
   - If `economic_benefit_state == BENEFIT_UNCERTAIN` or `ECONOMICALLY_NOT_BENEFICIAL`, system blocks `SELL` recommendation and gates to `REVIEW` or `HOLD`.
   - Tax rates are displayed ONLY when supplied by backend contract and labelled as `"Evaluated Transaction Tax Assumptions"`. Universal hard-coded UI tax rates are removed.
10. **Loading State:** Calculating hurdle spinner.
11. **Empty State:** N/A.
12. **Missing-Data State:** If tax/exit load data is missing, display: `"Tax/Exit Load Metadata Missing — System Cannot Confirm Economic Benefit"`.
13. **Insufficient-Evidence State:** Block switch recommendation; force `NO_ACTION`.
14. **Error State:** Calculation error notification.
15. **Stale-Data State:** Timestamp of cost schedule displayed.
16. **User Interaction Behavior:** Toggle switch between Full Redemption and Partial Redemption.
17. **Navigation Behavior:** Opened as a modal dialog over Action Center.
18. **Provenance Display:** Provenance attached to evaluated transaction tax assumptions.
19. **Explainability Behavior:** Step-by-step net math breakdown.
20. **User-Control Implications:** User may reject the switch; portfolio state remains 100% untouched.
21. **Accessibility Considerations:** Clear tabular layout for monetary amounts.
22. **Mobile Behavior:** Full-screen modal with fixed bottom button bar.
23. **Desktop Behavior:** Centered modal window ($800\text{px}$ width).
24. **Analytics/Event Logging:** `evaluate_switch_viewed`.
25. **Tests Required:** `test_switch_evaluator_displays_tax_breakdown()`, `test_switch_evaluator_handles_missing_cost_metadata()`.

---

## 6. EXPLAINABILITY PRESENTATION MODEL

The UI presents the 7-layer explainability payload in a user-friendly hierarchy. This is a **presentation sequence only** and does NOT alter backend execution or calculation order:

```
[ USER-FACING PRESENTATION SEQUENCE ]
  1. RECOMMENDATION ("What does the system recommend?")
  2. WHY ("What caused this recommendation?")
  3. DECISION CHAIN SUMMARY:
     ├── Fund Quality (Category-relative peer rank)
     ├── Investor Suitability (Risk alignment & constraints)
     ├── Portfolio Need (Exposure gap & goal fit)
     └── Economic Benefit (Net improvement vs tax/cost hurdles)
  4. EVIDENCE STRENGTH (Backend confidence_score & data completeness)
  5. DATA PROVENANCE & METHODOLOGY (AMFI URLs, timestamps, & versions)
```

---

## 7. MANDATORY UI CONTRACT SAFETY TESTS

The following explicit UI contract tests are required to ensure the presentation layer never bypasses backend financial rules:

1. **High Fund Quality Action Safety Test:**
   - *Invariant:* A high Fund Quality score ($> 90.0$) MUST NOT cause the UI to display a `BUY` badge unless `EndToEndDecisionResult.final_action_state == ActionState.BUY`.
2. **Low Fund Quality Action Safety Test:**
   - *Invariant:* A low Fund Quality score ($< 20.0$) MUST NOT cause the UI to display a `SELL` badge unless `EndToEndDecisionResult.final_action_state == ActionState.SELL`.
3. **Zero vs None Distinction Test:**
   - *Invariant:* A missing return metric (`None`) MUST render as `"Data Not Available"` and MUST NOT render as `0.0%` or trigger a zero penalty.
4. **User Rejection Immutability Test:**
   - *Invariant:* Recording `UserDecisionRecord(REJECT)` MUST leave `PortfolioSnapshot` 100% unchanged.

---

## 8. STRUCTURED TEXT WIREFRAME (ILLUSTRATIVE EXAMPLE)

> [!NOTE]
> **ILLUSTRATIVE / NON-PRODUCTION EXAMPLE:** The scheme names, codes, metrics, and dates below are strictly illustrative placeholders for UI layout review. They do NOT represent production defaults or actual scheme data.

```
===================================================================================
SCREEN: SCR-06 — FUND DETAIL (ILLUSTRATIVE / NON-PRODUCTION EXAMPLE)
===================================================================================

[ GLOBAL NAVIGATION BAR ]
Home | My Wealth | Discover | Action Center | Profile & Settings

[ HEADER ]
Fund Name: [Illustrative Scheme Name Placeholder]
Scheme Code: [AMFI Code Placeholder] | ISIN: [ISIN Placeholder]
Category: Equity :: Large Cap :: Direct :: Growth
System Status: [ MONITOR ] -------------------------------- (DecisionStateBadge)

[ SECTION 1: PRIMARY DECISION SUMMARY ]
Rationale: "Relative fund quality has weakened slightly, but current evidence does not establish a need to switch."
Primary Action: [ Check Portfolio Fit ]   Secondary: [ Compare with Peer ]

[ SECTION 2: FUND QUALITY ]
Quality Score: [Score Placeholder e.g. 72.4] / 100 -------- (FundQualityCard)
Peer Group: Equity :: Large Cap (N = [Peer Count] schemes)
Dimensions Breakdown:
  - Return (25%): [Score] [==========        ]
  - Consistency (20%): [Score] [========          ]
  - Volatility (15%): [Score] [=========         ]
  - Downside Risk (15%): [Score] [=========         ]
  - Max Drawdown (15%): [Score] [==========        ]
  - Cost Efficiency (10%): [Score] [========          ]

[ SECTION 3: EVIDENCE STRENGTH ]
Confidence Score: 0.95 (Backend Numerical Field) ----------- (EvidenceStrengthIndicator)
UI Label: Evidence Strength: Strong (Subject to Product Governance Approval)
Supporting Factors:
  [✓] 10+ Years History Available   [✓] 6/6 Scoring Dimensions Active
  [✓] Authoritative AMFI Feed       [✓] Canonical Scheme ID Verified

[ SECTION 4: INVESTOR SUITABILITY ]
Fit Status: SUITABLE --------------------------------------- (SuitabilityStatusCard)
Risk Alignment: Aligned Risk Tier = MEDIUM (Capacity: HIGH, Tolerance: MEDIUM)

[ SECTION 5: PORTFOLIO NEED ]
Need Status: NO MATERIAL NEED IDENTIFIED -------------------- (PortfolioNeedCard)

[ SECTION 6: ECONOMIC BENEFIT ]
Status: NO EVALUABLE CHANGE (Switching not evaluated)

[ SECTION 7: PROVENANCE & METHODOLOGY ] ------------------- (ProvenanceFooter)
Source: AMFI Official Portal | Retrieved: [Timestamp Placeholder]
Methodology Version: 1.0.0 | Weight Config: 1.0.0
===================================================================================
```

---

## 9. COPY GOVERNANCE

| State / Term | Approved UI Copy Template | Prohibited Copy |
|---|---|---|
| **`HOLD`** | *"Nothing requires action right now. Your portfolio continues to be monitored."* | *"Portfolio fully optimized"* / *"Top performer"* |
| **`MONITOR`** | *"A change has been detected, but current evidence does not justify action."* | *"Warning: Underperforming fund"* |
| **`REVIEW`** | *"Current evidence warrants a closer review of this holding."* | *"Sell immediately"* |
| **`BUY`** | *"This fund meets suitability constraints and satisfies an identified portfolio gap."* | *"Guaranteed returns"* / *"Best fund in category"* |
| **`SELL`** | *"Switching is evaluated as economically beneficial after accounting for exit loads and capital gains tax."* | *"Dump this loser"* / *"Superior future return forecast"* |
| **`None` Data** | *"Data Not Available — Historical observation unpopulated."* | `0.0%` / `"Zero return"` |
| **Confidence** | `"Confidence Score: [Value] (UI Presentation Label: Evidence Strength)"` | `"95% Probability of Profit"` / `"Probability of correctness"` |
| **Tax Rates** | `"Evaluated Transaction Tax Assumptions (Sourced from Economic Benefit Contract)"` | `"SEBI Mandated 20% Tax Rate"` |
