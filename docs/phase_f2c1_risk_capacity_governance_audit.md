# Phase F.2C.1 — Risk Capacity Methodology Governance Audit

**Phase:** Phase F.2C.1 — Governance & Methodology Audit  
**Date:** 2026-09-09 UTC  
**Final Status:** `PHASE F.2C.1 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Independent governance audit of Phase F.2C Risk Capacity methodology. **Zero production Python code modified.**

---

## 1. Executive Summary

This audit independently examines every material architectural claim, formula, governance label, and structural decision in the Phase F.2C Risk Capacity methodology. Its purpose is to identify any claim that has been over-stated as `APPROVED` when the actual evidence supports only `PROVISIONAL`, and to confirm where the methodology is sound before F.3 implementation begins.

### Key Findings

1. **Hard-Ceiling Governance Claim (§5, §RC-ARCH-03):** The label `APPROVED` is over-stated. The *general principle* that severe financial distress caps capacity is supported. The *specific implementation detail* — that each constraint dimension independently imposes a ceiling via a min() integration rule — is a product architecture choice, not an externally established principle. Status corrected to `PROVISIONAL`.

2. **Debt Denominator — Gross Income (§6, RC-D1-02):** The use of gross income is a reasonable and pragmatic choice, but the justification offered ("more verifiable and stable") is a product-design rationale, not an externally established financial rule. The FPSB India guidance cites net monthly income for the DTI guidance range. The denominator choice requires explicit documentation as `PROVISIONAL`. Status corrected to `PROVISIONAL`.

3. **Surplus Ratio as Third Constraint Dimension (§8, RC-D3-01):** The surplus ratio formulation is sound and avoids double-counting when used as a *derived indicator*. However, treating it as a third independent constraint *dimension* in the min() integration rule creates a structural double-count: the surplus ratio already incorporates debt and expenses, which are also independently assessed in Dimensions 1 and 2. The surplus ratio is better positioned as a *verification check or secondary constraint*, not an equal co-constraint alongside Dimensions 1 and 2. This is a genuine architectural finding.

4. **Reserve Adequacy Formula Denominator (§7, RC-D2-01):** The formula uses `essential_monthly_expenses × required_coverage_months` as the denominator. This is sound. The stability multiplier should modify `required_coverage_months`, not multiply the entire denominator independently — the methodology is correct on this point; it needs explicit clarification in the document.

5. **Multiplier Combination (Stability + Dependents):** Combining both a stability multiplier and a dependent modifier as additive adjustments on `required_coverage_months` is analytically appropriate and avoids the exponential compounding risk that would arise from multiplicative combination. The methodology correctly treats them as additive adjustments. This is confirmed `APPROVED`.

6. **Confidence Separation:** RC-INT-02 and RC-INT-03 are confidence parameters, not capacity parameters. The methodology is correct that confidence must not affect the underlying capacity calculation — the confidence score is an output field, not an input to the capacity tier determination. This is confirmed `APPROVED`.

7. **Household Context Gap:** The current data contract does not distinguish individual vs. household income, individual vs. household debt, or shared vs. individually-held reserves. This is a genuine data contract gap that needs to be documented before F.3 implementation. It does not require a revised contract during this audit.

8. **F.3 Startup Behavior:** Refusing startup in all modes is unnecessarily restrictive. A three-mode startup policy is more appropriate and safer.

9. **Risk Capacity vs. Affordability Boundary:** The methodology does not conflate these. The surplus ratio's role must be clarified explicitly as a *capacity-relevant resilience indicator* (can SIPs be sustained during stress?) rather than an affordability ceiling (how much can be invested optimally?). The distinction is present but should be made more explicit.

10. **No genuine contradictions** were found with PRODUCT_SPEC.md, ARCHITECTURE.md, or prior phase governance decisions.

---

## 2. Audit Methodology

Documents read in full before any findings were recorded:
1. `PRODUCT_SPEC.md` ✓
2. `ARCHITECTURE.md` ✓
3. `docs/phase_f_suitability_risk_alignment_specification.md` ✓
4. `docs/phase_f1_1_financial_rule_governance_correction.md` ✓
5. `docs/phase_f2a_financial_rule_research.md` ✓
6. `docs/phase_f2a_financial_rule_evidence_matrix.md` ✓
7. `docs/phase_f2b_financial_evidence_claim_audit.md` ✓
8. `docs/phase_f2c_risk_capacity_methodology.md` (all 614 lines) ✓
9. `docs/phase_f2c_risk_capacity_parameter_register.md` ✓
10. `docs/phase_f2c_risk_capacity_calibration_plan.md` ✓
11. `models/investor_profile.py` ✓
12. `docs/documentation_traceability_matrix.md` ✓

Findings are classified as:
- `GENUINE FINDING` — A real governance, mathematical, or architectural issue.
- `CONFIRMED SOUND` — The audit finds no issue; the methodology is well-reasoned.
- `CLARIFICATION NEEDED` — The methodology is correct, but the documentation is ambiguous or under-specified.

---

## 3. Finding 1 — Hard Ceiling Governance Label (RC-ARCH-03)

### Current Claim
> "Hard Capacity Ceilings for Extreme Conditions — `APPROVED` — CONCEPTUAL — Fiduciary irreversibility of forced liquidation principle"

### Audit Question
Does the evidence support **(A)** the general principle, or **(B)** the specific architectural implementation that each constraint dimension independently imposes a hard capacity ceiling via min() integration?

### Analysis

**General principle (A):** The claim that severe financial conditions — extreme debt burden or critical reserve deficiency — cap an investor's risk capacity is directly supported:
- FPSB India guidelines establish that reserve adequacy is a prerequisite for taking on market-linked investment risk.
- RBI HFC Report 2017 establishes that DSR >50% leaves households severely vulnerable to income shocks.
- Phase F.2B audit correctly classifies RC-01 as `PARTIALLY SUPPORTED` (concept supported; thresholds `PROVISIONAL`).
- The fiduciary principle that forced liquidation converts paper losses to permanent losses is a recognized and defensible concept.

**Specific architectural implementation (B):** The claim that the correct mechanism for implementing hard ceilings is precisely "each constraint dimension independently imposes a ceiling via min()" is not established by any external source. This is a *product architecture choice*. It is well-reasoned (see Finding 5), but it is the product team's design decision. Alternative architectures (hierarchical constraints, hybrid baseline + hard-cap) are also conceptually justifiable.

### Finding
`GENUINE FINDING — GOVERNANCE OVER-STATEMENT`

The general principle (A) is `APPROVED CONCEPT`. The specific implementation (B) — that each dimension independently applies a hard ceiling integrated via min() — is a `PROVISIONAL` product architecture choice.

### Required Correction
- RC-ARCH-03 status changes from `APPROVED` → `PROVISIONAL`.
- The methodology text must clarify: the *concept of hard capacity ceilings* is approved; the *min() bottleneck as the specific implementation mechanism* is provisional pending architectural validation.
- The general fiduciary principle of reserve/debt-as-capacity-constraint remains `APPROVED CONCEPT`.

---

## 4. Finding 2 — Debt Denominator: Gross vs. Net Income (RC-D1-02)

### Current Claim
> "Debt Burden: Use Gross (not Net) Income — `APPROVED` — CONCEPTUAL — Gross income is more verifiable and stable than net"

### Audit Question
Is the use of gross income (rather than net or disposable income) adequately supported as the denominator for the debt burden ratio?

### Analysis

**The FPSB India guidance** (Phase F.2B, Audit 1) explicitly states: "Financial planners should recommend capping total debt servicing (EMIs) within 40% to 50% of **net** monthly income." This is the primary external source establishing the debt burden concept. The source uses net income, not gross income.

**The RBI HFC Report 2017** uses DSR (Debt Service Ratio) expressed relative to household income, but does not specify gross or net in the context of individual investor capacity rules.

**Standard financial planning practice internationally** varies:
- Gross income DTI is used by mortgage lenders (because gross income is verifiable from salary slips and is lender-facing).
- Net/disposable income is more appropriate for personal financial resilience assessment because tax obligations are non-discretionary — they directly reduce the cash available to service debt and absorb losses.

**The product's own surplus formula** uses: `(gross_income − taxes − fixed_expenses − debt) / gross_income` — explicitly deducting taxes before computing surplus. If taxes are recognized as non-discretionary in the surplus formula, there is an inconsistency in treating gross income as the appropriate denominator for the debt burden ratio, where taxes are not accounted for.

**Pragmatic argument for gross income:** Gross income is more consistently user-declarable without requiring tax computation. Net income requires knowledge of applicable tax bracket, which varies by investor circumstance.

### Finding
`GENUINE FINDING — DENOMINATOR CHOICE NEEDS PROVISIONAL STATUS`

The denominator choice (gross vs. net) is a product design decision. The primary external source (FPSB India) uses net income for the analogous guidance. The gross income choice is pragmatically defensible but is not externally established — it contradicts the denominator used in the source that supports the debt burden concept.

### Required Correction
- RC-D1-02 status changes from `APPROVED` → `PROVISIONAL`.
- The methodology must document: "FPSB India DTI guidance uses net income; this engine uses gross income for verifiability. This is a product design decision, not an externally validated choice. The denominator should be empirically validated against the reserve adequacy and surplus formulations for consistency."
- No change to the formula structure — the gross income choice may be retained as a provisional default.
- RC-D1-02 calibration note added: validate whether gross vs. net denominator meaningfully affects the constraint tier assignment across representative Indian household profiles.

---

## 5. Finding 3 — Surplus Ratio as Third Independent Constraint Dimension

### Current Claim
> "Sustainable Surplus Ratio = `(income − taxes − expenses − debt) / income` — used as DIMENSION 3 in the min() integration"

### Audit Question
Does treating the surplus ratio as a third independent constraint dimension alongside Dimensions 1 (Debt) and 2 (Reserve) create a structural double-count?

### Analysis

**Mathematical relationship between the three dimensions:**

Dimension 1: `debt_servicing / income`  
Dimension 2: `liquid_reserves / (expenses × required_months)`  
Dimension 3: `(income − taxes − expenses − debt) / income` = `1 − tax_rate − expense_rate − debt_burden_ratio`

Note the algebraic dependency:
```
Surplus Ratio ≈ 1 − expense_rate − Debt Burden Ratio (ignoring taxes for simplicity)
```

This means Dimension 3 (surplus ratio) is **algebraically dependent on Dimension 1 (debt burden ratio)**. If Dimension 1 imposes a ceiling due to high debt burden, Dimension 3 will *simultaneously* impose a ceiling from the same underlying cause (the high debt). The min() integration then "sees" the debt constraint twice — once through D1 and once through D3.

**Is this necessarily problematic?**

For the *min()* integration rule: Yes. The min() should ideally reflect three genuinely independent constraint dimensions. If D1 and D3 are mathematically correlated, the min() does not provide three independent perspectives — it provides two (debt constraint, reserve adequacy) with one repeated in algebraically dependent form.

**Is the surplus ratio valueless?** No. The surplus ratio provides additive information in two genuine scenarios that D1 and D2 alone do not fully capture:
1. An investor with moderate debt burden but also very high fixed expenses (large household, high cost of living) may have near-zero surplus even when D1 and D2 appear acceptable. D3 catches this.
2. A tax event or income reduction that simultaneously pressures surplus without directly changing debt or reserve balances.

**Recommended architectural adjustment:** The surplus ratio should be retained, but its role should be clarified as a *verification constraint* or *secondary constraint* that can further constrain the capacity result from D1 and D2, rather than being labeled a fully independent co-equal constraint dimension. The practical outcome of the architecture does not need to change — the surplus ratio still imposes a capacity constraint — but the document should clearly state that D3 is not fully orthogonal to D1 and should be interpreted as a combined cash-flow check.

### Finding
`GENUINE FINDING — ARCHITECTURAL CLARITY NEEDED`

The surplus ratio is not fully independent of the debt burden ratio. Its use as a third independent dimension in the min() integration should be clarified. The architecture remains sound, but the document over-states the independence of the three dimensions. The surplus ratio's role should be explicitly documented as a dependent derived check that catches combined cash-flow stress scenarios not captured by D1 and D2 alone.

### Required Correction
- The methodology document must clarify that D3 (surplus ratio) is mathematically dependent on D1 inputs and serves as a combined cash-flow verification, not a fully orthogonal constraint.
- RC-D3-01 governance status remains `APPROVED` for the formula structure, but the architectural role description must be clarified.
- No change to the actual formula or the min() integration rule. The behavior is sound; the labeling needs clarity.

---

## 6. Finding 4 — Reserve Formula Denominator Clarification

### Current Claim
> "Reserve Adequacy Ratio = `liquid_emergency_reserves / (essential_monthly_expenses × required_coverage_months)`"
> The stability multiplier modifies `required_coverage_months`.

### Audit Question
Should the stability multiplier multiply the entire denominator, or only `required_coverage_months`? Should dependents also modify the same coverage months?

### Analysis

**The formula:** `reserves / (expenses × required_months)` means: "how many multiples of (required monthly coverage) do I have?"

**Stability modifier on required_months:** Correct. Income stability increases the *required number of months of coverage*, not the size of the monthly expense. A self-employed investor does not suddenly have higher monthly expenses — they need a longer runway because income interruption may last longer. Modifying `required_months` is the correct operationalization.

**Dependents modifier on required_months:** Similarly appropriate. More dependents do not necessarily raise the exact monthly expense used in the formula (that is already captured in declared expenses), but they increase the *probability and magnitude* of emergency expense shocks, which justifies a longer required buffer. Modifying `required_months` is again the correct target.

**Additive vs. multiplicative combination:**
- `required_months = base_months + stability_addition + dependent_addition` (additive) is appropriate.
- `required_months = base_months × stability_multiplier × dependent_multiplier` (multiplicative) would compound the effects exponentially — a self-employed investor with 4 dependents could face a required coverage so high that it becomes impossible to achieve, which is not calibrated to real financial risk.
- Additive combination is the more defensible choice.

**Risk of double-counting via reserve formula:** The denominator `essential_monthly_expenses` captures the declared expense level. If dependents are already reflected in the declared monthly expenses, adding a dependent modifier to required months creates a mild upward bias (dependents captured twice: once in expenses, once in the months multiplier). This is a minor and acceptable conservatism given that declared expenses may not fully reflect emergency expense shocks from dependents. It should be documented.

### Finding
`CLARIFICATION NEEDED — METHODOLOGY IS SOUND, ADDITIVE COMBINATION IS CORRECT`

The methodology's approach (stability + dependents modify `required_coverage_months` additively) is the correct operationalization. A clarification note should be added to acknowledge that declared expenses already partially capture dependent costs, and that the dependent months-modifier provides an additional buffer for unexpected emergency shocks — which is intentional conservatism, not double-counting.

### Required Correction
- No change to the methodology or formula.
- Add a clarification note to §7: "The additive combination of stability_addition and dependent_addition on required_coverage_months is the intended structure. The dependent modifier captures emergency shock exposure not fully reflected in declared monthly expenses."

---

## 7. Finding 5 — Bottleneck / Min() Architecture Assessment

### Audit Question
Is the min() bottleneck architecture preferable to weighted averaging, multiplicative scoring, hierarchical constraints, or a hybrid model? Does it create undesirable discontinuities?

### Analysis

**Weighted averaging:** Already rejected in the methodology — requires arbitrary weight justification; compensatory scoring is unsafe (high reserves do not cancel extreme debt burden). This rejection is correct.

**Multiplicative scoring:** Would compound the effects of multiple poor dimensions exponentially, creating extreme sensitivity to individual borderline inputs. More opaque than min(). Less justified than min() for a conservatism-oriented capacity assessment. Not recommended.

**Hierarchical constraints:** Could be structured as: reserve adequacy is the first-priority constraint, debt burden is secondary, surplus is tertiary. This is a valid alternative that imposes constraints in order of severity/importance rather than treating all three as equally binding. However, defining the hierarchy would require justifying the priority order, which is also an empirical calibration requirement.

**Hybrid (baseline + hard constraints):** Valid as an enhancement. A baseline from one primary dimension with hard overrides from others is compatible with the current architecture and adds nuance for borderline cases.

**Min() architecture evaluation:**

*Discontinuity risk:* Yes — the min() creates a discontinuity where a single dimension crossing a threshold boundary causes a sudden tier jump. For example, if reserve adequacy is just below a threshold, the entire capacity tier drops regardless of strong debt and surplus positions.

*Mitigation:* The use of internal continuous ratios (rather than directly classifying into discrete levels before applying min()) partially mitigates this. If each dimension computes a continuous score and the min() operates on continuous scores before discretization, the discontinuity is reduced. The methodology's statement that "the engine may compute an internal continuous capacity indicator per dimension" (§14) is a key architectural safeguard.

*Conservatism alignment:* For a fiduciary suitability engine, conservatism is appropriate. The min() aligns with PRODUCT_SPEC.md §2.4 ("Low confidence means insufficient evidence, not necessarily poor quality") and the general principle that erring on the side of caution in capacity assessment is preferable to erring on the side of overconfidence.

*Alternative — "sufficient evidence for upgrade requires all dimensions to be adequate":* This is effectively what min() implements. It requires all dimensions to be above threshold before upgrading capacity, which is more conservative but also more transparent to explain.

### Finding
`CONFIRMED SOUND — WITH CLARIFICATION ON CONTINUOUS INTERMEDIATE REPRESENTATION`

The min() bottleneck architecture is the most defensible choice for a fiduciary capacity engine at this stage of development. Its conservatism aligns with product principles. Discontinuities are mitigated by using continuous intermediate ratios before final tier assignment. The architecture label should remain but its status (see Finding 1) should be `PROVISIONAL` at the implementation level.

**Governance recommendation:** Architecture remains RECOMMENDED. RC-ARCH-01 and RC-INT-01 remain appropriate, with status refined as noted in Finding 1.

---

## 8. Finding 6 — Reserve Multiplier Combination (Stability + Dependents)

### Audit Question
Should stability and dependent modifiers be additive, multiplicative, sequential/contextual, or replaced by direct expense/obligation data?

### Analysis (per Finding 4 conclusion)
- **Additive** is appropriate — avoids compounding conservatism exponentially.
- **Multiplicative** would be excessive conservatism for combined high-stability-risk + high-dependent profiles.
- **Sequential/contextual** (apply one only if the other condition is met) adds complexity without benefit.
- **Replacing with direct expense data:** Ideally, if all emergency expenses are captured in declared expenses, the dependent modifier is redundant. However, declared expenses typically represent regular monthly spending, not one-off emergency costs. The dependent modifier captures emergency cost probability not reflected in regular declared expenses.

**Current formula structure (RC-D2-05 is TBD):** Correct approach — the additive combination structure is sound; the exact magnitudes remain TBD.

### Finding
`CONFIRMED SOUND — ADDITIVE COMBINATION IS APPROPRIATE`

The additive structure for reserve modifiers is the correct architecture. Exact magnitudes remain TBD (empirical calibration required). RC-D2-05 remains `TBD`.

---

## 9. Finding 7 — Household Context Gap

### Audit Question
Does the current data contract adequately distinguish individual vs. household income/expenses/debt/reserves?

### Analysis

**Current `FinancialCapacitySnapshot` fields:**
- `monthly_gross_income` — not specified as individual or household
- `monthly_fixed_expenses` — not specified
- `monthly_debt_servicing` — not specified
- `liquid_emergency_reserves` — not specified

**Why this matters:**
- In a dual-income household, emergency reserves may be jointly held, not individually held by the "investor" as an individual.
- Debt may be jointly serviced (home loan with co-borrower), shared with spouse, or individually held.
- Fixed expenses in multi-income households may be shared, reducing the individual burden.
- Using individual income but household expenses (or vice versa) produces a misleading capacity assessment.

**Example:** An investor declares ₹1L/month gross income. If their spouse contributes ₹80K/month and household expenses are declared at ₹90K/month (for the whole household), using only the individual income with full household expenses drastically underestimates surplus.

**Is this a blocking issue for F.3?** Not necessarily. The initial implementation can define a clear convention (all inputs are household-level by default, with the investor as the declared household head for the assessment), documented as a constraint of V1. The key requirement is that the convention is *explicit and documented*, not silently assumed.

### Finding
`GENUINE FINDING — DATA CONTRACT CONVENTION GAP`

The current data contract does not explicitly specify whether inputs represent individual or household-level values. This must be documented before F.3 implements logic that computes ratios from these inputs.

### Required Action
- Document in the Phase F.3 implementation that V1 treats all declared financial inputs as household-level aggregates (the declared income, expenses, debt, and reserves represent the investor's total household financial position, not individual figures).
- Flag this as a known limitation: a future version should support explicit individual vs. household input separation with corresponding calculation adjustments.
- No change to the data contract during this audit.

---

## 10. Finding 8 — Existing Assets Classification

### Audit Question
Could any asset categories be incorrectly treated as emergency reserves?

### Analysis

The methodology (§11) explicitly lists:
- **Correctly included in reserves:** Savings accounts, liquid mutual funds (overnight/liquid category), unrestricted FDs.
- **Correctly excluded:** Real estate, long-term equity portfolio, restricted FDs, Provident Fund/NPS, business assets.

**Edge cases requiring attention:**

1. **Short-duration debt funds (1–3 month duration):** Not listed explicitly. These are liquid-ish but not as liquid as overnight/liquid funds. F.3 should treat them conservatively — either exclude them from emergency reserves or apply a liquidity haircut.

2. **Arbitrage funds:** Low-volatility, relatively liquid, but STCG applies on redemption within 12 months. Their emergency utility is partially impaired by tax friction. F.3 should document whether these are included or excluded.

3. **Fixed maturity plans (FMPs):** Lock-in periods make them illiquid before maturity. Should be explicitly excluded.

4. **Sovereign Gold Bonds (SGBs):** Have a lock-in period and premature exit only through secondary market at market price. Should be excluded from emergency reserves.

5. **Overdraft against FD:** Not a liquid asset, but creates an effective credit line. The methodology does not address credit line access as a reserve substitute. This is a known gap; for V1 it should be excluded (conservative treatment).

### Finding
`CLARIFICATION NEEDED — SOME ASSET CATEGORIES NEED EXPLICIT CLASSIFICATION`

The broad categories are correctly established. A clarification note should be added for edge cases (short-duration debt funds, arbitrage funds, FMPs, SGBs, OD facilities) before F.3 implementation to prevent ambiguous data collection instructions.

### Required Action
- Add a note to the methodology: "Short-duration debt funds, arbitrage funds, FMPs, SGBs, and credit lines are excluded from emergency reserve classification in V1 (conservative treatment). Future versions may apply liquidity haircuts rather than binary exclusion."

---

## 11. Finding 9 — Missing Data / Confidence Audit

### Audit Question
Is the missing-data approach preferable to imputation or conservative defaults? Is confidence kept separate from the capacity calculation itself?

### Analysis

**Missing ≠ Zero:** The methodology is correct. Setting missing inputs to zero creates systematically misleading assessments (e.g., assuming zero debt for an investor who hasn't declared their debt is far more dangerous than treating debt as unknown).

**Missing ≠ Conservative Default:** Also correct. A "conservative default" such as "assume minimum reserves" would silently assign a capacity level that wasn't earned by declared data.

**Confidence score as output, not input to capacity tier:** This is correctly designed. The capacity tier is determined from declared inputs only; the confidence score separately reflects how much of the declared picture is complete. These must remain strictly separate in F.3 implementation.

**One potential risk in RC-INT-02 / RC-INT-03:** If confidence parameters were used in F.3 to modify the capacity *tier* (rather than only the confidence *output*), confidence would contaminate the capacity calculation. The audit confirms this is *not* the current design — confidence is only an output field. F.3 must maintain this separation explicitly: the capacity tier computation must never read the confidence score as an input.

**Multiple missing inputs → "capacity not upgraded beyond LOW":** This specific behavior in the methodology (§13) is a policy decision. It prevents an investor with no declared financial information from receiving a HIGH or VERY_HIGH capacity assessment. This is appropriate conservatism. However, it should be clearly labeled as a safety policy, not a financial rule. The capacity is `INSUFFICIENT_INFORMATION` when inputs are too sparse — not automatically `LOW`. The "not upgraded beyond LOW" language should be clarified to mean the conservative fallback for a *partial* assessment (some inputs present, some absent), not a substitute for genuine assessment.

### Finding
`LARGELY CONFIRMED SOUND — ONE CLARIFICATION ON "NOT UPGRADED BEYOND LOW" LANGUAGE`

The missing-data architecture is sound. One clarification: the "capacity not upgraded beyond LOW" statement in §13 should be distinguished from the `INSUFFICIENT_INFORMATION` state. Partial assessments may conservatively return LOW; complete-missing-input cases should return `INSUFFICIENT_INFORMATION`. These are two distinct states.

### Required Action
- Clarify in methodology §13: partial assessments (some inputs known) conservatively cap at `LOW` or `MODERATE` based on available information; fully missing critical inputs produce `INSUFFICIENT_INFORMATION` rather than any capacity tier. These are distinct states.

---

## 12. Finding 10 — Audit of All 13 TBD Parameters

### Analysis by Parameter

| Param ID | Parameter | Genuinely Required? | Type | F.3 Without Value? | Validation Required |
|---|---|---|---|---|---|
| RC-D1-04 | Debt: low constraint threshold | Yes — needed to classify debt ratio into constraint levels | Empirical calibration | Yes — as configurable stub | Empirical: RBI/FPSB DTI research |
| RC-D1-05 | Debt: moderate constraint threshold | Yes | Empirical calibration | Yes — as configurable stub | Empirical |
| RC-D1-06 | Debt: high constraint threshold | Yes | Empirical calibration | Yes — as configurable stub | Empirical |
| RC-D1-07 | Debt: constraint → ceiling mapping | Yes — maps debt severity to capacity ceiling | Product rule | Yes — as configurable stub | Layer 3 (cross-profile consistency) |
| RC-D2-04 | Reserve: variable income min months | Yes — needed for the variable-income category | Empirical calibration | Yes — as configurable stub | Empirical: income interruption frequency data |
| RC-D2-05 | Reserve: dependent adjustment | Yes — needed when dependents > 0 | Empirical calibration | Yes — as configurable stub (0 if no dependents) | Empirical: household emergency expense data |
| RC-D2-06 | Reserve: adequacy → ceiling mapping | Yes | Product rule | Yes — as configurable stub | Layer 3 |
| RC-D3-03 | Surplus: adequate threshold | Yes — needed to classify surplus ratio | Empirical calibration | Yes — as configurable stub | Empirical: financial stress data |
| RC-D3-04 | Surplus: limited threshold | Yes | Empirical calibration | Yes — as configurable stub | Empirical |
| RC-D3-05 | Surplus: thin/zero threshold | Yes — key boundary for VERY_LOW | Empirical calibration | Yes — as configurable stub | Empirical |
| RC-IS-02 | Stability → reserve multiplier | Yes — needed for non-salaried investors | Empirical calibration | Yes — as configurable stub | Empirical: income interruption frequency |
| RC-INT-02 | Confidence reduction per missing input | Yes — but is a confidence rule, not a capacity rule | Product design | Yes — as configurable stub | Layer 1/Layer 2 testing |
| RC-INT-03 | Confidence floor for partial assessment | Yes — but is a confidence rule, not a capacity rule | Product design | Yes — as configurable stub | Layer 1/Layer 2 testing |

### Critical Distinction: RC-INT-02 and RC-INT-03

These are confidence parameters, not Risk Capacity parameters. Their values must never influence the capacity tier computation. In F.3:
- The capacity tier is computed exclusively from declared financial inputs and calibrated thresholds.
- RC-INT-02 and RC-INT-03 are applied only *after* the capacity tier is determined, to set the `confidence_score` output field.
- A missing input lowers confidence; it does not change the computed capacity tier (it may produce `INSUFFICIENT_INFORMATION` if the input was critical, but that is an `assessment_status`, not a capacity tier modification).

### Finding
`CONFIRMED — ALL 13 TBD PARAMETERS ARE GENUINELY REQUIRED`

All 13 TBD parameters are necessary. F.3 can be implemented without their values by treating them as mandatory config stubs. RC-INT-02 and RC-INT-03 are correctly classified as confidence rules and must not influence the capacity tier calculation.

---

## 13. Finding 11 — F.3 Startup Behavior

### Current Claim
> "The engine must refuse startup if TBD parameters are absent from config."

### Audit Question
Is refusing startup in all modes the safest and most practical architecture?

### Analysis

Three distinct operating modes exist:

**Mode A — Production:** Must never proceed with missing or default-invented parameters. The engine should refuse to run a capacity assessment if any required financial threshold parameter is absent. Refusing startup (or refusing to execute assessments, which is functionally equivalent for a library) is correct here.

**Mode B — Calibration / Research Mode:** Researchers need to run the engine with placeholder or partial threshold sets to observe directional sensitivity. Refusing startup blocks this work. A safer approach: the engine can operate in research mode with a clear output flag (`assessment_context: RESEARCH_MODE_NOT_FOR_PRODUCTION`) and explicit logging that the results are not production-valid.

**Mode C — Test Mode:** Unit and integration tests (Layer 1 and Layer 2) must be able to inject arbitrary thresholds without being blocked by startup validation. Test mode must clearly label all outputs as synthetic.

### Recommended F.3 Startup Policy

```
STARTUP_MODE config key:
  PRODUCTION:   → All required parameters MUST be present and validated.
                  Missing parameter → engine startup error. No assessment permitted.
  RESEARCH:     → Required parameters validated as present (may be provisional/placeholder).
                  Assessment output tagged RESEARCH_MODE. Warning logged.
  TEST:         → Threshold validation bypassed. Test assertions in tests.
                  Output tagged SYNTHETIC_TEST_DATA.
