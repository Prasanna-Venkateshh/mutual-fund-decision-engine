"""
Security & Session Management Module for Web Application V1.

Provides session lifecycle management, secure HTTP cookie formatting,
anti-CSRF token validation via constant-time comparison, HTML escaping,
input sanitization, environment mode isolation (development vs production),
and principal-to-investor identity mapping.

Governance Rules Enforced:
- Governed portfolio upload size limit: MAX_PORTFOLIO_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024 (5 MB).
- Authenticated session principal mapped to internal investor_id.
- Production Mode (ENVIRONMENT_MODE=production) strictly REJECTS client-selected investor identity.
- Development Mode (ENVIRONMENT_MODE=development) isolates identity simulation and labels dev sessions.
- Cookies set with HttpOnly, SameSite=Lax, Path=/, Max-Age=86400.
- Synchronizer CSRF tokens validated via hmac.compare_digest.
- HTML output escaping applied to user-controlled fields.
"""

import html
import hmac
import os
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple

# Single Governed Portfolio Upload Size Cap (5 MB)
MAX_PORTFOLIO_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024


class SecurityError(Exception):
    """Base exception for security and session management errors."""
    pass


class InvalidCSRFTokenError(SecurityError):
    """Raised when CSRF token validation fails."""
    pass


class UnauthorizedError(SecurityError):
    """Raised when an unauthenticated request attempts to access a protected resource."""
    pass


class ForbiddenError(SecurityError):
    """Raised when an authenticated principal attempts unauthorized access to another investor's resource (IDOR)."""
    pass


