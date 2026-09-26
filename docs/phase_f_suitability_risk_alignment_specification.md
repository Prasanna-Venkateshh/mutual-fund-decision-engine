# Phase F — Investor Suitability & Risk Alignment Engine Specification

**Document Status:** GOVERNED ARCHITECTURE & FINANCIAL SPECIFICATION  
**Specification Version:** `1.0.0`  
**Status Marking:** `PROVISIONAL — REQUIRES VALIDATION`  
**Phase:** Phase F — Specification & Implementation Plan (No Engine Implementation in Phase F)

---

## 1. Executive Summary & Scope

The **Investor Suitability & Risk Alignment Engine** sits downstream of the Fund Quality Scoring Engine and upstream of Portfolio Need, Economic Benefit, and Action decisioning.

### Decision Pipeline Architecture

```
DATA ENGINE
    ↓
FINANCIAL METRIC ENGINE
    ↓
FUND QUALITY DATASET (Phase D.6)
    ↓
FUND QUALITY SCORING ENGINE (Phase E / Phase E.1)
    --------------------------------------------- [PHASE E BOUNDARY]
    ↓ (Consumes Fund Quality Score Result)
INVESTOR SUITABILITY & RISK ALIGNMENT ENGINE (Phase F Specification)
    ├── Risk Capacity Model
    ├── Risk Tolerance Model
    ├── Lower-of-the-Two Risk Alignment Rule
    ├── Goal-Level & General Wealth Context
    ├── Affordability & Sustainable Contribution Constraints
    └── Material Change Reassessment Engine
    --------------------------------------------- [PHASE F BOUNDARY]
    ↓ (Outputs Suitability Assessment & Constrained Risk Bounds)
PORTFOLIO NEED ENGINE (Future Phase)
    ↓
ECONOMIC BENEFIT ENGINE (Future Phase)
    ↓
ACTION ENGINE (Buy / Accumulate / Hold / Sell) (Future Phase)
```

---

## 2. Core Separation of Concerns

The architecture strictly enforces isolated boundaries between evaluation layers:

| Pipeline Layer | Core Question Answered | Governing Domain | Prohibited Contaminants |
|---|---|---|---|
| **A. Fund Quality** | *What is the intrinsic quality of this fund relative to appropriate peers?* | Category-relative performance, volatility, drawdown, consistency, cost, track record. | Investor age, income, risk tolerance, goals, portfolio holdings, tax status. |
| **B. Suitability** | *Is this category/asset class appropriate for this investor & goal context?* | Financial risk capacity, behavioral risk tolerance, time horizon, affordability, liquidity. | Portfolio overlap, trade execution costs, capital gains tax calculations, buy/sell trade signals. |
| **C. Portfolio Need** | *Does the investor's current portfolio require this asset exposure?* | Portfolio asset allocation gap, concentration risk, category coverage, factor exposure. | Market timing, short-term momentum, transaction cost friction. |
| **D. Economic Benefit** | *Does taking this action yield positive net value after costs & taxes?* | Switching costs, exit loads, STCG/LTCG taxes, expense ratio savings, yield differential. | Investor emotional preferences, brand perception. |
| **E. Action** | *What explicit recommendation should the platform present to the user?* | Action signals (`BUY`, `ACCUMULATE`, `HOLD`, `SELL`), transaction sizing, execution sequence. | Unconstrained asset recommendations exceeding suitability bounds. |

---

## 3. Investor Profile Data Architecture

The Investor Profile represents a versioned, point-in-time snapshot of investor financial and behavioral state.

### Attribute Classification

```
INVESTOR PROFILE SNAPSHOT (Versioned)
  ├── Stable Attributes (Slow-changing: Birth Date, Primary Occupation, Family Dependency Ratio)
  ├── Dynamic Attributes (Periodically updated: Monthly Net Income, Fixed Expenses, Liquid Reserves)
  ├── Goal Profiles (Goal-specific: Target Horizon, Target Amount, Priority, Liquidity Date)
  ├── Portfolio Context (Current Assets, Concentration, Debt-to-Equity Ratio, Active SIPs)
  ├── Behavioral Observations (Loss Reaction, Volatility Comfort, Drawdown Re-anchor History)
  └── Provenance & Audit Metadata (Timestamp UTC, Source ID, Profile Version, Confidence Score)
```

### Profile Attributes Matrix

