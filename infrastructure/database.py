"""
infrastructure/database.py  –  SQLAlchemy engine, session management, and init.

Provides ACID transaction support via atomic_session() context manager.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from config import settings
from logger import logger


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
#  Model Base (re-exported for Alembic)
# ═══════════════════════════════════════════════════════════════════════════════

ModelBase = declarative_base()

# ═══════════════════════════════════════════════════════════════════════════════
#  Engine setup
# ═══════════════════════════════════════════════════════════════════════════════

DATA_DIR = Path(settings.DATA_DIR)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR / "union_bank.db")
_engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)


@event.listens_for(_engine, "connect")
def _set_pragmas(dbapi_connection, connection_record):
    """Enable WAL mode and foreign keys for better performance and integrity."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
_thread_local = threading.local()


def get_engine():
    return _engine


# ═══════════════════════════════════════════════════════════════════════════════
#  Session management
# ═══════════════════════════════════════════════════════════════════════════════


def get_session() -> Session:
    """Get the current thread's database session."""
    if not hasattr(_thread_local, "session") or _thread_local.session is None:
        _thread_local.session = _SessionLocal()
    return _thread_local.session


def close_session():
    """Close the current thread's database session."""
    if hasattr(_thread_local, "session") and _thread_local.session is not None:
        try:
            _thread_local.session.close()
        except Exception:
            pass
        _thread_local.session = None


@contextmanager
def atomic_session() -> Generator[Session, None, None]:
    """Provide a transactional scope — commits on success, rolls back on exception."""
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  DB Initialization
# ═══════════════════════════════════════════════════════════════════════════════


def init_db():
    """Create all tables if they don't exist."""
    from .persistence import AccountModel, TransactionModel, SavingsGoalModel, AdminModel, LoginAttemptModel, TokenVersionModel, AuditLogModel  # noqa: F401
    ModelBase.metadata.create_all(bind=_engine)
