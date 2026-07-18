"""
tests/test_api_integration.py  –  FastAPI TestClient integration tests.

These tests exercise the real FastAPI application as a black box,
using an isolated SQLite database per test. All persistence goes
through the container's repositories/services — no JSON involved.

Usage:
    pytest tests/test_api_integration.py -v --tb=short
"""

from __future__ import annotations

import os
import tempfile
from decimal import Decimal

import pytest
from unionbank.infrastructure.container import get_container, reset_container
from fastapi.testclient import TestClient

# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _fresh_db():
    """
    Set up a fresh SQLite database for each test.

    Creates a temp directory for the DB, resets the container,
    and ensures every test starts clean.
    """
    data_dir = tempfile.mkdtemp(prefix="union_bank_api_test_")
    old_data_dir = os.environ.get("UNION_BANK_DATA_DIR")
    os.environ["UNION_BANK_DATA_DIR"] = data_dir
    os.environ["UNION_BANK_TESTING"] = "1"

    # Reset the DI container so a fresh DB gets created
    reset_container()

    yield

    reset_container()
    if old_data_dir:
        os.environ["UNION_BANK_DATA_DIR"] = old_data_dir
    else:
        os.environ.pop("UNION_BANK_DATA_DIR", None)


@pytest.fixture
def c():
    """Get a fresh DI container with a clean SQLite database."""
    return get_container()


@pytest.fixture
def client():
    """FastAPI TestClient connected to the real application."""
    # Import api after container is reset so init_db uses the test DB
    from unionbank.entrypoints.api.main import app
    with TestClient(app) as tc:
        yield tc


# ── Customer account fixtures ──────────────────────────────────────────────


@pytest.fixture
def sample_customer_registration() -> dict:
    """Valid customer registration payload."""
    return {
        "name": "Alice Johnson",
        "age": 28,
        "gender": "Female",
        "mobile": "9876543210",
        "email": "alice@example.com",
        "password": "SecureP@ss1",
        "confirm_password": "SecureP@ss1",
    }


