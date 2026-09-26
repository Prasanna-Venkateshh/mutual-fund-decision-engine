# Phase F.11.1.1 — Decision Safety & Actionability Forensic Audit Report

## Executive Summary

Phase F.11.1.1 conducted an independent forensic audit and safety verification of the F.11.1 integrated decision engine pipeline. The audit confirmed that the engine safely processes real production dataset records, preserves explicit missing metadata without synthetic defaults or manufactured financial certainty, strictly prevents consequential actions (`BUY`/`ACCUMULATE`/`SELL`) when evidence is missing or unvalidated, and propagates complete provenance and financial explanations end-to-end.

---

## 1. Audit Objectives & Baseline

- **Objective**: Forensically audit the F.11.1 integrated decision engine to verify action safety, partial-data safety, score/confidence separation, static fallbacks, determinism, and real-data provenance.
- **Baseline Test Suite**: `625 passed` (Phase F.11.1 baseline).
- **Final Test Suite**: `632 passed` (7 new safety audit tests added in `tests/financial/test_phase_f11_1_1_decision_safety_audit.py`).
- **Methodology Integrity**: Zero changes were made to financial scoring formulas, Fund Quality weights, Risk Capacity, Risk Tolerance, Risk Alignment, Suitability, Portfolio Need, Economic Benefit, or Action decision semantics.

---

## 2. Action State Forensic Matrix

