"""
services.py  –  Service layer for Union Bank.

Extracts duplicated business logic from account.py, webapp.py, api.py,
and admin.py into a single shared layer. All three interfaces call these
service functions instead of duplicating the same logic.

Each service function handles the complete operation including:
  - Business rule validation
  - SQLite atomic operations where needed
  - JSON file persistence for backward compatibility
  - Transaction logging
  - Error handling and logging
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from logger import logger
from utils import (
    load_json, save_json, generate_transaction_id, now_str, fmt_currency,
    calculate_monthly_interest, verify_password, hash_password,
    validate_email, validate_phone, validate_name, TRANSACTION_CATEGORIES,
    load_goals, save_goals, generate_goal_id,
    ACCOUNTS_FILE, TRANSACTIONS_FILE, ADMIN_FILE,
)
from database import (
    atomic_transfer, atomic_apply_interest, atomic_close_account,
    sync_account_from_json, close_session as db_close_session,
)
from config import settings


# ═══════════════════════════════════════════════════════════════════════════════
#  Result types
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TransferResult:
    success: bool
    sender_balance: float = 0.0
    receiver_balance: float = 0.0
    error_message: str = ""


@dataclass
class ServiceResult:
    success: bool
    message: str = ""
    data: Optional[dict] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Account helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _get_account_dict(acc_no: str) -> Optional[dict]:
    """Load a single account dict, or None if not found."""
    accounts = load_json(ACCOUNTS_FILE)
    return accounts.get(acc_no)


def _save_account_dict(acc_no: str, data: dict) -> None:
    """Save/update a single account in the JSON store."""
    accounts = load_json(ACCOUNTS_FILE)
    accounts[acc_no] = data
    save_json(ACCOUNTS_FILE, accounts)


def _log_transaction(acc_no: str, balance: float, txn_type: str,
                     amount: float, description: str,
                     category: str = "General",
                     target_acc: Optional[str] = None) -> str:
    """Log a transaction record to the JSON transaction store."""
    txns = load_json(TRANSACTIONS_FILE)
    if acc_no not in txns:
        txns[acc_no] = []
    txn_id = generate_transaction_id()
    record = {
        "txn_id": txn_id,
        "type": txn_type,
        "amount": amount,
        "description": description,
        "balance": balance,
        "timestamp": now_str(),
        "category": category or "General",
    }
    if target_acc:
        record["target_account"] = target_acc
    txns[acc_no].append(record)
    save_json(TRANSACTIONS_FILE, txns)
    logger.info(
        f"TXN [{txn_id}]  {txn_type:<14}  Acc:{acc_no}  "
        f"Amt:{fmt_currency(amount)}  Bal:{fmt_currency(balance)}"
        + (f"  -> {target_acc}" if target_acc else "")
    )
    return txn_id


# ═══════════════════════════════════════════════════════════════════════════════
#  Customer operations
# ═══════════════════════════════════════════════════════════════════════════════

def process_deposit(acc_no: str, amount: float,
                    category: str = "General") -> ServiceResult:
    """Deposit money into an account."""
    if amount <= 0:
        return ServiceResult(success=False, message="Amount must be positive.")

    accounts = load_json(ACCOUNTS_FILE)
    if acc_no not in accounts:
        return ServiceResult(success=False, message="Account not found.")

    data = accounts[acc_no]
    if data.get("is_frozen", False):
        return ServiceResult(success=False, message="Account is frozen.")
    if not data.get("is_active", True):
        return ServiceResult(success=False, message="Account is closed.")

    cat = category if category in TRANSACTION_CATEGORIES else "General"
    data["balance"] += amount
    _save_account_dict(acc_no, data)
    _log_transaction(acc_no, data["balance"], "DEPOSIT", amount,
                     "Deposit", category=cat)

    logger.info(f"Deposit -> Acc:{acc_no} Amt:{fmt_currency(amount)}")
    return ServiceResult(
        success=True,
        message=f"{fmt_currency(amount)} deposited successfully. "
                f"New balance: {fmt_currency(data['balance'])}",
        data={"balance": data["balance"], "balance_formatted": fmt_currency(data["balance"])},
    )


def process_withdraw(acc_no: str, amount: float,
                     category: str = "General") -> ServiceResult:
    """Withdraw money from an account."""
    if amount <= 0:
        return ServiceResult(success=False, message="Amount must be positive.")

    accounts = load_json(ACCOUNTS_FILE)
    if acc_no not in accounts:
        return ServiceResult(success=False, message="Account not found.")

    data = accounts[acc_no]
    if data.get("is_frozen", False):
        return ServiceResult(success=False, message="Account is frozen.")
    if not data.get("is_active", True):
        return ServiceResult(success=False, message="Account is closed.")

    if amount > data["balance"]:
        logger.warning(
            f"Insufficient balance -> Acc:{acc_no}  "
            f"Requested:{fmt_currency(amount)}  Available:{fmt_currency(data['balance'])}"
        )
        return ServiceResult(
            success=False,
            message=f"Insufficient balance. Available: {fmt_currency(data['balance'])}",
        )

    cat = category if category in TRANSACTION_CATEGORIES else "General"
    data["balance"] -= amount
    _save_account_dict(acc_no, data)
    _log_transaction(acc_no, data["balance"], "WITHDRAW", amount,
                     "Withdrawal", category=cat)

    logger.info(f"Withdraw -> Acc:{acc_no} Amt:{fmt_currency(amount)}")
    return ServiceResult(
        success=True,
        message=f"{fmt_currency(amount)} withdrawn successfully. "
                f"New balance: {fmt_currency(data['balance'])}",
        data={"balance": data["balance"], "balance_formatted": fmt_currency(data["balance"])},
    )


def process_transfer(sender_acc_no: str, receiver_acc_no: str,
                     amount: float, category: str = "General",
                     sender_name_hint: str = "",
                     receiver_name_hint: str = "") -> TransferResult:
    """Transfer funds atomically between two accounts.

    Uses SQLite ACID transaction to guarantee money is never lost.
    Falls back to JSON sync for backward compatibility.
    """
    if amount <= 0:
        return TransferResult(success=False, error_message="Amount must be positive.")

    accounts = load_json(ACCOUNTS_FILE)

    if sender_acc_no not in accounts:
        return TransferResult(success=False, error_message="Sender account not found.")
    if receiver_acc_no not in accounts:
        return TransferResult(success=False, error_message="Recipient account not found.")
    if sender_acc_no == receiver_acc_no:
        return TransferResult(success=False, error_message="Cannot transfer to your own account.")

    sender_data = accounts[sender_acc_no]
    receiver_data = accounts[receiver_acc_no]

    if sender_data.get("is_frozen", False):
        return TransferResult(success=False, error_message="Your account is frozen.")
    if not sender_data.get("is_active", True):
        return TransferResult(success=False, error_message="Your account is closed.")
    if receiver_data.get("is_frozen", False):
        return TransferResult(success=False, error_message="Recipient account is frozen.")
    if not receiver_data.get("is_active", True):
        return TransferResult(success=False, error_message="Recipient account is closed.")

    if amount > sender_data["balance"]:
        logger.warning(
            f"Transfer insufficient -> From:{sender_acc_no}  "
            f"Req:{fmt_currency(amount)}  Avail:{fmt_currency(sender_data['balance'])}"
        )
        return TransferResult(
            success=False,
            error_message=f"Insufficient balance. Available: {fmt_currency(sender_data['balance'])}",
        )

    cat = category if category in TRANSACTION_CATEGORIES else "General"

    # ── Sync to SQLite for atomic operation ─────────────────────────────
    sync_account_from_json(sender_acc_no, sender_data)
    sync_account_from_json(receiver_acc_no, receiver_data)

    result = atomic_transfer(
        sender_acc_no=sender_acc_no,
        receiver_acc_no=receiver_acc_no,
        amount=amount,
        category=cat,
        sender_name=sender_name_hint or sender_data.get("name", ""),
        receiver_name=receiver_name_hint or receiver_data.get("name", ""),
    )

    if not result.success:
        logger.warning(f"Atomic transfer failed: {result.error_message}")
        return result

    # ── Sync SQLite result back to JSON ─────────────────────────────────
    accounts = load_json(ACCOUNTS_FILE)
    if sender_acc_no in accounts:
        accounts[sender_acc_no]["balance"] = result.sender_balance
    if receiver_acc_no in accounts:
        accounts[receiver_acc_no]["balance"] = result.receiver_balance
    save_json(ACCOUNTS_FILE, accounts)

    # ── Log transactions in JSON store ───────────────────────────────────
    _log_transaction(
        sender_acc_no, result.sender_balance,
        "TRANSFER_OUT", amount,
        f"Transfer to {receiver_acc_no} (atomic)",
        target_acc=receiver_acc_no, category=cat,
    )
    _log_transaction(
        receiver_acc_no, result.receiver_balance,
        "TRANSFER_IN", amount,
        f"Transfer from {sender_acc_no} (atomic)",
        target_acc=sender_acc_no, category=cat,
    )

    logger.info(
        f"Atomic transfer complete -> From:{sender_acc_no} "
        f"To:{receiver_acc_no} Amt:{fmt_currency(amount)}"
    )
    return result


def process_close_account(acc_no: str, password: str,
                          stored_password_hash: str) -> ServiceResult:
    """Close an account after password verification.

    Args:
        acc_no: Account to close
        password: Raw password to verify
        stored_password_hash: Stored bcrypt hash to verify against
    """
    if not verify_password(password, stored_password_hash):
        logger.warning(f"Close account failed (wrong password) -> Acc:{acc_no}")
        return ServiceResult(success=False, message="Incorrect password.")

    # Atomic closure in SQLite
    accounts = load_json(ACCOUNTS_FILE)
    if acc_no in accounts:
        accounts[acc_no]["is_active"] = False
        save_json(ACCOUNTS_FILE, accounts)
        sync_account_from_json(acc_no, accounts[acc_no])

    atomic_close_account(acc_no)
    db_close_session()

    logger.critical(f"Account CLOSED -> Acc:{acc_no}")
    return ServiceResult(success=True, message="Account closed successfully.")


def process_apply_interest(acc_no: str, balance: float) -> ServiceResult:
    """Apply monthly interest using an atomic SQLite transaction.

    Args:
        acc_no: Account number
        balance: Current balance from JSON store

    Returns:
        ServiceResult with interest amount in data if successful
    """
    interest = calculate_monthly_interest(balance)
    if interest <= 0:
        return ServiceResult(success=False, message="No interest to apply.")

    # Sync to SQLite then apply atomically
    accounts = load_json(ACCOUNTS_FILE)
    sync_account_from_json(acc_no, accounts.get(acc_no, {}))

    if not atomic_apply_interest(acc_no, interest):
        return ServiceResult(success=False, message="Failed to apply interest.")

    # Update JSON store
    if acc_no in accounts:
        accounts[acc_no]["balance"] += interest
        save_json(ACCOUNTS_FILE, accounts)

    # Log transaction
    new_balance = (accounts.get(acc_no, {})).get("balance", balance + interest)
    _log_transaction(acc_no, new_balance, "INTEREST", interest,
                     "Monthly interest credit", category="Savings")

    logger.info(f"Interest applied -> Acc:{acc_no} Amt:{fmt_currency(interest)}")
    return ServiceResult(
        success=True,
        message=f"Interest of {fmt_currency(interest)} credited! "
                f"New balance: {fmt_currency(new_balance)}",
        data={"interest": interest, "balance": new_balance,
              "balance_formatted": fmt_currency(new_balance)},
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin operations
# ═══════════════════════════════════════════════════════════════════════════════

def get_bank_statistics() -> dict:
    """Compute bank-wide statistics from JSON data.

    Returns a dict with all summary metrics for dashboards and reports.
    """
    accounts = load_json(ACCOUNTS_FILE)
    txns = load_json(TRANSACTIONS_FILE)

    total_customers = len(accounts)
    active = sum(1 for a in accounts.values()
                 if a.get("is_active", True) and not a.get("is_frozen"))
    frozen = sum(1 for a in accounts.values() if a.get("is_frozen", False))
    closed = sum(1 for a in accounts.values()
                 if not a.get("is_active", True) and not a.get("is_frozen", False))
    total_balance = sum(a["balance"] for a in accounts.values())

    total_txns = sum(len(v) for v in txns.values())
    total_dep = sum(t["amount"] for v in txns.values()
                     for t in v if t["type"] == "DEPOSIT")
    total_with = sum(t["amount"] for v in txns.values()
                      for t in v if t["type"] == "WITHDRAW")
    total_trans = sum(t["amount"] for v in txns.values()
                       for t in v if t["type"] == "TRANSFER_OUT")

    # Category breakdown
    category_totals = {}
    for records in txns.values():
        for t in records:
            cat = t.get("category", "General")
            category_totals[cat] = category_totals.get(cat, 0) + abs(t["amount"])
    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_customers": total_customers,
        "active": active,
        "frozen": frozen,
        "closed": closed,
        "total_balance": total_balance,
        "total_balance_formatted": fmt_currency(total_balance),
        "total_dep": total_dep,
        "total_with": total_with,
        "total_trans": total_trans,
        "total_txns": total_txns,
        "sorted_categories": [{"name": c[0], "total": c[1]} for c in sorted_cats[:8]],
    }


def process_freeze_account(acc_no: str) -> ServiceResult:
    """Freeze a customer account (admin operation)."""
    accounts = load_json(ACCOUNTS_FILE)
    if acc_no not in accounts:
        return ServiceResult(success=False, message="Account not found.")

    acc = accounts[acc_no]
    if not acc.get("is_active", True) and not acc.get("is_frozen", False):
        return ServiceResult(success=False, message="Account is permanently closed.")

    if acc.get("is_frozen", False):
        return ServiceResult(success=False, message=f"Account {acc_no} is already frozen.")

    acc["is_frozen"] = True
    acc["is_active"] = False
    _save_account_dict(acc_no, acc)

    msg = f"Account {acc_no} ({acc['name']}) has been frozen."
    logger.critical(msg)
    return ServiceResult(success=True, message=msg)


def process_unfreeze_account(acc_no: str) -> ServiceResult:
    """Unfreeze a customer account (admin operation)."""
    accounts = load_json(ACCOUNTS_FILE)
    if acc_no not in accounts:
        return ServiceResult(success=False, message="Account not found.")

    acc = accounts[acc_no]
    if not acc.get("is_frozen", False):
        return ServiceResult(success=False, message=f"Account {acc_no} is not frozen.")

    acc["is_frozen"] = False
    acc["is_active"] = True
    _save_account_dict(acc_no, acc)

    msg = f"Account {acc_no} ({acc['name']}) has been unfrozen."
    logger.critical(msg)
    return ServiceResult(success=True, message=msg)


def process_delete_account(acc_no: str) -> ServiceResult:
    """Permanently delete a customer account and all its transactions (admin)."""
    accounts = load_json(ACCOUNTS_FILE)
    if acc_no not in accounts:
        return ServiceResult(success=False, message="Account not found.")

    acc_name = accounts[acc_no]["name"]
    del accounts[acc_no]
    save_json(ACCOUNTS_FILE, accounts)

    txns = load_json(TRANSACTIONS_FILE)
    if acc_no in txns:
        del txns[acc_no]
        save_json(TRANSACTIONS_FILE, txns)

    msg = f"Account {acc_no} ({acc_name}) has been deleted."
    logger.critical(msg)
    return ServiceResult(success=True, message=msg)


def admin_authenticate(username: str, password: str) -> ServiceResult:
    """Authenticate an admin user against the admin.json file."""
    from utils import verify_password as _verify

    creds = load_json(ADMIN_FILE)
    if username == creds.get("username", "") and _verify(password, creds.get("password", "")):
        return ServiceResult(success=True, data={"username": username})
    return ServiceResult(success=False, message="Invalid admin credentials.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings goals operations
# ═══════════════════════════════════════════════════════════════════════════════

def create_savings_goal(acc_no: str, name: str, target_amount: float,
                        target_date: str = "") -> ServiceResult:
    """Create a new savings goal for an account."""
    if not name or len(name) < 2:
        return ServiceResult(success=False, message="Goal name must be at least 2 characters.")
    if target_amount <= 0:
        return ServiceResult(success=False, message="Target amount must be positive.")

    goals = load_goals(acc_no)
    goal = {
        "goal_id": generate_goal_id(),
        "name": name,
        "target_amount": round(target_amount, 2),
        "current_amount": 0.0,
        "target_date": target_date,
        "created_at": now_str(),
        "is_completed": False,
    }
    goals.append(goal)
    save_goals(acc_no, goals)
    logger.info(f"Savings goal created -> Acc:{acc_no} Goal:{name}")
    return ServiceResult(success=True, message=f"Goal '{name}' created!", data=goal)


def contribute_to_goal(acc_no: str, goal_id: str, amount: float,
                       current_balance: float) -> ServiceResult:
    """Contribute money from account balance to a savings goal."""
    if amount <= 0:
        return ServiceResult(success=False, message="Amount must be positive.")
    if amount > current_balance:
        return ServiceResult(success=False, message="Insufficient balance.")

    goals = load_goals(acc_no)
    goal = next((g for g in goals if g["goal_id"] == goal_id), None)
    if not goal:
        return ServiceResult(success=False, message="Goal not found.")

    # Update account balance
    accounts = load_json(ACCOUNTS_FILE)
    if acc_no in accounts:
        accounts[acc_no]["balance"] -= amount
        save_json(ACCOUNTS_FILE, accounts)

    # Log transaction
    _log_transaction(acc_no, accounts[acc_no]["balance"] if acc_no in accounts else 0,
                     "TRANSFER_OUT", amount,
                     f"Savings goal: {goal['name']}", category="Savings")

    # Update goal
    for g in goals:
        if g["goal_id"] == goal_id:
            g["current_amount"] += amount
            if g["current_amount"] >= g["target_amount"]:
                g["is_completed"] = True
            break

    save_goals(acc_no, goals)
    logger.info(f"Goal contribution -> Acc:{acc_no} Goal:{goal['name']} Amt:{fmt_currency(amount)}")
    return ServiceResult(success=True, message=f"{fmt_currency(amount)} contributed to '{goal['name']}'!")


def delete_savings_goal(acc_no: str, goal_id: str) -> ServiceResult:
    """Delete a savings goal and refund the amount to the account balance."""
    goals = load_goals(acc_no)
    goal = next((g for g in goals if g["goal_id"] == goal_id), None)
    if not goal:
        return ServiceResult(success=False, message="Goal not found.")

    # Refund to balance
    accounts = load_json(ACCOUNTS_FILE)
    if goal["current_amount"] > 0 and acc_no in accounts:
        accounts[acc_no]["balance"] += goal["current_amount"]
        save_json(ACCOUNTS_FILE, accounts)
        _log_transaction(acc_no, accounts[acc_no]["balance"], "DEPOSIT",
                         goal["current_amount"],
                         f"Refund from deleted goal: {goal['name']}",
                         category="Savings")

    goals.remove(goal)
    save_goals(acc_no, goals)
    logger.info(f"Goal deleted -> Acc:{acc_no} Goal:{goal['name']}")
    return ServiceResult(success=True, message=f"Goal '{goal['name']}' deleted. Amount refunded.")
