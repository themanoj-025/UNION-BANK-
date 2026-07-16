"""infrastructure/database.py  –  SQLAlchemy engine, session management, and init.

Provides both synchronous (SQLite dev) and asynchronous (Postgres prod) database
access. The engine type is selected automatically based on the DATABASE_URL:

- ``sqlite:///...`` → synchronous SQLite
- ``postgresql://...`` → synchronous Postgres (via psycopg2)
- ``postgresql+asyncpg://...`` → async Postgres (via asyncpg)

Async support is added progressively — hot paths (transfer, deposit, withdraw)
are migrated first while colder paths remain synchronous.
"""

from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Generator, Optional

from unionbank.config import settings
from unionbank.domain.clock import utcnow as _utcnow  # noqa: F401
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ═══════════════════════════════════════════════════════════════════════════════
#  Model Base (re-exported for Alembic)
# ═══════════════════════════════════════════════════════════════════════════════

ModelBase = declarative_base()

# ═══════════════════════════════════════════════════════════════════════════════
#  Database URL resolution
# ═══════════════════════════════════════════════════════════════════════════════


def _get_db_path() -> str:
    """Get the SQLite database path from current settings / env override."""
    data_dir = Path(os.environ.get("UNION_BANK_DATA_DIR", str(settings.DATA_DIR)))
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "union_bank.db")


def get_db_url() -> str:
    """Resolve the database URL from settings, with SQLite fallback."""
    return settings.DATABASE_URL or f"sqlite:///{_get_db_path()}"


def is_sqlite(url: Optional[str] = None) -> bool:
    """Check if the given (or current) database URL is SQLite."""
    return (url or get_db_url()).startswith("sqlite")


def is_postgres(url: Optional[str] = None) -> bool:
    """Check if the given (or current) database URL is PostgreSQL."""
    return (url or get_db_url()).startswith("postgresql")


# ═══════════════════════════════════════════════════════════════════════════════
#  Synchronous engine (SQLite dev / psycopg2 Postgres)
# ═══════════════════════════════════════════════════════════════════════════════

_engine_instance = None
_session_maker = None
_thread_local = threading.local()


def get_engine():
    """Get or create the synchronous SQLAlchemy engine.

    Prefers DATABASE_URL (for PostgreSQL) when configured.
    Falls back to SQLite at the current DATA_DIR.
    The engine is lazily recreated when the database URL changes (e.g., during tests).
    """
    global _engine_instance, _session_maker

    db_url = get_db_url()

    # If engine exists for a different URL, dispose and recreate
    if _engine_instance is not None:
        current_url = str(_engine_instance.url)
        if current_url == db_url:
            return _engine_instance
        # URL changed — dispose old engine
        _engine_instance.dispose()
        _engine_instance = None
        _session_maker = None

    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True,
    }

    if is_sqlite(db_url):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10

        _engine_instance = create_engine(db_url, **engine_kwargs)

        @event.listens_for(_engine_instance, "connect")
        def _set_pragmas(dbapi_connection, connection_record):
            """Enable WAL mode and foreign keys for better performance and integrity."""
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
    else:
        # PostgreSQL — explicit pool settings
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
        _engine_instance = create_engine(db_url, **engine_kwargs)

    _session_maker = sessionmaker(autocommit=False, autoflush=False, bind=_engine_instance)
    return _engine_instance


# ═══════════════════════════════════════════════════════════════════════════════
#  Asynchronous engine (asyncpg Postgres)
# ═══════════════════════════════════════════════════════════════════════════════

_async_engine_instance = None
_async_session_maker = None


def get_async_engine():
    """Get or create the async SQLAlchemy engine (for asyncpg Postgres).

    Falls back to the synchronous engine if the URL is SQLite (which doesn't
    support async). Returns None if the current URL is SQLite.
    """
    global _async_engine_instance, _async_session_maker

    db_url = get_db_url()

    # SQLite doesn't support async, return None
    if is_sqlite(db_url):
        return None

    # Convert postgresql:// → postgresql+asyncpg:// for async driver
    async_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # If engine exists for a different URL, dispose and recreate
    if _async_engine_instance is not None:
        current_url = str(_async_engine_instance.url)
        if current_url == async_url:
            return _async_engine_instance
        _async_engine_instance.dispose()
        _async_engine_instance = None
        _async_session_maker = None

    _async_engine_instance = create_async_engine(
        async_url,
        echo=False,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
    )
    _async_session_maker = async_sessionmaker(
        _async_engine_instance,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return _async_engine_instance


# ═══════════════════════════════════════════════════════════════════════════════
#  Synchronous session management
# ═══════════════════════════════════════════════════════════════════════════════


def reset_engine():
    """Dispose the current engine and clear all sessions — for testing."""
    global _engine_instance, _session_maker
    global _async_engine_instance, _async_session_maker
    close_session()
    if _engine_instance is not None:
        try:
            _engine_instance.dispose()
        except Exception:
            from unionbank.utils.logger import logger
            logger.warning("Failed to dispose database engine", exc_info=True)
        _engine_instance = None
        _session_maker = None
    if _async_engine_instance is not None:
        try:
            _async_engine_instance.dispose()
        except Exception:
            from unionbank.utils.logger import logger
            logger.warning("Failed to dispose async database engine", exc_info=True)
        _async_engine_instance = None
        _async_session_maker = None


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
            from unionbank.utils.logger import logger
            logger.warning("Failed to close database session", exc_info=True)
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
#  Asynchronous session management
# ═══════════════════════════════════════════════════════════════════════════════


async def get_async_session() -> AsyncSession:
    """Get an async database session (for asyncpg Postgres connections).

    Raises RuntimeError if the current database URL is SQLite (which doesn't
    support async access).
    """
    engine = get_async_engine()
    if engine is None or _async_session_maker is None:
        raise RuntimeError(
            "Async sessions are not available with SQLite. "
            "Set DATABASE_URL to a PostgreSQL connection string to use async."
        )
    return _async_session_maker()


@asynccontextmanager
async def async_atomic_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async transactional scope — commits on success, rolls back on exception."""
    engine = get_async_engine()
    if engine is None or _async_session_maker is None:
        raise RuntimeError(
            "Async atomic sessions are not available with SQLite. "
            "Set DATABASE_URL to a PostgreSQL connection string."
        )
    session = _async_session_maker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  DB Initialization
# ═══════════════════════════════════════════════════════════════════════════════


def init_db():
    """Create all tables if they don't exist.

    Uses absolute imports to avoid relative-import issues when called
    from contexts where __package__ is not set (e.g., E2E test imports).
    """
    from unionbank.infrastructure.persistence import (  # noqa: F401
        AccountModel,
        AdminModel,
        AuditLogModel,
        LoanModel,
        LoginAttemptModel,
        NotificationModel,
        NotificationPreferenceModel,
        RefreshTokenModel,
        SavingsGoalModel,
        TokenVersionModel,
        TransactionModel,
    )
    engine = get_engine()
    ModelBase.metadata.create_all(bind=engine)
