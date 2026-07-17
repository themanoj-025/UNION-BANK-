"""interest.py  –  Interest calculation (domain-level pure function).

Extracted from the old utils/auth.py god module.
Moved here because it's a domain computation, not a utility.

This module has ZERO imports outside domain/ and stdlib.
Configuration (interest rate) is passed as a parameter.
"""


def calculate_monthly_interest(balance: float, annual_rate_pct: float = 3.5) -> float:
    """Calculate monthly interest on a balance.

    Args:
        balance: The account balance to calculate interest on.
        annual_rate_pct: Annual interest rate in percent (default 3.5%% p.a.).

    Returns:
        The monthly interest amount, rounded to 2 decimal places.

    Formula: interest = balance * (annual_rate / 12 / 100)
    """
    monthly_rate = annual_rate_pct / 12 / 100
    return round(balance * monthly_rate, 2)
