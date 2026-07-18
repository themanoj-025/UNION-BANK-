"""
categories.py  –  Transaction category selection (CLI helper).

Extracted from the old utils/auth.py god module.
"""

from unionbank.config import settings

TRANSACTION_CATEGORIES = settings.TRANSACTION_CATEGORIES


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
