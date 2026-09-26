# Mutual Fund Decision Engine — Product Specification

**Project:** `mutual-fund-decision-engine`  
**Status:** Draft v0.1  
**Purpose:** Single source of truth for product behavior, financial methodology, architecture, implementation and QA.

---

## 1. Product Vision

Build an explainable decision-support platform for Indian mutual-fund investors.

The platform must go beyond ranking funds. It should help an investor:

1. Understand their goals, risk profile and preferences.
2. Evaluate mutual funds using category-aware, multi-factor analysis.
3. Understand their existing portfolio.
4. Build and monitor goal-oriented investment plans.
5. Identify concentration, allocation and suitability risks.
6. Make low-turnover, tax-aware decisions.
7. Understand exactly why the platform made a recommendation or changed a status.
8. See the evidence and authoritative source behind material facts wherever possible.

Core pipeline:

`DATA → VALIDATION → METRICS → FUND QUALITY → SUITABILITY → PORTFOLIO/GOAL NEED → ECONOMIC BENEFIT → ACTION → EXPLANATION`

---

## 2. Non-Negotiable Product Principles

### 2.1 Explainability
Every material recommendation, score/status change and important factual claim must be traceable to:
- validated underlying data;
- the calculation/methodology used;
- the applicable rule/configuration;
- the previous state where a change is being explained.

Users should see:
- **What changed?**
- **Why did it change?**
- **What is the impact?**
- **What, if anything, should I do?**
- **What evidence supports this?**

### 2.2 Evidence and source transparency
Use free, authoritative sources wherever possible.

For material factual claims:
- link directly to the authoritative source wherever practical;
- identify the source and retrieval/observation date;
- distinguish published facts from platform-derived calculations;
- expose methodology for platform-derived metrics;
- never imply an external authority published a metric calculated by this platform.

If provenance cannot be validated, do not manufacture confidence.

### 2.3 Category-aware analysis
Do not rank fundamentally different fund categories against each other as if they were interchangeable.

Analyze funds within appropriate:
- category;
- sub-category;
- strategy;
- risk characteristics;
- investment objective.

Inter-category decisions belong primarily to portfolio/allocation logic.

### 2.4 Score and Confidence are separate
A strong score does not automatically mean a strong recommendation.

Outputs must distinguish:
- Fund Quality/Opportunity Score
- Confidence/Evidence Strength
- Suitability
- Portfolio Need
- Actionability

Low confidence means insufficient evidence, not necessarily poor quality.

### 2.5 Context-aware decisions
A fund may be good but unsuitable for a particular investor, goal or portfolio.

Recommendation hierarchy:

`Fund Quality → Suitability → Portfolio Need → Economic Benefit → Action`

### 2.6 Low turnover
Continuous monitoring does not mean continuous transactions.

Default behavior is **do nothing** unless a meaningful, persistent and economically actionable reason exists.

### 2.7 No silent financial changes
Recommendations must not silently change a user's portfolio or investment plan.

Actual financial transaction execution is separate from recommendation/intelligence.

### 2.8 No market timing
Macro conditions may influence risk assessment and projections, but must not independently trigger market-timing actions.

### 2.9 User remains in control
The platform should present an optimal recommendation first, explain it, then allow the user to customize/override it.

### 2.10 Simple by default, powerful by choice
Default UI must be succinct. Detailed reasoning, evidence, methodology and advanced controls are progressively disclosed.

---

## 3. Investor Journey

### New investor
`Build Profile → Define Goals → Assess Risk → Build Plan → Invest → Monitor → Optimize`

### Existing investor
`Review → Identify Gaps → Analyze Portfolio → Recommend → Execute/Apply Plan → Monitor → Optimize`

A user can move between these journeys over time.

---

## 4. Investor Profile

The profile is persistent and editable.

### Initial onboarding
Exactly 10 core questions are shown using a reverse countdown:
`10 → 9 → ... → 1`

Additional questions are progressive and contextual, not part of the countdown.

Every relevant question should provide:
- a concise question;
- optional **“Why are we asking?”** explanation;
- indication of where the answer can be revisited.

### Core profile areas
- goals;
- target amount;
- goal horizon;
- risk tolerance;
- risk capacity;
- current investments/SIPs;
- comfortable investment capacity;
- emergency-reserve context;
- investment preferences;
- constraints;
- existing portfolio.

