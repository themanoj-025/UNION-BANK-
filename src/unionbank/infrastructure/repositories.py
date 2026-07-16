"""infrastructure/repositories.py  –  SQLAlchemy repository implementations.

Each repository implements the corresponding Protocol from application/interfaces.py.
These are the only classes that directly use SQLAlchemy ORM models.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from unionbank.application.interfaces import KeysetPage
from unionbank.domain.clock import utcnow as _utcnow  # noqa: F401
from unionbank.domain.entities import (
    Account,
    AdminUser,
    IdempotencyRecord,
    Loan,
    LoginAttempt,
    Notification,
    NotificationPreference,
    RefreshToken,
    SavingsGoal,
    TokenVersion,
    Transaction,
    TransactionType,
)
from unionbank.infrastructure.mappers import (
    map_account,
    map_account_to_model,
    map_admin,
    map_loan,
    map_notification,
    map_refresh_token,
    map_savings_goal,
    map_transaction,
)
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from .persistence import (
    AccountModel,
    AdminModel,
    AuditLogModel,
    IdempotencyModel,
    LoanModel,
    LoginAttemptModel,
    NotificationModel,
    NotificationPreferenceModel,
    RefreshTokenModel,
    SavingsGoalModel,
    TokenVersionModel,
    TransactionModel,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  Account Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyAccountRepository:
    """Account repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, acc_no: str) -> Optional[Account]:
        model = self.session.query(AccountModel).filter_by(
            account_number=acc_no, deleted_at=None
        ).first()
        return map_account(model) if model else None

    def get_all(self) -> list[Account]:
        models = self.session.query(AccountModel).filter_by(
            deleted_at=None
        ).all()
        return [map_account(m) for m in models]

    def exists(self, acc_no: str) -> bool:
        return self.session.query(AccountModel).filter_by(
            account_number=acc_no, deleted_at=None
        ).first() is not None

    def create(self, account: Account) -> Account:
        data = map_account_to_model(account)
        model = AccountModel(**data)
        self.session.add(model)
        return account

    def update(self, account: Account) -> Account:
        model = self.session.query(AccountModel).filter_by(
            account_number=account.account_number, deleted_at=None
        ).first()
        if model is None:
            return self.create(account)
        for key, value in map_account_to_model(account).items():
            if key != "created_at":
                setattr(model, key, value)
        return account

    def update_balance(self, acc_no: str, new_balance: Decimal) -> bool:
        model = self.session.query(AccountModel).filter_by(
            account_number=acc_no, deleted_at=None
        ).first()
        if model is None:
            return False
        model.balance = new_balance
        return True

    def set_active(self, acc_no: str, active: bool) -> bool:
        model = self.session.query(AccountModel).filter_by(
            account_number=acc_no, deleted_at=None
        ).first()
        if model is None:
            return False
        model.is_active = active
        return True

    def set_frozen(self, acc_no: str, frozen: bool) -> bool:
        """Set the frozen status of an account.

        NOTE: This does NOT change is_active. Freezing does not imply
        closing, and unfreezing does not imply reactivating.
        Callers that need to change both must call set_active() separately.
        """
        model = self.session.query(AccountModel).filter_by(
            account_number=acc_no, deleted_at=None
        ).first()
        if model is None:
            return False
        model.is_frozen = frozen
        return True

    def delete(self, acc_no: str) -> bool:
        """Soft-delete: set deleted_at timestamp instead of removing the row.

        Transaction history and related records are preserved for audit/compliance.
        Soft-deleted accounts are excluded from all default queries via the
        `_active_query()` helper but remain recoverable via `get_deleted()`.
        """
        model = self.session.query(AccountModel).filter_by(
            account_number=acc_no, deleted_at=None
        ).first()
        if model is None:
            return False
        from domain.clock import utcnow as _now
        model.deleted_at = _now()
        model.is_active = False
        return True

    def undelete(self, acc_no: str) -> bool:
        """Restore a soft-deleted account by clearing deleted_at."""
        model = self.session.query(AccountModel).filter(
            AccountModel.account_number == acc_no,
            AccountModel.deleted_at.isnot(None),
        ).first()
        if model is None:
            return False
        model.deleted_at = None
        model.is_active = True
        return True

    def get_deleted(self, acc_no: str) -> Optional[Account]:
        """Get a soft-deleted account (bypasses the active-only filter)."""
        model = self.session.query(AccountModel).filter_by(
            account_number=acc_no
        ).filter(AccountModel.deleted_at.isnot(None)).first()
        return map_account(model) if model else None

    def search(self, query: str) -> list[Account]:
        q = f"%{query}%"
        models = self.session.query(AccountModel).filter(
            AccountModel.deleted_at.is_(None),
            or_(
                AccountModel.account_number.ilike(q),
                AccountModel.name.ilike(q),
            )
        ).all()
        return [map_account(m) for m in models]

    def count(self) -> int:
        return self.session.query(AccountModel).filter_by(
            deleted_at=None
        ).count()

    def total_balance(self) -> Decimal:
        result = self.session.query(
            func.sum(AccountModel.balance)
        ).filter(
            AccountModel.deleted_at.is_(None),
            AccountModel.is_active.is_(True),
            AccountModel.is_frozen.is_(False),
        ).scalar()
        return result or Decimal("0.00")

    def active_count(self) -> int:
        return self.session.query(AccountModel).filter(
            AccountModel.deleted_at.is_(None),
            AccountModel.is_active.is_(True),
            AccountModel.is_frozen.is_(False),
        ).count()

    def frozen_count(self) -> int:
        return self.session.query(AccountModel).filter(
            AccountModel.deleted_at.is_(None),
            AccountModel.is_frozen.is_(True),
        ).count()

    def closed_count(self) -> int:
        return self.session.query(AccountModel).filter(
            AccountModel.deleted_at.is_(None),
            AccountModel.is_active.is_(False),
            AccountModel.is_frozen.is_(False),
        ).count()

    def get_by_email(self, email: str) -> Optional[Account]:
        model = self.session.query(AccountModel).filter_by(
            email=email, deleted_at=None
        ).first()
        return map_account(model) if model else None

    def get_statistics(self) -> dict:
        """Get bank-wide account statistics in a single aggregate query.

        Returns:
            dict with keys: total_customers, active, frozen, closed, total_balance

        """
        row = self.session.query(
            func.count(AccountModel.account_number).label("total"),
            func.sum(
                case(
                    (AccountModel.is_active.is_(True) & AccountModel.is_frozen.is_(False), 1),
                    else_=0
                )
            ).label("active_count"),
            func.sum(
                case((AccountModel.is_frozen.is_(True), 1), else_=0)
            ).label("frozen_count"),
            func.sum(
                case(
                    (
                        AccountModel.is_active.is_(False) & AccountModel.is_frozen.is_(False),
                        1
                    ),
                    else_=0
                )
            ).label("closed_count"),
            func.sum(AccountModel.balance).label("total_balance"),
        ).filter(AccountModel.deleted_at.is_(None)).first()

        return {
            "total_customers": row.total or 0,
            "active": row.active_count or 0,
            "frozen": row.frozen_count or 0,
            "closed": row.closed_count or 0,
            "total_balance": float(row.total_balance or Decimal("0.00")),
        }

    def get_all_paginated(self, page: int = 1, per_page: int = 20) -> tuple[list[Account], int]:
        """Get accounts with offset-based pagination.

        Returns:
            Tuple of (accounts list, total count).

        """
        base_q = self.session.query(AccountModel).filter_by(deleted_at=None)
        total = base_q.count()
        offset = (page - 1) * per_page
        models = base_q.order_by(
            AccountModel.created_at.desc()
        ).offset(offset).limit(per_page).all()
        return [map_account(m) for m in models], total

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Transaction Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyTransactionRepository:
    """Transaction repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_account(self, acc_no: str) -> list[Transaction]:
        models = self.session.query(TransactionModel).filter_by(
            account_number=acc_no
        ).order_by(TransactionModel.timestamp.desc()).all()
        return [map_transaction(m) for m in models]

    def get_mini(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        models = self.session.query(TransactionModel).filter_by(
            account_number=acc_no
        ).order_by(TransactionModel.timestamp.desc()).limit(limit).all()
        return [map_transaction(m) for m in models]

    def create(self, transaction: Transaction) -> Transaction:
        model = TransactionModel(
            txn_id=transaction.txn_id,
            account_number=transaction.account_number,
            type=transaction.type.value,
            amount=transaction.amount,
            balance=transaction.balance,
            description=transaction.description,
            category=transaction.category,
            target_account=transaction.target_account,
            timestamp=transaction.timestamp or _utcnow(),
        )
        self.session.add(model)
        return transaction

    def get_all(self) -> list[Transaction]:
        models = self.session.query(TransactionModel).order_by(
            TransactionModel.timestamp.desc()
        ).all()
        return [map_transaction(m) for m in models]

    def total_by_type(self, txn_type: str) -> Decimal:
        result = self.session.query(
            func.sum(TransactionModel.amount)
        ).filter_by(type=txn_type).scalar()
        return result or Decimal("0.00")

    def count(self) -> int:
        return self.session.query(TransactionModel).count()

    def count_by_account(self, acc_no: str) -> int:
        return self.session.query(TransactionModel).filter_by(
            account_number=acc_no
        ).count()

    def get_category_totals(self) -> dict[str, Decimal]:
        results = self.session.query(
            TransactionModel.category,
            func.sum(TransactionModel.amount)
        ).group_by(TransactionModel.category).all()
        return {cat: total or Decimal("0.00") for cat, total in results}

    def get_paginated(
        self,
        acc_no: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> tuple[list[Transaction], int]:
        query = self.session.query(TransactionModel)

        if acc_no:
            query = query.filter(TransactionModel.account_number == acc_no)
        if from_date:
            query = query.filter(TransactionModel.timestamp >= from_date)
        if to_date:
            query = query.filter(TransactionModel.timestamp <= to_date)
        if txn_type:
            query = query.filter(TransactionModel.type == txn_type)

        total = query.count()
        offset = (page - 1) * per_page
        models = query.order_by(
            TransactionModel.timestamp.desc()
        ).offset(offset).limit(per_page).all()

        return [map_transaction(m) for m in models], total

    def get_paginated_keyset(
        self,
        acc_no: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[datetime] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> KeysetPage[Transaction]:
        """Keyset (cursor-based) pagination for transactions.

        Instead of OFFSET/LIMIT (which degrades on large datasets), this
        uses WHERE timestamp < :cursor to fetch the next page. The cursor
        is the timestamp of the last item in the previous page.

        Returns a KeysetPage with items, next cursor, and has_more flag.
        """
        query = self.session.query(TransactionModel)

        if acc_no:
            query = query.filter(TransactionModel.account_number == acc_no)
        if from_date:
            query = query.filter(TransactionModel.timestamp >= from_date)
        if to_date:
            query = query.filter(TransactionModel.timestamp <= to_date)
        if txn_type:
            query = query.filter(TransactionModel.type == txn_type)

        # Keyset: fetch one more than needed to determine has_more
        fetch_limit = limit + 1
        if cursor is not None:
            query = query.filter(TransactionModel.timestamp < cursor)

        models = query.order_by(
            TransactionModel.timestamp.desc()
        ).limit(fetch_limit).all()

        has_more = len(models) > limit
        items = [map_transaction(m) for m in models[:limit]]
        next_cursor = items[-1].timestamp if items else None

        return KeysetPage(
            items=items,
            cursor=next_cursor,
            has_more=has_more,
            cursor_key="timestamp",
        )

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyAdminRepository:
    """Admin repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> Optional[AdminUser]:
        model = self.session.query(AdminModel).filter_by(username=username).first()
        return map_admin(model) if model else None

    def create(self, admin: AdminUser) -> AdminUser:
        model = AdminModel(
            username=admin.username,
            password=admin.password,
            role=admin.role or "admin",
            totp_secret=admin.totp_secret,
            totp_enabled=admin.totp_enabled,
        )
        self.session.add(model)
        return admin

    def update_password(self, username: str, new_hashed: str) -> bool:
        model = self.session.query(AdminModel).filter_by(username=username).first()
        if model is None:
            return False
        model.password = new_hashed
        return True

    def update_totp(self, username: str, totp_secret: Optional[str], totp_enabled: bool) -> bool:
        model = self.session.query(AdminModel).filter_by(username=username).first()
        if model is None:
            return False
        model.totp_secret = totp_secret
        model.totp_enabled = totp_enabled
        return True

    def admin_count(self) -> int:
        return self.session.query(AdminModel).count()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings Goal Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemySavingsGoalRepository:
    """Savings goal repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_account(self, acc_no: str) -> list[SavingsGoal]:
        models = self.session.query(SavingsGoalModel).filter_by(
            account_number=acc_no
        ).all()
        return [map_savings_goal(m) for m in models]

    def get(self, goal_id: str) -> Optional[SavingsGoal]:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal_id).first()
        return map_savings_goal(model) if model else None

    def create(self, goal: SavingsGoal) -> SavingsGoal:
        model = SavingsGoalModel(
            goal_id=goal.goal_id,
            account_number=goal.account_number,
            name=goal.name,
            target_amount=goal.target_amount,
            current_amount=goal.current_amount,
            target_date=goal.target_date,
        )
        self.session.add(model)
        return goal

    def update(self, goal: SavingsGoal) -> SavingsGoal:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal.goal_id).first()
        if model:
            model.name = goal.name
            model.target_amount = goal.target_amount
            model.current_amount = goal.current_amount
            model.target_date = goal.target_date
            model.is_completed = goal.is_completed
        return goal

    def contribute(self, goal_id: str, amount: Decimal) -> Optional[SavingsGoal]:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal_id).first()
        if model is None:
            return None
        model.current_amount += amount
        if model.current_amount >= model.target_amount:
            model.is_completed = True
        return map_savings_goal(model)

    def delete(self, goal_id: str) -> Optional[SavingsGoal]:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal_id).first()
        if model is None:
            return None
        goal = map_savings_goal(model)
        self.session.delete(model)
        return goal

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# _map_loan moved to infrastructure/mappers.py — imported at top of file


# ═══════════════════════════════════════════════════════════════════════════════
#  Loan Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyLoanRepository:
    """Loan repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, loan_id: str) -> Optional[Loan]:
        model = self.session.query(LoanModel).filter_by(loan_id=loan_id).first()
        return map_loan(model) if model else None

    def get_by_account(self, acc_no: str) -> list[Loan]:
        models = self.session.query(LoanModel).filter_by(
            account_number=acc_no
        ).order_by(LoanModel.application_date.desc()).all()
        return [map_loan(m) for m in models]

    def get_all_pending(self) -> list[Loan]:
        models = self.session.query(LoanModel).filter_by(
            status="PENDING"
        ).order_by(LoanModel.application_date.asc()).all()
        return [map_loan(m) for m in models]

    def get_all_active(self) -> list[Loan]:
        models = self.session.query(LoanModel).filter(
            LoanModel.status.in_(["APPROVED", "ACTIVE"])
        ).order_by(LoanModel.application_date.desc()).all()
        return [map_loan(m) for m in models]

    def get_all(self) -> list[Loan]:
        models = self.session.query(LoanModel).order_by(
            LoanModel.application_date.desc()
        ).all()
        return [map_loan(m) for m in models]

    def create(self, loan: Loan) -> Loan:
        model = LoanModel(
            loan_id=loan.loan_id,
            account_number=loan.account_number,
            loan_type=loan.loan_type,
            principal_amount=loan.principal_amount,
            interest_rate=loan.interest_rate,
            tenure_months=loan.tenure_months,
            emi_amount=loan.emi_amount,
            amount_paid=loan.amount_paid,
            remaining_amount=loan.remaining_amount,
            status=loan.status,
            application_date=loan.application_date,
            approval_date=loan.approval_date,
            next_emi_date=loan.next_emi_date,
            purpose=loan.purpose,
            admin_notes=loan.admin_notes,
        )
        self.session.add(model)
        return loan

    def update(self, loan: Loan) -> Loan:
        model = self.session.query(LoanModel).filter_by(loan_id=loan.loan_id).first()
        if model:
            model.loan_type = loan.loan_type
            model.principal_amount = loan.principal_amount
            model.interest_rate = loan.interest_rate
            model.tenure_months = loan.tenure_months
            model.emi_amount = loan.emi_amount
            model.amount_paid = loan.amount_paid
            model.remaining_amount = loan.remaining_amount
            model.status = loan.status
            model.approval_date = loan.approval_date
            model.next_emi_date = loan.next_emi_date
            model.purpose = loan.purpose
            model.admin_notes = loan.admin_notes
        return loan

    def count_by_status(self, status: str) -> int:
        return self.session.query(LoanModel).filter_by(status=status).count()

    def total_disbursed(self) -> Decimal:
        result = self.session.query(
            func.sum(LoanModel.principal_amount)
        ).filter(
            LoanModel.status.in_(["APPROVED", "ACTIVE", "CLOSED"])
        ).scalar()
        return result or Decimal("0.00")

    def total_outstanding(self) -> Decimal:
        result = self.session.query(
            func.sum(LoanModel.remaining_amount)
        ).filter(
            LoanModel.status.in_(["APPROVED", "ACTIVE"])
        ).scalar()
        return result or Decimal("0.00")

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Login Attempt Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyLoginAttemptRepository:
    """Login attempt repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, key: str) -> Optional[LoginAttempt]:
        model = self.session.query(LoginAttemptModel).filter_by(key=key).first()
        if model is None:
            return None
        return LoginAttempt(
            key=model.key,
            count=model.count or 0,
            first_failed=model.first_failed,
            lockout_until=model.lockout_until,
            updated_at=model.updated_at,
        )

    def record_failure(self, key: str, max_attempts: int = 5,
                       lockout_minutes: int = 15) -> int:
        record = self.get(key)
        now = _utcnow()

        if record is None:
            record = LoginAttempt(key=key, count=1, first_failed=now)
            model = LoginAttemptModel(
                key=key, count=1, first_failed=now
            )
            self.session.add(model)
        else:
            model = self.session.query(LoginAttemptModel).filter_by(key=key).first()

            if model.lockout_until and now >= model.lockout_until:
                model.count = 1
                model.first_failed = now
                model.lockout_until = None
            else:
                model.count = (model.count or 0) + 1

            if model.count >= max_attempts:
                model.lockout_until = now + timedelta(minutes=lockout_minutes)

        return max(0, max_attempts - (getattr(model, 'count', record.count) or 0))

    def is_locked(self, key: str, max_attempts: int = 5) -> tuple[bool, int]:
        model = self.session.query(LoginAttemptModel).filter_by(key=key).first()
        if model is None or (model.count or 0) < max_attempts:
            return False, 0

        now = _utcnow()
        lockout_until = model.lockout_until

        # Handle timezone-naive datetimes (SQLite may strip tzinfo on roundtrip)
        if lockout_until is not None and lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=timezone.utc)

        if lockout_until and now < lockout_until:
            remaining = int((lockout_until - now).total_seconds() // 60)
            return True, max(1, remaining)
        if model:
            self.session.delete(model)
        return False, 0

    def reset(self, key: str) -> None:
        model = self.session.query(LoginAttemptModel).filter_by(key=key).first()
        if model:
            self.session.delete(model)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Token Version Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyTokenVersionRepository:
    """Token version repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get_version(self, account_number: str) -> int:
        model = self.session.query(TokenVersionModel).filter_by(
            account_number=account_number
        ).first()
        return model.version if model else 0

    def increment(self, account_number: str) -> int:
        model = self.session.query(TokenVersionModel).filter_by(
            account_number=account_number
        ).first()
        if model is None:
            model = TokenVersionModel(account_number=account_number, version=1)
            self.session.add(model)
        else:
            model.version += 1
        return model.version

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Notification Repository
# ═══════════════════════════════════════════════════════════════════════════════


