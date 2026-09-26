# Phase F.4.4 — Code-to-Spec Traceability Audit Matrix

**Phase:** Phase F.4.4 — Code-to-Spec Traceability Audit  
**Date:** 2026-09-12 UTC  
**Status:** Audit Completed  
**Final Decision:** `PHASE F.4.4 SUBSTANTIVE AUDIT ACCEPTED WITH PROVISIONAL METHODOLOGY`  

---

## 1. Traceability Audit Matrix

| Rule ID | Specification Requirement | Code Location | Test Coverage | Actual Behavior | Verdict |
|---|---|---|---|---|---|
| `RN-INV-1` | Input Validity Gate | `need_engine.py:91-118` | `test_05_invalid_input...` | Invalid input (empty investor_id or ID mismatch) returns `INVALID_ASSESSMENT` with `confidence_score = 0.0`. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-INF-1` | Mandatory Information Sufficiency Gate | `need_engine.py:121-147` | `test_04`, `test_31` | Absence of Goal/Wealth AND Allocation/Portfolio returns `INSUFFICIENT_INFORMATION` with `confidence_score = 0.0`. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-HARD-EXCESS` | Primary Excess Exposure Rule | `need_engine.py:281-285` | `test_02`, `test_15` | `NEGATIVE_GAP` (allocation surplus) returns `EXCESS_EXPOSURE`. High concentration alone cannot trigger this state. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-POS-1` | Primary Exposure Need Rule | `need_engine.py:286-291` | `test_01`, `test_14` | `POSITIVE_GAP` (allocation gap) returns `NEED_IDENTIFIED` with `ALLOCATION_GAP_PRESENT` flag. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-POS-BALANCED` | Primary Balanced Exposure Rule | `need_engine.py:292-295` | `test_03`, `test_13` | `BALANCED_EXPOSURE` returns `NO_MATERIAL_NEED`. High quality cannot override this. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-POS-UNDERFUNDED` | Goal Underfunded Fallback Rule | `need_engine.py:298-301` | `test_01` | Unknown/missing allocation gap direction with an `UNDERFUNDED` goal returns `NEED_IDENTIFIED`. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-COND-UNSUITABLE` | Candidate Unsuitability Constraint | `need_engine.py:321-325` | `test_07`, `test_18` | Suitability `NOT_SUITABLE` returns `CANDIDATE_CANNOT_FULFILL_NEED` and adds `CANDIDATE_UNSUITABLE` flag without erasing Need state. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-COND-INCAPABLE` | Candidate Asset/Category Incapability | `need_engine.py:331-335` | `test_08`, `test_19` | Candidate incapable returns `CANDIDATE_CANNOT_FULFILL_NEED` and adds `CANDIDATE_NOT_CAPABLE_OF_FULFILLING_NEED` flag without erasing Need state. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-POS-FULFILL` | Compatible Candidate Fulfillment | `need_engine.py:341-344` | `test_06` | Suitable + capable when `NEED_IDENTIFIED` exists returns `CANDIDATE_CAN_FULFILL_NEED`. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-COND-AFFORD` | Affordability Constraint Modifier | `need_engine.py:360-363` | `test_11` | `AFFORDABILITY_CONSTRAINED` sets status and flag without converting Need state to `NO_MATERIAL_NEED`. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-COND-CONC` | Category Overexposure Modifier | `need_engine.py:370-373` | `test_13`, `test_14` | Concentration sets flag `CATEGORY_OVEREXPOSED` without manufacturing `EXCESS_EXPOSURE`. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-COND-OVERLAP` | Security Overlap Modifier | `need_engine.py:375-378` | `test_28` | High security overlap sets flag `SECURITY_OVERLAP_CONCERN`. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-CONF-1` | Confidence Score Isolation | `need_engine.py:382-404` | `test_22` | Confidence is calculated after state determination; low confidence score does not flip Need state. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-PROV-1` | Upstream Provenance Preservation | `need_engine.py:79-88` | `test_26`, `test_33` | Preserves suitability, fund quality, risk alignment, and affordability assessment IDs in `upstream_assessment_ids`. | 🟢 IMPLEMENTED CORRECTLY |
| `RN-EXP-1` | Non-Recommendation Disclaimer | `need_engine.py:187` | `test_27` | Explanations explicitly state: "This assessment identifies portfolio/goal exposure need only and does not constitute a transaction recommendation (Buy/Sell/Switch)." | 🟢 IMPLEMENTED CORRECTLY |

---

## 2. Evaluation Legend

- 🟢 **IMPLEMENTED CORRECTLY:** Code strictly executes the specification requirement, verified by tests.
- 🟠 **GOVERNANCE CONCERN:** Implementation matches code but underlying rule is ambiguous or unsafe.
- 🔴 **DEFECT:** Implementation violates governing specification.
- ⚪ **NOT APPLICABLE:** Component not required in this phase.
