"""
infrastructure/repositories.py  –  SQLAlchemy repository implementations.

Each repository implements the corresponding Protocol from application/interfaces.py.
These are the only classes that directly use SQLAlchemy ORM models.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from application.interfaces import KeysetPage

from domain.entities import (
    Account, AdminUser, LoginAttempt, SavingsGoal,
    Transaction, TransactionType, TokenVersion,
)
from .persistence import (
    AccountModel, TransactionModel, SavingsGoalModel,
    AdminModel, LoginAttemptModel, TokenVersionModel,
    AuditLogModel,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _map_account(model: AccountModel) -> Account:
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
    )


def _map_account_to_model(account: Account) -> dict:
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
    }


def _map_transaction(model: TransactionModel) -> Transaction:
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


def _map_savings_goal(model: SavingsGoalModel) -> SavingsGoal:
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


def _map_admin(model: AdminModel) -> AdminUser:
    return AdminUser(
        id=model.id,
        username=model.username,
        password=model.password,
        role=model.role,
        created_at=model.created_at,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Account Repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqlAlchemyAccountRepository:
    """Account repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, acc_no: str) -> Optional[Account]:
        model = self.session.query(AccountModel).filter_by(account_number=acc_no).first()
        return _map_account(model) if model else None

    def get_all(self) -> list[Account]:
        models = self.session.query(AccountModel).all()
        return [_map_account(m) for m in models]

    def exists(self, acc_no: str) -> bool:
        return self.session.query(AccountModel).filter_by(account_number=acc_no).first() is not None

    def create(self, account: Account) -> Account:
        data = _map_account_to_model(account)
        model = AccountModel(**data)
        self.session.add(model)
        return account

    def update(self, account: Account) -> Account:
        model = self.session.query(AccountModel).filter_by(
            account_number=account.account_number
        ).first()
        if model is None:
            return self.create(account)
        for key, value in _map_account_to_model(account).items():
            if key != "created_at":
                setattr(model, key, value)
        return account

    def update_balance(self, acc_no: str, new_balance: Decimal) -> bool:
        model = self.session.query(AccountModel).filter_by(account_number=acc_no).first()
        if model is None:
            return False
        model.balance = new_balance
        return True

    def set_active(self, acc_no: str, active: bool) -> bool:
        model = self.session.query(AccountModel).filter_by(account_number=acc_no).first()
        if model is None:
            return False
        model.is_active = active
        return True

    def set_frozen(self, acc_no: str, frozen: bool) -> bool:
        model = self.session.query(AccountModel).filter_by(account_number=acc_no).first()
        if model is None:
            return False
        model.is_frozen = frozen
        if frozen:
            model.is_active = False
        else:
            model.is_active = True
        return True

    def delete(self, acc_no: str) -> bool:
        model = self.session.query(AccountModel).filter_by(account_number=acc_no).first()
        if model is None:
            return False
        self.session.delete(model)
        return True

    def search(self, query: str) -> list[Account]:
        q = f"%{query}%"
        models = self.session.query(AccountModel).filter(
            or_(
                AccountModel.account_number.ilike(q),
                AccountModel.name.ilike(q),
            )
        ).all()
        return [_map_account(m) for m in models]

    def count(self) -> int:
        return self.session.query(AccountModel).count()

    def total_balance(self) -> Decimal:
        result = self.session.query(
            func.sum(AccountModel.balance)
        ).filter(
            AccountModel.is_active.is_(True),
            AccountModel.is_frozen.is_(False),
        ).scalar()
        return result or Decimal("0.00")

    def active_count(self) -> int:
        return self.session.query(AccountModel).filter(
            AccountModel.is_active.is_(True),
            AccountModel.is_frozen.is_(False),
        ).count()

    def frozen_count(self) -> int:
        return self.session.query(AccountModel).filter(
            AccountModel.is_frozen.is_(True),
        ).count()

    def closed_count(self) -> int:
        return self.session.query(AccountModel).filter(
            AccountModel.is_active.is_(False),
            AccountModel.is_frozen.is_(False),
        ).count()

    def get_by_email(self, email: str) -> Optional[Account]:
        model = self.session.query(AccountModel).filter_by(email=email).first()
        return _map_account(model) if model else None

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
        return [_map_transaction(m) for m in models]

    def get_mini(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        models = self.session.query(TransactionModel).filter_by(
            account_number=acc_no
        ).order_by(TransactionModel.timestamp.desc()).limit(limit).all()
        return [_map_transaction(m) for m in models]

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
        return [_map_transaction(m) for m in models]

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

        return [_map_transaction(m) for m in models], total

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
        items = [_map_transaction(m) for m in models[:limit]]
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
        return _map_admin(model) if model else None

    def create(self, admin: AdminUser) -> AdminUser:
        model = AdminModel(
            username=admin.username,
            password=admin.password,
            role=admin.role or "admin",
        )
        self.session.add(model)
        return admin

    def update_password(self, username: str, new_hashed: str) -> bool:
        model = self.session.query(AdminModel).filter_by(username=username).first()
        if model is None:
            return False
        model.password = new_hashed
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
        return [_map_savings_goal(m) for m in models]

    def get(self, goal_id: str) -> Optional[SavingsGoal]:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal_id).first()
        return _map_savings_goal(model) if model else None

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
        return _map_savings_goal(model)

    def delete(self, goal_id: str) -> Optional[SavingsGoal]:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal_id).first()
        if model is None:
            return None
        goal = _map_savings_goal(model)
        self.session.delete(model)
        return goal

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
        if model.lockout_until and _utcnow() < model.lockout_until:
            remaining = int((model.lockout_until - _utcnow()).total_seconds() // 60)
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