The canonical decision orchestrator ([`integration/orchestrator.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/integration/orchestrator.py)) generates the following 8 canonical Action states based on strict evidence prerequisites:

| Action State | Generation Condition | Required Evidence | Suitability Requirement | Economic Benefit Requirement | Portfolio Need Requirement | Missing Metadata Coexistence | Consequential / Non-Consequential |
|---|---|---|---|---|---|---|---|
| **`NO_ACTION`** | Default safety outcome when inputs/evidence are missing, invalid, or no portfolio gap exists. | Input record & risk profile present. | `SUITABLE` or `ANY` | Not required or `BENEFIT_UNCERTAIN` | `NO_MATERIAL_NEED` or invalid evidence | Permitted (Routes to `NO_ACTION`) | Non-Consequential |
| **`HOLD`** | Incumbent holding in good standing without need to rebalance or switch. | Valid position & holding data. | `SUITABLE` | `NO_EVALUABLE_CHANGE` / `NEUTRAL` | Position owned | Permitted (TER/Riskometer/Benchmark `None`) | Non-Consequential |
| **`MONITOR`** | Mild deterioration detected in holding without validated replacement. | Position data & mild deterioration signal. | `SUITABLE` | `BENEFIT_UNCERTAIN` | Position owned | Permitted | Non-Consequential |
| **`REVIEW`** | Material deterioration, missing tax info, or high switching cost preventing SELL. | Position data & material deterioration. | `SUITABLE` | `BENEFIT_UNCERTAIN` / tax missing | Position owned | Permitted | Non-Consequential |
| **`INSUFFICIENT_INFORMATION`** | Missing mandatory investor profile or risk alignment inputs. | Incomplete investor/risk inputs. | `INSUFFICIENT_INFORMATION` | Unchecked | Unchecked | Mandatory profile fields missing | Non-Consequential |
| **`BUY`** | All 7 tiers satisfied; candidate capable, suitable, economically beneficial, and quality evidence valid. | Complete 7-tier evidence lineage. | `SUITABLE` | `ECONOMICALLY_BENEFICIAL` | `NEED_IDENTIFIED` & `CAN_FULFILL` | Prohibited (Missing FQ evidence blocks BUY) | **Consequential Transaction** |
| **`ACCUMULATE`** | Valid `BUY` path constrained by affordability limits. | Complete 7-tier evidence + affordability cap. | `SUITABLE` | `ECONOMICALLY_BENEFICIAL` | `NEED_IDENTIFIED` & `AFFORDABILITY_CONSTRAINED` | Prohibited | **Consequential Transaction** |
| **`SELL`** | Incumbent material deterioration + validated replacement + net economic benefit. | Position + validated switch + tax/cost evidence. | `SUITABLE` (replacement) | `ECONOMICALLY_BENEFICIAL` | Switch justified | Prohibited (Missing tax/cost blocks SELL) | **Consequential Transaction** |

---

## 3. Missing-Data Safety Matrix (Combinations A–G)

Evaluated all 7 combinations of missing metadata fields (`TER`, `Riskometer`, `Benchmark`) against live production dataset records:

| Combination | TER | Riskometer | Benchmark | Fund Quality Score | Fund Quality Confidence | Suitability Status | Actionability | Action State | Decision Explanation Summary |
|---|---|---|---|---|---|---|---|---|---|
| **Combo A** | `None` | `VERY_HIGH` | `NIFTY 50 TRI` | Evaluated (Rescaled) | Complete | `SUITABLE` | Dependent | `NO_ACTION` | Rescaled active weights; TER missing explicit `None`. Score alone cannot buy. |
| **Combo B** | `0.75%` | `None` | `NIFTY 50 TRI` | Evaluated | Complete | `SUITABLE` | Dependent | `NO_ACTION` | Riskometer missing explicit `None`. No synthetic risk label manufactured. |
| **Combo C** | `0.75%` | `VERY_HIGH` | `None` | Evaluated | Complete | `SUITABLE` | Dependent | `NO_ACTION` | Benchmark missing explicit `None`. Relative benchmark analysis skipped safely. |
| **Combo D** | `None` | `None` | `NIFTY 50 TRI` | Evaluated (Rescaled) | Complete | `SUITABLE` | Dependent | `NO_ACTION` | TER + Riskometer missing explicit `None`. Zero synthetic defaults introduced. |
| **Combo E** | `None` | `VERY_HIGH` | `None` | Evaluated (Rescaled) | Complete | `SUITABLE` | Dependent | `NO_ACTION` | TER + Benchmark missing explicit `None`. Cost & relative benchmark skipped. |
| **Combo F** | `0.75%` | `None` | `None` | Evaluated | Complete | `SUITABLE` | Dependent | `NO_ACTION` | Riskometer + Benchmark missing explicit `None`. |
| **Combo G** | `None` | `None` | `None` | Evaluated (Rescaled) | Complete | `SUITABLE` | Dependent | `NO_ACTION` | All 3 metadata fields explicitly `None`. Purchase prohibited due to partial evidence. |

---

## 4. Adversarial Safety Scenarios

### A. SELL Safety (Score Alone CANNOT Trigger SELL)
Constructed 8 adversarial cases:
1. Very low Fund Quality Score + missing metadata -> Evaluates to `NO_ACTION` / `HOLD`.
2. Very low Fund Quality Score + low confidence -> Evaluates to `MONITOR`.
3. Very low Fund Quality Score + no suitable replacement -> Evaluates to `REVIEW`.
4. Very low Fund Quality Score + unknown Economic Benefit -> Evaluates to `REVIEW`.
5. Very low Fund Quality Score + unsuitable replacement -> Evaluates to `REVIEW`.
6. Very low Fund Quality Score + high switching cost -> Evaluates to `REVIEW`.
7. Very low Fund Quality Score + missing tax cost -> Evaluates to `REVIEW`.
8. Very low Fund Quality Score + incomplete evidence -> Evaluates to `NO_ACTION` / `REVIEW`.
*Result*: 0 / 8 cases produced `SELL`. Fund Quality Score alone **NEVER** triggers `SELL`.

### B. BUY / ACCUMULATE Safety (Score Alone CANNOT Trigger BUY)
Constructed 8 adversarial cases:
1. Very high Fund Quality Score + missing TER -> Evaluates to `NO_ACTION`.
2. Very high Fund Quality Score + missing Riskometer -> Evaluates to `NO_ACTION`.
3. Very high Fund Quality Score + missing Benchmark -> Evaluates to `NO_ACTION`.
4. Very high Fund Quality Score + low Confidence -> Evaluates to `NO_ACTION`.
5. Very high Fund Quality Score + unsuitable candidate -> Evaluates to `NO_ACTION`.
6. Very high Fund Quality Score + missing Portfolio Need (`NO_MATERIAL_NEED`) -> Evaluates to `NO_ACTION`.
7. Very high Fund Quality Score + candidate cannot fulfill need -> Evaluates to `NO_ACTION`.
8. Very high Fund Quality Score + unknown Economic Benefit -> Evaluates to `NO_ACTION`.
*Result*: 0 / 8 cases produced `BUY` or `ACCUMULATE`. High score alone **NEVER** triggers `BUY`.

---

## 5. Static Fallback Audit

Executed codebase-wide search across `scoring/`, `risk/`, `action/`, `portfolio/`, `integration/`, `models/`, `data/`:
- **Search Patterns**: `or 0`, `or "MODERATE"`, `or "LOW"`, `or "HIGH"`, `or 0.0`, default TER/Riskometer/Benchmark.
- **Audit Findings**:
  - `risk/tolerance_engine.py`: Uses `or 0.25`, `or 0.40`, `or 0.20` strictly as internal fallback defaults for externalized configuration parameters in `config/risk/tolerance_config.py`. Classified: `SAFE_CONFIG_PARAMETER`.
  - `risk/capacity_engine.py`: Uses `or 0.0`, `or 0.15`, `or 0.50` strictly for externalized configuration parameters in `config/risk/capacity_config.py`. Classified: `SAFE_CONFIG_PARAMETER`.
  - `risk/alignment_engine.py`: Uses `or 0.70`, `or 0.85` strictly for externalized config thresholds. Classified: `SAFE_CONFIG_PARAMETER`.
  - **Zero Unsafe Production Fallbacks**: No code attempts to replace `ter_value`, `riskometer_label`, or `benchmark_name` with synthetic values.

---

## 6. Real-Data Forensic Audit

Audited 10 genuine production schemes from live AMFI dataset (`NAVAll.txt`):

| # | AMFI Code | Scheme Name | Category | TER | Riskometer | Benchmark | Action State | Provenance URL |
|---|---|---|---|---|---|---|---|---|
| 1 | `120503` | Axis Long Term Equity Fund - Direct - Growth | ELSS | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |
| 2 | `119551` | ABSL Banking & PSU Debt Fund - Direct - Growth | Debt - Banking & PSU | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |
| 3 | `120505` | Axis Children's Gift Fund - Direct - Growth | Solution - Children's | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |
| 4 | `119841` | ICICI Prudential Bluechip Fund - Direct - Growth | Large Cap | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |
| 5 | `118834` | SBI Small Cap Fund - Direct - Growth | Small Cap | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |
| 6 | `119775` | HDFC Mid-Cap Opportunities Fund - Direct - Growth | Mid Cap | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |
| 7 | `119598` | Nippon India Small Cap Fund - Direct - Growth | Small Cap | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |
| 8 | `120468` | Kotak Emerging Equity Fund - Direct - Growth | Mid Cap | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |
| 9 | `119061` | Bandhan Sterling Value Fund - Direct - Growth | Value / Flexi | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |
| 10 | `119363` | Tata Digital India Fund - Direct - Growth | Sectoral / IT | `None` | `None` | `None` | `NO_ACTION` | `https://www.amfiindia.com/spages/NAVAll.txt` |

*Verification*: Every real scheme preserves explicit `None` for missing metadata, attaches source provenance (`AMFI_OFFICIAL`), and evaluates cleanly to `NO_ACTION` with explicit missing-data explanation.

---

## 7. Provenance, Explanation, & Determinism Verification

1. **Provenance Audit**: Every `EndToEndDecisionResult` output preserves `canonical_scheme_id` (`CAN_AMFI_{code}`), `investor_id`, `goal_id`, `observation_timestamp`, `decision_timestamp_utc`, methodology version dictionary, and source provenance.
2. **Explanation Audit**: Explanations explicitly answer: (a) what was evaluated, (b) available vs missing evidence, (c) Fund Quality & Confidence status, (d) Suitability status, (e) Portfolio Need state, (f) Economic Benefit state, and (g) why no stronger action was taken.
3. **Determinism**: Evaluated 100 repeated runs of identical inputs. Output matching was 100% deterministic with zero variance in action state, status, or explanation strings.
4. **Temporal Safety**: Current observation dates remain strictly point-in-time; historical NAV dates are preserved; no current metadata is represented as historical.

---

## 8. Production Execution Boundary Verification

- **Order Placement**: `UNAUTHORIZED` (No broker/exchange integration code exists).
- **SIP Creation**: `UNAUTHORIZED`.
- **Switch Execution**: `UNAUTHORIZED`.
- **Portfolio Mutation**: `UNAUTHORIZED`.
- **Transaction APIs**: `UNAUTHORIZED` (Zero trade execution modules present).

---

## 9. Final Status & Acceptance Criteria Checklist

| Acceptance Criteria | Verified Status |
|---|---|
| 1. Missing metadata cannot become synthetic values (`None != 0`). | **PASS** |
| 2. Missing metadata cannot create false financial certainty. | **PASS** |
| 3. Fund Quality Score alone cannot trigger SELL. | **PASS** |
| 4. Fund Quality Score alone cannot trigger BUY. | **PASS** |
| 5. Fund Quality Score alone cannot trigger ACCUMULATE. | **PASS** |
| 6. Required evidence insufficiency is represented explicitly. | **PASS** |
| 7. Low Confidence remains distinct from low Score. | **PASS** |
| 8. Actionability remains distinct from Score and Confidence. | **PASS** |
| 9. Economic Benefit does not fabricate positive switching economics. | **PASS** |
| 10. Suitability constraints remain effective. | **PASS** |
| 11. Portfolio Need constraints remain effective. | **PASS** |
| 12. Quarantined/invalid records remain protected. | **PASS** |
| 13. Provenance survives end-to-end. | **PASS** |
| 14. Explanations disclose material missing evidence. | **PASS** |
| 15. Historical/current metadata remains temporally correct. | **PASS** |
| 16. Results are 100% deterministic. | **PASS** |
| 17. No unsafe financial fallbacks exist in production paths. | **PASS** |
| 18. Real production records were independently audited. | **PASS** |
| 19. Adversarial safety tests pass. | **PASS** |
| 20. Full regression passes (`632 / 632 passed`). | **PASS** |
| 21. No financial methodology was changed. | **PASS** |
| 22. Production execution remains inaccessible. | **PASS** |

---

## Final Status Declaration

```text
PHASE F.11.1.1 DECISION SAFETY & ACTIONABILITY FORENSIC AUDIT PASSED
```
