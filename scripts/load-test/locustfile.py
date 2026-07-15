"""
locustfile.py  –  Load test for Union Bank API.

Run with:
    locust -f scripts/load-test/locustfile.py --host=http://localhost:8000

Or headless:
    locust -f scripts/load-test/locustfile.py --host=http://localhost:8000 \\
        --headless --users 10 --spawn-rate 1 --run-time 30s

Requires:
    pip install locust
"""

from __future__ import annotations

import random
from locust import HttpUser, task, between, tag


# Pre-generated test data (valid account numbers from seed data)
TEST_ACCOUNTS = [
    "1111111111",
    "2222222222",
    "3333333333",
    "4444444444",
    "5555555555",
]

TEST_PASSWORD = "Password123!"


class BankUser(HttpUser):
    """Simulates a banking customer performing common operations."""

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    token: str = ""
    refresh_token: str = ""

    def on_start(self):
        """Log in as a test customer."""
        acc_no = random.choice(TEST_ACCOUNTS)
        with self.client.post(
            "/api/auth/login",
            json={"account_number": acc_no, "password": TEST_PASSWORD},
            catch_response=True,
            name="/api/auth/login",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token", "")
                self.refresh_token = data.get("refresh_token", "")
            else:
                resp.failure(f"Login failed: {resp.text}")
                self.token = ""

    @tag("balance")
    @task(5)
    def check_balance(self):
        """Check account balance (high-frequency read)."""
        if not self.token:
            return
        with self.client.get(
            "/api/account/balance",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/account/balance",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Balance check failed: {resp.status_code}")

    @tag("profile")
    @task(3)
    def view_profile(self):
        """View account profile."""
        if not self.token:
            return
        with self.client.get(
            "/api/account/profile",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/account/profile",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Profile view failed: {resp.status_code}")

    @tag("mini_statement")
    @task(4)
    def view_mini_statement(self):
        """View mini statement (last 5 transactions)."""
        if not self.token:
            return
        with self.client.get(
            "/api/account/statements/mini",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/account/statements/mini",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Mini statement failed: {resp.status_code}")

    @tag("full_statement")
    @task(2)
    def view_full_statement(self):
        """View full transaction statement."""
        if not self.token:
            return
        with self.client.get(
            "/api/account/statements",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/account/statements",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Full statement failed: {resp.status_code}")

    @tag("deposit")
    @task(2)
    def deposit(self):
        """Deposit a small amount."""
        if not self.token:
            return
        amount = round(random.uniform(10, 500), 2)
        with self.client.post(
            "/api/account/deposit",
            json={"amount": amount, "category": "General"},
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/account/deposit",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Deposit failed: {resp.status_code}")

    @tag("savings")
    @task(1)
    def list_savings_goals(self):
        """List savings goals."""
        if not self.token:
            return
        with self.client.get(
            "/api/savings",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/savings",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Savings list failed: {resp.status_code}")

    @tag("health")
    @task(1)
    def health_check(self):
        """Health check (unauthenticated)."""
        with self.client.get(
            "/api/health",
            catch_response=True,
            name="/api/health",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check failed: {resp.status_code}")


class AdminUser(HttpUser):
    """Simulates an admin performing management operations."""

    wait_time = between(3, 10)  # Admin ops are less frequent
    token: str = ""

    def on_start(self):
        """Log in as admin."""
        with self.client.post(
            "/api/auth/admin-login",
            json={"username": "simon", "password": "simon123"},
            catch_response=True,
            name="/api/auth/admin-login",
        ) as resp:
            if resp.status_code == 200:
                self.token = resp.json().get("access_token", "")
            elif resp.status_code == 428:
                # TOTP is enabled — skip admin tests
                self.token = ""
                resp.success()
            else:
                resp.failure(f"Admin login failed: {resp.status_code}")
                self.token = ""

    @tag("admin_accounts")
    @task(3)
    def view_accounts(self):
        """View all accounts (paginated)."""
        if not self.token:
            return
        with self.client.get(
            "/api/admin/accounts?page=1&per_page=20",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/admin/accounts",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"View accounts failed: {resp.status_code}")

    @tag("admin_statistics")
    @task(2)
    def view_statistics(self):
        """View bank statistics."""
        if not self.token:
            return
        with self.client.get(
            "/api/admin/statistics",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/admin/statistics",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Statistics failed: {resp.status_code}")

    @tag("admin_transactions")
    @task(2)
    def view_transactions(self):
        """View all transactions (paginated)."""
        if not self.token:
            return
        with self.client.get(
            "/api/admin/transactions?page=1&per_page=50",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
            name="/api/admin/transactions",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"View transactions failed: {resp.status_code}")
