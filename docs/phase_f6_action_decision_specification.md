# Phase F.6 Action Decision Engine Specification (Corrected - F.6.1)

## 1. Architectural Hierarchy & Core Responsibilities
The proposed **Action Decision Engine** operates as the final orchestration layer in the mutual fund decision architecture:

$$\text{DATA} \rightarrow \text{METRIC ENGINE} \rightarrow \text{FUND QUALITY} \rightarrow \text{SUITABILITY} \rightarrow \text{PORTFOLIO NEED} \rightarrow \text{ECONOMIC BENEFIT} \rightarrow \text{ACTION}$$

### Primary Role
The specification defines Action as the orchestration layer answering:
> *"What explicit transaction or holding recommendation should the platform present to the investor now, if anything?"*

### Structural & Construct Isolation Boundaries
The Action layer is designed as a decision and orchestration engine, **not** a scoring or tax engine. To preserve construct isolation and scope boundaries, the governed decision logic requires that the Action layer **MUST NOT**:
1. Recalculate or override **Fund Quality** scores or historical metrics.
2. Recalculate or override **Suitability** statuses or risk bounds.
3. Recalculate or override **Risk Alignment**, **Capacity**, or **Tolerance**.
4. Recalculate or override **Portfolio Need** states or candidate fulfillment logic.
5. Recalculate or override **Economic Benefit**, statutory capital gains tax rules, scheme exit loads, or transaction costs.
6. Manufacture expected return differences or market timing predictions.
7. Execute transactions directly or mutate user portfolios automatically.

---

## 2. Low-Turnover Principle & Governance
The foundational architectural rule governing Action decisioning is:

$$\text{DEFAULT ACTION} = \text{HOLD / DO NOTHING UNLESS EVIDENCE JUSTIFIES CHANGE}$$

### Low-Turnover Guardrails
The governed specification requires resisting:
- **Return Chasing & Recent Outperformance:** High recent returns alone shall never trigger a `BUY` or `SWITCH`.
- **Score & Rank Chasing:** A fund becoming second-best or experiencing cosmetic score shifts shall **not** trigger a transaction.
- **Exit-Load & Tax-Inefficient Turnover:** Switching is prohibited if realized costs offset expected benefits.
- **Short-Lived Volatility:** Temporary quarterly underperformance must not trigger premature liquidations.

The proposed engine shall require **material evidence proportional to the financial consequence** of the action.

---

## 3. Action State Taxonomy & Semantics

### Investor-Facing Vocabulary
| Action State | Position Applicability | Definition & Financial Semantics |
| :--- | :--- | :--- |
| **`BUY`** | New Position Only | A new position is justified by an identified portfolio/goal need, and the candidate fund is suitable, capable, sufficiently evidenced by validated criteria, and economically actionable. |
| **`ACCUMULATE`** | New or Existing Position | Existing or new holding where additional exposure is justified by a portfolio need, but progressive allocation staging (e.g. SIP/staged entry) is preferred due to allocation, capacity, or concentration constraints. |
| **`HOLD`** | Existing Position Only | Existing exposure remains appropriate and there is no sufficiently strong evidence or economic justification to change it. Default state for owned funds. |
| **`MONITOR`** | Existing Position Only | Observation signal or uncertainty exists (e.g. mild style drift, manager change), but evidence is currently insufficient to justify position reassessment or liquidation. |
| **`REVIEW`** | Existing Position Only | Material or persistent deterioration signal exists requiring explicit investor reassessment before continuing to hold or changing position. |
| **`SELL`** | Existing Position Only | Existing position should be reduced or liquidated because severe persistent deterioration exists OR a materially superior candidate exists AND after-tax/after-cost economics justify liquidation. |

---

## 4. Decision Precedence Hierarchy

When evaluating upstream evidence, conflicts shall be resolved via a strict 7-tier precedence model:

$$\text{Tier 1: INVALID / UNSAFE}$$
$$\downarrow$$
$$\text{Tier 2: INSUFFICIENT INFORMATION}$$
$$\downarrow$$
$$\text{Tier 3: NOT SUITABLE / HARD CONSTRAINT}$$
$$\downarrow$$
$$\text{Tier 4: MATERIAL REVIEW SIGNAL}$$
$$\downarrow$$
$$\text{Tier 5: ECONOMIC / PORTFOLIO ACTIONABILITY}$$
$$\downarrow$$
$$\text{Tier 6: POSITIVE OPPORTUNITY}$$
$$\downarrow$$
$$\text{Tier 7: HOLD / NO CHANGE (Default)}$$

### Conflict Resolution Invariants
- High Fund Quality **cannot** override an `INVALID` assessment or `NOT_SUITABLE` constraint.
- Positive Portfolio Need **cannot** override `UNSUITABLE` status or `ECONOMICALLY_NOT_BENEFICIAL` status.
- Positive opportunity **cannot** override insufficient evidence or unquantified tax/load costs.

---

## 5. Dependency Chains & Action Rules

### A. Purchase Recommendations (`BUY` / `ACCUMULATE`)
A purchase action requires evaluation across the 9-stage decision chain:
$$\text{Need Identified} \rightarrow \text{Candidate Capable} \rightarrow \text{Suitable} \rightarrow \text{Risk Aligned} \rightarrow \text{Quality Evidence} \rightarrow \text{Validated Actionability} \rightarrow \text{Economically Beneficial} \rightarrow \text{Data Sufficient} \rightarrow \text{Actionable}$$

