# Phase F.2C — Risk Capacity Methodology Design & Calibration

**Phase:** Phase F.2C — Risk Capacity Methodology Design  
**Date:** 2026-09-09 UTC  
**Final Status:** `PHASE F.2C ACCEPTED WITH PROVISIONAL PARAMETERS`  
**Scope:** Methodology design, factor selection, model architecture, and calibration planning for the Risk Capacity Engine. **Zero production Python code implemented.**

---

## 1. Precise Definition of Risk Capacity

**Risk Capacity** is an investor's *objective, financially measurable ability* to absorb capital loss in an investment portfolio without materially impairing:
- essential living obligations (fixed expenses);
- short-term financial security (liquid emergency reserve);
- committed debt obligations (EMIs, loan repayments);
- near-term financial commitments (goals with imminent liquidity needs).

### Operational Financial Definition

> **Risk Capacity answers:** "If this investor's portfolio fell by X% today, what is the probability that they could continue meeting essential obligations without forced liquidation of investments at a loss?"

### Mandatory Separation from Adjacent Concepts

These concepts must **NOT** collapse into a single score without explicit justification:

| Concept | Governing Question | Governing Inputs | Prohibited Conflation |
|---|---|---|---|
| **Risk Capacity** | Can this investor financially survive portfolio losses? | Income, expenses, debt, reserves, savings surplus | Behavioral preferences, investment goals, fund quality |
| **Risk Tolerance** | Is this investor psychologically willing to endure volatility? | Scenario questionnaire responses, behavioral history | Financial ratios, income level, net worth |
| **Investment Horizon** | How long until capital is needed for a specific goal? | Goal target date, goal type, commitment date | Risk capacity level, behavioral comfort |
| **Liquidity Need** | What near-term cash access does this investor require? | Short-term commitments, irregular income, emergency access | Risk tolerance, investment return expectations |
| **Affordability** | How much can this investor sustainably invest per period? | Sustainable surplus after all obligations | Risk capacity level, fund quality, behavioral preference |

These five constructs feed into suitability assessment, but each must be evaluated independently before combination.

---

## 2. Candidate Factor Evaluation

The following factors were systematically evaluated for inclusion in Risk Capacity assessment:

### A. Gross Monthly Income
- **Genuinely Risk Capacity?** Partially — raw income is context, not capacity.
- **Assessment:** Income alone does not determine capacity; a high-income investor with high fixed obligations may have lower capacity than a moderate-income investor with low obligations.
- **Verdict:** **Do not use raw income as a direct weighted factor.** Use income as a normalizing denominator for debt-to-income and savings-rate ratios. Including it independently would double-count against the derived ratios.

### B. Income Stability (Employment Type / Regularity)
- **Genuinely Risk Capacity?** Yes — income interruption risk is a genuine capacity modifier.
- **Assessment:** Stable salaried income provides predictable cash-flow; variable or self-employed income creates elevated interruption risk that amplifies the impact of any portfolio loss.
- **Verdict:** **Include as a capacity modifier / reserve requirement multiplier.** Do not assign arbitrary income-stability scores. Represent it through its consequence — a higher required emergency reserve for variable-income investors.

### C. Fixed Essential Expenses (Monthly)
- **Genuinely Risk Capacity?** Yes — fixed obligations are the floor below which income cannot fall without defaulting on essentials.
- **Assessment:** Essential expenses set the minimum sustainable cash-flow requirement. If portfolio returns are drawn down, the investor still must meet these.
- **Verdict:** **Include, but only as an input to surplus and reserve adequacy calculations — not as a standalone factor.** Avoids double-counting if also incorporated into savings calculation.

### D. Debt Servicing Burden (Monthly EMIs / Loan Repayments)
- **Genuinely Risk Capacity?** Yes — committed debt obligations directly constrain disposable income and cannot be deferred.
- **Assessment:** High debt service consumes cash-flow that would otherwise buffer portfolio losses.
- **Verdict:** **Include as a debt-burden ratio (debt servicing / income) with ordinal constraint effects.** See §6 for detailed treatment.

### E. Liquid Emergency Reserve (Current Balance)
- **Genuinely Risk Capacity?** Yes — directly determines how long an investor can sustain obligations if income is interrupted or portfolio is impaired.
- **Assessment:** Reserves are the primary firewall preventing forced investment liquidation during market downturns.
- **Verdict:** **Include as reserve adequacy ratio (reserve / essential monthly expenses), adjusted for income stability.** See §7 for detailed treatment.

### F. Sustainable Monthly Savings / Surplus
- **Genuinely Risk Capacity?** Yes, as a derived indicator — after all obligations, the remaining discretionary surplus measures how much capacity exists to sustain SIPs during market stress.
- **Assessment:** If surplus is thin, any income shock immediately translates into SIP discontinuation — a form of forced de-investment.
- **Verdict:** **Include as a derived factor, not independently alongside income, expenses, and debt — that would be triple-counting.** See §3 (Double-Counting Analysis) and §8.

### G. Financial Dependents / Household Obligations
- **Genuinely Risk Capacity?** Partially — dependents increase the minimum essential expense floor and typically increase the required emergency buffer.
- **Assessment:** Dependents reduce financial flexibility and increase exposure to unexpected expense shocks (medical, educational). However, their effect is best captured through the expense and reserve adequacy calculations rather than a standalone dependent-count factor.
- **Verdict:** **Do not assign arbitrary per-dependent monetary weights.** Include the dependent effect as a reserve requirement multiplier (higher dependents → higher required reserve coverage). See §10.

