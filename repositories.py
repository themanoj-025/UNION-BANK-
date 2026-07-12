"""
repositories.py  –  Data access layer for Union Bank.

Repositories abstract the data store behind a clean interface,
enabling dependency injection and testability.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    AccountModel, TransactionModel, SavingsGoalModel,
    AdminModel, LoginAttemptModel, TokenVersion,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
#  Account Repository
# ═══════════════════════════════════════════════════════════════════════════════

class AccountRepository:
    """Repository for customer account operations."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, acc_no: str) -> Optional[AccountModel]:
        return self.session.query(AccountModel).filter_by(
            account_number=acc_no
        ).first()

    def get_all(self) -> list[AccountModel]:
        return self.session.query(AccountModel).all()

    def exists(self, acc_no: str) -> bool:
        return self.session.query(AccountModel).filter_by(
            account_number=acc_no
        ).first() is not None

    def create(self, data: dict) -> AccountModel:
        account = AccountModel(
            account_number=data["account_number"],
            name=data.get("name", ""),
            age=data.get("age", 18),
            gender=data.get("gender", ""),
            mobile=data.get("mobile", ""),
            email=data.get("email", ""),
            password=data.get("password", ""),
            balance=Decimal(str(data.get("balance", 0))),
            is_active=data.get("is_active", True),
            is_frozen=data.get("is_frozen", False),
            created_at=_utcnow(),
        )
        self.session.add(account)
        return account

    def update_from_dict(self, acc_no: str, data: dict) -> Optional[AccountModel]:
        account = self.get(acc_no)
        if account is None:
            return None
        for key, value in data.items():
            if hasattr(account, key) and value is not None:
                if key == "balance":
                    setattr(account, key, Decimal(str(value)))
                else:
                    setattr(account, key, value)
        return account

    def update_balance(self, acc_no: str, new_balance: Decimal) -> bool:
        account = self.get(acc_no)
        if account is None:
            return False
        account.balance = new_balance
        return True

    def set_active(self, acc_no: str, active: bool) -> bool:
        account = self.get(acc_no)
        if account is None:
            return False
        account.is_active = active
        return True

    def set_frozen(self, acc_no: str, frozen: bool) -> bool:
        account = self.get(acc_no)
        if account is None:
            return False
        account.is_frozen = frozen
        account.is_active = not frozen
        return True

    def delete(self, acc_no: str) -> bool:
        account = self.get(acc_no)
        if account is None:
            return False
        self.session.delete(account)
        return True

    def search(self, query: str) -> list[AccountModel]:
        q = f"%{query}%"
        return self.session.query(AccountModel).filter(
            AccountModel.account_number.ilike(q)
            | AccountModel.name.ilike(q)
        ).all()

    def count(self) -> int:
        return self.session.query(AccountModel).count()

    def total_balance(self) -> Decimal:
        result = self.session.query(
            AccountModel.balance
        ).filter(
            AccountModel.is_active.is_(True),
            AccountModel.is_frozen.is_(False),
        ).all()
        return sum((r[0] for r in result), Decimal("0.00"))

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


# ═══════════════════════════════════════════════════════════════════════════════
#  Transaction Repository
# ═══════════════════════════════════════════════════════════════════════════════

class TransactionRepository:
    """Repository for transaction log operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_account(self, acc_no: str) -> list[TransactionModel]:
        return self.session.query(TransactionModel).filter_by(
            account_number=acc_no
        ).order_by(TransactionModel.timestamp.desc()).all()

    def get_mini(self, acc_no: str, limit: int = 5) -> list[TransactionModel]:
        return self.session.query(TransactionModel).filter_by(
            account_number=acc_no
        ).order_by(TransactionModel.timestamp.desc()).limit(limit).all()

    def create(self, acc_no: str, txn_type: str, amount: Decimal,
               balance: Decimal, description: str = "",
               category: str = "General",
               target_account: Optional[str] = None,
               txn_id: Optional[str] = None) -> TransactionModel:
        from utils import generate_transaction_id
        transaction = TransactionModel(
            txn_id=txn_id or generate_transaction_id(),
            account_number=acc_no,
            type=txn_type,
            amount=Decimal(str(amount)),
            balance=Decimal(str(balance)),
            description=description,
            category=category,
            target_account=target_account,
            timestamp=_utcnow(),
        )
        self.session.add(transaction)
        return transaction

    def get_all(self) -> list[TransactionModel]:
        return self.session.query(TransactionModel).order_by(
            TransactionModel.timestamp.desc()
        ).all()

    def get_by_account_and_type(self, acc_no: str) -> dict:
        """Get transactions grouped by type for statistics."""
        txns = self.get_by_account(acc_no)
        result = {"DEPOSIT": [], "WITHDRAW": [], "TRANSFER_OUT": [],
                  "TRANSFER_IN": [], "INTEREST": []}
        for t in txns:
            if t.type in result:
                result[t.type].append(t)
        return result

    def total_by_type(self, txn_type: str) -> Decimal:
        result = self.session.query(
            TransactionModel.amount
        ).filter_by(type=txn_type).all()
        return sum((r[0] for r in result), Decimal("0.00"))

    def count(self) -> int:
        return self.session.query(TransactionModel).count()

    def count_by_account(self, acc_no: str) -> int:
        return self.session.query(TransactionModel).filter_by(
            account_number=acc_no
        ).count()


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Repository
# ═══════════════════════════════════════════════════════════════════════════════

class AdminRepository:
    """Repository for admin user operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> Optional[AdminModel]:
        return self.session.query(AdminModel).filter_by(
            username=username
        ).first()

    def create_default(self) -> AdminModel:
        """Create the default admin if none exists."""
        existing = self.session.query(AdminModel).first()
        if existing:
            return existing
        from utils import hash_password
        admin = AdminModel(
            username="simon",
            password=hash_password("simon123"),
            role="admin",
        )
        self.session.add(admin)
        return admin

    def update_password(self, username: str, new_hashed: str) -> bool:
        admin = self.get_by_username(username)
        if admin is None:
            return False
        admin.password = new_hashed
        return True


