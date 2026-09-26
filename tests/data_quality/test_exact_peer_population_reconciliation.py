"""
Test Phase F.19 Forensic Reconciliation — Exact Peer Population & 105-vs-106 Reconciliation

Validates:
1. Production FundQualityScoringEngine peer_group_size definition.
2. Exact 105 vs 106 terminology reconciliation (104 non-target peers + target = 105 total scoring inputs).
3. Target CAN_AMFI_101206 presence in candidate pool prior to target handling (occurrence = 1).
4. Deterministic SHA256 of canonical ID set.
5. Exact reproducibility across independent scoring runs (EXACT_RESULT_MATCH = True).
6. Sum of weighted dimension contributions equals Quality Score.
"""

import sqlite3
import hashlib
from datetime import date
import pytest

from scoring.engine import FundQualityScoringEngine
from scoring.normalization import PeerGroupNormalizer
from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    SchemeMetricSnapshot,
    CategoryPointInTimeContext,
    OptionType,
    PlanType,
    ProvenanceMetadata
)
from models.metric_data import HistoryMaturityBucket
from data.adapters.category_context_adapter import CategoryContextAdapter

DB_PATH = "db/backfill_f12_2.db"
TARGET_ID = "CAN_AMFI_101206"
OBS_DATE = date(2025, 1, 31)


def get_canonical_overnight_population():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT canonical_scheme_id, scheme_name, plan_type, option_type FROM canonical_schemes WHERE scheme_name LIKE '%OVERNIGHT%'")
    rows = cur.fetchall()
    conn.close()
    
    # Filter Regular plan schemes matching target plan_type
    reg_schemes = [s for s in rows if 'REGULAR' in s[2].upper() or ('DIRECT' not in s[1].upper() and 'DIRECT' not in s[2].upper())]
    return reg_schemes


def test_01_peer_group_size_engine_definition():
    """1. Prove peer_group_size equals len(peers) including target."""
    engine = FundQualityScoringEngine()
    adapter = CategoryContextAdapter()
    
    reg_schemes = get_canonical_overnight_population()
    inputs = []
    for cid, sname, ptype, opttype in reg_schemes:
        ctx = adapter.resolve_category_context(cid, sname, OBS_DATE)
        inp = FundQualityDatasetInput(
            dataset_version="1.0.0",
            observation_date=OBS_DATE,
            canonical_scheme_id=cid,
            amfi_code=cid.replace("CAN_AMFI_", ""),
            scheme_name=sname,
            amc_name="TEST_AMC",
            plan_type=PlanType.REGULAR,
            option_type=OptionType.GROWTH,
            category_context=ctx,
            metrics=SchemeMetricSnapshot(
                observation_date=OBS_DATE,
                history_length_years=3.0,
                maturity_tier=HistoryMaturityBucket.THREE_TO_FIVE_YEARS,
                cagr_overall=0.065,
                rolling_1y_mean=0.065,
                rolling_3y_mean=0.065,
                annualized_volatility=0.005,
                downside_deviation=0.003,
                max_drawdown=-0.002,
                total_expense_ratio=0.002
            ),
            data_quality_score=1.0,
            confidence_score=1.0,
            provenance=ProvenanceMetadata(source_id="NAV_DB", source_document_url="http://amfiindia.com", retrieval_timestamp_utc=None),
            return_comparability_available=True
        )
        inputs.append(inp)
        
    target_inp = [i for i in inputs if i.canonical_scheme_id == TARGET_ID][0]
    res = engine.calculate_fund_quality_score(target_inp, inputs)
    
    assert res.peer_group_size == 105
    assert len(inputs) == 105


def test_02_reconcile_105_vs_106_counts():
    """2. Reconcile non-target peers (104), scoring inputs (105), target occurrence (1)."""
    reg_schemes = get_canonical_overnight_population()
    cids = [s[0] for s in reg_schemes]
    
    assert len(reg_schemes) == 105
    assert TARGET_ID in cids
    
    non_target_cids = [c for c in cids if c != TARGET_ID]
    assert len(non_target_cids) == 104
    assert cids.count(TARGET_ID) == 1


def test_03_canonical_id_hash_stability():
    """3. Prove canonical ID set hash is deterministic."""
    reg_schemes = get_canonical_overnight_population()
    sorted_cids = sorted([s[0] for s in reg_schemes])
    
    sha256_hash = hashlib.sha256("\n".join(sorted_cids).encode('utf-8')).hexdigest()
    assert len(sorted_cids) == 105
    assert sha256_hash == "fa34100cd70c55f6aa17caa56fdfb85e6673efe92951bb2d5088e8c284969ec4"


def test_04_target_pre_existence_in_candidate_set():
    """4. Verify target was present in candidate set prior to target append handling."""
    reg_schemes = get_canonical_overnight_population()
    cids = [s[0] for s in reg_schemes]
    
    # Candidate set already has 105 items including CAN_AMFI_101206
    assert TARGET_ID in cids
    assert cids.count(TARGET_ID) == 1


def test_05_reproducibility_and_score_provenance():
    """5. Re-run authoritative experiment twice, verify exact match and score provenance."""
    reg_schemes = get_canonical_overnight_population()
    adapter = CategoryContextAdapter()
    
    inputs = []
    for idx, (cid, sname, ptype, opttype) in enumerate(reg_schemes):
        ctx = adapter.resolve_category_context(cid, sname, OBS_DATE)
        cagr = 0.065 + (idx % 10) * 0.001
        vol = 0.005 + (idx % 8) * 0.0002
        downside = 0.003 + (idx % 5) * 0.0001
        max_dd = -0.002 - (idx % 6) * 0.0001
        ter = 0.002 + (idx % 4) * 0.0005
        
        inp = FundQualityDatasetInput(
            dataset_version="1.0.0",
            observation_date=OBS_DATE,
            canonical_scheme_id=cid,
            amfi_code=cid.replace("CAN_AMFI_", ""),
            scheme_name=sname,
            amc_name="TEST_AMC",
            plan_type=PlanType.REGULAR,
            option_type=OptionType.GROWTH,
            category_context=ctx,
            metrics=SchemeMetricSnapshot(
                observation_date=OBS_DATE,
                history_length_years=3.0,
                maturity_tier=HistoryMaturityBucket.THREE_TO_FIVE_YEARS,
                cagr_overall=cagr,
                rolling_1y_mean=cagr,
                rolling_3y_mean=cagr,
                annualized_volatility=vol,
                downside_deviation=downside,
                max_drawdown=max_dd,
                total_expense_ratio=ter
            ),
            data_quality_score=1.0,
            confidence_score=1.0,
            provenance=ProvenanceMetadata(source_id="NAV_DB", source_document_url="http://amfiindia.com", retrieval_timestamp_utc=None),
            return_comparability_available=True
        )
        inputs.append(inp)
        
    target_inp = [i for i in inputs if i.canonical_scheme_id == TARGET_ID][0]
    
    engine1 = FundQualityScoringEngine()
    res1 = engine1.calculate_fund_quality_score(target_inp, inputs)
    
    engine2 = FundQualityScoringEngine()
    res2 = engine2.calculate_fund_quality_score(target_inp, inputs)
    
    # Exact match assertion
    assert res1.quality_score == res2.quality_score
    assert res1.confidence_score == res2.confidence_score
    assert res1.peer_group_size == res2.peer_group_size == 105
    assert res1.dimension_scores == res2.dimension_scores
    
    # Score provenance assertion: sum(weighted contributions) == quality_score
    sum_contrib = sum(d.weighted_contribution for d in res1.dimension_scores.values())
    assert round(sum_contrib, 1) == res1.quality_score
