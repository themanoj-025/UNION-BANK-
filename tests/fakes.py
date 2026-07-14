"""
tests/fakes.py  –  In-memory repository fakes for unit testing.

Each fake implements the corresponding Protocol from application/interfaces.py
using plain dicts/lists instead of SQLite. This makes unit tests:
- Blazingly fast (no I/O, no DB setup)
- Deterministic (no shared state between tests when fresh instance created)
- Easy to debug (inspectable in-memory state)
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from application.interfaces import KeysetPage

from domain.entities import (
    Account, AdminUser, LoginAttempt, Notification,
    NotificationPreference, SavingsGoal,
    TokenVersion, Transaction, TransactionType,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Account Repository
# ═══════════════════════════════════════════════════════════════════════════════


class FakeAccountRepository:
    """In-memory account repository — stores accounts in a dict keyed by account_number."""

    def __init__(self):
        self._accounts: dict[str, Account] = {}

    def get(self, acc_no: str) -> Optional[Account]:
        return self._accounts.get(acc_no)

    def get_all(self) -> list[Account]:
        return list(self._accounts.values())

    def exists(self, acc_no: str) -> bool:
        return acc_no in self._accounts

    def create(self, account: Account) -> Account:
        self._accounts[account.account_number] = account
        return account

    def update(self, account: Account) -> Account:
        self._accounts[account.account_number] = account
        return account

    def update_balance(self, acc_no: str, new_balance: Decimal) -> bool:
        if acc_no not in self._accounts:
            return False
        self._accounts[acc_no].balance = new_balance
        return True

    def set_active(self, acc_no: str, active: bool) -> bool:
        if acc_no not in self._accounts:
            return False
        self._accounts[acc_no].is_active = active
        return True

    def set_frozen(self, acc_no: str, frozen: bool) -> bool:
        if acc_no not in self._accounts:
            return False
        self._accounts[acc_no].is_frozen = frozen
        if frozen:
            self._accounts[acc_no].is_active = False
        else:
            self._accounts[acc_no].is_active = True
        return True

    def delete(self, acc_no: str) -> bool:
        if acc_no not in self._accounts:
            return False
        del self._accounts[acc_no]
        return True

    def search(self, query: str) -> list[Account]:
        q = query.lower()
        return [
            a for a in self._accounts.values()
            if q in a.account_number.lower() or q in a.name.lower()
        ]

    def count(self) -> int:
        return len(self._accounts)

    def total_balance(self) -> Decimal:
        return sum(
            (a.balance for a in self._accounts.values()),
            Decimal("0.00"),
        )

    def active_count(self) -> int:
        return sum(
            1 for a in self._accounts.values()
            if a.is_active and not a.is_frozen
        )

    def frozen_count(self) -> int:
        return sum(1 for a in self._accounts.values() if a.is_frozen)

    def closed_count(self) -> int:
        return sum(
            1 for a in self._accounts.values()
            if not a.is_active and not a.is_frozen
        )

    def get_by_email(self, email: str) -> Optional[Account]:
        for a in self._accounts.values():
            if a.email == email:
                return a
        return None

    def commit(self) -> None:
        pass  # No-op for in-memory

    def rollback(self) -> None:
        pass  # No-op for in-memory


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Transaction Repository
# ═══════════════════════════════════════════════════════════════════════════════


class FakeTransactionRepository:
    """In-memory transaction repository — stores transactions in a list."""

    def __init__(self):
        self._transactions: list[Transaction] = []

    def get_by_account(self, acc_no: str) -> list[Transaction]:
        return sorted(
            [t for t in self._transactions if t.account_number == acc_no],
            key=lambda t: t.timestamp or _utcnow(),
            reverse=True,
        )

    def get_mini(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        txns = self.get_by_account(acc_no)
        return txns[:limit]

    def create(self, transaction: Transaction) -> Transaction:
        self._transactions.append(transaction)
        return transaction

    def get_all(self) -> list[Transaction]:
        return list(self._transactions)

    def total_by_type(self, txn_type: str) -> Decimal:
        return sum(
            (t.amount for t in self._transactions if t.type.value == txn_type),
            Decimal("0.00"),
        )

    def count(self) -> int:
        return len(self._transactions)

    def count_by_account(self, acc_no: str) -> int:
        return sum(1 for t in self._transactions if t.account_number == acc_no)

    def get_category_totals(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for t in self._transactions:
            cat = t.category or "General"
            totals[cat] = totals.get(cat, Decimal("0.00")) + t.amount
        return totals

    def get_paginated(
        self,
        acc_no: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> tuple[list[Transaction], int]:
        filtered = self._filter_txns(acc_no, from_date, to_date, txn_type)
        filtered.sort(key=lambda t: t.timestamp or _utcnow(), reverse=True)
        total = len(filtered)
        start = (page - 1) * per_page
        return filtered[start:start + per_page], total

    def get_paginated_keyset(
        self,
        acc_no: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[datetime] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> KeysetPage[Transaction]:
        filtered = self._filter_txns(acc_no, from_date, to_date, txn_type)
        filtered.sort(key=lambda t: t.timestamp or _utcnow(), reverse=True)

        if cursor is not None:
            filtered = [t for t in filtered if t.timestamp and t.timestamp < cursor]

        has_more = len(filtered) > limit
        items = filtered[:limit]
        next_cursor = items[-1].timestamp if items else None

        return KeysetPage(
            items=items,
            cursor=next_cursor,
            has_more=has_more,
            cursor_key="timestamp",
        )

    def _filter_txns(
        self,
        acc_no: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        txn_type: Optional[str] = None,
    ) -> list[Transaction]:
        """Filter transactions by optional criteria."""
        filtered = list(self._transactions)
        if acc_no:
            filtered = [t for t in filtered if t.account_number == acc_no]
        if from_date:
            filtered = [t for t in filtered if (t.timestamp or _utcnow()) >= from_date]
        if to_date:
            filtered = [t for t in filtered if (t.timestamp or _utcnow()) <= to_date]
        if txn_type:
            filtered = [t for t in filtered if t.type.value == txn_type]
        return filtered

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Admin Repository
# ═══════════════════════════════════════════════════════════════════════════════


class FakeAdminRepository:
    """In-memory admin repository."""

    def __init__(self):
        self._admins: dict[str, AdminUser] = {}

    def get_by_username(self, username: str) -> Optional[AdminUser]:
        return self._admins.get(username)

    def create(self, admin: AdminUser) -> AdminUser:
        self._admins[admin.username] = admin
        return admin

    def update_password(self, username: str, new_hashed: str) -> bool:
        if username not in self._admins:
            return False
        self._admins[username].password = new_hashed
        return True

    def admin_count(self) -> int:
        return len(self._admins)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Savings Goal Repository
# ═══════════════════════════════════════════════════════════════════════════════


class FakeSavingsGoalRepository:
    """In-memory savings goal repository."""

    def __init__(self):
        self._goals: dict[str, SavingsGoal] = {}

    def get_by_account(self, acc_no: str) -> list[SavingsGoal]:
        return [g for g in self._goals.values() if g.account_number == acc_no]

    def get(self, goal_id: str) -> Optional[SavingsGoal]:
        return self._goals.get(goal_id)

    def create(self, goal: SavingsGoal) -> SavingsGoal:
        self._goals[goal.goal_id] = goal
        return goal

    def update(self, goal: SavingsGoal) -> SavingsGoal:
        self._goals[goal.goal_id] = goal
        return goal

    def contribute(self, goal_id: str, amount: Decimal) -> Optional[SavingsGoal]:
        goal = self._goals.get(goal_id)
        if goal is None:
            return None
        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
        return goal

    def delete(self, goal_id: str) -> Optional[SavingsGoal]:
        return self._goals.pop(goal_id, None)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Login Attempt Repository
# ═══════════════════════════════════════════════════════════════════════════════


class FakeLoginAttemptRepository:
    """In-memory login attempt repository for rate limiting tests."""

    def __init__(self):
        self._records: dict[str, LoginAttempt] = {}

    def get(self, key: str) -> Optional[LoginAttempt]:
        return self._records.get(key)

    def record_failure(
        self, key: str, max_attempts: int = 5, lockout_minutes: int = 15
    ) -> int:
        now = _utcnow()
        record = self._records.get(key)

        if record is None:
            record = LoginAttempt(key=key, count=1, first_failed=now)
            self._records[key] = record
        else:
            if record.lockout_until and now >= record.lockout_until:
                record.count = 1
                record.first_failed = now
                record.lockout_until = None
            else:
                record.count += 1

            if record.count >= max_attempts:
                record.lockout_until = now + timedelta(minutes=lockout_minutes)

        return max(0, max_attempts - record.count)

    def is_locked(self, key: str, max_attempts: int = 5) -> tuple[bool, int]:
        record = self._records.get(key)
        if record is None or record.count < max_attempts:
            return False, 0
        if record.lockout_until and _utcnow() < record.lockout_until:
            remaining = int((record.lockout_until - _utcnow()).total_seconds() // 60)
            return True, max(1, remaining)
        if record and record.lockout_until and _utcnow() >= record.lockout_until:
            del self._records[key]
        return False, 0

    def reset(self, key: str) -> None:
        self._records.pop(key, None)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Token Version Repository
# ═══════════════════════════════════════════════════════════════════════════════


class FakeTokenVersionRepository:
    """In-memory token version repository."""

    def __init__(self):
        self._versions: dict[str, int] = {}

    def get_version(self, account_number: str) -> int:
        return self._versions.get(account_number, 0)

    def increment(self, account_number: str) -> int:
        version = self._versions.get(account_number, 0) + 1
        self._versions[account_number] = version
        return version

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Audit Log Repository
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Notification Repository
# ═══════════════════════════════════════════════════════════════════════════════


class FakeNotificationRepository:
    """In-memory notification repository."""

    def __init__(self):
        self._notifications: list[Notification] = []

    def get(self, notif_id: str) -> Optional[Notification]:
        for n in self._notifications:
            if n.notif_id == notif_id:
                return n
        return None

    def get_by_account(self, acc_no: str, limit: int = 50) -> list[Notification]:
        results = [n for n in self._notifications if n.account_number == acc_no]
        results.sort(key=lambda n: n.created_at, reverse=True)
        return results[:limit]

    def get_unread_count(self, acc_no: str) -> int:
        return sum(1 for n in self._notifications
                   if n.account_number == acc_no and not n.is_read)

    def get_unread(self, acc_no: str, limit: int = 20) -> list[Notification]:
        results = [n for n in self._notifications
                   if n.account_number == acc_no and not n.is_read]
        results.sort(key=lambda n: n.created_at, reverse=True)
        return results[:limit]

    def create(self, notification: Notification) -> Notification:
        self._notifications.append(notification)
        return notification

    def mark_as_read(self, notif_id: str) -> bool:
        for n in self._notifications:
            if n.notif_id == notif_id:
                n.is_read = True
                return True
        return False

    def mark_all_as_read(self, acc_no: str) -> int:
        count = 0
        for n in self._notifications:
            if n.account_number == acc_no and not n.is_read:
                n.is_read = True
                count += 1
        return count

    def delete_old(self, days: int = 30) -> int:
        from datetime import timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        old = [n for n in self._notifications if n.created_at < cutoff]
        for n in old:
            self._notifications.remove(n)
        return len(old)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Notification Preference Repository
# ═══════════════════════════════════════════════════════════════════════════════


class FakeNotificationPreferenceRepository:
    """In-memory notification preference repository."""

    def __init__(self):
        self._prefs: dict[str, NotificationPreference] = {}

    def get(self, acc_no: str) -> Optional[NotificationPreference]:
        return self._prefs.get(acc_no)

    def create_or_update(self, pref: NotificationPreference) -> NotificationPreference:
        self._prefs[pref.account_number] = pref
        return pref

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Fake Audit Log Repository
# ═══════════════════════════════════════════════════════════════════════════════


class FakeAuditLogRepository:
    """In-memory audit log repository — append-only."""

    def __init__(self):
        self._entries: list[dict] = []

    def log(self, actor: str, action: str, target: Optional[str] = None,
            details: Optional[str] = None, ip_address: Optional[str] = None,
            reason: Optional[str] = None) -> None:
        self._entries.append({
            "actor": actor,
            "action": action,
            "target": target,
            "details": details,
            "ip_address": ip_address,
            "reason": reason,
            "timestamp": str(_utcnow())[:19],
        })

    def get_recent(self, limit: int = 50) -> list:
        return list(reversed(self._entries))[:limit]

    def get_by_actor(self, actor: str, limit: int = 50) -> list:
        entries = [e for e in self._entries if e["actor"] == actor]
        return list(reversed(entries))[:limit]

    def get_by_action(self, action: str, limit: int = 50) -> list:
        entries = [e for e in self._entries if e["action"] == action]
        return list(reversed(entries))[:limit]

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass
