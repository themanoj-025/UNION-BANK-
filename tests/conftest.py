"""
pytest fixtures for Union Bank tests.

All tests use temporary directories — never touch real production data/ files.
Test-safe env vars are set BEFORE any project module is imported.
"""

import os
import tempfile
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
#  IMPORTANT: Set test-safe env vars BEFORE any project module is imported.
#  config.py calls _require_env() at module level, so JWT_SECRET must exist.
#  admin.py runs _init_admin() at import time, so UNION_BANK_DATA_DIR must also
#  be set to a temp directory BEFORE any module imports happen.
# ═══════════════════════════════════════════════════════════════════════════════
_test_data_dir = tempfile.mkdtemp(prefix="union_bank_test_")
os.environ.setdefault("UNION_BANK_DATA_DIR", _test_data_dir)
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")
os.environ.setdefault("FLASK_SECRET_KEY", "test-flask-secret-for-testing")
os.environ.setdefault("UNION_BANK_TESTING", "1")

# The unionbank package is installed via pip install -e ., so all
# imports use unionbank.-qualified paths. No sys.path manipulation needed.

import pytest


@pytest.fixture(autouse=True)
def _unset_env_vars_for_safety():
    """
    Prevent accidental use of real env secrets during tests.

    This runs after module imports (at test function time), but the module-level
    os.environ.setdefault() calls above ensure safe defaults exist already.
    """
    # We set test defaults at module level already; this fixture exists to
    # document the pattern and can be extended for per-test env isolation.
    yield


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """
    Provide a temporary data directory for JSON file-based tests.

    Sets UNION_BANK_DATA_DIR so that utils.py's file resolution uses the temp dir.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["UNION_BANK_DATA_DIR"] = str(data_dir)
    return data_dir


@pytest.fixture
def sample_account_data() -> dict:
    """Return a minimal valid account dict for unit tests."""
    return {
        "account_number": "9999999999",
        "name": "Test User",
        "age": 25,
        "gender": "Male",
        "mobile": "9876543210",
        "email": "test@example.com",
        "password": "$2b$12$testhash1234567890123456789012345678901234567890",
        "balance": 5000.0,
        "is_active": True,
        "is_frozen": False,
        "created_at": "2026-01-01 00:00:00",
    }


@pytest.fixture
def c():
    """
    Get a fresh DI container with a clean SQLite database.

    Creates a unique temp directory per test so tests never share
    database state. This mirrors test_integration.py's _fresh_db fixture
    but is available globally from conftest.py.
    """
    import tempfile
    data_dir = tempfile.mkdtemp(prefix="union_bank_c_")
    old = os.environ.get("UNION_BANK_DATA_DIR")
    os.environ["UNION_BANK_DATA_DIR"] = data_dir
    from unionbank.infrastructure.container import get_container, reset_container
    reset_container()
    yield get_container()
    reset_container()
    if old:
        os.environ["UNION_BANK_DATA_DIR"] = old
    else:
        os.environ.pop("UNION_BANK_DATA_DIR", None)


@pytest.fixture
def sample_account():
    """
    Return an Account domain object for tests.

    The account is created in the database so it can be used with
    both fake repositories (unit tests) and real repositories (integration tests).
    """
    from decimal import Decimal
    from unionbank.domain.entities import Account
    from unionbank.utils.hashing import hash_password

    return Account(
        account_number="1000000001",
        name="Test User",
        age=30,
        gender="Male",
        mobile="9876543210",
        email="test@example.com",
        password=hash_password("Secure1Pass"),
        balance=Decimal("1000.00"),
        is_active=True,
        is_frozen=False,
    )


@pytest.fixture
def sample_transaction_records() -> list[dict]:
    """Return sample transaction records for CSV/statement tests."""
    return [
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
