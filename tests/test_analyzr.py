"""tests/test_analyzr.py  –  Unit tests for the analyzr natural-language search engine.

Tests every intent pattern, amount extraction format, time window calculation,
and edge case independently — without needing a database connection (uses fakes).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

# Import pure functions from analyzr_core (no DB bootstrap needed)
from unionbank.utils.analyzr_core import (
    INTENT_PATTERNS,
    LARGE_AMOUNT_MULTIPLIER,
    SMALL_AMOUNT_MULTIPLIER,
    _compute_average_txn_amount,
    classify_intent,
    compute_time_window,
    extract_amount_range,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  Intent Classification Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntentClassification:

    def test_intent_patterns_list_is_not_empty(self):
        """INTENT_PATTERNS should have at least 15 defined intents."""
        assert len(INTENT_PATTERNS) >= 15

    def test_all_intents_have_required_keys(self):
        """Every intent pattern must have name, patterns, and description."""
        for intent in INTENT_PATTERNS:
            assert "name" in intent, f"Intent missing 'name': {intent}"
            assert "patterns" in intent, f"Intent {intent['name']} missing 'patterns'"
            assert "description" in intent, f"Intent {intent['name']} missing 'description'"

    def test_classify_large_deposits(self):
        intents = classify_intent("show me large deposits")
        names = [i["name"] for i in intents]
        assert "large_deposits" in names

    def test_classify_big_deposits_synonym(self):
        intents = classify_intent("big deposits")
        names = [i["name"] for i in intents]
        assert "large_deposits" in names

    def test_classify_food_spending(self):
        intents = classify_intent("what did I spend on food")
        names = [i["name"] for i in intents]
        assert "food_spending" in names

    def test_classify_food_spending_restaurant(self):
        intents = classify_intent("restaurant expenses this month")
        names = [i["name"] for i in intents]
        assert "food_spending" in names

    def test_classify_salary(self):
        intents = classify_intent("salary deposits last month")
        names = [i["name"] for i in intents]
        assert "salary_deposits" in names

    def test_classify_bills(self):
        intents = classify_intent("show my utility bills")
        names = [i["name"] for i in intents]
        assert "bills" in names

    def test_classify_bills_emi(self):
        intents = classify_intent("EMI payments")
        names = [i["name"] for i in intents]
        assert "bills" in names

    def test_classify_entertainment(self):
        intents = classify_intent("netflix streaming charges")
        names = [i["name"] for i in intents]
        assert "entertainment" in names

    def test_classify_shopping(self):
        intents = classify_intent("amazon purchases")
        names = [i["name"] for i in intents]
        assert "shopping" in names

    def test_classify_time_this_month(self):
        intents = classify_intent("transactions this month")
        names = [i["name"] for i in intents]
        assert "this_month" in names

    def test_classify_time_last_month(self):
        intents = classify_intent("last month spending")
        names = [i["name"] for i in intents]
        assert "last_month" in names

    def test_classify_time_yesterday(self):
        intents = classify_intent("yesterday transactions")
        names = [i["name"] for i in intents]
        assert "yesterday" in names

    def test_classify_suspicious(self):
        intents = classify_intent("any suspicious transactions")
        names = [i["name"] for i in intents]
        assert "suspicious" in names

    def test_classify_fraud(self):
        intents = classify_intent("possible fraud on my account")
        names = [i["name"] for i in intents]
        assert "suspicious" in names

    def test_classify_transfers_sent(self):
        intents = classify_intent("money sent to others")
        names = [i["name"] for i in intents]
        assert "transfers_sent" in names

    def test_classify_transfers_received(self):
        intents = classify_intent("transfers received this month")
        names = [i["name"] for i in intents]
        assert "transfers_received" in names
        assert "this_month" in names  # Should also match time intent

    def test_classify_all_deposits(self):
        intents = classify_intent("show all deposits")
        names = [i["name"] for i in intents]
        assert "all_deposits" in names

    def test_classify_all_withdrawals(self):
        intents = classify_intent("list withdrawals only")
        names = [i["name"] for i in intents]
        assert "all_withdrawals" in names

    def test_classify_empty_string(self):
        """Empty string should match the catch-all general_search pattern (.*)."""
        intents = classify_intent("")
        names = [i["name"] for i in intents]
        assert "general_search" in names

    def test_classify_nonsense_string(self):
        """Nonsense text should still match the catch-all general_search."""
        intents = classify_intent("xylophone zebra quantum")
        names = [i["name"] for i in intents]
        assert "general_search" in names

    def test_classify_multiple_intents(self):
        """A query should match multiple intents if relevant."""
        intents = classify_intent("show large deposits and suspicious activity last month")
        names = [i["name"] for i in intents]
        assert "large_deposits" in names
        assert "suspicious" in names
        assert "last_month" in names

    def test_case_insensitivity(self):
        """Intent classification should be case-insensitive."""
        intents = classify_intent("LARGE DEPOSITS LAST MONTH")
        names = [i["name"] for i in intents]
        assert "large_deposits" in names
        assert "last_month" in names

    def test_whitespace_handling(self):
        """Leading/trailing whitespace should not affect classification."""
        intents = classify_intent("  show me large deposits  ")
        names = [i["name"] for i in intents]
        assert "large_deposits" in names

    def test_intent_description_is_human_readable(self):
        """Every intent description should be a readable sentence."""
        for intent in INTENT_PATTERNS:
            desc = intent["description"]
            assert len(desc) > 5, f"Intent {intent['name']} has too-short description"
            assert desc[0].isupper(), f"Intent {intent['name']} description should start uppercase"


# ═══════════════════════════════════════════════════════════════════════════════
#  Amount Extraction Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAmountExtraction:

    def test_extract_over_amount(self):
        """'over 500' should extract min=500."""
        min_amt, max_amt = extract_amount_range("transactions over 500", [])
        assert min_amt == Decimal("500")
        assert max_amt is None

    def test_extract_more_than_amount(self):
        min_amt, max_amt = extract_amount_range("more than 1000 rupees", [])
        assert min_amt == Decimal("1000")
        assert max_amt is None

    def test_extract_under_amount(self):
        min_amt, max_amt = extract_amount_range("transactions under 200", [])
        assert min_amt is None
        assert max_amt == Decimal("200")

    def test_extract_less_than_amount(self):
        min_amt, max_amt = extract_amount_range("less than 50 dollars", [])
        assert min_amt is None
        assert max_amt == Decimal("50")

    def test_extract_between_range(self):
        min_amt, max_amt = extract_amount_range("between 100 and 500 rupees", [])
        assert min_amt == Decimal("100")
        assert max_amt == Decimal("500")

    def test_extract_between_with_dash(self):
        min_amt, max_amt = extract_amount_range("between 100-500", [])
        assert min_amt == Decimal("100")
        assert max_amt == Decimal("500")

    def test_extract_currency_symbol_inr(self):
        min_amt, max_amt = extract_amount_range("deposits over ₹1000", [])
        assert min_amt == Decimal("1000")

    def test_extract_currency_symbol_usd(self):
        min_amt, max_amt = extract_amount_range("over $500", [])
        assert min_amt == Decimal("500")

    def test_extract_exact_amount(self):
        min_amt, max_amt = extract_amount_range("show me the ₹250 transaction", [])
        assert min_amt == Decimal("250")
        assert max_amt == Decimal("250")

    def test_extract_no_amount_mentions(self):
        """Query with no amount mentions should return None for both."""
        min_amt, max_amt = extract_amount_range("show all deposits this month", [])
        assert min_amt is None
        assert max_amt is None

    def test_extract_with_commas(self):
        """Amounts with comma separators should be parsed correctly."""
        min_amt, max_amt = extract_amount_range("transactions over 1,000", [])
        assert min_amt == Decimal("1000")

    def test_extract_range_with_category(self):
        """Amount range extraction should work alongside category intent."""
        intents = classify_intent("food spending over 500")
        min_amt, max_amt = extract_amount_range("food spending over 500", intents)
        assert min_amt == Decimal("500")
        assert max_amt is None
        names = [i["name"] for i in intents]
        assert "food_spending" in names

    def test_extract_range_and_time_together(self):
        """Amount and time extraction should both work from a single query."""
        intents = classify_intent("transactions over 1000 last month")
        min_amt, max_amt = extract_amount_range("transactions over 1000 last month", intents)
        assert min_amt == Decimal("1000")
        assert max_amt is None
        names = [i["name"] for i in intents]
        assert "last_month" in names

    def test_extract_greater_than(self):
        min_amt, max_amt = extract_amount_range("greater than 750", [])
        assert min_amt == Decimal("750")


# ═══════════════════════════════════════════════════════════════════════════════
#  Time Window Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTimeWindow:

    def test_time_today(self):
        intents = [{"name": "today", "time_window": "today"}]
        from_date, to_date = compute_time_window(intents)
        assert from_date is not None
        assert to_date is None  # today has no to_date bound
        now = datetime.now(timezone.utc)
        assert from_date.day == now.day
        assert from_date.month == now.month
        assert from_date.year == now.year
        assert from_date.hour == 0
        assert from_date.minute == 0

    def test_time_yesterday(self):
        intents = [{"name": "yesterday", "time_window": "yesterday"}]
        from_date, to_date = compute_time_window(intents)
        assert from_date is not None
        assert to_date is not None
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        assert from_date.day == yesterday.day
        assert from_date.hour == 0

    def test_time_this_month(self):
        intents = [{"name": "this_month", "time_window": "this_month"}]
        from_date, to_date = compute_time_window(intents)
        assert from_date is not None
        assert to_date is None
        assert from_date.day == 1  # First day of month
        assert from_date.hour == 0
        assert from_date.minute == 0

    def test_time_this_week(self):
        intents = [{"name": "this_week", "time_window": "this_week"}]
        from_date, to_date = compute_time_window(intents)
        assert from_date is not None
        assert to_date is None
        # Should be a Monday
        assert from_date.weekday() == 0  # Monday
        assert from_date.hour == 0

    def test_time_last_90_days(self):
        intents = [{"name": "suspicious", "time_window": "last_90_days"}]
        from_date, to_date = compute_time_window(intents)
        assert from_date is not None
        assert to_date is None
        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=90)
        assert abs((from_date - expected).total_seconds()) < 1  # Within 1 second

    def test_no_time_intents(self):
        from_date, to_date = compute_time_window([])
        assert from_date is None
        assert to_date is None

    def test_time_unknown_window(self):
        intents = [{"name": "custom", "time_window": "unknown_window"}]
        from_date, to_date = compute_time_window(intents)
        assert from_date is None
        assert to_date is None


# ═══════════════════════════════════════════════════════════════════════════════
#  Average Amount Computation Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAverageAmount:

    def test_empty_list_uses_default(self):
        """Empty transaction list should use the default fallback of 500."""
        avg = _compute_average_txn_amount([])
        assert avg == Decimal("500.00")

    def test_single_transaction(self):
        """Single transaction should return its amount."""
        from collections import namedtuple
        MockTxn = namedtuple("MockTxn", ["amount"])
        txns = [MockTxn(amount=Decimal("250.00"))]
        avg = _compute_average_txn_amount(txns)
        assert avg == Decimal("250.00")

    def test_multiple_transactions(self):
        """Multiple transactions should return the arithmetic mean."""
        from collections import namedtuple
        MockTxn = namedtuple("MockTxn", ["amount"])
        txns = [
            MockTxn(amount=Decimal("100.00")),
            MockTxn(amount=Decimal("200.00")),
            MockTxn(amount=Decimal("300.00")),
        ]
        avg = _compute_average_txn_amount(txns)
        assert avg == Decimal("200.00")

    def test_decimal_precision_preserved(self):
        """Decimal precision should be preserved in average calculation."""
        from collections import namedtuple
        MockTxn = namedtuple("MockTxn", ["amount"])
        txns = [MockTxn(amount=Decimal("100.50")), MockTxn(amount=Decimal("200.75"))]
        avg = _compute_average_txn_amount(txns)
        assert avg == Decimal("150.625")


# ═══════════════════════════════════════════════════════════════════════════════
#  Constants Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestConstants:

    def test_large_amount_multiplier(self):
        assert LARGE_AMOUNT_MULTIPLIER == 5  # 5x average

    def test_small_amount_multiplier(self):
        assert SMALL_AMOUNT_MULTIPLIER == 0.5  # 0.5x average
