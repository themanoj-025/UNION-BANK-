"""
application/interfaces.py  –  Repository protocols (interfaces).

These ABCs/Protocols define the contract between the application layer
and the infrastructure layer. No concrete DB code lives here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, Optional, Protocol, TypeVar, runtime_checkable

from domain.entities import (
    Account,
    AdminUser,
    Loan,
    LoginAttempt,
    Notification,
    NotificationPreference,
    RefreshToken,
    SavingsGoal,
    TokenVersion,
    Transaction,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Shared types
# ═══════════════════════════════════════════════════════════════════════════════


T = TypeVar("T")


@dataclass(frozen=True)
class KeysetPage(Generic[T]):
    """A page of results returned by keyset (cursor-based) pagination.

    Attributes:
        items:       The items on this page.
        cursor:      Opaque cursor value to pass to the next page request.
                     Use the last item's timestamp for cursor-based pagination.
        has_more:    True if there are more results beyond this page.
        cursor_key:  The name of the field used as the cursor (e.g. 'timestamp').
    """
    items: list[T] = field(default_factory=list)
    cursor: Any = None
    has_more: bool = False
    cursor_key: str = "timestamp"


# ═══════════════════════════════════════════════════════════════════════════════
#  Repository Protocols
# ═══════════════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════════════
#  Account Repository Protocol
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class AccountRepositoryProtocol(Protocol):
    """Interface for account data access."""

    def get(self, acc_no: str) -> Optional[Account]: ...

    def get_all(self) -> list[Account]: ...

    def exists(self, acc_no: str) -> bool: ...

    def create(self, account: Account) -> Account: ...

    def update(self, account: Account) -> Account: ...

    def update_balance(self, acc_no: str, new_balance: Decimal) -> bool: ...

    def set_active(self, acc_no: str, active: bool) -> bool: ...

    def set_frozen(self, acc_no: str, frozen: bool) -> bool: ...

    def delete(self, acc_no: str) -> bool: ...

    def search(self, query: str) -> list[Account]: ...

    def count(self) -> int: ...

    def total_balance(self) -> Decimal: ...

    def active_count(self) -> int: ...

    def frozen_count(self) -> int: ...

    def closed_count(self) -> int: ...

    def get_by_email(self, email: str) -> Optional[Account]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
#  Transaction Repository Protocol
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class TransactionRepositoryProtocol(Protocol):
    """Interface for transaction data access."""

    def get_by_account(self, acc_no: str) -> list[Transaction]: ...

    def get_mini(self, acc_no: str, limit: int = 5) -> list[Transaction]: ...

    def create(self, transaction: Transaction) -> Transaction: ...

    def get_all(self) -> list[Transaction]: ...

    def total_by_type(self, txn_type: str) -> Decimal: ...

    def count(self) -> int: ...

    def count_by_account(self, acc_no: str) -> int: ...

    def get_category_totals(self) -> dict[str, Decimal]: ...

    def get_paginated(
        self,
        acc_no: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> tuple[list[Transaction], int]: ...

    def get_paginated_keyset(
        self,
        acc_no: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[datetime] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> KeysetPage[Transaction]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Repository Protocol
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class AdminRepositoryProtocol(Protocol):
    """Interface for admin user data access."""

    def get_by_username(self, username: str) -> Optional[AdminUser]: ...

    def create(self, admin: AdminUser) -> AdminUser: ...

    def update_password(self, username: str, new_hashed: str) -> bool: ...

    def update_totp(self, username: str, totp_secret: Optional[str], totp_enabled: bool) -> bool: ...

    def admin_count(self) -> int: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings Goal Repository Protocol
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class SavingsGoalRepositoryProtocol(Protocol):
    """Interface for savings goal data access."""

    def get_by_account(self, acc_no: str) -> list[SavingsGoal]: ...

    def get(self, goal_id: str) -> Optional[SavingsGoal]: ...

    def create(self, goal: SavingsGoal) -> SavingsGoal: ...

    def update(self, goal: SavingsGoal) -> SavingsGoal: ...

    def contribute(self, goal_id: str, amount: Decimal) -> Optional[SavingsGoal]: ...

    def delete(self, goal_id: str) -> Optional[SavingsGoal]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
#  Login Attempt Repository Protocol
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class LoginAttemptRepositoryProtocol(Protocol):
    """Interface for rate-limiting data access."""

    def get(self, key: str) -> Optional[LoginAttempt]: ...

    def record_failure(
        self, key: str, max_attempts: int = 5, lockout_minutes: int = 15
    ) -> int: ...

    def is_locked(self, key: str, max_attempts: int = 5) -> tuple[bool, int]: ...

    def reset(self, key: str) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
#  Token Version Repository Protocol
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class TokenVersionRepositoryProtocol(Protocol):
    """Interface for JWT token version tracking."""

    def get_version(self, account_number: str) -> int: ...

    def increment(self, account_number: str) -> int: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
#  Loan Repository Protocol
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class LoanRepositoryProtocol(Protocol):
    """Interface for loan data access."""

    def get(self, loan_id: str) -> Optional[Loan]: ...

    def get_by_account(self, acc_no: str) -> list[Loan]: ...

    def get_all_pending(self) -> list[Loan]: ...

    def get_all_active(self) -> list[Loan]: ...

    def get_all(self) -> list[Loan]: ...

    def create(self, loan: Loan) -> Loan: ...

    def update(self, loan: Loan) -> Loan: ...

    def count_by_status(self, status: str) -> int: ...

    def total_disbursed(self) -> Decimal: ...

    def total_outstanding(self) -> Decimal: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
#  Notification Repository Protocols
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class NotificationRepositoryProtocol(Protocol):
    """Interface for in-app notification data access."""

    def get(self, notif_id: str) -> Optional[Notification]: ...

    def get_by_account(self, acc_no: str, limit: int = 50) -> list[Notification]: ...

    def get_unread_count(self, acc_no: str) -> int: ...

    def get_unread(self, acc_no: str, limit: int = 20) -> list[Notification]: ...

    def create(self, notification: Notification) -> Notification: ...

    def mark_as_read(self, notif_id: str) -> bool: ...

    def mark_all_as_read(self, acc_no: str) -> int: ...

    def delete_old(self, days: int = 30) -> int: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


@runtime_checkable
class NotificationPreferenceRepositoryProtocol(Protocol):
    """Interface for notification preference data access."""

    def get(self, acc_no: str) -> Optional[NotificationPreference]: ...

    def create_or_update(self, pref: NotificationPreference) -> NotificationPreference: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
#  Notification Sender Protocol
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class NotificationSenderProtocol(Protocol):
    """Interface for sending real-time notifications via email/SMS."""

    def send_email(self, to_email: str, subject: str, body: str) -> bool: ...

    def send_sms(self, to_phone: str, message: str) -> bool: ...


# ═══════════════════════════════════════════════════════════════════════════════
#  Audit Log Repository Protocol
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class RefreshTokenRepositoryProtocol(Protocol):
    """Interface for DB-backed refresh token storage."""

    def get(self, token_id: str) -> Optional[RefreshToken]: ...

    def get_by_account(self, account_number: str) -> list[RefreshToken]: ...

    def create(self, token: RefreshToken) -> RefreshToken: ...

    def revoke(self, token_id: str) -> bool: ...

    def revoke_all_for_account(self, account_number: str) -> int: ...

    def clean_expired(self) -> int: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


@runtime_checkable
class AuditLogRepositoryProtocol(Protocol):
    """Interface for admin audit log."""

    def log(self, actor: str, action: str, target: Optional[str] = None,
            details: Optional[str] = None, ip_address: Optional[str] = None,
            reason: Optional[str] = None) -> None: ...

    def get_recent(self, limit: int = 50) -> list: ...

    def get_by_actor(self, actor: str, limit: int = 50) -> list: ...

    def get_by_action(self, action: str, limit: int = 50) -> list: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
