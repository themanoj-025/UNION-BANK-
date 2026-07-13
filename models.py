"""
models.py  –  SQLAlchemy ORM models for Union Bank Management System.

Re-exports from the new infrastructure layer for backward compatibility.
New code should import from infrastructure.persistence directly.
"""

# Re-export from the new architecture
from infrastructure.persistence import (  # noqa: F401
    AccountModel,
    TransactionModel,
    SavingsGoalModel,
    AdminModel,
    LoginAttemptModel,
    TokenVersionModel as TokenVersion,
)
from infrastructure.database import ModelBase as Base  # noqa: F401
