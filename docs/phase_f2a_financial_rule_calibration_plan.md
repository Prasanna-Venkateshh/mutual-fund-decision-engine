# Phase F.2A — Financial Rule Calibration & Empirical Validation Plan (Audit Corrected)

**Document Status:** GOVERNED CALIBRATION ROADMAP (AUDIT CORRECTED VIA PHASE F.2B)  
**Version:** `1.1.0`  
**Phase:** Phase F.2A / Phase F.2B — Financial Rule Research & Calibration

---

## 1. Executive Summary

This document specifies the multi-layer validation and empirical calibration roadmap required before provisional financial suitability parameters can be transitioned to validated production rules.

Following the Phase F.2B audit, all provisional parameters are explicitly designated as **Configurable Policy Defaults** or **Product Heuristics** that require empirical calibration prior to live deployment.

---

## 2. Five-Layer Validation Framework

To prevent misrepresenting software testing as empirical financial validation, validation is explicitly separated into 5 distinct domains:

```
FIVE-LAYER VALIDATION FRAMEWORK
  ├── Layer 1: Software & Logic Validation (Unit tests, edge case assertions, deterministic outputs)
  ├── Layer 2: Mathematical Validation (Range bounds, min/max matrix math, non-negative bounds)
  ├── Layer 3: Behavioral Questionnaire Validation (Consistency checks, scenario choice clarity)
  ├── Layer 4: Financial Methodology Validation (Fiduciary alignment, lower-of-two rule compliance)
  └── Layer 5: Empirical Calibration (Empirical demographic data, market cycle backtesting)
```

---

## 3. Calibration Requirements per Layer

### Layer 1 & 2 — Software & Mathematical Validation
- **Scope:** Completed in Phase F.2 (`tests/financial/test_suitability_contracts.py`).
- **Verified Properties:** Dataclass immutability, missing input handling (`Missing != 0`), invalid parameter rejection, SQLite persistence roundtrip.

### Layer 3 — Behavioral Questionnaire Validation
- **Scope:** Validates that behavioral risk scenarios ($RT-01$) generate consistent psychometric responses across user profiles.
- **Methodology:**
  1. Pilot test a 3-scenario questionnaire ($15\%$ immediate drawdown, $25\%$ prolonged stagnation, volatility trade-off choice) across 100+ sample responses.
  2. Compute scale reliability (Cronbach's Alpha \(\alpha\)). If \(\alpha \ge 0.70\), questionnaire scale reliability is confirmed.
  3. Evaluate individual response consistency. Contradictory responses fall back to the conservative lower tier and reduce `behavioral_consistency_score`.

### Layer 4 — Financial Methodology Validation
- **Scope:** Fiduciary alignment and lower-of-the-two risk constraint verification.
- **Methodology:**
  1. Verify that `Effective Risk Alignment = Min(Capacity, Tolerance)` is strictly enforced under all 25 Capacity $\times$ Tolerance matrix combinations.
  2. Verify that high behavioral risk tolerance **never** overrides low financial capacity.
  3. Verify that time-horizon ceilings ($H < 1.0$ Year \(\rightarrow\) Debt Only) strictly cap asset risk.

### Layer 5 — Empirical Calibration (Pending Production Deployment)
- **Scope:** Empirical calibration of provisional numerical thresholds using historical Indian market data and retail household finance statistics.
- **Required Calibration Tasks:**
  1. **Debt Servicing Tiers (RC-01 Calibration):** Calibrate Net Debt-to-Income (DTI) risk capacity tiers against RBI retail credit default and cash-flow shock survival statistics.
  2. **Emergency Cover Calibration (RC-02 Calibration):** Calibrate liquid emergency reserve requirements ($3-12$ months) against Indian household out-of-pocket shock frequency data.
  3. **Category Horizon Recovery Calibration (H-01 / H-02 Calibration):** Run rolling-return drawdown recovery simulations across AMFI 15-year NAV data (2010–2025) for Equity, Debt, and Hybrid categories to establish 99% confidence recovery horizons.

---

## 4. Calibration Execution Schedule

```
Phase F.2:  Data Contracts & Persistence (COMPLETED)
Phase F.2A: Research, Governance & Calibration Specification (COMPLETED)
Phase F.2B: Evidence Citation & Claim Audit (COMPLETED IN PHASE F.2B)
    ↓
Phase F.3:  Risk Capacity Engine (Implements Layer 1 & 4 Validation; Uses Provisional Defaults)
Phase F.4:  Risk Tolerance Engine (Implements Layer 1, 3 & 4 Validation; Uses Multi-Scenario Matrix)
Phase F.5:  Risk Alignment Orchestrator (Implements Lower-of-Two Rule)
Phase F.6:  Goal Horizon Engine (Implements Time-Horizon Ceilings)
Phase F.7:  Affordability Engine (Implements Sustainable Capacity Formula)
    ↓
Layer 5 Empirical Calibration Phase (Prior to Live Production Deployment):
  - AMFI 15-Year Rolling Return Recovery Simulation
  - RBI Household Demographic Survey Calibration
  - Regulatory Fiduciary Audit Approval
```
