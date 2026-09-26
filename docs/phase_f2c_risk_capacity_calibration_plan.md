# Phase F.2C — Risk Capacity Calibration Plan

**Document Status:** GOVERNED CALIBRATION ROADMAP  
**Version:** `1.0.0`  
**Phase:** Phase F.2C — Risk Capacity Methodology Design  
**Date:** 2026-09-09 UTC

---

## 1. Executive Summary

This document specifies the calibration roadmap required before the 13 currently-`TBD` Risk Capacity Engine parameters can transition to `PROVISIONAL` or `APPROVED` status.

**Critical governance principle:** Calibration validates financial-resilience constructs, not investment return optimization. Do not calibrate Risk Capacity by checking whether high-capacity investors achieved better mutual-fund returns.

---

## 2. What Must Be Calibrated

The following 13 parameter groups require calibration:

| Priority | Param IDs | Description | Data Required |
|---|---|---|---|
| **P1** | RC-D1-04, RC-D1-05, RC-D1-06, RC-D1-07 | Debt Burden constraint thresholds and capacity ceiling mapping | RBI household credit data; FPSB/industry DTI distribution data |
| **P1** | RC-D2-02, RC-D2-03, RC-D2-04, RC-D2-05, RC-D2-06 | Reserve adequacy thresholds, stability multipliers, dependent adjustment | Income interruption frequency data; FPSB benchmarks; household emergency expense surveys |
| **P1** | RC-D3-03, RC-D3-04, RC-D3-05 | Surplus ratio thresholds for capacity levels | Household financial stress event data; SIP discontinuation rate data |
| **P2** | RC-IS-02 | Income stability reserve multipliers | Income interruption frequency by employment type |
| **P3** | RC-INT-02, RC-INT-03 | Confidence reduction per missing input; partial assessment confidence floor | Product validation testing; user experience validation |

---

## 3. Calibration Framework — Five Independent Layers

Calibration is separated into five distinct layers that must not be collapsed:

### Layer 1 — Software & Logic Validation (Phase F.3 implementation)
**What it validates:** Engine code correctness, determinism, edge-case handling, missing input behavior.  
**Method:** Unit tests covering all constraint dimensions independently; integration tests; property tests for monotonic sensitivity.  
**Does this validate financial thresholds?** No. This only validates that the engine correctly applies whatever thresholds are configured.

### Layer 2 — Mathematical & Structural Validation (Phase F.3 implementation)
**What it validates:** The constraint architecture is mathematically sound; no division by zero; ratios remain bounded; bottleneck rule correctly selects the minimum.  
**Method:** Mathematical property tests; boundary value tests; sensitivity tests confirming monotonic directional relationships (see §6 in the Methodology document).  
**Does this validate financial thresholds?** No. This validates the mathematics of the architecture, not the calibration of the parameters.

### Layer 3 — Cross-Profile Consistency Validation (Pre-production, synthetic profiles)
**What it validates:** Across a range of synthetic investor financial profiles, does the capacity model produce a consistent, sensible ordinal ranking?  
**Method:** Construct a matrix of synthetic profiles spanning the full range of debt burden, reserve adequacy, and surplus ratios. Verify that the ranking is directionally consistent with financial common sense.  
**Does this validate financial thresholds?** Partially — it validates that the ordinal ordering is plausible; it does not validate whether a specific DTI of 45% should be moderate or high constraint.

### Layer 4 — Financial Methodology Validation (Pre-production, fiduciary review)
**What it validates:** The capacity methodology correctly implements the fiduciary principle that an investor should not take on investment risk they cannot financially withstand.  
**Method:** Expert financial planner review of capacity assessments across representative investor profiles; comparison against FPSB and SEBI RIA standard practices.  
**Does this validate numerical thresholds?** Partially — fiduciary review can identify clearly wrong thresholds, but cannot replace empirical data.

### Layer 5 — Empirical Calibration (Required before live production deployment)

This is the layer that validates the actual numerical thresholds.

---

## 4. Empirical Calibration Requirements by Dimension

### Dimension 1: Debt Burden Thresholds

**Research question:** At what debt-to-income ratios do Indian retail households begin to exhibit material financial stress that impairs investment sustenance?

**Data sources required:**
- RBI Household Finance Committee data and follow-up reports on Indian household debt servicing distributions.
- Reserve Bank of India data on retail loan default rates segmented by Debt Service Ratio (DSR).
- FPSB India practitioner data (where accessible) on client debt burden distributions.
- Credit bureau data (subject to access and privacy compliance) on EMI-to-income distributions by income bracket.

**Calibration method:**
1. Map Indian household DSR distributions across income quintiles.
2. Identify DSR thresholds corresponding to materially elevated financial stress indicators (default, income shock vulnerability, liquidity stress).
3. Cross-reference against FPSB DTI guidance ($40-50\%$ maximum for standard planning — supported in Phase F.2B).
4. Determine whether the constraint level boundaries should vary by income level, employment type, or household structure.
5. Validate candidate thresholds against financial stress outcome data.

**Output:** Calibrated values for RC-D1-04, RC-D1-05, RC-D1-06, and the capacity ceiling mapping RC-D1-07.

---

### Dimension 2: Reserve Adequacy Thresholds

**Research question:** What emergency reserve coverage ratios are sufficient to prevent forced investment liquidation in the event of income interruption or emergency expense for Indian retail investors?

