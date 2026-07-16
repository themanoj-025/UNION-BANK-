"""domain/clock.py  –  Shared time utilities for the domain layer.

Provides a single source of truth for timezone-aware UTC timestamps,
eliminating the ``_utcnow()`` copy-paste that previously existed across
7+ files. All domain entities, application services, and infrastructure
code should import ``utcnow`` from here rather than defining their own.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    All timestamps in the system use timezone-aware UTC datetimes
    to ensure consistency across:
    - Domain entity creation timestamps
    - Service-layer operation timestamps (transactions, interest, loans)
    - Repository-layer audit trails
    - Rate-limiting lockout calculations

    Returns:
        A timezone-aware ``datetime`` set to the current UTC time.

    """
    return datetime.now(timezone.utc)
