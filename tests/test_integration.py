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
from unionbank.infrastructure.container import get_container, reset_container
from unionbank.domain.entities import Account, TransactionType

# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _fresh_db():
    """
    Set up a fresh SQLite database for each test.

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

    def test_idempotency_repo_create_and_get(self, c):
        """Verify the idempotency repository can create and retrieve records."""
        from unionbank.domain.entities import IdempotencyRecord
        repo = c.idempotency_repo()

        record = IdempotencyRecord(
            idempotency_key="test-key-001",
            account_number="1000000001",
            operation="deposit",
            result_json='{"success": true}',
            amount=Decimal("100.00"),
        )
        repo.create(record)
        repo.commit()

        fetched = repo.get("test-key-001")
        assert fetched is not None
        assert fetched.idempotency_key == "test-key-001"
        assert fetched.operation == "deposit"

    def test_idempotency_deposit_prevents_double_spend(self, c):
        """
        ⭐ IDEMPOTENCY: Depositing twice with the same idempotency_key
        should only move the money once. The second call returns the
        cached result without modifying the balance.
        """
        account = Account(
            account_number="1000000001",
            name="Idempotency Tester",
            balance=Decimal("500.00"),
            password="pw",
        )
        c.account_repo().create(account)
        c.account_repo().commit()

        svc = c.transaction_service()

        # First call: should succeed and credit balance
        result1 = svc.deposit(
            acc_no="1000000001",
            amount=Decimal("100.00"),
            idempotency_key="dep-dup-001",
        )
        assert result1.success
        assert result1.data["balance"] == 600.0  # 500 + 100

        # Second call with the SAME key: should return cached result
        result2 = svc.deposit(
            acc_no="1000000001",
            amount=Decimal("100.00"),
            idempotency_key="dep-dup-001",
        )
        assert result2.success

        # Balance should still be 600, NOT 700
        account = c.account_repo().get("1000000001")
        assert account.balance == Decimal("600.00"), (
            f"Double-spend detected! Balance is {account.balance}, expected 600.00"
        )

    def test_idempotency_withdraw_prevents_double_spend(self, c):
        """
        Withdrawing twice with the same idempotency_key should only
        debit the account once.
        """
        account = Account(
            account_number="1000000001",
            name="Idempotency Tester",
            balance=Decimal("500.00"),
            password="pw",
        )
        c.account_repo().create(account)
        c.account_repo().commit()

        svc = c.transaction_service()

        # First withdraw
        result1 = svc.withdraw(
            acc_no="1000000001",
            amount=Decimal("100.00"),
            idempotency_key="wd-dup-001",
        )
        assert result1.success
        assert result1.data["balance"] == 400.0  # 500 - 100

        # Second withdraw with same key
        result2 = svc.withdraw(
            acc_no="1000000001",
            amount=Decimal("100.00"),
            idempotency_key="wd-dup-001",
        )
        assert result2.success

        account = c.account_repo().get("1000000001")
        assert account.balance == Decimal("400.00"), (
            f"Double-spend detected! Balance is {account.balance}, expected 400.00"
        )

    def test_idempotency_different_keys_both_succeed(self, c):
        """Different idempotency keys should each execute independently."""
        account = Account(
            account_number="1000000001",
            name="Idempotency Tester",
            balance=Decimal("500.00"),
            password="pw",
        )
        c.account_repo().create(account)
        c.account_repo().commit()

        svc = c.transaction_service()

        r1 = svc.deposit("1000000001", Decimal("50"), idempotency_key="key-a")
        r2 = svc.deposit("1000000001", Decimal("75"), idempotency_key="key-b")
        assert r1.success and r2.success

        account = c.account_repo().get("1000000001")
        assert account.balance == Decimal("625.00"), f"Expected 625, got {account.balance}"

    def test_idempotency_without_key_still_works(self, c):
        """
        Backward compatibility: not sending an idempotency_key should
        behave exactly as before (no dedup, no errors).
        """
        account = Account(
            account_number="1000000001",
            name="Back Compat",
            balance=Decimal("100.00"),
            password="pw",
        )
        c.account_repo().create(account)
        c.account_repo().commit()

        svc = c.transaction_service()

        # Without idempotency_key — should work
        r1 = svc.deposit("1000000001", Decimal("50"))
        assert r1.success
        assert r1.data["balance"] == 150.0

        # Same operation again (no key) — should execute again (no dedup)
        r2 = svc.deposit("1000000001", Decimal("50"))
        assert r2.success
        assert r2.data["balance"] == 200.0

    def test_soft_delete_preserves_transactions(self, c):
        """
        ⭐ COMPLIANCE: Soft-deleting an account must preserve transaction history.

        In a banking domain, destroying transaction records on account deletion
        is a compliance violation (record-retention requirements).
        Soft-delete sets deleted_at and hides the account from default queries,
        but transaction history survives for audit and regulatory purposes.
        """
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
        from unionbank.domain.entities import Transaction
        txn = Transaction(
            txn_id="TXN-DELETETEST",
            account_number="1000000001",
            type=TransactionType.DEPOSIT,
            amount=Decimal("50.00"),
            balance=Decimal("150.00"),
        )
        txn_repo.create(txn)
        txn_repo.commit()

        # Soft-delete the account
        repo.delete("1000000001")
        repo.commit()

        # Account should NOT be returned by normal get() (hidden from default queries)
        assert repo.get("1000000001") is None

        # Account SHOULD be recoverable via get_deleted()
        deleted = repo.get_deleted("1000000001")
        assert deleted is not None
        assert deleted.deleted_at is not None
        assert deleted.account_number == "1000000001"

        # ═══ CRITICAL: Transaction history MUST survive ═══
        assert txn_repo.count_by_account("1000000001") == 1, (
            "Transaction history was destroyed! Soft-delete must preserve "
            "transaction records for audit and compliance."
        )

        # Verify we can still read the transaction
        txns = txn_repo.get_by_account("1000000001")
        assert len(txns) == 1
        assert txns[0].txn_id == "TXN-DELETETEST"
        assert txns[0].amount == Decimal("50.00")


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
        """
        If a transfer fails mid-way, NO changes persist.

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
        """
        Freezing an account via AdminService should persist in SQLite.

        Freeze now explicitly also deactivates the account (via AdminService),
        but unfreezing does NOT reactivate it.
        """
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
        # AdminService.freeze_account() explicitly deactivates when freezing
        assert updated.is_active is False

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


    def test_unfreeze_does_not_reactivate_closed_account(self, c):
        """
        ⭐ REGRESSION TEST: Unfreezing must NOT reactivate a closed account.

        This tests the fix for the set_frozen() hidden side-effect.
        Previously, set_frozen(frozen=False) would silently set
        is_active=True, which meant unfreezing a previously-closed
        account would inadvertently reactivate it.

        Scenario:
          1. Create active account
          2. Freeze it → is_frozen=True, is_active=False (explicit deactivation)
          3. Unfreeze it → is_frozen=False, is_active=STILL False
          4. Account should require explicit reactivation
        """
        repo = c.account_repo()
        account = Account(
            account_number="1000000001", name="Freeze Regression",
            balance=Decimal("500.00"), password="pw",
            is_active=True, is_frozen=False,
        )
        repo.create(account)
        repo.commit()

        admin_svc = c.admin_service()

        # Step 1: Freeze (explicitly deactivates)
        freeze_result = admin_svc.freeze_account("1000000001", actor="admin")
        assert freeze_result.success is True
        after_freeze = repo.get("1000000001")
        assert after_freeze.is_frozen is True
        assert after_freeze.is_active is False  # Explicitly deactivated

        # Step 2: Unfreeze (should NOT reactivate)
        unfreeze_result = admin_svc.unfreeze_account("1000000001", actor="admin")
        assert unfreeze_result.success is True
        after_unfreeze = repo.get("1000000001")
        assert after_unfreeze.is_frozen is False  # Unfrozen
        assert after_unfreeze.is_active is False  # ⚠️ STILL inactive — this is correct!

        # Step 3: Account should STILL be unable to transact until explicitly reactivated
        assert after_unfreeze.can_transact is False  # is_active=False prevents transactions

    def test_freeze_closed_account_fails(self, c):
        """Freezing a permanently closed account should fail gracefully."""
        repo = c.account_repo()
        account = Account(
            account_number="1000000001", name="Closed Account",
            balance=Decimal("0.00"), password="pw",
            is_active=False, is_frozen=False,
        )
        repo.create(account)
        repo.commit()

        admin_svc = c.admin_service()
        result = admin_svc.freeze_account("1000000001", actor="admin")
        assert result.success is False
        assert "permanently closed" in result.message.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  Integration: Auth flow via Container
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthFlow:

    def test_register_and_login_flow(self, c):
        """Full auth flow: register → login → verify session data."""
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
        from unionbank.utils.hashing import hash_password
        admin_repo = c.admin_repo()

        # Create admin user directly in DB
        from unionbank.domain.entities import AdminUser
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
#  Integration: Concurrency (no lost updates)
# ═══════════════════════════════════════════════════════════════════════════════


