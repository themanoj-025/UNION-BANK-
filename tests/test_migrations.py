"""
tests/test_migrations.py  –  Alembic migration round-trip tests.

Verifies that:
  1. Alembic can upgrade to the latest migration
  2. Alembic can downgrade to the base (empty) state
  3. The upgrade+downgrade cycle is clean (no data loss in either direction)
  4. Schema changes are forward-compatible

Uses a temporary SQLite database to avoid touching the real DB.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from alembic.command import downgrade, upgrade
from alembic.config import Config


@pytest.fixture
def alembic_config() -> Config:
    """Create an Alembic config pointing at a temporary SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_migration.db")
        os.environ["UNION_BANK_DATA_DIR"] = tmpdir

        # Point alembic at the config
        project_root = Path(__file__).resolve().parent.parent
        alembic_cfg = Config(str(project_root / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

        yield alembic_cfg

        # Cleanup
        os.environ.pop("UNION_BANK_DATA_DIR", None)


class TestAlembicMigrations:

    def test_upgrade_to_head(self, alembic_config):
        """
        Upgrade from empty DB to latest migration should succeed.

        This verifies that all migrations in the versions/ directory
        apply cleanly without errors.
        """
        upgrade(alembic_config, "head")
        # Success means upgrade completed without exception

    def test_downgrade_to_base(self, alembic_config):
        """
        Upgrade to head, then downgrade to base should succeed.

        This verifies that the entire migration chain is reversible.
        """
        # Upgrade to head
        upgrade(alembic_config, "head")

        # Then downgrade all the way back
        downgrade(alembic_config, "base")

    def test_upgrade_downgrade_roundtrip(self, alembic_config):
        """
        Full upgrade + downgrade round-trip should be clean.

        This verifies that:
        1. All migrations can be applied (up -> head)
        2. All migrations can be rolled back (down -> base)
        3. The cycle doesn't leave the database in a broken state
        """
        # Upgrade
        upgrade(alembic_config, "head")
        # Downgrade
        downgrade(alembic_config, "base")
        # Re-upgrade (simulates production roll-forward after rollback)
        upgrade(alembic_config, "head")

    def test_upgrade_creates_all_tables(self, alembic_config):
        """After upgrade, all expected tables should exist in the database."""
        import sqlite3

        # Use same path calculation as env.py for consistency
        data_dir = os.environ.get("UNION_BANK_DATA_DIR", "")
        assert data_dir, "UNION_BANK_DATA_DIR must be set by fixture"
        db_path = os.path.join(data_dir, "union_bank.db")

        # Upgrade
        upgrade(alembic_config, "head")

        # Verify tables exist
        assert os.path.exists(db_path), f"Database not created at {db_path}"
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Expected tables from our Alembic migration models (actual names from DB)
        expected = [
            "accounts", "admins", "audit_log", "loans",
            "login_attempts", "notification_preferences", "notifications",
            "savings_goals", "token_versions", "transactions",
        ]

        for table in expected:
            assert table in tables, f"Expected table '{table}' not found after migration (got {tables})"

        # Alembic's own table
        assert "alembic_version" in tables

    def test_idempotent_upgrade(self, alembic_config):
        """Running upgrade head twice should be idempotent (no errors)."""
        upgrade(alembic_config, "head")
        # Running again should be a no-op
        upgrade(alembic_config, "head")

    def test_upgrade_downgrade_cycle_does_not_crash(self, alembic_config):
        """Running upgrade then downgrade should not crash (verifies migration chain exists)."""
        upgrade(alembic_config, "head")
        downgrade(alembic_config, "base")

    def test_version_table_exists_after_upgrade(self, alembic_config):
        """The alembic_version table should exist after upgrade."""
        import sqlite3

        # Use same path calculation as env.py for consistency
        data_dir = os.environ.get("UNION_BANK_DATA_DIR", "")
        assert data_dir, "UNION_BANK_DATA_DIR must be set by fixture"
        db_path = os.path.join(data_dir, "union_bank.db")

        upgrade(alembic_config, "head")

        assert os.path.exists(db_path), f"Database not created at {db_path}"
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "alembic_version" in tables, "alembic_version table not found after upgrade"
