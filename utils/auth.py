"""
auth.py  –  Authentication, rate limiting, session management, CSV export, interest calc.
"""

import csv
import os
import time
from datetime import datetime, timedelta

import bcrypt

from .file_io import load_json, save_json, LOGIN_ATTEMPTS_FILE
from logger import logger
from config import settings


# ── Constants (from centralized config) ───────────────────────────────────────
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOGIN_LOCKOUT_MINUTES = settings.LOGIN_LOCKOUT_MINUTES
SESSION_TIMEOUT_SECONDS = settings.SESSION_TIMEOUT_SECONDS
SAVINGS_INTEREST_RATE = settings.SAVINGS_INTEREST_RATE
TRANSACTION_CATEGORIES = settings.TRANSACTION_CATEGORIES


# ─────────────────────────────────────────────
#  Password hashing (bcrypt)
# ─────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt with a salt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, AttributeError):
        return False


# ─────────────────────────────────────────────
#  Rate limiting
# ─────────────────────────────────────────────

def _load_login_attempts() -> dict:
    """Load login attempt tracking data."""
    return load_json(LOGIN_ATTEMPTS_FILE)


def _save_login_attempts(data: dict) -> None:
    """Save login attempt tracking data."""
    save_json(LOGIN_ATTEMPTS_FILE, data)


def check_login_locked(acc_no: str) -> tuple:
    """
    Check if an account is locked due to too many failed attempts.
    Returns (is_locked: bool, remaining_minutes: int).
    """
    attempts = _load_login_attempts()
    record = attempts.get(acc_no)
    if not record:
        return False, 0

    if record["count"] >= MAX_LOGIN_ATTEMPTS:
        lockout_end = datetime.fromisoformat(record["lockout_until"])
        if datetime.now() < lockout_end:
            remaining = int((lockout_end - datetime.now()).total_seconds() // 60)
            return True, max(1, remaining)
        else:
            # Lockout expired, reset
            del attempts[acc_no]
            _save_login_attempts(attempts)
            return False, 0
    return False, 0


def record_failed_login(acc_no: str) -> int:
    """
    Record a failed login attempt. Returns remaining attempts before lockout.
    """
    attempts = _load_login_attempts()
    now = datetime.now()

    if acc_no not in attempts:
        attempts[acc_no] = {"count": 0, "first_failed": None, "lockout_until": None}

    record = attempts[acc_no]

    # Reset if lockout has expired
    if record["lockout_until"]:
        lockout_end = datetime.fromisoformat(record["lockout_until"])
        if now >= lockout_end:
            record["count"] = 0
            record["first_failed"] = None
            record["lockout_until"] = None

    record["count"] += 1
    if record["first_failed"] is None:
        record["first_failed"] = now.isoformat()

    if record["count"] >= MAX_LOGIN_ATTEMPTS:
        lockout_until = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        record["lockout_until"] = lockout_until.isoformat()
        logger.warning(f"Account locked due to {MAX_LOGIN_ATTEMPTS} failed attempts: {acc_no}")

    _save_login_attempts(attempts)
    return max(0, MAX_LOGIN_ATTEMPTS - record["count"])


def reset_login_attempts(acc_no: str) -> None:
    """Reset login attempts on successful login."""
    attempts = _load_login_attempts()
    if acc_no in attempts:
        del attempts[acc_no]
        _save_login_attempts(attempts)


# ─────────────────────────────────────────────
#  Session management
# ─────────────────────────────────────────────

def check_session_timeout(last_activity: float) -> bool:
    """
    Check if the session has timed out.
    Returns True if session is still valid, False if timed out.
    """
    return (time.time() - last_activity) < SESSION_TIMEOUT_SECONDS


def get_session_timeout_seconds() -> int:
    """Return the session timeout duration in seconds."""
    return SESSION_TIMEOUT_SECONDS


# ─────────────────────────────────────────────
#  Interest calculation
# ─────────────────────────────────────────────

def calculate_monthly_interest(balance: float) -> float:
    """
    Calculate monthly interest on a balance.
    Uses SAVINGS_INTEREST_RATE % per annum, compounded monthly.
    Returns the interest amount.
    """
    monthly_rate = SAVINGS_INTEREST_RATE / 12 / 100
    return round(balance * monthly_rate, 2)


# ─────────────────────────────────────────────
#  CSV export
# ─────────────────────────────────────────────

def export_transactions_to_csv(acc_no: str, records: list, filepath: str) -> str:
    """
    Export transaction records to a CSV file.
    Returns the filepath of the created file.
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Transaction ID", "Date/Time", "Type", "Amount", "Balance", "Description", "Category"])

        for t in records:
            sign = "+" if t["type"] in ("DEPOSIT", "TRANSFER_IN") else "-"
            amount_str = f"{sign}{t['amount']}"
            writer.writerow([
                t.get("txn_id", ""),
                t.get("timestamp", ""),
                t.get("type", ""),
                amount_str,
                t.get("balance", ""),
                t.get("description", ""),
                t.get("category", "General"),
            ])

    return filepath


def generate_csv_filename(acc_no: str) -> str:
    """Generate a default CSV export filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", f"statement_{acc_no}_{timestamp}.csv")


# ─────────────────────────────────────────────
#  Transaction categories helper
# ─────────────────────────────────────────────

def get_category_choice() -> str:
    """Prompt user to select a transaction category from predefined list."""
    print(f"\n  {'─' * 30}")
    print("  Select Category:")
    for i, cat in enumerate(TRANSACTION_CATEGORIES, 1):
        print(f"  {i:>2}) {cat}")
    print(f"  {'─' * 30}")

    try:
        choice = int(input("  Enter category number: ").strip())
        if 1 <= choice <= len(TRANSACTION_CATEGORIES):
            return TRANSACTION_CATEGORIES[choice - 1]
    except ValueError:
        pass
    return "General"