Questions may be skipped. Skipping reduces personalization/evidence confidence where relevant.

### Risk
Risk tolerance and risk capacity are separate concepts.

Recommended risk should be constrained by the lower of the two, subject to a nuanced methodology.

### Profile changes
A material profile change triggers a **Portfolio/Goal Impact Assessment**.

Never silently change the portfolio.

Where practical:
`Profile change → Impact preview → User review → Save/apply`

---

## 5. Goals

Support multiple goals plus general wealth creation.

Each goal can include:
- goal type;
- target amount;
- target date/horizon;
- priority;
- current amount if known;
- current contributions;
- preferred/acceptable risk;
- optional inflation treatment;
- linked investments.

Target amount can be skipped or marked “I don't know”; the system may later help estimate it.

### Goal progress

Use a hybrid assessment:
- current progress;
- future contributions;
- time remaining;
- reasonable return ranges;
- current portfolio risk;
- required contribution;
- relevant market/macro conditions.

Goal status:
- **On Track**
- **Needs Attention**
- **At Risk**

Avoid false precision.

### “What changed?” requirement
A material status change must show:
- previous status;
- new status;
- material drivers;
- contribution of relevant factors where measurable;
- market/macro context where relevant;
- whether action is required.

Macro context must not be presented as the sole cause unless supported by the calculations.

---

## 6. Fund Universe and Eligibility

Support a broad Indian mutual-fund universe, subject to strict eligibility and data-quality gates.

Eligibility should consider:
- valid scheme identity;
- usable historical data;
- category/classification;
- data completeness;
- source provenance;
- fund maturity;
- operational/data integrity.

Do not penalize a fund simply because it is new. New funds use a separate evaluation framework.

---

## 7. Fund Maturity and History

History requirements are flexible by data maturity.

Initial framework:
- `<1 year`: generally no conventional score;
- `1–3 years`: limited evidence / limited scoring where appropriate;
- `3–5 years`: reduced or normal evidence depending on metric;
- `5+ years`: fuller evidence;
- `10+ years`: stronger historical evidence where data quality supports it.

Exact thresholds must be validated through historical analysis and documented configuration, not arbitrary hard-coding.

Different metrics can require different evidence periods.

---

## 8. Fund Scoring

Fund scoring is composite and category-specific.

Initial maturity path:
1. Start with stable category-specific weights.
2. Later introduce controlled adaptive adjustments.
3. Only consider fully adaptive weighting if historical validation demonstrates benefit.

Potential dimensions include:
- returns;
- consistency;
- downside behavior;
- volatility/risk;
- drawdown;
- category-relative behavior;
- cost;
- portfolio characteristics;
- other validated factors.

Do not use a single metric as the decision rule.

### Dynamic downside importance
Downside importance can vary by:
- investor profile;
- category;
- market/regime context;
- portfolio context.

It must use bounded, transparent rules. No unconstrained AI-generated weights.

---

## 9. Confidence / Evidence Strength

Confidence is separate from score.

Confidence should consider:
- amount of history;
- data completeness;
- source quality;
- metric coverage;
- persistence of observed behavior;
- market/regime coverage;
- conflicting signals.

Example:

`Score 82 / 100 — Confidence Medium`

A high score with insufficient evidence must not automatically produce a strong action.

If validated data is insufficient:
`Recommendation unavailable / insufficient evidence`

---

## 10. New-Fund Framework

New funds should not automatically be classified as bad.

Use a separate framework that distinguishes:
- Score;
- Confidence;
- Fund Maturity.

Limited history should reduce confidence and/or actionability rather than mechanically reducing investment quality.

---

## 11. Macro / Market Regime

Macro affects:
1. fund scoring/context;
2. portfolio allocation;
3. goal projections/risk assessment.

Macro is a **risk-control/context mechanism**, not a market-timing mechanism.

Hierarchy:

`Fund fundamentals → Fund score → Macro adjustment/context → Suitability → Allocation → Execution`

Relevant data may include:
- interest rates;
- government bond yields;
- inflation;
- equity-market conditions;
- volatility;
- relevant economic/regulatory developments.

