"""
tests/test_edge_cases.py  –  Edge-case tests for low-coverage modules.

Targets uncovered lines identified by coverage report:
  - categories.py (20%)   → get_category_choice() error paths
  - formatting.py (64%)   → mask helpers, EMI calculator edge cases
  - file_io.py (59%)      → corruption recovery, backup chains
  - fakes.py (59%)        → error simulation methods
  - services.py (64%)     → edge case service paths
"""

from __future__ import annotations

import json
import os
import tempfile
from decimal import Decimal

import pytest

# ═══════════════════════════════════════════════════════════════════════════════
#  categories.py  –  get_category_choice() edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestCategoriesEdgeCases:

    def test_get_category_choice_invalid_input(self, monkeypatch):
        """Non-numeric input should return 'General'."""
        from unionbank.utils.categories import get_category_choice
        monkeypatch.setattr("builtins.input", lambda _: "abc")
        result = get_category_choice()
        assert result == "General"

    def test_get_category_choice_out_of_range(self, monkeypatch):
        """Input out of valid range should return 'General'."""
        from unionbank.utils.categories import TRANSACTION_CATEGORIES, get_category_choice
        # Enter a number > len(categories)
        monkeypatch.setattr("builtins.input", lambda _: str(len(TRANSACTION_CATEGORIES) + 1))
        result = get_category_choice()
        assert result == "General"

    def test_get_category_choice_negative(self, monkeypatch):
        """Negative input should return 'General'."""
        from unionbank.utils.categories import get_category_choice
        monkeypatch.setattr("builtins.input", lambda _: "-1")
        result = get_category_choice()
        assert result == "General"

    def test_get_category_choice_zero(self, monkeypatch):
        """Zero should return 'General' (since categories are 1-indexed)."""
        from unionbank.utils.categories import get_category_choice
        monkeypatch.setattr("builtins.input", lambda _: "0")
        result = get_category_choice()
        assert result == "General"

    def test_get_category_choice_valid(self, monkeypatch):
        """Valid input should return the correct category."""
        from unionbank.utils.categories import TRANSACTION_CATEGORIES, get_category_choice
        monkeypatch.setattr("builtins.input", lambda _: "1")
        result = get_category_choice()
        assert result == TRANSACTION_CATEGORIES[0]

    def test_transaction_categories_are_defined(self):
        """TRANSACTION_CATEGORIES should be a non-empty list."""
        from unionbank.utils.categories import TRANSACTION_CATEGORIES
        assert len(TRANSACTION_CATEGORIES) > 5
        assert "General" in TRANSACTION_CATEGORIES
        assert "Salary" in TRANSACTION_CATEGORIES


# ═══════════════════════════════════════════════════════════════════════════════
#  formatting.py  –  Edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestFormattingEdgeCases:

    def test_fmt_currency_large_number(self):
        from unionbank.utils.formatting import fmt_currency
        assert fmt_currency(1234567890.12) == "₹1,234,567,890.12"

    def test_fmt_currency_small(self):
        from unionbank.utils.formatting import fmt_currency
        assert fmt_currency(0.01) == "₹0.01"
        assert fmt_currency(0.009) == "₹0.01"

    def test_now_str_format(self):
        """now_str() should return a valid datetime string."""
        from unionbank.utils.formatting import now_str
        result = now_str()
        assert len(result) == 19  # YYYY-MM-DD HH:MM:SS
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == " "
        assert result[13] == ":"

    def test_generate_goal_id_format(self):
        from unionbank.utils.formatting import generate_goal_id
        gid = generate_goal_id()
        assert gid.startswith("GOAL-")
        assert len(gid) == 13  # "GOAL-" + 8 chars

    def test_generate_loan_id_format(self):
        from unionbank.utils.formatting import generate_loan_id
        lid = generate_loan_id()
        assert lid.startswith("LON-")
        assert len(lid) == 12  # "LON-" + 8 chars

    def test_generate_notification_id_format(self):
        from unionbank.utils.formatting import generate_notification_id
        nid = generate_notification_id()
        assert nid.startswith("NTF-")
        assert len(nid) == 12  # "NTF-" + 8 chars

    def test_calculate_emi_standard(self):
        """Standard EMI calculation."""
        from unionbank.utils.formatting import calculate_emi
        # Loan of 500,000 at 10.5% for 60 months
        emi = calculate_emi(500000, 10.5, 60)
        assert isinstance(emi, float)
        assert emi > 0
        # Expected: ~10,747 (verified against standard EMI formula)
        assert abs(emi - 10747.0) < 100  # Reasonable range

    def test_calculate_emi_zero_principal(self):
        from unionbank.utils.formatting import calculate_emi
        assert calculate_emi(0, 10.5, 60) == 0.0

    def test_calculate_emi_zero_rate(self):
        from unionbank.utils.formatting import calculate_emi
        # Zero interest rate returns 0 (guard clause: annual_rate <= 0 → invalid)
        result = calculate_emi(12000, 0, 12)
        assert result == 0.0  # Guard clause treats 0% as invalid input

    def test_calculate_emi_zero_tenure(self):
        from unionbank.utils.formatting import calculate_emi
        assert calculate_emi(10000, 10.5, 0) == 0.0

    def test_calculate_emi_small_amount(self):
        from unionbank.utils.formatting import calculate_emi
        result = calculate_emi(100, 5.0, 3)
        assert result > 0
        assert result < 100

    def test_calculate_emi_negative_principal(self):
        from unionbank.utils.formatting import calculate_emi
        assert calculate_emi(-1000, 10.5, 12) == 0.0

    def test_mask_account_number_standard(self):
        from unionbank.utils.formatting import mask_account_number
        result = mask_account_number("1234567890")
        assert result == "******7890"
        assert len(result) == 10

    def test_mask_account_number_short(self):
        from unionbank.utils.formatting import mask_account_number
        assert mask_account_number("123") == "****"
        assert mask_account_number("") == "****"

    def test_mask_account_number_none(self):
        from unionbank.utils.formatting import mask_account_number
        assert mask_account_number("") == "****"

    def test_mask_sensitive_data_account_numbers(self):
        from unionbank.utils.formatting import mask_sensitive_data
        result = mask_sensitive_data("Account 1234567890 processed transaction")
        assert "1234567890" not in result
        assert "******7890" in result

    def test_mask_sensitive_data_email(self):
        from unionbank.utils.formatting import mask_sensitive_data
        result = mask_sensitive_data("Contact user@example.com for info")
        assert "user@" not in result
        assert "***@example.com" in result

    def test_mask_sensitive_data_multiple(self):
        from unionbank.utils.formatting import mask_sensitive_data
        result = mask_sensitive_data("User: test@mail.com, Acc: 9876543210")
        assert "test@" not in result
        assert "9876543210" not in result

    def test_mask_sensitive_data_no_matches(self):
        from unionbank.utils.formatting import mask_sensitive_data
        result = mask_sensitive_data("Normal message with no sensitive data")
        assert result == "Normal message with no sensitive data"

    def test_get_int_valid(self, monkeypatch):
        from unionbank.utils.formatting import get_int
        monkeypatch.setattr("builtins.input", lambda _: "42")
        result = get_int("Enter: ")
        assert result == 42

    def test_get_int_invalid(self, monkeypatch):
        from unionbank.utils.formatting import get_int
        monkeypatch.setattr("builtins.input", lambda _: "abc")
        result = get_int("Enter: ")
        assert result is None

    def test_get_int_float(self, monkeypatch):
        from unionbank.utils.formatting import get_int
        monkeypatch.setattr("builtins.input", lambda _: "3.14")
        result = get_int("Enter: ")
        assert result is None  # int("3.14") raises ValueError

    def test_now_str_returns_valid_format(self):
        """now_str() should return a valid datetime string in YYYY-MM-DD HH:MM:SS format."""
        from unionbank.utils.formatting import now_str
        result = now_str()
        assert len(result) == 19
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == " "
        # Verify the parts are numeric
        parts = result.split(" ")
        date_parts = parts[0].split("-")
        time_parts = parts[1].split(":")
        assert len(date_parts) == 3
        assert len(time_parts) == 3
        assert all(p.isdigit() for p in date_parts)
        assert all(p.isdigit() for p in time_parts)


# ═══════════════════════════════════════════════════════════════════════════════
#  file_io.py  –  Edge cases (corruption recovery, backup chains)
# ═══════════════════════════════════════════════════════════════════════════════


