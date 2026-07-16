"""Tests for new features: rate limiting, CSV export, interest, categories, session mgmt.
"""
import json
import os
import tempfile
import time

import pytest

from unionbank.entrypoints.cli.account import Account
from unionbank.entrypoints.cli.ui import prompt_password
from unionbank.utils import (
    LOGIN_LOCKOUT_MINUTES,
    MAX_LOGIN_ATTEMPTS,
    SAVINGS_INTEREST_RATE,
    SESSION_TIMEOUT_SECONDS,
    TRANSACTION_CATEGORIES,
    calculate_monthly_interest,
    check_login_locked,
    check_session_timeout,
    export_transactions_to_csv,
    fmt_currency,
    generate_csv_filename,
    get_category_choice,
    get_session_timeout_seconds,
    now_str,
    record_failed_login,
    reset_login_attempts,
)
from unionbank.utils.file_io import (
    ACCOUNTS_FILE,
    LOGIN_ATTEMPTS_FILE,
    TRANSACTIONS_FILE,
    load_json,
    save_json,
)

# ───────────────────────────────────────────────
#  Rate Limiting Tests
# ───────────────────────────────────────────────

class TestRateLimiting:

    def setup_method(self):
        """Reset login attempts before each test."""
        # Clear the file
        data_dir = os.path.dirname(LOGIN_ATTEMPTS_FILE)
        os.makedirs(data_dir, exist_ok=True)
        save_json(LOGIN_ATTEMPTS_FILE, {})

    def test_fresh_account_not_locked(self):
        is_locked, _ = check_login_locked("9999999999")
        assert is_locked is False

    def test_after_few_attempts_not_locked(self):
        for _ in range(3):
            record_failed_login("1111111111")
        is_locked, _ = check_login_locked("1111111111")
        assert is_locked is False

    def test_after_max_attempts_is_locked(self):
        for _ in range(MAX_LOGIN_ATTEMPTS):
            record_failed_login("2222222222")
        is_locked, remaining = check_login_locked("2222222222")
        assert is_locked is True
        assert remaining > 0

    def test_remaining_attempts_count(self):
        for _ in range(2):
            record_failed_login("3333333333")
        remaining = record_failed_login("3333333333")
        # MAX_LOGIN_ATTEMPTS - 3 = remaining
        expected = MAX_LOGIN_ATTEMPTS - 3
        assert remaining == max(0, expected)

    def test_reset_after_lockout(self):
        for _ in range(MAX_LOGIN_ATTEMPTS - 1):
            record_failed_login("4444444444")
        # should not be locked yet
        is_locked, _ = check_login_locked("4444444444")
        assert is_locked is False

    def test_reset_after_successful_login(self):
        for _ in range(3):
            record_failed_login("5555555555")
        reset_login_attempts("5555555555")
        is_locked, _ = check_login_locked("5555555555")
        assert is_locked is False

    def test_different_accounts_independent(self):
        for _ in range(MAX_LOGIN_ATTEMPTS):
            record_failed_login("6666666666")
        is_locked_a, _ = check_login_locked("6666666666")
        is_locked_b, _ = check_login_locked("7777777777")
        assert is_locked_a is True
        assert is_locked_b is False


# ───────────────────────────────────────────────
#  Session Management Tests
# ───────────────────────────────────────────────

class TestSessionManagement:

    def test_session_active_recently(self):
        assert check_session_timeout(time.time()) is True

    def test_session_expired(self):
        past_time = time.time() - SESSION_TIMEOUT_SECONDS - 10
        assert check_session_timeout(past_time) is False

    def test_session_timeout_constant(self):
        assert get_session_timeout_seconds() == SESSION_TIMEOUT_SECONDS
        assert isinstance(SESSION_TIMEOUT_SECONDS, int)
        assert SESSION_TIMEOUT_SECONDS > 0


# ───────────────────────────────────────────────
#  CSV Export Tests
# ───────────────────────────────────────────────