Macro must be relevant to the actual investor/portfolio/goal before materially influencing a decision.

---

## 12. Portfolio Analysis

Portfolio analysis must operate at multiple levels:

`Portfolio → Asset Class → Category → Fund → Sector → Security`

Analyze:
- asset allocation;
- category allocation;
- concentration;
- overlap;
- sector exposure;
- security exposure;
- duplication;
- risk;
- goal alignment.

### Overlap
Distinguish:
- healthy overlap;
- material overlap;
- excessive concentration.

Overlap alone must not automatically cause a sell recommendation.

---

## 13. Performance Drift vs User-Driven Drift

Distinguish:

### Performance drift
Allocation changed because an asset appreciated/depreciated.

Example:
`70% equity → 82% equity` without the user changing their plan.

Do not automatically sell winners solely to restore a target.

### User-driven drift
Investor intentionally changes the allocation.

This should trigger a risk/suitability assessment.

### Winner protection principle
Do not sell a strong investment merely because it has become overweight.

First evaluate:
- fund quality;
- investor risk;
- goal horizon;
- concentration;
- tax/exit-load cost;
- ability of future contributions to correct drift.

Preferred correction for moderate drift may be redirecting new contributions.

### Anti-return-chasing guardrail
If a user proposes materially increasing exposure because of recent strong performance:
- explain additional risk;
- compare current vs proposed allocation;
- show potential benefit and downside/trade-off;
- allow customization where appropriate;
- do not silently accept a materially unsuitable change.

---

## 14. Rebalancing

Use:
`Monitor → Detect Material Drift → Review → Choose Lowest-Cost Suitable Correction → User Confirmation`

Consider:
- drift magnitude;
- persistence;
- cause;
- goal horizon;
- risk profile;
- concentration;
- market context;
- taxes;
- exit load;
- transaction costs;
- future contributions.

Prefer contributions/SIPs to correct moderate drift where practical.

Selling is considered only where economically and strategically justified.

---

## 15. Recommendation Engine

Recommendation stages:

`Fund Quality → Suitability → Portfolio Need → Economic Benefit → Action`

Actions:
- **Buy**
- **Accumulate**
- **Hold**
- **Monitor**
- **Review**
- **Sell/Switch**
- **Recommendation unavailable**

### Buy
Strong fund + suitable + portfolio need + favorable economic/actionability conditions.

### Accumulate
Strong and suitable, but progressive investment is preferable due to allocation, regime, execution or other context.

### Hold
Investment remains appropriate; no meaningful action needed.

### Sell/Switch
Persistent/material deterioration + suitable replacement + positive after-tax/after-cost benefit + suitability + execution feasibility + turnover rules.

Sell is a process, not a score threshold.

---

## 16. Fund Deterioration

Use:
`Monitor → Review → Action`

Do not hard-code a universal “4 quarters = enough” rule.

Evidence sufficiency must consider:
- persistence;
- magnitude;
- consistency across metrics;
- category-relative deterioration;
- cause;
- data maturity;
- metric-specific observation requirements;
- investor context.

Different events need different evidence horizons.

Example:
- manager change is known immediately;
- concluding that the new manager caused structural deterioration requires evidence.

---

## 17. Tax, Exit Load and Transaction Cost Engine

Switching decisions must be evaluated on an after-cost basis.

Conceptually:

`Expected Benefit of Switch − Tax − Exit Load − Transaction Costs`

A higher-scoring replacement is not automatically a better action.

If switching is not economically attractive:
`Hold / Monitor`

Tax rules must be:
- sourced from current official Government/Income Tax/CBDT/Finance Act material;
- versioned;
- date-effective;
- configuration-driven;
- independently tested.

Never hard-code tax assumptions throughout application logic.

---

## 18. Investment Plan / SIP Engine

The platform recommends investment plans; actual transaction execution is separate.

When **Apply Recommended Plan** is selected:
1. Calculate recommendation.
2. Auto-populate appropriate amount/range.
3. Show the resulting plan screen.
4. Allow user editing.
5. Recalculate projections when edited.
6. Distinguish system-recommended vs user-adjusted values.
7. Show impact of adjustment.
8. Require explicit confirmation.
9. Never execute a transaction automatically.

### Affordability

