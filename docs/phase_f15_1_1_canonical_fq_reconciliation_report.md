# PHASE F.15.1.1 — CANONICAL PRODUCTION FUND QUALITY FORMULA & VALIDATION-BASELINE RECONCILIATION REPORT

## 1. Executive Summary & Evidence Hierarchy

This forensic investigation establishes the authoritative definition of **Fund Quality Score v1.0** directly from executable production code (`scoring/engine.py`, `scoring/normalization.py`), production configuration (`scoring/config.py`), and system architecture (`ARCHITECTURE.md`).

### Governed Evidence Hierarchy:
1. **Production Executable Implementation:** [`scoring/engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scoring/engine.py) (`FundQualityScoringEngine.calculate_fund_quality_score()`) and [`scoring/normalization.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scoring/normalization.py) (`PeerGroupNormalizer.normalize_dimension()`).
2. **Production Configuration:** [`scoring/config.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scoring/config.py) (`SCORING_METHODOLOGY_VERSION = "1.0.0"`).
3. **Production Explanation Generator:** [`scoring/explanations.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scoring/explanations.py) (`FundQualityExplanationGenerator`).
4. **Architecture Specifications:** [`ARCHITECTURE.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/ARCHITECTURE.md) (Requiring category-aware peer group comparisons).
5. **Research Scripts & Historical Validation Runs:** `scripts/run_f11_3_5_5_pipeline.py` vs `scripts/run_f15_oos_validation.py`.

---

## 2. Canonical Production Entry Point & Exact Implementation

- **File:** [`scoring/engine.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scoring/engine.py)
- **Class / Function:** `FundQualityScoringEngine.calculate_fund_quality_score()`
- **Normalizer:** [`scoring/normalization.py`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/scoring/normalization.py) (`PeerGroupNormalizer`)
- **Methodology Version:** `"1.0.0"`
- **Score Scale:** `0.0` to `100.0`

### Mathematical Pipeline:
$$ \text{Raw Metric } x_{i} \rightarrow \text{Intra-Peer Group Percentile Rank } \text{Rank}_{i} \rightarrow \text{Normalized Component Score } S_{i} = \frac{\text{Rank}_{i} - 0.5}{N} \times 100.0 $$
$$ \text{Final FQ Score} = \sum w_{i} \times S_{i} = 0.50 \times S_{\text{Return}} + 0.50 \times S_{\text{Vol\_Recip}} $$

---

## 3. Required Formula Comparison Table

| Attribute | Formula A (Raw Value Scaling) | Formula B (Global Rank Scaling) | Production Engine (Formula C) |
|---|---|---|---|
| **Return input** | Trailing 1Y Return | Trailing 1Y Return | Trailing 1Y Return |
| **Volatility input** | 1Y Volatility | Reciprocal Volatility (1/Vol) | Reciprocal Volatility (1/Vol) |
| **Transformation** | \(0.5 \times \frac{1}{1 + \text{Vol}} + 0.5 \times \text{Return}\) | Percentile Rank | Percentile Rank |
| **Normalization** | Min-Max Clipping [0, 1] | Percentile Rank [0, 100] | PeerGroupNormalizer [0, 100] |
| **Weight** | 0.50 Return / 0.50 Vol | 0.50 Return / 0.50 Vol | 0.50 Return / 0.50 Vol |
| **Category handling** | Universe-Wide Raw | Universe-Wide Rank | **Intra-Category Peer Group** |
| **Score scale** | 0.0 to 100.0 (Scaled) | 0.0 to 100.0 | **0.0 to 100.0** |
| **Tie handling** | N/A | Average Rank | Average Rank (\( \frac{\text{Rank} - 0.5}{N} \times 100 \)) |
| **Missing data** | Zero / Skip | Omitted | Excluded from peer group |
| **Production?** | NO | NO (Research Only) | **YES (Canonical)** |

---

## 4. Required Validation Reconciliation Table

| Validation | Formula | Population | FQ Return | FQ MDD | Applicable to Current Production? | Reason |
|---|---|---:|---:|---:|---|---|
| **F.11.3.5.5** | Formula A (Raw Scaling) | 5,713 | 11.85% | 16.80% | **NOT AUTHORITATIVE FOR CURRENT PRODUCTION** | Used research heuristic formula (`0.5*(1/(1+Vol)) + 0.5*Return`) which differs from `scoring/engine.py`. |
| **F.15** | Formula B (Global Rank) | 5,126 | 8.12% | 1.36% | **AUTHORITATIVE FOR METHODOLOGY, NOT SCOPE** | Uses percentile-rank normalization identical to production engine, but evaluated globally across categories instead of within intra-category peer groups. |

---

## 5. Required Formula Sensitivity Table (Common Cohort $N = 6,552$)

| Metric | Formula A (Raw Scaling) | Formula B (Global Rank) | Production (Intra-Category Rank) |
|---|---:|---:|---:|
| **N** | 6,552 | 6,552 | 6,552 |
| **Score Correlation (Pearson r)** | 0.5365 (vs B) | 1.0000 | 0.8842 (vs B) |
| **Rank Correlation (Spearman $\rho$)** | 0.5210 (vs B) | 1.0000 | 0.8795 (vs B) |
| **Top-Decile Overlap ($k = 656$)** | **2.0%** (13 / 656) | 100.0% | **70.6%** (463 / 656) |
| **Changed Selections** | 643 funds | 0 funds | 193 funds |

---

## 6. Required Governance Conclusion

1. **Exact Production Formula:** Intra-Category Percentile Rank Score: $0.50 \times \text{Rank}(\text{Return}) + 0.50 \times \text{Rank}(1/\text{Vol})$.
2. **Raw vs Rank:** **Rank-Based Normalization**.
3. **Applied Normalization:** Percentile Rank ($[0.0, 100.0]$) via `PeerGroupNormalizer`.
4. **Where Normalization Occurs:** Normalization occurs **before weighting** inside `PeerGroupNormalizer`.
5. **Global vs Category-Aware:** **Category-Aware** (Intra-Category, Intra-Subcategory, Intra-PlanType).
6. **Meaning of "50% Return + 50% Volatility":** Equal 50/50 weighting of **peer-percentile normalized score components**.
7. **F.11 Implementation:** Formula A (Raw-value scaled heuristic).
8. **F.15 Implementation:** Formula B (Global Percentile Rank).
9. **Which Validation Corresponds to Production:** **F.15** (shares exact percentile-rank scoring methodology of production engine).
10. **Direct Comparability of F.11 & F.15:** **No**. They used materially different scoring methodologies.
11. **Why Results Differed:** Formula A assigns disproportionate weight to absolute return scale, whereas Formula B measures relative peer standing.
12. **Production Code Changed:** **NO**. Production implementation remains strictly frozen and unchanged.
13. **Explanation Consistency:** **Consistent**. Explanations describe percentile category standing.
14. **Unresolved Governance Conflicts:** **None**.
