"""
Portfolio Repository (data/repositories/).

Provides durable, privacy-conscious, deterministic SQLite storage for governed
PortfolioExposureSnapshot and PortfolioHoldingRecord data contracts.

Governance Invariants:
- None != 0.0 != False.
- Append-only version history for portfolio snapshots.
- Non-destructive updates: replacing a portfolio sets is_current = 0 for previous snapshots.
- Fail closed on database error or malformed payload.
- Zero broker trade execution capability.
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from portfolio.need_models import PortfolioExposureSnapshot, PortfolioHoldingRecord


class PortfolioPersistenceError(Exception):
    """Raised when portfolio database schema, insertion, or retrieval fails."""
    pass


CREATE_PORTFOLIO_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    portfolio_snapshot_id TEXT PRIMARY KEY,
    investor_id TEXT NOT NULL,
    snapshot_version TEXT NOT NULL DEFAULT '1.0.0',
    total_valuation REAL,
    is_valuation_available INTEGER NOT NULL DEFAULT 1,
    observation_date TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1,
    UNIQUE(investor_id, snapshot_version)
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    holding_id TEXT PRIMARY KEY,
    portfolio_snapshot_id TEXT NOT NULL,
    investor_id TEXT NOT NULL,
    canonical_scheme_id TEXT NOT NULL,
    amfi_code TEXT,
    isin TEXT,
    scheme_name_raw TEXT,
    units REAL NOT NULL,
    cost_basis_amount REAL,
    current_nav REAL,
    current_value REAL,
    acquisition_date TEXT,
    plan_type TEXT,
    option_type TEXT,
    goal_id TEXT,
    provenance_json TEXT NOT NULL,
    FOREIGN KEY(portfolio_snapshot_id) REFERENCES portfolio_snapshots(portfolio_snapshot_id)
);
"""