Distinguish:
- comfortable/current amount;
- recommended amount;
- required amount;
- optimal amount where appropriate.

Do not force an mathematically optimal but unsustainable amount.

### Trade-off engine
If user cannot afford the required amount, present viable options:
- increase contribution;
- extend timeline;
- reduce target;
- change strategy where suitable;
- combination.

Every option must quantify its impact.

---

## 19. Windfalls / One-Time Investments

A one-time amount must be assessed across the whole portfolio and all goals.

Example inputs:
- available amount;
- goals;
- funding gaps;
- current portfolio;
- risk;
- concentration;
- taxes/costs;
- suitable investment opportunities.

Show alternative allocations and quantified impact.

Do not simply allocate the windfall to the fund currently being viewed.

---

## 20. Investor Preferences and Constraints

Preferences are captured through:
- key onboarding questions;
- progressive learning;
- persistent Profile → Investment Preferences.

Preferences influence suitability but must not override investment evidence.

Users can customize constraints extensively.

The platform should:
1. show its optimal recommendation;
2. explain it;
3. allow customization;
4. warn about suitability/goal impact;
5. avoid repeatedly nagging the user.

### Recommendation overrides
- Ask once after a meaningful profile/preference change following an override.
- After every 3 meaningful overrides, show a non-invasive profile-verification nudge.
- After the second such nudge, offer “Do not show this again.”
- Do not automatically alter profile solely from behavior.

---

## 21. Goal / Portfolio Coordination

Each goal can have a goal-specific strategy.

The total portfolio must still be optimized across goals to avoid:
- duplication;
- excessive concentration;
- unnecessary turnover;
- conflicting allocation requirements.

A fund may be suitable for one goal but unsuitable for another.

---

## 22. Notifications

Principle:
**Simple by default, granular by choice.**

Notification hierarchy:
- overall;
- goals;
- individual goals;
- funds;
- individual funds;
- portfolio;
- market/macro;
- other categories.

User controls should support:
- On;
- Off;
- Pause;
- Mute/skip for a specific item/type.

Pause should have a duration and automatically resume.

Example:
`Pause this goal for 1 quarter`

Parent controls should cascade intelligently to children without destroying saved child preferences.

### Passive investor
Simple controls such as:
`Important updates only`
or
`Pause all for 1 quarter`

### Sophisticated investor
Progressively disclosed granular controls.

### Notification quality
Use severity + aggregation + deduplication.

Do not notify for every minor score movement.

Material alerts should show:
`What changed → Why → Impact → Recommended action`

Critical system/data/security/compliance events may have separate treatment.

---

## 23. Explainability Engine

The explanation engine must not invent reasons.

Each material output should be backed by structured evidence.

Conceptual evidence object:

```text
Metric
Value
Previous Value
Change
Underlying Data
Source
Source Date
Calculation Method
Rule/Configuration Version
Confidence
```

### Example

`Goal: On Track → Needs Attention`

Drivers:
- portfolio return;
- contribution gap;
- time remaining;
- updated projection assumptions;
- market/macro context.

The system must distinguish correlation/context from actual calculated causation.

### Explanation levels

**Default**
Short and succinct.

**Why?**
Concise reasoning.

**Detailed reasoning**
Full drivers, calculations, assumptions and evidence.

**Sources**
Direct source links.

**Methodology**
How the platform calculated the metric.

---

## 24. Evidence / Source Provenance Layer

Create a dedicated source registry and evidence layer.

### Source registry fields
- source_id;
- source_name;
- source_type;
- authority_level;
- official_url;
- specific_data_url;
- supported_data_fields;
- update_frequency;
- last successful retrieval;
- validation status;
- licensing/usage status.

### Evidence record
Every important calculated output should retain:
- input data identifiers;
- source;
- observation date;
- retrieval date;
- calculation method/version;
- rule/configuration version.

### Source priority
Prefer:
1. AMFI;
2. SEBI;
3. RBI;
4. Government / Income Tax / CBDT;
5. AMC official disclosures;
6. NSE/BSE and official index/exchange sources;
7. validated third-party sources only when necessary and after a formal validation gate.

### Third-party validation gate
Require:
- provenance/traceability;
- cross-check against authoritative sources;
- historical consistency;
- update reliability;
- reputation/transparency;
- licensing/terms review;
- ongoing discrepancy monitoring.

