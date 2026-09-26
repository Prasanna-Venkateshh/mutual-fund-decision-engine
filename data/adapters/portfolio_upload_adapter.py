"""
Portfolio Upload Adapter (data/adapters/).

Processes user portfolio CSV uploads in-memory, enforces security limits (5MB, 500 rows, formula injection defense),
resolves scheme identities via Scheme Master (ISIN/AMFI code), and constructs PortfolioExposureSnapshot
and PortfolioHoldingRecord instances.

Governance Invariants:
- Zero raw scheme-name fuzzy matching for identity.
- None != 0.0 != False.
- Strict quarantine for unresolved/ambiguous schemes.
- Discards raw CSV files from memory immediately after parsing.
"""

import csv
import io
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

from models.scheme import PlanType, OptionType, MappingConfidence
from data.mapping.scheme_master import SchemeMaster
from portfolio.need_models import PortfolioExposureSnapshot, PortfolioHoldingRecord
from web.security import MAX_PORTFOLIO_UPLOAD_SIZE_BYTES


class PortfolioUploadError(Exception):
    """Raised when file parsing, validation, or size limits fail."""
    pass


class PortfolioUploadAdapter:
    """Adapter for processing user CSV portfolio uploads and resolving holdings."""

    MAX_FILE_SIZE_BYTES = MAX_PORTFOLIO_UPLOAD_SIZE_BYTES  # Single governed 5 MB limit
    MAX_ROW_COUNT = 500  # 500 rows limit

    # Known CSV header aliases
    HEADER_ALIASES = {
        "isin": ["isin", "isin_code", "isin_number"],
        "amfi_code": ["amfi_code", "scheme_code", "amfi", "code"],
        "scheme_name": ["scheme_name", "fund_name", "scheme", "fund"],
        "units": ["units", "quantity", "balance_units", "unit_balance", "num_units"],
        "cost_basis": ["cost_basis", "purchase_value", "invested_amount", "buy_value", "total_cost"],
        "acquisition_date": ["acquisition_date", "purchase_date", "trx_date", "buy_date", "date"],
        "goal_id": ["goal_id", "goal", "associated_goal"],
    }

    def __init__(self, scheme_master: Optional[SchemeMaster] = None):
        self.scheme_master = scheme_master or SchemeMaster()

    def sanitize_cell_value(self, val: str) -> str:
        """Strips leading CSV formula injection triggers (=, +, -, @). Preserves valid negative numbers."""
        if not val:
            return ""
        val_str = str(val).strip()
        # Preserve legitimate negative numbers (e.g. -100.50)
        try:
            float(val_str)
            return val_str
        except ValueError:
            pass
        while val_str and val_str[0] in ("=", "+", "-", "@"):
            val_str = val_str[1:].strip()
        return val_str

    def parse_csv_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        investor_id: str,
        portfolio_snapshot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parses raw CSV bytes and resolves scheme identities.
        Returns a dict containing valid holdings, quarantined rows, rejected rows, and status summary.
        """
        if not file_bytes:
            raise PortfolioUploadError("File is empty (0 bytes).")

        if len(file_bytes) > self.MAX_FILE_SIZE_BYTES:
            raise PortfolioUploadError(
                f"File size ({len(file_bytes)} bytes) exceeds the maximum allowed limit of {self.MAX_FILE_SIZE_BYTES} bytes (5 MB)."
            )

        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception as e:
                raise PortfolioUploadError(f"Failed to decode CSV text: {e}") from e

        # Discard file_bytes from active reference
        del file_bytes

        stream = io.StringIO(text)
        reader = csv.reader(stream)
        
        try:
            rows = list(reader)
        except Exception as e:
            raise PortfolioUploadError(f"Malformed CSV format: {e}") from e

        if not rows:
            raise PortfolioUploadError("CSV file is empty.")

        header_raw = [self.sanitize_cell_value(c) for c in rows[0]]
        data_rows = rows[1:]

        if len(data_rows) > self.MAX_ROW_COUNT:
            raise PortfolioUploadError(
                f"Row count ({len(data_rows)}) exceeds the maximum allowed limit of {self.MAX_ROW_COUNT} rows."
            )

        header_map = self._map_headers(header_raw)
        
        # Check required columns
        if "units" not in header_map:
            raise PortfolioUploadError("Missing required CSV column: 'Units' (or alias 'quantity', 'balance_units').")

        if "isin" not in header_map and "amfi_code" not in header_map and "scheme_name" not in header_map:
            raise PortfolioUploadError("Missing scheme identification column: CSV must contain 'ISIN', 'AMFI_Code', or 'Scheme_Name'.")

        now_utc = datetime.now(timezone.utc)
        snap_id = portfolio_snapshot_id or f"snap_{investor_id}_{int(now_utc.timestamp())}"

        valid_holdings: List[PortfolioHoldingRecord] = []
        quarantined_rows: List[Dict[str, Any]] = []
        rejected_rows: List[Dict[str, Any]] = []
        
        seen_exact_rows: set = set()

        for idx, row in enumerate(data_rows, start=2): # line number 2+
            if not row or all(not str(cell).strip() for cell in row):
                continue  # Skip blank rows

            # Extract cell values safely
            raw_isin = self._get_cell(row, header_map.get("isin"))
            raw_amfi = self._get_cell(row, header_map.get("amfi_code"))
            raw_name = self._get_cell(row, header_map.get("scheme_name"))
            raw_units_str = self._get_cell(row, header_map.get("units"))
            raw_cost_str = self._get_cell(row, header_map.get("cost_basis"))
            raw_date_str = self._get_cell(row, header_map.get("acquisition_date"))
            raw_goal = self._get_cell(row, header_map.get("goal_id"))

            # Duplicate row check (exact file row duplicate)
            row_fingerprint = (raw_isin, raw_amfi, raw_name, raw_units_str, raw_cost_str, raw_date_str)
            is_duplicate_file_row = row_fingerprint in seen_exact_rows
            seen_exact_rows.add(row_fingerprint)

            # Parse Units
            units: Optional[float] = None
            if raw_units_str:
                try:
                    units = float(raw_units_str)
                except ValueError:
                    rejected_rows.append({
                        "line_number": idx,
                        "raw_row": row,
                        "reason": f"Invalid non-numeric units value: '{raw_units_str}'"
                    })
                    continue
            else:
                rejected_rows.append({
                    "line_number": idx,
                    "raw_row": row,
                    "reason": "Missing required 'Units' value."
                })
                continue

            # Parse Cost Basis
            cost_basis: Optional[float] = None
            if raw_cost_str:
                try:
                    cost_basis = float(raw_cost_str)
                except ValueError:
                    # Invalid cost basis parsed as None (unknown) without failing unit holding
                    cost_basis = None

            # Parse Date
            acquisition_date: Optional[datetime] = None
            if raw_date_str:
                acquisition_date = self._parse_date(raw_date_str)

            # Identity Resolution
            resolution_status, canonical_scheme, mapping = self._resolve_identity(
                isin=raw_isin,
                amfi_code=raw_amfi,
                scheme_name=raw_name
            )

            provenance = {
                "source_type": "USER_CSV_UPLOAD",
                "source_file_name": re.sub(r"[^\w\.-]", "_", filename),
                "line_number": idx,
                "import_timestamp_utc": now_utc.isoformat(),
                "raw_identifier_provided": {
                    "isin": raw_isin or None,
                    "amfi_code": raw_amfi or None,
                    "scheme_name": raw_name or None,
                },
                "resolution_status": resolution_status,
                "mapping_confidence": mapping.confidence.value if mapping else MappingConfidence.UNMAPPED.value,
                "is_duplicate_file_row": is_duplicate_file_row,
            }

            holding_id = f"hld_{investor_id}_{idx}_{int(now_utc.timestamp())}"

            if canonical_scheme and mapping and mapping.canonical_scheme_id:
                holding = PortfolioHoldingRecord(
                    holding_id=holding_id,
                    portfolio_snapshot_id=snap_id,
                    investor_id=investor_id,
                    canonical_scheme_id=mapping.canonical_scheme_id,
                    units=units,
                    source_provenance=provenance,
                    amfi_code=canonical_scheme.primary_amfi_code or raw_amfi,
                    isin=canonical_scheme.isin_growth or raw_isin,
                    scheme_name_raw=raw_name,
                    cost_basis_amount=cost_basis,
                    current_nav=None,
                    current_value=None,
                    acquisition_date=acquisition_date,
                    plan_type=canonical_scheme.plan_type.value if canonical_scheme.plan_type else None,
                    option_type=canonical_scheme.option_type.value if canonical_scheme.option_type else None,
                    goal_id=raw_goal or None,
                )
                valid_holdings.append(holding)
            else:
                quarantined_rows.append({
                    "line_number": idx,
                    "holding_id": holding_id,
                    "raw_isin": raw_isin,
                    "raw_amfi": raw_amfi,
                    "raw_name": raw_name,
                    "units": units,
                    "cost_basis": cost_basis,
                    "acquisition_date": acquisition_date.isoformat() if acquisition_date else None,
                    "goal_id": raw_goal,
                    "resolution_status": resolution_status,
                    "reason": mapping.notes if mapping else "Unresolved scheme identity. Requires user preview confirmation."
                })

        import_status = "IMPORT_VALID"
        if quarantined_rows and valid_holdings:
            import_status = "IMPORT_REQUIRES_REVIEW"
        elif quarantined_rows and not valid_holdings:
            import_status = "IMPORT_QUARANTINED_ONLY"
        elif rejected_rows and not valid_holdings and not quarantined_rows:
            import_status = "IMPORT_FAILED"

        return {
            "portfolio_snapshot_id": snap_id,
            "investor_id": investor_id,
            "import_status": import_status,
            "observation_date": now_utc,
            "valid_holdings": valid_holdings,
            "quarantined_rows": quarantined_rows,
            "rejected_rows": rejected_rows,
            "total_rows_received": len(data_rows),
            "valid_count": len(valid_holdings),
            "quarantine_count": len(quarantined_rows),
            "rejected_count": len(rejected_rows),
        }

    def _map_headers(self, header: List[str]) -> Dict[str, int]:
        """Maps CSV header labels to standard field keys using header aliases."""
        mapping: Dict[str, int] = {}
        for idx, col in enumerate(header):
            clean_col = col.lower().strip().replace(" ", "_").replace("-", "_")
            for field_key, aliases in self.HEADER_ALIASES.items():
                if clean_col in aliases and field_key not in mapping:
                    mapping[field_key] = idx
                    break
        return mapping

    def _get_cell(self, row: List[str], col_idx: Optional[int]) -> Optional[str]:
        """Safely extracts cell text from a row array."""
        if col_idx is None or col_idx >= len(row):
            return None
        val = self.sanitize_cell_value(row[col_idx])
        return val if val != "" else None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parses common ISO and date strings into standard UTC datetime."""
        date_clean = date_str.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                dt = datetime.strptime(date_clean, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    def _resolve_identity(
        self,
        isin: Optional[str],
        amfi_code: Optional[str],
        scheme_name: Optional[str]
    ) -> Tuple[str, Optional[Any], Optional[Any]]:
        """
        Resolves scheme identity strictly using ISIN or AMFI Scheme Code against Scheme Master.
        Raw scheme name string matching alone is PROHIBITED from establishing canonical identity.
        """
        # Priority 1: ISIN Lookup
        if isin and len(isin.strip()) >= 10:
            clean_isin = isin.strip().upper()
            sname = scheme_name or f"Sample Fund Direct Growth {clean_isin}"
            canonical, mapping = self.scheme_master.resolve_or_create_canonical_scheme(
                source_id="ISIN_MASTER",
                source_scheme_code=clean_isin,
                source_scheme_name=sname,
                isin_growth=clean_isin
            )
            if mapping.confidence in (MappingConfidence.EXACT_MATCH, MappingConfidence.HIGH_CONFIDENCE):
                return "RESOLVED_ISIN", canonical, mapping

        # Priority 2: AMFI Code Lookup
        if amfi_code and amfi_code.strip().isdigit():
            clean_amfi = amfi_code.strip()
            sname = scheme_name or f"Sample Fund Direct Growth {clean_amfi}"
            canonical, mapping = self.scheme_master.resolve_or_create_canonical_scheme(
                source_id="AMFI_OFFICIAL",
                source_scheme_code=clean_amfi,
                source_scheme_name=sname
            )
            if mapping.confidence in (MappingConfidence.EXACT_MATCH, MappingConfidence.HIGH_CONFIDENCE):
                return "RESOLVED_AMFI_CODE", canonical, mapping

        # Priority 3: Scheme Name Only (Prohibited from silent auto-mapping)
        if scheme_name:
            _, mapping = self.scheme_master.resolve_or_create_canonical_scheme(
                source_id="USER_NAME_ONLY",
                source_scheme_code="UNKNOWN",
                source_scheme_name=scheme_name
            )
            return "QUARANTINE_NAME_ONLY_PROHIBITED", None, mapping

        return "UNRESOLVED_MISSING_IDENTIFIER", None, None
