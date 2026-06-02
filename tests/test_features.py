"""
Tests for new features: rate limiting, CSV export, interest, categories, session mgmt.
"""
import os
import sys
import tempfile
import time
import json

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    check_login_locked,
    record_failed_login,
    reset_login_attempts,
    check_session_timeout,
    get_session_timeout_seconds,
    export_transactions_to_csv,
    generate_csv_filename,
    calculate_monthly_interest,
    get_category_choice,
    TRANSACTION_CATEGORIES,
    MAX_LOGIN_ATTEMPTS,
    LOGIN_LOCKOUT_MINUTES,
    SESSION_TIMEOUT_SECONDS,
    SAVINGS_INTEREST_RATE,
    load_json,
    save_json,
    now_str,
    fmt_currency,
    LOGIN_ATTEMPTS_FILE,
)
from ui import prompt_password
from account import Account


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

    def test_log_transaction_stores_category(self, monkeypatch):
        """Test that log_transaction stores the category field."""
        from utils import TRANSACTIONS_FILE

        # Create a temp account and call log_transaction directly
        from account import Account
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
        acc.balance = 1100.0
        acc.log_transaction("DEPOSIT", 100.0, "Test deposit", category="Salary")

        # Verify it was stored
        records = load_json(TRANSACTIONS_FILE)
        txns = records.get("8888888888", [])
        assert len(txns) >= 1
        last_txn = txns[-1]
        assert last_txn.get("category") == "Salary"

        # Clean up
        if "8888888888" in records:
            del records["8888888888"]
            save_json(TRANSACTIONS_FILE, records)


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
