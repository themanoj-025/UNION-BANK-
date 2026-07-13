"""
database.py  –  SQLite database engine, session helpers, and atomic operations.

Uses the unified models from models.py for schema definitions.
Provides ACID transaction support via atomic_session() context manager.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from logger import logger
from models import AccountModel, TransactionModel
from repositories import AccountRepository, TransactionRepository
from utils import generate_transaction_id

# Re-export for external use
from models import Base as ModelBase


def _utcnow() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
#  Database setup
# ═══════════════════════════════════════════════════════════════════════════════

# Use the same data directory as JSON files for consistency
DATA_DIR = Path(settings.DATA_DIR)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR / "union_bank.db")
_engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)

# Enable WAL mode for better concurrent read/write performance
@event.listens_for(_engine, "connect")
def _set_wal_mode(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

# Thread-local session storage
_thread_local = threading.local()


# ═══════════════════════════════════════════════════════════════════════════════
#  Session management
# ═══════════════════════════════════════════════════════════════════════════════

def get_session() -> Session:
    """Get the current thread's database session."""
    if not hasattr(_thread_local, "session") or _thread_local.session is None:
        _thread_local.session = _SessionLocal()
    return _thread_local.session


def close_session():
    """Close the current thread's database session."""
    if hasattr(_thread_local, "session") and _thread_local.session is not None:
        try:
            _thread_local.session.close()
        except Exception:
            pass
        _thread_local.session = None


@contextmanager
def atomic_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    Automatically commits on success, rolls back on exception.
    """
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  Initialization
# ═══════════════════════════════════════════════════════════════════════════════

# Re-export for external use
Base = ModelBase


def init_db():
    """Create all tables if they don't exist (uses models.py schema)."""
    ModelBase.metadata.create_all(bind=_engine)


def ensure_account_exists(acc_no: str, name: str = "", balance: float = 0.0) -> AccountModel:
    """Ensure an AccountModel row exists in the DB, creating it if necessary."""
    session = get_session()
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
    """Sync or create an AccountModel row from JSON data."""
    session = get_session()
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
    session = get_session()
    account = session.query(AccountModel).filter_by(account_number=acc_no).first()
    if account is None:
        return None
    return account.balance


# ═══════════════════════════════════════════════════════════════════════════════
#  ⭐ THE STAR OF THE SHOW — Atomic fund transfer
# ═══════════════════════════════════════════════════════════════════════════════
#  This is the bug fix. The entire sender-debit + receiver-credit is wrapped in
#  a single SQLite transaction. If anything fails, both are rolled back.
#  Money is NEVER lost. EVER.
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
    """Execute an atomic fund transfer between two accounts.

    This is the fix for the race condition bug. The entire operation:
      1. Debit sender
      2. Credit receiver
      3. Log both transactions

    ...is wrapped in a single SQLite transaction. If the process crashes
    at any point, the transaction is rolled back and NO money is lost.

    Args:
        sender_acc_no: Source account number
        receiver_acc_no: Destination account number
        amount: Amount to transfer
        category: Transaction category
        sender_name: Sender display name (for DB sync)
        receiver_name: Receiver display name (for DB sync)

    Returns:
        AtomicTransferResult with success status and new balances
    """
    if amount <= 0:
        return AtomicTransferResult(
            success=False, error_message="Amount must be positive."
        )

    with atomic_session() as session:
        # ── Lock both rows (SELECT FOR UPDATE on SQLite is implicit via row-level locking)
        sender = session.query(AccountModel).filter_by(account_number=sender_acc_no).first()
        if sender is None:
            return AtomicTransferResult(
                success=False, error_message="Sender account not found."
            )

        receiver = session.query(AccountModel).filter_by(account_number=receiver_acc_no).first()
        if receiver is None:
            return AtomicTransferResult(
                success=False, error_message="Receiver account not found."
            )

        if sender.is_frozen:
            return AtomicTransferResult(
                success=False, error_message="Sender account is frozen."
            )
        if not sender.is_active:
            return AtomicTransferResult(
                success=False, error_message="Sender account is closed."
            )
        if receiver.is_frozen:
            return AtomicTransferResult(
                success=False, error_message="Receiver account is frozen."
            )
        if not receiver.is_active:
            return AtomicTransferResult(
                success=False, error_message="Receiver account is closed."
            )
        if sender.balance < amount:
            return AtomicTransferResult(
                success=False,
                error_message=f"Insufficient balance. Available: {sender.balance:.2f}",
            )

        # ── Execute the transfer (both changes in same transaction) ──────────
        sender.balance -= Decimal(str(amount))
        receiver.balance += Decimal(str(amount))

        # ── Generate transaction records ─────────────────────────────────────
        now = _utcnow()
        sender_txn_id = generate_transaction_id()
        receiver_txn_id = generate_transaction_id()

        sender_txn = TransactionModel(
            txn_id=sender_txn_id,
            account_number=sender_acc_no,
            type="TRANSFER_OUT",
            amount=round(amount, 2),
            balance=round(sender.balance, 2),
            description=f"Transfer to {receiver_acc_no}",
            category=category,
            target_account=receiver_acc_no,
            timestamp=now,
        )
        receiver_txn = TransactionModel(
            txn_id=receiver_txn_id,
            account_number=receiver_acc_no,
            type="TRANSFER_IN",
            amount=round(amount, 2),
            balance=round(receiver.balance, 2),
            description=f"Transfer from {sender_acc_no}",
            category=category,
            target_account=sender_acc_no,
            timestamp=now,
        )

        session.add(sender_txn)
        session.add(receiver_txn)

        # ── Session.commit() happens on context manager exit ─────────────────
        # If anything above fails, the exception handler calls session.rollback()

        logger.info(
            f"Atomic transfer complete -> From:{sender_acc_no} "
            f"To:{receiver_acc_no} Amt:{amount:.2f} "
            f"(TXN:{sender_txn_id}/{receiver_txn_id})"
        )

        return AtomicTransferResult(
            success=True,
            sender_balance=round(float(sender.balance), 2),
            receiver_balance=round(receiver.balance, 2),
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Atomic interest application
# ═══════════════════════════════════════════════════════════════════════════════

def atomic_apply_interest(
    acc_no: str,
    interest_amount: float,
) -> bool:
    """Apply interest to an account atomically.

    Returns True if successful, False if account not found or frozen/closed.
    """
    if interest_amount <= 0:
        return False

    with atomic_session() as session:
        account = session.query(AccountModel).filter_by(account_number=acc_no).first()
        if account is None:
            return False
        if account.is_frozen or not account.is_active:
            return False

        account.balance += Decimal(str(interest_amount))

        txn = TransactionModel(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type="INTEREST",
            amount=round(interest_amount, 2),
            balance=round(account.balance, 2),
            description="Monthly interest credit",
            category="Savings",
            timestamp=_utcnow(),
        )
        session.add(txn)

        logger.info(f"Atomic interest applied -> Acc:{acc_no} Amt:{interest_amount:.2f}")
        return True


# ═══════════════════════════════════════════════════════════════════════════════
#  Atomic account closure
# ═══════════════════════════════════════════════════════════════════════════════

def atomic_close_account(acc_no: str) -> bool:
    """Mark an account as inactive atomically."""
    with atomic_session() as session:
        account = session.query(AccountModel).filter_by(account_number=acc_no).first()
        if account is None:
            return False
        account.is_active = False
        return True


# Initialize DB tables on import
init_db()
