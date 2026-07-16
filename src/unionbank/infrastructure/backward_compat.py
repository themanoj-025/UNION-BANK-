"""
backward_compat.py  –  Backward-compatible wrappers for migration and test support.

These functions provide a bridge between the old JSON-file-based service layer
and the new SQLAlchemy-based infrastructure. New code should use
``container.get_container()`` directly instead of these wrappers.

Functions
---------
- ensure_account_exists     — Create an AccountModel row if missing
- sync_account_from_json    — Sync JSON account data into SQLite (migration helper)
- get_db_balance            — Read current balance from SQLite
- atomic_transfer           — Atomic fund transfer wrapping TransactionService
- atomic_apply_interest     — Atomic interest application
- atomic_close_account      — Mark account as inactive atomically
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from unionbank.infrastructure.container import get_container
from unionbank.infrastructure.database import (
    atomic_session as _atomic_session,
    close_session as _close_session,
    get_session as _get_session,
    init_db as _init_db,
    ModelBase,
)
from unionbank.infrastructure.persistence import AccountModel

# Re-export session management for backward compatibility
atomic_session = _atomic_session
close_session = _close_session
get_session = _get_session
init_db = _init_db
Base = ModelBase


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Migration helpers (for scripts/seed, not for live code) ─────────────────


def ensure_account_exists(acc_no: str, name: str = "", balance: float = 0.0):
    """Ensure an AccountModel row exists in the DB."""
    session = _get_session()
    account = session.query(AccountModel).filter_by(account_number=acc_no).first()
    if account is None:
        account = AccountModel(
            account_number=acc_no,
            name=name,
            balance=Decimal(str(balance)),
            is_active=True,
            is_frozen=False,
        )
        session.add(account)
        session.commit()
    return account


def sync_account_from_json(acc_no: str, json_data: dict):
    """Sync or create an AccountModel row from JSON data (migration helper)."""
    session = _get_session()
    account = session.query(AccountModel).filter_by(account_number=acc_no).first()
    if account is None:
        account = AccountModel(
            account_number=acc_no,
            name=json_data.get("name", ""),
            age=json_data.get("age", 18),
            gender=json_data.get("gender", ""),
            mobile=json_data.get("mobile", ""),
            email=json_data.get("email", ""),
            password=json_data.get("password", ""),
            balance=Decimal(str(json_data.get("balance", 0.0))),
            is_active=json_data.get("is_active", True),
            is_frozen=json_data.get("is_frozen", False),
        )
        session.add(account)
    else:
        account.name = json_data.get("name", account.name)
        account.balance = Decimal(str(json_data.get("balance", float(account.balance))))
        account.is_active = json_data.get("is_active", account.is_active)
        account.is_frozen = json_data.get("is_frozen", account.is_frozen)
    session.commit()


def get_db_balance(acc_no: str) -> Optional[Decimal]:
    """Get the current balance from the SQLite DB."""
    session = _get_session()
    account = session.query(AccountModel).filter_by(account_number=acc_no).first()
    if account is None:
        return None
    return account.balance


# ═══════════════════════════════════════════════════════════════════════════════
#  Atomic operations (backward-compatible wrappers)
#  New code should use application/services.py directly via the container.
# ═══════════════════════════════════════════════════════════════════════════════


class AtomicTransferResult:
    """Result of an atomic transfer operation."""

    def __init__(
        self,
        success: bool,
        sender_balance: float = 0.0,
        receiver_balance: float = 0.0,
        error_message: str = "",
    ):
        self.success = success
        self.sender_balance = sender_balance
        self.receiver_balance = receiver_balance
        self.error_message = error_message


def atomic_transfer(
    sender_acc_no: str,
    receiver_acc_no: str,
    amount: float,
    category: str = "General",
    sender_name: str = "",
    receiver_name: str = "",
) -> AtomicTransferResult:
    """Execute an atomic fund transfer (backward-compatible wrapper)."""
    from decimal import Decimal as D

    svc = get_container().transaction_service()
    result = svc.transfer(
        sender_acc_no=sender_acc_no,
        receiver_acc_no=receiver_acc_no,
        amount=D(str(amount)),
        category=category,
    )
    return AtomicTransferResult(
        success=result.success,
        sender_balance=float(result.sender_balance),
        receiver_balance=float(result.receiver_balance),
        error_message=result.error_message,
    )


def atomic_apply_interest(acc_no: str, interest_amount: float) -> bool:
    """Apply interest atomically (backward-compatible wrapper).

    If interest_amount is provided, uses it directly for precise control
    (needed by tests that bypass interest calculation).
    """
    from decimal import Decimal as D

    from unionbank.domain.entities import Transaction, TransactionType
    from unionbank.utils import generate_transaction_id

    c = get_container()

    if interest_amount > 0:
        # Direct balance update for backward compatibility with tests
        account = c.account_repo().get(acc_no)
        if account is None:
            return False
        if account.is_frozen or not account.is_active:
            return False
        account.balance += D(str(interest_amount))
        c.account_repo().update(account)

        # Log a transaction record for the interest credit
        txn = c.transaction_repo()
        txn.create(
            Transaction(
                txn_id=generate_transaction_id(),
                account_number=acc_no,
                type=TransactionType.INTEREST,
                amount=D(str(interest_amount)),
                balance=account.balance,
                description="Monthly interest credit",
                category="Savings",
            )
        )
        c.account_repo().commit()
        return True

    svc = c.transaction_service()
    result = svc.apply_interest(acc_no)
    return result.success


def atomic_close_account(acc_no: str) -> bool:
    """Mark an account as inactive atomically (backward-compatible wrapper).

    Bypasses password verification for backward compatibility with tests
    and internal API calls. Production code should use AccountService directly.
    """
    c = get_container()
    account = c.account_repo().get(acc_no)
    if account is None:
        return False

    # Directly set inactive (bypassing password check for backward compat)
    account.is_active = False
    c.account_repo().update(account)
    c.account_repo().commit()
    return True
