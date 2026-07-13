"""
config.py  –  Centralized configuration for Union Bank Management System.

All environment variables, file paths, and application constants live here.
The app will refuse to boot if required env vars are missing (outside TESTING mode).
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Base directory ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


# ── Helper: read env or raise ────────────────────────────────────────────────
def _require_env(name: str, default: Optional[str] = None) -> str:
    """Read an env var. If missing and no default, raise RuntimeError."""
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"See .env.example or set it before starting the app."
        )
    return value


# ── Helper: read env or return None ──────────────────────────────────────────
def _optional_env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


# ═══════════════════════════════════════════════════════════════════════════════
#  Config dataclass
# ═══════════════════════════════════════════════════════════════════════════════

# Allow turning off strict env-var checks during tests
_TESTING = os.environ.get("UNION_BANK_TESTING", "0") == "1"


@dataclass(frozen=True)
class Config:
    # ── Secrets ──────────────────────────────────────────────────────────────
    JWT_SECRET: str = field(
        default_factory=lambda: (
            _require_env("JWT_SECRET") if not _TESTING else "test-secret-not-for-prod"
        )
    )
    JWT_PRIVATE_KEY: str = field(
        default_factory=lambda: (
            _optional_env("JWT_PRIVATE_KEY", "") or ""
        )
    )
    JWT_PUBLIC_KEY: str = field(
        default_factory=lambda: (
            _optional_env("JWT_PUBLIC_KEY", "") or ""
        )
    )
    FLASK_SECRET_KEY: str = field(
        default_factory=lambda: (
            _require_env("FLASK_SECRET_KEY") if not _TESTING else os.urandom(24).hex()
        )
    )

    # ── JWT ───────────────────────────────────────────────────────────────────
    # Use RS256 (asymmetric) in production — set JWT_PRIVATE_KEY + JWT_PUBLIC_KEY env vars.
    # Falls back to HS256 (symmetric) if RSA keys are not configured.
    JWT_ALGORITHM: str = "RS256" if _optional_env("JWT_PRIVATE_KEY") else "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived: 15 minutes
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh: 7 days

    # ── Rate limiting ─────────────────────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # ── Session ───────────────────────────────────────────────────────────────
    SESSION_TIMEOUT_SECONDS: int = 300  # 5 minutes

    # ── Interest ──────────────────────────────────────────────────────────────
    SAVINGS_INTEREST_RATE: float = 3.5  # % per annum

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ALLOWED_ORIGINS: list[str] = field(
        default_factory=lambda: (
            _optional_env("CORS_ALLOWED_ORIGINS", "http://localhost:5000,http://localhost:8000").split(",")
        )
    )

    # ── File paths (data directory) ───────────────────────────────────────────
    DATA_DIR: Path = DATA_DIR

    # ── Testing mode ──────────────────────────────────────────────────────────
    TESTING: bool = _TESTING

    # ── Transaction categories ────────────────────────────────────────────────
    TRANSACTION_CATEGORIES: list[str] = field(default_factory=lambda: [
        "General",
        "Food & Dining",
        "Transport",
        "Shopping",
        "Bills & Utilities",
        "Entertainment",
        "Health",
        "Education",
        "Salary",
        "Savings",
        "Investment",
        "Rent",
        "Other",
    ])


# ── Singleton instance ────────────────────────────────────────────────────────
settings = Config()
