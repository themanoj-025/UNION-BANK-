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
from decimal import Decimal
from typing import Optional

from logger import logger
from utils import (
    generate_transaction_id, now_str, fmt_currency,
    calculate_monthly_interest, verify_password,
    TRANSACTION_CATEGORIES,
)
from database import (
    atomic_transfer, atomic_apply_interest, atomic_close_account,
    close_session as db_close_session, get_session,
)
from repositories import (
    AccountRepository, TransactionRepository,
    AdminRepository, SavingsGoalRepository,
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
#  Session / repository helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _get_repos():
    """Get a DB session and repository instances.

    Returns (session, AccountRepository, TransactionRepository).
    The caller is responsible for session.commit() and session.close().
    """
    session = get_session()
    return (
        session,
        AccountRepository(session),
        TransactionRepository(session),
    )


def _account_to_float(acc) -> float:
    """Extract balance as float from an AccountModel instance."""
    return float(acc.balance) if hasattr(acc, 'balance') and acc.balance else 0.0


def _log_txn_repo(txn_repo, acc_no: str, balance: float, txn_type: str,
                  amount: float, description: str,
                  category: str = "General",
                  target_acc: Optional[str] = None) -> str:
    """Log a transaction using TransactionRepository."""
    from domain.entities import Transaction, TransactionType
    txn = Transaction(
        txn_id=generate_transaction_id(),
        account_number=acc_no,
        type=TransactionType(txn_type),
        amount=Decimal(str(amount)),
        balance=Decimal(str(balance)),
        description=description,
        category=category,
        target_account=target_acc,
    )
    txn_repo.create(txn)
    return txn.txn_id
    logger.info(
        f"TXN [{txn.txn_id}]  {txn_type:<14}  Acc:{acc_no}  "
        f"Amt:{fmt_currency(amount)}  Bal:{fmt_currency(balance)}"
        + (f"  -> {target_acc}" if target_acc else "")
    )
    return txn.txn_id


# ═══════════════════════════════════════════════════════════════════════════════
#  Customer operations
# ═══════════════════════════════════════════════════════════════════════════════

def process_deposit(acc_no: str, amount: float,
                    category: str = "General") -> ServiceResult:
    """Deposit money into an account using the repository layer."""
    if amount <= 0:
        return ServiceResult(success=False, message="Amount must be positive.")

    session, repo, txn_repo = _get_repos()
    try:
        account = repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if account.is_frozen:
            return ServiceResult(success=False, message="Account is frozen.")
        if not account.is_active:
            return ServiceResult(success=False, message="Account is closed.")

        cat = category if category in TRANSACTION_CATEGORIES else "General"
        account.balance += Decimal(str(amount))

        new_balance = _account_to_float(account)
        _log_txn_repo(txn_repo, acc_no, new_balance, "DEPOSIT", amount,
                      "Deposit", category=cat)
        session.commit()

        logger.info(f"Deposit -> Acc:{acc_no} Amt:{fmt_currency(amount)}")
        return ServiceResult(
            success=True,
            message=f"{fmt_currency(amount)} deposited successfully. "
                    f"New balance: {fmt_currency(new_balance)}",
            data={"balance": new_balance, "balance_formatted": fmt_currency(new_balance)},
        )
    finally:
        db_close_session()


def process_withdraw(acc_no: str, amount: float,
                     category: str = "General") -> ServiceResult:
    """Withdraw money from an account using the repository layer."""
    if amount <= 0:
        return ServiceResult(success=False, message="Amount must be positive.")

    session, repo, txn_repo = _get_repos()
    try:
        account = repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if account.is_frozen:
            return ServiceResult(success=False, message="Account is frozen.")
        if not account.is_active:
            return ServiceResult(success=False, message="Account is closed.")

        current = _account_to_float(account)
        if amount > current:
            logger.warning(
                f"Insufficient balance -> Acc:{acc_no}  "
                f"Requested:{fmt_currency(amount)}  Available:{fmt_currency(current)}"
            )
            return ServiceResult(
                success=False,
                message=f"Insufficient balance. Available: {fmt_currency(current)}",
            )

        cat = category if category in TRANSACTION_CATEGORIES else "General"
        account.balance -= Decimal(str(amount))

        new_balance = _account_to_float(account)
        _log_txn_repo(txn_repo, acc_no, new_balance, "WITHDRAW", amount,
                      "Withdrawal", category=cat)
        session.commit()

        logger.info(f"Withdraw -> Acc:{acc_no} Amt:{fmt_currency(amount)}")
        return ServiceResult(
            success=True,
            message=f"{fmt_currency(amount)} withdrawn successfully. "
                    f"New balance: {fmt_currency(new_balance)}",
            data={"balance": new_balance, "balance_formatted": fmt_currency(new_balance)},
        )
    finally:
        db_close_session()


def process_transfer(sender_acc_no: str, receiver_acc_no: str,
                     amount: float, category: str = "General",
                     sender_name_hint: str = "",
                     receiver_name_hint: str = "") -> TransferResult:
    """Transfer funds atomically between two accounts.

    Uses SQLite ACID transaction (database.py atomic_transfer).
    Verifies account status via repository before the atomic operation.
    """
    if amount <= 0:
        return TransferResult(success=False, error_message="Amount must be positive.")

    cat = category if category in TRANSACTION_CATEGORIES else "General"

    session, repo, _ = _get_repos()
    try:
        sender = repo.get(sender_acc_no)
        receiver = repo.get(receiver_acc_no)

        if sender is None:
            return TransferResult(success=False, error_message="Sender account not found.")
        if receiver is None:
            return TransferResult(success=False, error_message="Recipient account not found.")
        if sender_acc_no == receiver_acc_no:
            return TransferResult(success=False, error_message="Cannot transfer to your own account.")

        if sender.is_frozen:
            return TransferResult(success=False, error_message="Your account is frozen.")
        if not sender.is_active:
            return TransferResult(success=False, error_message="Your account is closed.")
        if receiver.is_frozen:
            return TransferResult(success=False, error_message="Recipient account is frozen.")
        if not receiver.is_active:
            return TransferResult(success=False, error_message="Recipient account is closed.")

        if _account_to_float(sender) < amount:
            logger.warning(
                f"Transfer insufficient -> From:{sender_acc_no}  "
                f"Req:{fmt_currency(amount)}  Avail:{fmt_currency(_account_to_float(sender))}"
            )
            return TransferResult(
                success=False,
                error_message=f"Insufficient balance. Available: {fmt_currency(_account_to_float(sender))}",
            )

        # Capture names inside the try block for use after session is closed
        sender_name = sender_name_hint or sender.name
        receiver_name = receiver_name_hint or receiver.name
        session.commit()
    finally:
        db_close_session()

    # Use the atomic SQLite transfer (handles commit/rollback internally)
    result = atomic_transfer(
        sender_acc_no=sender_acc_no,
        receiver_acc_no=receiver_acc_no,
        amount=amount,
        category=cat,
        sender_name=sender_name,
        receiver_name=receiver_name,
    )

    if result.success:
        logger.info(
            f"Atomic transfer complete -> From:{sender_acc_no} "
            f"To:{receiver_acc_no} Amt:{fmt_currency(amount)}"
        )
    else:
        logger.warning(f"Atomic transfer failed: {result.error_message}")
    return result


def process_close_account(acc_no: str, password: str,
                          stored_password_hash: str) -> ServiceResult:
    """Close an account after password verification (via repository)."""
    if not verify_password(password, stored_password_hash):
        logger.warning(f"Close account failed (wrong password) -> Acc:{acc_no}")
        return ServiceResult(success=False, message="Incorrect password.")

    # Atomic closure: SQLite first
    atomic_close_account(acc_no)
    db_close_session()

    # Then update via repository
    session, repo, _ = _get_repos()
    try:
        account = repo.get(acc_no)
        if account:
            account.is_active = False
            session.commit()
    finally:
        db_close_session()

    logger.critical(f"Account CLOSED -> Acc:{acc_no}")
    return ServiceResult(success=True, message="Account closed successfully.")


def process_apply_interest(acc_no: str, balance: float) -> ServiceResult:
    """Apply monthly interest via atomic SQLite transaction."""
    interest = calculate_monthly_interest(balance)
    if interest <= 0:
        return ServiceResult(success=False, message="No interest to apply.")

    if not atomic_apply_interest(acc_no, interest):
        return ServiceResult(success=False, message="Failed to apply interest.")

    # Read back the balance from DB (atomic_apply_interest already credited it)
    session, repo, txn_repo = _get_repos()
    try:
        account = repo.get(acc_no)
        new_balance = _account_to_float(account) if account else (balance + interest)
        _log_txn_repo(txn_repo, acc_no, new_balance, "INTEREST", interest,
                      "Monthly interest credit", category="Savings")
        session.commit()
    finally:
        db_close_session()

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
    """Compute bank-wide statistics using repository layer.

    Falls back to JSON if repository is unavailable.
    Returns a dict with all summary metrics.
    """
    session, repo, txn_repo = _get_repos()
    try:
        all_accounts = repo.get_all()
        total_customers = len(all_accounts)
        active = repo.active_count()
        frozen = repo.frozen_count()
        closed = repo.closed_count()
        total_balance = float(repo.total_balance())

        total_txns = txn_repo.count()
        total_dep = float(txn_repo.total_by_type("DEPOSIT"))
        total_with = float(txn_repo.total_by_type("WITHDRAW"))
        total_trans = float(txn_repo.total_by_type("TRANSFER_OUT"))

        # Category breakdown from all transactions
        all_txns = txn_repo.get_all() if total_txns > 0 else []
        category_totals = {}
        for t in all_txns:
            cat = t.category or "General"
            category_totals[cat] = category_totals.get(cat, 0) + float(abs(t.amount))
        sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

        session.commit()
    finally:
        close_session()

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
    """Freeze a customer account (admin operation) via repository."""
    session, repo, _ = _get_repos()
    try:
        account = repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_active and not account.is_frozen:
            return ServiceResult(success=False, message="Account is permanently closed.")
        if account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is already frozen.")

        repo.set_frozen(acc_no, True)
        session.commit()

        msg = f"Account {acc_no} ({account.name}) has been frozen."
        logger.critical(msg)
        return ServiceResult(success=True, message=msg)
    finally:
        db_close_session()


def process_unfreeze_account(acc_no: str) -> ServiceResult:
    """Unfreeze a customer account (admin operation) via repository."""
    session, repo, _ = _get_repos()
    try:
        account = repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is not frozen.")

        repo.set_frozen(acc_no, False)
        session.commit()

        msg = f"Account {acc_no} ({account.name}) has been unfrozen."
        logger.critical(msg)
        return ServiceResult(success=True, message=msg)
    finally:
        db_close_session()


def process_delete_account(acc_no: str) -> ServiceResult:
    """Permanently delete an account and its transactions (admin) via repository."""
    session, repo, _ = _get_repos()
    try:
        account = repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        acc_name = account.name
        repo.delete(acc_no)
        session.commit()

        msg = f"Account {acc_no} ({acc_name}) has been deleted."
        logger.critical(msg)
        return ServiceResult(success=True, message=msg)
    finally:
        db_close_session()


def admin_authenticate(username: str, password: str) -> ServiceResult:
    """Authenticate an admin user via AdminRepository."""
    session = get_session()
    try:
        admin_repo = AdminRepository(session)
        admin = admin_repo.get_by_username(username)
        if admin and verify_password(password, admin.password):
            return ServiceResult(success=True, data={"username": username})
        return ServiceResult(success=False, message="Invalid admin credentials.")
    finally:
        db_close_session()


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings goals operations
# ═══════════════════════════════════════════════════════════════════════════════

def create_savings_goal(acc_no: str, name: str, target_amount: float,
                        target_date: str = "") -> ServiceResult:
    """Create a new savings goal via SavingsGoalRepository."""
    if not name or len(name) < 2:
        return ServiceResult(success=False, message="Goal name must be at least 2 characters.")
    if target_amount <= 0:
        return ServiceResult(success=False, message="Target amount must be positive.")

    session = get_session()
    try:
        goal_repo = SavingsGoalRepository(session)
        goal_repo.create(acc_no, name, Decimal(str(target_amount)), target_date=target_date)
        session.commit()
    finally:
        db_close_session()

    logger.info(f"Savings goal created -> Acc:{acc_no} Goal:{name}")
    return ServiceResult(success=True, message=f"Goal '{name}' created!")


def contribute_to_goal(acc_no: str, goal_id: str, amount: float,
                       current_balance: float) -> ServiceResult:
    """Contribute money from account balance to a savings goal via repositories."""
    if amount <= 0:
        return ServiceResult(success=False, message="Amount must be positive.")
    if amount > current_balance:
        return ServiceResult(success=False, message="Insufficient balance.")

    session, repo, txn_repo = _get_repos()
    try:
        goal_repo = SavingsGoalRepository(session)
        goal = goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        # Update account balance
        account = repo.get(acc_no)
        if account:
            account.balance -= Decimal(str(amount))

            _log_txn_repo(txn_repo, acc_no, _account_to_float(account),
                          "TRANSFER_OUT", amount,
                          f"Savings goal: {goal.name}", category="Savings")

        # Update goal
        goal_repo.contribute(goal_id, Decimal(str(amount)))
        session.commit()
    finally:
        db_close_session()

    logger.info(f"Goal contribution -> Acc:{acc_no} Goal:{goal_id} Amt:{fmt_currency(amount)}")
    return ServiceResult(success=True, message=f"{fmt_currency(amount)} contributed!")


def delete_savings_goal(acc_no: str, goal_id: str) -> ServiceResult:
    """Delete a savings goal and refund the amount via repositories."""
    session = get_session()
    try:
        goal_repo = SavingsGoalRepository(session)
        repo = AccountRepository(session)

        # Get refund amount before deleting
        goal = goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        refund = float(goal.current_amount)
        name = goal.name
        goal_repo.delete(goal_id)

        # Refund to balance
        if refund > 0:
            account = repo.get(acc_no)
            if account:
                account.balance += Decimal(str(refund))

        session.commit()
    finally:
        db_close_session()

    logger.info(f"Goal deleted -> Acc:{acc_no} Goal:{name}")
    return ServiceResult(success=True, message=f"Goal '{name}' deleted. Amount refunded.")
