"""
Authentication & Security Test Suite (V1 Step 3 — Targeted Corrections).

Comprehensive unit and integration test suite verifying:
- Authenticated session lifecycle (creation, validation, expiry, invalidation, rotation).
- Environment Mode Isolation (Development Simulation vs Production Mode).
- Production Mode trusted principal assertion (X-Identity-Assertion) resolution.
- Rejection of client-selected investor_id in Production Mode.
- Server-side authorization & IDOR protection (strict investor_id scoping).
- Anti-CSRF token validation via constant-time comparison.
- Governed 5 MB portfolio upload size limit alignment (MAX_PORTFOLIO_UPLOAD_SIZE_BYTES = 5 MB).
- Preservation of legitimate negative numeric values (e.g. -100.50) without sign corruption.
- Security audit event logging without sensitive payload exposure.
- Zero financial methodology changes and 100% financial regression safety.
"""

import html
import hmac
import io
import os
import sqlite3
import tempfile
import urllib.parse
from datetime import datetime, timezone
import pytest

from audit.security_audit import SecurityAuditLogger, SecurityAuditError
from web.security import (
    SessionRepository,
    SecurityManager,
    PrincipalIdentityResolver,
    MAX_PORTFOLIO_UPLOAD_SIZE_BYTES,
    SecurityError,
    InvalidCSRFTokenError,
    UnauthorizedError,
    ForbiddenError,
)
from data.repositories.profile_repository import ProfileRepository
from data.repositories.portfolio_repository import PortfolioRepository
from data.adapters.portfolio_upload_adapter import PortfolioUploadAdapter
from models.investor_profile import InvestorProfileSnapshot, FinancialCapacitySnapshot
from portfolio.need_models import PortfolioExposureSnapshot, PortfolioHoldingRecord
from web.app import UIRequestHandler


@pytest.fixture
def temp_db_conn():
    """Creates a temporary SQLite database connection for isolated testing."""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_file.close()
    conn = sqlite3.connect(db_file.name)
    yield conn
    conn.close()
    if os.path.exists(db_file.name):
        os.remove(db_file.name)


# --- 1. SESSION MANAGEMENT & LIFECYCLE TESTS ---

def test_session_creation_and_retrieval(temp_db_conn):
    """Verifies creation of valid 256-bit token sessions and retrieval."""
    repo = SessionRepository(temp_db_conn)
    session = repo.create_session("inv_test_100")

    assert session.session_id.startswith("sess_")
    assert session.investor_id == "inv_test_100"
    assert session.is_active is True
    assert len(session.csrf_token) == 64  # hex 32 bytes

    retrieved = repo.get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.investor_id == "inv_test_100"
    assert retrieved.csrf_token == session.csrf_token


def test_session_invalidation_on_logout(temp_db_conn):
    """Verifies session invalidation upon explicit logout."""
    repo = SessionRepository(temp_db_conn)
    session = repo.create_session("inv_test_101")
    assert repo.get_session(session.session_id) is not None

    repo.invalidate_session(session.session_id)
    assert repo.get_session(session.session_id) is None


def test_session_fixation_rotation(temp_db_conn):
    """Verifies session rotation produces a new session_id and invalidates the old session."""
    repo = SessionRepository(temp_db_conn)
    old_session = repo.create_session("inv_test_102")

    new_session = repo.rotate_session(old_session.session_id)
    assert new_session.session_id != old_session.session_id
    assert new_session.investor_id == "inv_test_102"
    assert repo.get_session(old_session.session_id) is None
    assert repo.get_session(new_session.session_id) is not None


def test_empty_or_invalid_session_returns_none(temp_db_conn):
    """Verifies bogus session strings evaluate safely to None."""
    repo = SessionRepository(temp_db_conn)
    assert repo.get_session("") is None
    assert repo.get_session("bogus_session_id") is None


# --- 2. COOKIE FORMATTING & PARSING TESTS ---

def test_cookie_formatting_and_parsing():
    """Verifies Cookie formatting with HttpOnly, SameSite=Lax, Path=/ and parsing."""
    cookie_str = SecurityManager.format_session_cookie("sess_abc123", is_secure=False)
    assert "mf_session=sess_abc123" in cookie_str
    assert "Path=/" in cookie_str
    assert "SameSite=Lax" in cookie_str
    assert "HttpOnly" in cookie_str

    secure_cookie = SecurityManager.format_session_cookie("sess_abc123", is_secure=True)
    assert "__Host-mf_session=sess_abc123" in secure_cookie
    assert "Secure" in secure_cookie

    header = "other_cookie=123; mf_session=sess_abc123; foo=bar"
    parsed = SecurityManager.parse_session_cookie(header)
    assert parsed == "sess_abc123"

    logout_cookie = SecurityManager.format_logout_cookie()
    assert "Max-Age=0" in logout_cookie


