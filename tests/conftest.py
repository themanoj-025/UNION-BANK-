"""pytest fixtures for Union Bank tests.

All tests use temporary directories — never touch real production data/ files.
Test-safe env vars are set BEFORE any project module is imported.
"""

import os
import sys
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

# Ensure project root, src/, and src/unionbank/ are in path for imports
# The unionbank package lives under src/unionbank/ with a layered structure:
#   src/unionbank/domain/           → domain.*
#   src/unionbank/infrastructure/    → container, database (shim), etc.
#   src/unionbank/entrypoints/cli/   → ui, account (CLI modules)
#   src/unionbank/utils/             → utils.*
#   src/unionbank/application/       → application.*
#
# Order (highest priority first):
#   1. src/                     (for root-level src/ modules)
#   2. src/unionbank/           (for direct un-namespaced imports like domain.*, utils.*)
#   3. src/unionbank/infrastructure/  (for container, database)
#   4. src/unionbank/entrypoints/cli/ (for ui, account)
#   5. project root             (for api/, main.py, etc.)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
UNIONBANK_DIR = SRC_DIR / "unionbank"
INFRA_DIR = UNIONBANK_DIR / "infrastructure"
ENTRYPOINTS_DIR = UNIONBANK_DIR / "entrypoints"
CLI_DIR = ENTRYPOINTS_DIR / "cli"
# Ordering matters: UNIONBANK_DIR must be searched BEFORE SRC_DIR so that
# the real code in src/unionbank/{domain,utils,application,infrastructure}
# is found before the empty stub directories at src/{domain,utils,etc}.
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(CLI_DIR))
sys.path.insert(0, str(ENTRYPOINTS_DIR))
sys.path.insert(0, str(INFRA_DIR))
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(UNIONBANK_DIR))  # highest priority

import pytest


@pytest.fixture(autouse=True)
def _unset_env_vars_for_safety():
    """Prevent accidental use of real env secrets during tests.

    This runs after module imports (at test function time), but the module-level
    os.environ.setdefault() calls above ensure safe defaults exist already.
    """
    # We set test defaults at module level already; this fixture exists to
    # document the pattern and can be extended for per-test env isolation.
    yield


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Provide a temporary data directory for JSON file-based tests.

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
