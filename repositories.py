"""
repositories.py  –  Data access layer (backward-compatible re-exports).

Delegates to the new infrastructure layer. New code should import directly
from infrastructure.repositories.
"""

from infrastructure.repositories import (  # noqa: F401
    SqlAlchemyAccountRepository as AccountRepository,
    SqlAlchemyTransactionRepository as TransactionRepository,
    SqlAlchemyAdminRepository as AdminRepository,
    SqlAlchemySavingsGoalRepository as SavingsGoalRepository,
    SqlAlchemyLoginAttemptRepository as LoginAttemptRepository,
    SqlAlchemyTokenVersionRepository as TokenVersionRepository,
)
