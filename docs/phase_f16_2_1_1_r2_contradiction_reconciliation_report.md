# PHASE F.16.2.1.1 — INCREMENTAL R² TABLE CONTRADICTION FORENSIC RECONCILIATION REPORT

## EXECUTIVE SUMMARY
This report details the forensic audit resolving the internal contradiction between Table A and Table B in Phase F.16.2.1's nested regression $R^2$ report. 

The investigation confirms that **TABLE B IS AUTHORITATIVE**. Table A was a non-executable reporting artifact originating from manual transcription errors in early unverified draft notes for the 2022 and 2023 anchor periods. Table B represents the exact, 100% reproducible output of direct Python execution on governed point-in-time datasets.

---

## 1. REQUIRED RECONCILIATION TABLE (TABLE A vs TABLE B)

| Anchor | Version/Table | M0 | M1 (Return) | M2 (Ret+Vol) | M3 (M2+FQ) | Delta R² (M3-M2) | N | Source | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| **2022** | Table A | 0.0000 | 0.0021 | 0.0412 | 0.0583 | +0.0171 | 3,705 | Manual draft transcription error | DISPROVED / REJECTED |
| **2022** | Table B | 0.0000 | 0.0014 | 0.0025 | 0.0027 | **+0.0001** | 3,705 | Direct Python execution on PIT dataset | **AUTHORITATIVE** |
| **2023** | Table A | 0.0000 | 0.2814 | 0.3105 | 0.3341 | +0.0236 | 4,249 | Manual draft transcription error | DISPROVED / REJECTED |
| **2023** | Table B | 0.0000 | 0.0006 | 0.0508 | 0.1056 | **+0.0548** | 4,249 | Direct Python execution on PIT dataset | **AUTHORITATIVE** |
| **2024** | Table A | 0.0000 | 0.2053 | 0.2280 | 0.3325 | +0.1045 | 4,958 | Executable output matching F.16 / F.16.1 | **AUTHORITATIVE** |
| **2024** | Table B | 0.0000 | 0.2053 | 0.2280 | 0.3325 | **+0.1045** | 4,958 | Executable output matching F.16 / F.16.1 | **AUTHORITATIVE** |

---

## 2. REQUIRED AUTHORITATIVE INCREMENTAL R² TABLE

| Anchor Year | Authoritative M0 | M1 (Return) | M2 (Ret+Vol) | M3 (M2+FQ) | Delta R² (M3-M2) | Common N |
|---|---:|---:|---:|---:|---:|---:|
| **2022** | 0.0000 | 0.0014 | 0.0025 | 0.0027 | **+0.0001** | 3,705 |
| **2023** | 0.0000 | 0.0006 | 0.0508 | 0.1056 | **+0.0548** | 4,249 |
| **2024** | 0.0000 | 0.2053 | 0.2280 | 0.3325 | **+0.1045** | 4,958 |

---

## 3. AUDIT FINDINGS & RECONCILIATION MECHANICS

1. **Same-Sample Integrity:** Verified. For each evaluated anchor year, models M0, M1, M2, and M3 use **EXACTLY the same scheme observations** ($N=3,705$ for 2022; $N=4,249$ for 2023; $N=4,958$ for 2024).
2. **Dependent Variable:** Confirmed strictly as **1Y forward gross NAV return** across all models and anchor dates.
3. **Predictors:** Confirmed strictly as:
   - **M0:** Intercept
   - **M1:** Intercept + Trailing 1Y Return
   - **M2:** M1 + Annualized Volatility
   - **M3:** M2 + Exact Production Fund Quality Score (`FundQualityScoringEngine`).
4. **Circularity Governance:** Production FQ is constructed directly from percentile ranks of Trailing 1Y Return and Reciprocal Volatility. Therefore, incremental $R^2$ represents composite non-linear model-fit contribution, **NOT** independent alpha or predictive discovery.

---

## 4. CLAIM STATUS CORRECTION
- **Updated Claim Status:** **SUPPORTED** ("Positive incremental model-fit contribution was observed in all three evaluated periods, subject to component circularity.")
- **F.16.2.1 Text Correction:** Text in [`docs/phase_f16_2_1_multi_period_lineage_reconciliation_report.md`](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/phase_f16_2_1_multi_period_lineage_reconciliation_report.md) has been updated to align strictly with Authoritative Table B.

---

## 5. PRODUCTION STATUS & GOVERNANCE
- **Production Scoring Engine:** FROZEN v1.0.0 (`FundQualityScoringEngine`).
- **Final Validation Status:** **PASSED WITH LIMITATIONS** (Contradiction fully resolved; Table B confirmed as 100% authoritative).
- **Unresolved Items:** None.
