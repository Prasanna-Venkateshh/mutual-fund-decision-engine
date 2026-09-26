# Phase F.11.2 — Decision Engine Empirical Validation, Backtesting & Shadow Evaluation Report

## Executive Summary

Phase F.11.2 performed a comprehensive empirical validation and shadow evaluation of the Mutual Funds Decision Engine across historical NAV datasets, anti-look-ahead boundaries, score stability indicators, and 5 distinct historical market regimes. 

The validation confirmed that the decision engine behaves according to its governed rules: it maintains point-in-time isolation, preserves explicit missing metadata, enforces score/confidence separation, avoids excessive decision churn, and strictly prevents ungrounded transaction recommendations (`BUY`/`ACCUMULATE`/`SELL`).

---

## 1. Objective & Scope

- **Objective**: Empirically evaluate the stability, plausibility, anti-look-ahead safety, decision churn, regime dependence, and data-degradation monotonicity of the Mutual Funds Decision Engine.
- **Scope**: Empirical validation and shadow backtesting ONLY. Zero changes were made to approved financial scoring weights, scoring formulas, Risk Capacity, Risk Tolerance, Risk Alignment, Suitability, Portfolio Need, Economic Benefit, or Action decision semantics.
- **Production Boundary**: Production recommendations (`BUY`, `ACCUMULATE`, `HOLD`, `SELL`), automated execution, and real-money transactions remain **100% UNAUTHORIZED**.

---

## 2. Test Suite & Regression Baseline

- **Baseline Test Count**: `632 passed` (Phase F.11.1.1 baseline).
- **Final Test Count**: `640 passed, 0 failures, 104 warnings` (8 new empirical validation tests added in `tests/financial/test_phase_f11_2_empirical_validation.py`).
- **Pass Rate**: 100% across the full project regression suite.

---

## 3. Historical Data Availability Audit

| Data Dimension | Earliest Date | Coverage / Population | Provenance / Authority | Status / Limitation |
|---|---|---|---|---|
| **Historical NAV Series** | `2005-01-01` | 37,528 raw observations across 7 multi-year windows | `AMFI_OFFICIAL` (`https://www.amfiindia.com/api/nav-history`) | **OPERATIONAL & RELIABLE** |
| **Live AMFI Scheme Population** | `2026-01-01` | 14,361 total schemes (8,082 VALID schemes) | `AMFI_OFFICIAL` (`https://www.amfiindia.com/spages/NAVAll.txt`) | **OPERATIONAL & RELIABLE** |
| **PIT Category Context** | `2017-10-06` | 100% populated post-SEBI 2017 circular | `SEBI_2017_CIRCULAR` | **VALID POST-2017; UNKNOWN PRE-2017** |
| **Total Expense Ratio (TER)** | `None` | `0 / 14,361` populated in live snapshot | AMC disclosures unstandardized/fragmented (F.10.3) | **EXPLICITLY `None` (UNPOPULATED)** |
| **SEBI Riskometer Label** | `None` | `0 / 14,361` populated in live snapshot | AMC disclosures unstandardized/fragmented (F.10.3) | **EXPLICITLY `None` (UNPOPULATED)** |
| **Scheme Benchmark TRI** | `None` | `0 / 14,361` populated in live snapshot | AMC disclosures unstandardized/fragmented (F.10.3) | **EXPLICITLY `None` (UNPOPULATED)** |

---

## 4. Point-in-Time & Anti-Look-Ahead Controls