class PortfolioRepository:
    """Repository for managing persistent PortfolioExposureSnapshot and PortfolioHoldingRecord records in SQLite."""

    def __init__(self, db_conn: sqlite3.Connection):
        if db_conn is None:
            raise PortfolioPersistenceError("sqlite3.Connection cannot be None")
        self.conn = db_conn
        self._init_tables()

    def _init_tables(self) -> None:
        """Initializes database tables for portfolio snapshots and holdings."""
        try:
            self.conn.executescript(CREATE_PORTFOLIO_TABLES_SQL)
            self.conn.commit()
        except sqlite3.Error as e:
            raise PortfolioPersistenceError(f"Portfolio database schema initialization failed: {e}") from e

    def save_portfolio(
        self,
        snapshot: PortfolioExposureSnapshot,
        holdings: List[PortfolioHoldingRecord],
        version_string: str = "1.0.0"
    ) -> str:
        """
        Persists a PortfolioExposureSnapshot and its detailed PortfolioHoldingRecords.
        Sets previous portfolio versions for investor_id to is_current = 0
        and stores new portfolio as is_current = 1.
        """
        if not isinstance(snapshot, PortfolioExposureSnapshot):
            raise PortfolioPersistenceError(f"Expected PortfolioExposureSnapshot instance, got {type(snapshot)}")

        if not snapshot.investor_id or not snapshot.investor_id.strip():
            raise PortfolioPersistenceError("investor_id must be a non-empty string.")

        now_utc = datetime.now(timezone.utc).isoformat()
        obs_date_str = snapshot.observation_date.isoformat() if snapshot.observation_date else now_utc

        try:
            # Mark previous snapshots for investor as not current
            self.conn.execute(
                "UPDATE portfolio_snapshots SET is_current = 0 WHERE investor_id = ?;",
                (snapshot.investor_id,)
            )

            # Insert new snapshot
            sql_snap = """
            INSERT OR REPLACE INTO portfolio_snapshots (
                portfolio_snapshot_id, investor_id, snapshot_version,
                total_valuation, is_valuation_available, observation_date, created_at_utc, is_current
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1);
            """
            self.conn.execute(
                sql_snap,
                (
                    snapshot.portfolio_snapshot_id,
                    snapshot.investor_id,
                    version_string,
                    snapshot.total_valuation,
                    1 if snapshot.is_valuation_available else 0,
                    obs_date_str,
                    now_utc
                )
            )

            # Insert holdings
            sql_hld = """
            INSERT OR REPLACE INTO portfolio_holdings (
                holding_id, portfolio_snapshot_id, investor_id, canonical_scheme_id,
                amfi_code, isin, scheme_name_raw, units, cost_basis_amount,
                current_nav, current_value, acquisition_date, plan_type, option_type,
                goal_id, provenance_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """
            for h in holdings:
                acq_str = h.acquisition_date.isoformat() if h.acquisition_date else None
                prov_str = json.dumps(h.source_provenance or {})

                self.conn.execute(
                    sql_hld,
                    (
                        h.holding_id,
                        snapshot.portfolio_snapshot_id,
                        snapshot.investor_id,
                        h.canonical_scheme_id,
                        h.amfi_code,
                        h.isin,
                        h.scheme_name_raw,
                        h.units,
                        h.cost_basis_amount,
                        h.current_nav,
                        h.current_value,
                        acq_str,
                        h.plan_type,
                        h.option_type,
                        h.goal_id,
                        prov_str
                    )
                )

            self.conn.commit()
            return snapshot.portfolio_snapshot_id
        except sqlite3.Error as e:
            self.conn.rollback()
            raise PortfolioPersistenceError(f"Failed to save portfolio snapshot: {e}") from e

    def get_current_portfolio(
        self,
        investor_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the current active PortfolioExposureSnapshot and PortfolioHoldingRecords for investor_id.
        Returns None if no active portfolio exists for investor_id.
        """
        if not investor_id or not investor_id.strip():
            raise PortfolioPersistenceError("investor_id must be a non-empty string.")

        sql_snap = """
        SELECT portfolio_snapshot_id, snapshot_version, total_valuation, is_valuation_available, observation_date
        FROM portfolio_snapshots
        WHERE investor_id = ? AND is_current = 1
        ORDER BY created_at_utc DESC LIMIT 1;
        """
        try:
            cursor = self.conn.execute(sql_snap, (investor_id.strip(),))
            snap_row = cursor.fetchone()
            if not snap_row:
                return None

            snap_id, version_str, total_val, is_val_avail, obs_date_str = snap_row

            # Fetch holdings
            sql_hlds = """
            SELECT holding_id, canonical_scheme_id, amfi_code, isin, scheme_name_raw,
                   units, cost_basis_amount, current_nav, current_value, acquisition_date,
                   plan_type, option_type, goal_id, provenance_json
            FROM portfolio_holdings
            WHERE portfolio_snapshot_id = ?;
            """
            cursor_h = self.conn.execute(sql_hlds, (snap_id,))
            h_rows = cursor_h.fetchall()

            holdings: List[PortfolioHoldingRecord] = []
            canonical_scheme_ids: List[str] = []
            holding_ids: List[str] = []

            for r in h_rows:
                h_id, can_id, amfi, isin_val, sname, units_val, cost_val, nav_val, val_val, acq_str, plan, opt, g_id, prov_json = r
                
                holding_ids.append(h_id)
                canonical_scheme_ids.append(can_id)

                acq_dt = datetime.fromisoformat(acq_str) if acq_str else None
                prov_dict = json.loads(prov_json) if prov_json else {}

                holdings.append(
                    PortfolioHoldingRecord(
                        holding_id=h_id,
                        portfolio_snapshot_id=snap_id,
                        investor_id=investor_id,
                        canonical_scheme_id=can_id,
                        units=units_val,
                        source_provenance=prov_dict,
                        amfi_code=amfi,
                        isin=isin_val,
                        scheme_name_raw=sname,
                        cost_basis_amount=cost_val,
                        current_nav=nav_val,
                        current_value=val_val,
                        acquisition_date=acq_dt,
                        plan_type=plan,
                        option_type=opt,
                        goal_id=g_id,
                    )
                )

            obs_dt = datetime.fromisoformat(obs_date_str) if obs_date_str else datetime.now(timezone.utc)

            snapshot = PortfolioExposureSnapshot(
                portfolio_snapshot_id=snap_id,
                investor_id=investor_id,
                holding_ids=holding_ids,
                canonical_scheme_ids=canonical_scheme_ids,
                total_valuation=total_val,
                is_valuation_available=bool(is_val_avail),
                observation_date=obs_dt
            )

            return {
                "snapshot": snapshot,
                "holdings": holdings,
                "version_string": version_str
            }
        except (sqlite3.Error, ValueError, json.JSONDecodeError) as e:
            raise PortfolioPersistenceError(f"Failed to retrieve portfolio for investor_id '{investor_id}': {e}") from e

    def list_portfolio_versions(self, investor_id: str) -> List[Dict[str, Any]]:
        """Lists historical portfolio snapshot version metadata for investor_id."""
        if not investor_id or not investor_id.strip():
            raise PortfolioPersistenceError("investor_id must be a non-empty string.")

        sql = """
        SELECT portfolio_snapshot_id, snapshot_version, total_valuation, observation_date, created_at_utc, is_current
        FROM portfolio_snapshots
        WHERE investor_id = ?
        ORDER BY created_at_utc ASC;
        """
        try:
            cursor = self.conn.execute(sql, (investor_id.strip(),))
            rows = cursor.fetchall()
            return [
                {
                    "portfolio_snapshot_id": r[0],
                    "snapshot_version": r[1],
                    "total_valuation": r[2],
                    "observation_date": r[3],
                    "created_at_utc": r[4],
                    "is_current": bool(r[5]),
                }
                for r in rows
            ]
        except sqlite3.Error as e:
            raise PortfolioPersistenceError(f"Database error listing portfolio versions: {e}") from e
