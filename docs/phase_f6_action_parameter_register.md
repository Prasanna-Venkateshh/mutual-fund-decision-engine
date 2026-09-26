# Phase F.6 Action Parameter Governance Register (Corrected - F.6.1)

## 1. Parameter Governance & Validation Register
All parameters listed below are explicitly marked **VALIDATION REQUIRED**. Zero arbitrary production constants, magic thresholds, or statutory tax rates are owned by the Action layer in Phase F.6.1.

### Section A: Action Orchestration Parameters (Research Hypotheses Only - NOT Production Defaults)

The candidate ranges listed below are research hypotheses/examples only and are explicitly **PROHIBITED** from production implementation without formal empirical backtesting and governance approval.

| Parameter ID | Parameter Description | Research Hypothesis / Example Range | Validation Status | Owning Domain |
| :--- | :--- | :--- | :--- | :--- |
| `PAR-ACT-01` | Minimum Quality Score Drop for `MONITOR` | 5.0 - 10.0 points | `VALIDATION REQUIRED` | Metric & Scoring Governance |
| `PAR-ACT-02` | Persistent Underperformance Duration | 2 - 4 consecutive quarters | `VALIDATION REQUIRED` | Performance Research Team |
| `PAR-ACT-03` | Minimum Net Economic Benefit for `SELL` | 0.50% - 1.50% p.a. | `VALIDATION REQUIRED` | Economic Benefit Engine |
| `PAR-ACT-04` | Maximum Category Concentration Limit | 25.0% - 40.0% portfolio | `VALIDATION REQUIRED` | Portfolio Governance |
| `PAR-ACT-05` | Actionability Criterion Threshold | Unspecified (Scale 0.0 - 1.0) | `VALIDATION REQUIRED` | Quality & Evidence Architecture |
| `PAR-ACT-06` | Staged Entry Allocation Tranche (%) | 25.0% - 33.3% per tranche | `VALIDATION REQUIRED` | Execution Strategy |

---

## 2. Decoupled Tax & Cost Domain Ownership (Consumed by Action)

Statutory tax rates, LTCG/STCG holding period cutoffs, stamp duty rates, and exit loads are **NOT** Action-layer parameters. They are owned strictly by the future Tax/Cost Engine:

$$\text{ACTION CONSUMES VALIDATED TAX/COST ASSESSMENT}$$

| External Tax/Cost Parameter | Owning Domain / Authority | Action Consumption Behavior |
| :--- | :--- | :--- |
| **Equity LTCG Holding Period** | Tax/Cost Layer (Income Tax Act, Sec 2) | Action consumes generic *"statutory holding-period classification"* supplied by Tax/Cost layer. |
| **Equity STCG / LTCG Rates** | Tax/Cost Layer (Finance Act, 2024) | Action consumes net tax liability output. Action never hardcodes rates. |
| **Purchase Stamp Duty** | Tax/Cost Layer (Indian Stamp Act) | Action consumes transaction cost output. Action never hardcodes rates. |
| **Scheme Exit Load Schedule** | Tax/Cost Layer (AMFI / Scheme Master) | Action consumes exit load output. Action never assumes global 1% load rules. |

---

## 3. Governance Rules & Prohibitions
1. **No Production Defaults:** Parameters `PAR-ACT-01` through `PAR-ACT-06` are **NOT** production defaults and **MUST NOT** be implemented in production code without empirical validation.
2. **Tax Rule Isolation:** Action shall **never** hardcode statutory tax rates, holding periods (e.g. "365 days"), or stamp duty rates.
3. **Missing Tax/Cost Data:** If a required Tax/Cost assessment is unavailable (`UNKNOWN`), Action **must not** invent values, **must not** assume zero, and **must** downgrade/withhold consequential recommendations.