### H. Near-Term Financial Commitments
- **Genuinely Risk Capacity?** Yes — committed near-term financial obligations (school fees, home down payment, medical procedure) reduce the pool of investable capital and constrain risk-taking.
- **Assessment:** A material known commitment within 12–18 months creates an effective horizon floor.
- **Verdict:** **Include as a liquidity constraint, not as a separate capacity factor.** It constrains the percentage of capital that can be exposed to volatile assets rather than modifying the capacity tier directly.

### I. Investment Horizon
- **Genuinely Risk Capacity?** No — horizon is a separate, goal-specific construct (covered in Phase F.6).
- **Assessment:** Capacity is about financial resilience today; horizon is about when capital must be retrieved. These operate on different axes.
- **Verdict:** **Exclude from Risk Capacity.** The horizon engine applies a ceiling downstream.

### J. Liquidity Requirements
- **Genuinely Risk Capacity?** Partially — near-term liquidity needs constrain portfolio composition but are better captured through liquidity constraint / near-term commitment.
- **Verdict:** **Represent through the near-term commitment flag (§H), not as a standalone factor.**

### K. Existing Financial Assets (Total)
- **Genuinely Risk Capacity?** Partially — a large financial asset base provides a buffer, but asset type and liquidity matter greatly.
- **Assessment:** Liquid, accessible assets (savings accounts, liquid funds) extend the emergency buffer. Illiquid assets (real estate, locked deposits) do not. Counting all assets as equally liquidity-enhancing would misrepresent capacity.
- **Verdict:** **Include only liquid / readily accessible assets, and only in the context of emergency reserve calculation — not as a general wealth multiplier.** See §11.

### L. Existing Portfolio Exposure (Current Equity/Debt Mix)
- **Genuinely Risk Capacity?** No — current portfolio composition belongs to Portfolio Context and influences future Portfolio Need assessments.
- **Verdict:** **Exclude from Risk Capacity.** Portfolio composition analysis is a distinct downstream layer.

---

## 3. Double-Counting Analysis

The most critical structural risk in a multi-factor capacity model is **double-counting the same financial condition through multiple variables**.

### Identified Overlap Risks

**Primary Risk: Income / Expenses / Debt / Savings all measure the same underlying surplus.**

Consider the financial identity:

```
Gross Income
    − Taxes
    − Fixed Expenses
    − Debt EMIs
    = Sustainable Monthly Surplus
```

If all five components (income, taxes, expenses, debt, surplus) are independently scored and weighted, the same underlying constraint is counted five times. A person with ₹1L income, ₹40K expenses, and ₹30K debt has ₹30K surplus — counting income *and* expenses *and* debt *and* surplus as separate weighted inputs misrepresents the actual financial situation.

**Debt-to-Income and Savings Ratio both reflect the surplus.**

Net DTI ratio and savings ratio are algebraically correlated:
```
Savings Ratio ≈ 1 − Expense Ratio − Debt Ratio
```
Using all three as independent weighted inputs creates correlated, redundant signals.

### Recommended Structure to Minimize Double-Counting

Use a **constraint-based architecture** rather than a **weighted composite**:

1. **Reserve Adequacy Ratio** = `liquid reserves / (adjusted required monthly cover)` — one ratio, no double-counting.
2. **Debt Burden Ratio** = `monthly debt servicing / monthly gross income` — one ratio, normalizing income.
3. **Sustainable Surplus Ratio** = `(income − taxes − expenses − debt) / income` — a derived composite that absorbs all four components in a single, clean ratio.
4. **Income Stability** = categorical modifier on the reserve requirement — one adjustment, not a separate scored factor.

This structure avoids redundant weighting by treating income, expenses, and debt as sub-components of a single surplus calculation rather than independent factors.

---

## 4. Model Architecture Evaluation

### Model A — Weighted Composite Score
**Description:** Multiple normalized factors → weighted score → risk-capacity tier.

| Property | Assessment |
|---|---|
| Advantages | Continuous output; gradual scoring; familiar pattern |
| Disadvantages | Arbitrary weights; compensatory scoring (high reserves can mask extreme debt); double-counting risk |
| Explainability | Low — hard to explain why weight x on factor y |
| Robustness | Low — sensitive to weight choices |
| Missing data | Fragile — missing factor drops out and distorts score |
| Governance risk | High — weights require empirical justification that does not yet exist |
| **Verdict** | **NOT RECOMMENDED for Risk Capacity** |

### Model B — Constraint / Bottleneck Model
**Description:** Each financial dimension independently imposes a ceiling on capacity. The overall capacity is the minimum across all binding constraints.

| Property | Assessment |
|---|---|
| Advantages | No arbitrary weighting; explainable; worst-case constrains the whole; aligns with fiduciary conservatism |
| Disadvantages | Can be harsh if any single dimension is borderline; requires clear threshold calibration |
| Explainability | High — "Your capacity is constrained because debt burden is high" |
| Robustness | High — constraints are independent; adding a new dimension does not break existing logic |
| Missing data | Conservative: unknown factor → uncertain constraint → lower confidence, conservative fallback |
| Governance risk | Lower — each threshold is independently justifiable |
| **Verdict** | **RECOMMENDED as the primary structural pattern** |

### Model C — Hybrid Model (Baseline + Hard Constraints)
**Description:** A baseline capacity assessment (from surplus/reserve) with hard constraints imposed by extreme debt or reserve deficiency.

