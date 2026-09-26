# Phase F.3.4.2 — Suitability Data Contracts Specification Document

**Phase:** Phase F.3.4.2 — Suitability Data Contracts, Input Architecture & Ownership Governance  
**Date:** 2026-09-10 UTC  
**Status:** Approved Data Contracts  
**Final Decision:** `PHASE F.3.4.2 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Specification of immutable input/output data contracts, field validation rules, missing data semantics, and auditability requirements for the future Suitability Engine.

---

## 1. Purpose

The purpose of this document is to establish the production-ready data contracts for the future Suitability Engine. It defines the exact schemas, field types, validation constraints, and provenance metadata required for input consumption and result generation, ensuring that the eventual decision engine operates reproducibly without recomputing upstream metrics or silently mutating data.

---

## 2. Scope & Non-Scope

### In Scope
- Input contract definitions for Risk Alignment, Fund Quality, Fund Maturity, Fund Risk Profile, Goal Context, General Wealth Context, Portfolio Context, and Statutory Lock-In.
- Output contract definition (`SuitabilityAssessmentResult`).
- Data validation rules (invalid vs. missing vs. partial data).
- Explicit missing, unknown, and not-applicable semantics.
- Provenance and versioning contracts.

### Out of Scope
- Production execution logic or decision engine implementation (`risk/suitability_engine.py`).
- Scoring algorithms, numerical weights, or decision thresholds.
- Action generation (`BUY`, `ACCUMULATE`, `HOLD`, `SELL`).
- Downstream Portfolio Need or Economic Benefit logic.

---

## 3. Contract Principles

1. **Immutability:** All contract instances must be immutable data structures (e.g. `frozen=True` dataclasses or pydantic models).
2. **Explicit Nullability:** Optional fields must be explicitly typed (`Optional[...]`) and defaulted to `None`. No silent default substitutions (e.g. `0`, `0.0`, or empty strings for missing numbers/enums).
3. **Traceability:** Every contract must carry explicit `investor_id`, observation timestamps, methodology versions, rule versions, and provenance references.
4. **Validation Integrity:** Field validators must strictly reject invalid out-of-bound values (e.g. confidence scores $< 0.0$ or $> 1.0$) rather than silently clamping them during ingestion.

---

## 4. Upstream Input Data Contracts

### 4.1 Investor Context Contract (`InvestorProfileSnapshot`)
- **Owner:** Investor Profile Subsystem (`models/investor_profile.py`)
- **Role:** Read-only snapshot of investor identity, constraints, and general horizon preference.

```python
@dataclass(frozen=True)
class InvestorProfileSnapshot:
    investor_id: str
    profile_version: str
    assessment_timestamp_utc: datetime
    general_horizon_preference: Optional[str] = None
    category_restrictions: List[str] = field(default_factory=list)
```

### 4.2 Risk Alignment Contract (`RiskAlignmentAssessmentResult`)
- **Owner:** Risk Alignment Engine (`risk/alignment_models.py`)
- **Role:** Read-only input providing the investor's supportable risk envelope.

```python
@dataclass(frozen=True)
class RiskAlignmentAssessmentResult:
    assessment_id: str
    investor_id: str
    profile_version_used: str
    observation_date: date
    assessment_timestamp_utc: datetime
    alignment_status: AlignmentStatus
    limiting_constraint: LimitingConstraint
    aligned_risk_level: Optional[AlignedRiskLevel] = None
    capacity_confidence_score: float = 1.0
    tolerance_confidence_score: float = 1.0
    alignment_confidence_score: float = 1.0
    is_stale_input: bool = False
    explanation_tokens: List[str] = field(default_factory=list)
    missing_information_tokens: List[str] = field(default_factory=list)
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"
```

### 4.3 Fund Quality Contract (`FundQualityAssessmentResult`)
- **Owner:** Fund Quality Engine (`scoring/engine.py` / `models/fund_quality_dataset.py`)
- **Role:** Read-only input providing category-relative fund merit and evidence confidence.

```python
@dataclass(frozen=True)
class FundQualityAssessmentResult:
    dataset_id: str
    canonical_scheme_id: str
    amfi_code: str
    category_id: str
    observation_date: date
    overall_score: Optional[float] = None  # 0.0 to 100.0
    confidence_score: float = 1.0          # 0.0 to 1.0
    fund_maturity_bucket: str = "MATURE"
    evidence_sufficiency: str = "SUFFICIENT"
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
```

### 4.4 Fund Maturity Contract (`FundMaturityResult`)
- **Owner:** Metrics / Maturity Subsystem (`metrics/maturity.py`)
- **Role:** Read-only input describing track record length without recalculating NAV history.

```python
@dataclass(frozen=True)
class FundMaturityResult:
    canonical_scheme_id: str
    history_length_days: int
    maturity_bucket: str  # IMMATURE_UNDER_1YR, LIMITED_1_3YR, MODERATE_3_5YR, MATURE_5YR_PLUS
    maturity_confidence: float = 1.0
    observation_date: date
```

### 4.5 Fund Risk Profile Contract (`FundRiskProfile`)
- **Owner:** Data Ingestion / Scheme Master (`models/scheme_master.py`)
- **Role:** Read-only input providing authoritative fund riskometer / volatility classifications.

```python
@dataclass(frozen=True)
class FundRiskProfile:
    canonical_scheme_id: str
    amfi_code: str
    riskometer_level: str  # LOW, LOW_TO_MODERATE, MODERATE, MODERATELY_HIGH, HIGH, VERY_HIGH
    riskometer_source: str # AMFI_OFFICIAL, AMC_DISCLOSURE
    observation_date: date
    mapping_status: str = "PROVISIONAL"  # PROVISIONAL, APPROVED
