"""validation.py  –  Input validation helpers for Union Bank.
"""

import re


def validate_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """Validate Indian mobile number: 10 digits starting with 6-9."""
    return bool(re.match(r"^[6-9]\d{9}$", phone.strip()))


def validate_password(password: str) -> tuple:
    """Validate password strength.
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