| Property | Assessment |
|---|---|
| Advantages | Nuanced for middle-ground cases; hard constraints for extreme situations |
| Disadvantages | Introduces two distinct evaluation modes; harder to explain transitions |
| Explainability | Moderate |
| Missing data | Moderately robust |
| Governance risk | Moderate |
| **Verdict** | **ACCEPTABLE as an enhancement of Model B** — see recommended architecture below |

### Model D — Continuous Capacity Model
**Description:** Risk Capacity represented as a continuous [0.0, 1.0] score internally, mapped to ordinal tiers only for output.

| Property | Assessment |
|---|---|
| Advantages | No discrete discontinuities; gradual representation |
| Disadvantages | Continuous score still requires calibration; false precision; arbitrary scaling |
| Explainability | Lower for continuous internal scores |
| Governance risk | Higher — continuous functions require more parameters |
| **Verdict** | **USEFUL as an internal representation, NOT as the primary architecture** |

---

## 5. Recommended Architecture: Constraint-Based with Ordinal Output

### Core Architecture Design

The recommended architecture is a **Multi-Constraint Bottleneck Model** with three primary constraint dimensions:

```
RISK CAPACITY ASSESSMENT
    │
    ├── DIMENSION 1: Debt Burden Assessment
    │     Input: monthly_debt_servicing / monthly_gross_income
    │     Output: DEBT_CONSTRAINT_LEVEL (No Constraint | Moderate | High | Severe)
    │
    ├── DIMENSION 2: Reserve Adequacy Assessment
    │     Input: liquid_reserves / (required_monthly_cover × stability_multiplier)
    │     Output: RESERVE_CONSTRAINT_LEVEL (No Constraint | Thin | Inadequate | Critical)
    │
    ├── DIMENSION 3: Sustainable Surplus Assessment
    │     Input: (income − taxes − expenses − debt) / income
    │     Output: SURPLUS_CAPACITY_LEVEL (Adequate | Limited | Thin | None)
    │
    └── INTEGRATION RULE:
          overall_capacity = min(D1_capacity_ceiling, D2_capacity_ceiling, D3_capacity_ceiling)
          [The most constraining dimension governs.]
```

### Hard Constraint Rule (Concept-Approved, Thresholds TBD)

Certain financial conditions are conceptually justified as **hard capacity ceilings** rather than mere scoring penalties:

**Concept:** An investor with a critical reserve deficit (reserves meaningfully below required minimum) or extreme debt burden (debt servicing consuming an extreme fraction of income) does not have the financial resilience to sustain investment during market stress, regardless of other factors.

- **Hard ceiling concept — general principle:** `APPROVED CONCEPT` — Supported by the general principle that forced liquidation during a drawdown converts paper losses into permanent losses, recognized in behavioural finance and fiduciary practice (FPSB India; RBI HFC 2017). The *existence* of capacity ceilings under extreme financial conditions is approved.
- **Hard ceiling — specific implementation (min() per dimension):** `PROVISIONAL` — The exact mechanism by which this concept is implemented — specifically, that each of the three constraint dimensions independently imposes a hard ceiling integrated via min() — is a product architecture choice. Alternative architectures (hierarchical constraints, hybrid baseline + hard-cap) are also conceptually justifiable. This specific mechanism is provisional pending architectural validation.
- **Specific numerical thresholds:** TBD — EMPIRICAL CALIBRATION REQUIRED.

> [!NOTE]
> **Phase F.2C.1 Audit Correction:** The label `APPROVED` previously applied to RC-ARCH-03 covered both the general principle (correctly approved) and the specific min() implementation mechanism (correctly provisional). These are now distinguished.

---

## 5. Should There Be Hard Caps?

**Yes, the concept of hard capacity ceilings is justified for certain extreme conditions.** The reasoning:

1. **Irreversibility of forced liquidation:** An investor who must liquidate investments to meet essential expenses during a market downturn converts temporary paper losses into permanent realized losses. This harm is not symmetric with the upside of higher-risk investment.

2. **Fiduciary precedent:** FPSB India and SEBI RIA regulations both require advisers to assess financial resilience before recommending market-linked investments. The concept of minimum reserve adequacy is explicitly recognized.

3. **Compensatory weighting is unsafe for extreme cases:** A weighted composite could produce a moderate capacity score for an investor with zero emergency reserves and near-zero surplus if they have strong income — that is a dangerous outcome.

**What hard caps prevent:** The scoring system assigning a meaningful capacity level to someone who would be forced to liquidate investments within weeks of any income interruption.

**What hard caps should NOT do:** Apply the same ceiling to all investors who are merely "below average" on some dimension. Caps should apply only at genuinely extreme conditions.

**Thresholds:** The exact conditions triggering a hard ceiling are `PROVISIONAL — REQUIRES EMPIRICAL CALIBRATION`. They should not be invented. The architecture must allow the calibration thresholds to be externalized and updated.

---

## 6. Debt Servicing Treatment

### Recommended Formulation

**Debt Burden Ratio:** `monthly_debt_servicing / monthly_gross_income`

**Design decisions:**

- **Gross vs Net Income:** Gross income is used as the denominator for verifiability and consistency of declaration. Gross income is more objectively declarable (from payslip) and stable across months than net income, which requires knowledge of applicable tax bracket.  
  > [!NOTE]
  > **Phase F.2C.1 Audit Finding (RC-D1-02):** `PROVISIONAL`. The primary external source supporting the debt burden concept (FPSB India DTI guidance) expresses the 40–50% cap relative to **net monthly income**, not gross income. The use of gross income is a pragmatic product design choice for verifiability, not an externally validated financial rule. The denominator choice should be empirically validated for consistency with the surplus formula (§8) and across representative Indian household profiles before production use.
