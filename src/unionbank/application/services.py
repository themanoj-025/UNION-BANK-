"""application/services.py  –  Use-case service classes.

Each service has a single `execute()` method (or multiple focused methods).
Services depend only on repository protocols — never on concrete DB code.
"""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Generator, Optional




# ── Canonical constants (from centralized config) ────────────────────────────
from unionbank.config import settings
from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import (
    Account,
    AdminUser,
    IdempotencyRecord,
    Loan,
    LoanStatus,
    LoanType,
    SavingsGoal,
    ServiceResult,
    TokenVersion,
    Transaction,
    TransactionType,
    TransferResult,
)
from unionbank.domain.interest import calculate_monthly_interest
from sqlalchemy.orm import Session
from unionbank.utils.formatting import (
    calculate_emi,
    fmt_currency,
    generate_account_number,
    generate_goal_id,
    generate_loan_id,
    generate_transaction_id,
)
from unionbank.utils.hashing import hash_password, verify_password

from .interfaces import (
    AccountRepositoryProtocol,
    AdminRepositoryProtocol,
    AuditLogRepositoryProtocol,
    IdempotencyRepositoryProtocol,
    KeysetPage,
    LoanRepositoryProtocol,
    LoginAttemptRepositoryProtocol,
    NotificationServiceProtocol,
    SavingsGoalRepositoryProtocol,
    TokenVersionRepositoryProtocol,
    TransactionRepositoryProtocol,
)

import pybreaker

# ── Circuit breaker for notification service calls ──────────────────────────
# Prevents a slow or unresponsive notification provider from blocking
# money-movement responses. After 5 failures in 60 seconds the circuit opens
# for 30 seconds, failing fast instead of waiting for a timeout on each call.
NOTIFICATION_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Per-account concurrency lock
# ═══════════════════════════════════════════════════════════════════════════════
#
# SQLite's WAL mode provides snapshot isolation, enabling concurrent reads but
# allowing the classic "lost update" race under concurrent writes: two threads
# can read the same balance snapshot, both update, and only the last commit
# "wins."  The same mechanism prevents BEGIN IMMEDIATE from working through
# the SQLAlchemy dialect, so we serialize write operations at the application
# layer with per-account locks.  This is the recommended pattern for
# single-process SQLite-backed applications (used by Django, Peewee, etc.).
#
# For PostgreSQL deployments, this lock is a no-op safety net — row-level
# locking (SELECT … FOR UPDATE) in the async repositories provides the actual
# concurrency guarantee, and the threading lock does nothing harmful (it just
# serializes within a single process).
#
# Locks are always acquired in **sorted account-number order** to guarantee
# deadlock-free acquisition when multiple accounts are involved (transfer).
# ═══════════════════════════════════════════════════════════════════════════════

# Default dict with threading.Lock factory ensures thread-safe lock creation
# (avoids TOCTOU race between the "not in" check and lock creation).
_account_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)


@contextmanager
def _account_lock(*acc_nos: str) -> Generator[None, None, None]:
    """Context manager that acquires per-account locks in sorted order.

    Acquires locks for *all* given accounts in ascending account-number order,
    guaranteeing deadlock-free acquisition when multiple accounts are involved
    (e.g. transfer needs both sender and receiver).  Locks are released in
    reverse order on exit.
    """
    sorted_nos = sorted(acc_nos)
    for acc_no in sorted_nos:
        _account_locks[acc_no].acquire()
    try:
        yield
    finally:
        for acc_no in sorted_nos:
            _account_locks[acc_no].release()

TRANSACTION_CATEGORIES = settings.TRANSACTION_CATEGORIES
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOGIN_LOCKOUT_MINUTES = settings.LOGIN_LOCKOUT_MINUTES