**Data sources required:**
- FPSB India guidance ranges (already directly supported for concept: 3–6 months salaried, 6–12 months self-employed).
- Indian household income interruption frequency data (RBI / NSSO / PLFS household surveys).
- Indian household medical / emergency expense shock frequency data.
- AMFI SIP discontinuation data segmented by financial profile where available.

**Calibration method:**
1. Estimate the probability distribution of income interruption duration by employment type in India.
2. Identify the reserve coverage level that achieves a target probability of sustaining obligations (e.g., 90% of income interruption events resolved within X months).
3. Estimate emergency expense shock frequency and magnitude from household survey data.
4. Cross-validate against FPSB India guidance ranges.
5. Determine the dependent-count adjustment formula empirically from household expense data.

**Output:** Calibrated values for RC-D2-02, RC-D2-03, RC-D2-04, RC-D2-05, RC-D2-06.

---

### Dimension 3: Surplus Ratio Thresholds

**Research question:** What sustainable surplus ratios correspond to meaningful capacity tiers in the context of Indian household financial resilience?

**Data sources required:**
- Indian household savings rate distributions (RBI HFC Report; National Financial Inclusion surveys).
- SIP continuation/discontinuation rates segmented by household savings ratio (if available from AMFI or AMC research).
- Data on which savings rate thresholds correspond to sustained investment behavior during market downturns.

**Calibration method:**
1. Map Indian household savings rate distributions.
2. Identify savings rate thresholds above which investment sustenance during market stress is materially more likely.
3. Determine whether the capacity tier boundaries should be nonlinear.
4. Validate against FPSB sustainable contribution guidance.

**Output:** Calibrated values for RC-D3-03, RC-D3-04, RC-D3-05.

---

### Income Stability Reserve Multipliers (RC-IS-02)

**Research question:** By how much should the required reserve coverage increase for variable-income vs. salaried investors in the Indian context?

**Data sources required:**
- Indian self-employment income volatility data.
- Income interruption frequency data by employment type from PLFS/NSSO household surveys.
- FPSB India practitioner guidance on tiered reserve requirements.

**Calibration method:**
1. Estimate income interruption probability and duration by employment category.
2. Derive reserve multipliers from the required coverage probability target.
3. Validate against FPSB India guidance.

---

## 5. Calibration Prerequisites

Before empirical calibration can begin, the following must be in place:

1. **Phase F.3 engine implementation** — the capacity engine must be built with externalized configurable thresholds.
2. **Configuration schema** — `config/risk/capacity_config.yaml` must define all TBD parameters as required stubs.
3. **Layer 1 & 2 tests passing** — software and mathematical correctness must be verified before threshold calibration.
4. **Data access** — primary data sources must be identified and accessed:
   - RBI Household Finance Committee datasets.
   - PLFS / NSSO household income survey data.
   - FPSB India guidance documentation.
   - AMFI SIP statistics (where publicly available).

---

## 6. Calibration Execution Schedule

```
CALIBRATION ROADMAP
│
├── Phase F.3: Risk Capacity Engine Implementation
│     ├── All 13 TBD parameters implemented as CONFIGURABLE STUBS
│     ├── Engine refuses to start if TBD parameters are absent from config
│     ├── Layer 1 & 2 tests passing (software + math validation)
│     └── Sensitivity tests confirming monotonic directional relationships
│
├── Phase F.4 / F.5: Risk Tolerance & Alignment Engine
│     (Parallel — does not unblock RC calibration)
│
├── Pre-Production Calibration Phase:
│     ├── Dimension 1: Debt Burden threshold research & calibration
│     ├── Dimension 2: Reserve Adequacy threshold research & calibration
│     ├── Dimension 3: Surplus Ratio threshold research & calibration
│     ├── Income Stability reserve multiplier research & calibration
│     └── Layer 4 (Financial Methodology Validation) — fiduciary review
│
├── Integration Testing with Calibrated Parameters:
│     ├── Cross-profile consistency testing (Layer 3)
│     ├── Scenario testing across Scenarios A–F from the Methodology document
│     └── Regression testing — 185+ tests must continue passing
│
└── Pre-Live Approval Gate:
      ├── All 13 TBD parameters must have moved to PROVISIONAL or APPROVED
      ├── Financial methodology sign-off required
      └── No TBD parameters may enter live production
```

---

## 7. Calibration Governance Rules

1. **No parameter may be promoted from TBD to APPROVED without a cited external evidence source.**
2. **Financial stress data, not investment return data, is the calibration target.** Risk Capacity is a resilience construct.
3. **Each calibrated threshold must be documented with:** the data source, the methodology, the calibration date, and the confidence level.
4. **Thresholds that cannot be empirically supported must remain TBD** rather than being set to arbitrary round numbers.
5. **All calibrated thresholds must be externalized in `config/risk/capacity_config.yaml`** — never hard-coded in engine logic.
6. **Calibration updates must increment the `rule_version`** so that historical assessments remain reproducible.

---

## 8. Validation Criteria for Calibration Completion

Calibration for each dimension is complete when:

1. A specific numerical threshold has been set based on cited external evidence.
2. The threshold has been tested against the Layer 3 cross-profile consistency matrix.
3. The threshold has passed Layer 4 fiduciary review.
4. The parameter status has been updated from `TBD` to `PROVISIONAL` (if further empirical validation is desired) or `APPROVED` (if evidence fully supports the value).
5. The change has been logged in the documentation traceability matrix.
