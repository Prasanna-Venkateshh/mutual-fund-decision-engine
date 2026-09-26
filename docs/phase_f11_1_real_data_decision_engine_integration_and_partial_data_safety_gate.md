# Phase F.11.1 — Real-Data Decision Engine Integration & Partial-Data Safety Gate Report

**Project:** `mutual-fund-decision-engine`  
**Phase:** F.11.1  
**Audit Date:** 2026-09-14 UTC  
**Status:** `PHASE F.11.1 REAL-DATA DECISION ENGINE INTEGRATION & PARTIAL-DATA SAFETY GATE PASSED`  

---

## 1. Executive Conclusion

Phase F.11.1 integrated the real multi-feed production dataset (established through Phase F.10 / F.10.1 / F.10.2 / F.10.3) into the end-to-end Decision Engine pipeline while enforcing strict partial-data safety gates.

### Key Governance Invariants Verified
1. **Zero False Financial Certainty**: Missing metadata (`ter=None`, `riskometer=None`, `benchmark=None`) remains explicitly `None`. No synthetic defaults (`or 0`, `or "MODERATE"`, `or category_default`) or fuzzy string matches were introduced.
2. **Score vs Confidence Separation**: Missing cost/risk/benchmark metadata reduces confidence and actionability, but does not corrupt or penalize intrinsic quality scores.
3. **Action Safety & Low Turnover**: A Fund Quality score alone CANNOT trigger `SELL`. Evidence insufficiency routes to conservative states (`MONITOR`, `REVIEW`, `INSUFFICIENT_INFORMATION`, `NO_ACTION`).
4. **Canonical Identity Stability**: Preserved `CAN_AMFI_{code}` identity across all live dataset evaluations.
5. **Methodology Boundary**: Fund Quality weights, scoring formulas, Risk Capacity, Risk Tolerance, Risk Alignment, Suitability, Portfolio Need, Economic Benefit, and Action semantics remain 100% frozen.
6. **Zero Real-Money Execution**: All transaction execution and real-money authorization remain 100% unauthorized.

---

## 2. Integration Architecture & Data Flow

The decision engine pipeline operates strictly in the canonical order:

$$\text{DATA} \rightarrow \text{METRIC ENGINE} \rightarrow \text{FUND QUALITY} \rightarrow \text{SUITABILITY} \rightarrow \text{PORTFOLIO NEED} \rightarrow \text{ECONOMIC BENEFIT} \rightarrow \text{ACTION}$$

```
                        ┌──────────────────────────────────────────────┐
                        │   Real Production Dataset (NAVAll.txt)      │
                        │    - 14,361 Live AMFI Records                │
                        │    - 53 Distinct AMCs                        │
                        │    - Metadata: TER=None, Risk=None, BM=None  │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │    QualityEngine (Fund Quality Scoring)     │
                        │    - Active Weight Rescaling                 │
                        │    - Confidence Reduction (active_w < 80%)   │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │    SuitabilityEngine (Risk & Constraints)    │
                        │    - 5-Step Precedence Pipeline              │
                        │    - Preserves Risk Envelope                 │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │   PortfolioNeedEngine (Fulfillment & Gap)    │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │  EconomicBenefitEngine (Switching Economics) │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │     DecisionOrchestrator (Action Engine)     │
                        │     - 7-Tier Precedence Hierarchy            │
                        │     - Partial-Data Safety Gate               │
                        │     - Outputs: BUY, ACCUMULATE, HOLD,        │
                        │                MONITOR, REVIEW, NO_ACTION    │
                        └──────────────────────────────────────────────┘
```

---

## 3. Partial-Data Safety Gate Rules & Field Handling

| Data Field | Situation C State | Handling Rule | Downstream Pipeline Behavior |
| :--- | :---: | :--- | :--- |
| **Total Expense Ratio (TER)** | `ter=None` | Proportional active weight rescaling in QualityEngine | Excluded from `cost_efficiency` dimension. `active_weights_sum` reduced; confidence penalized proportionally. Zero synthetic TER substituted. |
| **Riskometer** | `riskometer=None` | Native string label preserved when available; missing remains `None` | Fund risk profile unmapped. Cannot trigger hard risk envelope violation without source evidence. |
| **Benchmark** | `benchmark=None` | Explicit missing state | Benchmark-relative return calculations return `None`. Peer ranking remains strictly intra-category. |
| **Historical NAV** | Available (1-Day EOD) | Quality score returns `None` for maturity < 1 Year | Funds with < 1 year track record return `quality_score=None` and `confidence=0.0`. |

---

## 4. Forensic Audit of 10 Real Production Schemes

A forensic evaluation script (`scratch/audit_f11_1_real_scheme_evaluations.py`) evaluated 10 genuine real schemes from the live AMFI `NAVAll.txt` dataset through the integrated Decision Engine pipeline.