```

### 4.6 Goal Context Contract (`GoalProfileSnapshot`)
- **Owner:** Goal Subsystem (`models/goal_profile.py`)
- **Role:** Read-only input describing specific goal parameters when evaluating goal-linked suitability.

```python
@dataclass(frozen=True)
class GoalProfileSnapshot:
    goal_id: str
    investor_id: str
    goal_name: str
    goal_type: str
    time_horizon_years: Optional[float] = None
    target_date: Optional[date] = None
    target_amount: Optional[float] = None
    priority: str = "MEDIUM"
```

### 4.7 Portfolio Context Contract (`PortfolioHoldingContext`)
- **Owner:** Portfolio Subsystem (Read-only view)
- **Role:** Read-only input providing holding breakdown and overlap matrices without performing portfolio need calculations.

```python
@dataclass(frozen=True)
class PortfolioHoldingContext:
    portfolio_id: str
    investor_id: str
    observation_date: date
    existing_category_allocations: Dict[str, float] = field(default_factory=dict)
    existing_amc_allocations: Dict[str, float] = field(default_factory=dict)
    overlap_matrix: Dict[str, float] = field(default_factory=dict)  # scheme_id -> overlap_ratio
    portfolio_completeness: str = "COMPLETE"  # COMPLETE, PARTIAL, ABSENT
```

---

## 5. Output Data Contract (`SuitabilityAssessmentResult`)

The primary output contract emitted by the Suitability layer:

```python
class SuitabilityStatus(Enum):
    SUITABLE = "SUITABLE"
    CONDITIONALLY_SUITABLE = "CONDITIONALLY_SUITABLE"
    NOT_SUITABLE = "NOT_SUITABLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"

@dataclass(frozen=True)
class SuitabilityAssessmentResult:
    assessment_id: str
    investor_id: str
    profile_version_used: str
    canonical_scheme_id: str
    amfi_code: str
    scheme_name: str
    category: str
    subcategory: str
    observation_date: date
    suitability_status: SuitabilityStatus
    goal_id: Optional[str] = None
    context_type: str = "GOAL_LINKED"  # GOAL_LINKED, GENERAL_WEALTH
    aligned_risk_level_used: Optional[AlignedRiskLevel] = None
    fund_risk_level_used: Optional[str] = None
    fund_quality_score_consumed: Optional[float] = None
    fund_quality_confidence_consumed: float = 1.0
    suitability_confidence_score: float = 1.0
    hard_constraint_violations: List[str] = field(default_factory=list)
    soft_factor_warnings: List[str] = field(default_factory=list)
    explanation_tokens: List[str] = field(default_factory=list)
    missing_information_tokens: List[str] = field(default_factory=list)
    risk_alignment_assessment_id: Optional[str] = None
    fund_quality_dataset_id: Optional[str] = None
    portfolio_snapshot_id: Optional[str] = None
    provenance: Optional[ProvenanceMetadata] = None
    assessment_timestamp_utc: Optional[datetime] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.assessment_id or not self.assessment_id.strip():
            raise ValueError("assessment_id cannot be empty")
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if not self.canonical_scheme_id or not self.canonical_scheme_id.strip():
            raise ValueError("canonical_scheme_id cannot be empty")
        if self.suitability_confidence_score < 0.0 or self.suitability_confidence_score > 1.0:
            raise ValueError(f"suitability_confidence_score must be between 0.0 and 1.0, got {self.suitability_confidence_score}")
```

---

## 6. Missing, Unknown & Invalid Data Semantics

- **`MISSING`:** Required field was not provided (e.g. missing Risk Alignment assessment). Results in `INSUFFICIENT_INFORMATION` and emits `MISSING_<FIELD>` token.
- **`UNKNOWN`:** Field is optionally absent or unstated by user (e.g. target amount is "I don't know"). Valid context; evaluated under General Wealth or partial evidence rules.
- **`NOT_APPLICABLE`:** Field does not apply to this evaluation mode (e.g. `goal_id` in General Wealth mode).
- **`INVALID`:** Value is present but violates type or range constraints (e.g. negative confidence). Triggers `INVALID_ASSESSMENT`.

*Governance Guarantee:* Missing data **never** converts to zero (`0`), neutral defaults, or conservative guesses.

---

## 7. Numerical Parameter Register

| Parameter Name | Value | Purpose | Source | Governance Status | Validation Requirement |
|---|---|---|---|---|---|
| `horizon_equity_min_years` | `5.0` | Min goal horizon for equity funds | Industry Practice | `PROVISIONAL` | Empirical risk study |
| `horizon_hybrid_min_years` | `3.0` | Min goal horizon for hybrid funds | Industry Practice | `PROVISIONAL` | Empirical risk study |
| `horizon_debt_min_years` | `1.0` | Min goal horizon for debt funds | Industry Practice | `PROVISIONAL` | Duration audit |
| `overlap_material_threshold` | `0.30` | Material security overlap cutoff | Diversification Practice | `PROVISIONAL` | Overlap study |
| `overlap_excessive_threshold` | `0.60` | Excessive security overlap cutoff | Diversification Practice | `PROVISIONAL` | Overlap study |
| `amc_concentration_limit` | `0.40` | Max AMC allocation threshold | Portfolio Risk Practice | `PROVISIONAL` | AMC risk audit |
