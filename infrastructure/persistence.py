"""
infrastructure/persistence.py  –  SQLAlchemy ORM models.

These are the database-visible representations of domain entities.
Only infrastructure code imports these — domain and application layers
use the pure dataclasses from domain/entities.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, Numeric, String, ForeignKey, Text,
)
from sqlalchemy.orm import relationship

from .database import ModelBase


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AccountModel(ModelBase):
    """SQLAlchemy model for customer accounts."""

    __tablename__ = "accounts"

    account_number = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    age = Column(Integer, nullable=False, default=18)
    gender = Column(String(20), nullable=False, default="")
    mobile = Column(String(15), nullable=False, default="")
    email = Column(String(100), nullable=False, default="")
    password = Column(String(128), nullable=False)
    balance = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    is_active = Column(Boolean, nullable=False, default=True)
    is_frozen = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    transactions = relationship(
        "TransactionModel", back_populates="account",
        order_by="TransactionModel.timestamp.desc()",
        cascade="all, delete-orphan",
    )
    savings_goals = relationship(
        "SavingsGoalModel", back_populates="account",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AccountModel {self.account_number} ({self.name})>"


class TransactionModel(ModelBase):
    """SQLAlchemy model for transaction records."""

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
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    account = relationship("AccountModel", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<TransactionModel {self.txn_id} ({self.type} {self.amount})>"


class SavingsGoalModel(ModelBase):
    """SQLAlchemy model for savings goals."""

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
    target_date = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    is_completed = Column(Boolean, nullable=False, default=False)

    account = relationship("AccountModel", back_populates="savings_goals")

    def __repr__(self) -> str:
        return f"<SavingsGoalModel {self.goal_id}: {self.name}>"


class AdminModel(ModelBase):
    """SQLAlchemy model for admin users."""

    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(String(128), nullable=False)
    role = Column(String(20), nullable=False, default="admin")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    def __repr__(self) -> str:
        return f"<AdminModel {self.username}>"


class LoginAttemptModel(ModelBase):
    """SQLAlchemy model for rate-limiting tracker."""

    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    count = Column(Integer, nullable=False, default=0)
    first_failed = Column(DateTime(timezone=True), nullable=True)
    lockout_until = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class TokenVersionModel(ModelBase):
    """SQLAlchemy model for JWT token version tracking."""

    __tablename__ = "token_versions"

    account_number = Column(String(10), primary_key=True)
    version = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class AuditLogModel(ModelBase):
    """Immutable audit log for admin actions — never deleted or updated."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(50), nullable=False, index=True)  # Admin username
    action = Column(String(50), nullable=False, index=True)  # freeze, unfreeze, delete, close, password_reset
    target = Column(String(50), nullable=True)  # Account number or username affected
    details = Column(String(500), nullable=True)  # Human-readable details (no PII)
    ip_address = Column(String(45), nullable=True)  # Client IP
    reason = Column(String(200), nullable=True)  # Optional reason provided by admin
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
