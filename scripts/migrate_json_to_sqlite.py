"""
migrate_json_to_sqlite.py  –  Migrate JSON data → SQLite tables.

Reads all existing JSON files and writes their contents into the SQLite
database via the repository layer. Safe to run multiple times (idempotent).

Usage:
    python scripts/migrate_json_to_sqlite.py
"""

import os
import sys
import time
from decimal import Decimal
from datetime import datetime, timezone

# Set testing env vars so Config doesn't require real secrets
os.environ.setdefault("UNION_BANK_TESTING", "1")
os.environ.setdefault("JWT_SECRET", "migration-secret")
os.environ.setdefault("FLASK_SECRET_KEY", "migration-flask-secret")

# Ensure project root is importable
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from utils import (
    load_json,
    ACCOUNTS_FILE, TRANSACTIONS_FILE, ADMIN_FILE,
    LOGIN_ATTEMPTS_FILE, SAVINGS_GOALS_FILE,
)
from logger import logger
from database import get_session, close_session
from infrastructure.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyTransactionRepository,
    SqlAlchemyAdminRepository,
    SqlAlchemySavingsGoalRepository,
    SqlAlchemyLoginAttemptRepository,
)
from infrastructure.persistence import (
    AccountModel, TransactionModel, SavingsGoalModel,
    AdminModel, LoginAttemptModel,
)


def _parse_ts(ts_str: str) -> datetime:
    """Parse a timestamp string into a timezone-aware datetime."""
    try:
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def migrate_accounts() -> int:
    """Migrate accounts from JSON to SQLite. Returns count migrated."""
    raw = load_json(ACCOUNTS_FILE)
    if not raw:
        print("  No accounts to migrate.")
        return 0

    session = get_session()
    try:
        repo = SqlAlchemyAccountRepository(session)
        migrated = 0

        for acc_no, data in raw.items():
            existing = repo.get(acc_no)
            if existing:
                # Update existing
                existing.name = data.get("name", existing.name)
                existing.age = data.get("age", existing.age)
                existing.gender = data.get("gender", existing.gender)
                existing.mobile = data.get("mobile", existing.mobile)
                existing.email = data.get("email", existing.email)
                existing.password = data.get("password", existing.password)
                existing.balance = Decimal(str(data.get("balance", existing.balance)))
                existing.is_active = data.get("is_active", existing.is_active)
                existing.is_frozen = data.get("is_frozen", existing.is_frozen)
            else:
                account = repo.create(data)
                session.add(account)
                migrated += 1

        session.commit()
        total = len(raw)
        print(f"  [+] Accounts: {migrated} new, {total - migrated} updated (total {total})")
        return total
    finally:
        close_session()


def migrate_transactions() -> int:
    """Migrate transactions from JSON to SQLite. Returns count migrated."""
    raw = load_json(TRANSACTIONS_FILE)
    if not raw:
        print("  No transactions to migrate.")
        return 0

    session = get_session()
    try:
        total = 0

        for acc_no, records in raw.items():
            for t in records:
                txn_id = t.get("txn_id", "")
                if not txn_id:
                    continue

                # Check for duplicates
                existing = session.query(TransactionModel).filter_by(txn_id=txn_id).first()
                if existing:
                    continue

                # Ensure the account exists in the DB (create stub if needed)
                account = session.query(AccountModel).filter_by(account_number=acc_no).first()
                if account is None:
                    logger.warning(f"Account {acc_no} not found in DB - creating stub for transaction {txn_id}")
                    account = AccountModel(
                        account_number=acc_no,
                        name=acc_no,  # placeholder name
                        password="",  # placeholder - account is inactive
                        balance=Decimal("0.00"),
                        is_active=False,
                        is_frozen=False,
                    )
                    session.add(account)
                    session.flush()  # Ensure FK is satisfied before inserting txn

                txn = TransactionModel(
                    txn_id=txn_id,
                    account_number=acc_no,
                    type=t.get("type", ""),
                    amount=Decimal(str(t.get("amount", 0))),
                    balance=Decimal(str(t.get("balance", 0))),
                    description=t.get("description", ""),
                    category=t.get("category", "General"),
                    target_account=t.get("target_account"),
                    timestamp=_parse_ts(t.get("timestamp", "")),
                )
                session.add(txn)
                total += 1

        session.commit()
        print(f"  [+] Transactions: {total} migrated")
        return total
    finally:
        close_session()