class TestConcurrentTransfers:
    """
    ⭐ Concurrency tests: fire simultaneous transfers and assert no lost updates.

    These are the single most convincing tests in a banking app because they
    directly demonstrate understanding of the domain's hardest problem:
    preventing race conditions on account balances.
    """

    def test_simultaneous_transfers_no_lost_updates(self, c):
        """
        Fire 10 concurrent transfers from one account and verify:
        1. Money is ALWAYS conserved (sender + receiver = initial total)
        2. At least some transfers succeeded

        Under SQLite's WAL mode, writes are serialized. Some concurrent
        transfers may fail due to "database is locked" — this is expected.
        The critical invariant is that NO money is ever lost or created.
        """
        import concurrent.futures

        repo = c.account_repo()
        from unionbank.domain.entities import Account

        INITIAL_BALANCE = Decimal("10000.00")

        sender = Account(
            account_number="1000000001",
            name="Sender",
            balance=INITIAL_BALANCE,
            password="pw",
            is_active=True, is_frozen=False,
        )
        receiver = Account(
            account_number="2000000002",
            name="Receiver",
            balance=Decimal("0.00"),
            password="pw",
            is_active=True, is_frozen=False,
        )
        repo.create(sender)
        repo.create(receiver)
        repo.commit()

        amount = Decimal("100.00")
        num_transfers = 10

        def do_transfer(_):
            """Execute one transfer in its own thread-local session."""
            from unionbank.infrastructure.container import get_container
            local_c = get_container()
            return local_c.transaction_service().transfer(
                sender_acc_no="1000000001",
                receiver_acc_no="2000000002",
                amount=amount,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(do_transfer, i) for i in range(num_transfers)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        successes = sum(1 for r in results if r.success)

        # ═══ CRITICAL INVARIANT: Money is conserved ═══
        updated_sender = repo.get("1000000001")
        updated_receiver = repo.get("2000000002")
        total = updated_sender.balance + updated_receiver.balance
        assert total == INITIAL_BALANCE, (
            f"❌ MONEY NOT CONSERVED! sender={updated_sender.balance} + "
            f"receiver={updated_receiver.balance} = {total}, expected {INITIAL_BALANCE}"
        )

        # Verify the balance is consistent with number of successes
        expected_sender = INITIAL_BALANCE - (amount * successes)
        expected_receiver = amount * successes
        assert updated_sender.balance == expected_sender, (
            f"Sender balance mismatch: got {updated_sender.balance}, "
            f"expected {expected_sender} ({successes}/{num_transfers} succeeded)"
        )
        assert updated_receiver.balance == expected_receiver, (
            f"Receiver balance mismatch: got {updated_receiver.balance}, "
            f"expected {expected_receiver}"
        )

        # At least some transfers must succeed (or the test is meaningless)
        assert successes > 0, (
            f"All {num_transfers} concurrent transfers failed. "
            f"Sample: {next((r.message for r in results if not r.success), 'unknown')}"
        )

    def test_concurrent_deposits_no_lost_updates(self, c):
        """
        Fire 20 concurrent deposits into the same account.
        Under SQLite's WAL mode, some may fail due to locking.
        The critical invariant: final balance = amount × successful_count.
        No money should appear or disappear.
        """
        import concurrent.futures

        repo = c.account_repo()
        from unionbank.domain.entities import Account

        acc = Account(
            account_number="1000000001",
            name="Deposit Target",
            balance=Decimal("0.00"),
            password="pw",
            is_active=True, is_frozen=False,
        )
        repo.create(acc)
        repo.commit()

        amount = Decimal("50.00")
        num_deposits = 20

        def do_deposit(_):
            from unionbank.infrastructure.container import get_container
            local_c = get_container()
            return local_c.transaction_service().deposit(
                acc_no="1000000001",
                amount=amount,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(do_deposit, i) for i in range(num_deposits)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        successes = sum(1 for r in results if r.success)

        updated = repo.get("1000000001")
        expected = amount * successes

        assert updated.balance == expected, (
            f"Deposit race: got {updated.balance}, expected {expected} "
            f"({successes}/{num_deposits} succeeded) — money was lost or created!"
        )

        # At least some deposits must succeed
        assert successes > 0, (
            f"All {num_deposits} concurrent deposits failed. "
            f"Sample: {next((r.message for r in results if not r.success), 'unknown')}"
        )


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
        """
        Verify keyset cursor-based pagination works end-to-end.

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
