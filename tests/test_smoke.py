"""
Smoke tests – verify that all modules import correctly after changes.
"""
import os
import sys
import tempfile

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSmoke:
    """Verify that all project modules can be imported without errors."""

    def test_import_utils(self):
        import utils
        assert hasattr(utils, "hash_password")
        assert hasattr(utils, "verify_password")
        assert hasattr(utils, "validate_email")
        assert hasattr(utils, "validate_phone")
        assert hasattr(utils, "validate_password")
        assert hasattr(utils, "validate_name")
        assert hasattr(utils, "fmt_currency")
        assert hasattr(utils, "generate_account_number")
        assert hasattr(utils, "generate_transaction_id")

    def test_import_logger(self):
        import logger
        assert hasattr(logger, "logger")

    def test_import_account(self):
        import account
        assert hasattr(account, "Account")

    def test_import_bank(self):
        import bank
        assert hasattr(bank, "Bank")

    def test_import_admin(self):
        # admin.py runs _init_admin() on import, so we need to ensure no crash
        import admin
        assert hasattr(admin, "Admin")

    def test_import_main(self):
        import main
        assert hasattr(main, "main_menu")
