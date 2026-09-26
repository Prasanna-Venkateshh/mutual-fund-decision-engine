"""
Security Audit Event Logger (V1 Step 3).

Provides immutable, append-only SQLite security audit event logging.
Captures security-sensitive operational events without logging passwords,
session tokens, full CSV file contents, income figures, or granular holdings.

Governance Invariants:
- Sensitive Data Logging Prohibition: Passwords, session tokens, CSV contents,
  and profile details are NEVER logged.
- Security audit records MUST NOT alter historical financial calculations or decision audit logs.
- Fail closed: database error on event logging raises SecurityAuditError.
"""

import hashlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


class SecurityAuditError(Exception):
    """Raised when security audit event schema creation or logging fails."""
    pass


CREATE_SECURITY_AUDIT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS security_audit_events (
    event_id TEXT PRIMARY KEY,
    timestamp_utc TEXT NOT NULL,
    actor_investor_id TEXT NOT NULL,
    subject_id TEXT,
    event_type TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    outcome TEXT NOT NULL,
    ip_address_redacted TEXT,
    user_agent_hash TEXT,
    request_id TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class SecurityAuditEvent:
    event_id: str
    timestamp_utc: str
    actor_investor_id: str
    event_type: str
    resource_type: str
    outcome: str
    request_id: str
    subject_id: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address_redacted: Optional[str] = None
    user_agent_hash: Optional[str] = None


class SecurityAuditLogger:
    """Logger for persisting immutable security audit events to SQLite."""

    def __init__(self, db_conn: sqlite3.Connection):
        if db_conn is None:
            raise SecurityAuditError("sqlite3.Connection cannot be None")
        self.conn = db_conn
        self._init_tables()

    def _init_tables(self) -> None:
        """Initializes security_audit_events database table."""
        try:
            self.conn.executescript(CREATE_SECURITY_AUDIT_TABLE_SQL)
            self.conn.commit()
        except sqlite3.Error as e:
            raise SecurityAuditError(f"Security audit schema initialization failed: {e}") from e

    def log_event(
        self,
        actor_investor_id: str,
        event_type: str,
        resource_type: str,
        outcome: str,
        subject_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """
        Persists a security audit event to SQLite.
        Sanitizes IP address and hashes User-Agent to protect PII.
        """
        if not actor_investor_id or not actor_investor_id.strip():
            actor_investor_id = "ANONYMOUS_OR_SYSTEM"

        event_id = f"sec_evt_{uuid.uuid4().hex[:16]}"
        now_utc = datetime.now(timezone.utc).isoformat()
        req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"

        # Redact IP address (e.g. 192.168.1.100 -> 192.168.1.xxx)
        ip_redacted = None
        if ip_address:
            parts = ip_address.split(".")
            if len(parts) == 4:
                ip_redacted = f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
            else:
                ip_redacted = "redacted_ip"

        # Hash User-Agent
        ua_hash = None
        if user_agent:
            ua_hash = hashlib.sha256(user_agent.encode("utf-8")).hexdigest()[:16]

        try:
            self.conn.execute(
                """
                INSERT INTO security_audit_events (
                    event_id, timestamp_utc, actor_investor_id, subject_id,
                    event_type, resource_type, resource_id, outcome,
                    ip_address_redacted, user_agent_hash, request_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_id,
                    now_utc,
                    actor_investor_id,
                    subject_id,
                    event_type,
                    resource_type,
                    resource_id,
                    outcome,
                    ip_redacted,
                    ua_hash,
                    req_id,
                ),
            )
            self.conn.commit()
            return event_id
        except sqlite3.Error as e:
            raise SecurityAuditError(f"Failed to log security audit event: {e}") from e

    def list_events(
        self,
        actor_investor_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Lists security audit events, optionally filtered by actor_investor_id."""
        try:
            if actor_investor_id:
                cursor = self.conn.execute(
                    """
                    SELECT event_id, timestamp_utc, actor_investor_id, subject_id,
                           event_type, resource_type, resource_id, outcome, request_id
                    FROM security_audit_events
                    WHERE actor_investor_id = ?
                    ORDER BY timestamp_utc DESC LIMIT ?;
                    """,
                    (actor_investor_id, limit),
                )
            else:
                cursor = self.conn.execute(
                    """
                    SELECT event_id, timestamp_utc, actor_investor_id, subject_id,
                           event_type, resource_type, resource_id, outcome, request_id
                    FROM security_audit_events
                    ORDER BY timestamp_utc DESC LIMIT ?;
                    """,
                    (limit,),
                )
            rows = cursor.fetchall()
            return [
                {
                    "event_id": row[0],
                    "timestamp_utc": row[1],
                    "actor_investor_id": row[2],
                    "subject_id": row[3],
                    "event_type": row[4],
                    "resource_type": row[5],
                    "resource_id": row[6],
                    "outcome": row[7],
                    "request_id": row[8],
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            raise SecurityAuditError(f"Failed to list security audit events: {e}") from e