| Category | Attribute Key | Data Type | Reassessment Trigger / Expiry | Source & Provenance |
|---|---|---|---|---|
| **Stable** | `birth_date` | `date` | Fixed (Age computed dynamically) | User Explicit / Verified ID |
| **Stable** | `financial_dependents_count` | `int` | Annual review / Life event | User Explicit |
| **Dynamic** | `monthly_gross_income` | `float` | Income change / 12 months | User Declared / Bank Sync |
| **Dynamic** | `monthly_fixed_expenses` | `float` | Expense change / 12 months | User Declared / Expense Tracker |
| **Dynamic** | `liquid_emergency_reserves` | `float` | Quarterly review / Withdrawal | Bank Account / Liquid Fund Balance |
| **Dynamic** | `existing_debt_servicing_monthly` | `float` | Loan closure / New EMI | User Declared / Bureau Record |
| **Goal** | `goal_id` | `str` | Goal creation / Amendment | User Defined |
| **Goal** | `target_date` / `effective_horizon_years` | `date` / `float` | Time decay (Continuous) | Computed from Target Date |
| **Goal** | `target_amount` | `Optional[float]` | User update (Optional field) | User Explicit / Skipped |
| **Behavioral**| `loss_tolerance_choice` | `Enum` | Market crash / Re-assessment | Scenario Questionnaire |
| **Behavioral**| `historical_drawdown_reaction` | `Enum` | Past transaction audit | System Behavior Log |

---

## 4. Risk Capacity Model Design

**Risk Capacity** is defined as the investor's *objective financial ability to absorb capital loss* without compromising essential living expenses, emergency security, or critical financial obligations.

### Risk Capacity Dimensions & Tiers

$$\text{Risk Capacity Score} = f(\text{Emergency Cover}, \text{Income Stability}, \text{Savings Rate}, \text{Horizon}, \text{Debt Servicing Ratio})$$

| Capacity Level | Ordinal Rank | Net Income Savings Ratio | Emergency Reserve Cover | Max Drawdown Capacity |
|---|---|---|---|---|
| `VERY_LOW` | 1 | $< 10\%$ | $< 3$ Months Expenses | $< 5\%$ Capital Loss |
| `LOW` | 2 | $10\% - 20\%$ | $3 - 6$ Months Expenses | $5\% - 10\%$ Capital Loss |
| `MODERATE` | 3 | $20\% - 35\%$ | $6 - 12$ Months Expenses | $10\% - 20\%$ Capital Loss |
| `HIGH` | 4 | $35\% - 50\%$ | $12 - 24$ Months Expenses | $20\% - 30\%$ Capital Loss |
| `VERY_HIGH` | 5 | $> 50\%$ | $> 24$ Months Expenses | $> 30\%$ Capital Loss |

> [!IMPORTANT]
> **Provisional Rule RC-01:** High income does **NOT** automatically imply high Risk Capacity. If fixed debt commitments consume $> 60\%$ of income or emergency reserves cover $< 3$ months, Risk Capacity is capped at `LOW` regardless of absolute income level.

---

## 5. Risk Tolerance Model Design

**Risk Tolerance** is defined as the investor's *psychological willingness and behavioral emotional comfort* to endure portfolio volatility, temporary losses, and prolonged market drawdowns without panic selling.

### Behavioral Scenario Questionnaire Matrix

```
SCENARIO QUESTIONNAIRE
  ├── Q1: Immediate 20% Portfolio Decline Reaction
  │     ├── Panic / Exit to Cash  → [Score: 1 - VERY_LOW]
  │     ├── Anxious / Hold & Wait  → [Score: 2 - LOW]
  │     ├── Calm / Rebalance      → [Score: 3 - MODERATE]
  │     └── Opportunity / Buy More → [Score: 4 - HIGH]
  ├── Q2: Prolonged 2-Year Market Stagnation Comfort
  ├── Q3: Volatility Trade-off (Stability vs Growth Focus)
  └── Q4: Past Market Crash Action Log (If Existing Investor)
```

### Inconsistent Response Resolution
If behavioral scenario responses conflict (e.g., Q1 indicates `HIGH` risk tolerance but Q3 indicates preference for zero loss):
1. **Conservative Tie-Breaker:** The engine defaults to the lower risk response.
2. **Behavioral Inconsistency Flag:** `behavioral_consistency_score` is reduced (\(< 0.70\)).
3. **Platform Confidence Penalty:** Overall suitability confidence is reduced, prompting Tier 2 progressive clarification.

---

## 6. Lower-of-the-Two Risk Constraint Rule

The engine calculates **Effective Risk Alignment** by enforcing the mandatory **Lower-of-the-Two Rule**:

$$\text{Effective Risk Alignment} = \min(\text{Risk Capacity Level}, \text{Risk Tolerance Level})$$

```
                   RISK TOLERANCE LEVEL
                  VERY_LOW  LOW  MODERATE  HIGH  VERY_HIGH
RISK CAPACITY
VERY_LOW            [1]     [1]    [1]     [1]     [1]
LOW                 [1]     [2]    [2]     [2]     [2]
MODERATE            [1]     [2]    [3]     [3]     [3]
HIGH                [1]     [2]    [3]     [4]     [4]
VERY_HIGH           [1]     [2]    [3]     [4]     [5]

Legend: [1] Very Low Risk, [2] Low Risk, [3] Moderate Risk, [4] High Risk, [5] Very High Risk.
```

> [!CAUTION]
> **Financial Safety Rule:** Behavioral willingness (\(\text{Risk Tolerance}\)) can **NEVER** override objective financial inability (\(\text{Risk Capacity}\)). An aggressive investor with zero emergency reserves must be restricted to a conservative risk alignment.

---

## 7. Multiple Goals & General Wealth Context

### Goal-Level vs Investor-Level Suitability

Investors may configure multiple simultaneous goals, each receiving a dedicated **Goal Risk Profile**:

```
INVESTOR SUITABILITY CONTEXT
  ├── Overall Investor Risk Alignment (Global Risk Capacity & Tolerance Baseline)
  │
  ├── Goal 1: "Child Higher Education" (Target: 3 Years)
  │     ├── Effective Horizon: 3.0 Years (Short)
  │     ├── Goal Risk Alignment: LOW RISK (Capped by Short Horizon)
  │     └── Suitable Asset Classes: Short Duration Debt, Banking & PSU Debt, Arbitrage
  │
  ├── Goal 2: "Retirement Wealth" (Target: 20 Years)
  │     ├── Effective Horizon: 20.0 Years (Long)
  │     ├── Goal Risk Alignment: HIGH RISK (Limited only by Investor Effective Risk Alignment)
  │     └── Suitable Asset Classes: Flexi Cap Equity, Large & Mid Cap Equity, Aggressive Hybrid
  │
  └── General Wealth (Non-Goal Surplus Capital)
        ├── Target: Flexible / Unconstrained
        └── Suitable Asset Classes: Matches Overall Investor Effective Risk Alignment
```

---

## 8. Time Horizon & Liquidity Override Rules

Time horizon acts as a strict ceiling on asset class suitability regardless of high risk capacity or tolerance.

### Time Horizon Suitability Bounds

| Effective Time Horizon (\(H\)) | Horizon Tier | Maximum Permissible Asset Risk Tier | Unsuitable Asset Categories |
|---|---|---|---|
| \(H < 1\text{ Year}\) | Ultra Short | `ULTRA_LOW_RISK` | Equity, Hybrid, Medium/Long Debt |
| \(1\text{ Yr} \le H < 3\text{ Yrs}\) | Short | `LOW_RISK` | Small Cap Equity, Sectoral/Thematic, Credit Risk |
| \(3\text{ Yrs} \le H < 5\text{ Yrs}\) | Medium | `MODERATE_RISK` | Small Cap Equity, High Volatility Sectoral |
| \(5\text{ Yrs} \le H < 7\text{ Yrs}\) | Long | `HIGH_RISK` | None (Subject to Risk Alignment) |
| \(H \ge 7\text{ Years}\) | Very Long | `VERY_HIGH_RISK` | None |

---

## 9. Sustainable Affordability & Unaffordable Goal Pathways

The engine distinguishes between current contributions and sustainable financial capacity:

$$\text{Sustainable Monthly Contribution} = \text{Monthly Income} - \text{Fixed Expenses} - \text{Debt EMIs} - \text{Emergency Contribution}$$

### Unaffordable Goal Resolution Pathways

If Goal Target Amount requires a monthly SIP of ₹25,000 but Sustainable Monthly Contribution is ₹15,000:

```
UNAFFORDABLE GOAL DETECTED (Funding Gap: ₹10,000 / month)
  │
  ├── Pathway 1: Adjust Contribution → Set SIP to Sustainable Maximum (₹15,000)
  ├── Pathway 2: Extend Timeline → Increase Target Date from 5 Years to 7.5 Years
  ├── Pathway 3: Reduce Target Amount → Adjust Target from ₹20 Lakhs to ₹12.5 Lakhs
  └── Pathway 4: Hybrid Adjustments → Combine 1-Year Extension + ₹15,000 SIP
  
  PROHIBITED ACTION: Do NOT recommend an unsuitable high-risk equity category to bridge the gap!
```

