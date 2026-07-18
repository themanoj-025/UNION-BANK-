"""
Smoke tests – verify that all project modules import correctly after changes.
"""

from unionbank.utils import (
    hash_password,
    validate_email,
)
from unionbank.utils.logger import logger
from unionbank.entrypoints.cli.account import Account
from unionbank.entrypoints.cli.bank import Bank
from unionbank.entrypoints.cli.admin import Admin
from unionbank.entrypoints.cli.main import main_menu


class TestSmoke:
    """Verify that all project modules can be imported without errors."""

    def test_import_utils(self):
        assert hasattr(validate_email, "__call__")
        assert hasattr(hash_password, "__call__")

    def test_import_logger(self):
        assert logger is not None

    def test_import_account(self):
        assert Account is not None

    def test_import_bank(self):
        assert Bank is not None

    def test_import_admin(self):
        assert Admin is not None

    def test_import_main(self):
        assert main_menu is not None
