# Current State — After Phase -1 & Phase 1 Cleanup

**Date:** July 15, 2026  
**Status:** Codebase consolidated to one canonical tree. Critical password leak fixed.

---

## What Changed

### Deleted Files (Phase 1)
**Root-level .py files (9)** — All confirmed DEAD via import-graph tracing:
- `account.py`, `admin.py`, `bank.py`, `ui.py`, `config.py`
- `container.py`, `database.py`, `logger.py`, `models.py`

**Root-level directories (5)** — All confirmed DEAD (shadowed by `src/`):
- `utils/`, `application/`, `infrastructure/`, `domain/`, `interfaces/`

**src/ files/directories (2)** — Confirmed unreachable:
- `src/main.py` (duplicate of root `main.py`)
- `src/interfaces/` (nothing imports from `interfaces.*`)

### Fixed
- **Password leak (CRITICAL):** Removed `"password": domain_account.password` from the dict returned by `get_current_customer()` in `api/common.py`. Password hash is no longer included in every authenticated API response.

### Updated
- **tests/conftest.py:** Added `src/` to sys.path so tests can find the canonical modules after root-level shims were deleted.

## Architecture (Current)

```
project_root/
├── api.py              ← LIVE FastAPI app (entry point)
├── main.py             ← LIVE CLI entry point
├── api/                ← LIVE API package (imported by api.py)
│   ├── __init__.py     ← Importlib loader for api.py
│   ├── common.py       ← JWT auth helpers (password leak FIXED)
│   ├── models.py       ← Pydantic models
│   └── v2.py           ← V2 envelope-wrapped router
├── src/                ← LIVE canonical application code
│   ├── container.py    ← DI container
│   ├── config.py       ← Configuration
│   ├── logger.py       ← Structured logging
│   ├── database.py     ← Re-export shim (to remove later)
│   ├── models.py       ← Re-export shim (to remove later)
│   ├── bank.py         ← CLI customer ops
│   ├── admin.py        ← CLI admin ops
│   ├── account.py      ← Account model/ops
│   ├── ui.py           ← CLI rendering
│   ├── seed_data.py    ← Seed script (JSON format, needs migration)
│   ├── domain/         ← Pure domain entities
│   ├── application/    ← Business logic services
│   ├── infrastructure/ ← DB, cache, metrics, repositories
│   └── utils/          ← Utilities
├── tests/              ← Test suite (141 pass)
├── docs/               ← Documentation
│   ├── INVENTORY.md    ← Module classification
│   └── CURRENT_STATE.md← This file
├── data/               ← Database + logs
├── scripts/            ← Docker entrypoint, migration
├── frontend/           ← React SPA
└── ...config files
```

## Test Results

| Suite | Status | Count |
|-------|--------|-------|
| Unit tests (services, utils) | ✅ All pass | 100 |
| Integration tests (SQLite) | ✅ All pass | 39 |
| Property-based tests | ✅ All pass | 5 |
| Smoke tests | ✅ All pass | 6 |
| **API integration tests** | ❌ **Pre-existing error** | 55 errors |
| **Concurrency tests** | ❌ **Pre-existing failure** | 2 failures |

**Pre-existing issues (not caused by cleanup):**
1. `test_api_integration.py`: `TypeError: Client.__init__() got an unexpected keyword argument 'app'` — Starlette/TestClient version incompatibility on Python 3.14
2. `TestConcurrentTransfers`: SQLite write-concurrency race conditions (known limitation)

## Security Status

| Issue | Status |
|-------|--------|
| Password hash in API response | ✅ **FIXED** (Phase 2, Step 1) |
| TOTP 2FA | ✅ Already implemented in LIVE code (root `api.py`) |
| Refresh token rotation | ✅ Already implemented in LIVE code |
| Token version validation | ✅ Already enforced in `get_current_customer()` |
| Hard-delete cascading transactions | ❌ Still open (Phase 3) |
| Idempotency keys | ❌ Still open (Phase 3) |

---

## Next Steps (Per v2 Master Prompt)

1. **Phase 2 — Security Hardening (continued)**
   - Complete TOTP audit (verify enrollment → QR → verification → login gating all work end-to-end)
   - Fix `except Exception: pass` bare swallows repo-wide (CI grep rule)
   - Add per-account rate limiting on transaction endpoints
   - Write THREAT_MODEL.md

2. **Phase 3 — Data Integrity & Compliance**
   - Soft-delete for accounts (stop cascading transaction deletion)
   - Idempotency keys for deposit/withdraw/transfer

3. **Phase 4 — Database & Performance**
   - PostgreSQL migration
   - Wire Redis cache into reads (already defined but not fully wired)
   - Consolidate 9 separate queries in `get_statistics()` into one

4. **Phase 5 — API, Error Handling & Frontend**
   - Register v2 exception handlers on app instance
   - Structured error codes
   - Frontend TypeScript migration
