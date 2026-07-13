"""
application/services.py  –  Use-case service classes.

Each service has a single `execute()` method (or multiple focused methods).
Services depend only on repository protocols — never on concrete DB code.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator, Optional

from sqlalchemy.orm import Session

from domain.entities import (
    Account,
    AdminUser,
    SavingsGoal,
    ServiceResult,
    TokenVersion,
    Transaction,
    TransactionType,
    TransferResult,
)

from .interfaces import (
    AccountRepositoryProtocol,
    AdminRepositoryProtocol,
    AuditLogRepositoryProtocol,
    LoginAttemptRepositoryProtocol,
    SavingsGoalRepositoryProtocol,
    TokenVersionRepositoryProtocol,
    TransactionRepositoryProtocol,
)

from utils.auth import hash_password, verify_password, calculate_monthly_interest
from utils.formatting import fmt_currency, generate_account_number, generate_transaction_id, generate_goal_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
#  Auth Service
# ═══════════════════════════════════════════════════════════════════════════════

TRANSACTION_CATEGORIES = [
    "General", "Food & Dining", "Transport", "Shopping",
    "Bills & Utilities", "Entertainment", "Health", "Education",
    "Salary", "Savings", "Investment", "Rent", "Other",
]

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15


class AuthService:
    """Authentication and authorization use-cases."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        admin_repo: AdminRepositoryProtocol,
        login_attempt_repo: LoginAttemptRepositoryProtocol,
        token_version_repo: Optional[TokenVersionRepositoryProtocol] = None,
    ):
        self.account_repo = account_repo
        self.admin_repo = admin_repo
        self.login_attempt_repo = login_attempt_repo
        self.token_version_repo = token_version_repo

    def customer_login(self, acc_no: str, password: str) -> ServiceResult:
        """Authenticate a customer login."""
        # Rate limiting check
        is_locked, remaining = self.login_attempt_repo.is_locked(acc_no)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Account locked. Try again in {remaining} minute(s).",
            )

        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if account.is_frozen:
            return ServiceResult(success=False, message="Account is frozen. Please contact the bank.")

        if not account.is_active:
            return ServiceResult(success=False, message="Account has been closed.")

        if not verify_password(password, account.password):
            remaining = self.login_attempt_repo.record_failure(
                acc_no, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
            )
            self.login_attempt_repo.commit()
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

        self.login_attempt_repo.reset(acc_no)
        self.login_attempt_repo.commit()
        return ServiceResult(success=True, data={"account_number": acc_no, "role": "customer"})

    def customer_register(
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
        self.account_repo.create(account)
        self.account_repo.commit()
        return ServiceResult(
            success=True,
            message=f"Account created successfully! Account number: {acc_no}",
            data={"account_number": acc_no},
        )

    def admin_login(self, username: str, password: str) -> ServiceResult:
        """Authenticate an admin login."""
        lock_key = f"admin_{username}"
        is_locked, remaining = self.login_attempt_repo.is_locked(lock_key)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Admin account locked. Try again in {remaining} minute(s).",
            )

        admin = self.admin_repo.get_by_username(username)
        if admin and verify_password(password, admin.password):
            self.login_attempt_repo.reset(lock_key)
            self.login_attempt_repo.commit()
            return ServiceResult(success=True, data={"username": username, "role": "admin"})

        remaining = self.login_attempt_repo.record_failure(
            lock_key, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
        )
        self.login_attempt_repo.commit()
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
#  Account Service
# ═══════════════════════════════════════════════════════════════════════════════


