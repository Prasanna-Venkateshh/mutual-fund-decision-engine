# Phase F.10.3 — Official AMC Metadata Source Discovery & Coverage Assessment

## Executive Summary

Phase F.10.3 performed a comprehensive assessment of official Asset Management Company (AMC) disclosure sources across all 44 SEBI-registered AMCs in India to determine if Total Expense Ratio (TER), SEBI Riskometer, and Scheme Benchmark metadata could be ingestible at production scale.

---

## Key Findings

1. **Source Fragmentation**: 
   - Each of the 44 AMCs publishes disclosures independently on their respective websites.
   - Disclosures are published predominantly in PDF format or unstructured HTML tables.

2. **Identifier Ambiguity**:
   - AMC disclosures rely on scheme names (e.g., "Axis Long Term Equity Fund - Direct Plan - Growth") without standardized 6-digit AMFI scheme codes or ISINs.
   - Name matching across 44 AMC websites introduces unacceptable false-positive matching risks violating Phase F.8 identity governance.

3. **Ingestion Scalability**:
   - Scraping 44 separate AMC websites with varying page structures, anti-bot mechanisms, and non-standard PDF formats is brittle, unmaintainable, and non-authoritative at production scale.

4. **Bulk API Absence**:
   - Neither AMFI nor individual AMCs currently provide a unified, machine-readable, bulk API for daily TER, Riskometer, or Benchmark metadata.

---

## Governed Outcome & Partial-Data Mandate

- **Explicit Missing Metadata**: Where metadata fields (TER, Riskometer, Benchmark) cannot be retrieved from a validated bulk API, they **MUST REMAIN EXPLICITLY `None`**.
- **No Synthetic Defaults**: `TER=None`, `Riskometer=None`, and `Benchmark=None` must **NEVER** be replaced with synthetic substitutes (`0.0`, `"MODERATE"`, or category defaults).
- **Downstream F.11 Integration**: The decision engine pipeline must safely process schemes with partial metadata, preserving explicit evidence insufficiency and defaulting to non-transactional outcomes (`NO_ACTION`, `HOLD`, `MONITOR`, `REVIEW`).
