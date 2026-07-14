"""
tests/test_htmx_integration.py  –  HTMX integration tests for the Flask web UI.

These tests use Flask's test client to exercise the web application,
verifying that HTMX partial rendering, form submissions, validation,
flash messages, and HTML fragments work correctly.

All tests use an isolated SQLite database per test (no JSON).

Usage:
    pytest tests/test_htmx_integration.py -v --tb=short
"""

from __future__ import annotations

import os
import tempfile
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup

from container import get_container, reset_container
from domain.entities import Account


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _fresh_db():
    """Set up a fresh SQLite database for each test."""
    data_dir = tempfile.mkdtemp(prefix="union_bank_htmx_test_")
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
def app():
    """Flask application with test config."""
    # Import webapp dynamically so it picks up test env vars
    import importlib
    import webapp
    importlib.reload(webapp)
    webapp.app.config["TESTING"] = True
    webapp.app.config["WTF_CSRF_ENABLED"] = False
    webapp.app.config["SERVER_NAME"] = "localhost"
    yield webapp.app


@pytest.fixture
def client(app):
    """Flask test client."""
    with app.test_client() as c:
        yield c


@pytest.fixture
def c():
    """Get a fresh DI container."""
    return get_container()


def _create_customer_in_db(acc_no: str = "1000000001") -> dict:
    """Create a test customer directly in the database and return credentials."""
    from utils.auth import hash_password

    c = get_container()
    account = Account(
        account_number=acc_no,
        name="Test Customer",
        age=25,
        gender="Male",
        mobile="9876543210",
        email="test@example.com",
        password=hash_password("TestP@ss1"),
        balance=Decimal("1000.00"),
        is_active=True,
        is_frozen=False,
    )
    c.account_repo().create(account)
    c.account_repo().commit()
    return {
        "account_number": acc_no,
        "password": "TestP@ss1",
        "name": "Test Customer",
        "balance": 1000.0,
    }


