"""
models.py  –  SQLAlchemy ORM models for Union Bank Management System.

All monetary values use Numeric(14,2) — never float — to avoid precision loss.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, Numeric, String, ForeignKey, Text,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def _utcnow() -> datetime:
    """Timezone-aware UTC now (replacement for deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc)


class AccountModel(Base):
    """Customer account — source of truth for balances and status."""

    __tablename__ = "accounts"

    account_number = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    age = Column(Integer, nullable=False, default=18)
    gender = Column(String(20), nullable=False, default="")
    mobile = Column(String(15), nullable=False, default="")
    email = Column(String(100), nullable=False, default="")
    password = Column(String(128), nullable=False)  # bcrypt hash
    balance = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    is_active = Column(Boolean, nullable=False, default=True)
    is_frozen = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    transactions = relationship(
        "TransactionModel", back_populates="account",
        order_by="TransactionModel.timestamp.desc()",
    )
    savings_goals = relationship(
        "SavingsGoalModel", back_populates="account",
    )

    def __repr__(self) -> str:
        return f"<Account {self.account_number} ({self.name})>"


class TransactionModel(Base):
    """Transaction record — append-only log of all account activity."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    txn_id = Column(String(20), nullable=False, unique=True, index=True)
    account_number = Column(
        String(10),
        ForeignKey("accounts.account_number", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(20), nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    balance = Column(Numeric(14, 2), nullable=False)
    description = Column(String(200), default="")
    category = Column(String(50), default="General", index=True)
    target_account = Column(String(10), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=_utcnow, index=True)

    account = relationship("AccountModel", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction {self.txn_id} ({self.type} {self.amount})>"


class SavingsGoalModel(Base):
    """Savings goal — linked to a customer account."""

    __tablename__ = "savings_goals"

    goal_id = Column(String(20), primary_key=True)
    account_number = Column(
        String(10),
        ForeignKey("accounts.account_number", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    target_amount = Column(Numeric(14, 2), nullable=False)
    current_amount = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    target_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    is_completed = Column(Boolean, nullable=False, default=False)

    account = relationship("AccountModel", back_populates="savings_goals")

    def __repr__(self) -> str:
        return f"<SavingsGoal {self.goal_id}: {self.name}>"


class AdminModel(Base):
    """Admin user — now lives in the same DB (no separate admin.json file)."""

    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(String(128), nullable=False)  # bcrypt hash
    role = Column(String(20), nullable=False, default="admin")
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    def __repr__(self) -> str:
        return f"<Admin {self.username}>"


class LoginAttemptModel(Base):
    """Rate-limiting tracker — stored in DB instead of a separate JSON file."""

    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    count = Column(Integer, nullable=False, default=0)
    first_failed = Column(DateTime, nullable=True)
    lockout_until = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)


class TokenVersion(Base):
    """Token version tracker — used to invalidate JWTs on password change."""

    __tablename__ = "token_versions"

    account_number = Column(String(10), primary_key=True)
    version = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
