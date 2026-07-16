"""rate_limit.py  –  Rate limiting (login attempts) and session management.

Extracted from the old utils/auth.py god module.
Uses the container's LoginAttemptRepository (SQLite) instead of JSON.
"""

import time

from config import settings

# ── Constants (from centralized config) ───────────────────────────────────────
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOGIN_LOCKOUT_MINUTES = settings.LOGIN_LOCKOUT_MINUTES
SESSION_TIMEOUT_SECONDS = settings.SESSION_TIMEOUT_SECONDS


# ─────────────────────────────────────────────
#  Rate limiting (via container's LoginAttemptRepository)
# ─────────────────────────────────────────────

def _get_login_attempt_repo():
    """Get the LoginAttemptRepository from the container."""
    from infrastructure.container import get_container
    return get_container().login_attempt_repo()


def check_login_locked(acc_no: str) -> tuple:
    """Check if an account is locked due to too many failed attempts.
    Returns (is_locked: bool, remaining_minutes: int).
    Uses SQLite-backed LoginAttemptRepository.
    """
    repo = _get_login_attempt_repo()
    return repo.is_locked(acc_no, MAX_LOGIN_ATTEMPTS)


def record_failed_login(acc_no: str) -> int:
    """Record a failed login attempt via SQLite repository.
    Returns remaining attempts before lockout.
    """
    from logger import logger
    repo = _get_login_attempt_repo()
    remaining = repo.record_failure(acc_no, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES)
    repo.commit()

    if remaining <= 0:
        logger.warning(f"Account locked due to {MAX_LOGIN_ATTEMPTS} failed attempts: {acc_no}")

    return remaining


def reset_login_attempts(acc_no: str) -> None:
    """Reset login attempts on successful login."""
    repo = _get_login_attempt_repo()
    repo.reset(acc_no)
    repo.commit()


# ─────────────────────────────────────────────
#  Session management
# ─────────────────────────────────────────────

def check_session_timeout(last_activity: float) -> bool:
    """Check if the session has timed out.
    Returns True if session is still valid, False if timed out.
    """
    return (time.time() - last_activity) < SESSION_TIMEOUT_SECONDS


def get_session_timeout_seconds() -> int:
    """Return the session timeout duration in seconds."""
    return SESSION_TIMEOUT_SECONDS
