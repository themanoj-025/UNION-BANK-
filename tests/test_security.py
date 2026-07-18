"""
tests/test_security.py  –  Security test fixtures for Phase 3 hardening.

Tests SQL injection payloads, XSS payloads, and CSRF token enforcement.
These tests verify that the application rejects malicious input and
enforces CSRF protection when cookies are used for authentication.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from unionbank.infrastructure.container import get_container, reset_container
from unionbank.utils.hashing import hash_password


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _fresh_db():
    """Fresh SQLite database per test."""
    data_dir = tempfile.mkdtemp(prefix="union_bank_security_test_")
    old_data_dir = os.environ.get("UNION_BANK_DATA_DIR")
    os.environ["UNION_BANK_DATA_DIR"] = data_dir
    os.environ["UNION_BANK_TESTING"] = "1"
    reset_container()
    yield
    reset_container()
    if old_data_dir:
        os.environ["UNION_BANK_DATA_DIR"] = old_data_dir
    else:
        os.environ.pop("UNION_BANK_DATA_DIR", None)


@pytest.fixture
def client():
    from unionbank.entrypoints.api.main import app
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def registered_customer(client: TestClient) -> dict:
    """
    Register a customer and return auth tokens.

    After login, clears cookies so subsequent requests use Bearer-only auth
    (no CSRF cookie), preventing 403s from the CSRF middleware.
    """
    resp = client.post("/api/auth/register", json={
        "name": "Security Test User",
        "age": 30,
        "gender": "Male",
        "mobile": "9876543210",
        "email": "security@test.com",
        "password": "SecureP@ss1",
        "confirm_password": "SecureP@ss1",
    })
    assert resp.status_code == 200
    msg = resp.json().get("message", "")
    acc_no = msg.split(": ")[-1].strip()

    login_resp = client.post("/api/auth/login", json={
        "account_number": acc_no,
        "password": "SecureP@ss1",
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()

    # Clear cookies so Bearer-only auth is used (no CSRF cookie present)
    client.cookies.clear()

    return {
        "account_number": acc_no,
        "access_token": login_data["access_token"],
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"},
    }


@pytest.fixture
def admin_token(client: TestClient) -> dict:
    """
    Create an admin user and return auth token.

    Clears cookies after login for Bearer-only auth.
    """
    from unionbank.domain.entities import AdminUser

    c = get_container()
    admin = AdminUser(username="testadmin", password=hash_password("Admin123!"))
    c.admin_repo().create(admin)
    c.admin_repo().commit()

    login_resp = client.post("/api/auth/admin-login", json={
        "username": "testadmin",
        "password": "Admin123!",
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()

    # Clear cookies so Bearer-only auth is used
    client.cookies.clear()

    return {
        "username": "testadmin",
        "access_token": login_data["access_token"],
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"},
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  SQL Injection Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSQLInjection:
    """Verify that SQL injection payloads in user input are safely handled."""

    SQLI_PAYLOADS = [
        "'; DROP TABLE accounts; --",
        "1' OR '1'='1",
        "admin'--",
        "1; UPDATE accounts SET balance=999999 WHERE account_number='1000000001'",
        "' UNION SELECT * FROM accounts --",
        "1' AND 1=1 UNION SELECT username, password FROM admins --",
        "'; INSERT INTO accounts VALUES('hacked','hacker',0); --",
        "1' WAITFOR DELAY '0:0:5' --",
        "'; EXEC xp_cmdshell('dir'); --",
    ]

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_sqli_in_register_name(self, client, payload):
        """SQLi in registration name field should be rejected by validation."""
        resp = client.post("/api/auth/register", json={
            "name": payload,
            "age": 25,
            "gender": "Male",
            "mobile": "9876543211",
            "email": "sqli@test.com",
            "password": "SecureP@ss1",
            "confirm_password": "SecureP@ss1",
        })
        # Should fail validation (name must be letters/spaces only)
        assert resp.status_code in (400, 422)

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_sqli_in_admin_search(self, client, admin_token, payload):
        """SQLi in admin search should not cause errors or data leaks."""
        resp = client.get(
            f"/api/admin/accounts/search?q={payload}",
            headers=admin_token["headers"],
        )
        # Should return empty results, not crash
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_sqli_in_v2_analyzr(self, client, registered_customer, payload):
        """SQLi in analyzr query should be handled safely."""
        resp = client.post(
            "/api/v2/analyzr/query",
            headers=registered_customer["headers"],
            json={"query": payload},
        )
        # Should return valid response, not crash
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


# ═══════════════════════════════════════════════════════════════════════════════
#  XSS Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestXSS:
    """Verify that XSS payloads in user input are safely handled."""

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<body onload=alert('XSS')>",
        "{{constructor.constructor('alert(1)')()}}",
        "<iframe src='javascript:alert(1)'>",
    ]

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_register_name(self, client, payload):
        """XSS in registration name should be rejected by validation."""
        resp = client.post("/api/auth/register", json={
            "name": payload,
            "age": 25,
            "gender": "Male",
            "mobile": "9876543212",
            "email": "xss@test.com",
            "password": "SecureP@ss1",
            "confirm_password": "SecureP@ss1",
        })
        # Should fail validation (name must be letters/spaces only)
        assert resp.status_code in (400, 422)

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_update_profile_name(self, client, registered_customer, payload):
        """XSS in profile update name should be rejected."""
        resp = client.put(
            "/api/account/profile",
            headers=registered_customer["headers"],
            json={"name": payload},
        )
        # Should fail validation (name must be letters/spaces only)
        assert resp.status_code in (400, 422)

    def test_security_headers_present(self, client):
        """Response should include security headers that mitigate XSS."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Content-Security-Policy" in resp.headers


