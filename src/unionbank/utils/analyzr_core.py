"""utils/analyzr_core.py  –  Natural-language transaction search engine.

This module contains the core parsing and search logic for analyzr.
It is importable from the unionbank package (unlike scripts/analyzr.py
which is a CLI wrapper only).

Architecture:
    1. classify_intent()     — regex pattern matching → intent detection
    2. extract_amount_range() — amount extraction (over/under/between)
    3. compute_time_window()  — date range calculation
    4. execute_query()        — orchestrates the pipeline with DB-backed search

Design constraints:
    - No external API calls → zero latency, zero cost, works offline
    - Deterministic → same query always produces same result
    - Composable → patterns combine (e.g. "large deposits in March")
    - Extensible → add new intents by adding entries to INTENT_PATTERNS
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
#  Intent Recognition
# ──────────────────────────────────────────────────────────────────────────────

# Each intent has: keywords, type filter, time window, amount qualifier
# Order matters — first match wins (most specific patterns first)

INTENT_PATTERNS = [
    # ── Specific transaction type + amount qualifier ─────────────────────────
    {
        "name": "large_deposits",
        "patterns": [
            r"large\s+deposits?", r"big\s+deposits?", r"deposits?\s+over",
            r"high\s+deposits?", r"significant\s+deposits?",
        ],
        "type_filter": ["DEPOSIT"],
        "amount_qualifier": "large",
        "description": "Find large/notable deposits",
    },
    {
        "name": "large_withdrawals",
        "patterns": [
            r"large\s+withdrawals?", r"big\s+withdrawals?",
            r"withdrawals?\s+over", r"high\s+withdrawals?",
            r"significant\s+withdrawals?",
        ],
        "type_filter": ["WITHDRAW"],
        "amount_qualifier": "large",
        "description": "Find large/notable withdrawals",
    },
    {
        "name": "small_deposits",
        "patterns": [r"small\s+deposits?", r"tiny\s+deposits?", r"deposits?\s+under"],
        "type_filter": ["DEPOSIT"],
        "amount_qualifier": "small",
        "description": "Find small deposits",
    },
    # ── Category-based ───────────────────────────────────────────────────────
    {
        "name": "food_spending",
        "patterns": [
            r"spen[dts].*food", r"food.*spen[dt]", r"food.*dining",
            r"restaurant", r"eating\s+out", r"grocer",
            r"what.*(spend|spent).*food",
        ],
        "type_filter": ["WITHDRAW", "TRANSFER_OUT"],
        "category_filter": ["Food & Dining", "Groceries"],
        "description": "Find food and dining-related spending",
    },
    {
        "name": "salary_deposits",
        "patterns": [
            r"salary", r"payroll", r"pay\s+deposit", r"income",
            r"wage", r"paycheck",
        ],
        "type_filter": ["DEPOSIT"],
        "category_filter": ["Salary"],
        "description": "Find salary/payroll deposits",
    },
    {
        "name": "bills",
        "patterns": [
            r"bills?", r"utility", r"electricity", r"water.*bill",
            r"phone.*bill", r"internet.*bill", r"rent",
            r"emi", r"loan.*payment",
        ],
        "type_filter": ["WITHDRAW", "TRANSFER_OUT"],
        "category_filter": ["Bills & Utilities", "Rent", "Loan"],
        "description": "Find bill payments and utility charges",
    },
    {
        "name": "entertainment",
        "patterns": [
            r"entertainment", r"movies?", r"streaming", r"netflix",
            r"spotify", r"games?", r"gaming", r"recreation",
        ],
        "type_filter": ["WITHDRAW", "TRANSFER_OUT"],
        "category_filter": ["Entertainment"],
        "description": "Find entertainment-related spending",
    },
    {
        "name": "shopping",
        "patterns": [
            r"shopp", r"purchase", r"online.*buy", r"amazon",
            r"flipkart", r"retail", r"cloth",
        ],
        "type_filter": ["WITHDRAW", "TRANSFER_OUT"],
        "category_filter": ["Shopping"],
        "description": "Find shopping and retail purchases",
    },
    # ── Time-based ───────────────────────────────────────────────────────────
    {
        "name": "this_month",
        "patterns": [
            r"this\s+month", r"current\s+month", r"this\s+month['\u2019]s",
        ],
        "time_window": "this_month",
        "description": "Show transactions from the current calendar month",
    },
    {
        "name": "last_month",
        "patterns": [
            r"last\s+month", r"previous\s+month",
        ],
        "time_window": "last_month",
        "description": "Show transactions from the previous calendar month",
    },
    {
        "name": "this_week",
        "patterns": [
            r"this\s+week", r"current\s+week", r"past\s+7\s+days?",
            r"last\s+7\s+days?",
        ],
        "time_window": "this_week",
        "description": "Show transactions from the current calendar week",
    },
    {
        "name": "last_week",
        "patterns": [
            r"last\s+week", r"previous\s+week",
        ],
        "time_window": "last_week",
        "description": "Show transactions from the previous calendar week",
    },
    {
        "name": "today",
        "patterns": [
            r"todays?", r"today['\u2019]s", r"today",
        ],
        "time_window": "today",
        "description": "Show today's transactions",
    },
    {
        "name": "yesterday",
        "patterns": [
            r"yesterday['\u2019]s?", r"yesterday",
        ],
        "time_window": "yesterday",
        "description": "Show yesterday's transactions",
    },
    # ── Anomaly / Suspicious ─────────────────────────────────────────────────
    {
        "name": "suspicious",
        "patterns": [
            r"suspicious", r"unusual", r"anomal", r"fraud",
            r"unauthorized", r"unknown.*transact", r"unrecognized",
        ],
        "type_filter": None,  # All types
        "amount_qualifier": "large",
        "time_window": "last_90_days",
        "description": "Search for potentially suspicious transactions",
    },
    {
        "name": "transfers_sent",
        "patterns": [
            r"transfers?\s+sent", r"sent\s+transfers?", r"outgoing\s+transfers?",
            r"money\s+sent", r"sent\s+money",
        ],
        "type_filter": ["TRANSFER_OUT"],
        "description": "Find outgoing transfers",
    },
    {
        "name": "transfers_received",
        "patterns": [
            r"transfers?\s+received", r"received\s+transfers?",
            r"incoming\s+transfers?", r"money\s+received",
            r"received\s+money",
        ],
        "type_filter": ["TRANSFER_IN"],
        "description": "Find incoming transfers",
    },
    {
        "name": "all_deposits",
        "patterns": [
            r"all\s+deposits?", r"show\s+deposits?", r"list\s+deposits?",
            r"deposits?\s+only",
        ],
        "type_filter": ["DEPOSIT"],
        "description": "Show all deposits",
    },
    {
        "name": "all_withdrawals",
        "patterns": [
            r"all\s+withdrawals?", r"show\s+withdrawals?", r"list\s+withdrawals?",
            r"withdrawals?\s+only",
        ],
        "type_filter": ["WITHDRAW"],
        "description": "Show all withdrawals",
    },
    {
        "name": "general_search",
        "patterns": [
            r".*",  # Catch-all — matches anything
        ],
        "description": "General transaction search (catch-all)",
    },
]

# Amount thresholds
LARGE_AMOUNT_MULTIPLIER = 5
SMALL_AMOUNT_MULTIPLIER = 0.5


def _compute_average_txn_amount(txns: list) -> Decimal:
    """Compute the average transaction amount from a list of transactions."""
    if not txns:
        return Decimal("500.00")
    total = sum(
        (Decimal(str(t.amount)) if not isinstance(t.amount, Decimal) else t.amount)
        for t in txns
    )
    return total / len(txns)


def classify_intent(query: str) -> list[dict]:
    """Classify a natural-language query into one or more intents."""
    query_lower = query.lower().strip()
    matched = []

    for intent in INTENT_PATTERNS:
        for pattern in intent["patterns"]:
            if re.search(pattern, query_lower):
                matched.append(intent)
                break

    return matched


def extract_amount_range(query: str, intents: list[dict]) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """Extract min/max amount from a natural-language query."""
    min_amt, max_amt = None, None

    amount_patterns = [
        (r"(?:over|more\s+than|above|greater\s+than|exceeding|>)\s*[₹$]?\s*(\d[\d,.]*)", "min"),
        (r"(?:under|less\s+than|below|up\s+to|<)\s*[₹$]?\s*(\d[\d,.]*)", "max"),
        (r"(?:between)\s*[₹$]?\s*(\d[\d,.]*)\s*(?:and|-|to)\s*[₹$]?\s*(\d[\d,.]*)", "range"),
        (r"[₹$]\s?(\d[\d,.]*)", "exact"),
    ]

    for pattern, kind in amount_patterns:
        match = re.search(pattern, query.lower())
        if match:
            if kind == "min":
                min_amt = Decimal(match.group(1).replace(",", ""))
            elif kind == "max":
                max_amt = Decimal(match.group(1).replace(",", ""))
            elif kind == "range":
                min_amt = Decimal(match.group(1).replace(",", ""))
                max_amt = Decimal(match.group(2).replace(",", ""))
            elif kind == "exact" and min_amt is None and max_amt is None:
                val = Decimal(match.group(1).replace(",", ""))
                min_amt = val
                max_amt = val

    return min_amt, max_amt


def compute_time_window(intents: list[dict]) -> tuple[Optional[datetime], Optional[datetime]]:
    """Compute from_date/to_date from matched time-window intents."""
    now = datetime.now(timezone.utc)
    from_date, to_date = None, None

    for intent in intents:
        tw = intent.get("time_window")
        if tw == "today":
            from_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif tw == "yesterday":
            yesterday = now - timedelta(days=1)
            from_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif tw == "this_week":
            from_date = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif tw == "last_week":
            last_monday = now - timedelta(days=now.weekday() + 7)
            from_date = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = (last_monday + timedelta(days=7)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif tw == "this_month":
            from_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif tw == "last_month":
            first_of_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            from_date = (first_of_this - timedelta(days=1)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            to_date = first_of_this
        elif tw == "last_90_days":
            from_date = now - timedelta(days=90)

    return from_date, to_date


# ──────────────────────────────────────────────────────────────────────────────
#  Query Execution
# ──────────────────────────────────────────────────────────────────────────────


def execute_query(
    query: str,
    account_number: Optional[str] = None,
    max_results: int = 50,
) -> dict:
    """Execute a natural-language transaction search query.

    Args:
        query: Natural language query string.
        account_number: Optional account number to scope the search.
        max_results: Maximum number of results to return.

    Returns:
        dict with keys: query, intent, filters, total, results

    """
    from unionbank.infrastructure.container import get_container

    # Classify intent
    intents = classify_intent(query)
    intent_names = [i["name"] for i in intents]

    # Build filter parameters
    txn_types = set()
    categories = set()
    has_amount_qualifier = False

    for intent in intents:
        if intent.get("type_filter"):
            txn_types.update(intent["type_filter"])
        if intent.get("category_filter"):
            categories.update(intent["category_filter"])
        if intent.get("amount_qualifier"):
            has_amount_qualifier = True

    type_filter = list(txn_types) if txn_types else None
    category_filter = list(categories) if categories else None

    # Extract amount range
    min_amount, max_amount = extract_amount_range(query, intents)

    # Compute time window
    from_date, to_date = compute_time_window(intents)

    # ── Fetch transactions via the service layer ────────────────────────────
    c = get_container()
    txn_service = c.transaction_service()

    if account_number:
        all_txns = txn_service.get_statement(account_number)
    else:
        from unionbank.utils.logger import logger
        logger.warning("analyzr: No account number provided — returning empty results")
        all_txns = []

    # ── Apply filters ───────────────────────────────────────────────────────
    results = []
    for txn in all_txns:
        # Type filter
        if type_filter and txn.type.value not in type_filter:
            continue

        # Category filter
        txn_cat = (txn.category or "General").lower()
        if category_filter and not any(
            cf.lower() in txn_cat for cf in category_filter
        ):
            continue

        # Date filter
        txn_ts = txn.timestamp
        if txn_ts and from_date:
            if txn_ts.tzinfo is None:
                txn_dt = txn_ts.replace(tzinfo=timezone.utc)
            else:
                txn_dt = txn_ts
            if txn_dt < from_date:
                continue
        if txn_ts and to_date:
            if txn_ts.tzinfo is None:
                txn_dt = txn_ts.replace(tzinfo=timezone.utc)
            else:
                txn_dt = txn_ts
            if txn_dt > to_date:
                continue

        # Amount qualifier
        if has_amount_qualifier and not min_amount and not max_amount:
            avg = _compute_average_txn_amount(all_txns)
            for intent in intents:
                if intent.get("amount_qualifier") == "large":
                    threshold = avg * LARGE_AMOUNT_MULTIPLIER
                    if Decimal(str(txn.amount)) < threshold:
                        continue
                elif intent.get("amount_qualifier") == "small":
                    threshold = avg * SMALL_AMOUNT_MULTIPLIER
                    if Decimal(str(txn.amount)) > threshold:
                        continue

        # Explicit amount range
        if min_amount is not None and Decimal(str(txn.amount)) < min_amount:
            continue
        if max_amount is not None and Decimal(str(txn.amount)) > max_amount:
            continue

        results.append(txn)

    # Sort by timestamp descending (most recent first)
    results.sort(key=lambda t: t.timestamp or datetime.min, reverse=True)
    results = results[:max_results]

    return {
        "query": query,
        "intent": intent_names,
        "filters": {
            "type_filter": type_filter,
            "category_filter": category_filter,
            "from_date": str(from_date) if from_date else None,
            "to_date": str(to_date) if to_date else None,
            "min_amount": str(min_amount) if min_amount else None,
            "max_amount": str(max_amount) if max_amount else None,
        },
        "total": len(results),
        "results": [
            {
                "txn_id": t.txn_id,
                "date": str(t.timestamp)[:19] if t.timestamp else "",
                "type": t.type.value,
                "amount": float(t.amount),
                "balance": float(t.balance),
                "description": t.description,
                "category": t.category or "General",
            }
            for t in results
        ],
    }
