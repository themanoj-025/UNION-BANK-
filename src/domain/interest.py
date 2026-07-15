"""
interest.py  –  Interest calculation (domain-level pure function).

Extracted from the old utils/auth.py god module.
Moved here because it's a domain computation, not a utility.
"""

from config import settings

SAVINGS_INTEREST_RATE = settings.SAVINGS_INTEREST_RATE


def calculate_monthly_interest(balance: float) -> float:
    """
    Calculate monthly interest on a balance.
    Uses SAVINGS_INTEREST_RATE % per annum, compounded monthly.
    Returns the interest amount.
    """
    monthly_rate = SAVINGS_INTEREST_RATE / 12 / 100
    return round(balance * monthly_rate, 2)
