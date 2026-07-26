"""
utils/analyzr_core.py  –  Natural-language transaction search engine.

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

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

#  Intent Recognition

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
        "descrip