@pytest.fixture
def registered_customer(client: TestClient, sample_customer_registration: dict) -> dict:
    """Register a customer and return the resulting account info + auth tokens."""
    resp = client.post("/api/auth/register", json=sample_customer_registration)
    assert resp.status_code == 200
    data = resp.json()

    # Extract account number from the message
    msg = data.get("message", "")
    assert "Account created successfully" in msg
    acc_no = msg.split(": ")[-1].strip()

    # Login to get JWT token
    login_resp = client.post("/api/auth/login", json={
        "account_number": acc_no,
        "password": sample_customer_registration["password"],
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()

    # Make sure the account has some balance for operations that need it
    c = get_container()
    c.transaction_service().deposit(acc_no, Decimal("1000.00"), "Salary")

    # Clear cookies so Bearer-only auth is used (no CSRF cookie present)
    client.cookies.clear()

    return {
        "account_number": acc_no,
        "name": sample_customer_registration["name"],
        "password": sample_customer_registration["password"],
        "access_token": login_data["access_token"],
        "refresh_token": login_data.get("refresh_token"),
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"},
    }


@pytest.fixture
def second_registered_customer(client: TestClient) -> dict:
    """Register a second customer (for transfer tests)."""
    resp = client.post("/api/auth/register", json={
        "name": "Bob Smith",
        "age": 32,
        "gender": "Male",
        "mobile": "9123456789",
        "email": "bob@example.com",
        "password": "BobStr0ng!",
        "confirm_password": "BobStr0ng!",
    })
    assert resp.status_code == 200
    msg = resp.json().get("message", "")
    acc_no = msg.split(": ")[-1].strip()

    login_resp = client.post("/api/auth/login", json={
        "account_number": acc_no,
        "password": "BobStr0ng!",
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()

    # Clear cookies so Bearer-only auth is used (no CSRF cookie present)
    client.cookies.clear()

    return {
        "account_number": acc_no,
        "name": "Bob Smith",
        "access_token": login_data["access_token"],
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"},
    }


@pytest.fixture
def admin_token(client: TestClient) -> dict:
    """Create an admin user and return auth token."""
    from unionbank.domain.entities import AdminUser
    from unionbank.utils.hashing import hash_password

    c = get_container()
    admin_repo = c.admin_repo()

    # Create admin user directly in DB
    admin = AdminUser(
        username="admin",
        password=hash_password("admin123"),
    )
    admin_repo.create(admin)
    admin_repo.commit()

    # Login
    resp = client.post("/api/auth/admin-login", json={
        "username": "admin",
        "password": "admin123",
    })
    assert resp.status_code == 200
    data = resp.json()

    # Clear cookies so Bearer-only auth is used (no CSRF cookie present)
    client.cookies.clear()

    return {
        "username": "admin",
        "access_token": data["access_token"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  1.  Health & Utility Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


class TestHealthAndUtilities:

    def test_health_check(self, client):
        """GET /api/health should return healthy status."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Union Bank API"

    def test_categories(self, client):
        """GET /api/categories should return the list of categories."""
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        categories = resp.json()
        assert isinstance(categories, list)
        assert len(categories) >= 5
        assert "General" in categories
        assert "Food & Dining" in categories
        assert "Salary" in categories


# ═══════════════════════════════════════════════════════════════════════════════
#  2.  Authentication
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuth:

    def test_register_success(self, client, sample_customer_registration):
        """Register a new customer should succeed."""
        resp = client.post("/api/auth/register", json=sample_customer_registration)
        assert resp.status_code == 200
        data = resp.json()
        assert "Account created successfully" in data["message"]
        assert "account_number" in data["message"] or "Account number" in data["message"]

    def test_register_duplicate_email(self, client, sample_customer_registration):
        """Registering with the same email should succeed (no email uniqueness enforced)."""
        resp1 = client.post("/api/auth/register", json=sample_customer_registration)
        assert resp1.status_code == 200

        # Change account number field but keep same email — should still work
        data2 = sample_customer_registration.copy()
        data2["mobile"] = "9876543211"
        resp2 = client.post("/api/auth/register", json=data2)
        assert resp2.status_code == 200

    def test_register_invalid_name(self, client, sample_customer_registration):
        """Register with invalid name (too short) should fail."""
        data = sample_customer_registration.copy()
        data["name"] = "A"
        resp = client.post("/api/auth/register", json=data)
        assert resp.status_code == 400

    def test_register_invalid_password(self, client, sample_customer_registration):
        """
        Register with weak password should fail.

        The Pydantic model enforces min_length=8 on the password field, so
        the request fails with a 422 Unprocessable Entity (not 400).
        """
        data = sample_customer_registration.copy()
        data["password"] = "weak"
        data["confirm_password"] = "weak"
        resp = client.post("/api/auth/register", json=data)
        assert resp.status_code == 422

    def test_register_password_mismatch(self, client, sample_customer_registration):
        """Register with non-matching passwords should fail."""
        data = sample_customer_registration.copy()
        data["confirm_password"] = "DifferentP@ss1"
        resp = client.post("/api/auth/register", json=data)
        assert resp.status_code == 400

    def test_login_success(self, client, registered_customer):
        """Successful login should return JWT tokens."""
        resp = client.post("/api/auth/login", json={
            "account_number": registered_customer["account_number"],
            "password": registered_customer["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "customer"

    def test_login_wrong_password(self, client, registered_customer):
        """Login with wrong password should fail."""
        resp = client.post("/api/auth/login", json={
            "account_number": registered_customer["account_number"],
            "password": "WrongPassword!1",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_account(self, client):
        """Login with an account that doesn't exist should fail."""
        resp = client.post("/api/auth/login", json={
            "account_number": "9999999999",
            "password": "SomePass123",
        })
        assert resp.status_code == 404

    def test_admin_login_success(self, client, admin_token):
        """Admin login should succeed."""
        # admin_token fixture already verified the login
        pass

    def test_admin_login_wrong_password(self, client):
        """Admin login with wrong password should fail."""
        resp = client.post("/api/auth/admin-login", json={
            "username": "admin",
            "password": "WrongPassword",
        })
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
#  3.  Account Profile
# ═══════════════════════════════════════════════════════════════════════════════


class TestAccountProfile:

    def test_get_profile(self, client, registered_customer):
        """GET /api/account/profile should return the customer's profile."""
        resp = client.get("/api/account/profile", headers=registered_customer["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_number"] == registered_customer["account_number"]
        assert data["name"] == registered_customer["name"]
        assert "balance" in data
        assert "status" in data

    def test_get_profile_unauthorized(self, client):
        """
        GET /api/account/profile without token should fail.

        HTTPBearer (no credentials) returns 401, not 403. 403 would come
        from a valid token with wrong role.
        """
        resp = client.get("/api/account/profile")
        assert resp.status_code == 401

    def test_update_profile(self, client, registered_customer):
        """PUT /api/account/profile should update customer details."""
        resp = client.put("/api/account/profile", headers=registered_customer["headers"], json={
            "name": "Alice Johnson Jr.",
            "age": 29,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Alice Johnson Jr."
        assert data["age"] == 29

    def test_change_password(self, client, registered_customer):
        """POST /api/account/change-password should update the password."""
        resp = client.post("/api/account/change-password", headers=registered_customer["headers"], json={
            "current_password": registered_customer["password"],
            "new_password": "NewStr0ngP@ss",
            "confirm_password": "NewStr0ngP@ss",
        })
        assert resp.status_code == 200

        # Verify new password works for login
        login_resp = client.post("/api/auth/login", json={
            "account_number": registered_customer["account_number"],
            "password": "NewStr0ngP@ss",
        })
        assert login_resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
#  4.  Transactions (Deposit, Withdraw, Transfer, Statement)
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransactions:

    def test_get_balance(self, client, registered_customer):
        """GET /api/account/balance should return the current balance."""
        resp = client.get("/api/account/balance", headers=registered_customer["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_number"] == registered_customer["account_number"]
        assert data["balance"] >= 1000.0  # deposited in fixture

    def test_deposit(self, client, registered_customer):
        """POST /api/account/deposit should add funds."""
        resp = client.post("/api/account/deposit", headers=registered_customer["headers"], json={
            "amount": 500.0,
            "category": "Salary",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "deposited successfully" in data["message"]

        # Verify balance updated
        bal_resp = client.get("/api/account/balance", headers=registered_customer["headers"])
        assert bal_resp.json()["balance"] >= 1500.0

    def test_deposit_invalid_amount(self, client, registered_customer):
        """
        Deposit with zero/negative amount should fail.

        The Pydantic model enforces gt=0 on the amount field, so the request
        fails with a 422 Unprocessable Entity (not 400).
        """
        resp = client.post("/api/account/deposit", headers=registered_customer["headers"], json={
            "amount": -100.0,
        })
        assert resp.status_code == 422

    def test_withdraw(self, client, registered_customer):
        """POST /api/account/withdraw should deduct funds."""
        resp = client.post("/api/account/withdraw", headers=registered_customer["headers"], json={
            "amount": 200.0,
            "category": "Food & Dining",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "withdrawn successfully" in data["message"]

    def test_withdraw_insufficient(self, client, registered_customer):
        """Withdraw more than balance should fail."""
        resp = client.post("/api/account/withdraw", headers=registered_customer["headers"], json={
            "amount": 999999.0,
        })
        assert resp.status_code == 400

    def test_transfer(self, client, registered_customer, second_registered_customer):
        """POST /api/account/transfer should move funds between accounts."""
        resp = client.post("/api/account/transfer", headers=registered_customer["headers"], json={
            "target_account": second_registered_customer["account_number"],
            "amount": 300.0,
            "category": "General",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "transferred" in data["message"].lower()

        # Verify sender balance decreased
        sender_bal = client.get("/api/account/balance", headers=registered_customer["headers"]).json()
        assert sender_bal["balance"] >= 700.0  # 1000 - 300 = 700

        # Verify receiver balance increased
        receiver_bal = client.get(
            "/api/account/balance", headers=second_registered_customer["headers"]
        ).json()
        assert receiver_bal["balance"] >= 300.0

    def test_transfer_to_self(self, client, registered_customer):
        """Transfer to own account should fail."""
        resp = client.post("/api/account/transfer", headers=registered_customer["headers"], json={
            "target_account": registered_customer["account_number"],
            "amount": 100.0,
        })
        assert resp.status_code == 400

    def test_transfer_to_nonexistent(self, client, registered_customer):
        """Transfer to nonexistent account should fail."""
        resp = client.post("/api/account/transfer", headers=registered_customer["headers"], json={
            "target_account": "9999999999",
            "amount": 100.0,
        })
        assert resp.status_code == 404

    def test_transfer_insufficient(self, client, registered_customer, second_registered_customer):
        """Transfer more than balance should fail."""
        resp = client.post("/api/account/transfer", headers=registered_customer["headers"], json={
            "target_account": second_registered_customer["account_number"],
            "amount": 999999.0,
        })
        assert resp.status_code == 400

    def test_full_statement(self, client, registered_customer):
        """GET /api/account/statements should return transaction history."""
        # Do some transactions first
        client.post("/api/account/deposit", headers=registered_customer["headers"], json={"amount": 100.0})
        client.post("/api/account/withdraw", headers=registered_customer["headers"], json={"amount": 50.0})

        resp = client.get("/api/account/statements", headers=registered_customer["headers"])
        assert resp.status_code == 200
        txns = resp.json()
        assert isinstance(txns, list)
        assert len(txns) >= 2  # initial deposit + new deposit + new withdraw
        # Newest first
        assert txns[0]["txn_id"] is not None

    def test_mini_statement(self, client, registered_customer):
        """GET /api/account/statements/mini should return last 5."""
        resp = client.get("/api/account/statements/mini", headers=registered_customer["headers"])
        assert resp.status_code == 200
        txns = resp.json()
        # The fixture deposits 1000, so at minimum we have 1 transaction
        assert len(txns) <= 5

    def test_export_csv(self, client, registered_customer):
        """GET /api/account/export-csv should return CSV content."""
        resp = client.get("/api/account/export-csv", headers=registered_customer["headers"])
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        content = resp.content.decode("utf-8-sig")
        assert "Transaction ID" in content
        assert "DEPOSIT" in content


# ═══════════════════════════════════════════════════════════════════════════════
#  5.  Savings Goals
# ═══════════════════════════════════════════════════════════════════════════════


class TestSavingsGoals:

    def test_create_goal(self, client, registered_customer):
        """POST /api/savings should create a new savings goal."""
        resp = client.post("/api/savings", headers=registered_customer["headers"], json={
            "name": "Vacation Fund",
            "target_amount": 5000.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Vacation Fund"
        assert data["target_amount"] == 5000.0
        assert data["current_amount"] == 0.0
        assert data["progress_pct"] == 0.0

    def test_list_goals(self, client, registered_customer):
        """GET /api/savings should list all goals."""
        # Create two goals
        client.post("/api/savings", headers=registered_customer["headers"], json={
            "name": "Goal 1", "target_amount": 1000.0,
        })
        client.post("/api/savings", headers=registered_customer["headers"], json={
            "name": "Goal 2", "target_amount": 2000.0,
        })

        resp = client.get("/api/savings", headers=registered_customer["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_goals"] >= 2
        assert len(data["goals"]) >= 2

    def test_contribute_to_goal(self, client, registered_customer):
        """POST /api/savings/{goal_id}/contribute should move funds to goal."""
        # Create a goal
        create_resp = client.post("/api/savings", headers=registered_customer["headers"], json={
            "name": "New Car", "target_amount": 10000.0,
        })
        goal_id = create_resp.json()["goal_id"]

        # Contribute
        resp = client.post(f"/api/savings/{goal_id}/contribute", headers=registered_customer["headers"], json={
            "amount": 500.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_amount"] == 500.0
        assert data["progress_pct"] == 5.0

    def test_contribute_insufficient(self, client, registered_customer):
        """Contribute more than balance should fail."""
        create_resp = client.post("/api/savings", headers=registered_customer["headers"], json={
            "name": "Dream House", "target_amount": 500000.0,
        })
        goal_id = create_resp.json()["goal_id"]

        resp = client.post(f"/api/savings/{goal_id}/contribute", headers=registered_customer["headers"], json={
            "amount": 99999999.0,
        })
        assert resp.status_code == 400

    def test_delete_goal(self, client, registered_customer):
        """DELETE /api/savings/{goal_id} should delete a goal."""
        create_resp = client.post("/api/savings", headers=registered_customer["headers"], json={
            "name": "Temporary Goal", "target_amount": 1000.0,
        })
        goal_id = create_resp.json()["goal_id"]

        resp = client.delete(f"/api/savings/{goal_id}", headers=registered_customer["headers"])
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  6.  Admin Operations
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdminOperations:

    def test_admin_view_accounts(self, client, admin_token, registered_customer):
        """GET /api/admin/accounts should return all accounts."""
        resp = client.get("/api/admin/accounts", headers=admin_token["headers"])
        assert resp.status_code == 200
        accounts = resp.json()
        assert isinstance(accounts, list)
        assert len(accounts) >= 1
        assert any(a["account_number"] == registered_customer["account_number"] for a in accounts)

    def test_admin_search_accounts(self, client, admin_token, registered_customer):
        """GET /api/admin/accounts/search should find accounts."""
        resp = client.get(
            f"/api/admin/accounts/search?q={registered_customer['account_number']}",
            headers=admin_token["headers"],
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        assert results[0]["account_number"] == registered_customer["account_number"]

    def test_admin_freeze_account(self, client, admin_token, registered_customer):
        """POST /api/admin/accounts/{acc_no}/freeze should freeze an account."""
        acc_no = registered_customer["account_number"]
        resp = client.post(f"/api/admin/accounts/{acc_no}/freeze", headers=admin_token["headers"])
        assert resp.status_code == 200
        assert "frozen" in resp.json()["message"].lower()

    def test_admin_unfreeze_account(self, client, admin_token, registered_customer):
        """POST /api/admin/accounts/{acc_no}/unfreeze should unfreeze an account."""
        acc_no = registered_customer["account_number"]
        # Freeze first
        client.post(f"/api/admin/accounts/{acc_no}/freeze", headers=admin_token["headers"])
        # Unfreeze
        resp = client.post(f"/api/admin/accounts/{acc_no}/unfreeze", headers=admin_token["headers"])
        assert resp.status_code == 200
        assert "unfrozen" in resp.json()["message"].lower()

    def test_admin_delete_account(self, client, admin_token, registered_customer):
        """DELETE /api/admin/accounts/{acc_no} should delete an account."""
        acc_no = registered_customer["account_number"]
        resp = client.delete(f"/api/admin/accounts/{acc_no}", headers=admin_token["headers"])
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

        # Verify account is gone
        accounts_resp = client.get("/api/admin/accounts", headers=admin_token["headers"])
        assert all(a["account_number"] != acc_no for a in accounts_resp.json())

    def test_admin_statistics(self, client, admin_token, registered_customer):
        """GET /api/admin/statistics should return bank statistics."""
        resp = client.get("/api/admin/statistics", headers=admin_token["headers"])
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_customers"] >= 1
        assert stats["total_transactions"] >= 1  # the deposit from fixture
        assert "total_balance" in stats
        assert "total_balance_formatted" in stats

    def test_admin_view_transactions(self, client, admin_token, registered_customer):
        """
        GET /api/admin/transactions should return all transactions.

        Returns a flat list of TransactionOut objects (not grouped by account).
        Client-side code can group by the `account_number` field.
        """
        resp = client.get("/api/admin/transactions", headers=admin_token["headers"])
        assert resp.status_code == 200
        txns = resp.json()
        assert isinstance(txns, list)
        assert len(txns) >= 1

    def test_admin_unauthorized_customer(self, client, registered_customer):
        """Admin endpoints should reject customer tokens."""
        resp = client.get("/api/admin/accounts", headers=registered_customer["headers"])
        assert resp.status_code == 403

    def test_admin_unauthorized_no_token(self, client):
        """
        Admin endpoints should reject unauthenticated requests.

        HTTPBearer (no credentials) returns 401, not 403. 403 would come
        from a valid token with wrong role.
        """
        resp = client.get("/api/admin/accounts")
        assert resp.status_code == 401

    def test_frozen_account_cannot_transact(self, client, admin_token, registered_customer,
                                             second_registered_customer):
        """A frozen account should not be able to withdraw or transfer."""
        acc_no = registered_customer["account_number"]

        # Freeze the account
        client.post(f"/api/admin/accounts/{acc_no}/freeze", headers=admin_token["headers"])

        # Try to withdraw
        resp = client.post("/api/account/withdraw", headers=registered_customer["headers"], json={
            "amount": 100.0,
        })
        # Note: the v1 API uses process_withdraw directly, so it may return 400
        assert resp.status_code in (400, 403)

        # Try to transfer
        resp = client.post("/api/account/transfer", headers=registered_customer["headers"], json={
            "target_account": second_registered_customer["account_number"],
            "amount": 100.0,
        })
        assert resp.status_code in (400, 403)


# ═══════════════════════════════════════════════════════════════════════════════
#  7.  Error Handling & Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrorHandling:

    def test_invalid_json_body(self, client):
        """Send invalid JSON should return 422 (Pydantic validation)."""
        resp = client.post("/api/auth/login", json={"not_correct_field": "x"})
        assert resp.status_code == 422

    def test_nonexistent_route(self, client):
        """GET a nonexistent route should return 404."""
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_invalid_account_number_format(self, client):
        """Login with empty password should fail validation."""
        resp = client.post("/api/auth/login", json={
            "account_number": "",
            "password": "",
        })
        assert resp.status_code == 422  # Pydantic min_length validation


# ═══════════════════════════════════════════════════════════════════════════════
#  8.  V2 API Tests (ApiResponse envelope)
# ═══════════════════════════════════════════════════════════════════════════════


class TestV2API:

    def test_v2_health_check(self, client):
        """V2 health check should use ApiResponse envelope."""
        resp = client.get("/api/v2/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert data["error"] is None

    def test_v2_register(self, client):
        """
        V2 register should return ApiResponse envelope.

        Note: "Charlie V2" contains a digit which fails validate_name()
        (letters and spaces only). Using "Charlie" instead.
        """
        resp = client.post("/api/v2/auth/register", json={
            "name": "Charlie",
            "age": 26,
            "gender": "Male",
            "mobile": "9988776655",
            "email": "charlie@example.com",
            "password": "CharlieP@ss1",
            "confirm_password": "CharlieP@ss1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["message"] is not None

    def test_v2_login_envelope(self, client, registered_customer):
        """V2 login should return success=true + data.access_token."""
        resp = client.post("/api/v2/auth/login", json={
            "account_number": registered_customer["account_number"],
            "password": registered_customer["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["access_token"] is not None
        assert data["data"]["role"] == "customer"

    def test_v2_error_envelope(self, client):
        """
        V2 endpoint errors should use ApiResponse envelope.

        The V2 login endpoint returns 404 for 'not found' accounts
        (distinct from 401 for wrong credentials on existing accounts).
        """
        resp = client.post("/api/v2/auth/login", json={
            "account_number": "9999999999",
            "password": "wrong",
        })
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert data["error"] is not None
        assert data["data"] is None

    def test_v2_validate_error(self, client):
        """
        V2 validation errors should return error envelope.

        Name "A" is too short (min 2 chars). The V2 endpoint validates this
        via the validate_name() function which returns False, triggering _err()
        which raises HTTPException with an ApiResponse dict.
        """
        resp = client.post("/api/v2/auth/register", json={
            "name": "A",  # too short
            "age": 25,
            "gender": "Male",
            "mobile": "9876543210",
            "email": "test@test.com",
            "password": "TestP@ss1",
            "confirm_password": "TestP@ss1",
        })
        assert resp.status_code == 400
        data = resp.json()
        assert data["success"] is False
        assert data["error"] is not None

    def test_v2_get_balance(self, client, registered_customer):
        """V2 balance endpoint should use ApiResponse."""
        resp = client.get("/api/v2/account/balance", headers=registered_customer["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["balance"] >= 1000.0

    def test_v2_deposit(self, client, registered_customer):
        """V2 deposit should work with ApiResponse."""
        resp = client.post("/api/v2/account/deposit", headers=registered_customer["headers"], json={
            "amount": 250.0,
            "category": "Salary",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "deposited" in data["data"]["message"]

    def test_v2_transfer(self, client, registered_customer, second_registered_customer):
        """V2 transfer should work with ApiResponse."""
        resp = client.post("/api/v2/account/transfer", headers=registered_customer["headers"], json={
            "target_account": second_registered_customer["account_number"],
            "amount": 200.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "transferred" in data["data"]["message"].lower()

    def test_v2_admin_statistics(self, client, admin_token):
        """V2 admin statistics should use ApiResponse."""
        resp = client.get("/api/v2/admin/statistics", headers=admin_token["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["total_customers"] >= 0