# ═══════════════════════════════════════════════════════════════════════════════
#  Login Attempt Repository
# ═══════════════════════════════════════════════════════════════════════════════

class LoginAttemptRepository:
    """Repository for rate-limiting data."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, key: str) -> Optional[LoginAttemptModel]:
        return self.session.query(LoginAttemptModel).filter_by(key=key).first()

    def record_failure(self, key: str, max_attempts: int = 5,
                       lockout_minutes: int = 15) -> int:
        from datetime import timedelta
        record = self.get(key)
        now = _utcnow()

        if record is None:
            record = LoginAttemptModel(key=key, count=1, first_failed=now)
            self.session.add(record)
        else:
            # Reset if lockout expired
            if record.lockout_until and now >= record.lockout_until:
                record.count = 1
                record.first_failed = now
                record.lockout_until = None
            else:
                record.count = (record.count or 0) + 1

            if record.count >= max_attempts:
                record.lockout_until = now + timedelta(minutes=lockout_minutes)

        return max(0, max_attempts - (record.count or 0))

    def is_locked(self, key: str, max_attempts: int = 5) -> tuple[bool, int]:
        record = self.get(key)
        if record is None or (record.count or 0) < max_attempts:
            return False, 0
        if record.lockout_until and _utcnow() < record.lockout_until:
            remaining = int(
                (record.lockout_until - _utcnow()).total_seconds() // 60
            )
            return True, max(1, remaining)
        # Lockout expired — reset
        if record:
            self.session.delete(record)
        return False, 0

    def reset(self, key: str) -> None:
        record = self.get(key)
        if record:
            self.session.delete(record)


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings Goal Repository
# ═══════════════════════════════════════════════════════════════════════════════

class SavingsGoalRepository:
    """Repository for savings goal operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_account(self, acc_no: str) -> list[SavingsGoalModel]:
        return self.session.query(SavingsGoalModel).filter_by(
            account_number=acc_no
        ).all()

    def get(self, goal_id: str) -> Optional[SavingsGoalModel]:
        return self.session.query(SavingsGoalModel).filter_by(
            goal_id=goal_id
        ).first()

    def create(self, acc_no: str, name: str, target_amount: Decimal,
               target_date: Optional[str] = None) -> SavingsGoalModel:
        from utils import generate_goal_id
        goal = SavingsGoalModel(
            goal_id=generate_goal_id(),
            account_number=acc_no,
            name=name,
            target_amount=Decimal(str(target_amount)),
            current_amount=Decimal("0.00"),
            target_date=target_date,
        )
        self.session.add(goal)
        return goal

    def update(self, goal_id: str, **kwargs) -> Optional[SavingsGoalModel]:
        goal = self.get(goal_id)
        if goal is None:
            return None
        for key, value in kwargs.items():
            if hasattr(goal, key) and value is not None:
                if key in ("target_amount", "current_amount"):
                    setattr(goal, key, Decimal(str(value)))
                else:
                    setattr(goal, key, value)
        goal.is_completed = goal.current_amount >= goal.target_amount
        return goal

    def contribute(self, goal_id: str, amount: Decimal) -> Optional[SavingsGoalModel]:
        goal = self.get(goal_id)
        if goal is None:
            return None
        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
        return goal

    def delete(self, goal_id: str) -> Optional[SavingsGoalModel]:
        goal = self.get(goal_id)
        if goal is None:
            return None
        refund = goal.current_amount
        self.session.delete(goal)
        return goal  # Return it so caller can access .current_amount for refund


# ═══════════════════════════════════════════════════════════════════════════════
#  Token Version Repository
# ═══════════════════════════════════════════════════════════════════════════════

class TokenVersionRepository:
    """Repository for JWT token version tracking."""

    def __init__(self, session: Session):
        self.session = session

    def get_version(self, account_number: str) -> int:
        record = self.session.query(TokenVersion).filter_by(
            account_number=account_number
        ).first()
        return record.version if record else 0

    def increment(self, account_number: str) -> int:
        record = self.session.query(TokenVersion).filter_by(
            account_number=account_number
        ).first()
        if record is None:
            record = TokenVersion(
                account_number=account_number, version=1
            )
            self.session.add(record)
        else:
            record.version += 1
        return record.version
