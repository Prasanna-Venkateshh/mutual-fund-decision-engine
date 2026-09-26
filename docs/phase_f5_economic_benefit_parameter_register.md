# Phase F.5 Economic Benefit Parameter Governance Register (Verified - F.5.2)

## 1. Parameter Governance Register

All non-statutory parameters listed below are explicitly marked **TBD** or **PROVISIONAL**. Zero arbitrary numerical thresholds or global exit-load assumptions have been approved for production use in Phase F.5.

### Section A: Statutory Tax & Regulatory Parameters (Source-Governed & Versioned)

Proposed future location for production tax engine configuration: `tax/rules.py` (Currently non-existent on disk; specification target only).

| Parameter ID | Parameter Description | Statutory Value | Governing Authority | Reference / Effective Date | Version / Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PAR-STAT-01` | Equity LTCG Holding Period Cutoff | 12 months (365 days) | Income Tax Act, 1961 | Sec 2(42A) | `STATUTORY_GOVERNED` (v2024.1) |
| `PAR-STAT-02` | Equity STCG Tax Rate | 20.0% (+ cess/surcharge)| Finance Act, 2024 | Sec 111A | `STATUTORY_GOVERNED` (v2024.1) |
| `PAR-STAT-03` | Equity LTCG Tax Rate | 12.5% (above ₹1.25L) | Finance Act, 2024 | Sec 112A | `STATUTORY_GOVERNED` (v2024.1) |
| `PAR-STAT-04` | Mutual Fund Purchase Stamp Duty | 0.005% | Indian Stamp Act, 1899 | Sec 9A (July 2020) | `STATUTORY_GOVERNED` (v2020.1) |
| `PAR-STAT-05` | Debt STCG/LTCG Holding Period | Slab rate / 36 months | Income Tax Act, 1961 | Sec 50AA (April 2023) | `STATUTORY_GOVERNED` (v2023.1) |

### Section B: Platform Methodology Parameters (TBD & Provisional)

| Parameter ID | Parameter Description | Candidate Value Range | Validation Status | Governing Authority |
| :--- | :--- | :--- | :--- | :--- |
| `PAR-EB-01` | Minimum Incremental Benefit Threshold | 0.25% - 1.00% p.a. | `TBD` / `REQUIRES EXTERNAL VALIDATION` | Financial Methodology Committee |
| `PAR-EB-02` | Minimum Absolute Monetary Benefit (₹) | ₹500 - ₹2,500 | `TBD` / `REQUIRES EXTERNAL VALIDATION` | Financial Methodology Committee |
| `PAR-EB-08` | Qualitative Friction Rating Scale | Non-monetary scale | `PROVISIONAL` | Governance Architecture |
| `PAR-EB-09` | High Confidence Benefit Horizon | 3 - 5 years | `TBD` / `REQUIRES EXTERNAL VALIDATION` | Quantitative Research Team |
| `PAR-EB-10` | Break-even Payback Period Cutoff | 12 - 24 months | `TBD` / `REQUIRES EXTERNAL VALIDATION` | Quantitative Research Team |

---

## 2. Prohibited Parameters & Governance Rules
- **Prohibited:** Global default exit-load rules (e.g. `1% < 365d`) are explicitly **PROHIBITED**. Exit loads are strictly scheme-specific and date-sensitive.
- Statutory parameters (`PAR-STAT-01` through `PAR-STAT-05`) are versioned statutory values, maintained in an external tax rules repository once created.
- Behavioral and economic thresholds (`PAR-EB-01`, `PAR-EB-02`, `PAR-EB-09`, `PAR-EB-10`) **MUST NOT** be embedded as production constants without prior empirical backtesting and formal governance sign-off.
