"""container.py  –  Dependency Injection Container.

Wires together the application's dependencies using simple factory functions.
All dependencies flow inward: interfaces → application services → infrastructure repos.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from application.notifications import LogNotificationSender, NotificationService
from application.services import (
    AccountService,
    AdminService,
    AuthService,
    LoanService,
    SavingsGoalService,
    TransactionService,
)
from infrastructure.database import close_session, get_session, init_db
from infrastructure.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyAdminRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyLoanRepository,
    SqlAlchemyLoginAttemptRepository,
    SqlAlchemyNotificationPreferenceRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemySavingsGoalRepository,
    SqlAlchemyTokenVersionRepository,
    SqlAlchemyTransactionRepository,
)
from sqlalchemy.orm import Session


class Container:
    """Dependency injection container for Union Bank."""

    def __init__(self):
        self._session: Optional[Session] = None

    # ── Session management ─────────────────────────────────────────────────

    def get_session(self) -> Session:
        """Get the current thread's DB session."""
        return get_session()

    def close_session(self):
        close_session()

    # ── Repositories ───────────────────────────────────────────────────────

    def account_repo(self) -> SqlAlchemyAccountRepository:
        return SqlAlchemyAccountRepository(self.get_session())

    def transaction_repo(self) -> SqlAlchemyTransactionRepository:
        return SqlAlchemyTransactionRepository(self.get_session())

    def admin_repo(self) -> SqlAlchemyAdminRepository:
        return SqlAlchemyAdminRepository(self.get_session())

    def savings_goal_repo(self) -> SqlAlchemySavingsGoalRepository:
        return SqlAlchemySavingsGoalRepository(self.get_session())

    def loan_repo(self) -> SqlAlchemyLoanRepository:
        return SqlAlchemyLoanRepository(self.get_session())

    def login_attempt_repo(self) -> SqlAlchemyLoginAttemptRepository:
        return SqlAlchemyLoginAttemptRepository(self.get_session())

    def token_version_repo(self) -> SqlAlchemyTokenVersionRepository:
        return SqlAlchemyTokenVersionRepository(self.get_session())

    def audit_log_repo(self) -> SqlAlchemyAuditLogRepository:
        return SqlAlchemyAuditLogRepository(self.get_session())

    def notif_repo(self) -> SqlAlchemyNotificationRepository:
        return SqlAlchemyNotificationRepository(self.get_session())

    def notif_pref_repo(self) -> SqlAlchemyNotificationPreferenceRepository:
        return SqlAlchemyNotificationPreferenceRepository(self.get_session())

    def idempotency_repo(self) -> SqlAlchemyIdempotencyRepository:
        return SqlAlchemyIdempotencyRepository(self.get_session())

    def refresh_token_repo(self) -> SqlAlchemyRefreshTokenRepository:
        return SqlAlchemyRefreshTokenRepository(self.get_session())

    def notification_sender(self) -> LogNotificationSender:
        return LogNotificationSender()

    def notification_service(self) -> NotificationService:
        return NotificationService(
            notif_repo=self.notif_repo(),
            pref_repo=self.notif_pref_repo(),
            account_repo=self.account_repo(),
            sender=self.notification_sender(),
        )

    # ── Services ───────────────────────────────────────────────────────────

    def auth_service(self) -> AuthService:
        return AuthService(
            account_repo=self.account_repo(),
            admin_repo=self.admin_repo(),
            login_attempt_repo=self.login_attempt_repo(),
            token_version_repo=self.token_version_repo(),
            notif_service=self.notification_service(),
        )

    def account_service(self) -> AccountService:
        return AccountService(
            account_repo=self.account_repo(),
            txn_repo=self.transaction_repo(),
            token_version_repo=self.token_version_repo(),
        )

    def transaction_service(self) -> TransactionService:
        _notif = self.notification_service()
        return TransactionService(
            account_repo=self.account_repo(),
            txn_repo=self.transaction_repo(),
            notif_service=_notif,
            idempotency_repo=self.idempotency_repo(),
        )

    def admin_service(self) -> AdminService:
        _notif = self.notification_service()
        return AdminService(
            account_repo=self.account_repo(),
            txn_repo=self.transaction_repo(),
            admin_repo=self.admin_repo(),
            audit_log_repo=self.audit_log_repo(),
            notif_service=_notif,
        )

    def savings_goal_service(self) -> SavingsGoalService:
        return SavingsGoalService(
            goal_repo=self.savings_goal_repo(),
            account_repo=self.account_repo(),
            txn_repo=self.transaction_repo(),
        )

    def loan_service(self) -> LoanService:
        _notif = self.notification_service()
        return LoanService(
            loan_repo=self.loan_repo(),
            account_repo=self.account_repo(),
            txn_repo=self.transaction_repo(),
            audit_log_repo=self.audit_log_repo(),
            notif_service=_notif,
        )


# ── Global singleton ─────────────────────────────────────────────────────────

_container: Optional[Container] = None


def get_container() -> Container:
    """Get or create the global DI container."""
    global _container
    if _container is None:
        init_db()
        _container = Container()
    return _container


def reset_container():
    """Reset the DI container and close all active sessions (useful for testing)."""
    global _container
    # Close any existing session before resetting
    from infrastructure.database import close_session, reset_engine
    close_session()
    reset_engine()
    _container = None
