# Phase F.5 Economic Benefit Decision Logic Specification (Verified - F.5.2)

## 1. Architectural Role & Principles
Economic Benefit sits downstream of **Portfolio Need** and upstream of **Action** in the mutual fund decision engine hierarchy:

$$\text{DATA} \rightarrow \text{METRIC ENGINE} \rightarrow \text{FUND QUALITY} \rightarrow \text{SUITABILITY} \rightarrow \text{PORTFOLIO NEED} \rightarrow \text{ECONOMIC BENEFIT} \rightarrow \text{ACTION}$$

### Fundamental Principle
$$\text{PORTFOLIO NEED} \neq \text{ECONOMIC BENEFIT} \neq \text{ACTION}$$

1. **Portfolio Need** identifies whether an underlying portfolio/goal requirement exists (`NEED_IDENTIFIED`, `EXCESS_EXPOSURE`, `NO_MATERIAL_NEED`).
2. **Economic Benefit** evaluates whether satisfying that requirement through a proposed implementation path creates net positive economic value after monetary costs and constraints.
3. **Action** determines execution parameters (order type, timing, allocation staging, SIP modification).

### Core Invariants
- A Portfolio Need does **not** automatically justify a transaction.
- A higher-quality fund does **not** automatically justify switching.
- A suitable candidate fund does **not** automatically justify switching.
- Economic Benefit **must** be evaluated relative to an explicit baseline before Action can be considered.

---

## 2. Decision Precedence & State Taxonomy

### 6-Stage Decision Precedence Sequence
1. **Stage 1: Validity Check** — Verify input non-nullness, schema compliance, and upstream assessment integrity. Returns `INVALID_ASSESSMENT` if malformed.
2. **Stage 2: Information Sufficiency Check** — Check presence of required baseline, proposed state, tax inputs, exit loads, and transaction cost metadata. If material costs are unknown and cannot be bounded, returns `INSUFFICIENT_INFORMATION`.
3. **Stage 3: Portfolio Need Verification** — Confirm upstream Portfolio Need status. If `NO_MATERIAL_NEED` (or no portfolio need), the engine emits `NO_EVALUABLE_CHANGE` (no portfolio need exists to justify switching; this does **not** falsely claim the candidate fund is economically harmful).
4. **Stage 4: Conceptual Net Economic Benefit Evaluation** — Evaluate change-relative expected improvement against monetary economic costs:
   $$\text{Monetary Economic Cost} = \text{Tax Liability} + \text{Exit Load} + \text{Transaction Cost} + \text{Other Validated Monetary Costs}$$
   $$\text{Conceptual Net Economic Benefit} = \text{Expected Improvement} - \text{Monetary Economic Cost}$$
5. **Stage 5: Friction & Uncertainty Integration** — Integrate qualitative non-monetary friction (operational complexity, investor effort, unnecessary turnover) to adjust evidence confidence and actionability. Qualitative friction is **never** added arithmetically to rupee-denominated monetary costs.
6. **Stage 6: Output State Assembly** — Assign canonical economic benefit state, assemble provenance, and generate deterministic natural-language explanations.

### State Taxonomy
- `ECONOMICALLY_BENEFICIAL`: Incremental expected monetary economic improvement exceeds total monetary economic costs and friction (Conceptual Outcome pending validated production methodology).
- `ECONOMICALLY_NOT_BENEFICIAL`: Validated monetary costs exceed expected improvement for an identified portfolio need (Conceptual Outcome pending validated production methodology).
- `ECONOMICALLY_NEUTRAL`: Expected improvement and monetary costs offset each other within uncertainty bounds.
- `NO_EVALUABLE_CHANGE`: No Portfolio Need exists to justify evaluating a portfolio change; no economic harm or benefit is claimed.
- `BENEFIT_UNCERTAIN`: Material cost or expected improvement inputs are unquantified or unvalidated; net benefit cannot be conclusively determined.
- `INSUFFICIENT_INFORMATION`: Missing mandatory structural inputs (e.g. absent baseline portfolio context or unresolvable holding dates).
- `INVALID_ASSESSMENT`: Upstream assessment references are malformed, negative, or invalid.

---

## 3. Change-Relative Evaluation Model

Economic Benefit is **strictly change-relative**. A proposed state is always compared against an explicit baseline:

$$\Delta \text{Economic Value} = \text{Value}(\text{Proposed State}) - \text{Value}(\text{Baseline State}) - \text{Monetary Economic Costs}$$

### Baseline Categorization
- `NO_CHANGE` / `CONTINUE_EXISTING_POSITION`: Current holdings and contribution allocations remain unaltered. Default reference baseline.
- `CURRENT_ALLOCATION`: Existing SIP/lump-sum contribution routing.