class AuthService:
    """Authentication and authorization use-cases."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        admin_repo: AdminRepositoryProtocol,
        login_attempt_repo: LoginAttemptRepositoryProtocol,
        token_version_repo: Optional[TokenVersionRepositoryProtocol] = None,
        notif_service: Optional[NotificationServiceProtocol] = None,
    ):
        self.account_repo = account_repo
        self.admin_repo = admin_repo
        self.login_attempt_repo = login_attempt_repo
        self.token_version_repo = token_version_repo
        self.notif_service = notif_service

    def customer_login(self, acc_no: str, password: str) -> ServiceResult:
        """Authenticate a customer login."""
        # Rate limiting check
        is_locked, remaining = self.login_attempt_repo.is_locked(acc_no)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Account locked. Try again in {remaining} minute(s).",
            )

        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if account.is_frozen:
            return ServiceResult(success=False, message="Account is frozen. Please contact the bank.")

        if not account.is_active:
            return ServiceResult(success=False, message="Account has been closed.")

        if not verify_password(password, account.password):
            remaining = self.login_attempt_repo.record_failure(
                acc_no, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
            )
            self.login_attempt_repo.commit()
            if remaining > 0:
                return ServiceResult(
                    success=False,
                    message=f"Incorrect password. {remaining} attempt(s) remaining.",
                )
            else:
                return ServiceResult(
                    success=False,
                    message=f"Incorrect password. Account locked for {LOGIN_LOCKOUT_MINUTES} minutes.",
                )

        self.login_attempt_repo.reset(acc_no)
        self.login_attempt_repo.commit()
        return ServiceResult(success=True, data={"account_number": acc_no, "role": "customer"})

    def customer_register(
        self,
        name: str, age: int, gender: str, mobile: str, email: str,
        password: str,
    ) -> ServiceResult:
        """Register a new customer account."""
        acc_no = generate_account_number()
        account = Account(
            account_number=acc_no,
            name=name,
            age=age,
            gender=gender,
            mobile=mobile,
            email=email,
            password=hash_password(password),
            balance=Decimal("0.00"),
            is_active=True,
            is_frozen=False,
        )
        self.account_repo.create(account)
        self.account_repo.commit()

        # Send welcome notification (non-fatal if fails)
        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_welcome)(acc_no)
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping welcome notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send welcome notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Account created successfully! Account number: {acc_no}",
            data={"account_number": acc_no},
        )

    def admin_login(self, username: str, password: str) -> ServiceResult:
        """Authenticate an admin login."""
        lock_key = f"admin_{username}"
        is_locked, remaining = self.login_attempt_repo.is_locked(lock_key)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Admin account locked. Try again in {remaining} minute(s).",
            )

        admin = self.admin_repo.get_by_username(username)
        if admin and verify_password(password, admin.password):
            self.login_attempt_repo.reset(lock_key)
            self.login_attempt_repo.commit()
            return ServiceResult(success=True, data={"username": username, "role": "admin"})

        remaining = self.login_attempt_repo.record_failure(
            lock_key, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
        )
        self.login_attempt_repo.commit()
        if remaining > 0:
            return ServiceResult(
                success=False,
                message=f"Invalid credentials. {remaining} attempt(s) remaining.",
            )
        return ServiceResult(
            success=False,
            message=f"Admin account locked for {LOGIN_LOCKOUT_MINUTES} minutes.",
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Account Service
# ═══════════════════════════════════════════════════════════════════════════════


class AccountService:
    """Customer account management use-cases."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        token_version_repo: Optional[TokenVersionRepositoryProtocol] = None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.token_version_repo = token_version_repo

    def get_profile(self, acc_no: str) -> Optional[Account]:
        return self.account_repo.get(acc_no)

    def update_profile(self, acc_no: str, **kwargs) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        for key, value in kwargs.items():
            if hasattr(account, key) and value is not None:
                setattr(account, key, value)

        self.account_repo.update(account)
        self.account_repo.commit()
        return ServiceResult(success=True, message="Profile updated successfully.")

    def change_password(self, acc_no: str, current_pwd: str, new_pwd: str) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(current_pwd, account.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        account.password = hash_password(new_pwd)
        self.account_repo.update(account)

        # Increment token version to invalidate all existing JWTs
        if self.token_version_repo:
            self.token_version_repo.increment(acc_no)

        self.account_repo.commit()
        return ServiceResult(success=True, message="Password changed successfully.")

    def close_account(self, acc_no: str, password: str) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(password, account.password):
            return ServiceResult(success=False, message="Incorrect password.")

        account.is_active = False
        self.account_repo.update(account)
        self.account_repo.commit()
        return ServiceResult(success=True, message="Account closed successfully.")

    def get_balance(self, acc_no: str) -> Optional[Decimal]:
        account = self.account_repo.get(acc_no)
        return account.balance if account else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Transaction Service
# ═══════════════════════════════════════════════════════════════════════════════


class TransactionService:
    """Transaction use-cases (deposit, withdraw, transfer, statement, interest).

    Idempotency: deposit/withdraw/transfer operations check the idempotency
    repository before executing. If a duplicate key is found, the cached
    result is returned instead of re-executing.
    """

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        notif_service: Optional[NotificationServiceProtocol] = None,
        idempotency_repo: Optional[IdempotencyRepositoryProtocol] = None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.notif_service = notif_service
        self.idempotency_repo = idempotency_repo

    def _ensure_non_negative_balance(self, balance: Decimal, operation: str = "transaction") -> None:
        """App-level guard: raise ValueError if balance would go negative.

        This is a defense-in-depth check — the DB also has a CHECK constraint.
        The app-level check catches errors before they reach the DB, providing
        a clearer error message and preventing wasted DB round-trips.
        """
        if balance < Decimal("0.00"):
            raise ValueError(f"Insufficient balance for {operation}.")

    def _check_idempotency(
        self, idempotency_key: Optional[str], acc_no: str, operation: str, amount: Decimal
    ) -> Optional[ServiceResult]:
        """Check if a request with this idempotency_key has already been processed.

        Returns the cached ServiceResult if found, None if this is a new request.
        """
        if not idempotency_key or not self.idempotency_repo:
            return None
        existing = self.idempotency_repo.get(idempotency_key)
        if existing is not None:
            # Key already exists — return cached result (prevents double-spend)
            try:
                data = json.loads(existing.result_json)
                return ServiceResult(
                    success=data.get("success", True),
                    message=data.get("message", "Operation already completed."),
                    data=data.get("data"),
                )
            except (json.JSONDecodeError, KeyError):
                from unionbank.utils.logger import logger
                logger.warning("Failed to parse cached idempotency result", exc_info=True)
                return ServiceResult(
                    success=True,
                    message="Operation already completed.",
                )
        return None

    def _store_idempotency(
        self, idempotency_key: Optional[str], acc_no: str, operation: str,
        amount: Decimal, result: ServiceResult,
    ) -> None:
        """Store the result of an idempotent operation for future dedup."""
        if not idempotency_key or not self.idempotency_repo:
            return
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            account_number=acc_no,
            operation=operation,
            result_json=json.dumps({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            }),
            amount=amount,
        )
        try:
            self.idempotency_repo.create(record)
            self.idempotency_repo.commit()
        except Exception:
            from unionbank.utils.logger import logger
            logger.warning("Failed to persist idempotency record", exc_info=True)
            self.idempotency_repo.rollback()

    def deposit(self, acc_no: str, amount: Decimal, category: str = "General",
                idempotency_key: Optional[str] = None) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        # Check idempotency first (outside lock — read-only)
        cached = self._check_idempotency(idempotency_key, acc_no, "deposit", amount)
        if cached is not None:
            return cached

        # Serialize writes to this account (prevents lost updates under SQLite WAL)
        with _account_lock(acc_no):
            account = self.account_repo.get(acc_no)
            if account is None:
                return ServiceResult(success=False, message="Account not found.")
            if not account.can_transact:
                status = "frozen" if account.is_frozen else "closed"
                return ServiceResult(success=False, message=f"Account is {status}.")

            account.balance += amount
            self.account_repo.update(account)

            txn = Transaction(
                txn_id=generate_transaction_id(),
                account_number=acc_no,
                type=TransactionType.DEPOSIT,
                amount=amount,
                balance=account.balance,
                description="Deposit",
                category=category if category in TRANSACTION_CATEGORIES else "General",
            )
            self.txn_repo.create(txn)
            self.account_repo.commit()

        result = ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} deposited successfully. "
                    f"New balance: {fmt_currency(float(account.balance))}",
            data={"balance": float(account.balance)},
        )

        # Store idempotency result (non-fatal if fails)
        self._store_idempotency(idempotency_key, acc_no, "deposit", amount, result)

        # Send notification (non-fatal if fails)
        if self.notif_service and account:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_deposit)(
                    acc_no, amount, account.balance, txn.txn_id
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping deposit notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send deposit notification", exc_info=True)

        return result

    def withdraw(self, acc_no: str, amount: Decimal, category: str = "General",
                  idempotency_key: Optional[str] = None) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        # Check idempotency first (outside lock — read-only)
        cached = self._check_idempotency(idempotency_key, acc_no, "withdraw", amount)
        if cached is not None:
            return cached

        # Serialize writes to this account (prevents lost updates under SQLite WAL)
        with _account_lock(acc_no):
            account = self.account_repo.get(acc_no)
            if account is None:
                return ServiceResult(success=False, message="Account not found.")
            if not account.can_transact:
                status = "frozen" if account.is_frozen else "closed"
                return ServiceResult(success=False, message=f"Account is {status}.")

            if amount > account.balance:
                return ServiceResult(
                    success=False,
                    message=f"Insufficient balance. Available: {fmt_currency(float(account.balance))}",
                )

            account.balance -= amount
            self._ensure_non_negative_balance(account.balance, "withdraw")  # App-level guard
            self.account_repo.update(account)

            txn = Transaction(
                txn_id=generate_transaction_id(),
                account_number=acc_no,
                type=TransactionType.WITHDRAW,
                amount=amount,
                balance=account.balance,
                description="Withdrawal",
                category=category if category in TRANSACTION_CATEGORIES else "General",
            )
            self.txn_repo.create(txn)
            self.account_repo.commit()

        result = ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} withdrawn successfully. "
                    f"New balance: {fmt_currency(float(account.balance))}",
            data={"balance": float(account.balance)},
        )

        # Store idempotency result (non-fatal if fails)
        self._store_idempotency(idempotency_key, acc_no, "withdraw", amount, result)

        # Send notification (non-fatal if fails)
        if self.notif_service and account:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_withdraw)(
                    acc_no, amount, account.balance, txn.txn_id
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping withdraw notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send withdraw notification", exc_info=True)

        return result

    def transfer(
        self, sender_acc_no: str, receiver_acc_no: str,
        amount: Decimal, category: str = "General",
        idempotency_key: Optional[str] = None,
    ) -> TransferResult:
        if amount <= 0:
            return TransferResult(success=False, error_message="Amount must be positive.")
        if sender_acc_no == receiver_acc_no:
            return TransferResult(success=False, error_message="Cannot transfer to your own account.")

        # Check idempotency first (outside lock — read-only)
        if idempotency_key and self.idempotency_repo:
            existing = self.idempotency_repo.get(idempotency_key)
            if existing is not None:
                try:
                    data = json.loads(existing.result_json)
                    return TransferResult(
                        success=data.get("success", True),
                        sender_balance=Decimal(str(data.get("sender_balance", 0))),
                        receiver_balance=Decimal(str(data.get("receiver_balance", 0))),
                        error_message=data.get("error_message", ""),
                    )
                except (json.JSONDecodeError, KeyError):
                    pass

        cat = category if category in TRANSACTION_CATEGORIES else "General"

        # ── Atomic transaction: all DB writes succeed or none do ──────────────
        # Wrapped in begin_nested() savepoint so a crash mid-transfer cannot
        # debit one account without crediting the other.
        # The outer _account_lock serializes concurrent transfers involving
        # either account, preventing lost updates under SQLite WAL mode.
        # Crucially, account reads happen INSIDE the lock so each thread sees
        # the latest committed state (not a stale WAL snapshot).
        try:
            with _account_lock(sender_acc_no, receiver_acc_no):
                sender = self.account_repo.get(sender_acc_no)
                receiver = self.account_repo.get(receiver_acc_no)

                if sender is None:
                    return TransferResult(
                        success=False, error_message="Sender account not found."
                    )
                if receiver is None:
                    return TransferResult(
                        success=False, error_message="Recipient account not found."
                    )

                if not sender.can_transact:
                    return TransferResult(
                        success=False, error_message="Your account is frozen or closed."
                    )
                if not receiver.can_transact:
                    return TransferResult(
                        success=False, error_message="Recipient account is frozen or closed."
                    )

                if amount > sender.balance:
                    return TransferResult(
                        success=False,
                        error_message=(
                            f"Insufficient balance. "
                            f"Available: {fmt_currency(float(sender.balance))}"
                        ),
                    )

                with self.account_repo.session.begin_nested():
                    sender.balance -= amount
                    self._ensure_non_negative_balance(
                        sender.balance, "transfer"
                    )  # App-level guard
                    receiver.balance += amount

                    self.account_repo.update(sender)
                    self.account_repo.update(receiver)

                    # Log both transactions
                    now = _utcnow()
                    sender_txn = Transaction(
                        txn_id=generate_transaction_id(),
                        account_number=sender_acc_no,
                        type=TransactionType.TRANSFER_OUT,
                        amount=amount,
                        balance=sender.balance,
                        description=f"Transfer to {receiver_acc_no}",
                        category=cat,
                        target_account=receiver_acc_no,
                        timestamp=now,
                    )
                    receiver_txn = Transaction(
                        txn_id=generate_transaction_id(),
                        account_number=receiver_acc_no,
                        type=TransactionType.TRANSFER_IN,
                        amount=amount,
                        balance=receiver.balance,
                        description=f"Transfer from {sender_acc_no}",
                        category=cat,
                        target_account=sender_acc_no,
                        timestamp=now,
                    )
                    self.txn_repo.create(sender_txn)
                    self.txn_repo.create(receiver_txn)

                # Flush savepoint changes to disk (still inside account lock)
                self.account_repo.commit()

                # Capture values for use outside the lock
                sender_balance = sender.balance
                receiver_balance = receiver.balance
                sender_txn_id = sender_txn.txn_id
                receiver_txn_id = receiver_txn.txn_id

        except Exception:
            from unionbank.utils.logger import logger
            logger.error("Transfer failed, rolling back", exc_info=True)
            self.account_repo.rollback()
            return TransferResult(
                success=False,
                error_message="Transfer failed due to a database error. Please try again.",
            )

        # Send notifications (non-fatal if fails, outside lock)
        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_transfer_sent)(
                    sender_acc_no, amount, receiver_acc_no,
                    sender_balance, sender_txn_id,
                )
                NOTIFICATION_BREAKER.call(self.notif_service.notify_transfer_received)(
                    receiver_acc_no, amount, sender_acc_no,
                    receiver_balance, receiver_txn_id,
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping transfer notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send transfer notification", exc_info=True)

        result = TransferResult(
            success=True,
            sender_balance=sender_balance,
            receiver_balance=receiver_balance,
        )

        # Store idempotency result (non-fatal if fails, outside lock)
        if idempotency_key and self.idempotency_repo:
            try:
                record = IdempotencyRecord(
                    idempotency_key=idempotency_key,
                    account_number=sender_acc_no,
                    operation="transfer",
                    result_json=json.dumps({
                        "success": result.success,
                        "sender_balance": float(result.sender_balance),
                        "receiver_balance": float(result.receiver_balance),
                        "error_message": result.error_message,
                    }),
                    amount=amount,
                )
                self.idempotency_repo.create(record)
                self.idempotency_repo.commit()
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to persist idempotency record for transfer", exc_info=True)
                self.idempotency_repo.rollback()

        return result

    def get_statement(self, acc_no: str) -> list[Transaction]:
        return self.txn_repo.get_by_account(acc_no)

    def get_mini_statement(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        return self.txn_repo.get_mini(acc_no, limit)

    def apply_interest(self, acc_no: str) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.can_transact:
            return ServiceResult(success=False, message="Account is frozen or closed.")

        interest = Decimal(str(calculate_monthly_interest(
            float(account.balance), settings.SAVINGS_INTEREST_RATE
        )))
        if interest <= 0:
            return ServiceResult(success=False, message="No interest to apply.")

        account.balance += interest
        self.account_repo.update(account)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.INTEREST,
            amount=interest,
            balance=account.balance,
            description="Monthly interest credit",
            category="Savings",
        )
        self.txn_repo.create(txn)
        self.account_repo.commit()

        # Send notification (non-fatal if fails)
        if self.notif_service and account:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_interest)(
                    acc_no, interest, account.balance, txn.txn_id
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping interest notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send interest notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Interest of {fmt_currency(float(interest))} credited! "
                    f"New balance: {fmt_currency(float(account.balance))}",
            data={"interest": float(interest), "balance": float(account.balance)},
        )

    def get_category_totals(self) -> dict[str, Decimal]:
        return self.txn_repo.get_category_totals()

    def get_paginated_transactions(
        self,
        acc_no: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> tuple[list[Transaction], int]:
        return self.txn_repo.get_paginated(
            acc_no=acc_no, page=page, per_page=per_page,
            from_date=from_date, to_date=to_date, txn_type=txn_type,
        )

    def get_paginated_keyset(
        self,
        acc_no: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[datetime] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> KeysetPage[Transaction]:
        """Keyset (cursor-based) pagination — more efficient than OFFSET on large datasets.

        Args:
            acc_no:     Optional account filter.
            limit:      Max items to return (default 20).
            cursor:     Timestamp cursor from the previous page (None = first page).
            from_date:  Optional start date filter.
            to_date:    Optional end date filter.
            txn_type:   Optional transaction type filter.

        Returns:
            KeysetPage with items, next_cursor, and has_more flag.

        """
        return self.txn_repo.get_paginated_keyset(
            acc_no=acc_no, limit=limit, cursor=cursor,
            from_date=from_date, to_date=to_date, txn_type=txn_type,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Service
# ═══════════════════════════════════════════════════════════════════════════════


class AdminService:
    """Admin use-cases for account oversight."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        admin_repo: AdminRepositoryProtocol,
        audit_log_repo: Optional[AuditLogRepositoryProtocol] = None,
        notif_service: Optional[NotificationServiceProtocol] = None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.admin_repo = admin_repo
        self.audit_log_repo = audit_log_repo
        self.notif_service = notif_service

    def _audit_log(self, actor: str, action: str, target: Optional[str] = None,
                   details: Optional[str] = None, ip_address: Optional[str] = None,
                   reason: Optional[str] = None) -> None:
        """Write an immutable audit log entry (silently skip if no repo configured)."""
        if self.audit_log_repo:
            self.audit_log_repo.log(
                actor=actor, action=action, target=target,
                details=details, ip_address=ip_address, reason=reason,
            )
            self.audit_log_repo.commit()

    def list_accounts(self) -> list[Account]:
        return self.account_repo.get_all()

    def search_accounts(self, query: str) -> list[Account]:
        return self.account_repo.search(query)

    def freeze_account(self, acc_no: str, actor: str = "admin",
                       reason: Optional[str] = None) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_active and not account.is_frozen:
            return ServiceResult(success=False, message="Account is permanently closed.")
        if account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is already frozen.")

        self.account_repo.set_frozen(acc_no, True)
        # Freezing an account also deactivates it (preventing transactions)
        self.account_repo.set_active(acc_no, False)
        self.account_repo.commit()

        # Audit log
        self._audit_log(
            actor=actor, action="freeze", target=acc_no,
            details=f"Frozen account for {account.name}",
            reason=reason,
        )

        # Send notification (non-fatal if fails)
        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_account_frozen)(
                    acc_no, reason=reason or ""
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping freeze notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send freeze notification", exc_info=True)

        return ServiceResult(success=True, message=f"Account {acc_no} ({account.name}) has been frozen.")

    def unfreeze_account(self, acc_no: str, actor: str = "admin",
                         reason: Optional[str] = None) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is not frozen.")

        self.account_repo.set_frozen(acc_no, False)
        # NOTE: Unfreezing does NOT automatically reactivate.
        # If the account was previously closed (is_active=False, is_frozen=False),
        # an admin must explicitly reactivate it via a separate operation.
        self.account_repo.commit()

        # Audit log
        self._audit_log(
            actor=actor, action="unfreeze", target=acc_no,
            details=f"Unfrozen account for {account.name}",
            reason=reason,
        )

        # Send notification (non-fatal if fails)
        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_account_unfrozen)(acc_no)
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping unfreeze notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send unfreeze notification", exc_info=True)

        return ServiceResult(success=True, message=f"Account {acc_no} ({account.name}) has been unfrozen.")

    def delete_account(self, acc_no: str, actor: str = "admin",
                       reason: Optional[str] = None) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        acc_name = account.name
        self.account_repo.delete(acc_no)
        self.account_repo.commit()

        # Audit log
        self._audit_log(
            actor=actor, action="delete", target=acc_no,
            details=f"Deleted account for {acc_name}",
            reason=reason,
        )
        return ServiceResult(success=True, message=f"Account {acc_no} ({acc_name}) has been deleted.")

    def list_accounts_paginated(self, page: int = 1, per_page: int = 20) -> tuple[list[Account], int]:
        """Get accounts with pagination (delegates to the repository)."""
        return self.account_repo.get_all_paginated(page=page, per_page=per_page)

    def get_statistics(self) -> dict:
        """Compute bank-wide statistics using consolidated aggregate queries.

        Previously made 10 separate DB queries. Now uses 2 aggregate queries:
        1. get_statistics() on account_repo — single query for all account stats
        2. get_category_totals() on txn_repo — single query for category breakdown
           (also fetches total_dep, total_with, total_trans via type filter)
        """
        stats = self.account_repo.get_statistics()

        total_txns = self.txn_repo.count()
        total_dep = float(self.txn_repo.total_by_type("DEPOSIT"))
        total_with = float(self.txn_repo.total_by_type("WITHDRAW"))
        total_trans = float(self.txn_repo.total_by_type("TRANSFER_OUT"))
        category_totals = self.txn_repo.get_category_totals()
        sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

        return {
            **stats,
            "total_balance_formatted": fmt_currency(stats["total_balance"]),
            "total_dep": total_dep,
            "total_with": total_with,
            "total_trans": total_trans,
            "total_txns": total_txns,
            "sorted_categories": [{"name": c[0], "total": float(c[1])} for c in sorted_cats[:8]],
        }

    def change_admin_password(self, username: str, current_pwd: str, new_pwd: str,
                              actor: str = "admin") -> ServiceResult:
        admin = self.admin_repo.get_by_username(username)
        if admin is None:
            return ServiceResult(success=False, message="Admin not found.")
        if not verify_password(current_pwd, admin.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        self.admin_repo.update_password(username, hash_password(new_pwd))
        self.admin_repo.commit()

        # Audit log
        self._audit_log(
            actor=actor, action="password_reset", target=username,
            details="Admin password changed",
        )
        return ServiceResult(success=True, message="Admin password changed successfully.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Loan Service
# ═══════════════════════════════════════════════════════════════════════════════

# Loan product config per loan type (using LoanType enum values as keys)
LOAN_PRODUCTS = {
    LoanType.PERSONAL.value:  {"max_rate": 15.0, "min_rate": 10.0, "max_tenure": 60},
    LoanType.HOME.value:      {"max_rate": 10.0, "min_rate": 7.0,  "max_tenure": 360},
    LoanType.VEHICLE.value:   {"max_rate": 12.0, "min_rate": 8.0,  "max_tenure": 84},
    LoanType.EDUCATION.value: {"max_rate": 11.0, "min_rate": 7.5,  "max_tenure": 120},
    LoanType.BUSINESS.value:  {"max_rate": 18.0, "min_rate": 12.0,  "max_tenure": 120},
}

# Derive LOAN_TYPES from the enum (single source of truth)
LOAN_TYPES = [lt.value for lt in LoanType]


class LoanService:
    """Loan management use-cases (apply, approve, reject, pay EMI, view)."""

    def __init__(
        self,
        loan_repo: LoanRepositoryProtocol,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        audit_log_repo: Optional[AuditLogRepositoryProtocol] = None,
        notif_service: Optional[NotificationServiceProtocol] = None,
    ):
        self.loan_repo = loan_repo
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.audit_log_repo = audit_log_repo
        self.notif_service = notif_service

    def _audit_log(self, actor: str, action: str, target: Optional[str] = None,
                   details: Optional[str] = None) -> None:
        if self.audit_log_repo:
            self.audit_log_repo.log(
                actor=actor, action=action, target=target, details=details,
            )
            self.audit_log_repo.commit()

    # ── Getters ────────────────────────────────────────────────────────────────

    def list_loans(self, acc_no: str) -> list[Loan]:
        return self.loan_repo.get_by_account(acc_no)

    def get_loan(self, loan_id: str) -> Optional[Loan]:
        return self.loan_repo.get(loan_id)

    def list_pending(self) -> list[Loan]:
        return self.loan_repo.get_all_pending()

    def list_active(self) -> list[Loan]:
        return self.loan_repo.get_all_active()

    def list_all(self) -> list[Loan]:
        return self.loan_repo.get_all()

    def get_loan_statistics(self) -> dict:
        return {
            "total_pending": self.loan_repo.count_by_status(LoanStatus.PENDING.value),
            "total_approved": self.loan_repo.count_by_status(LoanStatus.APPROVED.value),
            "total_active": self.loan_repo.count_by_status(LoanStatus.ACTIVE.value),
            "total_closed": self.loan_repo.count_by_status(LoanStatus.CLOSED.value),
            "total_rejected": self.loan_repo.count_by_status(LoanStatus.REJECTED.value),
            "total_disbursed": float(self.loan_repo.total_disbursed()),
            "total_outstanding": float(self.loan_repo.total_outstanding()),
        }

    # ── Apply for loan ──────────────────────────────────────────────────────────

    def apply_loan(
        self,
        acc_no: str,
        loan_type: str,
        principal_amount: Decimal,
        interest_rate: Decimal,
        tenure_months: int,
        purpose: str = "",
    ) -> ServiceResult:
        """Apply for a new loan."""
        # Validate account
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.can_transact:
            return ServiceResult(success=False, message="Account is frozen or closed.")

        # Validate loan type
        if loan_type not in LOAN_TYPES:
            return ServiceResult(
                success=False,
                message=f"Invalid loan type. Choose from: {', '.join(LOAN_TYPES)}",
            )

        # Validate principal
        min_principal = 1000
        max_principal = 10000000  # 1 Crore
        if principal_amount < min_principal:
            return ServiceResult(
                success=False,
                message=f"Minimum loan amount is {fmt_currency(min_principal)}.",
            )
        if principal_amount > max_principal:
            return ServiceResult(
                success=False,
                message=f"Maximum loan amount is {fmt_currency(max_principal)}.",
            )

        # Validate tenure
        product = LOAN_PRODUCTS.get(loan_type, {})
        max_tenure = product.get("max_tenure", 60)
        if tenure_months < 1 or tenure_months > max_tenure:
            return ServiceResult(
                success=False,
                message=f"Tenure must be between 1 and {max_tenure} months for {loan_type} loans.",
            )

        # Validate interest rate
        min_rate = product.get("min_rate", 5.0)
        max_rate = product.get("max_rate", 20.0)
        if interest_rate < Decimal(str(min_rate)) or interest_rate > Decimal(str(max_rate)):
            return ServiceResult(
                success=False,
                message=f"Interest rate must be between {min_rate}% and {max_rate}% for {loan_type} loans.",
            )

        # Calculate EMI
        emi = Decimal(str(calculate_emi(
            float(principal_amount), float(interest_rate), tenure_months
        )))

        now = _utcnow()
        loan = Loan(
            loan_id=generate_loan_id(),
            account_number=acc_no,
            loan_type=loan_type,
            principal_amount=principal_amount,
            interest_rate=interest_rate,
            tenure_months=tenure_months,
            emi_amount=emi,
            amount_paid=Decimal("0.00"),
            remaining_amount=principal_amount,
            status=LoanStatus.PENDING.value,
            application_date=now,
            purpose=purpose,
        )
        self.loan_repo.create(loan)
        self.loan_repo.commit()

        # Audit log
        self._audit_log(
            actor=acc_no, action="loan_apply", target=loan.loan_id,
            details=f"Applied for {loan_type} loan of {fmt_currency(float(principal_amount))}",
        )

        return ServiceResult(
            success=True,
            message=f"Loan application submitted! Your EMI would be {fmt_currency(float(emi))}/month.",
            data={
                "loan_id": loan.loan_id,
                "emi_amount": float(emi),
            },
        )

    # ── Admin: Approve loan ─────────────────────────────────────────────────────

    def approve_loan(self, loan_id: str, admin_user: str = "admin") -> ServiceResult:
        """Approve a pending loan and disburse funds."""
        loan = self.loan_repo.get(loan_id)
        if loan is None:
            return ServiceResult(success=False, message="Loan not found.")
        if loan.status != LoanStatus.PENDING.value:
            return ServiceResult(
                success=False,
                message=f"Loan is already {loan.status.lower()}. Only pending loans can be approved.",
            )

        account = self.account_repo.get(loan.account_number)
        if account is None:
            return ServiceResult(success=False, message="Customer account not found.")
        if not account.can_transact:
            return ServiceResult(success=False, message="Customer account is frozen or closed.")

        now = _utcnow()
        # Calculate first EMI date (30 days from now)
        first_emi_date = now + timedelta(days=30)

        # Update loan status
        loan.status = LoanStatus.ACTIVE.value
        loan.approval_date = now
        loan.next_emi_date = first_emi_date
        self.loan_repo.update(loan)

        # Disburse funds to account
        account.balance += loan.principal_amount
        self.account_repo.update(account)

        # Create disbursement transaction
        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=loan.account_number,
            type=TransactionType.LOAN_DISBURSEMENT,
            amount=loan.principal_amount,
            balance=account.balance,
            description=f"{loan.loan_type} loan disbursement ({loan.loan_id})",
            category="Loan",
        )
        self.txn_repo.create(txn)
        self.loan_repo.commit()

        # Audit log
        self._audit_log(
            actor=admin_user, action="loan_approve", target=loan_id,
            details=f"Approved {loan.loan_type} loan of {fmt_currency(float(loan.principal_amount))} for {loan.account_number}",
        )

        # Send notification (non-fatal if fails)
        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_loan_approved)(
                    loan.account_number, loan.principal_amount,
                    loan.loan_type, loan.loan_id,
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping loan approval notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send loan approval notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Loan approved! {fmt_currency(float(loan.principal_amount))} disbursed to account {loan.account_number}.",
            data={"balance": float(account.balance)},
        )

    # ── Admin: Reject loan ──────────────────────────────────────────────────────

    def reject_loan(self, loan_id: str, reason: str = "",
                    admin_user: str = "admin") -> ServiceResult:
        """Reject a pending loan application."""
        loan = self.loan_repo.get(loan_id)
        if loan is None:
            return ServiceResult(success=False, message="Loan not found.")
        if loan.status != LoanStatus.PENDING.value:
            return ServiceResult(
                success=False,
                message=f"Loan is already {loan.status.lower()}. Only pending loans can be rejected.",
            )

        loan.status = LoanStatus.REJECTED.value
        if reason:
            loan.admin_notes = reason
        self.loan_repo.update(loan)
        self.loan_repo.commit()

        # Audit log
        self._audit_log(
            actor=admin_user, action="loan_reject", target=loan_id,
            details=f"Rejected {loan.loan_type} loan: {reason or 'No reason provided'}",
        )

        # Send notification (non-fatal if fails)
        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_loan_rejected)(
                    loan.account_number, loan.loan_type, loan.loan_id, reason
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping loan rejection notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send loan rejection notification", exc_info=True)

        return ServiceResult(
            success=True,
            message="Loan application rejected." + (f" Reason: {reason}" if reason else ""),
        )

    # ── Pay EMI ─────────────────────────────────────────────────────────────────

    def pay_emi(self, acc_no: str, loan_id: str, amount: Optional[Decimal] = None) -> ServiceResult:
        """Pay the monthly EMI for a loan.

        If amount is None, pays the full EMI amount.
        """
        loan = self.loan_repo.get(loan_id)
        if loan is None:
            return ServiceResult(success=False, message="Loan not found.")
        if loan.status not in (LoanStatus.APPROVED.value, LoanStatus.ACTIVE.value):
            return ServiceResult(
                success=False,
                message=f"Loan is {loan.status.lower()}. Only active loans can receive payments.",
            )
        if loan.account_number != acc_no:
            return ServiceResult(success=False, message="Loan does not belong to this account.")

        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.can_transact:
            return ServiceResult(success=False, message="Account is frozen or closed.")

        payment = amount if amount is not None else loan.emi_amount
        if payment <= 0:
            return ServiceResult(success=False, message="Payment amount must be positive.")

        if payment > account.balance:
            return ServiceResult(
                success=False,
                message=f"Insufficient balance. Available: {fmt_currency(float(account.balance))}",
            )

        remaining_debt = loan.remaining_amount
        actual_payment = min(payment, remaining_debt)

        # Deduct from account
        account.balance -= actual_payment
        self.account_repo.update(account)

        # Update loan
        loan.amount_paid += actual_payment
        loan.remaining_amount -= actual_payment

        # Update next EMI date (+30 days)
        if loan.next_emi_date:
            loan.next_emi_date = loan.next_emi_date + timedelta(days=30)
        else:
            loan.next_emi_date = _utcnow() + timedelta(days=30)

        # Check if loan is fully paid
        if loan.remaining_amount <= 0:
            loan.status = LoanStatus.CLOSED.value
            loan.remaining_amount = Decimal("0.00")
            loan.next_emi_date = None

        self.loan_repo.update(loan)

        # Create repayment transaction
        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.LOAN_REPAYMENT,
            amount=actual_payment,
            balance=account.balance,
            description=f"EMI payment for {loan.loan_type} loan ({loan.loan_id})",
            category="Loan",
        )
        self.txn_repo.create(txn)
        self.loan_repo.commit()

        is_closed = loan.status == "CLOSED"
        msg = f"EMI of {fmt_currency(float(actual_payment))} paid for {loan.loan_type} loan."
        if is_closed:
            msg += " 🎉 Loan fully paid off! Congratulations!"

        # Send notification (non-fatal if fails)
        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_emi_paid)(
                    acc_no, actual_payment, loan.loan_type, loan.loan_id,
                    loan.remaining_amount,
                )
                if is_closed:
                    NOTIFICATION_BREAKER.call(self.notif_service.notify_loan_closed)(
                        acc_no, loan.loan_type, loan.loan_id
                    )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger
                logger.warning("Notification circuit breaker open, skipping EMI notification")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send EMI notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=msg,
            data={
                "amount_paid": float(actual_payment),
                "remaining_amount": float(loan.remaining_amount),
                "balance": float(account.balance),
                "is_closed": is_closed,
            },
        )

    # ── Calculate EMI preview (no application) ──────────────────────────────────

    def calculate_emi_preview(
        self, principal: float, annual_rate: float, tenure_months: int
    ) -> dict:
        """Calculate EMI preview without creating an application."""
        emi = calculate_emi(principal, annual_rate, tenure_months)
        total_payable = round(emi * tenure_months, 2)
        total_interest = round(total_payable - principal, 2)

        return {
            "principal": principal,
            "annual_rate": annual_rate,
            "tenure_months": tenure_months,
            "emi": emi,
            "total_payable": total_payable,
            "total_interest": total_interest,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings Goal Service
# ═══════════════════════════════════════════════════════════════════════════════


class SavingsGoalService:
    """Savings goal use-cases."""

    def __init__(
        self,
        goal_repo: SavingsGoalRepositoryProtocol,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
    ):
        self.goal_repo = goal_repo
        self.account_repo = account_repo
        self.txn_repo = txn_repo

    def list_goals(self, acc_no: str) -> list[SavingsGoal]:
        return self.goal_repo.get_by_account(acc_no)

    def create_goal(self, acc_no: str, name: str, target_amount: Decimal,
                    target_date: Optional[str] = None) -> ServiceResult:
        if not name or len(name) < 2:
            return ServiceResult(success=False, message="Goal name must be at least 2 characters.")
        if target_amount <= 0:
            return ServiceResult(success=False, message="Target amount must be positive.")

        goal = SavingsGoal(
            goal_id=generate_goal_id(),
            account_number=acc_no,
            name=name,
            target_amount=target_amount,
            target_date=target_date,
        )
        self.goal_repo.create(goal)
        self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' created!")

    def contribute(self, acc_no: str, goal_id: str, amount: Decimal) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if amount > account.balance:
            return ServiceResult(success=False, message="Insufficient balance.")

        goal = self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        # Deduct from account
        account.balance -= amount
        self.account_repo.update(account)

        # Log transfer-out transaction
        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.TRANSFER_OUT,
            amount=amount,
            balance=account.balance,
            description=f"Savings goal: {goal.name}",
            category="Savings",
        )
        self.txn_repo.create(txn)

        # Contribute to goal
        self.goal_repo.contribute(goal_id, amount)
        self.account_repo.commit()

        return ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} contributed to '{goal.name}'!",
        )

    def delete_goal(self, acc_no: str, goal_id: str) -> ServiceResult:
        goal = self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        refund = goal.current_amount
        name = goal.name
        self.goal_repo.delete(goal_id)

        # Refund to balance
        if refund > 0:
            account = self.account_repo.get(acc_no)
            if account:
                account.balance += refund
                self.account_repo.update(account)

        self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' deleted. Amount refunded.")