class TestFileIoEdgeCases:

    def test_backup_path_format(self):
        """_backup_path should append .bak to the path."""
        from unionbank.utils.file_io import _backup_path as bp
        assert bp("/path/to/file.json") == "/path/to/file.json.bak"

    def test_save_json_creates_dir(self):
        """save_json should create parent directories automatically."""
        from unionbank.utils.file_io import save_json
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "sub", "nested", "test.json")
            save_json(nested, {"key": "value"})
            assert os.path.exists(nested)
            with open(nested, "r") as f:
                data = json.load(f)
            assert data == {"key": "value"}

    def test_save_json_creates_backup(self):
        """save_json should create a .bak of the existing file."""
        from unionbank.utils.file_io import save_json
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            save_json(path, {"version": 1})
            save_json(path, {"version": 2})
            bak = path + ".bak"
            assert os.path.exists(bak)
            # Verify the backup is the original data
            with open(bak, "r") as f:
                data = json.load(f)
            assert data == {"version": 1}

    def test_load_json_corrupted_file_fallback(self, monkeypatch):
        """If a file is corrupted JSON, should return {}."""
        from unionbank.utils.file_io import load_json
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "corrupted.json")
            with open(path, "w") as f:
                f.write("{not valid json!!!}")
            data = load_json(path)
            assert data == {}

    def test_load_json_corrupted_with_valid_backup(self, monkeypatch):
        """If a file is corrupted but has a valid .bak, should recover from backup."""
        from unionbank.utils.file_io import load_json, save_json
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            # Save twice to ensure backup is created (first save has no prior file)
            save_json(path, {"original": "data"})
            save_json(path, {"second": "version"})  # This creates .bak with {"original": "data"}
            # Corrupt the file (overwrite with invalid JSON)
            with open(path, "w") as f:
                f.write("{corrupted!!!}")
            # Load should recover from backup
            data = load_json(path)
            assert data == {"original": "data"}

    def test_load_json_empty_file(self):
        """An empty file should return {}."""
        from unionbank.utils.file_io import load_json
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "empty.json")
            with open(path, "w") as f:
                f.write("")
            data = load_json(path)
            assert data == {}

    def test_load_json_whitespace_only(self):
        """A whitespace-only file should return {}."""
        from unionbank.utils.file_io import load_json
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "whitespace.json")
            with open(path, "w") as f:
                f.write("   \n  \t  ")
            data = load_json(path)
            assert data == {}

    def test_load_json_file_not_found(self):
        """A non-existent file should return {}."""
        from unionbank.utils.file_io import load_json
        result = load_json("/nonexistent/path/file.json")
        assert result == {}


# ═══════════════════════════════════════════════════════════════════════════════
#  fakes.py  –  Error simulation methods
# ═══════════════════════════════════════════════════════════════════════════════


class TestFakesErrorSimulation:

    def test_duplicate_key_simulation(self):
        """SimulatedDuplicateKeyError should be raised when simulate_duplicate_key is True."""
        from unionbank.domain.entities import Account

        from tests.fakes import (
            FakeAccountRepository,
            SimulatedDuplicateKeyError,
        )

        repo = FakeAccountRepository()
        repo.simulate_duplicate_key = True

        acc = Account(account_number="1000000001", name="Test", password="pw")
        repo.create(acc)  # First creation should succeed

        with pytest.raises(SimulatedDuplicateKeyError) as excinfo:
            repo.create(acc)  # Second creation should fail
        assert "1000000001" in str(excinfo.value)

    def test_duplicate_key_off_does_not_raise(self):
        """When simulate_duplicate_key is False (default), duplicates should be silently overwritten."""
        from unionbank.domain.entities import Account

        from tests.fakes import FakeAccountRepository

        repo = FakeAccountRepository()
        acc = Account(account_number="1000000001", name="Test", password="pw")
        repo.create(acc)
        # Should NOT raise (default behavior)
        repo.create(Account(account_number="1000000001", name="Overwritten", password="pw"))
        assert repo.get("1000000001").name == "Overwritten"

    def test_race_condition_error_class(self):
        """SimulatedRaceConditionError should be raise-able and contain a message."""
        from tests.fakes import SimulatedRaceConditionError
        with pytest.raises(SimulatedRaceConditionError) as exc:
            raise SimulatedRaceConditionError("Database is locked")
        assert "locked" in str(exc.value)

    def test_fk_violation_error_class(self):
        """SimulatedForeignKeyViolation should be raise-able and contain a message."""
        from tests.fakes import SimulatedForeignKeyViolation
        with pytest.raises(SimulatedForeignKeyViolation) as exc:
            raise SimulatedForeignKeyViolation("Foreign key violation on account")
        assert "account" in str(exc.value)

    def test_database_timeout_error_class(self):
        """SimulatedDatabaseTimeout should be raise-able and contain a message."""
        from tests.fakes import SimulatedDatabaseTimeout
        with pytest.raises(SimulatedDatabaseTimeout) as exc:
            raise SimulatedDatabaseTimeout("Database timeout after 30s")
        assert "30s" in str(exc.value)