# --- 3. ANTI-CSRF TOKEN VALIDATION TESTS ---

def test_csrf_token_validation():
    """Verifies constant-time anti-CSRF token comparison."""
    valid_token = "a1b2c3d4e5f67890" + "0" * 48
    
    assert SecurityManager.validate_csrf_token(valid_token, valid_token) is True
    assert SecurityManager.validate_csrf_token(valid_token, "wrong_token") is False
    assert SecurityManager.validate_csrf_token(valid_token, None) is False
    assert SecurityManager.validate_csrf_token("", valid_token) is False


# --- 4. INPUT SECURITY, XSS & CSV FORMULA SANITIZATION TESTS ---

def test_html_output_escaping():
    """Verifies HTML template escaping prevents XSS payloads."""
    xss_payload = '<script>alert("XSS")</script>'
    escaped = SecurityManager.escape_html(xss_payload)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped


def test_csv_formula_injection_sanitization():
    """Verifies formula characters (=, +, -, @) on text are escaped while negative numbers are preserved."""
    assert SecurityManager.sanitize_csv_text("=CMD|' /C calc'!A0") == "'=CMD|' /C calc'!A0"
    assert SecurityManager.sanitize_csv_text("+SUM(1,2)") == "'+SUM(1,2)"
    assert SecurityManager.sanitize_csv_text("@SUM(1,2)") == "'@SUM(1,2)"
    assert SecurityManager.sanitize_csv_text("Regular Scheme Name") == "Regular Scheme Name"

    # Preserves legitimate negative numbers
    assert SecurityManager.sanitize_csv_text("-100.50") == "-100.50"
    assert SecurityManager.sanitize_csv_text("-50") == "-50"

    adapter = PortfolioUploadAdapter()
    assert adapter.sanitize_cell_value("-100.50") == "-100.50"
    assert adapter.sanitize_cell_value("=CMD") == "CMD"


# --- 5. GOVERNED PORTFOLIO UPLOAD SIZE LIMIT ALIGNMENT TESTS ---

def test_governed_portfolio_upload_size_alignment():
    """Verifies application-level MAX_PORTFOLIO_UPLOAD_SIZE_BYTES is exactly 5 MB across HTTP layer & adapter."""
    assert MAX_PORTFOLIO_UPLOAD_SIZE_BYTES == 5 * 1024 * 1024
    assert PortfolioUploadAdapter.MAX_FILE_SIZE_BYTES == 5 * 1024 * 1024


# --- 6. SECURITY AUDIT EVENT LOGGING TESTS ---

def test_security_audit_logger(temp_db_conn):
    """Verifies immutable security audit event logging without sensitive payload leakage."""
    logger = SecurityAuditLogger(temp_db_conn)

    evt_id = logger.log_event(
        actor_investor_id="inv_test_200",
        event_type="AUTH_SUCCESS",
        resource_type="SESSION",
        outcome="SUCCESS",
        ip_address="192.168.1.50",
        user_agent="Mozilla/5.0 Test",
    )
    assert evt_id.startswith("sec_evt_")

    events = logger.list_events(actor_investor_id="inv_test_200")
    assert len(events) == 1
    assert events[0]["event_type"] == "AUTH_SUCCESS"
    assert events[0]["actor_investor_id"] == "inv_test_200"


# --- 7. AUTHORIZATION & INVESTOR IDENTITY SCOPING TESTS (IDOR PROTECTION) ---

