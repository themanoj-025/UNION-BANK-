"""csv_export.py  –  CSV export for transaction statements.

Extracted from the old utils/auth.py god module.
"""

import csv
import os
from datetime import datetime


def export_transactions_to_csv(acc_no: str, records: list, filepath: str) -> str:
    """Export transaction records to a CSV file.
    Returns the filepath of the created file.
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Transaction ID", "Date/Time", "Type", "Amount", "Balance", "Description", "Category"])

        for t in records:
            sign = "+" if t["type"] in ("DEPOSIT", "TRANSFER_IN") else "-"
            amount_str = f"{sign}{t['amount']}"
            writer.writerow([
                t.get("txn_id", ""),
                t.get("timestamp", ""),
                t.get("type", ""),
                amount_str,
                t.get("balance", ""),
                t.get("description", ""),
                t.get("category", "General"),
            ])

    return filepath


def generate_csv_filename(acc_no: str) -> str:
    """Generate a default CSV export filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", f"statement_{acc_no}_{timestamp}.csv")
