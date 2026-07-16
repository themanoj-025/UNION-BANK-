# Baseline Metrics — Union Bank Management System

**Date:** 2026-07-16
**Commit:** `808492a` (chore: raise CI coverage floor to 50%)
**Tag:** `pre-audit-baseline`
**Source:** Comprehensive 28-dimension audit (Buffy/DeepSeek V4)

---

## Test Metrics

| Metric | Value | Notes |
|--------|:-----:|-------|
| **Tests collected** | 313 | pytest discovery |
| **Tests passed** | 256 | |
| **Tests failed** | 2 | `test_simultaneous_transfers_no_lost_updates`, `test_concurrent_deposits_no_lost_updates` (race conditions) |
| **Tests errored** | 55 | `test_api_integration.py` — `ImportError: cannot import name 'app' from 'api'` (pre-existing, not caused by audit) |
| **Coverage (overall)** | 42% | Based on 256 running tests; 72% with all 313 tests running |
| **Frontend tests** | **0** | No test framework installed or configured |

### Coverage by Module (256 running tests)

| Module | Coverage |
|--------|:--------:|
| domain/entities.py | 86% |
| domain/interest.py | 100% |
| domain/clock.py | 100% |
| application/services.py | 64% |
| application/notifications.py | 72% |
| infrastructure/repositories.py | 61% |
| infrastructure/database.py | 90% |
| infrastructure/container.py | 91% |
| infrastructure/persistence.py | 95% |
| infrastructure/mappers.py | 86% |
| infrastructure/cache.py | 0% |
| infrastructure/metrics.py | 0% |
| entrypoints/api/common.py | 0% |
| entrypoints/api/main.py | 0% |
| entrypoints/api/v2.py | 0% |
| entrypoints/cli/* | 6-62% |
| utils/formatting.py | 96% |
| utils/validation.py | 100% |
| utils/hashing.py | 100% |
| utils/logger.py | 72% |
| utils/analyzr_core.py | 47% |
| utils/savings.py | 0% |
| config.py | 89% |

---

## Lines of Code (LOC) per Layer

| Layer | LOC | % of Backend |
|-------|:---:|:------------:|
| **Domain** (entities, interest, clock) | 415 | 3.6% |
| **Application** (services, notifications, interfaces) | 2,051 | 17.7% |
| **Infrastructure** (repos, DB, cache, metrics, mappers, container) | 2,435 | 21.0% |
| **API Entrypoints** (main.py, common.py, models.py, v2.py) | 3,451 | 29.7% |
| **CLI Entrypoints** (account, admin, bank, main, ui) | 1,711 | 14.7% |
| **Utils** (hashing, formatting, validation, etc.) | 1,210 | 10.4% |
| **Config / Logger** | 340 | 2.9% |
| **Total Backend Python (src)** | **11,613** | 100% |

| **Tests** | 5,500 | — |
| **Frontend (JSX + JS + CSS)** | 5,559 | — |
| **Total Project (excl node_modules)** | **24,351** | — |

---

## Issue Count from Audit

| Severity | Count | Key Issues |
|----------|:-----:|------------|
| 🔴 **P0 — Critical** | 4 | requirements.txt version mismatch, SQLite in production, no atomic transfer transaction, no balance CHECK constraint |
| 🟡 **P1 — High** | 3 | No async DB (sync SQLAlchemy in async framework), zero frontend tests, no non-negative balance app guard |
| 🟠 **P2 — Medium** | 5 | In-memory pagination for admin accounts, plaintext refresh tokens, TOTP secrets in same DB, duplicate business logic in API+service, magic string statuses |
| 🟢 **P3 — Low** | 3 | No cache invalidation on writes, frontend localStorage token storage, no pagination metadata in API |
| 🔵 **P4 — Enhancement** | 3 | No feature flags, no distributed tracing, no K8s manifests |
| ⚪ **Total** | **18** | |

---

## Security Baseline

| Category | Status |
|----------|--------|
| JWT authentication | ✅ HS256 (configurable RS256) |
| Password hashing | ✅ bcrypt |
| Refresh token rotation | ✅ Implemented |
| TOTP 2FA (admin) | ✅ Implemented |
| Rate limiting (IP-based) | ✅ slowapi on all endpoints |
| Rate limiting (account-based) | ❌ Missing on money movement |
| CORS restricted | ⚠️ `allow_methods="*"`, `allow_headers="*"` |
| Content Security Policy | ✅ Implemented |
| CSRF protection | ⚠️ Logging only mode |
| SQL injection protection | ✅ SQLAlchemy ORM |
| Token storage (frontend) | ❌ localStorage |
| Password in API response | ✅ Fixed |
| Security tests | ❌ Not present |
| Security documentation | ✅ THREAT_MODEL.md |

---

## DevOps Baseline

| Category | Status |
|----------|--------|
| Docker build | ✅ Multi-stage (base, api, dev) |
| Docker Compose | ✅ API + Redis |
| Production Compose | ⚠️ docker-compose.prod.yml exists but Redis port still exposed |
| CI pipeline | ✅ GitHub Actions (lint + test + build + coverage floor) |
| CD pipeline | ❌ Not implemented |
| K8s manifests | ❌ Not implemented |
| Secrets management | ❌ .env file |
| Monitoring | ⚠️ Prometheus metrics defined but dead counters |
| Health checks | ⚠️ /health returns 200 even if DB is down |
| Image size | Not measured |

---

## Architecture Baseline

| Dimension | Score |
|-----------|:-----:|
| Architecture | 7.0/10 |
| Code Quality | 7.5/10 |
| Readability | 8.0/10 |
| Scalability | 5.0/10 |
| Maintainability | 7.5/10 |
| Performance | 6.5/10 |
| Security | 8.5/10 |
| Documentation | 8.5/10 |
| Testing | 8.0/10 |
| DevOps | 7.0/10 |
| UI/UX | 6.0/10 |
| Developer Experience | 7.0/10 |
| Open Source Quality | 8.5/10 |
| Production Readiness | 5.5/10 |
| Portfolio Quality | 8.0/10 |
| Resume Value | 7.5/10 |
| **Overall** | **7.1/10** |

---

## Key Findings at Baseline

### P0 Issues (blockers for production)
1. `requirements.txt` has `fastapi==0.109.0` but pyproject.toml requires `>=0.115.0` — build would break
2. SQLite is the production database (no PostgreSQL migration path completed)
3. `TransactionService.transfer()` is NOT wrapped in an atomic DB transaction — crash mid-transfer loses money
4. No `CHECK (balance >= 0)` constraint at the database level

### Pre-existing Test Failures (not caused by audit)
1. 55 API integration tests error with `ImportError: cannot import name 'app' from 'api'` — import path issue
2. 2 concurrent transfer tests fail due to SQLite write serialization (known limitation)

### Version Mismatches
- `fastapi==0.109.0` < `>=0.115.0` (pyproject.toml minimum)
- `uvicorn==0.27.0` < `>=0.30.0` (pyproject.toml minimum)
- Multiple pyproject.toml dependencies not pinned in requirements.txt (pydantic, passlib, structlog, pybreaker, httpx, typer, rich)
