"""
formatting.py  –  Formatting helpers, ID generators, and CLI input helpers.
"""

import random
import re
import string
from datetime import datetime

from .file_io import load_json, ACCOUNTS_FILE


# ─────────────────────────────────────────────
#  Currency formatting
# ─────────────────────────────────────────────

def fmt_currency(amount: float) -> str:
    return f"₹{amount:,.2f}"


# ─────────────────────────────────────────────
#  Timestamp
# ─────────────────────────────────────────────

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def generate_goal_id() -> str:
    """Generate a unique goal ID like GOAL-XXXXXXXX."""
    return "GOAL-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ─────────────────────────────────────────────
#  CLI input helpers
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


# ═══════════════════════════════════════════════════════════════════════════════
#  PII-safe logging helpers
# ═══════════════════════════════════════════════════════════════════════════════


def mask_account_number(acc_no: str) -> str:
    """Mask an account number for safe logging — shows only last 4 digits."""
    if not acc_no or len(acc_no) < 4:
        return "****"
    return "*" * (len(acc_no) - 4) + acc_no[-4:]


def mask_sensitive_data(msg: str) -> str:
    """Mask sensitive data in a log message for PII safety.

    Masks:
    - Account numbers (8+ digit sequences)
    - Email addresses (local-part replaced with ***)
    """
    # Mask account numbers (sequences of 8+ digits)
    msg = re.sub(r'\b(\d{8,})\b', lambda m: mask_account_number(m.group(1)), msg)
    # Mask email addresses
    msg = re.sub(r'([\w.-]+)@([\w.-]+\.\w{2,})', r'***@\2', msg)
    return msg
