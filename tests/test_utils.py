"""
Tests for utils.py – validation helpers, password hashing, generators, etc.
"""
import os
import sys
import tempfile
import json

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    hash_password,
    verify_password,
    validate_email,
    validate_phone,
    validate_password,
    validate_name,
    generate_account_number,
    generate_transaction_id,
    fmt_currency,
    get_float,
)
from utils.file_io import (
    load_json,
    save_json,
    ACCOUNTS_FILE,
)


# ───────────────────────────────────────────────
#  Password hashing tests
# ───────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("SecurePass1")
        assert isinstance(hashed, str)
        assert hashed.startswith("$2")
        assert verify_password("SecurePass1", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("SecurePass1")
        assert verify_password("WrongPass1", hashed) is False

    def test_empty_password(self):
        hashed = hash_password("")
        # Empty password still hashes
        assert isinstance(hashed, str)
        assert hashed.startswith("$2")
        assert verify_password("", hashed) is True

    def test_verify_with_invalid_hash(self):
        assert verify_password("test", "not-a-valid-hash") is False
        assert verify_password("test", "") is False

    def test_two_hashes_are_different(self):
        h1 = hash_password("SecurePass1")
        h2 = hash_password("SecurePass1")
        # Each bcrypt hash uses a different salt
        assert h1 != h2


# ───────────────────────────────────────────────
#  Email validation tests
# ───────────────────────────────────────────────

class TestEmailValidation:
    def test_valid_emails(self):
        assert validate_email("user@example.com") is True
        assert validate_email("first.last@domain.co.in") is True
        assert validate_email("user+tag@example.org") is True
        assert validate_email("123@abc.xyz") is True
        assert validate_email("  user@example.com  ") is True  # whitespace trimmed

    def test_invalid_emails(self):
        assert validate_email("") is False
        assert validate_email("not-an-email") is False
        assert validate_email("@domain.com") is False
        assert validate_email("user@") is False
        assert validate_email("user@.com") is False
        assert validate_email("user@domain") is False  # no TLD
        assert validate_email("user@domain.c") is False  # TLD too short


# ───────────────────────────────────────────────
#  Phone validation tests
# ───────────────────────────────────────────────

class TestPhoneValidation:
    def test_valid_phones(self):
        assert validate_phone("9876543210") is True
        assert validate_phone("6123456789") is True
        assert validate_phone(" 9876543210 ") is True  # whitespace trimmed

    def test_invalid_phones(self):
        assert validate_phone("") is False
        assert validate_phone("1234567890") is False  # starts with 1
        assert validate_phone("987654321") is False   # 9 digits
        assert validate_phone("98765432100") is False  # 11 digits
        assert validate_phone("abcdefghij") is False   # letters
        assert validate_phone("0876543210") is False   # starts with 0


# ───────────────────────────────────────────────
#  Password strength validation tests
# ───────────────────────────────────────────────

class TestPasswordValidation:
    def test_valid_passwords(self):
        valid, msg = validate_password("Strong1!@")
        assert valid is True
        assert msg == ""

        valid, msg = validate_password("Abcdef1xyz")
        assert valid is True

        valid, msg = validate_password("P@ssw0rdLong")
        assert valid is True

    def test_too_short(self):
        valid, msg = validate_password("Ab1")
        assert valid is False
        assert "8 characters" in msg

    def test_no_uppercase(self):
        valid, msg = validate_password("abcdefgh1")
        assert valid is False
        assert "uppercase" in msg

    def test_no_lowercase(self):
        valid, msg = validate_password("ABCDEFGH1")
        assert valid is False
        assert "lowercase" in msg

    def test_no_digit(self):
        valid, msg = validate_password("Abcdefgh!")
        assert valid is False
        assert "digit" in msg

    def test_empty_password(self):
        valid, msg = validate_password("")
        assert valid is False


# ───────────────────────────────────────────────
#  Name validation tests
# ───────────────────────────────────────────────

class TestNameValidation:
    def test_valid_names(self):
        assert validate_name("John") is True
        assert validate_name("John Doe") is True
        assert validate_name("Mary Jane Smith") is True
        assert validate_name("  John  ") is True

    def test_invalid_names(self):
        assert validate_name("") is False
        assert validate_name("  ") is False
        assert validate_name("A") is False  # too short
        assert validate_name("John123") is False  # contains digits
        assert validate_name("John@Doe") is False  # special chars


# ───────────────────────────────────────────────
#  Generator tests
# ───────────────────────────────────────────────

class TestGenerators:
    def test_generate_account_number_structure(self):
        num = generate_account_number()
        assert isinstance(num, str)
        assert len(num) == 10
        assert num.isdigit()

    def test_generate_transaction_id_structure(self):
        txn_id = generate_transaction_id()
        assert isinstance(txn_id, str)
        assert txn_id.startswith("TXN-")
        assert len(txn_id) == 12  # "TXN-" + 8 chars

    def test_transaction_id_is_unique(self):
        ids = {generate_transaction_id() for _ in range(100)}
        assert len(ids) == 100


# ───────────────────────────────────────────────
#  Currency formatting tests
# ───────────────────────────────────────────────

class TestCurrencyFormatting:
    def test_basic_format(self):
        assert fmt_currency(0) == "₹0.00"
        assert fmt_currency(100) == "₹100.00"
        assert fmt_currency(1000) == "₹1,000.00"
        assert fmt_currency(1000000.50) == "₹1,000,000.50"

    def test_negative_amount(self):
        assert fmt_currency(-100) == "₹-100.00"


# ───────────────────────────────────────────────
#  JSON file helpers tests
# ───────────────────────────────────────────────

class TestJsonHelpers:
    def test_save_and_load_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            data = {"key": "value", "number": 42}
            save_json(tmp_path, data)

            loaded = load_json(tmp_path)
            assert loaded == data
        finally:
            os.unlink(tmp_path)

    def test_load_missing_file(self):
        result = load_json("/tmp/nonexistent_file_xyz.json")
        assert result == {}

    def test_load_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            result = load_json(tmp_path)
            assert result == {}
        finally:
            os.unlink(tmp_path)


# ───────────────────────────────────────────────
#  get_float tests (simulated input)
# ───────────────────────────────────────────────

class TestGetFloat:
    def test_valid_amount(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "100.50")
        result = get_float("Enter amount: ")
        assert result == 100.50

    def test_zero_fails(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "0")
        result = get_float("Enter amount: ")
        assert result is None

    def test_negative_fails(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "-50")
        result = get_float("Enter amount: ")
        assert result is None

    def test_non_numeric_fails(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "abc")
        result = get_float("Enter amount: ")
        assert result is None
