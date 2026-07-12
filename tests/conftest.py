"""
pytest fixtures for Union Bank tests.

All tests use temporary directories — never touch real production data/ files.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Ensure project root is in path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _unset_env_vars_for_safety():
    """Prevent accidental use of real env secrets during tests."""
    os.environ.pop("JWT_SECRET", None)
    os.environ.pop("FLASK_SECRET_KEY", None)
    yield


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Provide a temporary data directory for JSON file-based tests.

    Sets the environment variable UNION_BANK_DATA_DIR to the temp path
    so that utils.py's file resolution picks it up (if it reads from env).
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    # Future-proof: if the app reads DATA_DIR from env, this will redirect it
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