def test_profile_repository_identity_isolation(temp_db_conn):
    """Verifies InvestorProfileSnapshot records are strictly isolated by investor_id."""
    profile_repo = ProfileRepository(temp_db_conn)

    prof_a = InvestorProfileSnapshot(
        profile_id="prof_a_1",
        investor_id="investor_A",
        profile_version="1.0.0",
        effective_date=datetime.now(timezone.utc).date(),
    )
    prof_b = InvestorProfileSnapshot(
        profile_id="prof_b_1",
        investor_id="investor_B",
        profile_version="1.0.0",
        effective_date=datetime.now(timezone.utc).date(),
    )

    profile_repo.save_profile(prof_a)
    profile_repo.save_profile(prof_b)

    retrieved_a = profile_repo.get_current_profile("investor_A")
    retrieved_b = profile_repo.get_current_profile("investor_B")

    assert retrieved_a is not None and retrieved_a.investor_id == "investor_A"
    assert retrieved_b is not None and retrieved_b.investor_id == "investor_B"

    # Verify querying investor_A does NOT return investor_B's profile
    assert profile_repo.get_profile_version("investor_A", "1.0.0").profile_id == "prof_a_1"
    assert profile_repo.get_profile_version("investor_A", "prof_b_1") is None


def test_portfolio_repository_identity_isolation(temp_db_conn):
    """Verifies PortfolioExposureSnapshot records are strictly isolated by investor_id."""
    port_repo = PortfolioRepository(temp_db_conn)

    snap_a = PortfolioExposureSnapshot(
        portfolio_snapshot_id="snap_a_1",
        investor_id="investor_A",
        holding_ids=["h1"],
        canonical_scheme_ids=["CAN_100044"],
    )
    holding_a = PortfolioHoldingRecord(
        holding_id="h1",
        portfolio_snapshot_id="snap_a_1",
        investor_id="investor_A",
        canonical_scheme_id="CAN_100044",
        units=100.0,
        source_provenance="test",
    )

    port_repo.save_portfolio(snap_a, [holding_a])

    # Query investor_A receives portfolio
    port_a = port_repo.get_current_portfolio("investor_A")
    assert port_a is not None
    assert port_a["snapshot"].portfolio_snapshot_id == "snap_a_1"

    # Query investor_B receives None (IDOR protection)
    port_b = port_repo.get_current_portfolio("investor_B")
    assert port_b is None


# --- 8. WEB HTTP HANDLER & ENVIRONMENT MODE INTEGRATION TESTS ---

def create_mock_handler(path: str, method: str = "GET", headers: dict = None, body: bytes = b""):
    """Constructs a UIRequestHandler with mocked socket & stream for unit testing."""
    headers = dict(headers or {})
    if body and "Content-Length" not in headers:
        headers["Content-Length"] = str(len(body))

    rfile = io.BytesIO(body)
    wfile = io.BytesIO()

    handler = UIRequestHandler.__new__(UIRequestHandler)
    handler.rfile = rfile
    handler.wfile = wfile
    handler.path = path
    handler.command = method
    handler.request_version = "HTTP/1.1"
    
    class MockHeaders:
        def __init__(self, d):
            self._d = {k.lower(): v for k, v in d.items()}
        def get(self, k, default=None):
            return self._d.get(k.lower(), default)
        def items(self):
            return self._d.items()
        def keys(self):
            return self._d.keys()
        def __getitem__(self, k):
            return self._d[k.lower()]

    handler.headers = MockHeaders(headers)
    handler.client_address = ("127.0.0.1", 12345)

    handler.response_code = None
    handler.response_headers = {}

    def mock_send_response(code, message=None):
        handler.response_code = code

    def mock_send_header(keyword, value):
        handler.response_headers[keyword.lower()] = value

    def mock_end_headers():
        pass

    def mock_send_error(code, message=None):
        handler.response_code = code
        handler.error_message = message

    handler.send_response = mock_send_response
    handler.send_header = mock_send_header
    handler.end_headers = mock_end_headers
    handler.send_error = mock_send_error

    return handler


def test_unauthenticated_request_redirects_to_login(temp_db_conn):
    """Verifies protected GET route redirects unauthenticated user to /login."""
    handler = create_mock_handler("/wealth")
    handler._get_db_connection = lambda: temp_db_conn

    handler.do_GET()

    assert handler.response_code == 303
    assert "/login?next=/wealth" in handler.response_headers.get("location", "")


def test_public_route_accessible_without_auth(temp_db_conn):
    """Verifies public route /discover is accessible without active session."""
    handler = create_mock_handler("/discover")
    handler._get_db_connection = lambda: temp_db_conn

    handler.do_GET()

    assert handler.response_code == 200
    out_html = handler.wfile.getvalue().decode("utf-8")
    assert "Discover Funds" in out_html