```

This is safer than a binary refuse/allow because it:
- Prevents production use with missing thresholds.
- Allows calibration research to proceed.
- Allows test infrastructure to inject controlled thresholds.

### Finding
`GENUINE FINDING — STARTUP POLICY REQUIRES THREE MODES`

The current "refuse startup if parameters absent" is correct for production but unnecessarily blocks calibration and testing. A three-mode startup policy is the recommended approach.

### Required Action
- Document the three-mode startup policy before F.3 implementation.
- F.3 must read a `STARTUP_MODE` flag from config and apply mode-specific validation accordingly.
- No code implemented in this audit.

---

## 14. Finding 12 — Risk Capacity vs. Affordability Boundary

### Audit Question
Does the methodology conflate Risk Capacity (ability to absorb loss) with Affordability (ability to contribute)?

### Analysis

**The surplus ratio serves both:**
- **As capacity indicator:** "Can this investor sustain SIP contributions during market stress without depleting reserves or missing obligations?" → Risk Capacity use.
- **As affordability indicator:** "What is the maximum SIP amount this investor can sustainably commit?" → Affordability use (Phase F.9, Sustainable Contribution Engine).

**The separation in the current methodology:**

The surplus ratio in the Risk Capacity engine answers: "Is there enough residual cash-flow that a portfolio loss wouldn't create immediate financial stress?" This is a *binary* or *ordinal* capacity check, not a precise monetary limit.

The Affordability engine (AF-01, established in Phase F.1.1) answers: "What is the maximum monthly contribution that fits within declared cash-flow?" This produces a specific monetary ceiling.

These are correctly separate. However, the methodology's §8 says the surplus ratio's role is "how much residual cash-flow exists after all obligations. An investor with thin surplus cannot sustain SIP contributions during market volatility." This language straddles the boundary — "sustain SIP contributions" is an affordability concept, not purely a capacity concept.

**Correct framing for Risk Capacity:** The surplus ratio's role in the Risk Capacity engine should be framed as: "Does this investor have sufficient financial buffer (beyond essential obligations) to withstand a period of investment loss without being forced into financial hardship?" This is a resilience check, not an affordability ceiling.

### Finding
`CLARIFICATION NEEDED — BOUNDARY IS SOUND, FRAMING NEEDS SHARPENING`

The methodology does not conflate Risk Capacity with Affordability in its architecture. However, the language in §8 leans toward affordability framing. The distinction should be made more explicit.

### Required Correction
- In the methodology §8, add a boundary clarification note: "In the Risk Capacity engine, the surplus ratio answers: 'Does this investor have sufficient financial resilience to absorb investment loss without incurring financial hardship?' This is distinct from the Affordability engine (AF-01), which answers: 'What is the maximum investment contribution this investor can sustainably make?' The surplus ratio in Risk Capacity is used as a resilience indicator, not as an affordability ceiling."

---

## 15. Finding 13 — Risk Capacity vs. Horizon Audit

### Audit Question
Is investment horizon silently being converted into Risk Capacity?

### Analysis

The methodology explicitly:
- Excludes investment horizon from Risk Capacity (§2, Factor I).
- Notes that horizon acts as a downstream ceiling in Phase F.6.
- Correctly distinguishes near-term financial commitments (which affect investable capital today) from goal horizons (which are assessed per goal downstream).

**Near-term commitment flag (§12):** This is the only time-related concept in the Risk Capacity engine. The treatment is sound: a near-term commitment reduces the effective investable capital that can bear market risk. This is not a horizon calculation — it is a liquidity ring-fence that reduces the capital pool for risk-taking. The horizon for the ring-fenced capital is implicitly "now" (or within 12–18 months), which justifies treating it in Risk Capacity rather than in the downstream horizon engine.

**Risk of creep:** If the near-term commitment flag began to influence the capacity *tier* directly (rather than only the ring-fenced capital pool), it would introduce horizon logic into capacity assessment. The methodology correctly prevents this by saying the flag "modifies the capacity assessment for the ring-fenced capital... [and] does not affect the core capacity tier calculation for remaining investable capital."

### Finding
`CONFIRMED SOUND — SEPARATION IS MAINTAINED`

Investment horizon is correctly excluded from Risk Capacity. The near-term commitment flag is correctly handled as a liquidity ring-fence on capital, not as a horizon-based capacity modifier.

---

## 16. Financial Reasonableness Scenario Tests

These verify directional behavior without manufacturing numerical scores.

| # | Profile | D1 (Debt) | D2 (Reserve) | D3 (Surplus) | Expected Direction | Architecture Behavior |
|---|---|---|---|---|---|---|
| 1 | High income, low debt, strong reserves, high surplus | No constraint | No constraint | Adequate | **HIGH / VERY_HIGH** | All three dimensions present no meaningful ceiling → high capacity output |
| 2 | High income, high debt, weak reserves | High constraint | Critical | Thin (debt consumes surplus) | **VERY_LOW / LOW** | D1 and D2 both impose severe ceilings; D3 also constrained by high debt → min() produces very low |
| 3 | Moderate income, low debt, strong reserves | No constraint | No constraint | Adequate | **MODERATE / HIGH** | No ceilings triggered; surplus limited by moderate income but adequate |
| 4 | Variable income, strong reserves (>12 months for variable) | No constraint | Adequate (high required months met) | Adequate | **MODERATE** | Reserve requirement adjusted upward for income instability; reserves sufficient → moderate overall |
| 5 | Stable income, weak reserves (<3 months) | Low/none | Inadequate | Potentially adequate | **LOW / VERY_LOW** | D2 imposes a capacity ceiling despite adequate debt and surplus |
| 6 | High dependents (vs. identical baseline without dependents) | Same as baseline | More constrained (required months increase) | Same as baseline | **Lower than baseline** | Reserve adequacy decreases due to increased required coverage → capacity falls |
| 7 | Negative monthly surplus | No constraint | No constraint | None (negative surplus) | **VERY_LOW** | D3 catches this: surplus below zero means investor cannot meet current obligations → strong capacity constraint |
| 8 | Missing debt information (unknown, not zero) | Unknown → reduced confidence, uncertain D1 | Assessed independently | Assessed partially (without debt component) | **PARTIAL / LOW confidence** | Assessment proceeds partially without D3; D1 uncertain; confidence reduced; conservative result |
| 9 | Missing reserve information | Assessed normally | INSUFFICIENT_INFORMATION | Assessed normally | **PARTIAL, conservative cap** | D2 cannot be assessed; partial assessment conservatively caps at LOW or produces INSUFFICIENT_INFORMATION for D2 |
| 10 | Missing expense information | Assessed normally (debt ratio calculable) | Cannot compute D2 denominator | Cannot compute D3 | **PARTIAL, reduced confidence** | D2 and D3 both impaired; D1 partially assessed; confidence significantly reduced |

**All 10 scenarios produce directionally sensible outcomes** under the proposed architecture. No scenario requires hard-coded thresholds to produce the correct directional result — the architecture itself drives the direction.

---

## 17. Governance Classification Table

| Decision | Previous Status | Audited Status | Reason |
|---|---|---|---|
| **Constraint-Based Bottleneck Architecture** (RC-ARCH-01) | `APPROVED` | `APPROVED` | Well-reasoned structural choice; preferable to weighted composite for fiduciary conservatism |
| **Hard Ceiling Concept — General Principle** (FPSB/RBI support) | `APPROVED` | `APPROVED` | External sources (FPSB India, RBI HFC 2017) support the concept that severe financial distress caps capacity |
| **Hard Ceiling — Min() as Specific Implementation** (RC-ARCH-03) | `APPROVED` | `PROVISIONAL` | The specific implementation mechanism (min() per independent dimension) is a product architecture choice, not externally established |
| **Lower-of-the-Two Rule** (RC-ARCH-02) | `APPROVED` | `APPROVED` | Established by Phase F specification and FPSB/SEBI fiduciary standards |
| **Debt Burden Ratio Formula Structure** (RC-D1-01) | `APPROVED` | `APPROVED` | Debt/income ratio is the standard measure; formula structure is sound |
| **Debt Denominator: Gross Income** (RC-D1-02) | `APPROVED` | `PROVISIONAL` | FPSB source uses net income; gross income is a pragmatic product choice, not externally validated for this specific use |
| **Debt Scope: Recurring Committed Only** (RC-D1-03) | `APPROVED` | `APPROVED` | Standard financial planning principle; sound |
| **Reserve Adequacy Formula Structure** (RC-D2-01) | `APPROVED` | `APPROVED` | Formula structure (reserves / required cover) is sound and evidence-aligned |
| **Reserve: FPSB 3–6 months salaried concept** (RC-D2-02) | `PROVISIONAL` | `PROVISIONAL` | FPSB directly establishes the range concept; exact value remains provisional |
| **Reserve: FPSB 6–12 months self-employed concept** (RC-D2-03) | `PROVISIONAL` | `PROVISIONAL` | Same as above |
| **Income Stability as Reserve Modifier** (RC-IS-01) | `APPROVED` | `APPROVED` | Conceptually sound; FPSB income stability distinction directly supports this |
| **Stability + Dependents: Additive on Required Months** | `APPROVED` (implicit) | `APPROVED` | Additive combination is correct; multiplicative would compound excessively |
| **Surplus Ratio Formula Structure** (RC-D3-01) | `APPROVED` | `APPROVED` | Formula is mathematically coherent; taxes-deducted surplus is sound for resilience assessment |
| **Surplus as 3rd Independent Constraint Dimension** | `APPROVED` (implied) | `PROVISIONAL` | Surplus ratio is algebraically dependent on debt inputs; it is a derived verification check, not a fully orthogonal dimension |
| **Five-Level Ordinal Scale** (RC-ARCH-05) | `APPROVED` | `APPROVED` | Appropriate granularity for suitability guidance; consistent with Phase F specification |
| **Missing Data → Reduced Confidence (not zero)** (RC-ARCH-04) | `APPROVED` | `APPROVED` | Directly established by PRODUCT_SPEC.md §25 and ARCHITECTURE.md §15 |
| **Confidence Separation from Capacity** (RC-INT-01/02/03 design) | `APPROVED` | `APPROVED` | Confidence is an output; it must not feed back into the capacity tier computation |
| **INSUFFICIENT_INFORMATION as distinct from LOW** | `APPROVED` | `APPROVED` (with clarification) | Methodology is correct; language in §13 needs sharpening on the distinction |
| **F.3 Startup: Refuse if params absent** | `APPROVED` | `PROVISIONAL` | Correct for production; needs expansion to three modes (Production/Research/Test) |
| **Household Context Convention** | Not stated | `TBD — MUST BE DOCUMENTED` | V1 must explicitly define whether inputs are individual or household-level |
| **Illiquid Assets Excluded from Reserves** | `APPROVED` | `APPROVED` | Correct exclusion; edge cases need explicit classification in F.3 |
| **Horizon Excluded from Risk Capacity** | `APPROVED` | `APPROVED` | Separation is correctly maintained throughout the methodology |
| **Risk Capacity ≠ Affordability** | `APPROVED` | `APPROVED` (with clarification) | Architecture is correctly separated; framing in §8 needs sharpening |
| **All 13 TBD parameters remain TBD** | `TBD` | `TBD` | Confirmed — none can be responsibly set without empirical calibration |

---

## 18. Required Document Corrections

### A. `docs/phase_f2c_risk_capacity_methodology.md`

1. **§5 / Hard Ceiling section:** Add clarification distinguishing the *general principle* (APPROVED CONCEPT) from the *specific min() implementation mechanism* (PROVISIONAL product architecture choice).
2. **§6 / Debt denominator:** Add note: "FPSB India DTI guidance references net monthly income as the denominator. This engine uses gross income for verifiability. This is a provisional product design choice. The denominator selection should be empirically validated for consistency with the surplus formula."
3. **§7 / Reserve formula:** Add note clarifying that stability and dependent adjustments are applied additively to `required_coverage_months`, not multiplicatively to the full denominator.
4. **§8 / Surplus as 3rd dimension:** Add clarification that D3 is algebraically dependent on D1 inputs; it serves as a combined cash-flow verification check rather than a fully orthogonal constraint dimension.
5. **§8 / Capacity vs. Affordability boundary:** Add explicit boundary note.
6. **§11 / Edge-case assets:** Add a note explicitly classifying short-duration debt funds, arbitrage funds, FMPs, SGBs, and OD facilities as excluded from emergency reserves in V1.
7. **§13 / Missing data language:** Clarify that partial assessments cap conservatively; fully missing critical inputs produce `INSUFFICIENT_INFORMATION`, not a LOW tier.
8. **New section — Household Context Convention:** Document that V1 treats all declared inputs as household-level aggregates; individual vs. household separation is a known V1 limitation.
9. **New section — F.3 Startup Modes:** Document the three-mode startup policy.

### B. `docs/phase_f2c_risk_capacity_parameter_register.md`

10. **RC-ARCH-03:** Status corrected from `APPROVED` → `PROVISIONAL`.
11. **RC-D1-02:** Status corrected from `APPROVED` → `PROVISIONAL`. Add note: FPSB source uses net income; gross is a provisional product choice.
12. **New entry — Household Context Convention:** `HOUSEHOLD_INPUT_CONVENTION` — `PROVISIONAL` — V1 treats all inputs as household aggregates.
13. **New entry — F.3 Startup Mode:** `STARTUP_MODE` — `APPROVED` — three-mode policy.

---

## 19. Exact Files Changed / Not Changed

| File | Action | Reason |
|---|---|---|
| `docs/phase_f2c1_risk_capacity_governance_audit.md` | `[NEW]` | This audit report |
| `docs/phase_f2c_risk_capacity_methodology.md` | `[MODIFY]` | Corrections per §18 items 1–9 |
| `docs/phase_f2c_risk_capacity_parameter_register.md` | `[MODIFY]` | Status corrections per §18 items 10–13 |
| `docs/documentation_traceability_matrix.md` | `[MODIFY]` | Add Phase F.2C.1 entry |
| **All `.py` files** | **NOT MODIFIED** | This is a documentation-only audit |

---

## 20. Production Code Modification Status

**CONFIRMED: ZERO production Python files, test files, database schemas, or configuration files were modified during Phase F.2C.1.**

---

## 21. Issues Remaining Before F.3

| Issue | Severity | Required Action Before F.3 |
|---|---|---|
| RC-ARCH-03 status over-statement | Medium | Corrected in this audit → PROVISIONAL |
| RC-D1-02 (gross income denominator) status | Medium | Corrected in this audit → PROVISIONAL |
| Surplus ratio independence over-statement | Medium | Clarification added to methodology |
| Household context convention not documented | High | Must be documented in F.3 spec before implementation |
| F.3 startup three-mode policy | High | Must be documented in F.3 spec before implementation |
| 13 TBD empirical calibration parameters | High (expected) | F.3 implements as config stubs; no calibration required for F.3 |
| Edge-case asset classification | Low | Document in methodology; F.3 data collection spec |
| Affordability / capacity framing in §8 | Low | Clarification added to methodology |
| Missing data language precision in §13 | Low | Clarification added to methodology |

---

## 22. Final Determination

**Can F.3 Risk Capacity Engine implementation begin after this audit?**

**YES — with the following pre-implementation requirements:**

1. The governance corrections to `phase_f2c_risk_capacity_methodology.md` and `phase_f2c_risk_capacity_parameter_register.md` must be applied first (done in this audit).
2. F.3 implementation spec must explicitly document the household context convention (V1 = household-level aggregates).
3. F.3 implementation spec must document the three-mode startup policy.
4. All 13 TBD parameters must be implemented as externalized config stubs — no invented values.
5. Confidence parameters (RC-INT-02, RC-INT-03) must not be read as inputs to the capacity tier computation.
6. D3 (surplus ratio) must be implemented as a verification check that is algebraically aware of its dependency on D1 inputs.

**DO NOT BEGIN F.3 AUTOMATICALLY. Await explicit user instruction.**
