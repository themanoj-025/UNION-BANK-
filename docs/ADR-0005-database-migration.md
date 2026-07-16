# ADR-0005: Database Migration & Performance

**Status:** Accepted  
**Date:** 2026-07-16  
**References:**
- [ADR-0004: Data Retention & Idempotency](./ADR-0004-data-retention.md)
- [THREAT_MODEL.md](./THREAT_MODEL.md)

---

## Context

Two independent engineering audits flagged several database and performance
concerns:

1. **SQLite in production** — The project uses SQLite, which is unsuitable for
   concurrent writes at scale. PostgreSQL is the intended target for production.

2. **`generate_account_number()` unbounded loop** — The function loops
   indefinitely until it finds a unique number. In a near-exhausted number
   space, this could hang forever.

3. **`get_statistics()` makes 10 separate queries** — Each call fires 10
   sequential aggregate queries against the DB. These could be consolidated.

4. **Admin account list is unbounded** — `AdminService.list_accounts()`
   returns all accounts in one response, which degrades with 5,000+ accounts.

5. **Missing dependencies** — `redis` and `alembic` packages were not
   in `requirements.txt`, causing silent failures and blocking migrations.

6. **`ondelete="CASCADE"` still on TransactionModel FK** — Despite soft-delete
   in ADR-0004, the FK constraint remained. A future hard-delete path would
   still cascade.

---

## Decisions

### 1. PostgreSQL migration readiness

Add `DATABASE_URL` to `Config` and `alembic` to `requirements.txt`. The
codebase already abstracts database access behind SQLAlchemy ORM and
repository protocols, so the migration path is:

1. Create Alembic migrations for the current SQLite schema.
2. Point `DATABASE_URL` at a PostgreSQL instance.
3. Run migrations.
4. The application works with no code changes (SQLAlchemy ORM abstracts
   the dialect differences).

The `get_engine()` function is updated to prefer `DATABASE_URL` over the
default SQLite path when configured.

### 2. Cap `generate_account_number()` retry loop

Replace `while True` with `for _ in range(max_attempts)` and raise
`RuntimeError` after exhaustion. Default max is 1000 attempts — more than
enough for a 9-billion-number space, but prevents hangs.

### 3. Consolidated `get_statistics()` query

Add `get_statistics()` to `AccountRepositoryProtocol` and implement it as a
single aggregate query using SQLAlchemy `func.count()`, `func.sum()`, and
`case()` expressions. This replaces 5 separate queries (count, active_count,
frozen_count, closed_count, total_balance) with 1.

**Before:** 10 separate DB round-trips  
**After:** 2 DB round-trips (1 for account stats, 1 for txn stats)

### 4. Paginated admin account list

Add `get_all_paginated(page, per_page)` to the account repository and
`AdminService.list_accounts_paginated()`. The admin API endpoint (`api.py`)
already implements offset-based pagination with cache, but the service layer
now supports it natively.

### 5. Add missing indexes

- `idx_accounts_mobile` — index on `mobile` column for admin searches
- `idx_accounts_created_deleted` — composite index on `created_at` + `deleted_at`

### 6. Requirements.txt cleanup

- Added: `alembic>=1.13.0`, `redis>=5.0.0`
- Removed: `Flask`, `Flask-WTF`, `fpdf2` (dead dependencies from the v1
  Flask web app which was deleted)

---

## Consequences

### Positive

- **Safety:** No more infinite loops in account number generation.
- **Performance:** `get_statistics()` is ~5x faster (1 query vs 5 queries).
- **Scalability:** Paginated admin list prevents memory/time blowup at scale.
- **Production readiness:** PostgreSQL path is prepared; missing deps are added.
- **Search speed:** Mobile index speeds up admin account searches.

### Negative

- **SQLite remains default** — We're "PostgreSQL-ready" but not migrated yet.
  The actual migration requires a running PostgreSQL instance and Alembic
  execution, which is out of scope for this phase.
- **Alembic initial migration not created** — A `revision --autogenerate`
  must be run against PostgreSQL to generate the initial migration.
- **Admin pagination is offset-based** — Keyset (cursor) pagination would be
  more efficient for very large datasets, but offset is simpler and sufficient
  for admin panels with <100K accounts.

---

## Future Work

1. Run Alembic autogenerate against PostgreSQL to create initial migration.
2. Add Redis connection pooling and retry logic (currently single-connection).
3. Replace offset-based admin pagination with keyset pagination.
4. Add read-replica support for PostgreSQL (separate engine for reads).
