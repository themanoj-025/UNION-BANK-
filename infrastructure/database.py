"""
infrastructure/database.py  –  SQLAlchemy engine, session management, and init.

Provides ACID transaction support via atomic_session() context manager.
Engine creation is lazy — it picks up the current DATA_DIR each time.
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
#  Lazy engine creation — recreates when DATA_DIR changes (e.g., during tests)
# ═══════════════════════════════════════════════════════════════════════════════

_engine_instance = None
_session_maker = None
_thread_local = threading.local()


def _get_db_path() -> str:
    """Get the SQLite database path from current settings / env override."""
    data_dir = Path(os.environ.get("UNION_BANK_DATA_DIR", str(settings.DATA_DIR)))
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "union_bank.db")


def get_engine():
    """Get or create the SQLAlchemy engine for the current DATA_DIR."""
    global _engine_instance, _session_maker
    db_path = _get_db_path()

    # If engine exists for a different path, dispose and recreate
    if _engine_instance is not None:
        current_url = str(_engine_instance.url)
        expected_url = f"sqlite:///{db_path}"
        if current_url == expected_url:
            return _engine_instance
        # Path changed — dispose old engine
        _engine_instance.dispose()
        _engine_instance = None
        _session_maker = None

    _engine_instance = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    @event.listens_for(_engine_instance, "connect")
    def _set_pragmas(dbapi_connection, connection_record):
        """Enable WAL mode and foreign keys for better performance and integrity."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    _session_maker = sessionmaker(autocommit=False, autoflush=False, bind=_engine_instance)
    return _engine_instance


def reset_engine():
    """Dispose the current engine and clear all sessions — for testing."""
    global _engine_instance, _session_maker
    close_session()
    if _engine_instance is not None:
        try:
            _engine_instance.dispose()
        except Exception:
            pass
        _engine_instance = None
        _session_maker = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Session management
# ═══════════════════════════════════════════════════════════════════════════════


def get_session() -> Session:
    """Get the current thread's database session."""
    get_engine()  # Ensure engine exists for the current DATA_DIR
    if not hasattr(_thread_local, "session") or _thread_local.session is None:
        _thread_local.session = _session_maker()
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
    get_engine()  # Ensure engine and session maker are initialized
    session = _session_maker()
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
    from .persistence import AccountModel, LoanModel, NotificationModel, NotificationPreferenceModel, TransactionModel, SavingsGoalModel, AdminModel, LoginAttemptModel, TokenVersionModel, AuditLogModel  # noqa: F401
    engine = get_engine()
    ModelBase.metadata.create_all(bind=engine)
