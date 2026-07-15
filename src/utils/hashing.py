"""
hashing.py  –  Password hashing (bcrypt).

Extracted from the old utils/auth.py god module.
"""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with a salt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, AttributeError):
        return False