class AccountService:
    """Customer account management use-cases."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        token_version_repo: Optional[TokenVersionRepositoryProtocol] = None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.token_version_repo = token_version_repo

    def get_profile(self, acc_no: str) -> Optional[Account]:
        return self.account_repo.get(acc_no)

    def update_profile(self, acc_no: str, **kwargs) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        for key, value in kwargs.items():
            if hasattr(account, key) and value is not None:
                setattr(account, key, value)

        self.account_repo.update(account)
        self.account_repo.commit()
        return ServiceResult(success=True, message="Profile updated successfully.")

    def change_password(self, acc_no: str, current_pwd: str, new_pwd: str) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(current_pwd, account.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        account.password = hash_password(new_pwd)
        self.account_repo.update(account)

        # Increment token version to invalidate all existing JWTs
        if self.token_version_repo:
            self.token_version_repo.increment(acc_no)

        self.account_repo.commit()
        return ServiceResult(success=True, message="Password changed successfully.")

    def close_account(self, acc_no: str, password: str) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(password, account.password):
            return ServiceResult(success=False, message="Incorrect password.")

        account.is_active = False
        self.account_repo.update(account)
        self.account_repo.commit()
        return ServiceResult(success=True, message="Account closed successfully.")

    def get_balance(self, acc_no: str) -> Optional[Decimal]:
        account = self.account_repo.get(acc_no)
        return account.balance if account else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Transaction Service
# ═══════════════════════════════════════════════════════════════════════════════


class TransactionService:
    """Transaction use-cases (deposit, withdraw, transfer, statement, interest)."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo

    def deposit(self, acc_no: str, amount: Decimal, category: str = "General") -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.can_transact:
            status = "frozen" if account.is_frozen else "closed"
            return ServiceResult(success=False, message=f"Account is {status}.")

        account.balance += amount
        self.account_repo.update(account)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.DEPOSIT,
            amount=amount,
            balance=account.balance,
            description="Deposit",
            category=category if category in TRANSACTION_CATEGORIES else "General",
        )
        self.txn_repo.create(txn)
        self.account_repo.commit()

        return ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} deposited successfully. "
                    f"New balance: {fmt_currency(float(account.balance))}",
            data={"balance": float(account.balance)},
        )

    def withdraw(self, acc_no: str, amount: Decimal, category: str = "General") -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        account = self.account_repo.get(acc_no)
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
        self.account_repo.update(account)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.WITHDRAW,
            amount=amount,
            balance=account.balance,
            description="Withdrawal",
            category=category if category in TRANSACTION_CATEGORIES else "General",
        )
        self.txn_repo.create(txn)
        self.account_repo.commit()

        return ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} withdrawn successfully. "
                    f"New balance: {fmt_currency(float(account.balance))}",
            data={"balance": float(account.balance)},
        )

    def transfer(
        self, sender_acc_no: str, receiver_acc_no: str,
        amount: Decimal, category: str = "General",
    ) -> TransferResult:
        if amount <= 0:
            return TransferResult(success=False, error_message="Amount must be positive.")
        if sender_acc_no == receiver_acc_no:
            return TransferResult(success=False, error_message="Cannot transfer to your own account.")

        sender = self.account_repo.get(sender_acc_no)
        receiver = self.account_repo.get(receiver_acc_no)

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

        cat = category if category in TRANSACTION_CATEGORIES else "General"

        # Atomic debit/credit
        sender.balance -= amount
        receiver.balance += amount

        self.account_repo.update(sender)
        self.account_repo.update(receiver)

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
        self.txn_repo.create(sender_txn)
        self.txn_repo.create(receiver_txn)
        self.account_repo.commit()

        return TransferResult(
            success=True,
            sender_balance=sender.balance,
            receiver_balance=receiver.balance,
        )

    def get_statement(self, acc_no: str) -> list[Transaction]:
        return self.txn_repo.get_by_account(acc_no)

    def get_mini_statement(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        return self.txn_repo.get_mini(acc_no, limit)

    def apply_interest(self, acc_no: str) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.can_transact:
            return ServiceResult(success=False, message="Account is frozen or closed.")

        interest = Decimal(str(calculate_monthly_interest(float(account.balance))))
        if interest <= 0:
            return ServiceResult(success=False, message="No interest to apply.")

        account.balance += interest
        self.account_repo.update(account)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.INTEREST,
            amount=interest,
            balance=account.balance,
            description="Monthly interest credit",
            category="Savings",
        )
        self.txn_repo.create(txn)
        self.account_repo.commit()

        return ServiceResult(
            success=True,
            message=f"Interest of {fmt_currency(float(interest))} credited! "
                    f"New balance: {fmt_currency(float(account.balance))}",
            data={"interest": float(interest), "balance": float(account.balance)},
        )

    def get_category_totals(self) -> dict[str, Decimal]:
        return self.txn_repo.get_category_totals()

    def get_paginated_transactions(
        self,
        acc_no: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> tuple[list[Transaction], int]:
        return self.txn_repo.get_paginated(
            acc_no=acc_no, page=page, per_page=per_page,
            from_date=from_date, to_date=to_date, txn_type=txn_type,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Service
# ═══════════════════════════════════════════════════════════════════════════════


class AdminService:
    """Admin use-cases for account oversight."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        admin_repo: AdminRepositoryProtocol,
        audit_log_repo: Optional[AuditLogRepositoryProtocol] = None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.admin_repo = admin_repo
        self.audit_log_repo = audit_log_repo

    def _audit_log(self, actor: str, action: str, target: Optional[str] = None,
                   details: Optional[str] = None, ip_address: Optional[str] = None,
                   reason: Optional[str] = None) -> None:
        """Write an immutable audit log entry (silently skip if no repo configured)."""
        if self.audit_log_repo:
            self.audit_log_repo.log(
                actor=actor, action=action, target=target,
                details=details, ip_address=ip_address, reason=reason,
            )
            self.audit_log_repo.commit()

    def list_accounts(self) -> list[Account]:
        return self.account_repo.get_all()

    def search_accounts(self, query: str) -> list[Account]:
        return self.account_repo.search(query)

    def freeze_account(self, acc_no: str, actor: str = "admin",
                       reason: Optional[str] = None) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_active and not account.is_frozen:
            return ServiceResult(success=False, message="Account is permanently closed.")
        if account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is already frozen.")

        self.account_repo.set_frozen(acc_no, True)
        self.account_repo.commit()

        # Audit log
        self._audit_log(
            actor=actor, action="freeze", target=acc_no,
            details=f"Frozen account for {account.name}",
            reason=reason,
        )
        return ServiceResult(success=True, message=f"Account {acc_no} ({account.name}) has been frozen.")

    def unfreeze_account(self, acc_no: str, actor: str = "admin",
                         reason: Optional[str] = None) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is not frozen.")

        self.account_repo.set_frozen(acc_no, False)
        self.account_repo.commit()

        # Audit log
        self._audit_log(
            actor=actor, action="unfreeze", target=acc_no,
            details=f"Unfrozen account for {account.name}",
            reason=reason,
        )
        return ServiceResult(success=True, message=f"Account {acc_no} ({account.name}) has been unfrozen.")

    def delete_account(self, acc_no: str, actor: str = "admin",
                       reason: Optional[str] = None) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        acc_name = account.name
        self.account_repo.delete(acc_no)
        self.account_repo.commit()

        # Audit log
        self._audit_log(
            actor=actor, action="delete", target=acc_no,
            details=f"Deleted account for {acc_name}",
            reason=reason,
        )
        return ServiceResult(success=True, message=f"Account {acc_no} ({acc_name}) has been deleted.")

    def get_statistics(self) -> dict:
        """Compute bank-wide statistics."""
        total_customers = self.account_repo.count()
        active = self.account_repo.active_count()
        frozen = self.account_repo.frozen_count()
        closed = self.account_repo.closed_count()
        total_balance = float(self.account_repo.total_balance())
        total_txns = self.txn_repo.count()
        total_dep = float(self.txn_repo.total_by_type("DEPOSIT"))
        total_with = float(self.txn_repo.total_by_type("WITHDRAW"))
        total_trans = float(self.txn_repo.total_by_type("TRANSFER_OUT"))
        category_totals = self.txn_repo.get_category_totals()
        sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_customers": total_customers,
            "active": active,
            "frozen": frozen,
            "closed": closed,
            "total_balance": total_balance,
            "total_balance_formatted": fmt_currency(total_balance),
            "total_dep": total_dep,
            "total_with": total_with,
            "total_trans": total_trans,
            "total_txns": total_txns,
            "sorted_categories": [{"name": c[0], "total": float(c[1])} for c in sorted_cats[:8]],
        }

    def change_admin_password(self, username: str, current_pwd: str, new_pwd: str,
                              actor: str = "admin") -> ServiceResult:
        admin = self.admin_repo.get_by_username(username)
        if admin is None:
            return ServiceResult(success=False, message="Admin not found.")
        if not verify_password(current_pwd, admin.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        self.admin_repo.update_password(username, hash_password(new_pwd))
        self.admin_repo.commit()

        # Audit log
        self._audit_log(
            actor=actor, action="password_reset", target=username,
            details="Admin password changed",
        )
        return ServiceResult(success=True, message="Admin password changed successfully.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings Goal Service
# ═══════════════════════════════════════════════════════════════════════════════


class SavingsGoalService:
    """Savings goal use-cases."""

    def __init__(
        self,
        goal_repo: SavingsGoalRepositoryProtocol,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
    ):
        self.goal_repo = goal_repo
        self.account_repo = account_repo
        self.txn_repo = txn_repo

    def list_goals(self, acc_no: str) -> list[SavingsGoal]:
        return self.goal_repo.get_by_account(acc_no)

    def create_goal(self, acc_no: str, name: str, target_amount: Decimal,
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
        self.goal_repo.create(goal)
        self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' created!")

    def contribute(self, acc_no: str, goal_id: str, amount: Decimal) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if amount > account.balance:
            return ServiceResult(success=False, message="Insufficient balance.")

        goal = self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        # Deduct from account
        account.balance -= amount
        self.account_repo.update(account)

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
        self.txn_repo.create(txn)

        # Contribute to goal
        self.goal_repo.contribute(goal_id, amount)
        self.account_repo.commit()

        return ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} contributed to '{goal.name}'!",
        )

    def delete_goal(self, acc_no: str, goal_id: str) -> ServiceResult:
        goal = self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        refund = goal.current_amount
        name = goal.name
        self.goal_repo.delete(goal_id)

        # Refund to balance
        if refund > 0:
            account = self.account_repo.get(acc_no)
            if account:
                account.balance += refund
                self.account_repo.update(account)

        self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' deleted. Amount refunded.")
