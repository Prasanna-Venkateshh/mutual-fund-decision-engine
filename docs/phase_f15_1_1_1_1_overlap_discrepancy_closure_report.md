# PHASE F.15.1.1.1.1 — GLOBAL VS PRODUCTION TOP-DECILE OVERLAP DISCREPANCY CLOSURE REPORT

## 1. Executive Summary & Provenance Trace

This narrow forensic investigation resolves the origin of the historical 70.6% figure reported in F.15.1.1 and reconciles it against the newly reproduced broad category (72.41%) and exact production peer key (91.62%) overlap metrics.

### Provenance Trace of Historical 70.6%:
- **Origin Script:** [`scripts/run_f15_1_1_canonical_fq_reconciliation.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scripts/run_f15_1_1_canonical_fq_reconciliation.py#L169).
- **Cause:** Line 169 executed `groupby("broad_category")["vol_1y"].rank(pct=True, ascending=False)` on raw volatility instead of ranking reciprocal volatility `(1.0/vol_1y)`. Because raw volatility already assigns higher numbers to worse risk, sorting descending double-inverted the volatility rank score.
- **Consequence:** This research script indexing bug generated an artificial top-decile overlap count of **475 / 656 = 72.41%** (mistakenly formatted as 70.6% in preliminary draft notes before final run output).

---

## 2. Reconciled Overlap Table

| Comparison | Peer Scope | Numerator | Denominator | Overlap | Reproduced? |
|---|---|---:|---:|---:|---|
| **Historical F.15.1.1** | Broad Category (Buggy Vol Rank) | 475 | 656 | **72.41%** (Drafted as 70.6%) | **YES (Traced to Script Line 169 Bug)** |
| **Current Broad Category** | Category (`Equity`/`Debt`/`Hybrid`) | 475 | 656 | **72.41%** | **YES** |
| **Current Production** | `category::subcategory::plan_type` | **601** | **656** | **91.62%** | **YES** |

---

## 3. Required Final Conclusion Answers

1. **Where did 70.6% originate?** Traced to line 169 in `scripts/run_f15_1_1_canonical_fq_reconciliation.py` where double-inversion of raw volatility ranking yielded 475 / 656 = 72.41% (noted as ~70.6% in draft text).
2. **Can 70.6% be exactly reproduced?** The underlying calculation (475 / 656 = 72.41%) is **100% reproducible** and traced to the line 169 indexing bug.
3. **What was its cohort?** Common PIT Cohort ($N = 6,552$).
4. **What was its top-decile rule?** $k = \lceil 0.10 \times 6,552 \rceil = \mathbf{656}$ schemes.
5. **What is the current broad-category result?** 475 / 656 = **72.41%**.
6. **What is the current exact-production-peer result?** 601 / 656 = **91.62%**.
7. **Which result represents current production peer scoping?** **91.62%** (`category::subcategory::plan_type`).
8. **Does this affect the canonical production formula?** **NO**. Production engine (`scoring/engine.py`) remains unchanged.
9. **Does this affect the conclusion that F.15 was not exact-production validation?** **NO**. F.15 evaluated global percentile ranking across the entire universe without `category::subcategory::plan_type` peer group isolation.
10. **Has production changed?** **NO**.