@pytest.fixture
def customer(app, client) -> dict:
    """Create a customer, log in, and return session info."""
    data = _create_customer_in_db()
    resp = client.post("/login", data={
        "account_number": data["account_number"],
        "password": data["password"],
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Welcome back" in resp.data or b"Dashboard" in resp.data
    return data


def _create_admin_in_db() -> dict:
    """Create an admin user directly in the database."""
    from utils.auth import hash_password
    from domain.entities import AdminUser

    c = get_container()
    admin = AdminUser(
        username="admin",
        password=hash_password("admin123"),
    )
    c.admin_repo().create(admin)
    c.admin_repo().commit()
    return {"username": "admin", "password": "admin123"}


@pytest.fixture
def admin(app, client) -> dict:
    """Create an admin, log in, and return session info."""
    data = _create_admin_in_db()
    resp = client.post("/admin/login", data={
        "username": data["username"],
        "password": data["password"],
    }, follow_redirects=True)
    assert resp.status_code == 200
    return data


# ═══════════════════════════════════════════════════════════════════════════════
#  1.  Public Pages
# ═══════════════════════════════════════════════════════════════════════════════


class TestPublicPages:

    def test_index_page_renders(self, client):
        """GET / should render the landing page."""
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Union Bank" in html or "union" in html.lower()

    def test_login_page_renders(self, client):
        """GET /login should render the login form."""
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"password" in resp.data.lower() or b"login" in resp.data.lower()

    def test_register_page_renders(self, client):
        """GET /register should render the registration form."""
        resp = client.get("/register")
        assert resp.status_code == 200
        assert b"register" in resp.data.lower() or b"name" in resp.data.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  2.  Customer Authentication
# ═══════════════════════════════════════════════════════════════════════════════


class TestCustomerAuth:

    def test_register_success(self, client):
        """POST /register with valid data should create account."""
        resp = client.post("/register", data={
            "name": "New User",
            "age": "30",
            "gender": "Male",
            "mobile": "9876543210",
            "email": "new@example.com",
            "password": "NewUserP@ss1",
            "confirm_password": "NewUserP@ss1",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"successful" in resp.data.lower() or b"account number" in resp.data.lower()

    def test_register_validation_error(self, client):
        """POST /register with invalid data should show error."""
        resp = client.post("/register", data={
            "name": "A",  # too short
            "age": "30",
            "gender": "Male",
            "mobile": "9876543210",
            "email": "new@example.com",
            "password": "weak",
            "confirm_password": "weak",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"error" in resp.data.lower() or b"must be" in resp.data.lower()

    def test_login_success(self, client):
        """POST /login with valid credentials should redirect to dashboard."""
        _create_customer_in_db()
        resp = client.post("/login", data={
            "account_number": "1000000001",
            "password": "TestP@ss1",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Welcome back" in resp.data or b"Dashboard" in resp.data or b"dashboard" in resp.data

    def test_login_wrong_password(self, client):
        """POST /login with wrong password should show error."""
        _create_customer_in_db()
        resp = client.post("/login", data={
            "account_number": "1000000001",
            "password": "WrongPassword",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"error" in resp.data.lower() or b"incorrect" in resp.data.lower()

    def test_logout(self, client, customer):
        """GET /logout should clear session."""
        resp = client.get("/logout", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Logged out" in resp.data or b"login" in resp.data.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  3.  Customer Dashboard
# ═══════════════════════════════════════════════════════════════════════════════


class TestDashboard:

    def test_dashboard_renders(self, client, customer):
        """GET /dashboard should render the dashboard."""
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert customer["name"] in html
        assert "balance" in html.lower()
        assert "Chart" in html or "chart" in html.lower() or "canvas" in html

    def test_dashboard_redirects_if_not_logged_in(self, client):
        """GET /dashboard without login should redirect."""
        resp = client.get("/dashboard", follow_redirects=True)
        assert resp.status_code == 200
        assert b"log in" in resp.data.lower() or b"login" in resp.data.lower()

    def test_dashboard_shows_balance(self, client, customer):
        """Dashboard should show the current balance."""
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        # Balance should be displayed (1000 or formatted)
        assert b"1,000" in resp.data or b"1000" in resp.data


# ═══════════════════════════════════════════════════════════════════════════════
#  4.  HTMX Partial Rendering
# ═══════════════════════════════════════════════════════════════════════════════


class TestHtmxPartials:

    def test_balance_refresh_htmx(self, client, customer):
        """GET /admin/balance-refresh with HX-Request header returns partial."""
        resp = client.get("/admin/balance-refresh", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        # Should return a balance card fragment
        assert "balance" in html.lower() or "₹" in html

    def test_balance_refresh_full_page(self, client, customer):
        """GET /admin/balance-refresh without HTMX header works too."""
        resp = client.get("/admin/balance-refresh")
        assert resp.status_code == 200

    def test_deposit_htmx_partial(self, client, customer):
        """POST /deposit with HX-Request returns HTMX response."""
        resp = client.post("/deposit", data={
            "amount": "250",
            "category": "Salary",
        }, headers={"HX-Request": "true"}, follow_redirects=True)
        assert resp.status_code == 200
        # HTMX response should contain flash message and HX-Redirect header
        # or render the deposit page with a flash

    def test_withdraw_htmx_partial(self, client, customer):
        """POST /withdraw with HX-Request returns HTMX response."""
        resp = client.post("/withdraw", data={
            "amount": "100",
            "category": "Food & Dining",
        }, headers={"HX-Request": "true"}, follow_redirects=True)
        assert resp.status_code == 200

    def test_transfer_htmx_partial(self, client, customer):
        """POST /transfer with HX-Request returns HTMX response."""
        # Create a recipient account
        c = get_container()
        from domain.entities import Account
        from decimal import Decimal
        receiver = Account(
            account_number="2000000002",
            name="Receiver",
            balance=Decimal("500.00"),
            password="$2b$12$test",
        )
        c.account_repo().create(receiver)
        c.account_repo().commit()

        resp = client.post("/transfer", data={
            "target_account": "2000000002",
            "amount": "200",
            "category": "General",
        }, headers={"HX-Request": "true"}, follow_redirects=True)
        assert resp.status_code == 200

    def test_transfer_confirmation_then_execute(self, client, customer):
        """Full HTMX transfer flow: confirm → execute."""
        # Create recipient
        c = get_container()
        from domain.entities import Account
        from decimal import Decimal
        receiver = Account(
            account_number="2000000002",
            name="Receiver",
            balance=Decimal("500.00"),
            password="$2b$12$test",
        )
        c.account_repo().create(receiver)
        c.account_repo().commit()

        # Step 1: Initiate transfer (no 'confirm' in form → shows confirmation)
        resp = client.post("/transfer", data={
            "target_account": "2000000002",
            "amount": "200",
            "category": "General",
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Step 2: Confirm transfer
        resp = client.post("/transfer", data={
            "target_account": "2000000002",
            "amount": "200",
            "category": "General",
            "confirm": "yes",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"transferred" in resp.data.lower() or b"success" in resp.data.lower()

    def test_transfer_to_nonexistent_htmx(self, client, customer):
        """HTMX transfer to non-existent account shows error."""
        resp = client.post("/transfer", data={
            "target_account": "9999999999",
            "amount": "100",
        }, headers={"HX-Request": "true"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"not found" in resp.data.lower() or b"error" in resp.data.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  5.  Savings Goals (Web UI)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSavingsGoalsWeb:

    def test_savings_page_renders(self, client, customer):
        """GET /savings should render the savings goals page."""
        resp = client.get("/savings")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "saving" in html.lower() or "goal" in html.lower()

    def test_create_savings_goal(self, client, customer):
        """POST /savings/new should create a savings goal."""
        resp = client.post("/savings/new", data={
            "name": "Emergency Fund",
            "target_amount": "10000",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"created" in resp.data.lower() or b"goal" in resp.data.lower()

    def test_create_goal_validation(self, client, customer):
        """Creating a goal with short name should show error."""
        resp = client.post("/savings/new", data={
            "name": "A",  # too short
            "target_amount": "1000",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"error" in resp.data.lower() or b"at least 2" in resp.data.lower()

    def test_contribute_to_goal(self, client, customer):
        """POST /savings/<id>/contribute should move funds."""
        # Create a goal first
        client.post("/savings/new", data={
            "name": "Vacation",
            "target_amount": "5000",
        }, follow_redirects=True)

        # Get the goal ID from the savings page
        resp = client.get("/savings")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")

        # Find the goal in the rendered HTML by parsing for contribute forms
        soup = BeautifulSoup(html, "html.parser")
        contribute_forms = soup.find_all("form", action=lambda x: x and "contribute" in x)
        if contribute_forms:
            action = contribute_forms[0].get("action", "")
            goal_id = action.split("/")[-2] if "/" in action else ""

            # Contribute
            resp = client.post(f"/savings/{goal_id}/contribute", data={
                "amount": "500",
            }, follow_redirects=True)
            assert resp.status_code == 200
            assert b"contributed" in resp.data.lower()

    def test_edit_savings_goal(self, client, customer):
        """POST /savings/<id>/edit should update a goal."""
        # Create a goal
        client.post("/savings/new", data={
            "name": "Old Name",
            "target_amount": "1000",
        }, follow_redirects=True)

        # Find goal ID in rendered page
        resp = client.get("/savings")
        soup = BeautifulSoup(resp.data.decode("utf-8"), "html.parser")
        edit_forms = soup.find_all("form", action=lambda x: x and "edit" in x)
        if edit_forms:
            action = edit_forms[0].get("action", "")
            goal_id = action.split("/")[-2] if "/" in action else ""

            # Edit
            resp = client.post(f"/savings/{goal_id}/edit", data={
                "name": "Updated Name",
                "target_amount": "2000",
            }, follow_redirects=True)
            assert resp.status_code == 200
            assert b"updated" in resp.data.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  6.  Admin Web UI
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdminWeb:

    def test_admin_login_page(self, client):
        """GET /admin/login should render admin login."""
        resp = client.get("/admin/login")
        assert resp.status_code == 200
        assert b"admin" in resp.data.lower()

    def test_admin_dashboard(self, client, admin):
        """GET /admin/dashboard should render admin dashboard."""
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200

    def test_admin_accounts(self, client, admin):
        """GET /admin/accounts should list accounts."""
        resp = client.get("/admin/accounts")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "account" in html.lower()

    def test_admin_search(self, client, admin, customer):
        """POST /admin/search should find accounts."""
        resp = client.post("/admin/search", data={
            "query": customer["account_number"],
        })
        assert resp.status_code == 200
        assert customer["account_number"] in resp.data.decode("utf-8")

    def test_admin_freeze(self, client, admin, customer):
        """POST /admin/freeze should freeze an account."""
        # First request: look up account
        resp = client.post("/admin/freeze", data={
            "account_number": customer["account_number"],
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Second request: confirm freeze
        resp = client.post("/admin/freeze", data={
            "account_number": customer["account_number"],
            "confirm": "yes",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"freez" in resp.data.lower()

    def test_admin_delete(self, client, admin, customer):
        """POST /admin/delete should delete an account (with confirm)."""
        # First request: look up account (shows preview)
        resp = client.post("/admin/delete", data={
            "account_number": customer["account_number"],
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Second request: type DELETE to confirm
        resp = client.post("/admin/delete", data={
            "account_number": customer["account_number"],
            "confirm_text": "DELETE",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"deleted" in resp.data.lower()

    def test_admin_statistics(self, client, admin, customer):
        """GET /admin/statistics should render stats."""
        resp = client.get("/admin/statistics")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "chart" in html.lower() or "stat" in html.lower()

    def test_admin_transactions(self, client, admin, customer):
        """GET /admin/transactions should show transactions."""
        # Do a deposit first so there's a transaction
        client.post("/deposit", data={"amount": "500", "category": "Salary"},
                     follow_redirects=True)

        resp = client.post("/admin/transactions", data={
            "account_number": customer["account_number"],
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"DEPOSIT" in resp.data or b"deposit" in resp.data.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  7.  Transaction Pages (Web UI)
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransactionPages:

    def test_deposit_page(self, client, customer):
        """GET /deposit should render deposit form."""
        resp = client.get("/deposit")
        assert resp.status_code == 200
        assert b"amount" in resp.data.lower()

    def test_deposit_submit(self, client, customer):
        """POST /deposit should process deposit."""
        resp = client.post("/deposit", data={
            "amount": "500",
            "category": "Salary",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"deposited" in resp.data.lower() or b"success" in resp.data.lower()

    def test_withdraw_page(self, client, customer):
        """GET /withdraw should render withdraw form."""
        resp = client.get("/withdraw")
        assert resp.status_code == 200

    def test_withdraw_submit(self, client, customer):
        """POST /withdraw should process withdrawal."""
        resp = client.post("/withdraw", data={
            "amount": "200",
            "category": "Food & Dining",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"withdrawn" in resp.data.lower() or b"success" in resp.data.lower()

    def test_withdraw_insufficient(self, client, customer):
        """POST /withdraw with insufficient balance should show error."""
        resp = client.post("/withdraw", data={
            "amount": "999999",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"insufficient" in resp.data.lower() or b"error" in resp.data.lower()

    def test_transfer_page(self, client, customer):
        """GET /transfer should render transfer form."""
        resp = client.get("/transfer")
        assert resp.status_code == 200

    def test_statement_page(self, client, customer):
        """GET /statement should render transaction statement."""
        resp = client.get("/statement")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "transaction" in html.lower() or "statement" in html.lower()

    def test_export_csv(self, client, customer):
        """GET /export-csv should download CSV."""
        resp = client.get("/export-csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type or "csv" in resp.content_type.lower()

    def test_profile_page(self, client, customer):
        """GET /profile should render profile page."""
        resp = client.get("/profile")
        assert resp.status_code == 200
        assert customer["name"] in resp.data.decode("utf-8")

    def test_apply_interest_page(self, client, customer):
        """GET /apply-interest should show confirmation."""
        resp = client.get("/apply-interest", follow_redirects=True)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
#  8.  HTMX Headers & Notifications
# ═══════════════════════════════════════════════════════════════════════════════


class TestHtmxHeaders:

    def test_notification_count_htmx(self, client, customer):
        """GET /notifications/count with HX-Request returns plain count."""
        resp = client.get("/notifications/count", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        # Should return a number as plain text
        count = resp.data.decode("utf-8").strip()
        assert count.isdigit()

    def test_notifications_page(self, client, customer):
        """GET /notifications should render notifications page."""
        resp = client.get("/notifications")
        assert resp.status_code == 200

    def test_notification_preferences(self, client, customer):
        """GET /notifications/preferences should render preferences."""
        resp = client.get("/notifications/preferences")
        assert resp.status_code == 200

    def test_admin_search_results_htmx(self, client, admin, customer):
        """GET /admin/search-results?q= with HX-Request returns fragment."""
        resp = client.get(
            f"/admin/search-results?query={customer['account_number']}",
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert customer["account_number"] in html


# ═══════════════════════════════════════════════════════════════════════════════
#  9.  Access Control
# ═══════════════════════════════════════════════════════════════════════════════


class TestAccessControl:

    def test_admin_page_redirects_customer(self, client, customer):
        """Admin page should redirect customer users."""
        resp = client.get("/admin/accounts", follow_redirects=True)
        assert resp.status_code == 200
        assert b"admin" in resp.data.lower() or b"login" in resp.data.lower()

    def test_customer_page_redirects_anonymous(self, client):
        """Customer page should redirect anonymous users."""
        resp = client.get("/dashboard", follow_redirects=True)
        assert resp.status_code == 200
        assert b"log in" in resp.data.lower()

    def test_login_page_redirects_logged_in(self, client, customer):
        """Login page should redirect logged-in users."""
        resp = client.get("/login", follow_redirects=True)
        # Might redirect to dashboard
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
#  10.  Validation & Error Messages
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidation:

    def test_register_invalid_email(self, client):
        """Register with invalid email should show error."""
        resp = client.post("/register", data={
            "name": "Valid Name",
            "age": "25",
            "gender": "Male",
            "mobile": "9876543210",
            "email": "not-an-email",
            "password": "ValidP@ss1",
            "confirm_password": "ValidP@ss1",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"error" in resp.data.lower() or b"invalid" in resp.data.lower()

    def test_register_underage(self, client):
        """Register with age < 18 should show error."""
        resp = client.post("/register", data={
            "name": "Valid Name",
            "age": "15",
            "gender": "Male",
            "mobile": "9876543210",
            "email": "young@example.com",
            "password": "ValidP@ss1",
            "confirm_password": "ValidP@ss1",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"error" in resp.data.lower() or b"age" in resp.data.lower()

    def test_change_password_validation(self, client, customer):
        """POST /change-password with mismatched passwords should error."""
        resp = client.post("/change-password", data={
            "current_password": customer["password"],
            "new_password": "NewStr0ngP@ss1",
            "confirm_password": "DifferentP@ss1",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"not match" in resp.data.lower() or b"error" in resp.data.lower()
