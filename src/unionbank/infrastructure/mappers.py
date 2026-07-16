"""infrastructure/mappers.py  –  Shared mapper functions: DB models ↔ domain entities.

Centralises all ORM-to-domain mapping so every repository (and any future
read-model projection) uses the same transformation functions.
"""

from __future__ import annotations

from decimal import Decimal

from unionbank.domain.clock import utcnow as _utcnow  # noqa: F401 — used as default in _map_account_to_model
from unionbank.domain.entities import (
    Account,
    AdminUser,
    Loan,
    Notification,
    RefreshToken,
    SavingsGoal,
    Transaction,
    TransactionType,
)

from .persistence import (
    AccountModel,
    AdminModel,
    LoanModel,
    NotificationModel,
    RefreshTokenModel,
    SavingsGoalModel,
    TransactionModel,
)


def map_account(model: AccountModel) -> Account:
    """Map an AccountModel to a domain Account entity."""
    return Account(
        account_number=model.account_number,
        name=model.name,
        age=model.age,
        gender=model.gender,
        mobile=model.mobile,
        email=model.email,
        password=model.password,
        balance=model.balance,
        is_active=model.is_active,
        is_frozen=model.is_frozen,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def map_account_to_model(account: Account) -> dict:
    """Map a domain Account entity to DB model kwargs."""
    return {
        "account_number": account.account_number,
        "name": account.name,
        "age": account.age,
        "gender": account.gender,
        "mobile": account.mobile,
        "email": account.email,
        "password": account.password,
        "balance": account.balance,
        "is_active": account.is_active,
        "is_frozen": account.is_frozen,
        "created_at": account.created_at,
        "updated_at": _utcnow(),
        "deleted_at": account.deleted_at,
    }


def map_transaction(model: TransactionModel) -> Transaction:
    """Map a TransactionModel to a domain Transaction entity."""
    return Transaction(
        txn_id=model.txn_id,
        account_number=model.account_number,
        type=TransactionType(model.type),
        amount=model.amount,
        balance=model.balance,
        description=model.description or "",
        category=model.category or "General",
        target_account=model.target_account,
        timestamp=model.timestamp,
    )


def map_savings_goal(model: SavingsGoalModel) -> SavingsGoal:
    """Map a SavingsGoalModel to a domain SavingsGoal entity."""
    return SavingsGoal(
        goal_id=model.goal_id,
        account_number=model.account_number,
        name=model.name,
        target_amount=model.target_amount,
        current_amount=model.current_amount,
        target_date=model.target_date,
        created_at=model.created_at,
        is_completed=model.is_completed,
    )


def map_admin(model: AdminModel) -> AdminUser:
    """Map an AdminModel to a domain AdminUser entity."""
    return AdminUser(
        id=model.id,
        username=model.username,
        password=model.password,
        role=model.role,
        totp_secret=model.totp_secret,
        totp_enabled=model.totp_enabled,
        created_at=model.created_at,
    )


def map_refresh_token(model: RefreshTokenModel) -> RefreshToken:
    """Map a RefreshTokenModel to a domain RefreshToken entity."""
    return RefreshToken(
        token_id=model.token_id,
        account_number=model.account_number,
        role=model.role,
        expires_at=model.expires_at,
        revoked_at=model.revoked_at,
        created_at=model.created_at,
    )


def map_loan(model: LoanModel) -> Loan:
    """Map a LoanModel to a domain Loan entity."""
    return Loan(
        loan_id=model.loan_id,
        account_number=model.account_number,
        loan_type=model.loan_type,
        principal_amount=model.principal_amount,
        interest_rate=model.interest_rate,
        tenure_months=model.tenure_months,
        emi_amount=model.emi_amount,
        amount_paid=model.amount_paid,
        remaining_amount=model.remaining_amount,
        status=model.status,
        application_date=model.application_date,
        approval_date=model.approval_date,
        next_emi_date=model.next_emi_date,
        purpose=model.purpose or "",
        admin_notes=model.admin_notes or "",
    )


def map_notification(model: NotificationModel) -> Notification:
    """Map a NotificationModel to a domain Notification entity."""
    return Notification(
        notif_id=model.notif_id,
        account_number=model.account_number,
        type=model.type,
        title=model.title,
        message=model.message,
        is_read=model.is_read,
        created_at=model.created_at,
        related_txn_id=model.related_txn_id,
    )