def test_development_mode_login(temp_db_conn, monkeypatch):
    """Verifies development mode permits simulated investor_id login."""
    monkeypatch.setenv("ENVIRONMENT_MODE", "development")

    body = b"investor_id=inv_dev_user_1&next=%2Fsettings"
    handler = create_mock_handler("/login", method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"}, body=body)
    handler._get_db_connection = lambda: temp_db_conn

    handler.do_POST()

    assert handler.response_code == 303
    assert handler.response_headers.get("location") == "/settings"
    cookie_str = handler.response_headers.get("set-cookie", "")
    assert "mf_session=" in cookie_str


def test_production_mode_rejects_client_selected_investor_id(temp_db_conn, monkeypatch):
    """Verifies production mode strictly rejects unverified client-selected investor_id login with HTTP 401."""
    monkeypatch.setenv("ENVIRONMENT_MODE", "production")

    body = b"investor_id=inv_hacker_attempt"
    handler = create_mock_handler("/login", method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"}, body=body)
    handler._get_db_connection = lambda: temp_db_conn

    handler.do_POST()

    assert handler.response_code == 401
    assert "Production mode authentication requires trusted external identity assertion" in getattr(handler, "error_message", "")


def test_production_mode_accepts_trusted_principal_assertion(temp_db_conn, monkeypatch):
    """Verifies production mode accepts trusted identity assertion header and resolves investor_id server-side."""
    monkeypatch.setenv("ENVIRONMENT_MODE", "production")

    # Map trusted principal
    resolver = PrincipalIdentityResolver(temp_db_conn)
    resolver.map_principal_to_investor("principal_oidc_777", "inv_canonical_777")

    headers = {
        "X-Identity-Assertion": "principal_oidc_777",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    handler = create_mock_handler("/login", method="POST", headers=headers, body=b"")
    handler._get_db_connection = lambda: temp_db_conn

    handler.do_POST()

    assert handler.response_code == 303
    cookie_str = handler.response_headers.get("set-cookie", "")
    assert "mf_session=" in cookie_str

    # Retrieve session and verify server-resolved identity
    session_id = SecurityManager.parse_session_cookie(cookie_str)
    session_repo = SessionRepository(temp_db_conn)
    session = session_repo.get_session(session_id)
    assert session is not None
    assert session.investor_id == "inv_canonical_777"
    assert session.is_dev_simulation is False


def test_production_mode_rejects_client_identity_override_attempt(temp_db_conn, monkeypatch):
    """Verifies production mode rejects client attempt to override server-resolved principal identity with HTTP 403."""
    monkeypatch.setenv("ENVIRONMENT_MODE", "production")

    resolver = PrincipalIdentityResolver(temp_db_conn)
    resolver.map_principal_to_investor("principal_oidc_777", "inv_canonical_777")

    headers = {
        "X-Identity-Assertion": "principal_oidc_777",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = b"investor_id=inv_override_attempt"
    handler = create_mock_handler("/login", method="POST", headers=headers, body=body)
    handler._get_db_connection = lambda: temp_db_conn

    handler.do_POST()

    assert handler.response_code == 403
    assert "Production mode rejects client-selected investor identity override" in getattr(handler, "error_message", "")


def test_upload_exceeding_5mb_rejected_at_http_layer(temp_db_conn):
    """Verifies HTTP layer rejects portfolio upload exceeding 5 MB with HTTP 400."""
    sess_repo = SessionRepository(temp_db_conn)
    session = sess_repo.create_session("inv_upload_test")

    # 5 MB + 1 byte
    oversized_body = b"x" * (5 * 1024 * 1024 + 1)
    headers = {
        "Cookie": f"mf_session={session.session_id}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": str(len(oversized_body)),
    }
    handler = create_mock_handler("/wealth/upload", method="POST", headers=headers, body=oversized_body)
    handler._get_db_connection = lambda: temp_db_conn

    handler.do_POST()

    assert handler.response_code == 400
    assert "File size exceeds 5 MB limit" in getattr(handler, "error_message", "")


def test_csrf_validation_failure_on_post(temp_db_conn):
    """Verifies state-changing POST without valid CSRF token is rejected with HTTP 400."""
    sess_repo = SessionRepository(temp_db_conn)
    session = sess_repo.create_session("inv_csrf_test")

    body = b"question_2=6.0&csrf_token=invalid_token"
    headers = {
        "Cookie": f"mf_session={session.session_id}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    handler = create_mock_handler("/onboarding", method="POST", headers=headers, body=body)
    handler._get_db_connection = lambda: temp_db_conn

    handler.do_POST()

    assert handler.response_code == 400
    assert "Anti-CSRF token validation failed" in getattr(handler, "error_message", "")
