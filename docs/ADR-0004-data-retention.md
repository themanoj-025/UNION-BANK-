# ADR-0004: Data Retention & Idempotency

**Status:** Accepted  
**Date:** 2026-07-16  
**Deciders:** Engineering Team  
**References:**
- [ADR-0001: Consolidate Service Layer](./ADR-0001-consolidate-service-layer.md)
- [THREAT_MODEL.md](./THREAT_MODEL.md)

---

## Context

Two independent engineering audits of the Union Bank codebase identified a
**regulatory compliance bug** in the account-deletion flow, and a
**correctness gap** in money-movement operations:

1. **Hard-delete with cascade** — `AdminService.delete_account()` removed
   the `Account` row from SQLite, and the `ON DELETE CASCADE` foreign key
   on `TransactionModel` silently destroyed all associated transaction
   history. In a banking domain, this is a **record-retention violation**.
   Transaction records are audit-mandatory and must survive account closure.

2. **No idempotency on money movement** — `deposit()`, `withdraw()`, and
   `transfer()` had no mechanism to detect retries. If a client sends the
   same request twice (network retry, browser refresh, payment-provider
   callback), the money would move twice — a **double-spend vulnerability**.

---

## Decision

### 1. Soft-delete for accounts

Replace `DELETE FROM accounts WHERE account_number = ?` with:

- Set `deleted_at = now()`, `is_active = False` on the account row.
- No cascade — FK constraints no longer declare `ON DELETE CASCADE`.
- All default queries filter `WHERE deleted_at IS NULL`.
- Admin can recover via `undelete()`; audit/recovery via `get_deleted()`.

This means transaction history, loan records, savings goals, notifications,
and notification preferences **all survive account deletion** with their
original account_number foreign keys intact.

### 2. Idempotency keys for deposit/withdraw/transfer

Add an optional `idempotency_key` (string) field to `TransactionRequest`
and `TransferRequest` API models, and to the three service methods:

1. `deposit(acc_no, amount, category, idempotency_key?)`
2. `withdraw(acc_no, amount, category, idempotency_key?)`
3. `transfer(sender, receiver, amount, category, idempotency_key?)`

**Protocol:**  
- Client generates a globally unique key (e.g. UUIDv4) per operation.
- Server checks `IdempotencyRepository.get(key)` before executing.
- If a cached record exists → return it. Never re-execute.
- After executing → store the serialized result under that key.
- Key is the primary key in the `idempotency_keys` table (unique constraint).

**Boundary:** The check-then-execute window is not covered by a single
SQLite transaction (the check is read-only, the execute is read-write). For
a synchronous Python application with SQLite WAL mode, the probability of
two identical-key requests overlapping in that window is near zero. If this
project ever moves to async + Postgres, the idempotency check should be
moved inside the write transaction with `INSERT ... ON CONFLICT DO NOTHING`.

---

## Consequences

### Positive

- **Compliance:** Transaction history is now append-only and survives
  account deletion. This matches regulatory norms for record retention.
- **Correctness:** Double-spend from retries is eliminated. The idempotency
  contract is standard: same key = same result; different key = new operation.
- **Backward compatible:** `idempotency_key` is optional (`None` by default).
  Existing API clients that don't send it behave exactly as before.
- **Recoverable:** Soft-deleted accounts are recoverable via admin tooling.

### Negative

- **Storage growth:** Soft-deleted account rows and their related records
  accumulate in the database. An admin cleanup job (hard-delete after N days
  with explicit export) is future work.
- **No key expiry:** Idempotency keys accumulate indefinitely. A TTL-based
  cleanup job should be added for production deployments (e.g. delete keys
  older than 24 hours).
- **Migration needed:** Existing databases have `ON DELETE CASCADE` on the
  `transactions` FK. Alembic migration must rewrite the table or drop/recreate
  the FK constraint. The application code handles this correctly once
  migrated.

---

## Known Limitations

1. **Idempotency is not atomic** — the check and execute are separate
   round-trips to the DB. See "Boundary" note above.
2. **No cross-operation dedup** — the same key used for `deposit` and then
   `withdraw` would return the deposit result for the withdraw call. Clients
   must ensure unique keys per operation.
3. **Soft-delete does NOT mean reversible** — deleted accounts are hidden
   and recoverable, but their balance may be stale. An undelete should be
   paired with an admin review.

---

## Alternatives Considered

| Alternative | Rejected Because |
|---|---|
| Hard-delete + archive table | More complex; soft-delete achieves the same goal with simpler code |
| CASCADE to archive table | SQLite doesn't support this natively; application-level logic would be fragile |
| Transaction-level idempotency with DB constraints | Requires Postgres `pg_advisory_xact_lock` or similar; over-engineering for current scale |
| Client-side dedup only | Server must be the authority on correctness; client-side dedup is insufficient |

---

## Migration Plan

1. Create Alembic migration to remove `ondelete="CASCADE"` from existing FK.
2. Add `deleted_at` column to `accounts` table (nullable, default NULL).
3. Create `idempotency_keys` table.
4. Existing data is unaffected — no data backfill needed.
5. Application code handles both old and new schema (soft-delete only reads
   `deleted_at` if the column exists; the FKs are advisory at the app level).