def migrate_admin() -> int:
    """Migrate admin credentials from JSON to SQLite. Returns count migrated."""
    raw = load_json(ADMIN_FILE)
    if not raw:
        print("  No admin data to migrate.")
        return 0

    session = get_session()
    try:
        repo = SqlAlchemyAdminRepository(session)
        username = raw.get("username", "simon")

        existing = repo.get_by_username(username)
        if existing:
            print(f"  [i] Admin '{username}' already exists in DB - skipped")
            return 0

        # Create via model directly (repository create_default uses hash)
        admin = AdminModel(
            username=username,
            password=raw.get("password", ""),
            role="admin",
        )
        session.add(admin)
        session.commit()
        print(f"  [+] Admin '{username}' migrated")
        return 1
    finally:
        close_session()


def migrate_login_attempts() -> int:
    """Migrate login attempt data from JSON to SQLite. Returns count migrated."""
    raw = load_json(LOGIN_ATTEMPTS_FILE)
    if not raw:
        print("  No login attempt data to migrate.")
        return 0

    session = get_session()
    try:
        total = 0
        from datetime import timedelta

        for key, record in raw.items():
            existing = session.query(LoginAttemptModel).filter_by(key=key).first()
            if existing:
                continue

            count = record.get("count", 0)
            first_failed = None
            lockout_until = None

            if record.get("first_failed"):
                first_failed = _parse_ts(record["first_failed"])
            if record.get("lockout_until"):
                lockout_until = _parse_ts(record["lockout_until"])

            attempt = LoginAttemptModel(
                key=key,
                count=count,
                first_failed=first_failed,
                lockout_until=lockout_until,
            )
            session.add(attempt)
            total += 1

        session.commit()
        print(f"  [+] Login attempts: {total} migrated")
        return total
    finally:
        close_session()


def migrate_savings_goals() -> int:
    """Migrate savings goals from JSON to SQLite. Returns count migrated."""
    raw = load_json(SAVINGS_GOALS_FILE)
    if not raw:
        print("  No savings goals to migrate.")
        return 0

    session = get_session()
    try:
        total = 0

        for acc_no, goals in raw.items():
            for g in goals:
                goal_id = g.get("goal_id", "")
                if not goal_id:
                    continue

                existing = session.query(SavingsGoalModel).filter_by(goal_id=goal_id).first()
                if existing:
                    continue

                goal = SavingsGoalModel(
                    goal_id=goal_id,
                    account_number=acc_no,
                    name=g.get("name", ""),
                    target_amount=Decimal(str(g.get("target_amount", 0))),
                    current_amount=Decimal(str(g.get("current_amount", 0))),
                    target_date=g.get("target_date"),
                    is_completed=g.get("is_completed", False),
                )
                session.add(goal)
                total += 1

        session.commit()
        print(f"  [+] Savings goals: {total} migrated")
        return total
    finally:
        close_session()


def main():
    """Run all migrations."""
    print()
    print("  " + "=" * 42)
    print("     JSON to SQLite Data Migration")
    print("  " + "=" * 42)
    print()

    start = time.time()

    a = migrate_accounts()
    t = migrate_transactions()
    ad = migrate_admin()
    la = migrate_login_attempts()
    sg = migrate_savings_goals()

    elapsed = time.time() - start
    total = a + t + ad + la + sg

    print()
    print(f"  {'-' * 42}")
    print(f"  Migration complete!")
    print(f"  {'-' * 42}")
    print(f"    Accounts        : {a:>8}")
    print(f"    Transactions    : {t:>8}")
    print(f"    Admin           : {ad:>8}")
    print(f"    Login attempts  : {la:>8}")
    print(f"    Savings goals   : {sg:>8}")
    print(f"    {'-' * 30}")
    print(f"    Total records   : {total:>8}")
    print(f"    Time            : {elapsed:>8.2f}s")
    print(f"  {'-' * 42}")
    print()

    if total == 0:
        print("  Nothing to migrate - DB is already up to date.\n")
    else:
        print("  Migration successful! JSON data is now in SQLite.\n")


if __name__ == "__main__":
    main()
