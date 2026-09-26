"""
Ingestion Run Manager (Phase F.9).

Manages execution lifecycle and audit logging of data ingestion runs.
Captures start/end timestamps, retrieval statuses, record counts, and errors.
"""

from datetime import datetime, timezone
import uuid
from typing import List, Optional, Dict, Any

from models.production_dataset import IngestionRunRecord


class IngestionRunManager:
    """Manages ingestion run execution context, tracking metrics and producing audit records."""

    def __init__(self):
        self._active_runs: Dict[str, Dict[str, Any]] = {}
        self._completed_runs: Dict[str, IngestionRunRecord] = {}

    def start_run(self, source_id: str, requested_date_range: Optional[str] = None) -> str:
        """Starts a new ingestion run and returns a unique run_id."""
        run_id = f"run_{source_id.lower()}_{uuid.uuid4().hex[:8]}"
        self._active_runs[run_id] = {
            "run_id": run_id,
            "source_id": source_id,
            "start_time_utc": datetime.now(timezone.utc),
            "requested_date_range": requested_date_range,
            "total_records": 0,
            "valid_records": 0,
            "partial_records": 0,
            "invalid_records": 0,
            "quarantined_records": 0,
            "conflict_records": 0,
            "error_log": [],
        }
        return run_id

    def record_metrics(
        self,
        run_id: str,
        total: int = 0,
        valid: int = 0,
        partial: int = 0,
        invalid: int = 0,
        quarantined: int = 0,
        conflict: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Increments metrics for an active run."""
        if run_id not in self._active_runs:
            raise KeyError(f"Ingestion run {run_id} is not active or unknown.")

        ctx = self._active_runs[run_id]
        ctx["total_records"] += total
        ctx["valid_records"] += valid
        ctx["partial_records"] += partial
        ctx["invalid_records"] += invalid
        ctx["quarantined_records"] += quarantined
        ctx["conflict_records"] += conflict
        if error:
            ctx["error_log"].append(error)

    def complete_run(self, run_id: str, status: str = "SUCCESS") -> IngestionRunRecord:
        """Completes an active run and returns an immutable IngestionRunRecord."""
        if run_id not in self._active_runs:
            if run_id in self._completed_runs:
                return self._completed_runs[run_id]
            raise KeyError(f"Ingestion run {run_id} is not active.")

        ctx = self._active_runs.pop(run_id)
        end_time = datetime.now(timezone.utc)

        record = IngestionRunRecord(
            run_id=ctx["run_id"],
            source_id=ctx["source_id"],
            start_time_utc=ctx["start_time_utc"],
            end_time_utc=end_time,
            requested_date_range=ctx["requested_date_range"],
            retrieval_status=status,
            total_records_processed=ctx["total_records"],
            valid_record_count=ctx["valid_records"],
            partial_record_count=ctx["partial_records"],
            invalid_record_count=ctx["invalid_records"],
            quarantined_record_count=ctx["quarantined_records"],
            conflict_record_count=ctx["conflict_records"],
            error_log=list(ctx["error_log"])
        )
        self._completed_runs[run_id] = record
        return record

    def get_run(self, run_id: str) -> Optional[IngestionRunRecord]:
        """Retrieves a completed run record."""
        return self._completed_runs.get(run_id)

    def list_completed_runs(self) -> List[IngestionRunRecord]:
        """Returns all completed run records."""
        return list(self._completed_runs.values())
