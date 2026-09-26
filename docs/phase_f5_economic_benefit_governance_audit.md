# Phase F.5 Economic Benefit Governance Audit (Verified - F.5.2)

## 1. Compliance Audit Matrix

| Governance Requirement | Governing Rule / Principle | Implementation / Spec Design | Verdict |
| :--- | :--- | :--- | :--- |
| **Tax Module Provenance** | Zero Tax Engine code implemented | `tax/rules.py` confirmed non-existent on disk; specification path only | 🟢 COMPLIANT |
| **Expected Improvement Terminology** | Conceptual $\neq$ Production input | `EXPECTED_IMPROVEMENT` is conceptual spec requirement; missing model = `BENEFIT_UNCERTAIN` | 🟢 COMPLIANT |
| **Monetary vs Friction Separation** | Qualitative friction $\neq$ Rupee cost | Friction affects confidence/actionability; never added to monetary cost | 🟢 COMPLIANT |
| **New-Money Governance** | No automatic `NEW_MONEY` preference | `NEW_MONEY` is evaluated alongside `SWITCH_EXISTING` on suitability & capacity | 🟢 COMPLIANT |
| **No-Need Semantics** | No Need $\neq$ Economic Harm | If `NO_MATERIAL_NEED`, outcome is `NO_EVALUABLE_CHANGE` (no false harm claimed) | 🟢 COMPLIANT |
| **Exit-Load Governance** | Scheme-specific & date-sensitive | Global 1% default eliminated; missing load marked `UNKNOWN` | 🟢 COMPLIANT |
| **Tax Parameter Governance** | Versioned & source-referenced | Statutory tax parameters separated from platform parameters & versioned | 🟢 COMPLIANT |
| **Formula Approval Governance** | Conceptual framework only | Conceptual relationship approved; production numerical formula deferred | 🟢 COMPLIANT |
| **Expected Improvement Governance**| Forward-looking model required | Historical CAGR substitution prohibited; missing model = `UNKNOWN` | 🟢 COMPLIANT |
| **Confidence Separation** | Magnitude vs Confidence separate | Confidence degrades on friction/uncertainty; no hidden thresholds | 🟢 COMPLIANT |
| **Action Isolation** | No Action recommendations | Zero `BUY`/`SELL`/`REBALANCE` enums emitted by Economic Benefit | 🟢 COMPLIANT |
| **Numerical Parameter Governance** | No arbitrary magic numbers | All thresholds marked `TBD` / `PROVISIONAL` or statutory in Parameter Register | 🟢 COMPLIANT |

---

## 2. Verified State Taxonomy & Decision Matrix

### State Taxonomy Rules:
- `NO_PORTFOLIO_NEED` $\rightarrow$ `NO_EVALUABLE_CHANGE` (does **not** imply `ECONOMICALLY_NOT_BENEFICIAL`).
- `UNKNOWN EXPECTED IMPROVEMENT` $\rightarrow$ `BENEFIT_UNCERTAIN` (does **not** default to zero or use trailing CAGR).
- `ECONOMICALLY_BENEFICIAL` & `ECONOMICALLY_NOT_BENEFICIAL` remain **conceptual outcomes** pending a validated production numerical methodology.

### Conflict Matrix:
- **Case A (No Need + Higher Quality Candidate):** `NO_EVALUABLE_CHANGE` (no portfolio need exists to justify change; no false harm claimed).
- **Case B (Need + Suitable Candidate + Positive Improvement + Known Costs):** Potentially `ECONOMICALLY_BENEFICIAL` (conceptual outcome).
- **Case C (Need + Positive Improvement + Monetary Costs Exceeding Improvement):** `ECONOMICALLY_NOT_BENEFICIAL` (conceptual outcome).
- **Case D (Expected Improvement Unknown):** `BENEFIT_UNCERTAIN`.
- **Case E (New Money vs Switch Existing):** Evaluate alternatives (`NEW_MONEY` vs `SWITCH_EXISTING` vs `REDISTRIBUTE_CONTRIBUTIONS`); no automatic preference.
- **Case F (Benefit Positive, Affordability Constrained):** `ECONOMICALLY_BENEFICIAL` + `AFFORDABILITY_CONSTRAINED` context flag.
- **Case G (Material Costs Unknown):** `BENEFIT_UNCERTAIN`.
