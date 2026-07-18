"""
async_repositories.py  –  Async SQLAlchemy repository implementations.

Each repository mirrors its synchronous counterpart in repositories.py but
uses ``AsyncSession`` and ``await session.execute(select(...))`` for all
database operations. These are used when the application is configured with
a PostgreSQL DATABASE_URL (async via asyncpg).

SQLite does NOT support async access, so these repos will raise at runtime
if called with a SQLite database URL.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from unionbank.application.interfaces import KeysetPage
from unionbank.domain.clock import utcnow as _utcnow
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
    Transaction,
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
#  Account Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyAccountRepository:
    """Account repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, acc_no: str) -> Optional[Account]:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        return map_account(model) if model else None

    async def get_all(self) -> list[Account]:
        result = await self.session.execute(
            select(AccountModel).where(AccountModel.deleted_at.is_(None))
        )
        models = result.scalars().all()
        return [map_account(m) for m in models]

    async def exists(self, acc_no: str) -> bool:
        result = await self.session.execute(
            select(AccountModel.account_number).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            ).limit(1)
        )
        return result.first() is not None

    async def create(self, account: Account) -> Account:
        data = map_account_to_model(account)
        model = AccountModel(**data)
        self.session.add(model)
        return account

    async def update(self, account: Account) -> Account:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == account.account_number,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return await self.create(account)
        for key, value in map_account_to_model(account).items():
            if key != "created_at":
                setattr(model, key, value)
        return account

    async def update_balance(self, acc_no: str, new_balance: Decimal) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.balance = new_balance
        return True

    async def set_active(self, acc_no: str, active: bool) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.is_active = active
        return True

    async def set_frozen(self, acc_no: str, frozen: bool) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.is_frozen = frozen
        return True

    async def delete(self, acc_no: str) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.deleted_at = _utcnow()
        model.is_active = False
        return True

    async def undelete(self, acc_no: str) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.isnot(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.deleted_at = None
        model.is_active = True
        return True

    async def get_deleted(self, acc_no: str) -> Optional[Account]:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.isnot(None),
            )
        )
        model = result.scalar_one_or_none()
        return map_account(model) if model else None

    async def search(self, query: str) -> list[Account]:
        q = f"%{query}%"
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.deleted_at.is_(None),
                or_(
                    AccountModel.account_number.ilike(q),
                    AccountModel.name.ilike(q),
                ),
            )
        )
        models = result.scalars().all()
        return [map_account(m) for m in models]

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(AccountModel).where(
                AccountModel.deleted_at.is_(None)
            )
        )
        return result.scalar() or 0

    async def total_balance(self) -> Decimal:
        result = await self.session.execute(
            select(func.sum(AccountModel.balance)).where(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_active.is_(True),
                AccountModel.is_frozen.is_(False),
            )
        )
        return result.scalar() or Decimal("0.00")

    async def active_count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(AccountModel).where(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_active.is_(True),
                AccountModel.is_frozen.is_(False),
            )
        )
        return result.scalar() or 0

    async def frozen_count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(AccountModel).where(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_frozen.is_(True),
            )
        )
        return result.scalar() or 0

    async def closed_count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(AccountModel).where(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_active.is_(False),
                AccountModel.is_frozen.is_(False),
            )
        )
        return result.scalar() or 0

    async def get_by_email(self, email: str) -> Optional[Account]:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.email == email,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        return map_account(model) if model else None

    async def get_statistics(self) -> dict:
        result = await self.session.execute(
            select(
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
            ).where(AccountModel.deleted_at.is_(None))
        )
        row = result.one()

        return {
            "total_customers": row.total or 0,
            "active": row.active_count or 0,
            "frozen": row.frozen_count or 0,
            "closed": row.closed_count or 0,
            "total_balance": float(row.total_balance or Decimal("0.00")),
        }

    async def get_all_paginated(self, page: int = 1, per_page: int = 20) -> tuple[list[Account], int]:
        total_result = await self.session.execute(
            select(func.count()).select_from(AccountModel).where(
                AccountModel.deleted_at.is_(None)
            )
        )
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        result = await self.session.execute(
            select(AccountModel)
            .where(AccountModel.deleted_at.is_(None))
            .order_by(AccountModel.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        models = result.scalars().all()
        return [map_account(m) for m in models], total

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Transaction Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyTransactionRepository:
    """Transaction repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_account(self, acc_no: str) -> list[Transaction]:
        result = await self.session.execute(
            select(TransactionModel)
            .where(TransactionModel.account_number == acc_no)
            .order_by(TransactionModel.timestamp.desc())
        )
        models = result.scalars().all()
        return [map_transaction(m) for m in models]

    async def get_mini(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        result = await self.session.execute(
            select(TransactionModel)
            .where(TransactionModel.account_number == acc_no)
            .order_by(TransactionModel.timestamp.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        return [map_transaction(m) for m in models]

    async def create(self, transaction: Transaction) -> Transaction:
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

    async def get_all(self) -> list[Transaction]:
        result = await self.session.execute(
            select(TransactionModel).order_by(TransactionModel.timestamp.desc())
        )
        models = result.scalars().all()
        return [map_transaction(m) for m in models]

    async def total_by_type(self, txn_type: str) -> Decimal:
        result = await self.session.execute(
            select(func.sum(TransactionModel.amount)).where(
                TransactionModel.type == txn_type
            )
        )
        return result.scalar() or Decimal("0.00")

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(TransactionModel)
        )
        return result.scalar() or 0

    async def count_by_account(self, acc_no: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(TransactionModel).where(
                TransactionModel.account_number == acc_no
            )
        )
        return result.scalar() or 0

    async def get_category_totals(self) -> dict[str, Decimal]:
        result = await self.session.execute(
            select(
                TransactionModel.category,
                func.sum(TransactionModel.amount)
            ).group_by(TransactionModel.category)
        )
        rows = result.all()
        return {cat: total or Decimal("0.00") for cat, total in rows}

    async def get_paginated(
        self,
        acc_no: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> tuple[list[Transaction], int]:
        query = select(TransactionModel)

        if acc_no:
            query = query.where(TransactionModel.account_number == acc_no)
        if from_date:
            query = query.where(TransactionModel.timestamp >= from_date)
        if to_date:
            query = query.where(TransactionModel.timestamp <= to_date)
        if txn_type:
            query = query.where(TransactionModel.type == txn_type)

        # Get total count
        count_query = select(func.count()).select_from(TransactionModel)
        if acc_no:
            count_query = count_query.where(TransactionModel.account_number == acc_no)
        if from_date:
            count_query = count_query.where(TransactionModel.timestamp >= from_date)
        if to_date:
            count_query = count_query.where(TransactionModel.timestamp <= to_date)
        if txn_type:
            count_query = count_query.where(TransactionModel.type == txn_type)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * per_page
        result = await self.session.execute(
            query.order_by(TransactionModel.timestamp.desc())
            .offset(offset)
            .limit(per_page)
        )
        models = result.scalars().all()

        return [map_transaction(m) for m in models], total

    async def get_paginated_keyset(
        self,
        acc_no: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[datetime] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> KeysetPage[Transaction]:
        query = select(TransactionModel)

        if acc_no:
            query = query.where(TransactionModel.account_number == acc_no)
        if from_date:
            query = query.where(TransactionModel.timestamp >= from_date)
        if to_date:
            query = query.where(TransactionModel.timestamp <= to_date)
        if txn_type:
            query = query.where(TransactionModel.type == txn_type)

        fetch_limit = limit + 1
        if cursor is not None:
            query = query.where(TransactionModel.timestamp < cursor)

        result = await self.session.execute(
            query.order_by(TransactionModel.timestamp.desc()).limit(fetch_limit)
        )
        models = result.scalars().all()

        has_more = len(models) > limit
        items = [map_transaction(m) for m in models[:limit]]
        next_cursor = items[-1].timestamp if items else None

        return KeysetPage(
            items=items,
            cursor=next_cursor,
            has_more=has_more,
            cursor_key="timestamp",
        )

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyAdminRepository:
    """Admin repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> Optional[AdminUser]:
        result = await self.session.execute(
            select(AdminModel).where(AdminModel.username == username)
        )
        model = result.scalar_one_or_none()
        return map_admin(model) if model else None

    async def create(self, admin: AdminUser) -> AdminUser:
        from unionbank.utils.token_security import encrypt_totp_secret
        model = AdminModel(
            username=admin.username,
            password=admin.password,
            role=admin.role or "admin",
            totp_secret=encrypt_totp_secret(admin.totp_secret),
            totp_enabled=admin.totp_enabled,
        )
        self.session.add(model)
        return admin

    async def update_password(self, username: str, new_hashed: str) -> bool:
        result = await self.session.execute(
            select(AdminModel).where(AdminModel.username == username)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.password = new_hashed
        return True

    async def update_totp(self, username: str, totp_secret: Optional[str], totp_enabled: bool) -> bool:
        from unionbank.utils.token_security import encrypt_totp_secret
        result = await self.session.execute(
            select(AdminModel).where(AdminModel.username == username)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.totp_secret = encrypt_totp_secret(totp_secret)
        model.totp_enabled = totp_enabled
        return True

    async def admin_count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(AdminModel)
        )
        return result.scalar() or 0

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings Goal Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemySavingsGoalRepository:
    """Savings goal repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_account(self, acc_no: str) -> list[SavingsGoal]:
        result = await self.session.execute(
            select(SavingsGoalModel).where(
                SavingsGoalModel.account_number == acc_no
            )
        )
        models = result.scalars().all()
        return [map_savings_goal(m) for m in models]

    async def get(self, goal_id: str) -> Optional[SavingsGoal]:
        result = await self.session.execute(
            select(SavingsGoalModel).where(SavingsGoalModel.goal_id == goal_id)
        )
        model = result.scalar_one_or_none()
        return map_savings_goal(model) if model else None

    async def create(self, goal: SavingsGoal) -> SavingsGoal:
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

    async def update(self, goal: SavingsGoal) -> SavingsGoal:
        result = await self.session.execute(
            select(SavingsGoalModel).where(SavingsGoalModel.goal_id == goal.goal_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.name = goal.name
            model.target_amount = goal.target_amount
            model.current_amount = goal.current_amount
            model.target_date = goal.target_date
            model.is_completed = goal.is_completed
        return goal

    async def contribute(self, goal_id: str, amount: Decimal) -> Optional[SavingsGoal]:
        result = await self.session.execute(
            select(SavingsGoalModel).where(SavingsGoalModel.goal_id == goal_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.current_amount += amount
        if model.current_amount >= model.target_amount:
            model.is_completed = True
        return map_savings_goal(model)

    async def delete(self, goal_id: str) -> Optional[SavingsGoal]:
        result = await self.session.execute(
            select(SavingsGoalModel).where(SavingsGoalModel.goal_id == goal_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        goal = map_savings_goal(model)
        await self.session.delete(model)
        return goal

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Loan Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyLoanRepository:
    """Loan repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, loan_id: str) -> Optional[Loan]:
        result = await self.session.execute(
            select(LoanModel).where(LoanModel.loan_id == loan_id)
        )
        model = result.scalar_one_or_none()
        return map_loan(model) if model else None

    async def get_by_account(self, acc_no: str) -> list[Loan]:
        result = await self.session.execute(
            select(LoanModel)
            .where(LoanModel.account_number == acc_no)
            .order_by(LoanModel.application_date.desc())
        )
        models = result.scalars().all()
        return [map_loan(m) for m in models]

    async def get_all_pending(self) -> list[Loan]:
        result = await self.session.execute(
            select(LoanModel)
            .where(LoanModel.status == "PENDING")
            .order_by(LoanModel.application_date.asc())
        )
        models = result.scalars().all()
        return [map_loan(m) for m in models]

    async def get_all_active(self) -> list[Loan]:
        result = await self.session.execute(
            select(LoanModel)
            .where(LoanModel.status.in_(["APPROVED", "ACTIVE"]))
            .order_by(LoanModel.application_date.desc())
        )
        models = result.scalars().all()
        return [map_loan(m) for m in models]

    async def get_all(self) -> list[Loan]:
        result = await self.session.execute(
            select(LoanModel).order_by(LoanModel.application_date.desc())
        )
        models = result.scalars().all()
        return [map_loan(m) for m in models]

    async def create(self, loan: Loan) -> Loan:
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

    async def update(self, loan: Loan) -> Loan:
        result = await self.session.execute(
            select(LoanModel).where(LoanModel.loan_id == loan.loan_id)
        )
        model = result.scalar_one_or_none()
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

    async def count_by_status(self, status: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(LoanModel).where(
                LoanModel.status == status
            )
        )
        return result.scalar() or 0

    async def total_disbursed(self) -> Decimal:
        result = await self.session.execute(
            select(func.sum(LoanModel.principal_amount)).where(
                LoanModel.status.in_(["APPROVED", "ACTIVE", "CLOSED"])
            )
        )
        return result.scalar() or Decimal("0.00")

    async def total_outstanding(self) -> Decimal:
        result = await self.session.execute(
            select(func.sum(LoanModel.remaining_amount)).where(
                LoanModel.status.in_(["APPROVED", "ACTIVE"])
            )
        )
        return result.scalar() or Decimal("0.00")

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Login Attempt Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyLoginAttemptRepository:
    """Login attempt repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> Optional[LoginAttempt]:
        result = await self.session.execute(
            select(LoginAttemptModel).where(LoginAttemptModel.key == key)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return LoginAttempt(
            key=model.key,
            count=model.count or 0,
            first_failed=model.first_failed,
            lockout_until=model.lockout_until,
            updated_at=model.updated_at,
        )

    async def record_failure(self, key: str, max_attempts: int = 5,
                              lockout_minutes: int = 15) -> int:
        record = await self.get(key)
        now = _utcnow()

        if record is None:
            model = LoginAttemptModel(
                key=key, count=1, first_failed=now
            )
            self.session.add(model)
        else:
            result = await self.session.execute(
                select(LoginAttemptModel).where(LoginAttemptModel.key == key)
            )
            model = result.scalar_one_or_none()

            if model and model.lockout_until and now >= model.lockout_until:
                model.count = 1
                model.first_failed = now
                model.lockout_until = None
            else:
                if model:
                    model.count = (model.count or 0) + 1

            if model and model.count >= max_attempts:
                model.lockout_until = now + timedelta(minutes=lockout_minutes)

        current_count = getattr(model, 'count', 0) if model else 1
        return max(0, max_attempts - (current_count or 0))

    async def is_locked(self, key: str, max_attempts: int = 5) -> tuple[bool, int]:
        result = await self.session.execute(
            select(LoginAttemptModel).where(LoginAttemptModel.key == key)
        )
        model = result.scalar_one_or_none()
        if model is None or (model.count or 0) < max_attempts:
            return False, 0

        now = _utcnow()
        lockout_until = model.lockout_until

        if lockout_until is not None and lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=timezone.utc)

        if lockout_until and now < lockout_until:
            remaining = int((lockout_until - now).total_seconds() // 60)
            return True, max(1, remaining)
        if model:
            await self.session.delete(model)
        return False, 0

    async def reset(self, key: str) -> None:
        result = await self.session.execute(
            select(LoginAttemptModel).where(LoginAttemptModel.key == key)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Token Version Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyTokenVersionRepository:
    """Token version repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_version(self, account_number: str) -> int:
        result = await self.session.execute(
            select(TokenVersionModel).where(
                TokenVersionModel.account_number == account_number
            )
        )
        model = result.scalar_one_or_none()
        return model.version if model else 0

    async def increment(self, account_number: str) -> int:
        result = await self.session.execute(
            select(TokenVersionModel).where(
                TokenVersionModel.account_number == account_number
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = TokenVersionModel(account_number=account_number, version=1)
            self.session.add(model)
        else:
            model.version += 1
        return model.version

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Notification Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyNotificationRepository:
    """Notification repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, notif_id: str) -> Optional[Notification]:
        result = await self.session.execute(
            select(NotificationModel).where(NotificationModel.notif_id == notif_id)
        )
        model = result.scalar_one_or_none()
        return map_notification(model) if model else None

    async def get_by_account(self, acc_no: str, limit: int = 50) -> list[Notification]:
        result = await self.session.execute(
            select(NotificationModel)
            .where(NotificationModel.account_number == acc_no)
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        return [map_notification(m) for m in models]

    async def get_unread_count(self, acc_no: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(NotificationModel).where(
                NotificationModel.account_number == acc_no,
                NotificationModel.is_read.is_(False),
            )
        )
        return result.scalar() or 0

    async def get_unread(self, acc_no: str, limit: int = 20) -> list[Notification]:
        result = await self.session.execute(
            select(NotificationModel)
            .where(
                NotificationModel.account_number == acc_no,
                NotificationModel.is_read.is_(False),
            )
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        return [map_notification(m) for m in models]

    async def create(self, notification: Notification) -> Notification:
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

    async def mark_as_read(self, notif_id: str) -> bool:
        result = await self.session.execute(
            select(NotificationModel).where(NotificationModel.notif_id == notif_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.is_read = True
        return True

    async def mark_all_as_read(self, acc_no: str) -> int:
        result = await self.session.execute(
            select(NotificationModel).where(
                NotificationModel.account_number == acc_no,
                NotificationModel.is_read.is_(False),
            )
        )
        models = result.scalars().all()
        count = len(models)
        for model in models:
            model.is_read = True
        return count

    async def delete_old(self, days: int = 30) -> int:
        from datetime import timedelta
        cutoff = _utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(NotificationModel).where(
                NotificationModel.created_at < cutoff
            )
        )
        models = result.scalars().all()
        count = len(models)
        for model in models:
            await self.session.delete(model)
        return count

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Notification Preference Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyNotificationPreferenceRepository:
    """Notification preferences repository backed by async SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, acc_no: str) -> Optional[NotificationPreference]:
        result = await self.session.execute(
            select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.account_number == acc_no
            )
        )
        model = result.scalar_one_or_none()
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

    async def create_or_update(self, pref: NotificationPreference) -> NotificationPreference:
        result = await self.session.execute(
            select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.account_number == pref.account_number
            )
        )
        model = result.scalar_one_or_none()
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

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Refresh Token Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyRefreshTokenRepository:
    """Refresh token repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, token_id: str) -> Optional[RefreshToken]:
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_id == token_id)
        )
        model = result.scalar_one_or_none()
        return map_refresh_token(model) if model else None

    async def get_by_account(self, account_number: str) -> list[RefreshToken]:
        result = await self.session.execute(
            select(RefreshTokenModel)
            .where(RefreshTokenModel.account_number == account_number)
            .order_by(RefreshTokenModel.created_at.desc())
        )
        models = result.scalars().all()
        return [map_refresh_token(m) for m in models]

    async def create(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            token_id=token.token_id,
            account_number=token.account_number,
            role=token.role,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
        )
        self.session.add(model)
        return token

    async def revoke(self, token_id: str) -> bool:
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_id == token_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.revoked_at = datetime.now(timezone.utc)
        return True

    async def revoke_all_for_account(self, account_number: str) -> int:
        result = await self.session.execute(
            select(RefreshTokenModel).where(
                RefreshTokenModel.account_number == account_number,
                RefreshTokenModel.revoked_at.is_(None),
            )
        )
        models = result.scalars().all()
        now = datetime.now(timezone.utc)
        for model in models:
            model.revoked_at = now
        return len(models)

    async def clean_expired(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(RefreshTokenModel).where(
                RefreshTokenModel.expires_at < now
            )
        )
        models = result.scalars().all()
        count = len(models)
        for model in models:
            await self.session.delete(model)
        return count

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Idempotency Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyIdempotencyRepository:
    """Idempotency key repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        result = await self.session.execute(
            select(IdempotencyModel).where(
                IdempotencyModel.idempotency_key == idempotency_key
            )
        )
        model = result.scalar_one_or_none()
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

    async def create(self, record: IdempotencyRecord) -> IdempotencyRecord:
        model = IdempotencyModel(
            idempotency_key=record.idempotency_key,
            account_number=record.account_number,
            operation=record.operation,
            result_json=record.result_json,
            amount=record.amount,
        )
        self.session.add(model)
        return record

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


# ═══════════════════════════════════════════════════════════════════════════════
#  Audit Log Repository (async)
# ═══════════════════════════════════════════════════════════════════════════════


class AsyncSqlAlchemyAuditLogRepository:
    """Audit log repository — append-only, never deleted or updated. (async)"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, actor: str, action: str, target: Optional[str] = None,
                   details: Optional[str] = None, ip_address: Optional[str] = None,
                   reason: Optional[str] = None) -> None:
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

    async def get_recent(self, limit: int = 50) -> list:
        result = await self.session.execute(
            select(AuditLogModel)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
        )
        models = result.scalars().all()
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

    async def get_by_actor(self, actor: str, limit: int = 50) -> list:
        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.actor == actor)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
        )
        models = result.scalars().all()
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

    async def get_by_action(self, action: str, limit: int = 50) -> list:
        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.action == action)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
        )
        models = result.scalars().all()
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

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
