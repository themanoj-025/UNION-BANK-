"""
tests/test_integration.py  –  Integration tests with real SQLite in-memory DB.

These tests use the actual DI container and SQLite (in-memory, via temp file)
to verify that the infrastructure layer, repositories, and services work
correctly together. This catches bugs that in-memory fakes cannot detect
(e.g., SQLAlchemy model mapping errors, constraint violations).

Testcontainers are not needed — the project uses SQLite, so an in-memory
database is the most faithful test environment.
"""

from __future__ import annotations

import os
import tempfile
from decimal import Decimal

import pytest

from domain.entities import Account, TransactionType
from container import get_container, reset_container


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _fresh_db():
    """Set up a fresh SQLite database for each test.

    Uses a temp directory for the database file and resets the DI container
    so each test starts with a clean database.
    """
    # Create a temp directory for this test's database
    data_dir = tempfile.mkdtemp(prefix="union_bank_inttest_")
    old_data_dir = os.environ.get("UNION_BANK_DATA_DIR")
    os.environ["UNION_BANK_DATA_DIR"] = data_dir
    os.environ["UNION_BANK_TESTING"] = "1"

    reset_container()

    yield

    # Cleanup: reset container state
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
def sample_account() -> dict:
    """Return a dict representing a valid account for Account(...) constructor."""
    return {
        "account_number": "1000000001",
        "name": "Integration Tester",
        "age": 30,
        "gender": "Male",
        "mobile": "9876543210",
        "email": "inttest@example.com",
        "password": "$2b$12$test.int.hash.123456789012345678901234567890",
        "balance": 1000.0,
        "is_active": True,
        "is_frozen": False,
        "created_at": "2026-01-01 00:00:00",
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Integration: Account CRUD via Container
# ═══════════════════════════════════════════════════════════════════════════════


class TestAccountCRUD:

    def test_create_and_get_account(self, c):
        """Create an account via the container and verify it persists."""
        account = Account(
            account_number="1000000001",
            name="Test User",
            balance=Decimal("500.00"),
            password="$2b$12$testhash",
        )
        repo = c.account_repo()
        repo.create(account)
        repo.commit()

        fetched = repo.get("1000000001")
        assert fetched is not None
        assert fetched.account_number == "1000000001"
        assert fetched.name == "Test User"
        assert fetched.balance == Decimal("500.00")

    def test_create_and_list_accounts(self, c):
        """List all accounts after creating multiple."""
        repo = c.account_repo()
        repo.create(Account(account_number="1000000001", name="User 1", password="pw"))
        repo.create(Account(account_number="2000000002", name="User 2", password="pw"))
        repo.commit()

        accounts = repo.get_all()
        assert len(accounts) == 2

    def test_delete_account_cascades_to_transactions(self, c):
        """Deleting an account should delete its transactions (ON DELETE CASCADE)."""
        repo = c.account_repo()
        txn_repo = c.transaction_repo()

        account = Account(
            account_number="1000000001",
            name="To Delete",
            balance=Decimal("100.00"),
            password="pw",
        )
        repo.create(account)
        repo.commit()

        # Create a transaction for this account
        from domain.entities import Transaction
        txn = Transaction(
            txn_id="TXN-DELETETEST",
            account_number="1000000001",
            type=TransactionType.DEPOSIT,
            amount=Decimal("50.00"),
            balance=Decimal("150.00"),
        )
        txn_repo.create(txn)
        txn_repo.commit()

        # Delete the account
        repo.delete("1000000001")
        repo.commit()

        # Transaction should also be deleted (CASCADE)
        assert repo.get("1000000001") is None
        assert txn_repo.count_by_account("1000000001") == 0


# ═══════════════════════════════════════════════════════════════════════════════
#  Integration: Transaction flow via Services
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransactionFlow:

    def test_deposit_creates_transaction_record(self, c):
        """Deposit updates account balance AND creates a transaction record."""
        repo = c.account_repo()
        account = Account(
            account_number="1000000001", name="Flow Test",
            balance=Decimal("0.00"), password="pw",
        )
        repo.create(account)
        repo.commit()

        svc = c.transaction_service()
        result = svc.deposit("1000000001", Decimal("250.00"), "Salary")
        assert result.success is True

        # Verify balance updated
        updated = repo.get("1000000001")
        assert updated.balance == Decimal("250.00")

        # Verify transaction record exists
        txns = c.transaction_repo().get_by_account("1000000001")
        assert len(txns) == 1
        assert txns[0].type == TransactionType.DEPOSIT
        assert txns[0].amount == Decimal("250.00")
        assert txns[0].balance == Decimal("250.00")

    def test_full_deposit_withdraw_transfer_flow(self, c):
        """Complete banking flow: deposit → withdraw → transfer → verify all persisted."""
        repo = c.account_repo()
        svc = c.transaction_service()

        # Create accounts
        sender = Account(
            account_number="1000000001", name="Sender",
            balance=Decimal("500.00"), password="pw",
        )
        receiver = Account(
            account_number="2000000002", name="Receiver",
            balance=Decimal("100.00"), password="pw",
        )
        repo.create(sender)
        repo.create(receiver)
        repo.commit()

        # Deposit
        svc.deposit("1000000001", Decimal("300.00"))
        assert repo.get("1000000001").balance == Decimal("800.00")

        # Withdraw
        svc.withdraw("1000000001", Decimal("100.00"))
        assert repo.get("1000000001").balance == Decimal("700.00")

        # Transfer
        svc.transfer("1000000001", "2000000002", Decimal("200.00"))
        assert repo.get("1000000001").balance == Decimal("500.00")
        assert repo.get("2000000002").balance == Decimal("300.00")

        # Verify all transactions recorded
        txns = c.transaction_repo().get_all()
        assert len(txns) == 4  # 1 deposit + 1 withdraw + 2 transfer

    def test_transfer_rollback_on_failure(self, c):
        """If a transfer fails mid-way, NO changes persist.

        The atomic transfer should roll back both the debit and the credit
        if any part of the operation fails.
        """
        repo = c.account_repo()
        svc = c.transaction_service()

        sender = Account(
            account_number="1000000001", name="Sender",
            balance=Decimal("100.00"), password="pw",
        )
        receiver = Account(
            account_number="2000000002", name="Receiver",
            balance=Decimal("50.00"), password="pw",
        )
        repo.create(sender)
        repo.create(receiver)
        repo.commit()

        # Try to transfer more than sender has
        result = svc.transfer("1000000001", "2000000002", Decimal("99999.00"))
        assert result.success is False

        # Both accounts must be unchanged
        assert repo.get("1000000001").balance == Decimal("100.00")
        assert repo.get("2000000002").balance == Decimal("50.00")


# ═══════════════════════════════════════════════════════════════════════════════
#  Integration: Admin operations via Container
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdminOperations:

    def test_freeze_account_via_service(self, c):
        """Freezing an account via AdminService should persist in SQLite."""
        repo = c.account_repo()
        account = Account(
            account_number="1000000001", name="Freeze Target",
            balance=Decimal("1000.00"), password="pw",
            is_active=True, is_frozen=False,
        )
        repo.create(account)
        repo.commit()

        admin_svc = c.admin_service()
        result = admin_svc.freeze_account("1000000001", actor="test_admin")
        assert result.success is True

        updated = repo.get("1000000001")
        assert updated.is_frozen is True
        assert updated.is_active is False  # Frozen implies inactive

    def test_audit_log_persisted(self, c):
        """Admin audit log entries should be persisted in SQLite."""
        repo = c.account_repo()
        account = Account(
            account_number="1000000001", name="Audit Target",
            balance=Decimal("500.00"), password="pw",
        )
        repo.create(account)
        repo.commit()

        admin_svc = c.admin_service()
        admin_svc.freeze_account("1000000001", actor="test_admin",
                                  reason="Testing audit log")

        # Check audit log via the audit_log_repo
        audit_repo = c.audit_log_repo()
        entries = audit_repo.get_by_action("freeze")
        assert len(entries) >= 1
        assert entries[0]["actor"] == "test_admin"
        assert entries[0]["reason"] == "Testing audit log"


# ═══════════════════════════════════════════════════════════════════════════════
#  Integration: Savings Goals via Container
# ═══════════════════════════════════════════════════════════════════════════════


class TestSavingsGoalPersistence:

    def test_create_and_contribute_to_goal(self, c):
        """Create a savings goal, contribute to it, verify everything persisted."""
        repo = c.account_repo()
        goal_repo = c.savings_goal_repo()

        account = Account(
            account_number="1000000001", name="Savery",
            balance=Decimal("1000.00"), password="pw",
        )
        repo.create(account)
        repo.commit()

        # Create a goal via the service
        goal_svc = c.savings_goal_service()
        result = goal_svc.create_goal(
            acc_no="1000000001",
            name="Integration Goal",
            target_amount=Decimal("500.00"),
        )
        assert result.success is True

        # Get the goal from DB
        goals = goal_repo.get_by_account("1000000001")
        assert len(goals) == 1
        goal = goals[0]
        assert goal.name == "Integration Goal"
        assert goal.current_amount == Decimal("0.00")

        # Contribute
        result2 = goal_svc.contribute("1000000001", goal.goal_id, Decimal("200.00"))
        assert result2.success is True

        # Verify goal updated
        updated_goal = goal_repo.get(goal.goal_id)
        assert updated_goal.current_amount == Decimal("200.00")

        # Verify account debited
        assert repo.get("1000000001").balance == Decimal("800.00")

        # Verify transaction created
        txns = c.transaction_repo().get_by_account("1000000001")
        assert any("Savings goal" in t.description for t in txns)


# ═══════════════════════════════════════════════════════════════════════════════
#  Integration: Auth flow via Container
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthFlow:

    def test_register_and_login_flow(self, c):
        """Full auth flow: register → login → verify session data."""
        from utils.auth import hash_password, verify_password

        # Register via auth service
        auth = c.auth_service()
        result = auth.customer_register(
            name="New Customer",
            age=28,
            gender="Female",
            mobile="9123456789",
            email="new@example.com",
            password="MyStr0ngPass!",
        )
        assert result.success is True

        # Login with credentials
        acc_no = result.data["account_number"]
        login_result = auth.customer_login(acc_no, "MyStr0ngPass!")
        assert login_result.success is True
        assert login_result.data["role"] == "customer"

    def test_admin_login(self, c):
        """Admin login via container should work."""
        from utils.auth import hash_password
        admin_repo = c.admin_repo()

        # Create admin user directly in DB
        from domain.entities import AdminUser
        admin = AdminUser(
            username="test_admin",
            password=hash_password("AdminStr0ng!"),
        )
        admin_repo.create(admin)
        admin_repo.commit()

        # Login
        auth = c.auth_service()
        result = auth.admin_login("test_admin", "AdminStr0ng!")
        assert result.success is True
        assert result.data["role"] == "admin"


# ═══════════════════════════════════════════════════════════════════════════════
#  Integration: Pagination and Filtering
# ═══════════════════════════════════════════════════════════════════════════════


class TestPagination:

    def test_paginated_transactions(self, c):
        """Verify offset-based pagination works correctly via the real SQLite DB."""
        repo = c.account_repo()
        svc = c.transaction_service()

        account = Account(
            account_number="1000000001", name="Page Test",
            balance=Decimal("0.00"), password="pw",
        )
        repo.create(account)
        repo.commit()

        # Create 25 deposits
        for i in range(25):
            svc.deposit("1000000001", Decimal("100.00"))

        # Page 1: 20 items
        page1, total = svc.get_paginated_transactions(
            acc_no="1000000001", page=1, per_page=20
        )
        assert len(page1) == 20
        assert total == 25

        # Page 2: 5 items
        page2, _ = svc.get_paginated_transactions(
            acc_no="1000000001", page=2, per_page=20
        )
        assert len(page2) == 5

    def test_keyset_pagination_roundtrip(self, c):
        """Verify keyset cursor-based pagination works end-to-end.

        Creates 15 transactions and pages through them with limit=5,
        verifying that has_more is correct and the cursor advances properly.
        """
        repo = c.account_repo()
        svc = c.transaction_service()

        account = Account(
            account_number="1000000001", name="Keyset Test",
            balance=Decimal("0.00"), password="pw",
        )
        repo.create(account)
        repo.commit()

        # Create 15 deposits (timestamps will be slightly different due to DB precision)
        for i in range(15):
            svc.deposit("1000000001", Decimal("50.00"))

        # Page 1: should get 5 items, has_more=True
        page1 = svc.get_paginated_keyset(
            acc_no="1000000001", limit=5
        )
        assert len(page1.items) == 5
        assert page1.has_more is True
        assert page1.cursor is not None
        assert page1.cursor_key == "timestamp"

        # Page 2: should get 5 items, has_more=True
        page2 = svc.get_paginated_keyset(
            acc_no="1000000001", limit=5, cursor=page1.cursor
        )
        assert len(page2.items) == 5
        assert page2.has_more is True

        # Page 3: should get 5 items, has_more=False
        page3 = svc.get_paginated_keyset(
            acc_no="1000000001", limit=5, cursor=page2.cursor
        )
        assert len(page3.items) == 5
        assert page3.has_more is False

        # Page 4: should get 0 items
        page4 = svc.get_paginated_keyset(
            acc_no="1000000001", limit=5, cursor=page3.cursor
        )
        assert len(page4.items) == 0
        assert page4.has_more is False

        # Items should be in reverse chronological order (most recent first)
        timestamps = [t.timestamp for t in page1.items]
        for i in range(1, len(timestamps)):
            assert timestamps[i - 1] >= timestamps[i] or timestamps[i] is None