No paid data source is required for V1.

---

## 25. Data Architecture

Separate:

`Source → Ingestion → Raw Data → Validation → Normalized Data → Metrics → Decision`

Derived metrics should generally be calculated internally from validated raw data.

Do not make the scoring engine dependent on third-party precomputed ratios when raw data is available.

### Data quality states
Data can be:
- valid;
- incomplete;
- stale;
- conflicting;
- unavailable;
- unvalidated.

Missing data must not silently become zero or a guessed value.

---

## 26. Initial Data Governance

The data-source matrix must eventually document:

| Field | Source | Free? | Authority | Update Frequency | History | Validation | Fallback |
|---|---|---|---|---|---|---|---|

Only use sources after verifying their current availability, terms and suitability.

The current `mfapi.in` experiment is a prototype/secondary source only until validated. It must not dictate the final architecture.

---

## 27. System Architecture

Recommended modular architecture:

```text
                 DATA SOURCES
                      ↓
                DATA INGESTION
                      ↓
                DATA VALIDATION
                      ↓
        ┌─────────────┴─────────────┐
        ↓                           ↓
     FUND DATA                 MARKET/MACRO
        ↓                           ↓
     FUND METRICS              MACRO METRICS
        └─────────────┬─────────────┘
                      ↓
              FUND QUALITY ENGINE
                      ↓
              SUITABILITY ENGINE
                      ↓
              PORTFOLIO ENGINE
                      ↓
                GOAL ENGINE
                      ↓
              RISK/DRIFT ENGINE
                      ↓
             TAX & COST ENGINE
                      ↓
               DECISION ENGINE
                      ↓
             RECOMMENDATION
                      ↓
             EXPLANATION ENGINE
                      ↓
                   USER
```

The UI must not contain financial decision rules.

---

## 28. Technology Direction

MVP:
- Python
- pandas
- NumPy
- requests
- SQLite

Potential later:
- FastAPI
- Streamlit initially for rapid UI
- production frontend/API architecture as appropriate.

Use Git/GitHub.

The system should be modular enough to replace the UI, database or source without rewriting the financial decision logic.

---

## 29. Configuration and Versioning

Financial rules must be externalized and versioned where practical.

Examples:
- scoring weights;
- risk bands;
- evidence thresholds;
- maturity thresholds;
- drift rules;
- recommendation thresholds;
- tax rules;
- cost assumptions;
- projection assumptions.

Every material decision should be reproducible from:
`Data Version + Methodology Version + Rule Version + Profile/Portfolio State`

Avoid unexplained magic numbers.

---

## 30. Code Quality Requirements

Code must be understandable and maintainable by a future developer or AI agent.

Meaningful code chunks require:
- docstrings;
- comments explaining purpose and business/financial logic;
- assumptions;
- inputs/outputs;
- non-obvious calculations;
- validation behavior.

Avoid excessive comments for trivial syntax.

Use:
- clear naming;
- small functions;
- separation of concerns;
- explicit types/models where useful;
- centralized configuration;
- deterministic calculations where possible.

---

## 31. QA Strategy

QA is a first-class requirement.

Every feature must have:

### Functional QA
Does the feature behave as specified?

### Financial/business-rule QA
Are calculations and decisions correct?

### Data-quality QA
Test:
- missing;
- stale;
- duplicate;
- conflicting;
- malformed;
- partial;
- unavailable data.

### Technical QA
Test:
- APIs;
- database;
- failures;
- retries;
- validation;
- performance;
- logging;
- persistence.

### Edge-case QA
Examples:
- new funds;
- insufficient history;
- zero values;
- missing answers;
- extreme values;
- very short/long horizons;
- large one-time investment;
- very high concentration.

### Explainability QA
For every material output:
- reason exists;
- reason is supported by evidence;
- source is correct;
- calculations are reproducible;
- previous state is available for change explanations;
- no unsupported claims are generated.

### Source integrity QA
Test:
- source link correctness;
- correct scheme/document;
- current source;
- broken link handling;
- source/date mismatch;
- calculation vs published metric distinction.