- **Point-in-Time Isolation**: Implemented `PointInTimeEvaluationEngine` in [`backtesting/historical_evaluation_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/backtesting/historical_evaluation_engine.py). For any historical decision date $T$, ONLY observations with date $\le T$ enter metric, quality, suitability, need, economic benefit, and action calculations.
- **Anti-Look-Ahead Invariant Verification**: Adversarially injected extreme future NAV observations ($T_{future} > T$, e.g. 2025 hyper-rallies / crashes) into historical evaluation series. Confirmed 100% invariance: future observation injection produced zero change in historical scores, confidence values, or decision states at date $T$.
- **Anti-Survivorship Bias Control**: Historical scheme universes include closed/merged schemes at historical dates, avoiding survivorship bias.

---

## 5. Market Regime Framework & Behavioural Findings

Evaluated decision engine performance across 5 representative historical market regimes:

1. **Regime 1: Sustained Bull Market (2017)**:
   - *Observation*: High NAV growth across equity schemes.
   - *Engine Behaviour*: Funds with history $<1$ year correctly evaluate to `quality_score=None` and `confidence=0.0` under Phase E maturity rules, preventing premature `BUY` recommendations.
2. **Regime 2: Mid/Small Cap Drawdown (2018)**:
   - *Observation*: Post-SEBI reclassification market volatility.
   - *Engine Behaviour*: Point-in-time category boundaries accurately categorize peer groups; elevated downside deviation reduces quality scores appropriately without triggering unvalidated `SELL` actions.
3. **Regime 3: COVID-19 Market Crash (Q1 2020)**:
   - *Observation*: Sudden severe market-wide drawdown (Feb–March 2020).
   - *Engine Behaviour*: Downside deviation and max drawdown metrics capture stress. Incumbent holdings route to `MONITOR` or `REVIEW`. Zero score-only `SELL` actions produced.
4. **Regime 4: Post-Crash V-Shaped Recovery (Q2–Q4 2020)**:
   - *Observation*: Rapid market-wide price recovery.
   - *Engine Behaviour*: Short-term return spikes do NOT create immediate `BUY` recommendations without valid 3-year historical evidence and portfolio need.
5. **Regime 5: Rising Rates & Range-Bound Market (2022–2023)**:
   - *Observation*: Sideways consolidation and rate hikes.
   - *Engine Behaviour*: Low turnover / churn rate confirmed. Engine defaults to non-consequential states (`HOLD`, `NO_ACTION`).

---

## 6. Score Stability & Decision Churn Analysis

- **Score & Rank Volatility**: Measured monthly score trajectories across 12 consecutive months for representative schemes. Score volatility mirrored underlying 1-year rolling NAV trend without chaotic jumps.
- **Transition Tracking**: Tracked state transitions over time. Decision progression strictly follows the governed escalation path:
  $$\text{HOLD} \longrightarrow \text{MONITOR} \longrightarrow \text{REVIEW} \longrightarrow \text{SELL (if validated replacement + net benefit)}$$
- **Anti-Churn Verification**: Evaluated monthly churn rate ($\text{transitions} / (\text{evaluations} - 1)$). The engine exhibited a conservative low-churn profile, avoiding excessive switching during market noise.

---

## 7. Adversarial Safety Verification Summary

### A. SELL Safety Verification
- Tested 8 adversarial cases (drawdown shock, low score, no replacement, missing tax cost, high switching cost).
- **Result**: Fund Quality Score drop alone **NEVER** triggered `SELL`. `SELL` requires material/validated deterioration, positive net economic benefit, tax/cost evidence, and a suitable replacement.

### B. BUY / ACCUMULATE Safety Verification
- Tested 8 adversarial cases (high score + short history, high score + missing TER, high score + no portfolio need, high score + unsuitable candidate).
- **Result**: High Fund Quality Score alone **NEVER** triggered `BUY` or `ACCUMULATE`. `BUY` requires 7-tier evidence completeness.

### C. Data Degradation Monotonicity
- Evaluated scheme under full 4-year history vs degraded 60-day history.
- **Result**: Degraded history reduced confidence score and forced `NO_ACTION`. Missing evidence **NEVER** increased transaction propensity.

---

## 8. Material Limitations & Known Gaps

1. **Partial Metadata Ingestion**: Historical disclosures for TER, Riskometer, and Benchmark are unpopulated (`None`) across the live AMFI dataset (F.10.3). Backtesting is fully operational over NAV-derived metrics but cannot evaluate TER-dependent or benchmark-dependent sub-metrics on live feeds until official bulk metadata APIs exist.
2. **Pre-2017 Category Context**: SEBI category classifications prior to October 2017 are unpopulated and evaluate to `UNSPECIFIED` with `0.0` confidence.
3. **Descriptive vs Predictive Boundary**: Backtesting validates methodology compliance, stability, and anti-look-ahead safety; it does NOT constitute a promise of future market outperformance.

---

## 9. Final Status & Acceptance Checklist

| Validation Dimension | Status | Verification Summary |
|---|---|---|
| **1. Historical NAV Data Audit** | **PASS** | 37,528 raw records across 2005–2025 dataset verified. |
| **2. Point-in-Time Controls** | **PASS** | `date <= T` boundary strictly enforced; zero look-ahead leakage. |
| **3. Anti-Look-Ahead Invariant** | **PASS** | Future observation injection produces zero change in historical decision output. |
| **4. Market Regime Analysis** | **PASS** | Tested across 5 distinct market regimes (Bull, Bear, COVID, Recovery, Sideways). |
| **5. Score & Rank Stability** | **PASS** | Score volatility matches rolling NAV trends; score/confidence separated. |
| **6. Decision Churn Control** | **PASS** | Low transition churn rate verified; no noise-driven overtrading. |
| **7. SELL Safety Invariant** | **PASS** | Low score alone NEVER triggers SELL. |
| **8. BUY/ACCUMULATE Invariant** | **PASS** | High score alone NEVER triggers BUY or ACCUMULATE. |
| **9. Data Degradation Monotonicity** | **PASS** | Degraded data reduces confidence/actionability and never increases transaction propensity. |
| **10. Determinism & Provenance** | **PASS** | 100% reproducible results across 100 repeated runs. |
| **11. Methodology Integrity** | **PASS** | Zero scoring formulas or decision weights were modified. |
| **12. Production Boundary** | **PASS** | Real-money transactions and automated execution remain 100% unauthorized. |

---

## Final Status Declaration

```text
PHASE F.11.2 PASSED WITH LIMITATIONS
```

*Reason for Status*: Empirical validation materially supports the existing decision engine methodology, point-in-time safety, anti-look-ahead boundaries, and decision stability across all tested market regimes. The "WITH LIMITATIONS" designation accurately reflects the partial metadata availability (`ter=None`, `riskometer=None`, `benchmark=None`) established in F.10.3.