- **Recurring vs Discretionary Debt:** Only recurring committed obligations (home loan EMI, car loan, personal loan repayment) should be included. Discretionary credit card spending is not a committed obligation.
- **Normalization:** Yes — expressing debt as a ratio of income is the appropriate normalization. Absolute EMI figures without income context are meaningless for capacity assessment.
- **Effect type:** The debt burden should impose a **capacity ceiling** rather than a penalty score, for the reasons in §5. The severity of the ceiling should increase with the ratio.
- **Nonlinearity:** Justified in concept. The marginal harm of increasing debt burden accelerates: moving from 20% to 30% debt burden is meaningfully less harmful than moving from 50% to 60%, where the investor has essentially no remaining discretionary buffer.
- **Household context:** Yes, relevant. A dual-income household with the same aggregate debt burden has more resilience than a single-income household. See §22 (Household Context Convention) for the V1 treatment of individual vs. household inputs.

**Exact boundaries:**  
`TBD — EMPIRICAL CALIBRATION REQUIRED`  
Current placeholders ($<30\%$, $30-50\%$, $>50\%$) are provisional hypotheses only.

---

## 7. Emergency Reserve Treatment

### Recommended Formulation

**Reserve Adequacy Ratio:** `liquid_emergency_reserves / (essential_monthly_expenses × required_coverage_months)`

**Design decisions:**

- **Should reserve adequacy depend on income stability?** Yes. A salaried investor with stable, predictable income can tolerate a shorter reserve because income interruption risk is lower. A self-employed or variable-income investor faces higher interruption probability.
- **Employment-type determinant:** Income stability (salaried / variable / self-employed) is the appropriate and verifiable determinant. It must come from user-declared data or verified source — not inferred.
- **Exact ranges (3-6 months salaried, 6-12 months self-employed):** These are FPSB India guidance ranges, classified as `APPROVED CONCEPT` in Phase F.2B. The exact multipliers within those ranges remain `PROVISIONAL`.
- **Representation:** A **continuous adequacy ratio** (actual months covered / required months) is preferable to discrete categories. Values ≥1.0 mean the requirement is met; values <1.0 indicate a deficit.
- **Constraint form:** Reserve deficit imposes a capacity ceiling. The magnitude of the ceiling should increase as the coverage ratio falls below the required minimum.
- **Stability and dependent modifiers — combination rule:** Both stability and dependents modify `required_coverage_months` **additively**, not multiplicatively. Multiplicative compounding would produce excessively high required-months for investors who are simultaneously variable-income and high-dependents. Additive combination is the intended structure: `required_months = base_months + stability_addition + dependent_addition`.
- **Dependents modifier:** Investors with more financial dependents face higher emergency expense shocks. The minimum required coverage should be modified upward — but by a conceptually justified relationship (more dependents → more required months) rather than an arbitrary per-dependent monetary deduction. Note: declared monthly expenses already partially capture the cost of dependents; the dependent months-modifier provides an additional buffer for unexpected emergency shocks, which is intentional conservatism.

**Exact coverage thresholds and dependent modifiers:**  
`TBD — EMPIRICAL CALIBRATION REQUIRED`

---

## 8. Savings / Surplus Treatment

### Recommended Formulation

**Sustainable Surplus Ratio:** `(gross_income − taxes − fixed_expenses − debt_servicing) / gross_income`

**Design decisions:**

- **Is this an independent factor or derived indicator?** A **derived indicator** that absorbs income, expenses, and debt as a single composite measure. It should NOT be scored independently alongside its components.
- **Role in Risk Capacity vs. Affordability:**
  - **Risk Capacity use:** The surplus ratio answers — *"Does this investor have sufficient financial resilience to absorb investment loss without incurring financial hardship?"* This is a resilience check about the investor's ability to sustain obligations during portfolio stress, not a calculation of optimal contribution amount.
  - **Affordability use (Phase F.9, separate engine):** The Sustainable Contribution Engine (AF-01) answers — *"What is the maximum investment contribution this investor can sustainably make?"* This produces a monetary ceiling.
  - These are correctly separate calculations. The surplus ratio in the Risk Capacity engine produces an ordinal resilience tier, not a monetary limit.
- **Surplus as constraint dimension — algebraic dependency note:**
  > [!NOTE]
  > **Phase F.2C.1 Audit Finding:** The surplus ratio is algebraically dependent on the debt burden ratio: `Surplus Ratio ≈ 1 − expense_rate − Debt Burden Ratio`. Dimension 3 (surplus) is therefore not fully orthogonal to Dimension 1 (debt). When both are used in the min() integration, a high-debt scenario causes both D1 and D3 to impose constraints from the same underlying cause. D3 should be understood as a **combined cash-flow verification check** — it catches combined stress scenarios (e.g., moderate debt + high expenses + low income simultaneously) not fully captured by D1 and D2 alone. F.3 implementation must document this dependency explicitly.
- **Surplus as constraint check:** If the surplus is negative or near-zero, it is a direct indicator that the investor cannot meet current obligations — a strong capacity-limiting condition.
- **The 40% denominator in the prior formula (`Savings / (Income × 40%)`):** This benchmark is arbitrary without evidence that 40% is a financially meaningful reference point. It is **not retained as a formula**. The surplus ratio itself (`surplus / income`) is a cleaner, evidence-neutral measure.
- **Taxes:** Including taxes is conceptually sound — taxes are a non-discretionary outgoing. However, individual tax computations are complex and situation-specific. In practice, the engine should accept either net income (post-tax) or gross income with a tax flag — with appropriate handling for each. Missing tax data should reduce confidence rather than block assessment.