### Notification QA
Test:
- parent/child controls;
- pause/expiry;
- mute/skip/off;
- restoration of child preferences;
- aggregation;
- deduplication;
- severity;
- suppressed notifications;
- critical-event handling.

### Regression QA
Every feature addition must run relevant previous tests.

---

## 32. QA Traceability

Maintain:

`Requirement → Business Rule → Implementation → Test Case → Execution Result → Defect → Fix → Regression Result`

No feature is complete until:
- requirements are documented;
- implementation is documented;
- tests exist;
- tests pass or exceptions are formally recorded;
- regression impact is assessed.

---

## 33. AI QA Agent Requirements

The eventual QA agent must not merely report “looks good.”

It must:
1. Read the current specification.
2. Identify applicable requirements.
3. Locate relevant implementation.
4. Run automated tests.
5. Generate/execute edge cases.
6. Validate calculations independently where possible.
7. Test data-quality failure modes.
8. Test source provenance and links.
9. Test explainability.
10. Test UI workflows.
11. Test regression.
12. Record failures with reproducible steps.
13. Never mark a test passed without evidence.
14. Produce a structured QA report.

A later `QA_SPEC.md` should contain the executable test inventory.

---

## 34. Documentation Lifecycle

For each major feature:

### Before implementation
Document:
- requirement;
- financial/business logic;
- data sources;
- assumptions;
- acceptance criteria;
- test cases.

### During implementation
Document:
- architectural decision;
- code structure;
- configuration;
- non-obvious logic.

### After implementation
Document:
- implemented behavior;
- tests executed;
- results;
- defects;
- fixes;
- regression results;
- known limitations.

---

## 35. MVP Development Philosophy

Do not build the entire system at once.

Build vertical, testable slices.

Suggested initial progression:

1. Source registry + data ingestion framework.
2. Validated historical NAV dataset.
3. Fund metric engine.
4. Category-aware fund scoring.
5. Score + confidence.
6. Explainability/evidence layer.
7. Basic fund recommendation.
8. Investor profile.
9. Goals.
10. Portfolio ingestion.
11. Portfolio/goal analysis.
12. Allocation/rebalancing.
13. Tax/cost engine.
14. Investment-plan engine.
15. Notifications.
16. Advanced optimization.

Each slice must have its own QA coverage before the next dependent slice is built.

---

## 36. Current Technical State

Existing prototype files include:
- `data/fetch_amfi.py`
- `metrics/returns.py`
- `amfi_data.csv`
- `README.md`
- `.gitignore`

The existing NAV experiment uses `mfapi.in` and a single scheme code. Treat this as experimental only.

Before productionizing data ingestion:
- verify scheme identity;
- validate source provenance;
- implement AMFI/authoritative-source strategy;
- design normalized data contracts;
- add tests;
- avoid coupling metrics to the current CSV structure.

Do not continue expanding the prototype merely because it already exists.

---

## 37. Definition of Done

A feature is considered complete only when:

- Product requirement is documented.
- Financial/business logic is documented.
- Data sources are documented.
- Implementation is modular and explainable.
- Configuration is explicit/versioned where applicable.
- Functional tests exist and pass.
- Financial/business-rule tests exist and pass.
- Data-quality tests exist and pass.
- Edge-case tests exist and pass.
- Technical tests exist and pass.
- Explainability tests pass.
- Source/provenance tests pass where applicable.
- Regression tests pass.
- Known limitations are documented.
- QA evidence is recorded.

---

## 38. Future Scope

Potential later capabilities:
- advanced portfolio optimization;
- richer tax-lot optimization;
- automated transaction connectivity;
- advanced scenario analysis;
- probabilistic goal modeling;
- richer macro/regime models;
- controlled adaptive scoring;
- personalized behavioral insights;
- broader asset classes.

These must not be allowed to destabilize the core explainable architecture.

---

## 39. Core Product Philosophy

The platform should behave less like:

> “This fund scored 91. Buy it.”

and more like:

> “This fund appears strong for your situation. Here is the evidence, here is how we calculated it, here is our confidence, here is how it fits your portfolio and goal, here are the costs and risks of acting, and here is what we recommend — with you remaining in control.”

The system should optimize for **decision quality, suitability, evidence, transparency and sustainable investor outcomes**, not maximum activity.