---

## 10. Progressive Profiling Architecture

To eliminate up-front questionnaire friction, profiling is collected in progressive tiers:

```
PROGRESSIVE PROFILING TIERS
  ├── Tier 1: Minimum Viable Profile (Required for initial exploration)
  │     ├── Basic Age / Birth Date
  │     ├── Stated Horizon
  │     └── Primary Investment Objective (Growth vs Income vs Stability)
  │
  ├── Tier 2: Financial Context Profiling (Required prior to portfolio generation)
  │     ├── Monthly Income & Sustainable Savings Range
  │     ├── Emergency Reserve Coverage Bucket
  │     └── Behavioral Loss Reaction Scenario (1 Question)
  │
  └── Tier 3: Comprehensive Profile Refinement (For multi-goal optimization)
        ├── Detailed Expense & Debt Servicing Breakdown
        ├── Historical Transaction Behavioral Log
        └── Tax Bracket & Existing Outside Asset Portfolio
```

---

## 11. Material Change Detection & Reassessment Triggers

The engine monitors for material changes that invalidate historical suitability assessments:

```
MATERIAL CHANGE DETECTOR
  ├── Income / Savings Change Event (> 20% change in monthly sustainable savings)
  ├── Debt Commitment Event (New loan / EMI added)
  ├── Goal Modification Event (Target date shifted by > 1 year or target amount altered)
  ├── Stale Profile Event (Profile age > 12 months without confirmation)
  └── Market Regime Shift / Portfolio Concentration Drift (> 15% asset class allocation drift)
        │
        └── TRIGGER: Reassessment Notification (No automatic trades; user prompted to review)
```

---

## 12. Machine-Readable Data Contracts

### A. Investor Profile Contract (`models/investor_profile.py`)

```python
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict

class RiskCapacityLevel(Enum):
    VERY_LOW = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    VERY_HIGH = 5

class RiskToleranceLevel(Enum):
    VERY_LOW = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    VERY_HIGH = 5

@dataclass(frozen=True)
class FinancialCapacitySnapshot:
    monthly_gross_income: Optional[float]
    monthly_fixed_expenses: Optional[float]
    liquid_emergency_reserves: Optional[float]
    monthly_debt_servicing: Optional[float]
    emergency_reserve_months: float
    savings_ratio: float
    capacity_tier: RiskCapacityLevel

@dataclass(frozen=True)
class BehavioralToleranceSnapshot:
    loss_reaction_choice: str
    stagnation_comfort_choice: str
    historical_drawdown_action: Optional[str]
    behavioral_consistency_score: float
    tolerance_tier: RiskToleranceLevel

@dataclass(frozen=True)
class InvestorProfileSnapshot:
    profile_id: str
    investor_id: str
    profile_version: str
    effective_date: date
    birth_date: date
    financial_capacity: FinancialCapacitySnapshot
    behavioral_tolerance: BehavioralToleranceSnapshot
    overall_effective_risk_alignment: RiskCapacityLevel  # Min(Capacity, Tolerance)
    profiling_tier_completed: int  # 1, 2, or 3
    confidence_score: float
    created_timestamp_utc: datetime
    is_stale: bool = False
```

### B. Suitability Assessment Result Contract (`models/suitability_assessment.py`)

```python
class SuitabilityStatus(Enum):
    SUITABLE = "SUITABLE"
    SUITABLE_WITH_CONSTRAINTS = "SUITABLE_WITH_CONSTRAINTS"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    NOT_SUITABLE = "NOT_SUITABLE"

@dataclass(frozen=True)
class SuitabilityAssessmentResult:
    assessment_id: str
    investor_id: str
    goal_id: Optional[str]
    canonical_scheme_id: str
    amfi_code: str
    scheme_name: str
    category: str
    subcategory: str
    observation_date: date
    suitability_status: SuitabilityStatus
    effective_risk_alignment: str
    max_permissible_asset_risk: str
    effective_horizon_years: float
    sustainable_sip_capacity: Optional[float]
    fund_quality_score_consumed: Optional[float]
    fund_quality_confidence_consumed: float
    suitability_confidence_score: float
    constraints_applied: List[str]
    rejection_reasons: List[str]
    summary_explanation: str
    profile_version_used: str
    suitability_rule_version: str
    assessment_timestamp_utc: datetime
```

