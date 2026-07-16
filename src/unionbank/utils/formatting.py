"""formatting.py  –  Formatting helpers, ID generators, and CLI input helpers.
"""

import random
import re
import string
from datetime import datetime

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

def generate_account_number(max_attempts: int = 1000) -> str:
    """Return a unique 10-digit account number (as string).

    Checks uniqueness against the SQLite database via the container.
    Raises RuntimeError if a unique number cannot be found within max_attempts.
    """
    from container import get_container
    c = get_container()
    repo = c.account_repo()
    for _ in range(max_attempts):
        number = str(random.randint(1000000000, 9999999999))
        if not repo.exists(number):
            return number
    raise RuntimeError(
        f"Could not generate a unique account number after {max_attempts} attempts. "
        "The account number space (9 billion possible numbers) may be exhausted."
    )


def generate_transaction_id() -> str:
    """Return a unique transaction ID like TXN-XXXXXXXX."""
    return "TXN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def generate_goal_id() -> str:
    """Generate a unique goal ID like GOAL-XXXXXXXX."""
    return "GOAL-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def generate_loan_id() -> str:
    """Generate a unique loan ID like LON-XXXXXXXX."""
    return "LON-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def generate_notification_id() -> str:
    """Generate a unique notification ID like NTF-XXXXXXXX."""
    return "NTF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ═══════════════════════════════════════════════════════════════════════════════
#  EMI Calculator
# ═══════════════════════════════════════════════════════════════════════════════


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculate EMI using the standard formula.

    EMI = P × r × (1+r)^n / ((1+r)^n - 1)

    Where:
        P = Principal amount
        r = Monthly interest rate (annual_rate / 12 / 100)
        n = Number of monthly installments

    Args:
        principal:     Loan principal amount.
        annual_rate:   Annual interest rate in percent (e.g. 10.5 for 10.5%%).
        tenure_months: Loan tenure in months.

    Returns:
        Monthly EMI amount rounded to 2 decimal places.

    """
    if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
        return 0.0

    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return round(principal / tenure_months, 2)

    emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / \
          (((1 + monthly_rate) ** tenure_months) - 1)
    return round(emi, 2)


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
