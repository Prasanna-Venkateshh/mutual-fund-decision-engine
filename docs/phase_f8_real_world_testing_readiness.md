# PHASE F.8 — REAL-WORLD TESTING READINESS SPECIFICATION

## Executive Summary

This specification defines the 7 progressive stages (Stage A through Stage G) required to transition the India mutual-fund decision engine from software specification to live production readiness.

> [!CAUTION]
> Passing Phase F.8 does **NOT** authorize real-money transaction execution or live retail financial advice. Phase F.8 establishes the governance infrastructure required to conduct real-world data validation safely.

---

## 1. The 7 Progressive Real-World Testing Stages

```
STAGE A: Real Data Smoke Test
   │
   ▼
STAGE B: Real Dataset Construction
   │
   ▼
STAGE C: Historical Backtest & Shadow Evaluation
   │
   ▼
STAGE D: Current-Market Shadow Mode
   │
   ▼
STAGE E: Human-Supervised Pilot
   │
   ▼
STAGE F: Production Recommendation Eligibility
   │
   ▼
STAGE G: Controlled Transaction Execution (Future Phase)
```

---

## 2. Detailed Stage Definitions & Gate Criteria

### 2.1 Stage A — Real Data Smoke Test
- **Description**: Technical validation of live network adapters, API connections (AMFI, NSE/BSE, AMC Direct), parser stability, and schema validation on actual market data payloads without executing financial scoring or decision engines.
- **Entry Gate**: Unit and integration test suite 100% green; Source Registry populated.
- **Exit Gate**: Continuous EOD data retrievals executed over a formal testing period without unhandled parser exceptions or silent field corruptions.

### 2.2 Stage B — Real Dataset Construction
- **Description**: Construction of a production-grade historical mutual-fund dataset covering target schemes across historical NAVs, TER series, SEBI categories, Riskometers, and benchmark indices.
- **Entry Gate**: Stage A completion; Coverage Ledger infrastructure active.
- **Exit Gate**: Coverage Ledger verifies scheme-level historical completeness across target universe with 100% scheme identity resolution (zero ambiguous identity matches).

### 2.3 Stage C — Historical Backtest & Shadow Evaluation
- **Description**: Processing historical market snapshots through the decision engine pipeline to verify financial behavior, decision stability, turnover rates, and anti-churn guardrails across historical market cycles.
- **Entry Gate**: Stage B dataset sign-off; Audit trail logger active.
- **Exit Gate**: Zero financial logic crashes, zero look-ahead PIT violations, zero non-beneficial switches, and validated low-turnover rates.

### 2.4 Stage D — Current-Market Shadow Mode
- **Description**: Running the engine daily against live current-market EOD data in shadow mode (parallel to existing operations). Output decisions are logged for audit but **NOT** presented to investors or used for advice.
- **Entry Gate**: Stage C backtest acceptance; Real-time logging infrastructure active.
- **Exit Gate**: Sustained period of stable daily shadow evaluations with zero safety invariant violations.

### 2.5 Stage E — Human-Supervised Pilot
- **Description**: Evaluation of actual anonymized investor profiles and portfolio contexts where engine output recommendations are subjected to 100% mandatory review and sign-off by qualified human financial advisors / domain experts.
- **Entry Gate**: Stage D shadow mode completion; Advisor review dashboard active.
- **Exit Gate**: Human review confirms full alignment on safety, suitability, and economic benefit logic across a diverse set of representative investor cases.

### 2.6 Stage F — Production Recommendation Eligibility
- **Description**: The decision engine is authorized to generate automated informational mutual-fund recommendations for retail investors under applicable regulatory disclosures.
- **Entry Gate**: Stage E pilot completion; Independent regulatory compliance sign-off; Full F.8–F.13 governance sign-off.
- **Exit Gate**: Continuous production operation with real-time Data Quality Dashboard monitoring.

### 2.7 Stage G — Controlled Transaction Execution (Future Phase)
- **Description**: Automated routing of authorized recommendations to order routing portals / payment gateways / AMC transaction engines.
- **Scope Note**: **STRICTLY OUTSIDE THE SCOPE OF PHASE F.8**. Requires separate future architectural specification and regulatory authorization.

---

## 3. Transition Gate Summary Matrix

| Stage | Data Ingest | Financial Engine | Output Action | Human Review | Money Transfer | Gate Sign-off Required |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage A** | Real Live | Disabled | Discarded | Technical Only | **Prohibited** | Data Engineering Lead |
| **Stage B** | Real Historic | Disabled | Dataset Only | Data QA Lead | **Prohibited** | Data Governance Lead |
| **Stage C** | Real Historic | Enabled | Logged Backtest | Quantitative QA | **Prohibited** | Financial Domain Lead |
| **Stage D** | Real Live EOD | Enabled | Logged Shadow | Compliance Audit | **Prohibited** | Chief Risk Officer |
| **Stage E** | Real Live | Enabled | Advisor Review | 100% Mandatory | **Prohibited** | Principal Investment Officer |
| **Stage F** | Real Live | Enabled | Recommendation | Audited Sampling | **Prohibited** | Investment Committee |
| **Stage G** | Real Live | Enabled | Execution Order | Automated / Exception | Controlled | Board / Regulators |
