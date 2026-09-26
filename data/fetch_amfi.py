"""
AMFI Data Ingestion Module & Wrapper.

Updated for Slice 1 to use official SourceRegistry, AMFIIngestor, NAVValidator,
SchemeMaster, and NAVNormalizer pipeline.
"""

import sys
import os
import requests
import pandas as pd

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import DatabaseConnection
from data.ingestion.source_registry import SourceRegistry
from data.ingestion.amfi_ingestor import AMFIIngestor
from data.validation.nav_validator import NAVValidator
from data.mapping.scheme_master import SchemeMaster
from data.normalization.nav_normalizer import NAVNormalizer
from data.repositories.nav_repository import NAVRepository


def run_amfi_slice1_pipeline(sample_csv_path: str = "amfi_data.csv", db_path: str = ":memory:"):
    """
    Execute the Slice 1 Ingestion, Validation, Mapping, and Normalization Pipeline.
    
    Data Flow:
    Source Registry -> AMFIIngestor -> NAVValidator -> SchemeMaster -> NAVNormalizer -> Database
    """
    print(f"--- Running Slice 1 Data Pipeline on '{sample_csv_path}' ---")
    
    db = DatabaseConnection(db_path)
    registry = SourceRegistry(db=db)
    ingestor = AMFIIngestor(registry=registry)
    validator = NAVValidator()
    scheme_master = SchemeMaster()
    normalizer = NAVNormalizer(scheme_master=scheme_master)
    repo = NAVRepository(db=db)

    # Ingest from local sample CSV if file exists
    if os.path.exists(sample_csv_path):
        with open(sample_csv_path, "r", encoding="utf-8") as f:
            csv_content = f.read()
        raw_records = ingestor.fetch_raw_data(content=csv_content, format_type="csv")
    else:
        # Fallback raw line simulation
        raw_text = "119551;INF200K01VR1;INF200K01VS9;Aditya Birla Sun Life Banking & PSU Debt Fund - Direct Plan-Growth;394.9197;30-Apr-2026"
        raw_records = ingestor.fetch_raw_data(content=raw_text, format_type="txt")

    print(f"1. Raw Ingestion: Captured {len(raw_records)} raw records.")
    repo.save_raw_observations(raw_records)

    valid_tuples, quarantine_records = validator.process_and_quarantine(raw_records)
    print(f"2. Data Validation: {len(valid_tuples)} valid, {len(quarantine_records)} quarantined.")

    normalized_records, norm_quarantine = normalizer.normalize_batch(valid_tuples)
    quarantine_records.extend(norm_quarantine)

    print(f"3. Scheme Master & Normalization: {len(normalized_records)} normalized NAV records.")
    
    for norm_rec in normalized_records:
        canonical = scheme_master._canonical_schemes.get(norm_rec.canonical_scheme_id)
        if canonical:
            repo.save_canonical_scheme(canonical)
            mapping = scheme_master._mappings.get(f"{norm_rec.source_id}:{norm_rec.canonical_scheme_id}")
            if mapping:
                repo.save_scheme_mapping(mapping)

    repo.save_normalized_records(normalized_records)
    repo.save_quarantine_records(quarantine_records)

    print(f"4. Persistence: Database successfully populated. Total Quarantine Count: {repo.get_quarantine_count()}")
    return len(normalized_records), len(quarantine_records)


def fetch_fund_history_experimental():
    """
    Experimental prototype function retained for legacy compatibility only.
    Uses unvalidated third-party API (mfapi.in).
    """
    print("[WARNING] fetch_fund_history_experimental uses unvalidated mfapi.in API.")
    scheme_code = "119551"
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data["data"])
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
        df["nav"] = df["nav"].astype(float)
        df = df.sort_values("date")
        print(df.head())
        return df
    except Exception as e:
        print(f"[ERROR] Experimental fetch failed: {e}")
        return None


if __name__ == "__main__":
    run_amfi_slice1_pipeline()