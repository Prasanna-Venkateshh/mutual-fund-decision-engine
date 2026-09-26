# Phase F.3.4.2 — Suitability Domain Ownership Matrix Document

**Phase:** Phase F.3.4.2 — Suitability Data Contracts, Input Architecture & Ownership Governance  
**Date:** 2026-09-10 UTC  
**Status:** Approved Ownership Matrix  
**Final Decision:** `PHASE F.3.4.2 ACCEPTED WITH PROVISIONAL METHODOLOGY`  
**Scope:** Definitive domain ownership matrix establishing subsystem boundaries, recalculation permissions, and authoritative sources.

---

## 1. Subsystem Ownership Matrix

| Financial / System Concept | Owning Subsystem | Suitability Engine Role | Recalculate in Suitability? | Authoritative Source / Model |
|---|---|---|---|---|
| Debt Servicing Ratio | Risk Capacity Engine | None (Processed upstream) | **NO** | [`risk/capacity_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_engine.py) |
| Emergency Reserve Coverage | Risk Capacity Engine | None (Processed upstream) | **NO** | [`risk/capacity_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_engine.py) |
| Sustainable Monthly Surplus | Risk Capacity Engine | None (Processed upstream) | **NO** | [`risk/capacity_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/capacity_engine.py) |
| Behavioral Risk Comfort Score | Risk Tolerance Engine | None (Processed upstream) | **NO** | [`risk/tolerance_engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/tolerance_engine.py) |
| Financial Risk Capacity Tier | Risk Capacity Engine | Read-only input to Alignment | **NO** | `RiskCapacityAssessmentResult` |
| Behavioral Risk Tolerance Tier | Risk Tolerance Engine | Read-only input to Alignment | **NO** | `RiskToleranceAssessmentResult` |
| Aligned Risk Envelope | Risk Alignment Engine | Primary Risk Bound Constraint | **NO** | `RiskAlignmentAssessmentResult` |
| Fund Risk-Adjusted Returns | Fund Quality Engine | Read-only Merit Input | **NO** | `FundQualityAssessmentResult` |
| Category Peer Ranking & Score | Fund Quality Engine | Read-only Merit Input | **NO** | `FundQualityAssessmentResult` |
| Track Record Length / Maturity | Metrics Engine | Read-only Maturity Input | **NO** | `FundMaturityResult` |
| Statutory Lock-In Metadata | Scheme Master / AMFI | Contractual Lock-In Constraint | **NO** | `SchemeMaster` / AMFI Feed |
| Fund Riskometer Classification | Data Ingestion / SEBI | Read-only Fund Risk Input | **NO** | `FundRiskProfile` / SEBI Feed |
| Goal Time Horizon & Target Date | Goal Profile Subsystem | Timeline Compatibility Input | **NO** | `GoalProfileSnapshot` |
| Portfolio Asset/AMC Exposure | Portfolio Subsystem | Read-only Context Input | **NO** | `PortfolioHoldingContext` |
| Portfolio Overlap Matrix | Portfolio Subsystem | Read-only Overlap Input | **NO** | `PortfolioHoldingContext` |
| SIP Affordability / Plan Calculation | Investment Plan / SIP Engine | Downstream Consumer | **NO** | Downstream SIP Engine |
| Portfolio Allocation Gap Reduction | Portfolio Need Engine | Downstream Consumer | **NO** | Downstream Portfolio Need Engine |
| After-Tax Switching Benefit | Tax / Cost Engine | Downstream Consumer | **NO** | Downstream Tax Engine |
| Transaction Action (Buy/Sell) | Economic Action Engine | Downstream Consumer | **NO** | Downstream Action Engine |

---

## 2. Governance Assertions

1. **Zero Upstream Recalculation:** Suitability consumes pre-computed results from upstream engines. Under no circumstances may the Suitability Engine re-run NAV calculations, questionnaire scoring, or financial ratio formulas.
2. **Zero Downstream Action Selection:** Suitability determines contextual appropriateness (`SUITABLE`, `NOT_SUITABLE`, etc.). Downstream action selection (`BUY`, `ACCUMULATE`, `HOLD`, `SELL`) is strictly owned by the Economic Action Engine.
3. **Immutable Contracts:** All data passed across subsystem boundaries must use frozen data contracts to prevent accidental state mutation.