- **No Need Constraint:** If `Portfolio Need = NO_MATERIAL_NEED`, purchase is prohibited $\rightarrow$ `HOLD` (existing) or `NO_ACTION` (new candidate).
- **Affordability Constraint:** If need exists but `Affordability = CONSTRAINED`, the governed logic specifies emitting constrained `ACCUMULATE` (staged entry) rather than an unaffordable lump-sum `BUY`.
- **Unknown Economic Benefit:** If `Economic Benefit = BENEFIT_UNCERTAIN`, a switch or purchase cannot claim financial justification $\rightarrow$ downgrade to `MONITOR` / `REVIEW`.
- **Evidence & Actionability Requirement:** `BUY` requires sufficient validated evidence and actionability according to a separately governed production criterion. Arbitrary numerical confidence thresholds are prohibited. Low confidence reduces willingness to take consequential action.

### B. Tax & Cost Consumption Rule
$$\text{ACTION CONSUMES VALIDATED TAX/COST ASSESSMENT}$$

- Action does **NOT** own statutory tax rules, holding-period classifications, tax-lot calculations, exit-load schedule parsing, or transaction cost calculations.
- The future Tax/Cost layer owns all statutory tax calculations, exit loads, transaction fees, and after-tax/after-cost economic assessments.
- Action consumes the resulting governed Tax/Cost assessment.
- If a required Tax/Cost assessment is unavailable (`UNKNOWN`), Action **must not** invent the value, **must not** assume zero, and **must** downgrade or withhold consequential transaction recommendations.
- Holding-period rules are referred to generically as: *"validated statutory holding-period classification supplied by the Tax/Cost layer."* Action documentation does not hardcode statutory rules or 365-day assumptions.

### C. Deterioration Escalation Model (`MONITOR` $\rightarrow$ `REVIEW` $\rightarrow$ `SELL`)
Deterioration shall progress through governed escalation stages:
1. **`MONITOR` Stage:** Early indicator detected (e.g. 1-quarter alpha drop, minor TER hike). Position is flagged for observation; zero transaction recommended.
2. **`REVIEW` Stage:** Persistent or material deterioration confirmed (e.g. 3-quarter category underperformance, loss of key manager, style drift). Position marked for explicit investor review.
3. **`SELL` Stage:** Reassessment confirms holding is no longer justified AND replacement candidate is suitable, capable, AND after-tax/after-cost switching economics are positive (`ECONOMICALLY_BENEFICIAL`).

---

## 6. Switch & Liquidation Guardrails

A `SELL` or `SWITCH` recommendation shall require positive verification of 14 guardrail items:
1. Existing holding suitability status
2. Existing holding deterioration evidence
3. Candidate scheme suitability status
4. Candidate scheme capability (`CANDIDATE_CAN_FULFILL_NEED`)
5. Candidate Fund Quality score and stability
6. Overall evidence confidence
7. Economic benefit state (`ECONOMICALLY_BENEFICIAL`)
8. Realized capital gains tax impact (Supplied by Tax/Cost layer)
9. Scheme exit load schedule (Supplied by Tax/Cost layer)
10. Transaction fee schedule (Supplied by Tax/Cost layer)
11. Portfolio concentration and category overlap
12. Impact on goal allocation
13. Execution feasibility and contribution capacity
14. Data completeness and freshness

**Guardrail Invariants:**
- Higher candidate score alone **never** triggers `SELL` of an existing suitable holding.
- If tax or exit load data is missing (`UNKNOWN`), `SELL` is prohibited $\rightarrow$ downgrade to `REVIEW` with data warning.

---

## 7. Macro & Market Context Boundaries
- Macro context (e.g. market volatility regime, interest rate cycle) serves **exclusively** as a risk-control and contextual flag.
- Macro context **MUST NOT** be used for market timing, return forecasting, automatic crash buying, automatic rally liquidations, or tactical regime switching.

---

## 8. Provenance & Explainability Requirements

Every Action assessment result shall preserve end-to-end auditability and structured explanations:

### Provenance Attributes
- `assessment_id` & `timestamp_utc`
- `investor_profile_id`, `goal_id`, `portfolio_id`
- `fund_quality_assessment_id`
- `suitability_assessment_id`
- `portfolio_need_assessment_id`
- `economic_benefit_assessment_id`
- `action_state` (`BUY`, `ACCUMULATE`, `HOLD`, `MONITOR`, `REVIEW`, `SELL`)
- `actionability_status` & `action_confidence`
- `methodology_version` & `rule_version`

### Structured Explanation Schema
Each action shall include structured reasoning containing:
1. **Primary Action Rationale:** Core driver (e.g. portfolio gap fulfillment, persistent deterioration).
2. **Supporting Evidence Summary:** Key metrics and upstream states.
3. **Blocking & Constraint Warnings:** Affordability limits, tax friction warnings, missing metadata warnings.
4. **Non-Execution Disclaimer:** Explicit statement that Action is an analytical recommendation and not an automated broker order.
