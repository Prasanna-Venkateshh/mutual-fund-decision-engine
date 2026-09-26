# Mutual Fund Decision Engine — Feature Catalog

**Project:** `mutual-fund-decision-engine`  
**Version:** 1.0 (Investor & Product Perspective)  
**Related Documents:** [`PRODUCT_SPEC.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/PRODUCT_SPEC.md), [`ARCHITECTURE.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/ARCHITECTURE.md), [`DECISION_RULES.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/DECISION_RULES.md)

---

## Overview

This catalog defines the investor-facing features of the platform. Every feature is designed from the perspective of an Indian mutual fund investor, focusing on decision quality, evidence transparency, suitability, and long-term financial outcomes rather than transactional frequency.

---

## 1. Investor Profile & Onboarding

### 1.1 Core 10-Question Profile Onboarding
* **Investor Problem:** Onboarding forms are often tedious, overwhelming, or ask irrelevant questions without explaining why the data matters.
* **Investor-Facing Outcome:** A structured 10-question questionnaire that establishes the investor's baseline goals, risk capacity, and preferences using an encouraging reverse countdown (`10 → 9 → ... → 1`).
* **Journey Phase:** Initial Onboarding (`Build Profile`).
* **Inputs Required:** Goals, target horizon, risk tolerance, risk capacity, emergency reserve status, existing SIPs, comfortable investment capacity, constraints.
* **Platform Evaluation:** Separates risk tolerance (emotional willingness) from risk capacity (financial ability), setting recommended risk to the lower of the two.
* **Investor-Facing Output:** Personal Investor Profile summary with a visual risk constraints summary.
* **Next Steps:** Proceed to Goal Setup or Portfolio Review.
* **Explainability:** Each question offers an optional *"Why are we asking?"* explanation detailing how the answer affects future suitability.
* **Acceptance Criteria:**
  - Shows reverse countdown timer from 10 down to 1.
  - Questions can be skipped; skipping gracefully degrades confidence without blocking onboarding.
* **Edge Cases:** Extreme risk tolerance paired with zero risk capacity (constrained to low risk capacity).
* **What Platform Must NOT Do:** Must NOT force an investor to complete skipped non-mandatory fields.

### 1.2 Profile Change & Impact Preview
* **Investor Problem:** Changing personal circumstances (e.g., job change, new dependent) alter risk profile, but conventional platforms silently alter plans or ignore the change.
* **Investor-Facing Outcome:** An interactive impact preview showing how profile updates affect current goals and portfolio suitability before changes are saved.
* **Journey Phase:** Profile Maintenance (`Optimize`).
* **Inputs Required:** Updated profile parameters (income, risk capacity, timeline).
* **Platform Evaluation:** Re-evaluates goal progress, portfolio suitability, and asset allocation against updated profile rules.
* **Investor-Facing Output:** Visual **Impact Assessment** (`Profile Change → Impact Preview → User Review → Apply`).
* **Next Steps:** Investor reviews impact and clicks "Apply Changes" or cancels.
* **What Platform Must NOT Do:** Must NOT silently modify investor portfolio or investment plans without explicit confirmation.

---

## 2. Goal Planning & Progress Monitoring

### 2.1 Multi-Goal Tracking & Hybrid Status Assessment
* **Investor Problem:** Investors struggle to answer "Am I on track to meet my goal?" due to market volatility and uncertain future contributions.
* **Investor-Facing Outcome:** Real-time goal tracking with hybrid progress evaluation combining current savings, future SIPs, remaining horizon, and reasonable return expectations.
* **Journey Phase:** Ongoing Monitoring (`Monitor`).
* **Inputs Required:** Goal target amount, target date, priority, current linked fund values, ongoing SIP contributions.
* **Platform Evaluation:** Calculates required vs projected final value under realistic return ranges.
* **Statuses:**
  - **On Track:** Projected value meets target within comfortable confidence.
  - **Needs Attention:** Minor funding gap or horizon risk identified.
  - **At Risk:** Significant gap requiring timeline, target, or contribution adjustment.
* **Next Steps:** View trade-off options if status is *Needs Attention* or *At Risk*.
* **Explainability:** Provides comparative *"What changed?"* status delta explanations (e.g., *"Status changed from On Track to Needs Attention because portfolio return fell 1.2% below projection and SIP gap widened"*).
* **What Platform Must NOT Do:** Must NOT manufacture false precision by promising exact future rupee amounts.

### 2.2 Goal Gap & Affordability Trade-Off Engine
* **Investor Problem:** When a goal is behind schedule, investors do not know whether to increase monthly SIPs, extend their deadline, or lower their target.
* **Investor-Facing Outcome:** Quantified trade-off scenarios when an investor cannot afford the mathematically required SIP amount.
* **Journey Phase:** Goal Optimization (`Optimize`).
* **Inputs Required:** Comfortable monthly contribution capacity.
* **Platform Evaluation:** Evaluates 4 trade-off levers:
  1. Increase monthly SIP.
  2. Extend target horizon date.
  3. Reduce target goal amount.
  4. Combination of timeline and contribution adjustments.
* **Investor-Facing Output:** Comparative side-by-side table showing the exact impact of each trade-off choice.
* **Next Steps:** Select preferred trade-off and apply to investment plan.
* **What Platform Must NOT Do:** Must NOT force an optimal SIP amount that exceeds comfortable affordability.

---

## 3. Category-Aware Fund Evaluation & Scoring

### 3.1 Composite Multi-Factor Category Fund Scoring
* **Investor Problem:** Standard fund rating portals rank funds purely on short-term past returns or compare equity funds against debt funds.
* **Investor-Facing Outcome:** Category-aware fund evaluation comparing funds strictly within their peer group (e.g., Large Cap vs Large Cap, Banking & PSU Debt vs Banking & PSU Debt).
* **Journey Phase:** Fund Selection & Review (`Analyze / Recommend`).
* **Inputs Required:** Historical NAV time-series, AMC fund metadata.
* **Platform Evaluation:** Evaluates multi-factor dimensions:
  - Returns & Consistency
  - Downside Risk & Max Drawdown
  - Volatility & Risk-adjusted Behavior
  - Expense Ratio (TER) & Cost Structure
* **Investor-Facing Output:** Composite **Fund Quality Score** (0–100) paired with an explicit **Evidence Confidence Level**.
* **Explainability:** Displays exact metric breakdown, calculation methodology, and source references.
* **What Platform Must NOT Do:** Must NOT rank funds across fundamentally different asset classes against each other.

### 3.2 Fund History & New-Fund Framework
* **Investor Problem:** New funds (NFOs or funds with <3 years history) are often unfairly rated zero or recklessly recommended without historical proof.
* **Investor-Facing Outcome:** Transparent maturity framework that evaluates funds based on available data history without penalizing new funds.
* **History Buckets:**
  - `< 1 Year`: Conventional score unavailable (insufficient history).
  - `1–3 Years`: Limited evidence / reduced score confidence.
  - `3–5 Years`: Normal evidence evaluation.
  - `5+ Years`: Full evidence evaluation.
  - `10+ Years`: Strong historical persistence evaluation.
* **Statuses:** `Recommendation unavailable / Insufficient evidence` when data is inadequate.
* **What Platform Must NOT Do:** Must NOT mechanically classify new funds as poor investments merely because they lack multi-year history.

---

## 4. Portfolio & Concentration Analysis

### 4.1 Multi-Level Portfolio Analysis
* **Investor Problem:** Investors holding multiple mutual funds often unknowingly duplicate stock holdings or over-concentrate in a single sector.
* **Investor-Facing Outcome:** Full portfolio breakdown across 6 structural levels:
  $$\text{Portfolio} \rightarrow \text{Asset Class} \rightarrow \text{Category} \rightarrow \text{Fund} \rightarrow \text{Sector} \rightarrow \text{Security}$$
* **Journey Phase:** Portfolio Review (`Analyze Portfolio`).
* **Inputs Required:** Investor portfolio holdings, monthly AMC portfolio disclosures.
* **Platform Evaluation:** Calculates asset allocation, stock overlap, sector concentration, and fund house duplication.
* **Investor-Facing Output:** Concentration alerts and overlap matrix distinguishing healthy overlap from excessive duplication.
* **What Platform Must NOT Do:** Must NOT trigger automatic sell recommendations solely due to mild stock overlap.

---

## 5. Low-Turnover Rebalancing & Winner Protection

### 5.1 Performance Drift vs User-Driven Drift
* **Investor Problem:** Conventional rebalancing tools force investors to sell outperforming funds merely because market gains altered their target asset allocation.
* **Investor-Facing Outcome:** Intelligent rebalancing that protects outperforming funds (**Winner Protection Principle**).
* **Journey Phase:** Portfolio Monitoring (`Monitor / Rebalance`).
* **Platform Evaluation:** Distinguishes performance-driven drift (market appreciation) from user-driven drift (intentional changes).
* **Correction Hierarchy:**
  1. Redirect new monthly SIP contributions to underweighted categories.
  2. One-time windfall allocation to underweighted areas.
  3. Selling overweight funds only when risk tolerance is severely breached and after-tax benefit is positive.
* **Explainability:** Displays after-tax, after-exit-load net economic benefit calculation before suggesting any switch.
* **What Platform Must NOT Do:** Must NOT recommend selling a strong fund merely because market appreciation made it overweight.

### 5.2 Anti-Return-Chasing Guardrail
* **Investor Problem:** Investors frequently want to shift money into recent top-performing funds right at market peaks.
* **Investor-Facing Outcome:** Protective risk guardrail when an investor proposes increasing exposure to recent high performers.
* **Platform Evaluation:** Compares current vs proposed risk profile, drawdown potential, and historical cycle persistence.
* **Investor-Facing Output:** Trade-off warning highlighting potential downside risk and long-term suitability misalignment.
* **What Platform Must NOT Do:** Must NOT silently accept a materially unsuitable high-risk allocation change without warning.

---

## 6. Tax & Cost-Aware Recommendation Engine

### 6.1 Net After-Tax Economic Benefit Engine
* **Investor Problem:** Switching recommendations often ignore capital gains tax (STCG/LTCG) and exit loads, wiping out expected gains.
* **Investor-Facing Outcome:** Recommendations evaluated strictly on a net after-cost basis:
  $$\text{Net Benefit} = \text{Expected Benefit of Switch} - \text{Capital Gains Tax} - \text{Exit Load} - \text{Transaction Fees}$$
* **Journey Phase:** Recommendation Generation (`Recommend`).
* **Platform Evaluation:** Computes holding periods, tax rates (versioned Income Tax rules), and exit load schedules.
* **Decision Actions:**
  - **Buy:** Strong fund + suitable + portfolio need + positive after-cost benefit.
  - **Accumulate:** Strong & suitable; progressive SIP preferred due to regime/context.
  - **Hold:** Fund remains appropriate; no action needed.
  - **Monitor:** Deterioration suspected but evidence insufficient for action.
  - **Review:** Persistent deterioration detected; replacement evaluation required.
  - **Sell/Switch:** Persistent deterioration + suitable replacement + positive net after-cost benefit.
  - **Recommendation unavailable:** Data incomplete or evidence insufficient.
* **What Platform Must NOT Do:** Must NOT recommend a fund switch unless net after-cost benefit is positive.

---

## 7. Windfalls & One-Time Capital Allocation

### 7.1 Multi-Goal Windfall Allocation
* **Investor Problem:** Receiving a lump sum (bonus, inheritance) leads investors to invest in a single trending fund rather than strengthening their overall financial plan.
* **Investor-Facing Outcome:** Portfolio-wide allocation of lump-sum funds across multiple active goals based on funding gaps and risk capacity.
* **Journey Phase:** Capital Allocation (`Invest / Optimize`).
* **Inputs Required:** Lump-sum windfall amount.
* **Platform Evaluation:** Evaluates goal funding gaps, portfolio asset allocation, concentration limits, and tax implications.
* **Investor-Facing Output:** Quantified multi-goal distribution options showing impact on each goal's completion timeline.
* **What Platform Must NOT Do:** Must NOT allocate a windfall solely to the single fund currently being viewed on screen.

---

## 8. Evidence, Provenance & Transparency

### 8.1 Progressive Disclosure & Source Links
* **Investor Problem:** Financial apps generate opaque scores or generate fake "AI advice" without providing supporting proof.
* **Investor-Facing Outcome:** Every recommendation provides 5 levels of progressive disclosure:
  1. **Default:** Succinct action summary.
  2. **Why?:** Concise bulleted rationale.
  3. **Detailed Reasoning:** Full metric drivers, risk factors, and calculations.
  4. **Sources:** Clickable links to authoritative sources (AMFI, SEBI, RBI, AMC disclosures).
  5. **Methodology:** Explicit formula explanation.
* **What Platform Must NOT Do:** Must NOT imply an external authority published a score calculated internally by the platform.