**Surplus Ratio thresholds for capacity levels:**  
`TBD — EMPIRICAL CALIBRATION REQUIRED`

---

## 9. Income Stability Treatment

### Recommended Approach

Income stability belongs in Risk Capacity as a **modifier on reserve requirements**, not as a standalone scored dimension.

**Conceptual distinctions (in order of income predictability):**
1. **Stable Salaried (government/established private sector):** Low interruption risk; lower required reserve.
2. **Stable Salaried (general private sector):** Moderate interruption risk; standard required reserve.
3. **Variable / Bonus-Dependent:** Moderate-high interruption risk; reserve requirement increases.
4. **Self-Employed / Professional Practice:** Higher interruption risk; higher required reserve.
5. **Irregular / Project-Based / Contractual:** High interruption risk; highest required reserve.
6. **Unknown / Not Declared:** Cannot assess; reduce confidence in capacity assessment.

**Implementation rule:** Income stability adjusts the `required_coverage_months` in the Reserve Adequacy Ratio. It does not create a separate capacity tier of its own.

**Provenance requirement:** Employment type must come from user-declared profile data. Do not infer employment risk from investment behavior or portfolio patterns.

---

## 10. Dependents & Household Obligations

### Recommended Approach

Dependents do not independently create a capacity factor. They amplify existing risks:

1. **Higher essential expense floor:** More dependents typically mean higher non-discretionary monthly spending.
2. **Higher emergency reserve requirement:** More dependents increase the probability and magnitude of emergency expense events.
3. **Higher income vulnerability impact:** Loss of income has more severe consequences in households with dependents.

**Implementation:** Dependents modify the `required_coverage_months` in the Reserve Adequacy calculation. The direction is clear (more dependents → higher requirement); the exact magnitude is `TBD — EMPIRICAL CALIBRATION REQUIRED`.

**What is NOT included:** An arbitrary per-dependent monetary deduction from income or an arbitrary per-dependent "debt weight." These would introduce false precision.

---

## 11. Existing Assets Treatment

### Recommended Approach

Existing assets can only contribute to Risk Capacity through **emergency liquidity**, and only if the assets are:
- Genuinely liquid (accessible within 1–3 business days without significant loss);
- Not already pledged or committed;
- Not the primary investment portfolio itself (which is what is being analyzed for risk).

**Liquid assets that appropriately expand the reserve buffer:**
- Savings account balances
- Liquid mutual funds (overnight, liquid category)
- Unrestricted FDs / bank deposits with immediate access

**Assets that should NOT automatically increase capacity:**
- Real estate (illiquid; realization uncertain and costly)
- Long-term equity portfolio (cannot be liquidated during a downturn without realizing losses)
- Restricted FDs / insurance endowments with lock-in periods
- Provident fund / NPS (restricted withdrawals)
- Business assets / goodwill

**Edge-case asset classification (V1 — Conservative Treatment):**
> [!NOTE]
> **Phase F.2C.1 Audit Addition:** The following asset types are **excluded from emergency reserves in V1** (conservative binary exclusion). Future versions may apply liquidity haircuts rather than binary exclusion:
> - Short-duration debt funds (1–3 month duration): partially liquid but not as immediate as overnight/liquid funds.
> - Arbitrage funds: redemption subject to STCG within 12 months; tax friction reduces emergency utility.
> - Fixed Maturity Plans (FMPs): lock-in periods make them illiquid before maturity.
> - Sovereign Gold Bonds (SGBs): premature exit only through secondary market at variable price.
> - Overdraft against FD: a credit line, not a liquid asset — excluded from reserve classification.

**Belongs in Risk Capacity or Portfolio Context?** Liquid assets belong in Risk Capacity as an emergency reserve component. Total financial wealth belongs in Portfolio Context (a downstream layer).

---

## 12. Horizon and Liquidity Commitment in Risk Capacity

Risk Capacity **does** need to consider one aspect of time:

> **Near-term financial commitment:** If a material sum is needed within 12–18 months (child's school fees, home down payment), that capital cannot absorb market risk — it represents a **liquidity ring-fence** that reduces the effective risk-bearing pool.

This is distinct from the Goal Horizon engine (Phase F.6), which operates at the goal level. Here, the effect is:
- Near-term commitment → reduces effective investable capital → reduces the absolute capital loss an investor can tolerate while still being able to fund the commitment.

**Implementation:** Near-term commitment is a **binary or categorical flag** (commitment present / not present / amount known) that modifies the capacity assessment for the ring-fenced capital. It does not affect the core capacity tier calculation for remaining investable capital.

**Risk Capacity and Goal Horizon are separate constructs** — the horizon engine applies a ceiling downstream; Risk Capacity does not re-compute the horizon.

---

## 13. Missing Information Policy

**Governing principle:** Missing inputs must reduce confidence or trigger a bounded partial assessment. Missing ≠ zero. Missing ≠ conservative default.

### Recommended Behavior by Missing Input

| Missing Input | Effect | Rationale |
|---|---|---|
| `monthly_gross_income` | Cannot compute debt ratio or surplus ratio. Assessment produces `INSUFFICIENT_INFORMATION`. | Cannot normalize debt or compute surplus without income. |
| `monthly_fixed_expenses` | Cannot compute surplus. Debt assessment can still proceed partially. Confidence reduced. | Surplus computation is blocked; debt ratio still calculable. |
| `monthly_debt_servicing` | Assume no structured debt only if explicitly confirmed by user. If unknown, treat as unknown (not zero). Confidence reduced. | Zero debt assumption is unsafe — many investors have undisclosed debt. |
| `liquid_emergency_reserves` | Cannot assess reserve adequacy. Capacity ceiling defaults conservatively to reflect unknown reserve status. Confidence heavily reduced. | Unknown reserves cannot be presumed adequate. |
| `income_stability_type` | Use "unknown" category → required coverage months cannot be calibrated → use conservative reserve requirement. Confidence reduced. | Cannot make employment-risk assumptions without user declaration. |
| `financial_dependents_count` | Use zero dependents as a lower bound for reserve requirement, but flag confidence reduction. | Absence of declared dependents does not guarantee no dependents exist. |

### Recommended Missing-Data Architecture

```
MISSING DATA FLOW
    │
    ├── All critical inputs present → Full capacity assessment
    │
    ├── One input missing → Partial assessment with reduced confidence
    │       (confidence_score proportional to missing information severity)
    │       (capacity tier computed from available inputs only)
    │
    ├── Multiple inputs missing → INSUFFICIENT_INFORMATION for affected dimensions
    │       (partial assessment: conservative capacity tier from remaining inputs)
    │       (assessment_status = PARTIAL; capacity not upgraded beyond LOW from partial data)
    │
    └── Critical inputs missing (e.g., income) → INSUFFICIENT_INFORMATION
            (assessment_status = INSUFFICIENT_INFORMATION; no capacity tier returned)
            [DISTINCT from PARTIAL — no capacity tier is produced]
```

> [!NOTE]
> **Phase F.2C.1 Audit Clarification:** `PARTIAL` and `INSUFFICIENT_INFORMATION` are two distinct `assessment_status` states. A partial assessment (some inputs present) may conservatively produce a LOW or MODERATE tier. A fully missing critical input (e.g., no income declared) produces `INSUFFICIENT_INFORMATION` with no capacity tier — it does not default to any tier including LOW. These states must not be conflated in F.3 implementation.

**Progressive profiling:** Missing inputs at Tier 2 profiling trigger a prompt for the next visit, not an immediate block on using the platform.

---

## 14. Risk Capacity Scale Assessment

The existing five-level scale is appropriate:

| Level | Ordinal | Interpretation |
|---|---|---|
| `VERY_LOW` | 1 | Investor cannot sustain any meaningful capital loss without compromising obligations. |
| `LOW` | 2 | Investor can tolerate small, short-duration losses with existing reserves intact. |
| `MODERATE` | 3 | Investor has adequate reserves and surplus to sustain moderate drawdowns without behavioral force-sell. |
| `HIGH` | 4 | Investor has substantial reserves and surplus; can sustain significant drawdowns across market cycles. |
| `VERY_HIGH` | 5 | Investor has robust reserves, minimal debt, and strong surplus; can absorb extreme drawdowns without threat to obligations. |

**Do the five levels require numerical boundaries?** The levels require conceptual calibration criteria (what conditions correspond to each level). The exact numerical thresholds for those conditions are `TBD — EMPIRICAL CALIBRATION REQUIRED`.

**Continuous internal representation:** The engine may compute an internal continuous capacity indicator per dimension (e.g., Reserve Adequacy Ratio = 0.73) and map it to ordinal levels via calibrated thresholds. This supports gradual sensitivity to changing inputs without creating arbitrary tier-jump discontinuities in the output.

---

## 15. Financial Loss-Absorption Scenarios

These scenarios test whether the proposed architecture produces directionally sensible capacity outcomes:

| Scenario | Financial Profile | Expected Directional Outcome | Architecture Behavior |
|---|---|---|---|
| **A** | High stable income + high liquidity + low debt | **HIGH or VERY_HIGH** | All constraints minimal; no ceilings triggered |
| **B** | High income + high debt + low liquidity | **LOW or MODERATE** | Debt constraint and reserve constraint both active |
| **C** | Moderate income + strong reserves + low debt | **MODERATE or HIGH** | Reserve constraint satisfied; surplus adequate |
| **D** | Variable income + high reserves + low debt | **MODERATE** | Reserve requirement adjusted upward for income instability; reserve still adequate |
| **E** | Low surplus + substantial obligations | **VERY_LOW or LOW** | Surplus constraint and/or debt constraint active |
| **F** | Missing financial information | **INSUFFICIENT_INFORMATION** | Missing inputs → reduce confidence → conservative partial assessment |

All six scenarios produce directionally sensible results under the constraint-based architecture without requiring specific numerical thresholds to be calibrated now.

---

## 16. Sensitivity Requirements

The following monotonic relationships must hold:

| Input Change | Expected Capacity Direction | Rationale |
|---|---|---|
| Increasing debt burden (fixed income) | Capacity decreases or stays flat | Higher committed outgoings reduce resilience |
| Decreasing liquid reserves | Capacity decreases | Less financial buffer for market drawdowns |
| Increasing liquid reserves | Capacity increases or stays flat | Enhanced financial buffer |
| Increasing fixed expenses (fixed income, fixed reserves) | Capacity decreases | Less surplus; higher reserve-coverage denominator |
| Increasing sustainable surplus | Capacity increases or stays flat | More discretionary buffer available |
| Worsening income stability (salaried → self-employed) | Required reserve increases → capacity decreases if reserves don't grow | Higher interruption risk raises the required buffer |
| Adding dependents | Required reserve increases → capacity decreases unless reserves increase proportionally | Dependents amplify emergency expense shocks |

These sensitivity tests do **not** require specific numerical thresholds — they express directional constraints the model must satisfy.

---

## 17. Empirical Calibration Requirements

Risk Capacity calibration must NOT merely optimize for investment return outcomes. It calibrates the investor's **financial resilience** construct:

### A. Parameter Calibration
- What debt-to-income ratios correspond to which constraint levels in the Indian retail context?
- What reserve-to-expense coverage ratios have historically enabled investors to sustain SIPs through market drawdowns without forced liquidation?
- What surplus ratios correspond to meaningful capacity tiers?

**Data required:** RBI household finance survey data, AMFI/NSE SIP discontinuation rates by investor financial profile, retail credit bureau default rate statistics by income/debt quintile.

### B. Financial Methodology Validation
- Does the constraint-based architecture correctly rank investor financial resilience across known profiles?
- Does the lower-of-the-two rule correctly prevent high tolerance from overriding low capacity?

### C. Behavioral Validation
- Do investors classified as HIGH capacity actually sustain SIPs through market drawdowns, or do they discontinue despite measured capacity?

### D. Market Scenario Testing
- Does the capacity assessment remain meaningful across different market regimes (bull market, bear market, high-inflation environment)?

### E. Outcome Validation (Pre-production)
- Does the final capacity assessment correctly identify investors who need to reduce risk, versus investors who have stable financial foundations?

---

## 18. F.3 Input / Output Contract

This specifies what Phase F.3 must consume and produce. **This is a contract definition, not implementation.**

### INPUTS (from `FinancialCapacitySnapshot`)

```
Required Inputs:
  - monthly_gross_income: Optional[float]     — normalizing denominator for ratios
  - monthly_fixed_expenses: Optional[float]    — surplus computation component
  - monthly_debt_servicing: Optional[float]    — debt burden numerator
  - liquid_emergency_reserves: Optional[float] — reserve adequacy numerator
  - financial_dependents_count: Optional[int]  — reserve requirement modifier
  - income_stability_type: Optional[str]       — reserve requirement multiplier

Configuration Context (from versioned config, NOT hardcoded):
  - rule_version: str
  - methodology_version: str
  - debt_constraint_thresholds: dict           — PROVISIONAL (TBD)
  - reserve_coverage_thresholds: dict          — PROVISIONAL (TBD)
  - surplus_capacity_thresholds: dict          — PROVISIONAL (TBD)
  - stability_reserve_multipliers: dict        — PROVISIONAL (TBD)
  - dependent_reserve_adjustment: dict         — PROVISIONAL (TBD)
```

### OUTPUTS

```
RiskCapacityAssessment:
  - capacity_tier: RiskCapacityLevel           — VERY_LOW / LOW / MODERATE / HIGH / VERY_HIGH
  - assessment_status: str                     — ASSESSED / INSUFFICIENT_INFORMATION / PARTIAL
  - debt_constraint_level: str                 — severity of debt burden constraint
  - reserve_constraint_level: str              — severity of reserve inadequacy constraint
  - surplus_capacity_level: str                — severity of surplus limitation
  - binding_constraint: str                    — which dimension governs the final tier
  - confidence_score: float                    — [0.0, 1.0]; lower if inputs are missing
  - missing_inputs: List[str]                  — what data was absent from the assessment
  - explanation_tokens: List[str]              — factual reasons behind the outcome
  - methodology_version: str
  - rule_version: str
  - assessment_timestamp_utc: datetime
  - provenance: ProvenanceMetadata
```

---

## 19. Explainability Design

The engine must support user-facing explanations of the form:

> "Your risk capacity is **Low** because:"

Explanation tokens must be factual and based only on actual inputs. Examples:

- *"Your debt commitments account for a significant portion of your income, limiting available financial buffer."*
- *"Your emergency reserves cover a shorter period than recommended for your income profile, reducing your ability to sustain investments during a market downturn."*
- *"After essential expenses and debt obligations, your available monthly surplus is limited, constraining how much market volatility your finances can absorb."*
- *"We couldn't assess your full financial capacity because some information is missing. Completing your financial profile will give you a more accurate capacity assessment."*

**Explainability rules:**
1. Never mention numerical thresholds (e.g., "your DTI is 47%") in user-facing explanations — that adds technical noise.
2. Only cite factors actually present in the assessment.
3. Identify the binding constraint explicitly.
4. Where confidence is reduced due to missing information, say so clearly.

---

## 20. Governance Summary

### Approved Conceptual Principles
- Risk Capacity is an investor's objective financial ability to absorb portfolio losses without impairing essential obligations.
- Debt servicing burden is a genuine Risk Capacity constraint.
- Emergency reserve adequacy is a genuine Risk Capacity constraint.
- Sustainable surplus is a genuine Risk Capacity derived indicator.
- Income stability modifies the required reserve coverage level.
- Dependents modify the required emergency reserve coverage.
- Missing inputs must reduce confidence rather than silently default to zero or conservative assumptions.
- Hard capacity ceilings are conceptually justified for extreme financial conditions.
- The lower-of-the-two rule (Capacity, Tolerance) governs Effective Risk Alignment.

### Evidence-Supported Concepts
- Debt servicing beyond a material threshold of income impairs household financial resilience: **FPSB India + RBI Household Finance Report 2017** (concept supported; thresholds TBD).
- Emergency reserves of 3–6 months (salaried) and 6–12 months (self-employed) represent recognized professional planning benchmarks: **FPSB India** (directly supported).
- Constraint-based architecture (bottleneck model) avoids compensatory scoring dangers: **standard fiduciary design principle**.

### Provisional Parameters (All Require Calibration)
- Numerical thresholds for debt burden constraint levels.
- Numerical thresholds for reserve adequacy constraint levels.
- Surplus ratio thresholds for capacity levels.
- Income stability reserve multipliers.
- Dependent-count reserve adjustment formula.
- Final mapping from constraint combination to ordinal capacity tier.

### Areas Where Evidence Is Insufficient
- Exact numerical debt-to-income thresholds for Indian retail investor risk capacity.
- Quantitative relationship between surplus ratio and capacity tier.
- Dependent-count adjustment formula.

---

## 21. Final Governance Review Answers

1. **Is the recommended architecture financially defensible?** Yes — constraint-based bottleneck with no arbitrary weights; hard ceilings only for extreme conditions; all concepts grounded in regulatory or academic source.
2. **Does it avoid double-counting?** Yes — surplus ratio absorbs income/expenses/debt as a single derived indicator; no redundant weighting of sub-components.
3. **Does it avoid arbitrary weights?** Yes — constraint architecture eliminates weighting. Thresholds will require calibration but can be calibrated independently.
4. **Does it avoid arbitrary thresholds?** Yes — thresholds are explicitly marked `TBD — EMPIRICAL CALIBRATION REQUIRED`; not invented.
5. **Does it preserve Risk Capacity vs Risk Tolerance separation?** Yes — capacity is financial; tolerance is behavioral; they meet only in the Lower-of-Two Rule (Phase F.5).
6. **Does it preserve Risk Capacity vs Goal Horizon separation?** Yes — horizon ceilings applied downstream (Phase F.6); not conflated with capacity.
7. **Does it handle missing data safely?** Yes — missing inputs reduce confidence or trigger `INSUFFICIENT_INFORMATION`; never default to zero.
8. **Does it preserve explainability?** Yes — binding constraint is explicit; user-facing explanation tokens are factual.
9. **Can F.3 be implemented without inventing additional financial rules?** Yes — all financial thresholds are in the configuration layer, not the engine logic.
10. **Which exact parameters remain TBD?** All numerical thresholds for the three constraint dimensions, the stability reserve multipliers, and the dependent adjustment formula.
11. **Does Dimension 3 (surplus) create a double-count with Dimension 1 (debt)?** Partially — the surplus ratio is algebraically dependent on the debt burden ratio. D3 serves as a combined cash-flow verification check, not a fully orthogonal constraint. F.3 must document this dependency. The architecture is retained with this clarification.

---

## 22. Household Context Convention (V1)

> [!IMPORTANT]
> **Phase F.2C.1 Audit Requirement:** This convention must be documented before F.3 implementation begins.

### V1 Convention

All declared financial inputs to the Risk Capacity Engine are treated as **household-level aggregates**, representing the investor's total household financial position. The "investor" for the purposes of data collection is defined as the household head or primary account holder, and their declared figures represent the full household:

| Input Field | V1 Interpretation |
|---|---|
| `monthly_gross_income` | Total household gross income (all earners) |
| `monthly_fixed_expenses` | Total household fixed essential expenses |
| `monthly_debt_servicing` | Total household debt servicing obligations (all joint and individual loans) |
| `liquid_emergency_reserves` | Total household liquid emergency reserves (jointly and individually held) |
| `financial_dependents_count` | Total number of financial dependents in the household |
| `income_stability_type` | Primary earner's income stability category |

### Known V1 Limitation

V1 does not support explicit individual vs. household input separation. A dual-income household's second earner income, individual expenses, or individual debt are declared as part of the household aggregate. This is a known simplification.

**Future version requirement:** A V2 profile should support explicit individual vs. household input declaration with corresponding calculation adjustments (e.g., individual risk capacity vs. household risk capacity for joint investment decisions).

---

## 23. F.3 Startup Mode Policy

> [!IMPORTANT]
> **Phase F.2C.1 Audit Requirement:** This policy must be implemented in F.3. Refusing startup unconditionally in all modes is unnecessarily restrictive for calibration and testing.

### Three-Mode Startup Policy

The F.3 Risk Capacity Engine reads a `STARTUP_MODE` configuration key and applies mode-specific parameter validation:

```
STARTUP_MODE: PRODUCTION
  → All required financial threshold parameters MUST be present and validated in config.
  → Missing parameter → engine startup error. No assessment permitted.
  → Outputs carry no special tag.

STARTUP_MODE: RESEARCH
  → Required parameters validated as present (may be provisional placeholders).
  → Engine runs normally but output is tagged: assessment_context = "RESEARCH_MODE_NOT_FOR_PRODUCTION".
  → Warning logged for every assessment produced.
  → Intended for calibration research and methodological sensitivity testing.

STARTUP_MODE: TEST
  → Threshold validation is bypassed; tests inject arbitrary threshold sets.
  → All outputs tagged: assessment_context = "SYNTHETIC_TEST_DATA".
  → Must never be used outside automated test environments.
```

### Governance Rule

A production deployment **must never** be configured with `STARTUP_MODE: RESEARCH` or `STARTUP_MODE: TEST`. The deployment configuration must be validated at startup to enforce this.
