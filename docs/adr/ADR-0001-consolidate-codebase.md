# ADR-0001: Consolidate Codebase to Single Canonical Tree

**Status:** Implemented  
**Date:** July 15, 2026  
**Author:** Automated audit + manual import tracing  

## Context

The Union Bank codebase had a dual directory structure: root-level `.py` files and directories (`account.py`, `admin.py`, `bank.py`, `config.py`, `container.py`, `database.py`, `logger.py`, `models.py`, `ui.py`, `utils/`, `application/`, `infrastructure/`, `domain/`, `interfaces/`) coexisting with an identical set under `src/`.

This structure arose from a partially completed architecture migration:
1. **Generation 1:** Root-level Flask + JSON-based system
2. **Generation 2:** Root-level SQLAlchemy system (overwrote gen1 shims)
3. **Generation 3:** `src/`-scoped SQLAlchemy system (canonical target)

The root-level files were kept as backward-compatibility shims, relying on `sys.path.insert(0, "src/")` to let the `src/` versions shadow them at runtime. This created a confusing codebase where:
- New contributors couldn't tell which copy was live
- Two copies of every module diverged slightly
- The `src/interfaces/api/` directory existed but was completely unreachable (root `api/` package was live instead)
- `src/main.py` duplicated root `main.py` but was never executed

## Decision

Delete all confirmed DEAD modules, leaving only one canonical tree:

```
project_root/
├── api.py              # LIVE — FastAPI entry point
├── main.py             # LIVE — CLI entry point
├── api/                # LIVE — API package (imported explicitly, no src/ mirror)
│   ├── __init__.py
│   ├── common.py
│   ├── models.py
│   └── v2.py
├── src/                # LIVE — Canonical application code
│   ├── container.py
│   ├── config.py
│   ├── logger.py
│   ├── bank.py, admin.py, account.py, ui.py
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── utils/
├── tests/
├── docs/
└── ...
```

### Modules Deleted

**Root-level .py files (9):** `account.py`, `admin.py`, `bank.py`, `ui.py`, `config.py`, `container.py`, `database.py`, `logger.py`, `models.py` — All confirmed DEAD via import-graph tracing. Every import from live code resolved to `src/` versions via `sys.path.insert(0, "src/")`. No live code ever reached these files.

**Root-level directories (5):** `utils/`, `application/`, `infrastructure/`, `domain/`, `interfaces/` — Same analysis. Entirely shadowed by `src/` versions.

**src/ files/directories (2):** `src/main.py` (duplicate of root `main.py`, never executed) and `src/interfaces/` (completely unreachable — nothing ever imports `from interfaces`).

### Modules Kept (with caveats)

**`src/database.py`** — Kept because it contains real backward-compatibility functions (`sync_account_from_json`, `get_db_balance`, `atomic_transfer`, etc.) used by tests and seed scripts. Not a pure re-export shim.

**`src/models.py`** — Pure re-export shim. Slated for removal when `alembic/env.py` and `scripts/migrate_json_to_sqlite.py` are updated to import from `infrastructure.persistence` directly.

**`seed_data.py`** (root + `src/seed_data.py`) — Both kept but AMBIGUOUS. Both write to JSON files (legacy format) instead of SQLite. Slated for migration.

### Evidence

Each deletion was verified with:
1. Import-graph tracing (determine which imports resolve to which file)
2. Test suite validation (141/141 tests pass after deletion)
3. Application boot testing (app boots with 80 routes)

## Consequences

**Positive:**
- New contributors see one canonical tree
- No confusion about which copy is live
- Reduced cognitive overhead when reading/modifying code
- Smaller clone size
- `docs/INVENTORY.md` documents the complete classification for reference

**Negative:**
- `tests/conftest.py` had to be updated to add `src/` to `sys.path` (tests previously relied on root-level shadow files)
- Root `api.py` still uses `sys.path.insert` for backward compatibility with root `api/` package imports

## Future Work

This ADR covers only Phase -1 and Phase 1 of the v2 master plan. Subsequent phases (security hardening, data integrity, database migration, etc.) are tracked in `docs/CURRENT_STATE.md`.