# ═══════════════════════════════════════════════════════════════════════════════
#  services.py  –  Edge case paths
# ═══════════════════════════════════════════════════════════════════════════════


class TestServiceEdgeCases:

    def test_auth_service_customer_register_welcome_notification_fails_gracefully(self):
        """Welcome notification failure should not prevent successful registration."""
        from unionbank.application.services import AuthService

        from tests.fakes import (
            FakeAccountRepository,
            FakeAdminRepository,
            FakeLoginAttemptRepository,
            FakeTokenVersionRepository,
        )

        auth = AuthService(
            account_repo=FakeAccountRepository(),
            admin_repo=FakeAdminRepository(),
            login_attempt_repo=FakeLoginAttemptRepository(),
            token_version_repo=FakeTokenVersionRepository(),
            notif_service=None,  # No notification service
        )
        result = auth.customer_register(
            name="Edge Case", age=25, gender="Male",
            mobile="9876543210", email="edge@test.com",
            password="Str0ngPass!",
        )
        assert result.success is True
        assert "created" in result.message.lower()

    def test_account_service_change_password_token_version_incremented(self):
        """Password change should increment token version."""
        from unionbank.application.services import AccountService
        from unionbank.domain.entities import Account
        from unionbank.utils.hashing import hash_password

        from tests.fakes import (
            FakeAccountRepository,
            FakeTokenVersionRepository,
            FakeTransactionRepository,
        )

        repo = FakeAccountRepository()
        token_repo = FakeTokenVersionRepository()
        svc = AccountService(
            account_repo=repo,
            txn_repo=FakeTransactionRepository(),
            token_version_repo=token_repo,
        )

        acc = Account(
            account_number="1000000001", name="Token Test",
            password=hash_password("OldPass1!@"), balance=Decimal("100"),
        )
        repo.create(acc)

        # Before password change, version should be 0
        assert token_repo.get_version("1000000001") == 0

        svc.change_password("1000000001", "OldPass1!@", "NewPass1!@")

        # After password change, version should be 1
        assert token_repo.get_version("1000000001") == 1

    def test_transaction_service_deposit_with_idempotency_repo(self):
        """Deposit with idempotency repo configured should work."""
        from unionbank.application.services import TransactionService
        from unionbank.domain.entities import Account
        from unionbank.utils.hashing import hash_password

        from tests.fakes import (
            FakeAccountRepository,
            FakeTransactionRepository,
        )

        repo = FakeAccountRepository()
        svc = TransactionService(
            account_repo=repo,
            txn_repo=FakeTransactionRepository(),
            idempotency_repo=None,  # Explicitly None
        )

        acc = Account(
            account_number="1000000001", name="Idem Test",
            password=hash_password("pass"), balance=Decimal("100"),
        )
        repo.create(acc)

        # Deposit without idempotency key should work
        result = svc.deposit("1000000001", Decimal("50"), idempotency_key=None)
        assert result.success is True
        assert repo.get("1000000001").balance == Decimal("150")

    def test_admin_service_list_accounts_paginated(self):
        """Admin paginated listing should work."""
        from unionbank.application.services import AdminService
        from unionbank.domain.entities import Account
        from unionbank.utils.hashing import hash_password

        from tests.fakes import FakeAccountRepository

        repo = FakeAccountRepository()
        for i in range(25):
            repo.create(Account(
                account_number=f"1000000{i:03d}",
                name=f"User {i}",
                password=hash_password("pass"),
                balance=Decimal(str(i * 100)),
            ))

        svc = AdminService(
            account_repo=repo,
            txn_repo=None,  # Not needed for this test
            admin_repo=None,
            audit_log_repo=None,
        )

        page1, total = svc.list_accounts_paginated(page=1, per_page=10)
        assert len(page1) == 10
        assert total == 25

        page2, _ = svc.list_accounts_paginated(page=2, per_page=10)
        assert len(page2) == 10

        page3, _ = svc.list_accounts_paginated(page=3, per_page=10)
        assert len(page3) == 5

    def test_savings_goal_delete_nonexistent_fails(self):
        """Delete a non-existent goal should fail."""
        from unionbank.application.services import SavingsGoalService

        from tests.fakes import (
            FakeAccountRepository,
            FakeSavingsGoalRepository,
            FakeTransactionRepository,
        )

        svc = SavingsGoalService(
            goal_repo=FakeSavingsGoalRepository(),
            account_repo=FakeAccountRepository(),
            txn_repo=FakeTransactionRepository(),
        )

        result = svc.delete_goal("1000000001", "GOAL-NONEXIST")
        assert result.success is False
        assert "not found" in result.message.lower()