CREATE_SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS session_records (
    session_id TEXT PRIMARY KEY,
    investor_id TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    expires_at_utc TEXT NOT NULL,
    last_accessed_at_utc TEXT NOT NULL,
    csrf_token TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_dev_simulation INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS principal_identity_mappings (
    principal_id TEXT PRIMARY KEY,
    investor_id TEXT NOT NULL UNIQUE,
    created_at_utc TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    investor_id: str
    created_at_utc: str
    expires_at_utc: str
    last_accessed_at_utc: str
    csrf_token: str
    is_active: bool = True
    is_dev_simulation: bool = False


class PrincipalIdentityResolver:
    """Repository managing trusted principal-to-investor mappings."""

    def __init__(self, db_conn: sqlite3.Connection):
        if db_conn is None:
            raise SecurityError("sqlite3.Connection cannot be None")
        self.conn = db_conn
        self._init_tables()

    def _init_tables(self) -> None:
        try:
            self.conn.executescript(CREATE_SESSIONS_TABLE_SQL)
            self.conn.commit()
        except sqlite3.Error as e:
            raise SecurityError(f"Principal mapping schema initialization failed: {e}") from e

    def map_principal_to_investor(self, principal_id: str, investor_id: str) -> str:
        """Persists trusted principal -> internal investor_id mapping."""
        if not principal_id or not investor_id:
            raise SecurityError("principal_id and investor_id must be non-empty strings.")

        now_utc = datetime.now(timezone.utc).isoformat()
        try:
            self.conn.execute(
                """
                INSERT INTO principal_identity_mappings (principal_id, investor_id, created_at_utc)
                VALUES (?, ?, ?)
                ON CONFLICT(principal_id) DO UPDATE SET investor_id = excluded.investor_id;
                """,
                (principal_id, investor_id, now_utc),
            )
            self.conn.commit()
            return investor_id
        except sqlite3.Error as e:
            raise SecurityError(f"Failed to map principal to investor: {e}") from e

    def resolve_investor_id(self, principal_id: str) -> Optional[str]:
        """Resolves internal investor_id from a trusted principal_id assertion."""
        if not principal_id:
            return None
        try:
            cursor = self.conn.execute(
                "SELECT investor_id FROM principal_identity_mappings WHERE principal_id = ?;",
                (principal_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            raise SecurityError(f"Failed to resolve investor identity: {e}") from e


class SessionRepository:
    """Repository managing server-side authenticated sessions in SQLite."""

    def __init__(self, db_conn: sqlite3.Connection):
        if db_conn is None:
            raise SecurityError("sqlite3.Connection cannot be None")
        self.conn = db_conn
        self._init_tables()

    def _init_tables(self) -> None:
        """Initializes session_records and additive columns if missing."""
        try:
            self.conn.executescript(CREATE_SESSIONS_TABLE_SQL)

            cursor = self.conn.execute("PRAGMA table_info(session_records);")
            columns = [row[1] for row in cursor.fetchall()]
            if "is_dev_simulation" not in columns:
                self.conn.execute("ALTER TABLE session_records ADD COLUMN is_dev_simulation INTEGER NOT NULL DEFAULT 0;")
            
            self.conn.commit()
        except sqlite3.Error as e:
            raise SecurityError(f"Session database schema initialization failed: {e}") from e

    def create_session(self, investor_id: str, lifetime_seconds: int = 86400, is_dev_simulation: bool = False) -> SessionRecord:
        """
        Creates a new authenticated session for an investor_id.
        Generates 256-bit cryptographically secure session_id and CSRF token.
        """
        if not investor_id or not investor_id.strip():
            raise SecurityError("investor_id must be a non-empty string.")

        session_id = f"sess_{secrets.token_urlsafe(32)}"
        csrf_token = secrets.token_hex(32)
        
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        expires_str = (now + timedelta(seconds=lifetime_seconds)).isoformat()
        dev_flag = 1 if is_dev_simulation else 0

        try:
            self.conn.execute(
                """
                INSERT INTO session_records (
                    session_id, investor_id, created_at_utc, expires_at_utc,
                    last_accessed_at_utc, csrf_token, is_active, is_dev_simulation
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?);
                """,
                (session_id, investor_id, now_str, expires_str, now_str, csrf_token, dev_flag),
            )
            self.conn.commit()
            return SessionRecord(
                session_id=session_id,
                investor_id=investor_id,
                created_at_utc=now_str,
                expires_at_utc=expires_str,
                last_accessed_at_utc=now_str,
                csrf_token=csrf_token,
                is_active=True,
                is_dev_simulation=is_dev_simulation,
            )
        except sqlite3.Error as e:
            raise SecurityError(f"Failed to create session: {e}") from e

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """
        Retrieves a valid, active, non-expired session.
        Updates last_accessed_at_utc upon retrieval.
        """
        if not session_id or not session_id.strip():
            return None

        now_utc = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.conn.execute(
                """
                SELECT session_id, investor_id, created_at_utc, expires_at_utc,
                       last_accessed_at_utc, csrf_token, is_active, is_dev_simulation
                FROM session_records
                WHERE session_id = ? AND is_active = 1 AND expires_at_utc > ?;
                """,
                (session_id, now_utc),
            )
            row = cursor.fetchone()
            if not row:
                return None

            # Touch session
            self.conn.execute(
                "UPDATE session_records SET last_accessed_at_utc = ? WHERE session_id = ?;",
                (now_utc, session_id),
            )
            self.conn.commit()

            return SessionRecord(
                session_id=row[0],
                investor_id=row[1],
                created_at_utc=row[2],
                expires_at_utc=row[3],
                last_accessed_at_utc=now_utc,
                csrf_token=row[5],
                is_active=bool(row[6]),
                is_dev_simulation=bool(row[7]),
            )
        except sqlite3.Error as e:
            raise SecurityError(f"Failed to retrieve session: {e}") from e

    def invalidate_session(self, session_id: str) -> None:
        """Invalidates a session on logout."""
        if not session_id:
            return
        try:
            self.conn.execute(
                "UPDATE session_records SET is_active = 0 WHERE session_id = ?;",
                (session_id,),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            raise SecurityError(f"Failed to invalidate session: {e}") from e

    def rotate_session(self, old_session_id: str) -> SessionRecord:
        """
        Session fixation protection: invalidates old session and creates a new session
        for the same investor_id.
        """
        old_session = self.get_session(old_session_id)
        if not old_session:
            raise SecurityError("Cannot rotate invalid or expired session.")

        self.invalidate_session(old_session_id)
        return self.create_session(old_session.investor_id, is_dev_simulation=old_session.is_dev_simulation)


class SecurityManager:
    """Helper utilities for cookies, CSRF validation, environment mode, and XSS escaping."""

    COOKIE_NAME = "mf_session"
    HOST_COOKIE_NAME = "__Host-mf_session"

    @staticmethod
    def get_environment_mode() -> str:
        """Returns current environment mode: 'development' vs 'production'."""
        mode = os.environ.get("ENVIRONMENT_MODE", os.environ.get("CONFIG_ENV", "development")).lower().strip()
        return "production" if mode in ("production", "prod") else "development"

    @staticmethod
    def is_production_mode() -> bool:
        """Returns True if running in production mode."""
        return SecurityManager.get_environment_mode() == "production"

    @staticmethod
    def authenticate_login_request(
        headers: Dict[str, str],
        post_params: Dict[str, Any],
        principal_resolver: PrincipalIdentityResolver,
    ) -> Tuple[str, bool]:
        """
        Authenticates a login request based on environment mode.
        
        Production Mode Rules:
        - Rejects client-supplied investor_id form inputs.
        - Requires a trusted identity assertion header (e.g. X-Identity-Assertion or X-Trusted-Principal).
        - Resolves identity strictly via PrincipalIdentityResolver.
        
        Development Mode Rules:
        - Labels identity as [DEV SIMULATION].
        - Allows local development testing while preventing production accidental reliance.
        """
        is_prod = SecurityManager.is_production_mode()

        # Normalize headers dictionary keys to lowercase for robust lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}
        trusted_header = headers_lower.get("x-identity-assertion") or headers_lower.get("x-trusted-principal")
        if trusted_header:
            trusted_header = trusted_header.strip()
            resolved = principal_resolver.resolve_investor_id(trusted_header)
            if resolved:
                # If client form param attempts to override trusted identity in prod, fail
                client_inv = post_params.get("investor_id", [""])[0].strip()
                if is_prod and client_inv and client_inv != resolved:
                    raise ForbiddenError("Production mode rejects client-selected investor identity override.")
                return resolved, False

        # In Production Mode: Fail closed if no trusted assertion is present
        if is_prod:
            raise UnauthorizedError(
                "Production mode authentication requires trusted external identity assertion (X-Identity-Assertion). "
                "Client-selected investor_id login is disabled in production."
            )

        # In Development Mode: Allow isolated identity simulation
        client_inv = post_params.get("investor_id", ["investor_dev_default"])[0].strip()
        if not client_inv:
            client_inv = "investor_dev_default"
        return client_inv, True

    @staticmethod
    def format_session_cookie(session_id: str, is_secure: bool = False, max_age: int = 86400) -> str:
        """Formats governed HTTP Set-Cookie header string."""
        name = SecurityManager.HOST_COOKIE_NAME if is_secure else SecurityManager.COOKIE_NAME
        secure_flag = "; Secure" if is_secure else ""
        return f"{name}={session_id}; Path=/; SameSite=Lax; HttpOnly; Max-Age={max_age}{secure_flag}"

    @staticmethod
    def format_logout_cookie(is_secure: bool = False) -> str:
        """Formats expired cookie header for logout."""
        name = SecurityManager.HOST_COOKIE_NAME if is_secure else SecurityManager.COOKIE_NAME
        secure_flag = "; Secure" if is_secure else ""
        return f"{name}=deleted; Path=/; SameSite=Lax; HttpOnly; Max-Age=0{secure_flag}"

    @staticmethod
    def parse_session_cookie(cookie_header_str: Optional[str]) -> Optional[str]:
        """Parses session ID from Cookie request header string."""
        if not cookie_header_str:
            return None

        cookies = cookie_header_str.split(";")
        for cookie in cookies:
            cookie = cookie.strip()
            if "=" in cookie:
                k, v = cookie.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k in (SecurityManager.HOST_COOKIE_NAME, SecurityManager.COOKIE_NAME):
                    if v and v != "deleted":
                        return v
        return None

    @staticmethod
    def validate_csrf_token(session_csrf_token: str, submitted_csrf_token: Optional[str]) -> bool:
        """
        Validates anti-CSRF token using constant-time string comparison (hmac.compare_digest).
        """
        if not session_csrf_token or not submitted_csrf_token:
            return False
        return hmac.compare_digest(session_csrf_token.strip(), submitted_csrf_token.strip())

    @staticmethod
    def escape_html(val: Any) -> str:
        """Escapes string for safe insertion into HTML templates."""
        if val is None:
            return ""
        return html.escape(str(val), quote=True)

    @staticmethod
    def sanitize_csv_text(val: Optional[str]) -> Optional[str]:
        """Strips or escapes leading CSV formula injection characters (=, +, -, @). Preserves negative numbers."""
        if val is None:
            return None
        s = str(val).strip()
        # Preserve legitimate negative numbers (e.g. -100.50)
        try:
            float(s)
            return s
        except ValueError:
            pass
        if s and s[0] in ("=", "+", "-", "@"):
            return "'" + s
        return s