---

## 13. Auditability & Historical Reproducibility

To satisfy fiduciary compliance:
1. **Immutable Snapshots:** Every assessment logs `profile_version_used`, `suitability_rule_version`, and full `ProfileSnapshot`.
2. **Deterministic Re-execution:** Re-running the engine with the historical `ProfileSnapshot` and `FundQualityDatasetInput` as of date \(T\) yields an **identical** `SuitabilityAssessmentResult`.
3. **No Overwrites:** Historical assessments are stored in an append-only audit repository.

---

## 14. Formal Provisional Rule Register

Every numerical parameter in this specification is explicitly registered as a configurable default marked `PROVISIONAL — REQUIRES VALIDATION`:

| Rule ID | Parameter Key | Default Value | Governance Status | Required Evidence for Final Validation |
|---|---|---|---|---|
| **RC-01** | `DEFAULT_DEBT_SERVICING_CAP_RATIO` | `0.60` | `PROVISIONAL — REQUIRES VALIDATION` | Empirical default rates across debt servicing ratios in Indian retail portfolios. |
| **RC-02** | `DEFAULT_MIN_EMERGENCY_RESERVE_MONTHS` | `3.0` | `PROVISIONAL — REQUIRES VALIDATION` | Retail cash-flow shock survival statistics under job loss / emergency events. |
| **RC-03** | `DEFAULT_CAPACITY_SAVINGS_TIERS` | Dict (10-50%) | `PROVISIONAL — REQUIRES VALIDATION` | Household savings distribution statistics from national financial surveys. |
| **RT-01** | `DEFAULT_SCENARIO_DRAWDOWN_PCT` | `0.20` | `PROVISIONAL — REQUIRES VALIDATION` | Behavioral panic-sale trigger thresholds from historical investor transaction logs. |
| **RT-02** | `DEFAULT_INCONSISTENCY_SCORE_THRESHOLD` | `0.70` | `PROVISIONAL — REQUIRES VALIDATION` | Psychometric questionnaire consistency and re-test reliability studies. |
| **H-01** | `DEFAULT_ULTRA_SHORT_HORIZON_YEARS` | `1.0` | `PROVISIONAL — REQUIRES VALIDATION` | Historical recovery period probabilities for fixed income vs equity categories. |
| **H-02** | `DEFAULT_HORIZON_TIERS` | Dict (1-7 Yrs) | `PROVISIONAL — REQUIRES VALIDATION` | Category rolling return recovery probabilities across investment horizons. |
| **MC-01** | `DEFAULT_MATERIAL_INCOME_CHANGE_RATIO` | `0.20` | `PROVISIONAL — REQUIRES VALIDATION` | Financial planning sensitivity analysis of income volatility on goal probability. |
| **MC-02** | `DEFAULT_MATERIAL_PORTFOLIO_DRIFT_RATIO` | `0.15` | `PROVISIONAL — REQUIRES VALIDATION` | Rebalancing tracking error and transaction friction trade-off analysis. |
| **MC-03** | `DEFAULT_PROFILE_STALENESS_MONTHS` | `12` | `PROVISIONAL — REQUIRES VALIDATION` | Annual financial review regulatory guidelines and profile decay metrics. |

---

## 15. Five-Layer Validation Framework

To prevent misrepresenting software testing as empirical financial validation, validation is explicitly separated into 5 distinct domains:

```
FIVE-LAYER VALIDATION FRAMEWORK
  ├── Layer 1: Software & Logic Validation (Unit tests, edge case assertions, deterministic outputs)
  ├── Layer 2: Mathematical Validation (Range bounds, min/max matrix math, non-negative bounds)
  ├── Layer 3: Behavioral Questionnaire Validation (Consistency checks, scenario choice clarity)
  ├── Layer 4: Financial Methodology Validation (Fiduciary alignment, lower-of-two rule compliance)
  └── Layer 5: Empirical Calibration (Empirical demographic data, market cycle backtesting)
```

Synthetic data is used **ONLY** for Layer 1 and Layer 2 software/mathematical testing, and is **NEVER** cited as empirical validation for Layer 5 financial methodology.

---

## 16. Status & Governance Marking

> [!IMPORTANT]
> **Governance Status:** `PROVISIONAL — REQUIRES VALIDATION`  
> All risk capacity formulas, behavioral scenario weights, and time-horizon threshold bounds in this specification are provisional V1 designs. They are externalized as configurable defaults and subject to Layer 5 empirical testing prior to production engine deployment.
