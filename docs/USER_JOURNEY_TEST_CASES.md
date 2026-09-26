# USER JOURNEY TEST CASES & VERIFICATION MATRIX

## Overview
This document defines the authoritative test cases and validation matrix for the four primary investor user journeys and adversarial negative conditions in the **Mutual Fund Decision Engine**.

---

## Comprehensive Test Case Matrix

| Test ID | Journey | Objective | Preconditions | Test Data | Steps | Expected UI Result | Expected Engine Result | Expected Persistence Result | Expected Recommendation Result | Expected Execution Result | Evidence / Methodology Check | Negative Conditions | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **J1-01** | Journey 1 | Onboarding & Profile Persistence for New Investor | New User, No Profile | `RETIREMENT`, `12.0` Reserve, `HOLD_STEADY` | 1. Authenticate<br>2. Complete Onboarding<br>3. Save Profile | Profile summary rendered on /settings | `InvestorProfileSnapshot` generated | Profile saved to `ProfileRepository` | N/A | `NOT_EXECUTED` | Version `1.0.0` logged in audit | Incomplete inputs block step progression | 🟢 PASSED |
| **J1-02** | Journey 1 | Portfolio Absence Non-Blocking Flow | Profile Complete, 0 Holdings | Investor `inv_j1_nop` | 1. Navigate to /wealth<br>2. Check holdings | Displays "No holdings currently imported" | Portfolio evaluation evaluates 0 holdings | Zero holdings in `PortfolioRepository` | Guidance: Explore Funds | `NOT_EXECUTED` | No fake holdings or fabricated allocations | Forced portfolio upload error avoided | 🟢 PASSED |
| **J1-03** | Journey 1 | Recommendation & Non-Execution Contract | Profile Active | `inv_j1_nop` | 1. View /action-center | Displays zero pending reviews | Engine evaluates decision orchestrator | Zero DB mutations | `HOLD_STEADY` / No-Op | `NOT_EXECUTED` | Evidence box shows System Rec ≠ User Decision | Recommendation display never mutates holdings | 🟢 PASSED |
| **J2-01** | Journey 2 | Direct CSV File Upload & Portfolio Confirmation | Authenticated User | Valid CSV Payload (ISIN `INF200K01123`) | 1. POST /wealth/upload<br>2. Review preview<br>3. POST confirm | Review table shows resolved holding | `PortfolioUploadAdapter` parses 1 valid holding | `PortfolioRepository.save_portfolio()` creates snapshot | Portfolio holding active | `NOT_EXECUTED` | Quarantine count = 0 | Unconfirmed preview does not persist | 🟢 PASSED |
| **J2-02** | Journey 2 | Existing Portfolio Re-adjustment & Non-Execution | Active Portfolio | Holding `CAN_AMFI_118266` (150 units) | 1. View /wealth<br>2. Check Suitability | Holdings rendered with resolved status | `SuitabilityEngine` evaluates holding | Portfolio snapshot retained | Action state `HOLD` | `NOT_EXECUTED` | Suitability status verified | Decision review does not trigger execution | 🟢 PASSED |
| **J3-01** | Journey 3 | Template CSV Download Roundtrip | Authenticated User | Official Template CSV Header | 1. GET /wealth/template<br>2. Fill template<br>3. Upload & confirm | Downloaded header matches `PortfolioUploadAdapter` | Header aliases matched deterministically | Template holdings persisted | Active portfolio updated | `NOT_EXECUTED` | CSV content-disposition verified | Header mismatch triggers import error | 🟢 PASSED |
| **J4-01** | Journey 4 | Fund Discovery, Scoring & Secondary Metadata | Anonymous / Authenticated | Scheme `CAN_AMFI_118266` | 1. Search scheme<br>2. Open Fund Detail | Fund Name is `<h1>`, Canonical ID is secondary metadata | Scheme name queried from `canonical_schemes` | Read-only GET request | N/A | `NOT_EXECUTED` | Evidence box displays `CAN_AMFI_118266` | ID is not primary heading | 🟢 PASSED |
| **J4-02** | Journey 4 | Analytical Tables & Missing Data Integrity | Scheme Detail Page | Scheme `CAN_AMFI_118266` | 1. Inspect metrics table<br>2. Inspect 6-dim table | Missing values display `Not available` | Underlying raw metrics checked | Read-only GET request | N/A | `NOT_EXECUTED` | Missing metric is never zero-filled | 0.00% is not displayed for missing metrics | 🟢 PASSED |
| **J4-03** | Journey 4 | Exploration Dirty-Guard Exclusion Contract | Read-only routes | Search input typing, category filter | 1. Type in search bar<br>2. Click 'My Wealth' | Navigation occurs immediately without unsaved modal | Dirty guard JS ignores `data-no-dirty` & GET inputs | Zero form submission | N/A | `NOT_EXECUTED` | `isDirty` remains `false` | Unsaved modal never appears on /discover | 🟢 PASSED |
| **ADV-01** | Adversarial | Name-Only Portfolio Row Quarantine | Invalid Input | CSV with missing ISIN & AMFI code | 1. Upload malformed CSV | Row quarantined with clear reason | `PortfolioUploadAdapter` flags resolution failure | Row excluded from active holdings | N/A | `NOT_EXECUTED` | Quarantined table displayed in UI | Invalid row does not create active holding | 🟢 PASSED |
| **ADV-02** | Adversarial | Duplicate Confirmation Idempotency | Active User | Identical snapshot payload POST twice | 1. POST confirm twice | Portfolio holdings count remains exactly 1 | Snapshot versioning handles idempotency | Zero DB row duplicate growth | N/A | `NOT_EXECUTED` | Snapshot ID matches previous payload | Duplicate submission does not double holdings | 🟢 PASSED |
| **ADV-03** | Adversarial | Genuine Editable Dirty Guard Enforcement | Editable Form | Onboarding radio change on /onboarding | 1. Change radio answer<br>2. Click 'Explore' link | Custom "Leave this page?" modal appears | Client JS detects `POST` form mutation | Pending navigation paused until decision | Save or Leave | `NOT_EXECUTED` | `isDirty` evaluates to `true` | Navigating away without decision blocked | 🟢 PASSED |