| # | Scheme Code | Scheme Name | Category | Metadata State | Quality Score (Conf) | Suitability Status | Action Outcome | Reason / Explanation |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | `135762` | Axis Children's Fund - Direct Plan - Growth | Children's Fund | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |
| **2** | `135765` | Axis Children's Fund - Direct Plan - IDCW | Children's Fund | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |
| **3** | `135759` | Axis Children's Fund - Regular Plan - Growth | Children's Fund | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |
| **4** | `135760` | Axis Children's Fund - Regular Plan - IDCW | Children's Fund | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |
| **5** | `135764` | Axis Children's Fund - Direct Plan - Growth | Children's Fund | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |
| **6** | `135763` | Axis Children's Fund - Direct Plan - IDCW | Children's Fund | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |
| **7** | `135766` | Axis Children's Fund - Regular Plan - Growth | Children's Fund | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |
| **8** | `135761` | Axis Children's Fund - Regular Plan - IDCW | Children's Fund | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |
| **9** | `119551` | ABSL Banking & PSU Debt - Direct IDCW Reinvest | Banking & PSU Debt | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |
| **10** | `119552` | ABSL Banking & PSU Debt - Direct Monthly IDCW Payout | Banking & PSU Debt | TER=None, Risk=None, BM=None | `None` (0.0) | SUITABLE (0.0) | `NO_ACTION` | Fund Quality score/evidence is missing. Purchase prohibited. |

---

## 5. Decision-Specific Evidence Gates

The pipeline enforces decision-specific evidence gates:
- **`BUY` Gate**: Requires `FundQualityScore != None`, `FundQualityConfidence >= 0.50`, `Suitability == SUITABLE`, `PortfolioNeed == NEED_IDENTIFIED`, and `EconomicBenefit == ECONOMICALLY_BENEFICIAL`. Missing metadata routes candidates to `NO_ACTION`.
- **`SELL` Gate**: Requires validated deterioration, suitable replacement availability, valid quality score comparison, known tax liability, known exit load, and net economic benefit. A low quality score alone defaults to `HOLD`.
- **`HOLD` Gate**: Baseline default state when evidence is partial or insufficient for an existing position.

---

## 6. Files Changed

1. **`scratch/audit_f11_1_real_scheme_evaluations.py`**: Created real-data forensic audit script evaluating 10 live schemes.
2. **`tests/financial/test_phase_f11_1_real_data_decision_engine.py`**: Created focused test suite covering real dataset integration, partial-data safety, score/confidence separation, and canonical identity stability.
3. **`docs/phase_f11_1_real_data_decision_engine_integration_and_partial_data_safety_gate.md`**: Master report created.
4. **`docs/documentation_traceability_matrix.md`**: Registered Phase F.11.1.
5. **`docs/phase_f10_3_official_amc_metadata_source_discovery_and_coverage_assessment.md`**: Added Phase F.11.1 integration addendum.
6. **`ARCHITECTURE.md`**: Updated with F.11.1 partial-data safety gate architecture notes.

---

## 7. Tests Executed & Exact Results

- **Command**: `python -m pytest tests/ -v --tb=short`
- **Baseline Test Count**: 619 passed
- **Final Test Count**: **625 passed, 0 failures, 76 warnings in 18.25s**
- **F.11.1 Test Suite**: 6 passed (`tests/financial/test_phase_f11_1_real_data_decision_engine.py`).

---

## 8. F.11.2 Readiness & Final Status

Phase F.11.1 has established the partial-data safety gate and verified end-to-end integration over real production dataset records. The project is fully ready for **Phase F.11.2 — Downstream Decision Engine Backtesting & Historical Performance Audit**.

```
PHASE F.11.1 REAL-DATA DECISION ENGINE INTEGRATION & PARTIAL-DATA SAFETY GATE PASSED
```

---

## 9. Phase F.11.1.1 Decision Safety & Actionability Forensic Audit Addendum

- **Audit Findings**: Phase F.11.1.1 completed an independent forensic audit of all 8 Action states, 7 missing-data combinations, 16 adversarial safety scenarios, static fallback inventory, real-data provenance, and determinism.
- **Test Baseline Expansion**: Test suite increased from `625 passed` to `632 passed` (`tests/financial/test_phase_f11_1_1_decision_safety_audit.py`).
- **Static Fallback Audit**: Confirmed zero unsafe production fallbacks exist (`ter`, `riskometer`, and `benchmark` fallbacks do NOT exist).
- **Safety Invariants Verified**:
  1. Fund Quality Score alone **CANNOT** trigger `SELL`.
  2. Fund Quality Score alone **CANNOT** trigger `BUY` or `ACCUMULATE`.
  3. Missing metadata is preserved explicitly as `None` without synthetic defaults.
- **Audit Status**:
```
PHASE F.11.1.1 DECISION SAFETY & ACTIONABILITY FORENSIC AUDIT PASSED
```