# _map_notification moved to infrastructure/mappers.py — imported at top of file


class SqlAlchemyNotificationRepository:
    """In-app notification repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, notif_id: str) -> Optional[Notification]:
        model = self.session.query(NotificationModel).filter_by(notif_id=notif_id).first()
        return map_notification(model) if model else None

    def get_by_account(self, acc_no: str, limit: int = 50) -> list[Notification]:
        models = self.session.query(NotificationModel).filter_by(
            account_number=acc_no
        ).order_by(NotificationModel.created_at.desc()).limit(limit).all()
        return [map_notification(m) for m in models]

    def get_unread_count(self, acc_no: str) -> int:
        return self.session.query(NotificationModel).filter_by(
            account_number=acc_no, is_read=False
        ).count()

    def get_unread(self, acc_no: str, limit: int = 20) -> list[Notification]:
        models = self.session.query(NotificationModel).filter_by(
            account_number=acc_no, is_read=False
        ).order_by(NotificationModel.created_at.desc()).limit(limit).all()
        return [map_notification(m) for m in models]

    def create(self, notification: Notification) -> Notification:
        model = NotificationModel(
            notif_id=notification.notif_id,
            account_number=notification.account_number,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at or _utcnow(),
            related_txn_id=notification.related_txn_id,
        )
        self.session.add(model)
        return notification

    def mark_as_read(self, notif_id: str) -> bool:
        model = self.session.query(NotificationModel).filter_by(notif_id=notif_id).first()
        if model is None:
            return False
        model.is_read = True
        return True

    def mark_all_as_read(self, acc_no: str) -> int:
        count = self.session.query(NotificationModel).filter_by(
            account_number=acc_no, is_read=False
        ).update({"is_read": True})
        return count

    def delete_old(self, days: int = 30) -> int:
        from datetime import timedelta
        cutoff = _utcnow() - timedelta(days=days)
        deleted = self.session.query(NotificationModel).filter(
            NotificationModel.created_at < cutoff
        ).delete()
        return deleted

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Notification Preference Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyNotificationPreferenceRepository:
    """Notification preferences repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, acc_no: str) -> Optional[NotificationPreference]:
        model = self.session.query(NotificationPreferenceModel).filter_by(
            account_number=acc_no
        ).first()
        if model is None:
            return None
        return NotificationPreference(
            account_number=model.account_number,
            in_app_enabled=model.in_app_enabled,
            email_enabled=model.email_enabled,
            sms_enabled=model.sms_enabled,
            deposit_alerts=model.deposit_alerts,
            withdraw_alerts=model.withdraw_alerts,
            transfer_alerts=model.transfer_alerts,
            interest_alerts=model.interest_alerts,
            loan_alerts=model.loan_alerts,
            admin_alerts=model.admin_alerts,
            updated_at=model.updated_at,
        )

    def create_or_update(self, pref: NotificationPreference) -> NotificationPreference:
        model = self.session.query(NotificationPreferenceModel).filter_by(
            account_number=pref.account_number
        ).first()
        if model is None:
            model = NotificationPreferenceModel(
                account_number=pref.account_number,
                in_app_enabled=pref.in_app_enabled,
                email_enabled=pref.email_enabled,
                sms_enabled=pref.sms_enabled,
                deposit_alerts=pref.deposit_alerts,
                withdraw_alerts=pref.withdraw_alerts,
                transfer_alerts=pref.transfer_alerts,
                interest_alerts=pref.interest_alerts,
                loan_alerts=pref.loan_alerts,
                admin_alerts=pref.admin_alerts,
            )
            self.session.add(model)
        else:
            model.in_app_enabled = pref.in_app_enabled
            model.email_enabled = pref.email_enabled
            model.sms_enabled = pref.sms_enabled
            model.deposit_alerts = pref.deposit_alerts
            model.withdraw_alerts = pref.withdraw_alerts
            model.transfer_alerts = pref.transfer_alerts
            model.interest_alerts = pref.interest_alerts
            model.loan_alerts = pref.loan_alerts
            model.admin_alerts = pref.admin_alerts
        return pref

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Refresh Token Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyRefreshTokenRepository:
    """Refresh token repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, token_id: str) -> Optional[RefreshToken]:
        model = self.session.query(RefreshTokenModel).filter_by(token_id=token_id).first()
        return map_refresh_token(model) if model else None

    def get_by_account(self, account_number: str) -> list[RefreshToken]:
        models = self.session.query(RefreshTokenModel).filter_by(
            account_number=account_number
        ).order_by(RefreshTokenModel.created_at.desc()).all()
        return [map_refresh_token(m) for m in models]

    def create(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            token_id=token.token_id,
            account_number=token.account_number,
            role=token.role,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
        )
        self.session.add(model)
        return token

    def revoke(self, token_id: str) -> bool:
        model = self.session.query(RefreshTokenModel).filter_by(token_id=token_id).first()
        if model is None:
            return False
        from datetime import datetime, timezone
        model.revoked_at = datetime.now(timezone.utc)
        return True

    def revoke_all_for_account(self, account_number: str) -> int:
        from datetime import datetime, timezone
        count = self.session.query(RefreshTokenModel).filter_by(
            account_number=account_number,
            revoked_at=None,
        ).update({"revoked_at": datetime.now(timezone.utc)})
        return count

    def clean_expired(self) -> int:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        deleted = self.session.query(RefreshTokenModel).filter(
            RefreshTokenModel.expires_at < now
        ).delete()
        return deleted

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Idempotency Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyIdempotencyRepository:
    """Idempotency key repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        """Retrieve an existing idempotency record by key."""
        model = self.session.query(IdempotencyModel).filter_by(
            idempotency_key=idempotency_key
        ).first()
        if model is None:
            return None
        return IdempotencyRecord(
            idempotency_key=model.idempotency_key,
            account_number=model.account_number,
            operation=model.operation,
            result_json=model.result_json,
            amount=model.amount,
            created_at=model.created_at,
        )

    def create(self, record: IdempotencyRecord) -> IdempotencyRecord:
        """Store an idempotency record."""
        model = IdempotencyModel(
            idempotency_key=record.idempotency_key,
            account_number=record.account_number,
            operation=record.operation,
            result_json=record.result_json,
            amount=record.amount,
        )
        self.session.add(model)
        return record

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Audit Log Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyAuditLogRepository:
    """Audit log repository — append-only, never deleted or updated."""

    def __init__(self, session: Session):
        self.session = session

    def log(self, actor: str, action: str, target: Optional[str] = None,
            details: Optional[str] = None, ip_address: Optional[str] = None,
            reason: Optional[str] = None) -> None:
        """Append an immutable audit log entry."""
        from datetime import timezone
        model = AuditLogModel(
            actor=actor,
            action=action,
            target=target,
            details=details[:500] if details else None,
            ip_address=ip_address,
            reason=reason[:200] if reason else None,
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(model)

    def get_recent(self, limit: int = 50) -> list:
        models = self.session.query(AuditLogModel).order_by(
            AuditLogModel.timestamp.desc()
        ).limit(limit).all()
        return [{
            "id": m.id,
            "actor": m.actor,
            "action": m.action,
            "target": m.target,
            "details": m.details,
            "ip_address": m.ip_address,
            "reason": m.reason,
            "timestamp": str(m.timestamp)[:19],
        } for m in models]

    def get_by_actor(self, actor: str, limit: int = 50) -> list:
        models = self.session.query(AuditLogModel).filter_by(
            actor=actor
        ).order_by(AuditLogModel.timestamp.desc()).limit(limit).all()
        return [{
            "id": m.id,
            "actor": m.actor,
            "action": m.action,
            "target": m.target,
            "details": m.details,
            "ip_address": m.ip_address,
            "reason": m.reason,
            "timestamp": str(m.timestamp)[:19],
        } for m in models]

    def get_by_action(self, action: str, limit: int = 50) -> list:
        models = self.session.query(AuditLogModel).filter_by(
            action=action
        ).order_by(AuditLogModel.timestamp.desc()).limit(limit).all()
        return [{
            "id": m.id,
            "actor": m.actor,
            "action": m.action,
            "target": m.target,
            "details": m.details,
            "ip_address": m.ip_address,
            "reason": m.reason,
            "timestamp": str(m.timestamp)[:19],
        } for m in models]

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