---

## Scoring Architecture Reconciliation

| Displayed UI Dimension | Production Engine Metric Mapping | Base Weight (Equity) | Implementation Status | Data Availability Handling |
| :--- | :--- | :--- | :--- | :--- |
| **1. Historical Performance Consistency** | `rolling_3y_mean` / `cagr_overall` | 20.0% / 25.0% | 🟢 Genuine Engine Metric (`return` / `consistency`) | `Not available` when NAV history insufficient |
| **2. Risk-Adjusted Return Efficiency** | `sharpe_ratio` / `sortino_ratio` | Dynamic | 🟢 Genuine Engine Metric | `Not available` when risk-free rate missing |
| **3. Downside Capital Protection** | `downside_deviation` / `max_drawdown` | 15.0% / 15.0% | 🟢 Genuine Engine Metric (`downside_risk` / `max_drawdown`) | `Not available` when drawdown missing |
| **4. Expense Ratio Efficiency** | `total_expense_ratio` | 10.0% | 🟢 Genuine Engine Metric (`cost_efficiency`) | `Not available` when TER unpopulated |
| **5. Portfolio & AMC Track Record** | AMC track record / manager tenure | Baseline | 🟠 Methodological Gap (Provisional in V1) | Rendered as `Not available` (Honest Gap) |
| **6. Data Quality & Coverage Integrity** | NAV observation completeness | 100 / 100 | 🟢 Verified Pipeline Metric | Rendered as `100 / 100` for complete NAVs |

---

## Step 6.2 — Discover & 10-Fund Comparison Test Matrix

For the complete 27-test matrix covering Fund Universe Audit (17,507 schemes), Nippon India Nifty 50 Direct Growth discovery (`CAN_AMFI_118741`), Dynamic Filter Composability (AMC, Plan, Option, Search), Server-Side Pagination, and 10-Fund Side-by-Side Comparison Matrix, refer to:
- [DISCOVER_AND_COMPARE_TEST_CASES.md](file:///d:/AI%20Portfolio/mutual-fund-decision-engine/docs/DISCOVER_AND_COMPARE_TEST_CASES.md)

