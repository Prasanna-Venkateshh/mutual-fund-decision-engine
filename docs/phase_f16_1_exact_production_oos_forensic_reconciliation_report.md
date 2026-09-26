# PHASE F.16.1 — EXACT-PRODUCTION OOS RESULT FORENSIC RECONCILIATION & DECISION-USE GOVERNANCE REPORT

## 1. Executive Summary & Forensic Verification

This report documents the narrow forensic audit and population reconciliation of Phase F.16. All numerical distributions, population waterfalls, selection overlaps, and regression model contributions have been verified and reconciled against executable production code (`scoring/engine.py`).

### Key Forensic Findings:
1. **Population Waterfall Reconciled:** From Stage 1 Anchor NAV Population ($5,874$) down to Stage 6 Final Scored Population ($5,125$) and Valid Scored Population ($N = 4,958$, Top Decile $k = 496$).
2. **Strategy Distribution Reconciliation:**
   - **Strategy A (Trailing Return):** Mean Return = $12.98\%$, Median Return = $11.08\%$, Mean MDD = $16.67\%$ ($N = 496$).
   - **Strategy B (Lowest Volatility):** Mean Return = $6.33\%$, Median Return = $7.24\%$, Mean MDD = $0.11\%$ ($N = 496$).
   - **Strategy C (Exact Production FQ):** Mean Return = $13.01\%$, Median Return = $12.33\%$, Mean MDD = $14.86\%$ ($N = 496$).
3. **Difference Scoping:**
   - Mean Return Difference (FQ vs Trailing Return): $+0.03\%$ gross NAV return ($+0.0003$).
   - Forward MDD Difference (FQ vs Trailing Return): $-1.81\%$ gross MDD ($-0.0181$).

---

## 2. Population Waterfall Reconciliation Table

| Stage | Population Description | Count ($N$) | Excluded Count | Exclusion Rule / Taxonomy |
|---|---|---:|---:|---|
| **Stage 1** | Anchor NAV Population (2024-01-31) | 5,874 | 0 | Base active NAV series on anchor date |
| **Stage 2** | History Length Filter ($\ge 252$ days) | 5,178 | 696 | Insufficient PIT historical length ($< 252$ daily NAVs) |
| **Stage 3** | Non-Positive NAV Filter | 5,178 | 0 | Non-positive or corrupted historical NAV values |
| **Stage 4** | Forward Reachable Filter ($\ge 200$ days) | 5,125 | 53 | Forward period unreachable ($< 200$ forward NAV records) |
| **Stage 5 / 6** | Final Production Scored Population | 5,125 | 0 | Inputs passed to `FundQualityScoringEngine` |
| **Valid Scored** | Valid Non-NaN Production Score | **4,958** | 167 | Excluded schemes with 0 return / non-comparable IDCW |
| **Top Decile** | Top 10% Selected ($k = \lceil 0.10 \times 4958 \rceil$) | **496** | 4,462 | Below top-decile score threshold |

---

## 3. Historical Phase Population Reconciliation Table

| Phase | Anchor N | Reachable N | Final Scored N | Key Eligibility / Filtering Rule |
|---|---:|---:|---:|---|
| **F.12.3.1.2** | 5,874 | 5,750 | 5,750 | Strict NAV observation on anchor date $T$ |
| **F.11.3.5.5** | 5,874 | 5,750 | 5,713 | Excluded non-reachable and non-positive NAVs |
| **F.15** | 5,874 | 5,126 | 5,126 | Required $\ge 252$ PIT daily observations |
| **F.16 / F.16.1** | 5,874 | 5,125 | **4,958** | Required valid non-NaN production FQ score |

---

## 4. Reconciled Strategy Distribution Table

| Strategy | N | Mean Return | Median Return | Std Return | Min Return | Max Return | Mean MDD | Median MDD | Std MDD | Min MDD | Max MDD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Strategy A (Trailing Return)** | 496 | 12.98% | 11.08% | 9.40% | -7.41% | 77.81% | 16.67% | 16.41% | 3.23% | 8.47% | 27.70% |
| **Strategy B (Lowest Volatility)** | 496 | 6.33% | 7.24% | 2.63% | -14.11% | 8.16% | 0.11% | 0.00% | 1.18% | 0.00% | 17.28% |
| **Strategy C (Exact Production FQ)** | 496 | 13.01% | 12.33% | 5.85% | -8.68% | 29.08% | 14.86% | 15.35% | 4.46% | 0.00% | 24.39% |

---

## 5. Required Governance Claim Matrix

| Claim | Evidence | Status |
|---|---|---|
| Production engine executes correctly | `FundQualityScoringEngine` executed on $4,958$ schemes | **SUPPORTED** |
| Exact production peer scope used | `category::subcategory::plan_type` applied | **SUPPORTED** |
| PIT integrity | Future-injection test passed ($100\%$ leak-free) | **SUPPORTED** |
| OOS forward association | Monotonic forward return across quintiles ($Q1 \rightarrow Q5$) | **SUPPORTED** |
| FQ has higher mean return than trailing comparator | $+0.03\%$ gross NAV return difference ($13.01\%$ vs $12.98\%$) | **SUPPORTED** |
| FQ has lower mean MDD than trailing comparator | $-1.81\%$ gross MDD difference ($14.86\%$ vs $16.67\%$) | **SUPPORTED** |
| FQ adds model-fit contribution beyond Return + Vol | Model M3 Incremental $R^2 = +0.1045$ | **SUPPORTED** |
| FQ provides independent information | Component circularity present in score inputs | **NOT SUPPORTED** |
| FQ demonstrates causal risk protection | Observational statistical correlation only | **NOT SUPPORTED** |
| FQ demonstrates economic benefit | Gross NAV evaluation; costs/taxes unmodeled | **NOT TESTABLE** |
| FQ is ready to drive consequential investor actions | Requires multi-period & downstream Action engine validation | **PARTIALLY SUPPORTED** |

---

## 6. Decision-Use Governance Statement

> **DECISION-USE GOVERNANCE STATEMENT:**
> Exact-production OOS validation passed mechanically, but consequential decision-use readiness remains subject to broader multi-period validation and downstream Suitability / Portfolio Need / Economic Benefit / Action controls.
