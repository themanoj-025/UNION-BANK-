"""
async_container.py  –  Dependency Injection Container (async variant).

Provides async repository AND service instances when the application is
configured with a PostgreSQL DATABASE_URL. Works alongside the synchronous
Container for SQLite-based development and testing.

Usage::

    from unionbank.infrastructure.database import is_postgres
    from unionbank.infrastructure.container import get_container
    from unionbank.infrastructure.async_container import get_async_container

    if is_postgres():
        container = await get_async_container()
        account = await container.account_repo().get("1000000001")
        result = await container.transaction_service().deposit(...)
    else:
        container = get_container()
        account = container.account_repo().get("1000000001")
        result = container.transaction_service().deposit(...)
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from unionbank.infrastructure.async_repositories import (
    AsyncSqlAlchemyAccountRepository,
    AsyncSqlAlchemyAdminRepository,
    AsyncSqlAlchemyAuditLogRepository,
    AsyncSqlAlchemyIdempotencyRepository,
    AsyncSqlAlchemyLoanRepository,
    AsyncSqlAlchemyLoginAttemptRepository,
    AsyncSqlAlchemyNotificationPreferenceRepository,
    AsyncSqlAlchemyNotificationRepository,
    AsyncSqlAlchemyRefreshTokenRepository,
    AsyncSqlAlchemySavingsGoalRepository,
    AsyncSqlAlchemyTokenVersionRepository,
    AsyncSqlAlchemyTransactionRepository,
)
from unionbank.infrastructure.database import get_async_session


class AsyncContainer:
    """Dependency injection container with async repository and service access.

    All repository methods return coroutines. Services using this container
    must ``await`` every repository call.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── Repositories ───────────────────────────────────────────────────────

    def account_repo(self) -> AsyncSqlAlchemyAccountRepository:
        return AsyncSqlAlchemyAccountRepository(self._session)

    def transaction_repo(self) -> AsyncSqlAlchemyTransactionRepository:
        return AsyncSqlAlchemyTransactionRepository(self._session)

    def admin_repo(self) -> AsyncSqlAlchemyAdminRepository:
        return AsyncSqlAlchemyAdminRepository(self._session)

    def savings_goal_repo(self) -> AsyncSqlAlchemySavingsGoalRepository:
        return AsyncSqlAlchemySavingsGoalRepository(self._session)

    def loan_repo(self) -> AsyncSqlAlchemyLoanRepository:
        return AsyncSqlAlchemyLoanRepository(self._session)

    def login_attempt_repo(self) -> AsyncSqlAlchemyLoginAttemptRepository:
        return AsyncSqlAlchemyLoginAttemptRepository(self._session)

    def token_version_repo(self) -> AsyncSqlAlchemyTokenVersionRepository:
        return AsyncSqlAlchemyTokenVersionRepository(self._session)

    def audit_log_repo(self) -> AsyncSqlAlchemyAuditLogRepository:
        return AsyncSqlAlchemyAuditLogRepository(self._session)

    def notif_repo(self) -> AsyncSqlAlchemyNotificationRepository:
        return AsyncSqlAlchemyNotificationRepository(self._session)

    def notif_pref_repo(self) -> AsyncSqlAlchemyNotificationPreferenceRepository:
        return AsyncSqlAlchemyNotificationPreferenceRepository(self._session)

    def idempotency_repo(self) -> AsyncSqlAlchemyIdempotencyRepository:
        return AsyncSqlAlchemyIdempotencyRepository(self._session)

    def refresh_token_repo(self) -> AsyncSqlAlchemyRefreshTokenRepository:
        return AsyncSqlAlchemyRefreshTokenRepository(self._session)

    # ── Services ───────────────────────────────────────────────────────────

    def transaction_service(self):
        """Create an async TransactionService wired to async repositories."""
        from unionbank.application.async_services import AsyncTransactionService
        return AsyncTransactionService(
            account_repo=self.account_repo(),
            txn_repo=self.transaction_repo(),
            idempotency_repo=self.idempotency_repo(),
        )

    def account_service(self):
        """Create an async AccountService wired to async repositories."""
        from unionbank.application.async_services import AsyncAccountService
        return AsyncAccountService(
            account_repo=self.account_repo(),
            txn_repo=self.transaction_repo(),
            token_version_repo=self.token_version_repo(),
        )

    def auth_service(self):
        """Create an async AuthService wired to async repositories."""
        from unionbank.application.async_services import AsyncAuthService
        return AsyncAuthService(
            account_repo=self.account_repo(),
            admin_repo=self.admin_repo(),
            login_attempt_repo=self.login_attempt_repo(),
            token_version_repo=self.token_version_repo(),
        )

    def admin_service(self):
        """Create an async AdminService wired to async repositories."""
        from unionbank.application.async_services import AsyncAdminService
        return AsyncAdminService(
            account_repo=self.account_repo(),
            txn_repo=self.transaction_repo(),
            admin_repo=self.admin_repo(),
            audit_log_repo=self.audit_log_repo(),
        )

    def savings_goal_service(self):
        """Create an async SavingsGoalService wired to async repositories."""
        from unionbank.application.async_services import AsyncSavingsGoalService
        return AsyncSavingsGoalService(
            goal_repo=self.savings_goal_repo(),
            account_repo=self.account_repo(),
            txn_repo=self.transaction_repo(),
        )

    async def close_session(self):
        """Close the underlying async session."""
        await self._session.close()


_async_container: Optional[AsyncContainer] = None


async def get_async_container() -> AsyncContainer:
    """Get or create the global async DI container (for PostgreSQL)."""
    global _async_container
    if _async_container is None:
        from unionbank.infrastructure.database import init_db
        init_db()
        session = await get_async_session()
        _async_container = AsyncContainer(session)
    return _async_container


async def reset_async_container():
    """Reset the async container — for testing."""
    global _async_container
    if _async_container is not None:
        await _async_container.close_session()
        _async_container = None
