"""
Seed Lifecycle Data Module — Phase D: Controlled Seed Dataset.

Provides a small, deterministic seed dataset based on the representative events
validated in the Phase D Prototype.

Governing Documents:
- ARCHITECTURE.md §4, §11
- PRODUCT_SPEC.md §24, §25
- DECISION_RULES.md §12.18.2
- config/lifecycle/lifecycle_config.yaml
"""

from datetime import datetime, timezone
from typing import List, Tuple

from data.ingestion.lifecycle_ingestion_pipeline import (
    RawLifecycleDocument,
    CandidateLifecycleEvent,
    LifecycleIngestionPipeline,
)
from models.scheme_lifecycle import LifecycleEvent


def get_phase_d_seed_documents() -> List[Tuple[RawLifecycleDocument, CandidateLifecycleEvent]]:
    """
    Return the controlled Phase D seed documents and candidate events.
    """
    retrieval_dt = datetime(2026, 9, 8, 10, 0, 0, tzinfo=timezone.utc)

    seed_items = [
        # Item 0: Scheme Creation for SBI Horizon Fund
        (
            RawLifecycleDocument(
                document_id="doc_seed_creation_sbi_horizon_2010",
                source_id="SEBI_OFFICIAL",
                source_document_url="https://www.sebi.gov.in",
                retrieval_timestamp_utc=retrieval_dt,
                raw_content="SBI Horizon Fund - Short Term Plan inception notice.",
                document_metadata={"publisher": "SEBI"},
            ),
            CandidateLifecycleEvent(
                source_document_id="doc_seed_creation_sbi_horizon_2010",
                raw_scheme_name="SBI Horizon Fund - Short Term Plan",
                raw_amfi_code="102345",
                event_type_str="SCHEME_CREATION",
                effective_date_str="2010-01-01",
                effective_date_precision_str="DAY",
                source_document_fact="SBI Horizon Fund inception date was January 1, 2010.",
            ),
        ),
        # Item 1: Scheme Merger
        (
            RawLifecycleDocument(
                document_id="doc_seed_merger_sbi_2018",
                source_id="AMC_STATUTORY_DISCLOSURE",
                source_document_url="https://www.sbimf.com/en-us/disclosure",
                retrieval_timestamp_utc=retrieval_dt,
                raw_content="Notice-cum-Addendum: Merger of SBI Horizon Fund - Short Term Plan into SBI Short Term Debt Fund effective May 18, 2018.",
                document_metadata={"publisher": "SBI Mutual Fund", "notice_ref": "SBI-MF-2018-05"},
            ),
            CandidateLifecycleEvent(
                source_document_id="doc_seed_merger_sbi_2018",
                raw_scheme_name="SBI Horizon Fund - Short Term Plan",
                raw_predecessor_name="SBI Horizon Fund - Short Term Plan",
                raw_successor_name="SBI Short Term Debt Fund",
                raw_amfi_code="102345",
                event_type_str="SCHEME_MERGED_INTO",
                effective_date_str="2018-05-18",
                effective_date_precision_str="DAY",
                source_document_fact="SBI Horizon Fund - Short Term Plan merged into SBI Short Term Debt Fund effective May 18, 2018.",
                notes="Verified from SBI MF Addendum notice.",
            ),
        ),
        # Item 2: Scheme Rename
        (
            RawLifecycleDocument(
                document_id="doc_seed_rename_nippon_2019",
                source_id="AMFI_OFFICIAL",
                source_document_url="https://www.amfiindia.com/commission-structure-circulars-and-updates",
                retrieval_timestamp_utc=retrieval_dt,
                raw_content="AMFI Industry Update: Renaming of Reliance Mutual Fund schemes to Nippon India Mutual Fund. Reliance Large Cap Fund renamed to Nippon India Large Cap Fund effective September 28, 2019.",
                document_metadata={"publisher": "AMFI / Nippon India MF", "circular_ref": "AMFI-2019-09"},
            ),
            CandidateLifecycleEvent(
                source_document_id="doc_seed_rename_nippon_2019",
                raw_scheme_name="Reliance Large Cap Fund",
                raw_amfi_code="100346",
                raw_isin="INF204K01918",
                event_type_str="SCHEME_RENAMED",
                effective_date_str="2019-09-28",
                effective_date_precision_str="DAY",
                source_document_fact="Reliance Large Cap Fund renamed to Nippon India Large Cap Fund effective September 28, 2019.",
                old_value="Reliance Large Cap Fund",
                new_value="Nippon India Large Cap Fund",
                notes="AMFI Scheme Master text alignment.",
            ),
        ),
        # Item 3: Scheme Closure / Winding Up
        (
            RawLifecycleDocument(
                document_id="doc_seed_closure_franklin_2020",
                source_id="AMC_STATUTORY_DISCLOSURE",
                source_document_url="https://www.franklintempletonindia.com",
                retrieval_timestamp_utc=retrieval_dt,
                raw_content="Franklin Templeton Trustee Notice: Decision to wind up Franklin India Ultra Short Bond Fund effective April 24, 2020 pursuant to Regulation 39(2)(a).",
                document_metadata={"publisher": "Franklin Templeton Trustee", "notice_ref": "FT-TRUSTEE-2020-04"},
            ),
            CandidateLifecycleEvent(
                source_document_id="doc_seed_closure_franklin_2020",
                raw_scheme_name="Franklin India Ultra Short Bond Fund",
                raw_amfi_code="105894",
                event_type_str="SCHEME_CLOSED",
                effective_date_str="2020-04-24",
                effective_date_precision_str="DAY",
                source_document_fact="Franklin India Ultra Short Bond Fund wound up effective April 24, 2020.",
                notes="Official Trustee disclosure notice.",
            ),
        ),
        # Item 4: Scheme Creation / NFO
        (
            RawLifecycleDocument(
                document_id="doc_seed_creation_sbi_nifty_2021",
                source_id="SEBI_OFFICIAL",
                source_document_url="https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&smid=2",
                retrieval_timestamp_utc=retrieval_dt,
                raw_content="SBI Nifty 50 Index Fund NFO Allotment Notice. Scheme allotment date: December 20, 2021.",
                document_metadata={"publisher": "SEBI / SBI MF", "filing_ref": "SEBI-SID-2021-12"},
            ),
            CandidateLifecycleEvent(
                source_document_id="doc_seed_creation_sbi_nifty_2021",
                raw_scheme_name="SBI Nifty 50 Index Fund - Direct Plan - Growth",
                raw_amfi_code="149231",
                raw_isin="INF200KA1UT3",
                event_type_str="SCHEME_CREATION",
                effective_date_str="2021-12-20",
                effective_date_precision_str="DAY",
                source_document_fact="SBI Nifty 50 Index Fund allotment date was December 20, 2021.",
                notes="SEBI NFO Allotment filing.",
            ),
        ),
        # Item 5: Plan / Option Mandate Change
        (
            RawLifecycleDocument(
                document_id="doc_seed_plan_direct_2013",
                source_id="SEBI_OFFICIAL",
                source_document_url="https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&smid=2",
                retrieval_timestamp_utc=retrieval_dt,
                raw_content="SEBI Circular CIR/IMD/DF/21/2012: Mandatory introduction of Direct Plans in all mutual fund schemes effective January 1, 2013.",
                document_metadata={"publisher": "SEBI", "circular_ref": "CIR/IMD/DF/21/2012"},
            ),
            CandidateLifecycleEvent(
                source_document_id="doc_seed_plan_direct_2013",
                raw_scheme_name="HDFC Top 200 Fund - Direct Plan",
                raw_amfi_code="119061",
                event_type_str="PLAN_TYPE_CHANGED",
                effective_date_str="2013-01-01",
                effective_date_precision_str="DAY",
                source_document_fact="SEBI mandated Direct Plans for all mutual fund schemes effective January 1, 2013.",
                old_value="REGULAR",
                new_value="DIRECT",
                notes="SEBI Direct Plan regulatory directive.",
            ),
        ),
        # Item 6: Ambiguous / Quarantined Event (Testing Quarantine Path & MD-3)
        (
            RawLifecycleDocument(
                document_id="doc_seed_quarantine_ambiguous_2022",
                source_id="AMC_STATUTORY_DISCLOSURE",
                source_document_url=None,  # Missing source URL forces Quarantine
                retrieval_timestamp_utc=retrieval_dt,
                raw_content="Unverified restructuring notice: Contradictory ISIN change and scheme mapping without official publication link.",
                document_metadata={"publisher": "Unknown"},
            ),
            CandidateLifecycleEvent(
                source_document_id="doc_seed_quarantine_ambiguous_2022",
                raw_scheme_name="Unresolved Legacy Growth Scheme",
                raw_amfi_code="999999",
                event_type_str="ISIN_CHANGED",
                effective_date_str="2022-06-15",
                effective_date_precision_str="DAY",
                source_document_fact="Unverified ISIN change with conflicting scheme mapping.",
                notes="Conflict in ISIN mapping; missing authoritative URL.",
            ),
        ),
    ]

    return seed_items


def ingest_phase_d_seed_dataset(pipeline: LifecycleIngestionPipeline) -> List[LifecycleEvent]:
    """
    Ingest the complete Phase D seed dataset through the 6-stage pipeline.
    """
    seed_items = get_phase_d_seed_documents()
    all_ingested: List[LifecycleEvent] = []

    for doc, candidate in seed_items:
        events = pipeline.process_document(doc, [candidate])
        all_ingested.extend(events)

    return all_ingested
