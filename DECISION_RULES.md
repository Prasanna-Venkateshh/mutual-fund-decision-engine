# Mutual Fund Decision Engine — Financial & Product Decision Rules

**Project:** `mutual-fund-decision-engine`  
**Version:** 1.0 (Product & Investor Perspective)  
**Related Documents:** [`PRODUCT_SPEC.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/PRODUCT_SPEC.md), [`ARCHITECTURE.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/ARCHITECTURE.md), [`FEATURE_CATALOG.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/FEATURE_CATALOG.md)

---

## 1. Decision Philosophy & Core Concepts

The platform operates on a strict context-aware recommendation hierarchy:

$$\text{Fund Quality} \rightarrow \text{Suitability} \rightarrow \text{Portfolio Need} \rightarrow \text{Economic Benefit} \rightarrow \text{Action}$$

### 1.1 Separation of Score, Confidence, and Action
A high fund quality score does **not** automatically produce a `Buy` recommendation. Outputs must explicitly distinguish:
1. **Fund Quality Score:** Composite evaluation of historical returns, consistency, downside behavior, volatility, and cost relative to peer category (*Methodology to be validated*).
2. **Evidence Confidence:** Degree of data completeness, historical maturity, and persistence supporting the score (*Methodology to be validated*).
3. **Suitability:** Alignment with the individual investor's risk capacity, risk tolerance, time horizon, and personal constraints.
4. **Portfolio Need:** Structural requirement within the total portfolio (asset allocation gap, sector exposure, category balance).
5. **Actionability:** Economic feasibility after taking into account capital gains tax, exit loads, transaction fees, and turnover rules.

If data completeness or historical evidence is insufficient, the system outputs:  
`Recommendation unavailable / Insufficient evidence`

---

## 2. Recommendation Action Definitions

Every output action carries a distinct operational definition:

* **Buy:** Strong fund quality + suitable for investor profile + clear portfolio need + positive after-cost economic benefit.
* **Accumulate:** Fund is strong and suitable, but progressive investment via monthly SIP is recommended due to allocation limits or market context.
* **Hold:** Current investment remains appropriate; no action or transaction required.
* **Monitor:** Minor performance or organizational deterioration suspected, but evidence is insufficient to warrant selling.
* **Review:** Persistent or structural deterioration confirmed; replacement evaluation required.
* **Sell/Switch:** Persistent fund deterioration + suitable replacement available + positive net after-cost economic benefit + turnover rules satisfied.
* **Recommendation Unavailable:** Validated data or historical evidence is insufficient to make a recommendation without manufacturing false confidence.

---

## 3. Fund Deterioration & Manager Change Evaluation

Deterioration is evaluated as a continuous process, not an arbitrary single-quarter score drop:
1. **Manager Change:** Known immediately as an event; concluding that the new manager caused structural deterioration requires persistent observation evidence (*Methodology to be validated*).
2. **Category-Relative Deterioration:** Performance declines are evaluated relative to peer category benchmarks, not in isolation.
3. **Evidence Requirement:** Different events require different evidence observation horizons before triggering a `Sell/Switch` action (*Methodology to be validated*).

---

## 4. Portfolio Analysis, Concentration & Overlap

### 4.1 Multi-Level Portfolio Breakdown
Analyzes holdings across 6 levels:  
$$\text{Portfolio} \rightarrow \text{Asset Class} \rightarrow \text{Category} \rightarrow \text{Fund} \rightarrow \text{Sector} \rightarrow \text{Security}$$

### 4.2 Overlap Distinction
Distinguishes three levels of overlap:
- **Healthy Overlap:** Natural holding duplication among top category benchmark stocks.
- **Material Overlap:** Significant duplication across multiple funds that reduces diversification benefit.
- **Excessive Concentration:** Over-concentration in a single stock, sector, or fund house that breaches investor risk limits (*Methodology to be validated*).

Overlap alone does **not** automatically trigger a sell recommendation.

---

## 5. Rebalancing, Drift & Winner Protection

### 5.1 Drift Classification
- **Performance Drift:** Portfolio allocation shift caused purely by market appreciation/depreciation.
- **User-Driven Drift:** Intentional asset allocation change initiated by the investor.

### 5.2 Winner Protection Principle
Outperforming funds are **not** automatically sold merely because market gains caused them to become overweight.

Correction sequence for portfolio drift:
1. **Redirect New Contributions:** Direct ongoing monthly SIPs into underweighted asset classes/categories.
2. **Windfall Allocation:** Allocate lump-sum investments to underweighted categories.
3. **Rebalancing via Sale:** Selling overweight funds is considered **only** when risk tolerance is severely breached and after-cost benefit is positive.

### 5.3 Anti-Return-Chasing Guardrail
When an investor proposes increasing allocation to recent top-performing funds:
- Warn about potential downside risk and mean reversion.
- Present side-by-side comparison of current vs proposed allocation.
- Require explicit investor confirmation.

---

## 6. Net After-Tax Economic Benefit Engine

Switching decisions are evaluated strictly on an after-cost basis:

$$\text{Net Benefit} = \text{Expected Benefit of Switch} - \text{Capital Gains Tax} - \text{Exit Load} - \text{Transaction Fees}$$

If $\text{Net Benefit} \le 0$, the engine outputs `Hold` or `Monitor`.

Tax rules must be:
- Sourced from official CBDT / Income Tax regulations.
- Versioned and date-effective.
- Configuration-driven (*Methodology to be validated*).

---

## 7. Goal Progress & Affordability Trade-Offs

### 7.1 Goal Progress Statuses
- **On Track:** Projected final goal value meets target amount under realistic return assumptions.
- **Needs Attention:** Minor funding gap or timeline risk detected.
- **At Risk:** Substantial gap requiring timeline, target, or contribution adjustment.

### 7.2 Affordability Lever Hierarchy
When a required SIP contribution exceeds an investor's comfortable capacity, the trade-off engine presents 4 options:
1. Increase monthly SIP contribution.
2. Extend target horizon date.
3. Reduce goal target amount.
4. Combination adjustment.

Every option quantifies its exact impact on goal completion probability (*Methodology to be validated*).

---

## 8. Windfall Capital Allocation

Lump-sum windfalls are evaluated across the **entire portfolio and all active goals**:
- Assesses goal funding gaps, asset allocation, concentration limits, and tax implications.
- Generates multi-goal distribution options showing impact on each goal.
- Does **not** allocate the windfall solely to the fund currently being viewed.

---

## 9. Macro / Market Regime Context

Macro indicators (interest rates, yield curves, inflation) serve as a **risk-control and projection context mechanism**, **never** as a market-timing mechanism.

Macro context must be directly relevant to the investor's specific goal, horizon, and portfolio before influencing decisions.

---

## 10. Rule Externalization & Reproducibility

Every material financial decision must be reproducible from:

$$\text{Decision State} = \text{Data Snapshot ID} + \text{Methodology Version} + \text{Rule Config Version} + \text{Investor Profile Snapshot}$$

No financial rules or thresholds are hardcoded in application logic. All weights, risk bands, tax rules, and thresholds are stored in externalized versioned configuration files (`config/`).

---

## 11. Slice 2 Provisional Methodology Assumptions (Methodology to be Validated)

The Slice 2 Fund Metric Engine relies on three provisional financial calculation parameters:

1. **Annualized Trading Days (`trading_days_per_year = 252`)**:
   - **Status**: Current implementation convention; NOT a permanently approved financial rule (*Methodology to be validated*).
   - **Purpose**: Annualizing daily volatility ($\sigma_{\text{daily}} \times \sqrt{252}$) and daily downside deviation.
   - **Requirement**: Must be formally validated against actual Indian exchange trading calendars prior to Fund Quality Scoring (Slice 4). Must remain a configurable parameter in calculation functions.

2. **Minimum Acceptable Return (`mar_daily = 0.0`)**:
   - **Status**: Current implementation convention; NOT a permanently approved financial rule (*Methodology to be validated*).
   - **Purpose**: Threshold for computing downside semi-variance, treating any daily return $r_t < 0$ as downside risk.
   - **Requirement**: Must be formally validated against investor risk profile targets or risk-free rate benchmarks prior to Fund Quality Scoring (Slice 4). Must remain a configurable parameter in calculation functions.

3. **Rolling Window Tolerance (`tolerance_days = 30`)**:
   - **Status**: Current implementation convention; NOT a permanently approved financial rule (*Methodology to be validated*).
   - **Purpose**: Window matching tolerance around target calendar window lengths (e.g. 365 or 1095 days) to accommodate exchange non-trading days.
   - **Requirement**: Must be formally validated against historical market trading gap distributions prior to Fund Quality Scoring (Slice 4). Must remain a configurable parameter in calculation functions.

---

## 12. Fund Quality Scoring — Provisional Methodology Framework

This framework defines the financial, statistical, and product logic for evaluating fund quality prior to numerical parameter validation or scoring implementation. It ensures that Fund Quality Scoring remains category-aware, multi-factor, transparent, and financially defensible without inventing arbitrary numerical weights or thresholds.

### 12.1 Fund Quality Dimensions

The scoring engine evaluates fund quality across seven conceptual dimensions:

1. **Return Performance**:
   - **What it measures**: Compound wealth generation over multiple historical horizons.
   - **Investor Significance**: Indicates long-term compounding efficiency and asset growth.
   - **Directionality**: Higher is better.
   - **Limitations**: Historical return does not guarantee future return; point-to-point returns can be distorted by end-date selection bias.
   - **Slice 2 Metric Support**: `CAGR_OVERALL`, `ABSOLUTE_RETURN`.

2. **Consistency & Persistence**:
   - **What it measures**: Stability of return performance across daily sliding time windows and market cycles.
   - **Investor Significance**: Helps investors avoid "one-hit wonder" funds that generated strong returns during a single narrow market phase but underperform consistently.
   - **Directionality**: Higher mean/median rolling returns and higher positive return ratio are better.
   - **Limitations**: Requires multi-year daily NAV time-series; less meaningful for funds with short history.
   - **Slice 2 Metric Support**: `ROLLING_RETURN_MEAN_1Y`, `ROLLING_RETURN_MEAN_3Y`.

3. **Volatility & Price Risk**:
   - **What it measures**: Fluctuation intensity of daily NAV returns.
   - **Investor Significance**: Measures price uncertainty and path instability during the investment period.
   - **Directionality**: Lower is better.
   - **Limitations**: Treats upside volatility (rapid gains) and downside volatility (rapid drops) equally.
   - **Slice 2 Metric Support**: `ANNUALIZED_VOLATILITY`.

4. **Downside Risk**:
   - **What it measures**: Frequency and magnitude of returns falling below a Minimum Acceptable Return ($\text{MAR} = 0.0$).
   - **Investor Significance**: Directly measures the risk of capital loss, which matters more to investors than upside variance.
   - **Directionality**: Lower is better.
   - **Limitations**: Depends on target MAR threshold selection (*Methodology to be validated*).
   - **Slice 2 Metric Support**: `DOWNSIDE_DEVIATION`.

5. **Maximum Drawdown**:
   - **What it measures**: Worst peak-to-trough NAV percentage drop experienced over the observation period.
   - **Investor Significance**: Tests investor behavioral endurance and worst-case capital loss depth.
   - **Directionality**: Smaller drop (value closer to 0.0) is better.
   - **Limitations**: Single point-in-time extreme event; may reflect a historical market crisis rather than ongoing fund management defect.
   - **Slice 2 Metric Support**: `MAX_DRAWDOWN`.

6. **Structural Cost Efficiency (Conceptual / Future Dimension)**:
   - **What it measures**: Operational expense burden (Total Expense Ratio) incurred by the fund relative to category peers.
   - **Investor Significance**: High cost acts as a persistent drag on net investor returns.
   - **Directionality**: Lower is better.
   - **Current Data Status**: **Data Not Available in Current Slice 1 / Slice 2 Dataset**. The current dataset contains daily NAV observations only. Cost Efficiency CANNOT be scored from current data and remains a conceptual dimension until authoritative AMC Total Expense Ratio (TER) disclosure feeds are ingested in future data slices.

7. **History & Evidence Longevity**:
   - **What it measures**: Calendar span of validated historical NAV observations available for evaluation.
   - **Investor Significance**: Longer history provides higher statistical confidence that observed behavior represents structural fund skill rather than short-term luck.
   - **Directionality**: Longer history is better for evidence confidence.
   - **Limitations**: Past history length does not alter fund strategy or manager changes.
   - **Slice 2 Metric Support**: `HISTORY_LENGTH_DAYS`, `HistoryMaturityBucket`.

---

### 12.2 Metric-to-Dimension Mapping & Double-Counting Prevention

Each Slice 2 metric is assigned a specific role within the scoring architecture:

| Slice 2 Metric | Scoring Role | Target Dimension | Treatment Rationale |
| :--- | :--- | :--- | :--- |
| `CAGR_OVERALL` | Direct Contributor | Return Performance | Primary measure of long-term point-to-point compound return (active for history $\ge 365$ days). |
| `ABSOLUTE_RETURN` | Validation / Context Only | Return Performance | **Does NOT contribute directly to long-term Quality Score** when `CAGR_OVERALL` is active. Serves primarily as short-history ($< 365$ days) fallback and sanity validation. |
| `ROLLING_RETURN_MEAN_1Y` | Direct Contributor | Consistency & Persistence | Measures 1-year rolling window return average across market cycles. |
| `ROLLING_RETURN_MEAN_3Y` | Direct Contributor | Consistency & Persistence | Measures 3-year rolling window return average (active for history $\ge 1095$ days). |
| `ANNUALIZED_VOLATILITY` | Direct Contributor | Volatility & Price Risk | Measures total return variation intensity. |
| `DOWNSIDE_DEVIATION` | Direct Contributor | Downside Risk | Measures semi-variance of returns below MAR threshold. |
| `MAX_DRAWDOWN` | Direct Contributor | Maximum Drawdown | Measures historical peak-to-trough loss severity and recovery requirement. |
| `HISTORY_LENGTH_DAYS` | Evidence Confidence Only | History & Evidence Longevity | Determines `HistoryMaturityBucket` and `DataQualityState`. Does **NOT** directly alter quality score values. |

> [!IMPORTANT]
> **Statistical Overlap & Double-Counting Prevention**:
> 1. `ABSOLUTE_RETURN` vs `CAGR_OVERALL`: To prevent double-counting return levels, `ABSOLUTE_RETURN` is excluded from scoring whenever `CAGR_OVERALL` is active ($\ge 365$ days).
> 2. `CAGR_OVERALL` vs `ROLLING_RETURN`: `CAGR_OVERALL` measures overall point-to-point compounding (`Return`), whereas `ROLLING_RETURN` measures performance stability across sliding windows (`Consistency`). Dimension weights must treat them as separate quality aspects rather than duplicating return scores (*Methodology to be validated*).
> 3. `ANNUALIZED_VOLATILITY` vs `DOWNSIDE_DEVIATION`: Volatility measures total variation (upside + downside), whereas Downside Deviation isolates loss risk. Both are retained because downside risk matters more to conservative investors, but their relative weights must be calibrated to avoid over-penalizing volatile growth funds.

---

### 12.3 Category, Sub-Category, and Strategy Awareness

Mutual funds must be evaluated **strictly against economically appropriate peer groups**:

$$\text{Peer Universe} = \text{Category} + \text{Sub-Category} (+ \text{Strategy Class, Conditional})$$

1. **Category Isolation**: Equity, Debt, Hybrid, Solution-Oriented, and Index funds exhibit fundamentally different baseline risk-return profiles. A 12% volatility in Equity Small Cap represents disciplined risk control, whereas 12% volatility in Liquid Debt indicates catastrophic risk. Funds must never be scored in a single global universe.
2. **Sub-Category Granularity**: Primary peer evaluation must occur within SEBI sub-categories (e.g. Large Cap, Flexi Cap, Corporate Bond, Short Duration).
3. **Conditional Strategy Peer Grouping**: Strategy-level peer grouping (e.g. Value vs Growth vs Momentum style) is **conditional on authoritative and consistently available classification data**. If strategy metadata is missing or inconsistent, peer grouping defaults to `Category + Sub-Category` to prevent excessive peer fragmentation. Over-fragmenting peer groups reduces sample size and would artificially suppress scores by triggering peer-insufficiency states.
4. **Peer Group Insufficiency**: If a sub-category has fewer than $N$ valid canonical peer schemes (where $N$ is a configurable parameter, e.g. $N < 5$), relative scoring must be suppressed, returning `Score: Unavailable (Insufficient Peer Data)`.

---

### 12.4 Direct vs Regular Plan Analysis

The framework analyzes three conceptual options for Direct vs Regular plan evaluation:

- **Option A: Completely Separate Scoring Universes**  
  - *Pros*: Direct and Regular plans are evaluated strictly against their own plan-type peers.
  - *Cons*: Ignores the fact that Direct and Regular plans of the exact same fund share the identical underlying portfolio, stock holdings, and fund manager.
- **Option B: Common Underlying Quality Assessment + Plan Cost Adjustment (Recommended)**  
  - *Pros*: Evaluates the underlying portfolio management quality across a unified fund universe, then applies plan-specific expense ratio adjustments. Reflects financial reality accurately.
  - *Cons*: Requires unbundling manager gross performance from plan expense drag.
- **Option C: Direct-Only Primary Scoring**  
  - *Pros*: Eliminates distributor commission noise completely.
  - *Cons*: Disadvantages investors holding Regular plans who want to evaluate their existing fund's portfolio quality.

*Decision Status*: *Methodology to be validated*.

---

### 12.5 Growth vs IDCW Option Analysis

Growth and Income Distribution cum Capital Withdrawal (IDCW) options represent different cash-flow distribution mechanics for the same underlying portfolio:

1. **NAV Historical Continuity & Data Reality**: Slice 1 and Slice 2 currently ingest daily NAV series only (cash dividend distribution histories are not present in the current dataset). IDCW cash payouts cause sudden drop-offs in raw IDCW NAV series that do not represent investment losses. Evaluating raw IDCW NAV series would incorrectly interpret cash payouts as performance drops and downside risk.
2. **Primary Evaluation Rule**: Historical return, consistency, volatility, downside deviation, and max drawdown must be calculated using the **Growth option NAV series** (or reconstructed total-return series) of the canonical scheme.
3. **Suitability Layer Role**: The choice between Growth and IDCW options belongs to investor suitability, tax optimization, and cash-flow preference, **not** to underlying Fund Quality.

---

### 12.6 Peer-Relative Normalization

Raw financial metrics must be transformed into non-dimensional, comparable scores within a peer group. Conceptual methods under evaluation:

- **Percentile Ranking**: Ranks funds from 0 to 100 within peer group. Simple and robust against outliers, but loses magnitude information (e.g. the difference between 1st and 2nd percentile may be tiny or huge).
- **Standardized Z-Scores**: Measures standard deviations from peer group mean ($Z = \frac{X - \mu}{\sigma}$). Preserves relative magnitude distance, but sensitive to extreme outliers.
- **Robust Normalization (Winsorized / Median Absolute Deviation)**: Uses peer median and interquartile range with outlier capping. Prevents market crash anomalies from distorting scores.

*Decision Status*: *Methodology to be validated*.

---

### 12.7 Weighting Framework Progression

The engine will follow a 3-stage maturity progression for combining dimensions into a composite score:

1. **Stage 1 (Initial)**: Category-specific fixed weights defined in external versioned configuration files (`config/scoring_rules.json`).
2. **Stage 2 (Intermediate)**: Bounded adaptive weighting based on investor profile risk capacity (e.g., increasing downside weight for conservative risk profiles).
3. **Stage 3 (Advanced)**: Fully adaptive regime-aware weighting, activated **only if** empirical historical validation proves superior risk-adjusted investor outcomes.

*Decision Status*: No numerical percentage weights are assigned in this slice (*Methodology to be validated*).

---

### 12.8 Dynamic Downside Importance Framework

Dynamic downside importance allows category risk emphasis to adjust while preserving the core product hierarchy:

$$\text{Weight}_{\text{Downside}} = f(\text{Risk Tolerance}, \text{Risk Capacity}, \text{Category}, \text{Regime Context}, \text{Goal Horizon})$$

**Analysis of Investor Context Placement Options**:
- *Option A (Direct Score Mutation)*: Investor risk profile directly alters the intrinsic Fund Quality Score. (Rejected: corrupts the concept of intrinsic category-relative fund quality).
- *Option B (Dual Score Output)*: Generates separate intrinsic and investor-adjusted quality scores. (Rejected: creates user confusion).
- *Option C (Mandated Architecture)*: **Intrinsic Fund Quality Score remains objective and category-relative**. Investor Risk Tolerance, Risk Capacity, Goal Horizon, and Portfolio Context operate exclusively within **Suitability**, **Portfolio Need**, and **Actionability**. Dynamic downside importance adjusts category risk emphasis in Suitability evaluation, ensuring the Quality Score does not become merely a re-packaged investor-risk score.

Operational Constraints:
1. **Bounded**: Must operate strictly within configurable minimum and maximum weight bounds.
2. **Transparent**: The exact weight adjustment formula must be inspectable.
3. **Versioned**: Weighting rules must be stored in external configuration files with explicit version identifiers (`ConfigVersion`).
4. **Deterministic**: Identical inputs must produce identical weights every time.
5. **Explainable**: The system must explain *why* downside importance was adjusted.

---

### 12.9 Cost Separation & Anti-Double-Counting

Costs must be accounted for cleanly across distinct architecture layers without double-counting:

```
+------------------------------------+---------------------------------------------------+
| Architecture Layer                 | Cost Element Evaluated                            |
+------------------------------------+---------------------------------------------------+
| 1. Fund Quality Engine             | Structural Total Expense Ratio (TER) relative to  |
|                                    | category peer average.                            |
+------------------------------------+---------------------------------------------------+
| 2. Net Economic Benefit Engine    | Capital Gains Tax (STCG/LTCG), Exit Load          |
|                                    | penalties, and Transaction Fees.                  |
+------------------------------------+---------------------------------------------------+
```

> [!CAUTION]
> Exit loads and capital gains taxes must **NEVER** be deducted from the Fund Quality Score. A high-quality fund does not become a low-quality fund merely because an investor faces an exit load to sell it.

---

### 12.10 Missing Data & Confidence Handling

When data observations or metrics are unavailable:

1. **No Silent Imputation**: Missing values must **NEVER** be filled with 0.0, category averages, or assumed defaults.
2. **Core vs Optional Metrics**:
   - *Core Metrics* (`ABSOLUTE_RETURN`, `ANNUALIZED_VOLATILITY`, `MAX_DRAWDOWN`): If missing, score calculation is **suppressed**, returning `Score: Unavailable`.
   - *Optional / Long-Term Metrics* (`ROLLING_RETURN_MEAN_3Y`): If missing due to shorter history, available dimensions are re-scaled, but **Evidence Confidence is downgraded** (e.g., `Confidence: LIMITED`).
3. **Independence of Score and Confidence**: Missing data lowers Evidence Confidence, **not** the numeric Quality Score itself. Confidence must never become a hidden penalty in the numeric Quality Score.

---

### 12.11 Fund History & Data Maturity

History length dictates **evidence strength and score availability**, not intrinsic quality:

- **New Funds ($<1\text{ Year}$ history)**: Assigned `HistoryMaturityBucket.LESS_THAN_1_YEAR` and `DataQualityState.INCOMPLETE`. Conventional quality scoring is **suppressed**. The system outputs: `Recommendation unavailable / Insufficient evidence`.
- **Limited History ($1\text{ to }3\text{ Years}$ history)**: Eligible for 1-year rolling return scoring; tagged with `Confidence: LIMITED`.
- **Full History ($\ge 5\text{ Years}$ history)**: Eligible for full multi-cycle scoring; tagged with `Confidence: HIGH`.

New funds are **NEVER** assigned a poor score merely because they lack historical data.

---

### 12.12 Outliers & Extreme Market Events

Safeguards against extreme data anomalies:

1. **Data Quality Rejection vs Market Events**:
   - *Erroneous Data* (unparsed strings, negative NAVs, duplicate dates): Rejected and quarantined at the Data Ingestion / Validation layer (Slice 1).
   - *Genuine Market Events* (e.g., March 2020 COVID crash): Retained in historical NAV observations. Genuine crashes provide critical evidence of downside risk and drawdown recovery.
2. **Robust Normalization**: Score normalization algorithms must use Winsorizing or median-based scaling so single extreme days do not distort the scores of an entire category.

---

### 12.13 Score Scale & Interpretation Requirements

The numeric score scale must satisfy three investor interpretation requirements:
1. **Intuitive Ordering**: Higher score must consistently indicate superior category-relative quality.
2. **Category Context**: The score must clearly communicate that it represents performance *relative to category peers*, not an absolute global guarantee.
3. **Non-Binary Presentation**: The score must not act as a binary pass/fail toggle.

*Decision Status*: The final choice between a 0–100 standardized index, category percentile rank, or 5-tier quality classification remains *Methodology to be validated*.

---

### 12.14 Score Comparability Rules

Two Fund Quality Scores can be legitimately compared **IF AND ONLY IF** all of the following criteria match:
1. Same SEBI Category and Sub-Category.
2. Same Plan Type (`DIRECT` vs `REGULAR`).
3. Same Option Type (`GROWTH` vs `IDCW`).
4. Same `MethodologyVersion` (e.g., `"1.0.0"`).
5. Same `ConfigVersion` (e.g., `"2026.1"`).
6. Both schemes have `DataQualityState.VALID` and sufficient history.

---

### 12.15 Score Stability & Anti-Noise Principles (Conceptual Mechanisms)

To prevent minor daily NAV noise from creating score volatility, the following **conceptual stability mechanisms** are defined (exact parameters require empirical validation prior to implementation):
1. **Rolling Observations**: Primary return and risk inputs use multi-day/multi-year rolling averages rather than single-day point observations.
2. **Score Hysteresis / Buffer Bands**: Quality tier transitions require score movements beyond a minimum threshold before triggering alerts.
3. **Evaluation Frequency**: Fund Quality Scores are re-calculated on a scheduled batch basis (e.g. monthly or quarterly), not on every micro-second NAV tick.

---

### 12.16 Strict Separation of Decision Layers

The scoring engine enforces the strict distinction:

$$\text{Fund Quality} \rightarrow \text{Score} \rightarrow \text{Confidence} \rightarrow \text{Suitability} \rightarrow \text{Portfolio Need} \rightarrow \text{Economic Benefit} \rightarrow \text{Actionability}$$

- **High Score $\ne$ Buy**: A fund scored 92/100 in Small Cap Equity is unsuitable for an investor needing liquid funds in 3 months.
- **Low Score $\ne$ Sell**: A fund scored 45/100 should not be sold if exit loads and capital gains taxes outweigh the expected net benefit of switching.

---

### 12.17 Explainability & Evidence Requirements

Every generated Fund Quality Score must provide a structured evidence payload:
- **Overall Score & Category Rank/Percentile**.
- **Evidence Confidence Rating** (`HIGH`, `MEDIUM`, `LOW`, `INCOMPLETE`).
- **Top Positive Drivers** (e.g., "Top 5% 3-Year Rolling Return in Large Cap Category").
- **Top Negative Drivers** (e.g., "Higher than average Downside Deviation").
- **Category Peer Context** (Peer Group Size, Mean, Median, Min, Max).
- **Provenance Attributes** (`MethodologyVersion`, `ConfigVersion`, Data Snapshot Timestamp).

---

### 12.18 Empirical Backtesting Design & Validation Plan

#### 12.18.1 Core Fund Quality Data vs Optional Benchmark Data
Distinguishing core NAV-based scoring validation from benchmark-relative validation:
- **Core Fund Quality Validation (Required Prerequisite)**: Validating core NAV-based scoring dimensions (CAGR, rolling returns, volatility, downside deviation, max drawdown, peer percentile rankings) requires only:
  1. Historical daily NAV time-series across full peer universes.
  2. Point-in-time scheme universe catalog (including merged/closed schemes).
  3. Point-in-time Category and Sub-Category classification history.
  4. Plan (`DIRECT`/`REGULAR`) and Option (`GROWTH`/`IDCW`) identities.
  5. Historical Total Expense Ratio (TER) data (where Cost Efficiency is evaluated).
- **Benchmark-Relative Validation (Optional Second Stage)**: Benchmark index histories and benchmark mappings are required **ONLY** for validating benchmark-relative metrics (e.g. Alpha, Beta, Tracking Error, Information Ratio). Benchmark data is **NOT** a prerequisite for validating core peer-relative NAV scoring dimensions.

#### 12.18.2 Bias Prevention Safeguards
1. **Survivorship Bias Control**: Historical validation must **NOT** use only today's surviving schemes. The backtest dataset must include schemes that historically existed as of evaluation date $T$ but subsequently closed, merged, renamed, or changed SEBI categories.
2. **Look-Ahead Bias Control**: A Fund Quality Score calculated for historical date $T$ must strictly use information that was available as of $T$. No future NAV observations, future category reclassifications, future TER disclosures, or future peer universe membership may leak into historical score construction.
3. **Point-in-Time Peer Universe**: Peer normalization at historical date $T$ must be constructed using the peer universe and classifications that were valid at date $T$, not today's current scheme classifications.
4. **Fund Lifecycle Event Handling**: The backtesting framework must track scheme lifecycle events (mergers, closures, category shifts) to ensure performance histories are attributed correctly without creating artificial performance jumps or survivor distortions.

#### 12.18.3 Conceptual Backtest Design Pipeline
The backtest pipeline follows an 11-step deterministic structure:

$$\text{Snapshot}(T) \rightarrow \text{Universe}(T) \rightarrow \text{Classification}(T) \rightarrow \text{Metrics}(T) \rightarrow \text{Peers}(T) \rightarrow \text{Normalization} \rightarrow \text{Candidate Score} \rightarrow \text{Forward Period} \rightarrow \text{Outcomes} \rightarrow \text{Stability} \rightarrow \text{Comparison}$$

1. **Historical Data Snapshot ($T$)**: Select historical evaluation date $T$.
2. **Point-in-Time Universe Construction**: Extract all schemes active at date $T$.
3. **Point-in-Time Classification**: Retrieve scheme categories and sub-categories valid at date $T$.
4. **Metric Calculation**: Compute Slice 2 metrics using NAV history available up to date $T$.
5. **Peer Universe Assembly**: Group schemes into point-in-time sub-category peer sets.
6. **Peer Normalization**: Transform raw metrics into candidate non-dimensional scores.
7. **Candidate Score Generation**: Synthesize composite candidate scores for date $T$.
8. **Forward Observation Window**: Track fund performance over subsequent forward periods.
9. **Outcome & Stability Measurement**: Evaluate score rank persistence, volatility, and risk-adjusted return behavior.
10. **Overfitting & Regime Control**: Test across multiple market regimes (bull, bear, volatile, sideways) using walk-forward / out-of-sample validation to prevent data-mining bias.
11. **Methodology Candidate Comparison**: Compare alternative normalization, weighting, and stability parameter sets to select optimal production rules.

#### 12.18.4 Validation Objectives (What Backtesting Evaluates)
Empirical backtesting evaluates whether candidate methodology options produce desirable system properties:
- **Meaningful Peer Differentiation**: Scores differentiate high-quality funds from weak funds within sub-categories.
- **Rank Persistence & Low Noise**: High-quality funds exhibit reasonable score stability across consecutive months without excessive score churn caused by single-day NAV noise.
- **Robustness Across Market Regimes**: Scoring methodologies perform consistently across bull, bear, and sideways regimes.
- **No Unintended Bias**: Ensures no artificial bias against newer funds ($\ge 1\text{ Year}$ history) or bias introduced by scheme survival.

> [!NOTE]
> Backtesting evaluates statistical methodology properties (stability, differentiation, regime robustness). It does **NOT** claim predictive future return guarantees.

#### 12.18.5 Score vs Confidence in Validation
Empirical validation evaluates Evidence Confidence strictly as a measure of **data completeness and evidence longevity**, never as a score boost or penalty.

#### 12.18.6 Backtest Evidence Retention Payload
Every validation run must retain a complete audit record containing:
- Data Snapshot Timestamp & Database Version ID.
- Methodology Version & Candidate Rule Config Version.
- Point-in-Time Scheme Universe & Classification Catalog.
- Computed Metrics, Peer Statistics, Normalization Scores, and Confidence States.
- Forward Observation Metrics & Stability Metrics.
- Reproducibility Metadata.

---

### 12.19 Final Readiness Statement & Methodology Decision Register

#### Three-Tier Readiness Assessment:
1. **Methodology Readiness: READY.** The conceptual frameworks, decision boundaries, dimension mappings, bias controls, and backtesting architecture are fully specified.
2. **Historical Data Architecture Readiness: PARTIALLY READY.** The Slice 1 & 2 SQLite schema and repositories support point-in-time normalized NAV storage, scheme mapping, and metric persistence.
3. **Historical Dataset Availability: NOT READY.** The current repository contains a sample AMFI dataset. Meaningful empirical backtesting **CANNOT** occur until a multi-year daily NAV dataset covering the full Indian mutual fund universe is ingested.

#### Methodology Decision Register:

| Decision Area | Current Position | Status | Validation Needed |
| :--- | :--- | :--- | :--- |
| **Separation of Quality, Score, Confidence, Suitability & Action** | Enforced by Product Principles | **Defined by Product Principles** | None (Core Rule) |
| **Category-Isolated Peer Evaluation** | Enforced by Product Principles | **Defined by Product Principles** | Sub-category peer minimum size ($N$) |
| **New Fund Treatment ($<1\text{ Year}$ history)** | Suppress scoring, mark INCOMPLETE | **Defined by Product Principles** | None (Core Rule) |
| **No Silent Data Imputation** | Reject or suppress on missing data | **Defined by Product Principles** | Core vs optional metric classification |
| **Direct vs Regular Evaluation Model** | Common portfolio quality + plan expense adjustment | **Provisional Implementation Convention** | Compare separate vs unified universe models |
| **Growth vs IDCW NAV Series Usage** | Growth option NAV used for quality calculations | **Provisional Implementation Convention** | Total-return series adjustment validation |
| **Annualized Trading Days ($252$)** | Default 252 trading days per year | **Provisional Implementation Convention** | Verify against Indian exchange calendars |
| **Minimum Acceptable Return ($\text{MAR} = 0.0$)** | Default 0.0 threshold for downside dev | **Provisional Implementation Convention** | Risk-free rate vs 0.0 MAR target comparison |
| **Rolling Window Tolerance ($30$ days)** | Default $\pm 30$ calendar days tolerance | **Provisional Implementation Convention** | Market holiday gap distribution review |
| **Dimension Weighting Percentages** | Category-specific fixed weights initially | **Methodology to be Validated** | Empirical historical backtesting |
| **Peer Normalization Algorithm** | Percentile vs Z-Score vs Robust | **Methodology to be Validated** | Outlier sensitivity analysis |
| **Dynamic Downside Weight Bounds** | Piecewise linear risk-based bounds | **Methodology to be Validated** | Investor risk tolerance backtest |
| **Final Score Scale (0–100 vs Star)** | Standardized 0–100 composite index | **Methodology to be Validated** | Investor UX interpretation review |
| **Score Stability Hysteresis Band** | Minimum delta for tier transition | **Methodology to be Validated** | Turnover impact analysis |