# ═══════════════════════════════════════════════════════════════════════════════
#  CSRF Protection Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCSRF:
    """Verify CSRF protection with double-submit cookie pattern."""

    def test_csrf_token_set_on_login(self, client):
        """Login should set ub_csrf_token cookie."""
        reg_resp = client.post("/api/auth/register", json={
            "name": "CSRF Test User",
            "age": 28,
            "gender": "Female",
            "mobile": "9876543213",
            "email": "csrf@test.com",
            "password": "SecureP@ss1",
            "confirm_password": "SecureP@ss1",
        })
        msg = reg_resp.json().get("message", "")
        acc_no = msg.split(": ")[-1].strip()

        resp = client.post("/api/auth/login", json={
            "account_number": acc_no,
            "password": "SecureP@ss1",
        })
        # Check cookies were set — get_list returns raw header strings
        set_cookie_headers = resp.headers.get_list("set-cookie")
        cookie_names = [h.split("=")[0] for h in set_cookie_headers]
        assert "ub_access_token" in cookie_names
        assert "ub_refresh_token" in cookie_names
        assert "ub_csrf_token" in cookie_names

    def test_stateful_request_without_csrf_cookie_allowed(self, client, registered_customer):
        """Stateful request without CSRF cookie (Bearer token only) should work."""
        # registered_customer fixture clears cookies, so no CSRF cookie present
        resp = client.post(
            "/api/account/deposit",
            headers=registered_customer["headers"],
            json={"amount": 100.0},
        )
        assert resp.status_code == 200

    def test_stateful_request_with_csrf_cookie_wrong_header(self, client):
        """Stateful request with CSRF cookie but wrong header should fail."""
        # Set a CSRF cookie but send wrong header
        client.cookies.set("ub_csrf_token", "real_token_value")
        resp = client.post(
            "/api/account/deposit",
            headers={
                "X-CSRF-Token": "wrong_token_value",
            },
            json={"amount": 100.0},
        )
        # CSRF middleware should reject (403) since tokens don't match
        assert resp.status_code == 403

    def test_csrf_token_validated_on_transfer(self, client):
        """Transfer with CSRF cookie must include matching header."""
        client.cookies.set("ub_csrf_token", "test_csrf_token_123")
        resp = client.post(
            "/api/account/transfer",
            headers={"X-CSRF-Token": "different_token"},
            json={"target_account": "9999999999", "amount": 50.0},
        )
        # Should fail CSRF validation (403) since tokens don't match
        assert resp.status_code == 403

    def test_auth_endpoints_exempt_from_csrf(self, client):
        """Login/register/refresh should not require CSRF token."""
        # These endpoints set cookies, so they must be exempt
        resp = client.post("/api/auth/login", json={
            "account_number": "1000000001",
            "password": "wrong",
        })
        # Should fail auth (401/404), not CSRF (403)
        assert resp.status_code in (401, 404)

    def test_safe_methods_exempt_from_csrf(self, client):
        """GET requests should not require CSRF token."""
        resp = client.get("/api/health")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
#  Cookie Security Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCookieSecurity:
    """Verify cookie security attributes."""

    def test_access_token_cookie_is_http_only(self, client):
        """Access token cookie should be httpOnly (not accessible to JS)."""
        reg_resp = client.post("/api/auth/register", json={
            "name": "Cookie Test User",
            "age": 25,
            "gender": "Male",
            "mobile": "9876543214",
            "email": "cookie@test.com",
            "password": "SecureP@ss1",
            "confirm_password": "SecureP@ss1",
        })
        msg = reg_resp.json().get("message", "")
        acc_no = msg.split(": ")[-1].strip()

        resp = client.post("/api/auth/login", json={
            "account_number": acc_no,
            "password": "SecureP@ss1",
        })
        set_cookie_headers = resp.headers.get_list("set-cookie")
        for cookie_header in set_cookie_headers:
            if "ub_access_token" in cookie_header:
                assert "httponly" in cookie_header.lower()
                break
        else:
            pytest.fail("ub_access_token cookie not found in response")

    def test_csrf_token_cookie_is_not_http_only(self, client):
        """CSRF token cookie should NOT be httpOnly (JS needs to read it)."""
        reg_resp = client.post("/api/auth/register", json={
            "name": "CSRF Cookie Test",
            "age": 25,
            "gender": "Male",
            "mobile": "9876543215",
            "email": "csrfcookie@test.com",
            "password": "SecureP@ss1",
            "confirm_password": "SecureP@ss1",
        })
        msg = reg_resp.json().get("message", "")
        acc_no = msg.split(": ")[-1].strip()

        resp = client.post("/api/auth/login", json={
            "account_number": acc_no,
            "password": "SecureP@ss1",
        })
        set_cookie_headers = resp.headers.get_list("set-cookie")
        for cookie_header in set_cookie_headers:
            if "ub_csrf_token" in cookie_header:
                assert "httponly" not in cookie_header.lower()
                break
        else:
            pytest.fail("ub_csrf_token cookie not found in response")