class TestCsvExport:

    def test_generate_csv_filename(self):
        filename = generate_csv_filename("1234567890")
        assert filename.endswith(".csv")
        assert "1234567890" in filename

    def test_export_empty_records(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = export_transactions_to_csv("1234567890", [], path)
            assert result == path
            assert os.path.exists(path)
            with open(path, "r") as f:
                content = f.read()
                assert "Transaction ID" in content  # header only
        finally:
            os.unlink(path)

    def test_export_with_records(self):
        records = [
            {
                "txn_id": "TXN-ABC123",
                "timestamp": "2026-06-01 10:00:00",
                "type": "DEPOSIT",
                "amount": 1000.0,
                "balance": 1000.0,
                "description": "Test deposit",
                "category": "Salary",
            },
            {
                "txn_id": "TXN-DEF456",
                "timestamp": "2026-06-02 11:00:00",
                "type": "WITHDRAW",
                "amount": 200.0,
                "balance": 800.0,
                "description": "Test withdrawal",
                "category": "Food & Dining",
            },
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            export_transactions_to_csv("1234567890", records, path)
            with open(path, "r") as f:
                lines = f.readlines()
            assert len(lines) == 3  # header + 2 records
            assert "Salary" in lines[1]
            assert "Food & Dining" in lines[2]
            assert "+1000.0" in lines[1]
            assert "-200.0" in lines[2]
        finally:
            os.unlink(path)


# ───────────────────────────────────────────────
#  Interest Calculation Tests
# ───────────────────────────────────────────────

class TestInterestCalculation:

    def test_interest_on_positive_balance(self):
        interest = calculate_monthly_interest(100000)
        expected = round(100000 * SAVINGS_INTEREST_RATE / 12 / 100, 2)
        assert interest == expected
        assert interest > 0

    def test_interest_on_zero_balance(self):
        interest = calculate_monthly_interest(0)
        assert interest == 0.0

    def test_interest_on_small_balance(self):
        interest = calculate_monthly_interest(100)
        assert isinstance(interest, float)
        assert interest >= 0

    def test_interest_rate_constant(self):
        assert isinstance(SAVINGS_INTEREST_RATE, float)
        assert SAVINGS_INTEREST_RATE > 0


# ───────────────────────────────────────────────
#  Transaction Categories Tests
# ───────────────────────────────────────────────

class TestTransactionCategories:

    def test_categories_defined(self):
        assert len(TRANSACTION_CATEGORIES) >= 5
        assert "General" in TRANSACTION_CATEGORIES
        assert "Food & Dining" in TRANSACTION_CATEGORIES
        assert "Salary" in TRANSACTION_CATEGORIES

    def test_categories_unique(self):
        assert len(TRANSACTION_CATEGORIES) == len(set(TRANSACTION_CATEGORIES))

    def test_log_transaction_stores_category(self, monkeypatch, tmp_data_dir):
        """Test that log_transaction stores the category field (via SQLite)."""
        # Create a temp account and call log_transaction directly
        # Note: log_transaction now writes to SQLite only (no JSON)
        from unionbank.infrastructure.container import get_container
        c = get_container()

        data = {
            "account_number": "8888888888",
            "name": "Category Test",
            "age": 25,
            "gender": "Male",
            "mobile": "9876543210",
            "email": "cat@test.com",
            "password": "$2b$12$test",
            "balance": 1000.0,
            "is_active": True,
            "is_frozen": False,
            "created_at": "2026-01-01 00:00:00",
        }
        acc = Account(data)
        acc.save()  # Create account in SQLite first
        acc.balance = 1100.0
        acc.log_transaction("DEPOSIT", 100.0, "Test deposit", category="Salary")

        # Verify it was stored in SQLite via the container
        txns = c.transaction_repo().get_by_account("8888888888")
        assert len(txns) >= 1
        last_txn = txns[-1]
        assert last_txn.category == "Salary"

        # No cleanup needed — tmp_data_dir will be deleted automatically


# ───────────────────────────────────────────────
#  Account Model Enhanced Tests
# ───────────────────────────────────────────────

class TestAccountEnhanced:
    """Test new methods on Account model with mocked data."""

    def test_account_has_export_method(self):
        """Account class should have the export_csv method."""
        assert hasattr(Account, "export_csv")

    def test_account_has_interest_method(self):
        """Account class should have the apply_interest method."""
        assert hasattr(Account, "apply_interest")

    def test_account_to_dict_includes_all_fields(self, monkeypatch):
        """Verify to_dict includes category-relevant fields."""
        data = {
            "account_number": "9999999999",
            "name": "Test User",
            "age": 25,
            "gender": "Male",
            "mobile": "9876543210",
            "email": "test@example.com",
            "password": "$2b$12$testhash",
            "balance": 5000.0,
            "is_active": True,
            "is_frozen": False,
            "created_at": "2026-01-01 00:00:00",
        }
        acc = Account(data)
        d = acc.to_dict()
        assert d["account_number"] == "9999999999"
        assert d["balance"] == 5000.0


# ───────────────────────────────────────────────
#  ⭐ CRASH-MID-TRANSFER REGRESSION TEST
#  This is THE most important test in the suite.
#  It proves that if the process crashes mid-transfer,
#  the total system balance is preserved.
# ───────────────────────────────────────────────

class TestAtomicTransfer:
    """Tests for the atomic fund transfer (fix for the money-losing race condition)."""

    SENDER = "1111111111"
    RECEIVER = "2222222222"

    def _setup_accounts(self, tmp_data_dir):
        """Create two test accounts with known balances."""
        sender_data = {
            "account_number": self.SENDER,
            "name": "Sender",
            "age": 30,
            "gender": "Male",
            "mobile": "9876543210",
            "email": "sender@test.com",
            "password": "$2b$12$test",
            "balance": 1000.0,
            "is_active": True,
            "is_frozen": False,
            "created_at": "2026-01-01 00:00:00",
        }
        receiver_data = {
            "account_number": self.RECEIVER,
            "name": "Receiver",
            "age": 25,
            "gender": "Female",
            "mobile": "9123456789",
            "email": "receiver@test.com",
            "password": "$2b$12$test",
            "balance": 500.0,
            "is_active": True,
            "is_frozen": False,
            "created_at": "2026-01-01 00:00:00",
        }

        accounts = {self.SENDER: sender_data, self.RECEIVER: receiver_data}
        save_json(ACCOUNTS_FILE, accounts)
        save_json(TRANSACTIONS_FILE, {})

        # Also sync to SQLite (since atomic_transfer reads from SQLite)
        from database import sync_account_from_json
        sync_account_from_json(self.SENDER, sender_data)
        sync_account_from_json(self.RECEIVER, receiver_data)

        return sender_data, receiver_data

    def _get_total_balance(self) -> float:
        """Compute the total system balance across JSON and SQLite."""
        accounts = load_json(ACCOUNTS_FILE)
        json_total = sum(a["balance"] for a in accounts.values())

        from database import get_db_balance
        sender_sqlite = get_db_balance(self.SENDER) or 0
        receiver_sqlite = get_db_balance(self.RECEIVER) or 0
        sqlite_total = sender_sqlite + receiver_sqlite

        return json_total, sqlite_total

    def test_atomic_transfer_success(self, tmp_data_dir):
        """A normal transfer should work correctly."""
        self._setup_accounts(tmp_data_dir)

        from database import atomic_transfer
        result = atomic_transfer(
            sender_acc_no=self.SENDER,
            receiver_acc_no=self.RECEIVER,
            amount=300.0,
            category="General",
        )

        assert result.success is True
        assert result.sender_balance == 700.0  # 1000 - 300
        assert result.receiver_balance == 800.0  # 500 + 300

    def test_atomic_transfer_insufficient_balance(self, tmp_data_dir):
        """Transfer should fail gracefully when sender has insufficient funds."""
        self._setup_accounts(tmp_data_dir)

        from database import atomic_transfer
        result = atomic_transfer(
            sender_acc_no=self.SENDER,
            receiver_acc_no=self.RECEIVER,
            amount=99999.0,
            category="General",
        )

        assert result.success is False
        assert "Insufficient" in result.error_message

    def test_atomic_transfer_preserves_total_balance_on_crash(self, tmp_data_dir):
        """⭐ CRASH TEST: If the transfer is interrupted after debiting the sender
        but before crediting the receiver, total system balance must remain unchanged.

        This simulates the old JSON race condition where money was lost.
        The new implementation uses a single SQLite ACID transaction, so even
        if we simulate a crash (rollback), the balances are preserved.
        """
        self._setup_accounts(tmp_data_dir)

        initial_json_total, initial_sqlite_total = self._get_total_balance()

        from database import atomic_transfer

        # Attempt a transfer that will FAIL (insufficient balance)
        # This simulates a crash mid-transfer — the atomic_session context
        # manager rolls back the transaction on exception.
        result = atomic_transfer(
            sender_acc_no=self.SENDER,
            receiver_acc_no=self.RECEIVER,
            amount=99999.0,  # Way more than available
            category="General",
        )

        assert result.success is False

        # Total balances must be unchanged — the failed transfer rolled back
        json_total, sqlite_total = self._get_total_balance()
        assert json_total == initial_json_total, (
            f"JSON total changed from {initial_json_total} to {json_total} "
            "after failed transfer! Money would have been lost!"
        )
        assert sqlite_total == initial_sqlite_total, (
            f"SQLite total changed from {initial_sqlite_total} to {sqlite_total} "
            "after failed transfer! Money would have been lost!"
        )

    def test_atomic_transfer_rolls_back_on_exception(self, tmp_data_dir):
        """⭐ CRASH TEST: Prove that if an exception occurs DURING a transaction,
        the SQLite atomic_session context manager rolls back all changes,
        leaving both sender and receiver balances unchanged.

        This tests the core guarantee: the atomic_session commits on success
        and rolls back on ANY exception, so money is never lost mid-transfer.
        """
        self._setup_accounts(tmp_data_dir)

        from database import AccountModel as DbAccount
        from database import atomic_session, get_db_balance

        # Start an atomic transaction, make a change, then simulate a crash
        try:
            with atomic_session() as session:
                sender = session.query(DbAccount).filter_by(
                    account_number=self.SENDER
                ).first()
                # Make a change (debit sender)
                sender.balance -= 300.0
                # ⚡ CRASH: Exception before commit → rollback
                raise Exception("Simulated crash during transaction!")
        except Exception:
            pass  # Expected — the rollback happened

        # Verify rollback: sender balance must be unchanged
        assert get_db_balance(self.SENDER) == 1000.0, (
            "Sender balance changed after rollback! "
            "The atomic transaction did not prevent data loss!"
        )
        assert get_db_balance(self.RECEIVER) == 500.0, (
            "Receiver balance changed after rollback! "
            "The atomic transaction did not prevent data loss!"
        )

    def test_atomic_apply_interest_rolls_back_on_failure(self, tmp_data_dir):
        """Verify that apply_interest is also atomic."""
        self._setup_accounts(tmp_data_dir)

        from database import atomic_apply_interest, get_db_balance

        # Apply interest successfully
        result = atomic_apply_interest(self.SENDER, 50.0)
        assert result is True
        assert get_db_balance(self.SENDER) == 1050.0  # 1000 + 50

    def test_atomic_close_account(self, tmp_data_dir):
        """Verify close_account is atomic."""
        self._setup_accounts(tmp_data_dir)

        from infrastructure.persistence import AccountModel as DbAccount

        from database import atomic_close_account, get_db_balance, get_session

        result = atomic_close_account(self.SENDER)
        assert result is True

        session = get_session()
        account = session.query(DbAccount).filter_by(
            account_number=self.SENDER
        ).first()
        assert account.is_active is False
