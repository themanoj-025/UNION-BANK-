import csv
import io
import json
import os
import random
import re
import shutil
import string
import tempfile
import time
from datetime import datetime, timedelta

import bcrypt

from logger import logger

# ── Data directory: respect env override for test isolation ───────────────────
_data_dir = os.environ.get(
    "UNION_BANK_DATA_DIR",
    os.path.join(os.path.dirname(__file__), "data"),
)
ACCOUNTS_FILE = os.path.join(_data_dir, "accounts.json")
TRANSACTIONS_FILE = os.path.join(_data_dir, "transactions.json")
LOGIN_ATTEMPTS_FILE = os.path.join(_data_dir, "login_attempts.json")
SAVINGS_GOALS_FILE = os.path.join(_data_dir, "savings_goals.json")
ADMIN_FILE = os.path.join(_data_dir, "admin.json")

# ── Constants ────────────────────────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15
SESSION_TIMEOUT_SECONDS = 300  # 5 minutes of inactivity

# ── Transaction categories ───────────────────────────────────────────────────
TRANSACTION_CATEGORIES = [
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
]

# ── Interest rate ────────────────────────────────────────────────────────────
SAVINGS_INTEREST_RATE = 3.5  # % per annum

# ── Savings goals helper ─────────────────────────────────────────────────

def load_goals(acc_no: str) -> list:
    """Load savings goals for a specific account."""
    all_goals = load_json(SAVINGS_GOALS_FILE)
    return all_goals.get(acc_no, [])


def save_goals(acc_no: str, goals: list) -> None:
    """Save savings goals for a specific account."""
    all_goals = load_json(SAVINGS_GOALS_FILE)
    all_goals[acc_no] = goals
    save_json(SAVINGS_GOALS_FILE, all_goals)


def generate_goal_id() -> str:
    """Generate a unique goal ID like GOAL-XXXXXXXX."""
    return "GOAL-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ─────────────────────────────────────────────
#  JSON helpers (hardened with auto-backup)
# ─────────────────────────────────────────────

def _backup_path(filepath: str) -> str:
    """Return the backup file path (same directory, .bak extension)."""
    return filepath + ".bak"


def load_json(filepath: str) -> dict:
    """
    Load JSON file safely with corruption recovery.
    Returns empty dict if file is missing, empty, or corrupted.
    On corruption, attempts to restore from backup.
    """
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, ValueError, IOError) as e:
        logger.error(f"Corrupted JSON file detected: {filepath} — {e}")

        # Attempt recovery from backup
        backup = _backup_path(filepath)
        if os.path.exists(backup):
            logger.info(f"Attempting recovery from backup: {backup}")
            try:
                with open(backup, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        # Restore the original from backup
                        with open(filepath, "w", encoding="utf-8") as fw:
                            json.dump(data, fw, indent=4)
                        logger.info(f"Recovered {filepath} from backup successfully.")
                        return data
            except (json.JSONDecodeError, IOError):
                logger.error(f"Backup file also corrupted: {backup}")

        # If backup also fails or doesn't exist, reset
        logger.warning(f"Resetting corrupted file to empty: {filepath}")
        save_json(filepath, {})
        return {}


def save_json(filepath: str, data) -> None:
    """
    Persist data to JSON file atomically with auto-backup.
    - Creates a .bak copy of the previous version before overwriting
    - Writes to a temp file first, then atomically renames (reduces corruption)
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Create backup of existing file before overwriting
    if os.path.exists(filepath):
        try:
            shutil.copy2(filepath, _backup_path(filepath))
        except (IOError, shutil.Error) as e:
            logger.warning(f"Failed to create backup for {filepath}: {e}")

    # Atomic write: write to temp file, then rename
    try:
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json",
            prefix=os.path.basename(filepath) + ".",
            dir=os.path.dirname(filepath),
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(fd)

        # Atomic rename (on Windows, replace=True is needed)
        os.replace(tmp_path, filepath)
    except (IOError, OSError) as e:
        logger.error(f"Failed to save {filepath}: {e}")
        raise


# ─────────────────────────────────────────────
#  ID / number generators
# ─────────────────────────────────────────────

def generate_account_number() -> str:
    """Return a unique 10-digit account number (as string)."""
    accounts = load_json(ACCOUNTS_FILE)
    while True:
        number = str(random.randint(1000000000, 9999999999))
        if number not in accounts:
            return number


def generate_transaction_id() -> str:
    """Return a unique transaction ID like TXN-XXXXXXXX."""
    return "TXN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ─────────────────────────────────────────────
#  Timestamp
# ─────────────────────────────────────────────

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────
#  Currency formatting
# ─────────────────────────────────────────────

def fmt_currency(amount: float) -> str:
    return f"₹{amount:,.2f}"


# ─────────────────────────────────────────────
#  Input helpers
# ─────────────────────────────────────────────

def get_float(prompt: str):
    """Prompt for a positive float; return None on invalid input."""
    try:
        val = float(input(prompt))
        if val <= 0:
            raise ValueError
        return val
    except ValueError:
        print("  [!] Invalid amount. Please enter a positive number.")
        return None


def get_int(prompt: str):
    try:
        return int(input(prompt))
    except ValueError:
        print("  [!] Please enter a valid integer.")
        return None


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
    return os.path.join(os.path.dirname(__file__), "data", f"statement_{acc_no}_{timestamp}.csv")


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
#  Transaction categories
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


# ─────────────────────────────────────────────
#  Input validation helpers
# ─────────────────────────────────────────────

def validate_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """Validate Indian mobile number: 10 digits starting with 6-9."""
    return bool(re.match(r"^[6-9]\d{9}$", phone.strip()))


def validate_password(password: str) -> tuple:
    """
    Validate password strength.
    Returns (is_valid: bool, error_message: str).
    Rules: min 8 chars, at least 1 uppercase, 1 lowercase, 1 digit.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit."
    return True, ""


def validate_name(name: str) -> bool:
    """Validate name: non-empty, letters and spaces only."""
    return bool(name.strip()) and bool(re.match(r"^[A-Za-z\s.]{2,50}$", name.strip()))
