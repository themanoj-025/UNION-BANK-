"""add_balance_check_constraint

Revision ID: bc2a4f8e9d1b
Revises: 808505b8d0f3
Create Date: 2026-07-16 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc2a4f8e9d1b'
down_revision: Union[str, Sequence[str], None] = '808505b8d0f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add CHECK (balance >= 0) constraint to accounts table.

    This is a defense-in-depth measure — the application layer already
    prevents negative balances in withdraw() and transfer(), but the
    DB-level constraint ensures no bug or race condition can corrupt
    balance data.
    """
    op.create_check_constraint(
        "ck_accounts_balance_non_negative",
        "accounts",
        "balance >= 0",
    )


def downgrade() -> None:
    """Remove the CHECK constraint.

    Note: SQLite does not support ALTER TABLE DROP CONSTRAINT directly.
    The only way to remove a CHECK constraint in SQLite is to recreate
    the table. Alembio's batch mode handles this automatically when
    batch_alter_table() is used.
    """
    # SQLite doesn't support DROP CONSTRAINT — use batch mode
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_constraint(
            "ck_accounts_balance_non_negative",
            type_="check",
        )
