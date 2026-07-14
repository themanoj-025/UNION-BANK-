"""
domain/entities.py  –  Pure domain entities (no framework/DB imports).

All monetary values use Decimal — never float — to avoid precision loss.
Timestamps are timezone-aware datetime objects, never strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, auto
from typing import Optional


def _utcnow() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════════════════════


class AccountStatus(Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class TransactionType(Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    INTEREST = "INTEREST"
    LOAN_DISBURSEMENT = "LOAN_DISBURSEMENT"
    LOAN_REPAYMENT = "LOAN_REPAYMENT"


class LoanType(Enum):
    PERSONAL = "Personal"
    HOME = "Home"
    VEHICLE = "Vehicle"
    EDUCATION = "Education"
    BUSINESS = "Business"


class LoanStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


# ═══════════════════════════════════════════════════════════════════════════════
#  Entities
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Customer:
    """Customer personal information (no account data)."""

    name: str
    age: int
    gender: str
    mobile: str
    email: str
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class Account:
    """Customer account — source of truth for balances and status."""

    account_number: str
    name: str
    age: int = 18
    gender: str = ""
    mobile: str = ""
    email: str = ""
    password: str = ""
    balance: Decimal = Decimal("0.00")
    is_active: bool = True
    is_frozen: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    @property
    def status(self) -> AccountStatus:
        if self.is_frozen:
            return AccountStatus.FROZEN
        if not self.is_active:
            return AccountStatus.CLOSED
        return AccountStatus.ACTIVE

    @property
    def can_transact(self) -> bool:
        return self.is_active and not self.is_frozen

    def __repr__(self) -> str:
        return f"<Account {self.account_number} ({self.name})>"


@dataclass
class Transaction:
    """Transaction record — append-only log of all account activity."""

    txn_id: str
    account_number: str
    type: TransactionType
    amount: Decimal
    balance: Decimal
    description: str = ""
    category: str = "General"
    target_account: Optional[str] = None
    timestamp: datetime = field(default_factory=_utcnow)

    def __repr__(self) -> str:
        return f"<Transaction {self.txn_id} ({self.type.value} {self.amount})>"


@dataclass
class SavingsGoal:
    """Savings goal — linked to a customer account."""

    goal_id: str
    account_number: str
    name: str
    target_amount: Decimal
    current_amount: Decimal = Decimal("0.00")
    target_date: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    is_completed: bool = False

    @property
    def progress_pct(self) -> float:
        if self.target_amount <= 0:
            return 0.0
        return float(self.current_amount / self.target_amount * 100)

    @property
    def remaining(self) -> Decimal:
        return max(Decimal("0.00"), self.target_amount - self.current_amount)


@dataclass
class AdminUser:
    """Admin user."""

    id: Optional[int] = None
    username: str = ""
    password: str = ""
    role: str = "admin"
    created_at: datetime = field(default_factory=_utcnow)

    def __repr__(self) -> str:
        return f"<Admin {self.username}>"


@dataclass
class LoginAttempt:
    """Rate-limiting tracker."""

    key: str
    count: int = 0
    first_failed: Optional[datetime] = None
    lockout_until: Optional[datetime] = None
    updated_at: datetime = field(default_factory=_utcnow)

    @property
    def is_locked(self) -> bool:
        if self.lockout_until is None:
            return False
        return _utcnow() < self.lockout_until

    @property
    def remaining_minutes(self) -> int:
        if not self.is_locked:
            return 0
        return max(1, int((self.lockout_until - _utcnow()).total_seconds() // 60))


@dataclass
class TokenVersion:
    """Token version tracker — used to invalidate JWTs on password change."""

    account_number: str
    version: int = 0
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class Loan:
    """Loan — linked to a customer account."""

    loan_id: str
    account_number: str
    loan_type: str  # Personal, Home, Vehicle, Education, Business
    principal_amount: Decimal
    interest_rate: Decimal  # Annual interest rate %
    tenure_months: int
    emi_amount: Decimal
    amount_paid: Decimal = Decimal("0.00")
    remaining_amount: Decimal = Decimal("0.00")
    status: str = "PENDING"  # PENDING, APPROVED, ACTIVE, CLOSED, REJECTED
    application_date: datetime = field(default_factory=_utcnow)
    approval_date: Optional[datetime] = None
    next_emi_date: Optional[datetime] = None
    purpose: str = ""
    admin_notes: str = ""

    @property
    def progress_pct(self) -> float:
        """Percentage of loan repaid."""
        if self.principal_amount <= 0:
            return 0.0
        return float(self.amount_paid / self.principal_amount * 100)

    @property
    def remaining_emis(self) -> int:
        """Estimated remaining EMIs."""
        if self.emi_amount <= 0:
            return 0
        remaining = self.remaining_amount
        return int(remaining / self.emi_amount) + (1 if remaining % self.emi_amount > 0 else 0)

    @property
    def is_active(self) -> bool:
        return self.status in ("APPROVED", "ACTIVE")

    @property
    def is_overdue(self) -> bool:
        if not self.next_emi_date or self.status not in ("APPROVED", "ACTIVE"):
            return False
        return _utcnow() > self.next_emi_date


# ═══════════════════════════════════════════════════════════════════════════════
#  Notification entity
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Notification:
    """In-app notification for a customer account."""

    notif_id: str
    account_number: str
    type: str  # deposit, withdraw, transfer, loan_approved, loan_rejected, emi_paid, account_frozen, etc.
    title: str
    message: str
    is_read: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    related_txn_id: Optional[str] = None

    def __repr__(self) -> str:
        return f"<Notification {self.notif_id} ({self.type})>"


@dataclass
class NotificationPreference:
    """Per-account notification channel preferences."""

    account_number: str
    in_app_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    deposit_alerts: bool = True
    withdraw_alerts: bool = True
    transfer_alerts: bool = True
    interest_alerts: bool = True
    loan_alerts: bool = True
    admin_alerts: bool = True
    updated_at: datetime = field(default_factory=_utcnow)


# ═══════════════════════════════════════════════════════════════════════════════
#  Result types
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TransferResult:
    success: bool
    sender_balance: Decimal = Decimal("0.00")
    receiver_balance: Decimal = Decimal("0.00")
    error_message: str = ""


@dataclass
class ServiceResult:
    success: bool
    message: str = ""
    data: Optional[dict] = None
