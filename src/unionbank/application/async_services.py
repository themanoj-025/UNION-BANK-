"""
application/async_services.py  –  Async use-case service classes.

These mirror the synchronous services in services.py but use async/await for
all database operations. They are used when the application is configured
with a PostgreSQL DATABASE_URL (async via asyncpg).

For SQLite (which doesn't support async), the synchronous services in
services.py are used instead.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional

from unionbank.config import settings
from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import (
    Account,
    IdempotencyRecord,
    SavingsGoal,
    ServiceResult,
    Transaction,
    TransactionType,
    TransferResult,
)
from unionbank.domain.interest import calculate_monthly_interest
from unionbank.utils.formatting import (
    fmt_currency,
    generate_account_number,
    generate_goal_id,
    generate_transaction_id,
)
from unionbank.utils.hashing import hash_password, verify_password

from .interfaces import (
    KeysetPage,
)

TRANSACTION_CATEGORIES = settings.TRANSACTION_CATEGORIES
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOGIN_LOCKOUT_MINUTES = settings.LOGIN_LOCKOUT_MINUTES


# ═══════════════════════════════════════════════════════════════════════════════
#  Async per-account concurrency lock
# ═══════════════════════════════════════════════════════════════════════════════

_account_locks: dict[str, asyncio.Lock] = {}


def _get_account_lock(*acc_nos: str) -> asyncio.Lock:
    """
    Get an asyncio.Lock for the given accounts, creating if needed.

    For single-account operations, returns the lock for that account.
    For multi-account operations (transfer), returns a lock based on the
    sorted account numbers to prevent deadlocks.
    """
    # Use a combined key for multi-account operations
    sorted_nos = sorted(acc_nos)
    key = ":".join(sorted_nos)
    if key not in _account_locks:
        _account_locks[key] = asyncio.Lock()
    return _account_locks[key]


# ═══════════════════════════════════════════════════════════════════════════════
#  Async Transaction Service
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncTransactionService:
    """
    Async transaction use-cases (deposit, withdraw, transfer, statement, interest).

    All database operations are awaited. Uses asyncio.Lock for per-account
    serialization to prevent lost updates under concurrent access.
    """

    def __init__(
        self,
        account_repo,  # AsyncSqlAlchemyAccountRepository
        txn_repo,  # AsyncSqlAlchemyTransactionRepository
        notif_service=None,
        idempotency_repo=None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.notif_service = notif_service
        self.idempotency_repo = idempotency_repo

    def _ensure_non_negative_balance(self, balance: Decimal, operation: str = "transaction") -> None:
        """App-level guard: raise ValueError if balance would go negative."""
        if balance < Decimal("0.00"):
            raise ValueError(f"Insufficient balance for {operation}.")

    async def _check_idempotency(
        self, idempotency_key: Optional[str], acc_no: str, operation: str, amount: Decimal
    ) -> Optional[ServiceResult]:
        """Check if a request with this idempotency_key has already been processed."""
        if not idempotency_key or not self.idempotency_repo:
            return None
        existing = await self.idempotency_repo.get(idempotency_key)
        if existing is not None:
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

    async def _store_idempotency(
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
            await self.idempotency_repo.create(record)
            await self.idempotency_repo.commit()
        except Exception:
            from unionbank.utils.logger import logger
            logger.warning("Failed to persist idempotency record", exc_info=True)
            await self.idempotency_repo.rollback()

    async def deposit(
        self, acc_no: str, amount: Decimal, category: str = "General",
        idempotency_key: Optional[str] = None
    ) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        # Check idempotency first (outside lock — read-only)
        cached = await self._check_idempotency(idempotency_key, acc_no, "deposit", amount)
        if cached is not None:
            return cached

        # Serialize writes to this account
        lock = _get_account_lock(acc_no)
        async with lock:
            account = await self.account_repo.get(acc_no)
            if account is None:
                return ServiceResult(success=False, message="Account not found.")
            if not account.can_transact:
                status = "frozen" if account.is_frozen else "closed"
                return ServiceResult(success=False, message=f"Account is {status}.")

            account.balance += amount
            await self.account_repo.update(account)

            txn = Transaction(
                txn_id=generate_transaction_id(),
                account_number=acc_no,
                type=TransactionType.DEPOSIT,
                amount=amount,
                balance=account.balance,
                description="Deposit",
                category=category if category in TRANSACTION_CATEGORIES else "General",
            )
            await self.txn_repo.create(txn)
            await self.account_repo.commit()

        result = ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} deposited successfully. "
                    f"New balance: {fmt_currency(float(account.balance))}",
            data={"balance": float(account.balance)},
        )

        # Store idempotency result (non-fatal if fails)
        await self._store_idempotency(idempotency_key, acc_no, "deposit", amount, result)

        # Send notification (non-fatal if fails)
        if self.notif_service and account:
            try:
                await self.notif_service.notify_deposit(
                    acc_no, amount, account.balance, txn.txn_id
                )
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send deposit notification", exc_info=True)

        return result

    async def withdraw(
        self, acc_no: str, amount: Decimal, category: str = "General",
        idempotency_key: Optional[str] = None
    ) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        # Check idempotency first (outside lock — read-only)
        cached = await self._check_idempotency(idempotency_key, acc_no, "withdraw", amount)
        if cached is not None:
            return cached

        # Serialize writes to this account
        lock = _get_account_lock(acc_no)
        async with lock:
            account = await self.account_repo.get(acc_no)
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
            self._ensure_non_negative_balance(account.balance, "withdraw")
            await self.account_repo.update(account)

            txn = Transaction(
                txn_id=generate_transaction_id(),
                account_number=acc_no,
                type=TransactionType.WITHDRAW,
                amount=amount,
                balance=account.balance,
                description="Withdrawal",
                category=category if category in TRANSACTION_CATEGORIES else "General",
            )
            await self.txn_repo.create(txn)
            await self.account_repo.commit()

        result = ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} withdrawn successfully. "
                    f"New balance: {fmt_currency(float(account.balance))}",
            data={"balance": float(account.balance)},
        )

        # Store idempotency result (non-fatal if fails)
        await self._store_idempotency(idempotency_key, acc_no, "withdraw", amount, result)

        # Send notification (non-fatal if fails)
        if self.notif_service and account:
            try:
                await self.notif_service.notify_withdraw(
                    acc_no, amount, account.balance, txn.txn_id
                )
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send withdraw notification", exc_info=True)

        return result

    async def transfer(
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
            existing = await self.idempotency_repo.get(idempotency_key)
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

        # Serialize both accounts to prevent lost updates
        lock = _get_account_lock(sender_acc_no, receiver_acc_no)
        async with lock:
            sender = await self.account_repo.get(sender_acc_no)
            receiver = await self.account_repo.get(receiver_acc_no)

            if sender is None:
                return TransferResult(success=False, error_message="Sender account not found.")
            if receiver is None:
                return TransferResult(success=False, error_message="Recipient account not found.")

            if not sender.can_transact:
                return TransferResult(success=False, error_message="Your account is frozen or closed.")
            if not receiver.can_transact:
                return TransferResult(success=False, error_message="Recipient account is frozen or closed.")

            if amount > sender.balance:
                return TransferResult(
                    success=False,
                    error_message=f"Insufficient balance. Available: {fmt_currency(float(sender.balance))}",
                )

            # Perform atomic transfer
            try:
                sender.balance -= amount
                self._ensure_non_negative_balance(sender.balance, "transfer")
                receiver.balance += amount

                await self.account_repo.update(sender)
                await self.account_repo.update(receiver)

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
                await self.txn_repo.create(sender_txn)
                await self.txn_repo.create(receiver_txn)
                await self.account_repo.commit()
            except Exception:
                from unionbank.utils.logger import logger
                logger.error("Transfer failed, rolling back", exc_info=True)
                await self.account_repo.rollback()
                return TransferResult(
                    success=False,
                    error_message="Transfer failed due to a database error. Please try again.",
                )

        # Send notifications (non-fatal if fails, outside lock)
        if self.notif_service:
            try:
                await self.notif_service.notify_transfer_sent(
                    sender_acc_no, amount, receiver_acc_no,
                    sender.balance, sender_txn.txn_id,
                )
                await self.notif_service.notify_transfer_received(
                    receiver_acc_no, amount, sender_acc_no,
                    receiver.balance, receiver_txn.txn_id,
                )
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send transfer notification", exc_info=True)

        result = TransferResult(
            success=True,
            sender_balance=sender.balance,
            receiver_balance=receiver.balance,
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
                await self.idempotency_repo.create(record)
                await self.idempotency_repo.commit()
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to persist idempotency record for transfer", exc_info=True)
                await self.idempotency_repo.rollback()

        return result

    async def get_statement(self, acc_no: str) -> list[Transaction]:
        return await self.txn_repo.get_by_account(acc_no)

    async def get_mini_statement(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        return await self.txn_repo.get_mini(acc_no, limit)

    async def apply_interest(self, acc_no: str) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
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
        await self.account_repo.update(account)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.INTEREST,
            amount=interest,
            balance=account.balance,
            description="Monthly interest credit",
            category="Savings",
        )
        await self.txn_repo.create(txn)
        await self.account_repo.commit()

        # Send notification (non-fatal if fails)
        if self.notif_service and account:
            try:
                await self.notif_service.notify_interest(
                    acc_no, interest, account.balance, txn.txn_id
                )
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send interest notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Interest of {fmt_currency(float(interest))} credited! "
                    f"New balance: {fmt_currency(float(account.balance))}",
            data={"interest": float(interest), "balance": float(account.balance)},
        )

    async def get_category_totals(self) -> dict[str, Decimal]:
        return await self.txn_repo.get_category_totals()

    async def get_paginated_transactions(
        self,
        acc_no: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> tuple[list[Transaction], int]:
        return await self.txn_repo.get_paginated(
            acc_no=acc_no, page=page, per_page=per_page,
            from_date=from_date, to_date=to_date, txn_type=txn_type,
        )

    async def get_paginated_keyset(
        self,
        acc_no: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[datetime] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> KeysetPage[Transaction]:
        """Keyset (cursor-based) pagination."""
        return await self.txn_repo.get_paginated_keyset(
            acc_no=acc_no, limit=limit, cursor=cursor,
            from_date=from_date, to_date=to_date, txn_type=txn_type,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Async Account Service
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncAccountService:
    """Async customer account management use-cases."""

    def __init__(
        self,
        account_repo,  # AsyncSqlAlchemyAccountRepository
        txn_repo,  # AsyncSqlAlchemyTransactionRepository
        token_version_repo=None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.token_version_repo = token_version_repo

    async def get_profile(self, acc_no: str) -> Optional[Account]:
        return await self.account_repo.get(acc_no)

    async def update_profile(self, acc_no: str, **kwargs) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        for key, value in kwargs.items():
            if hasattr(account, key) and value is not None:
                setattr(account, key, value)

        await self.account_repo.update(account)
        await self.account_repo.commit()
        return ServiceResult(success=True, message="Profile updated successfully.")

    async def change_password(self, acc_no: str, current_pwd: str, new_pwd: str) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(current_pwd, account.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        account.password = hash_password(new_pwd)
        await self.account_repo.update(account)

        # Increment token version to invalidate all existing JWTs
        if self.token_version_repo:
            await self.token_version_repo.increment(acc_no)

        await self.account_repo.commit()
        return ServiceResult(success=True, message="Password changed successfully.")

    async def close_account(self, acc_no: str, password: str) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(password, account.password):
            return ServiceResult(success=False, message="Incorrect password.")

        account.is_active = False
        await self.account_repo.update(account)
        await self.account_repo.commit()
        return ServiceResult(success=True, message="Account closed successfully.")

    async def get_balance(self, acc_no: str) -> Optional[Decimal]:
        account = await self.account_repo.get(acc_no)
        return account.balance if account else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Async Auth Service
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncAuthService:
    """Async authentication and authorization use-cases."""

    def __init__(
        self,
        account_repo,  # AsyncSqlAlchemyAccountRepository
        admin_repo,  # AsyncSqlAlchemyAdminRepository
        login_attempt_repo,  # AsyncSqlAlchemyLoginAttemptRepository
        token_version_repo=None,
        notif_service=None,
    ):
        self.account_repo = account_repo
        self.admin_repo = admin_repo
        self.login_attempt_repo = login_attempt_repo
        self.token_version_repo = token_version_repo
        self.notif_service = notif_service

    async def customer_login(self, acc_no: str, password: str) -> ServiceResult:
        """Authenticate a customer login."""
        # Rate limiting check
        is_locked, remaining = await self.login_attempt_repo.is_locked(acc_no)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Account locked. Try again in {remaining} minute(s).",
            )

        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if account.is_frozen:
            return ServiceResult(success=False, message="Account is frozen. Please contact the bank.")

        if not account.is_active:
            return ServiceResult(success=False, message="Account has been closed.")

        if not verify_password(password, account.password):
            remaining = await self.login_attempt_repo.record_failure(
                acc_no, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
            )
            await self.login_attempt_repo.commit()
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

        await self.login_attempt_repo.reset(acc_no)
        await self.login_attempt_repo.commit()
        return ServiceResult(success=True, data={"account_number": acc_no, "role": "customer"})

    async def customer_register(
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
        await self.account_repo.create(account)
        await self.account_repo.commit()

        # Send welcome notification (non-fatal if fails)
        if self.notif_service:
            try:
                await self.notif_service.notify_welcome(acc_no)
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send welcome notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Account created successfully! Account number: {acc_no}",
            data={"account_number": acc_no},
        )

    async def admin_login(self, username: str, password: str) -> ServiceResult:
        """Authenticate an admin login."""
        lock_key = f"admin_{username}"
        is_locked, remaining = await self.login_attempt_repo.is_locked(lock_key)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Admin account locked. Try again in {remaining} minute(s).",
            )

        admin = await self.admin_repo.get_by_username(username)
        if admin and verify_password(password, admin.password):
            await self.login_attempt_repo.reset(lock_key)
            await self.login_attempt_repo.commit()
            return ServiceResult(success=True, data={"username": username, "role": "admin"})

        remaining = await self.login_attempt_repo.record_failure(
            lock_key, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
        )
        await self.login_attempt_repo.commit()
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
#  Async Admin Service
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncAdminService:
    """Async admin use-cases for account oversight."""

    def __init__(
        self,
        account_repo,  # AsyncSqlAlchemyAccountRepository
        txn_repo,  # AsyncSqlAlchemyTransactionRepository
        admin_repo,  # AsyncSqlAlchemyAdminRepository
        audit_log_repo=None,
        notif_service=None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.admin_repo = admin_repo
        self.audit_log_repo = audit_log_repo
        self.notif_service = notif_service

    async def _audit_log(self, actor: str, action: str, target: Optional[str] = None,
                   details: Optional[str] = None, ip_address: Optional[str] = None,
                   reason: Optional[str] = None) -> None:
        """Write an immutable audit log entry."""
        if self.audit_log_repo:
            await self.audit_log_repo.log(
                actor=actor, action=action, target=target,
                details=details, ip_address=ip_address, reason=reason,
            )
            await self.audit_log_repo.commit()

    async def list_accounts(self) -> list[Account]:
        return await self.account_repo.get_all()

    async def search_accounts(self, query: str) -> list[Account]:
        return await self.account_repo.search(query)

    async def freeze_account(self, acc_no: str, actor: str = "admin",
                       reason: Optional[str] = None) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_active and not account.is_frozen:
            return ServiceResult(success=False, message="Account is permanently closed.")
        if account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is already frozen.")

        await self.account_repo.set_frozen(acc_no, True)
        await self.account_repo.set_active(acc_no, False)
        await self.account_repo.commit()

        await self._audit_log(
            actor=actor, action="freeze", target=acc_no,
            details=f"Frozen account for {account.name}", reason=reason,
        )

        if self.notif_service:
            try:
                await self.notif_service.notify_account_frozen(acc_no, reason=reason or "")
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send freeze notification", exc_info=True)

        return ServiceResult(success=True, message=f"Account {acc_no} ({account.name}) has been frozen.")

    async def unfreeze_account(self, acc_no: str, actor: str = "admin",
                         reason: Optional[str] = None) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is not frozen.")

        await self.account_repo.set_frozen(acc_no, False)
        await self.account_repo.commit()

        await self._audit_log(
            actor=actor, action="unfreeze", target=acc_no,
            details=f"Unfrozen account for {account.name}", reason=reason,
        )

        if self.notif_service:
            try:
                await self.notif_service.notify_account_unfrozen(acc_no)
            except Exception:
                from unionbank.utils.logger import logger
                logger.warning("Failed to send unfreeze notification", exc_info=True)

        return ServiceResult(success=True, message=f"Account {acc_no} ({account.name}) has been unfrozen.")

    async def delete_account(self, acc_no: str, actor: str = "admin",
                       reason: Optional[str] = None) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        acc_name = account.name
        await self.account_repo.delete(acc_no)
        await self.account_repo.commit()

        await self._audit_log(
            actor=actor, action="delete", target=acc_no,
            details=f"Deleted account for {acc_name}", reason=reason,
        )
        return ServiceResult(success=True, message=f"Account {acc_no} ({acc_name}) has been deleted.")

    async def list_accounts_paginated(self, page: int = 1, per_page: int = 20) -> tuple[list[Account], int]:
        """Get accounts with pagination."""
        return await self.account_repo.get_all_paginated(page=page, per_page=per_page)

    async def get_statistics(self) -> dict:
        """Compute bank-wide statistics."""
        stats = await self.account_repo.get_statistics()

        total_txns = await self.txn_repo.count()
        total_dep = float(await self.txn_repo.total_by_type("DEPOSIT"))
        total_with = float(await self.txn_repo.total_by_type("WITHDRAW"))
        total_trans = float(await self.txn_repo.total_by_type("TRANSFER_OUT"))
        category_totals = await self.txn_repo.get_category_totals()
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

    async def change_admin_password(self, username: str, current_pwd: str, new_pwd: str,
                              actor: str = "admin") -> ServiceResult:
        admin = await self.admin_repo.get_by_username(username)
        if admin is None:
            return ServiceResult(success=False, message="Admin not found.")
        if not verify_password(current_pwd, admin.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        await self.admin_repo.update_password(username, hash_password(new_pwd))
        await self.admin_repo.commit()

        await self._audit_log(
            actor=actor, action="password_reset", target=username,
            details="Admin password changed",
        )
        return ServiceResult(success=True, message="Admin password changed successfully.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Async Savings Goal Service
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSavingsGoalService:
    """Async savings goal use-cases."""

    def __init__(
        self,
        goal_repo,  # AsyncSqlAlchemySavingsGoalRepository
        account_repo,  # AsyncSqlAlchemyAccountRepository
        txn_repo,  # AsyncSqlAlchemyTransactionRepository
    ):
        self.goal_repo = goal_repo
        self.account_repo = account_repo
        self.txn_repo = txn_repo

    async def list_goals(self, acc_no: str) -> list[SavingsGoal]:
        return await self.goal_repo.get_by_account(acc_no)

    async def create_goal(self, acc_no: str, name: str, target_amount: Decimal,
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
        await self.goal_repo.create(goal)
        await self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' created!")

    async def contribute(self, acc_no: str, goal_id: str, amount: Decimal) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if amount > account.balance:
            return ServiceResult(success=False, message="Insufficient balance.")

        goal = await self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        # Deduct from account
        account.balance -= amount
        await self.account_repo.update(account)

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
        await self.txn_repo.create(txn)

        # Contribute to goal
        await self.goal_repo.contribute(goal_id, amount)
        await self.account_repo.commit()

        return ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} contributed to '{goal.name}'!",
        )

    async def delete_goal(self, acc_no: str, goal_id: str) -> ServiceResult:
        goal = await self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        refund = goal.current_amount
        name = goal.name
        await self.goal_repo.delete(goal_id)

        # Refund to balance
        if refund > 0:
            account = await self.account_repo.get(acc_no)
            if account:
                account.balance += refund
                await self.account_repo.update(account)

        await self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' deleted. Amount refunded.")
