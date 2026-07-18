#!/usr/bin/env python3
"""
analyzr  –  Natural-language transaction search for Union Bank (CLI).

Usage:
    python scripts/analyzr.py "show me all deposits over 500 last month" --account 1000000001
    python scripts/analyzr.py "find large withdrawals" --account 1000000001
    python scripts/analyzr.py "what did I spend on food this month?" --account 1000000001
    python scripts/analyzr.py list-queries

The core search logic lives in src/unionbank/utils/analyzr_core.py.
This script is just the CLI entry point.
"""

from __future__ import annotations

import json

# The unionbank package is installed via pip install -e ., so all
# imports use the unionbank. prefix. No sys.path manipulation needed.
from unionbank.utils.analyzr_core import (
    execute_query,
    INTENT_PATTERNS,
)


def _format_results(results: list, query: str) -> str:
    """Format transaction results as a terminal table."""
    lines = []
    lines.append(f"\n  {'─' * 70}")
    lines.append(f"  Query: {query}")
    lines.append(f"  Results: {len(results)} transaction(s) found")
    lines.append(f"  {'─' * 70}")

    if not results:
        lines.append("  No transactions match your query.")
        lines.append(f"  {'─' * 70}\n")
        return "\n".join(lines)

    lines.append(
        f"  {'ID':<14} {'Date':<22} {'Type':<14} {'Amount':>10} {'Category':<16}"
    )
    lines.append(f"  {'─' * 70}")

    for txn in results:
        amt_str = (
            f"+{float(txn['amount']):>8.2f}"
            if txn["type"] in ("DEPOSIT", "TRANSFER_IN")
            else f"-{float(txn['amount']):>8.2f}"
        )
        lines.append(
            f"  {txn['txn_id']:<14} {txn['date']:<22} {txn['type']:<14} {amt_str} {txn['category']:<16}"
        )

    lines.append(f"  {'─' * 70}")
    lines.append("")
    return "\n".join(lines)


def _print_results(formatted: str, query: str, intents: list[str]) -> None:
    """Print formatted results to stdout."""
    try:
        from colorama import init, Fore, Style
        init()
        CYAN = Fore.CYAN
        YELLOW = Fore.YELLOW
        RESET = Style.RESET_ALL
    except ImportError:
        CYAN = YELLOW = RESET = ""

    print(f"\n  {CYAN}╔════════════════════════════════════════════╗{RESET}")
    print(f"  {CYAN}║       🔍  Analyzr — Query Engine         ║{RESET}")
    print(f"  {CYAN}╚════════════════════════════════════════════╝{RESET}")
    if intents:
        print(f"  {YELLOW}Detected intent(s):{RESET} {', '.join(intents)}")
    print(formatted)


def list_queries() -> None:
    """Print all supported query patterns."""
    try:
        from colorama import init, Fore, Style
        init()
        H = Fore.CYAN
        D = Fore.WHITE
        R = Style.RESET_ALL
    except ImportError:
        H = D = R = ""

    print(f"\n  {H}══════════════════════════════════════════════════════{R}")
    print(f"  {H}  Supported Query Patterns (analyzr){R}")
    print(f"  {H}══════════════════════════════════════════════════════{R}\n")

    for intent in INTENT_PATTERNS:
        if intent["name"] == "general_search":
            continue
        print(f"  {D}{intent['description']}{R}")
        print(f"      patterns: {', '.join(f'\"{p}\"' for p in intent['patterns'][:3])}")
        if intent.get("type_filter"):
            print(f"      filters: {', '.join(intent['type_filter'])}")
        print()

    print(f"\n  {H}Examples:{R}")
    print('    python scripts/analyzr.py "show me large deposits" --account 1000000001')
    print('    python scripts/analyzr.py "what did I spend on food last month" --account 1000000001')
    print('    python scripts/analyzr.py "find suspicious transactions" --account 1000000001')
    print('    python scripts/analyzr.py list-queries')


def main() -> None:
    """Main entry point for the analyzr CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="🔍 Analyzr — Natural-language transaction search for Union Bank",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/analyzr.py "show all deposits over 500" --account 1000000001
  python scripts/analyzr.py "what did I spend on food this month?" --account 1000000001
  python scripts/analyzr.py list-queries
        """,
    )
    parser.add_argument("query", nargs="?", help="Natural-language query")
    parser.add_argument("--account", "-a", help="Account number to search")
    parser.add_argument("--max", type=int, default=50, help="Maximum results (default: 50)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--list-queries", "-l", action="store_true",
                        help="List all supported query patterns and exit")
    args = parser.parse_args()

    if args.query == "list-queries" or args.list_queries:
        list_queries()
        return

    if not args.query:
        parser.print_help()
        return

    # Execute the query via the core engine
    result = execute_query(
        query=args.query,
        account_number=args.account,
        max_results=args.max,
    )

    # Format and print
    formatted = _format_results(result.get("results", []), args.query)
    _print_results(formatted, args.query, result.get("intent", []))

    # JSON output if requested
    if args.json:
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