### Implementation Evaluation Framework
The engine evaluates alternative implementation paths without arbitrary global preference:
1. **New Money Allocation (`NEW_MONEY`):** Deploying unallocated cash or fresh monthly contributions into a candidate fund. Potentially lower monetary cost (avoids tax/exit load on existing holdings), but must be evaluated for suitability, affordability, allocation preservation, and overall expected improvement.
2. **Existing Holding Switch (`SWITCH_EXISTING`):** Redeeming units of an existing holding to acquire a candidate fund. Requires explicit accounting for tax liability, exit loads, and transaction costs.
3. **Contribution Redistribution (`REDISTRIBUTE_CONTRIBUTIONS`):** Redirecting future regular inflows (SIPs) from an existing fund to a candidate fund without liquidating accumulated units.

**Governance Rule:** `NEW_MONEY` is **not** automatically preferred over `SWITCH_EXISTING`. It is a distinct candidate path to be evaluated on suitability, affordability, capacity, and net economic value.

---

## 4. Cost Taxonomy & Friction Separation

Monetary economic costs and non-monetary qualitative friction are strictly decoupled:

$$\text{Monetary Economic Cost} = \text{Tax Liability} + \text{Exit Load} + \text{Transaction Cost} + \text{Other Validated Monetary Costs}$$

Qualitative non-monetary friction (operational complexity, turnover penalty, investor effort) is **never** arithmetically added to rupee monetary costs.

| Cost Category | Type | Description | Authority / Source | Missing Data Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Tax Liability** | Monetary | Realized capital gains tax (STCG / LTCG) based on holding period, asset class, and versioned tax rules. | Future Authoritative Tax Module (Proposed path: `tax/rules.py`) | Set to `UNKNOWN`; do NOT default to zero. |
| **Exit Load** | Monetary | Scheme-specific, date-sensitive exit penalty based on redemption date vs purchase date. | Scheme Master / Factsheets | Set to `UNKNOWN`; do NOT default to zero or global 1% assumptions. |
| **Transaction Cost** | Monetary | Statutory STT, stamp duty, platform transaction fees. | Regulatory / Platform Fee Schedule | Set to `UNKNOWN`; do NOT default to zero. |
| **Qualitative Friction** | Non-Monetary | Operational complexity, unnecessary turnover, investor effort. | Qualitative Context Flag | Modifies confidence/actionability; NEVER converted to arbitrary rupee values. |

---

## 5. Distinction Between Conceptual Framework and Production Calculation

- **Conceptual Economic Framework (Approved in F.5.1/F.5.2):** The architectural relationship that net economic value equals forward expected improvement minus monetary economic costs, modified by qualitative friction confidence adjustments.
- **Validated Production Calculation (Future Work):** Exact numerical calculation formulas, which remain deferred until forward return models, tax-lot parser integration, and scheme exit-load schedule parsers are fully integrated and empirically validated.

---

## 6. Expected Improvement Governance & Terminology Clarification

- **Conceptual vs Production Expected Improvement:**
  $$\text{Conceptual Expected Improvement} \neq \text{Validated Production Decision Input}$$
- **Forward-Looking Requirement:** `Historical Observed Return Difference` $\neq$ `Expected Future Return Difference`.
- **Missing Forward Model Rule:** The platform currently lacks a validated forward-looking expected-return model. Therefore, `EXPECTED_IMPROVEMENT` remains `UNKNOWN` in all production-evaluation contexts, resulting in `BENEFIT_UNCERTAIN`.
- **Prohibited Substitutions:** Trailing CAGR, recent outperformance, Fund Quality scores, percentiles, or scheme rankings must **never** be substituted for forward expected return difference.
- **Production Guardrail:** `EXPECTED_IMPROVEMENT` cannot be used as a numerical decision input in production code until a separately governed and validated forward-looking return methodology is formally established.

---

## 7. Construct Isolation & Architectural Boundaries

To preserve architectural integrity, the Economic Benefit layer **MUST NOT**:
1. Recalculate or override **Fund Quality** scores.
2. Recalculate or override **Suitability** assessments.
3. Recalculate or override **Risk Alignment**, **Capacity**, or **Tolerance**.
4. Manufacture expected returns by substituting historical CAGR for forward-looking return models.
5. Manufacture missing tax rates, exit loads, or transaction costs.
6. Apply global default exit-load assumptions (e.g. 1% within 365 days).
7. Generate Action recommendations (`BUY`, `SELL`, `HOLD`, `REBALANCE`, `SWITCH`).
8. Perform automated tax-loss harvesting or portfolio rebalancing optimization.

---

## 8. Provenance & Explainability Requirements

Every Economic Benefit assessment result must capture full end-to-end traceability:

### Provenance Attributes
- `assessment_id` & `timestamp_utc`
- `portfolio_need_assessment_id`
- `upstream_suitability_assessment_id`
- `baseline_portfolio_id` & `baseline_holding_id`
- `proposed_candidate_id`
- `implementation_mode` (`NEW_MONEY`, `SWITCH_EXISTING`, `REDISTRIBUTE_CONTRIBUTIONS`)
- `tax_input_reference_id` & `exit_load_reference_id`
- `methodology_version` & `rule_version`

### Explanation Requirements
1. Explicitly identify baseline and proposed states.
2. Itemize expected improvements, monetary taxes, exit loads, and transaction fees.
3. Highlight qualitative friction and remaining uncertainties.
4. Provide a clear statement explaining why the result is **not** an Action recommendation.
