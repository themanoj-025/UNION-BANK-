"""
account_rate_limit.py  –  Account-based rate limiting for money-movement endpoints.

Unlike IP-based rate limiting (slowapi), this tracks operations per ACCOUNT,
so an attacker cannot bypass limits by rotating IPs. Each account is limited
to a configurable number of money-movement operations per hour.

Uses an in-memory sliding window. For production, this should be backed by
Redis, but for a portfolio project this is sufficient and demonstrates the
concept clearly.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

from unionbank.config import settings


class AccountRateLimiter:
    """
    Per-account sliding window rate limiter for money-movement operations.
    
    Tracks deposit/withdraw/transfer operations per account within a rolling
    time window. When the limit is exceeded, the operation is rejected with
    a clear message indicating when to retry.
    
    Limits are configured via settings.MONEY_MOVEMENT_RATE_LIMIT (default: "5/hour").
    """

    def __init__(self):
        # {account_number: [timestamp, timestamp, ...]}
        self._operations: dict[str, list[float]] = defaultdict(list)
        self._max_ops, self._window_seconds = self._parse_limit(
            settings.MONEY_MOVEMENT_RATE_LIMIT
        )

    def _parse_limit(self, limit: str) -> tuple[int, int]:
        """Parse rate limit string like '5/hour' into (count, seconds)."""
        count_str, period = limit.split("/")
        count = int(count_str)
        period_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        return count, period_map.get(period, 3600)

    def _cleanup_window(self, acc_no: str) -> None:
        """Remove timestamps outside the current window."""
        cutoff = time.time() - self._window_seconds
        self._operations[acc_no] = [
            ts for ts in self._operations[acc_no] if ts > cutoff
        ]

    def check_and_record(self, acc_no: str) -> tuple[bool, Optional[str]]:
        """
        Check if an operation is allowed for this account, and record it.
        
        Returns:
            (allowed, retry_after_message):
                (True, None) if the operation is allowed
                (False, "Retry after X seconds") if rate limited
        """
        self._cleanup_window(acc_no)
        current_count = len(self._operations[acc_no])

        if current_count >= self._max_ops:
            # Calculate when the oldest operation in the window expires
            oldest = self._operations[acc_no][0]
            retry_after = int(self._window_seconds - (time.time() - oldest))
            return False, (
                f"Rate limit exceeded. {current_count}/{self._max_ops} "
                f"money-movement operations in the last hour. "
                f"Retry after {max(1, retry_after)} seconds."
            )

        # Record this operation
        self._operations[acc_no].append(time.time())
        return True, None

    def get_remaining(self, acc_no: str) -> int:
        """Get the number of remaining allowed operations for this account."""
        self._cleanup_window(acc_no)
        return max(0, self._max_ops - len(self._operations[acc_no]))


# Singleton instance
_account_rate_limiter: Optional[AccountRateLimiter] = None


def get_account_rate_limiter() -> AccountRateLimiter:
    """Get the global account rate limiter instance."""
    global _account_rate_limiter
    if _account_rate_limiter is None:
        _account_rate_limiter = AccountRateLimiter()
    return _account_rate_limiter
