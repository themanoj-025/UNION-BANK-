"""Alembic environment configuration for Union Bank.

Supports both SQLite (development/testing) and PostgreSQL (production).
The database type is selected by the DATABASE_URL environment variable.
"""

import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Compute project root for data directory fallback
_PROJECT_DIR = Path(__file__).resolve().parent.parent

# Alembic Config
config = context.config

# Set up Python logging from the ini file FIRST
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models AFTER logging is configured
from unionbank.infrastructure.database import ModelBase as Base, get_db_url, is_sqlite  # noqa: E402
target_metadata = Base.metadata

# Determine the database URL from settings (respects DATABASE_URL env var)
db_url = get_db_url()
if is_sqlite(db_url):
    # For SQLite, ensure the data directory exists
    data_dir = os.environ.get("UNION_BANK_DATA_DIR", str(_PROJECT_DIR / "data"))
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    db_path = Path(data_dir) / "union_bank.db"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
else:
    # For PostgreSQL, use the DATABASE_URL directly
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
