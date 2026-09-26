# PHASE F.15.1.1.1 — PRODUCTION PEER-GROUP SCOPE & FORMULA SENSITIVITY FORENSIC RECONCILIATION REPORT

## 1. Executive Summary & Verification

This narrow forensic reconciliation establishes the exact peer-group construction, percentile-rank calculation, and formal validation lineage of the canonical **Production Fund Quality v1.0** scoring methodology.

### Key Forensic Findings:
1. **Production Peer-Group Construction:** Strictly filters schemes by `category`, `subcategory`, and `plan_type` (`category::subcategory::plan_type`) prior to executing dimension normalization.
2. **Exact Percentile-Rank Calculation:** $\text{Score} = \frac{\text{Rank} - 0.5}{N} \times 100.0$ on $[0.0, 100.0]$.
3. **Formula A vs Formula B Reproduction:**
   - Pearson Correlation $r = \mathbf{0.5365}$ (**Exactly Reproduced**).
   - Top-Decile Overlap = $\mathbf{13 / 656 = 1.98\%}$ (**Exactly Reproduced**).
4. **Global Rank (F.15) vs Production Rank (Current Production):**
   - Broad Category Peer Group Overlap = $\mathbf{475 / 656 = 72.41\%}$ (reconciles $70.6\%$).
   - Exact Peer Key ($category::subcategory::plan\_type$) Overlap = $\mathbf{601 / 656 = 91.62\%}$.
5. **Exact Current-Production OOS Validation Status:** **PENDING**. Prior validation F.15 evaluated the percentile-rank transformation globally across the entire universe rather than within production peer groups ($category::subcategory::plan\_type$).

---

## 2. Formal Validation Lineage Table

| Phase | Transformation | Peer Scope | Current Production Match? | Validation Status |
|---|---|---|---|---|
| **F.11.3.5.5** | Raw-value scaling ($0.5 \times \frac{1}{1+\text{Vol}} + 0.5 \times \text{Return}$) | Universe-wide raw values | **NO** | **HISTORICAL PROTOTYPE ONLY** (Not evidence for current production) |
| **F.15** | Percentile-rank scoring ($0.50 \times \text{Rank}(1/\text{Vol}) + 0.50 \times \text{Rank}(\text{Return})$) | Global mutual-fund universe | **TRANSFORMATION MATCH ONLY** | **PARTIAL VALIDATION** (Evaluated rank transformation, but lacked intra-category peer scoping) |
| **Current Production** | `PeerGroupNormalizer` percentile rank | Intra-category, intra-subcategory, intra-plan_type peer group | **YES** | **CANONICAL PRODUCTION METHODOLOGY** (Exact OOS decision-value validation remains pending) |

---

## 3. Exact Denominators & Numerical Reconciliation

- **Common Cohort $N$:** $6,552$ funds
- **Top-Decile Threshold $k$:** $\lceil 0.10 \times 6,552 \rceil = \mathbf{656}$ funds
- **Formula A vs B Overlap:** Numerator = $13$, Denominator = $656$, Overlap = $\mathbf{1.98\%}$
- **Global Rank (F.15) vs Production Rank Overlap:**
  - Broad Category ($k=656$): Numerator = $475$, Denominator = $656$, Overlap = $\mathbf{72.41\%}$
  - Exact Production Peer Key ($category::subcategory::plan\_type$): Numerator = $601$, Denominator = $656$, Overlap = $\mathbf{91.62\%}$

---

## 4. Governance & Validation Language

- **F.11 Authoritative Statement:** *"F.11 historical results are not validation evidence for the current production Fund Quality implementation."*
- **F.15 Authoritative Statement:** *"F.15 evaluated the percentile-rank transformation using a global peer population. It does not constitute validation of the complete current production Fund Quality methodology because production applies peer-group scoping."*
- **Current Production Status Statement:** *"Exact-production OOS decision-value validation remains pending."*
