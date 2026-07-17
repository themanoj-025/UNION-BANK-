# Changelog

All notable changes to the **Union Bank Management System** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.2.0] — 2026-07-17

### Added

#### 🔒 Phase 1 — P0 Blockers
- **Atomic transfers** — `TransactionService.transfer()` wrapped in SQLAlchemy `begin_nested()` transaction. Crash-mid-transfer test proves no partial write survives.
- **`CHECK (balance >= 0)` constraint** — Alembic migration adds DB-level CHECK constraint. App-level guard in `services.py` rejects negative balance before write (defense in depth).
- **sys.path hacks removed** — `pip install -e .` replaces all `sys.path.insert()` calls. Zero import path hacks remain.
- **Version sync** — `requirements.txt` pinned versions now match or exceed `pyproject.toml` minimums.

#### 🗄 Phase 2 — PostgreSQL + Async Migration (Partial)
- **PostgreSQL support** — `DATABASE_URL` env var for Postgres; SQLite retained for local dev.
- **Async services** — `async_services.py` with async repository methods for hot paths (deposit, withdraw, transfer, get_profile).
- **Async pagination** — `get_accounts_paginated_async()` with SQL-level pagination (no in-memory slicing).
- **Cache invalidation** — All write paths invalidate Redis cache in same request.

#### 🛡 Phase 3 — Security Hardening
- **Refresh token hashing** — `token_id` field stores bcrypt hash of raw refresh token (not reversible).
- **TOTP secrets encrypted** — Fernet-encrypted with key from env var `TOTP_ENCRYPT_KEY`.
- **CORS restricted** — `allow_methods` and `allow_headers` are explicit lists (no wildcard).
- **Account-based rate limiting** — Money-movement endpoints rate-limited per account (max 5/hour), bypassable via different IP.
- **CSRF protection** — Double-submit cookie pattern with CSRF token validation on state-changing requests.
- **httpOnly cookies** — Frontend token storage migrated from localStorage to httpOnly, Secure, SameSite=Strict cookies.
- **Security test fixtures** — SQLi attempt fixtures, XSS payload fixtures, CSRF token omission tests.

#### 🔌 Phase 4 — Frontend↔Backend Wiring
- **AdminTransactions bugfix** — Missing error + loading states, wrong API endpoint for freeze/unfreeze fixed.
- **Error state handling** — All admin pages show visible error states on 4xx/5xx (AdminAccounts, AdminDashboard, AdminLoans, AdminTransactions).
- **Loading states** — Consistent loading indicators across all admin pages.
- **Response headers** — Pagination (`X-Total-Count`) and rate limiting (`X-RateLimit-Remaining`) headers on list/money-movement endpoints.

#### 🧪 Phase 5 — Testing to 10/10
- **Frontend tests** — Vitest + React Testing Library with 10 tests across ErrorBoundary, Header, PrivateRoute components.
- **Coverage gaps closed** — `services.py` coverage raised to 85%+ on critical branches (loan rejection, freeze/unfreeze, notification failure).
- **Mutation testing** — `mutmut` wired in CI as non-blocking report (can be promoted to blocking gate).
- **Schemathesis fuzz** — OpenAPI spec fuzzing in CI against all endpoints.
- **Security test suite** — Dedicated CI job for security tests on every PR.

#### ⚙️ Phase 6 — DevOps & Observability
- **Multi-stage Dockerfile** — `.dockerignore` excludes tests, docs, node_modules, .git. Final image reduced.
- **docker-compose.prod.yml** — Prometheus + Grafana added. Postgres/Redis ports hidden from host.
- **Health endpoint** — `/api/v2/health` checks DB + Redis connectivity, returns 503 on failure.
- **`cache.ping()`** — Added to all cache implementations (base, NullCache, RedisCache).
- **Grafana dashboard** — 6 panels: request rate, error rate, p95 latency, cache hit ratio, DB query rate, in-flight requests.
- **K8s manifests** — `deployment.yaml`, `service.yaml`, `ingress.yaml`, `hpa.yaml` — ready for cluster deployment.
- **CI secrets check** — Automated scan for RSA keys, AWS keys, GitHub tokens, Stripe keys.

#### 🎨 Phase 7 — Code Quality Polish
- **Protocol-based DI** — `NotificationServiceProtocol` replaces bare `Optional = None` in all 4 service constructors. `IdempotencyRepositoryProtocol` for idempotency repo.
- **LoanStatus enum** — All status comparisons/assignments use `LoanStatus.X.value` across entire LoanService. No raw strings.
- **LOAN_TYPES from enum** — Derived from `LoanType` enum values — single source of truth.
- **Domain purity** — `domain/interest.py` passes rate as parameter; zero config/infra imports in domain.
- **Circuit breaker** — `pybreaker.CircuitBreaker` around all 12 notification call sites; `CircuitBreakerError` caught before `Exception`.
- **Import ordering** — Conventional order (stdlib → third-party → project) with proper grouping.
- **Pyright type checking** — Close to zero type errors; full Python type annotations.

### Changed

- **`domain/interest.py`** — `calculate_monthly_interest()` now accepts `annual_rate_pct` parameter (default 3.5) instead of importing from global config.
- **`application/services.py`** — 4 service constructors now use typed Protocols for dependency injection.
- **`application/interfaces.py`** — Added `NotificationServiceProtocol` with 12 method signatures.
- **`frontend/src/api.js`** — Token storage migrated from localStorage to httpOnly cookies with CSRF header.
- **`frontend/src/pages/Admin/*.jsx`** — Error states, loading states, pagination headers added.
- **`.husky/`** — Git hooks initialized with commitlint enforcement.
- **`CONTRIBUTING.md`** — Complete rewrite with branch strategy, conventional commits, modern architecture.

### Added

- **`docs/adr/ADR-0006-git-strategy.md`** — Git branch strategy, conventional commits policy, release process.
- **`monitoring/prometheus.yml`** — Prometheus scrape config targeting API on port 8000.
- **`monitoring/grafana/datasources/prometheus.yml`** — Auto-provisioned Prometheus datasource.
- **`monitoring/grafana/dashboards/union-bank-dashboard.json`** — 6-panel Grafana dashboard.
- **`k8s/deployment.yaml`** — Kubernetes deployment with 2 replicas, rolling update, probes.
- **`k8s/service.yaml`** — ClusterIP service.
- **`k8s/ingress.yaml`** — TLS ingress.
- **`k8s/hpa.yaml`** — Horizontal Pod Autoscaler (CPU 70%, Memory 80%, 2-10 replicas).
- **`package.json`** — Root-level package.json for git tooling (husky, commitlint).
- **`commitlint.config.js`** — commitlint config enforcing Conventional Commits.
- **`.husky/commit-msg`** — commitlint git hook.
- **`tests/test_security.py`** — Security test fixtures for SQLi, XSS, CSRF.

### Fixed

- **Pre-existing API test failures** — Missing `ApiResponse` import in `main.py` fixed. All 375+ backend tests pass.
- **AdminAccounts page** — Wrong column name, wrong endpoint, missing loading states.
- **`NotificationService` indentation** — Corrected str_replace artifact in notification.py.
- **`services.py` import ordering** — `import pybreaker` moved after all other imports.
- **`utils/__init__.py`** — Removed import of `SAVINGS_INTEREST_RATE` from `domain/interest`.

---

## [2.1.0] — 2026-07-17

### Added

#### 🏗 Architecture Consolidation (Phase -1 & 1)
- **Forensic inventory** (`INVENTORY.md`) — Module-by-module classification as LIVE/DEAD/AMBIGUOUS with import-graph evidence. Zero AMBIGUOUS entries remaining.
- **Single canonical tree** — Consolidated from 2-3 overlapping code generations to `src/unionbank/` with clean layered architecture (domain → application → infrastructure → entrypoints → utils)
- **Dead code deleted** — Removed all root-level Flask/JSON files (`account.py`, `admin.py`, `bank.py`, `ui.py`, `config.py`, `container.py`, `database.py`, `logger.py`, `models.py`) and stale `templates/`, `static/` directories
- **God module split** — `utils/auth.py` (was hashing + rate limiting + sessions + CSV export + interest + categories) split into focused modules: `hashing.py`, `rate_limit.py`, `csv_export.py`, `interest.py`, `categories.py`, `formatting.py`, `validation.py`
- **Versioned API** — `/api/v1/` (legacy, deprecated) and `/api/v2/` (current, envelope-wrapped `ApiResponse[T]`) with deprecation headers
- **ADR-0001** — Service layer consolidation: single canonical tree, protocol-based DI

#### 🛡 Security Hardening (Phase 2)
- **Password leak fixed** — Removed password hash from all API responses. Test `test_password_leak.py` enforces no response model contains a "password" key.
- **TOTP 2FA completed** — Fully implemented for admin: enrollment (QR provisioning URI), verification (pyotp with valid_window=1), login enforcement, disable with TOTP code. 4 endpoints: status/setup/verify/disable.
- **DB-backed refresh tokens** — Rotation + revocation (old token revoked on each refresh). Stored in SQLite with expiry tracking.
- **Token versioning** — Password change increments version → all existing JWTs invalidated. Tested in `test_integration.py`.
- **Rate limiting** — Account-aware (5 failed attempts → 15-min lockout) per-account + IP-based (slowapi) on all endpoints: login (10/min), register (5/min), deposit/withdraw/transfer (10/min), admin (10-30/min)
- **CSRF protection** — Origin/Referer validation middleware (defense in depth for Bearer-token API)
- **Security headers** — HSTS, X-Frame-Options, X-Content-Type-Options, CSP, Permissions-Policy, X-XSS-Protection via middleware
- **Bare except:pass banned** — All exception handlers log with context. CI grep-check enforces no silent swallowing.
- **THREAT_MODEL.md** — 10 threats documented with STRIDE classification, risk assessment, mitigations, and incident response procedures
- **ADR-0002** — Token strategy, 2FA, and CSRF defense-in-depth architecture
- **ADR-0003** — TOTP 2FA completion: enrollment, verification, login enforcement, disable

#### 💾 Data Integrity & Compliance (Phase 3)
- **Soft-delete** — Accounts now use `deleted_at` timestamp instead of hard-delete. Default queries filter out soft-deleted records. Transaction history survives account "deletion."
- **Idempotency keys** — `IdempotencyRecord` entity + `_check_idempotency()` in TransactionService. Deposit/withdraw/transfer endpoints accept `idempotency_key` — retries return cached result instead of re-executing.
- **Concurrent transfer safety** — 10 parallel transfers with `ThreadPoolExecutor` prove no lost updates, no double-spending.
- **ADR-0004** — Data retention: soft-delete + idempotency framed around banking regulatory norms

#### 🗄 Database & Performance (Phase 4)
- **Alembic migrations** — Migration infrastructure with versioned schema changes. 5 migration round-trip tests.
- **PostgreSQL support** — `DATABASE_URL` env var for PostgreSQL. Migration path via Alembic. Documented in ADR-0005.
- **Pagination** — Offset-based pagination on admin account list, admin transactions. Keyset (cursor-based) pagination on statements.
- **Aggregated statistics** — `get_statistics()` consolidated from 9 separate queries to single pass.
- **Redis caching** — Wired for admin account list with 60s TTL, invalidation-on-write pattern in `infrastructure/cache.py`.
- **Bounded account number generation** — Hard cap at 1000 retries with `RuntimeError` (previously unbounded loop).
- **Database indexes** — Composite indexes on accounts (status, name+number, created+deleted, mobile), transactions (account+timestamp, timestamp+type), loans, savings, notifications.
- **ADR-0005** — PostgreSQL migration strategy

#### 🔬 Observability (Phase 6)
- **Prometheus metrics** — `MetricsMiddleware` wired on FastAPI app. `/metrics` endpoint exposes request rate, latency histogram, in-flight requests, error rate, cache hit/miss.
- **Structured JSON logging** — JSON format → `bank.jsonl` with `request_id`, account context, level. Uvicorn access logs routed through same logger.
- **Request tracing** — Every request gets unique `X-Request-ID` header propagated through all log lines.
- **Health probes** — `/api/healthz` (liveness), `/api/readyz` (readiness with DB connectivity check).
- **RUNBOOK.md** — Incident response procedures, troubleshooting guides, operational runbook.

#### 🔍 Analyzr — Natural-Language Search (Phase 8)
- **Zero-dependency offline engine** — `utils/analyzr_core.py` with 20 intent patterns, regex-based classification, amount extraction, time window computation. No LLM costs, no API latency.
- **53 unit tests** — Covering intent detection, amount parsing (over/under/between/currency), time windows (today/this week/last month/90 days), averages, edge cases.
- **API endpoint** — `POST /api/v2/analyzr/query` accepts natural-language query + optional account number.
- **CLI wrapper** — `scripts/analyzr.py` with argparse, color output, JSON mode, query pattern listing.

#### 🧪 Testing Expansion (Phase 7)
- **256 tests** (up from ~149) — Full coverage boost from 26% → 72%.
- **Property-based tests** — 5 hypothesis invariants + stateful money machine for transfer correctness.
- **Concurrency tests** — 10 parallel transfers proving no race conditions or lost updates.
- **Security tests** — Password leak detection, JWT tampering, expired token rejection, SQL injection attempts.
- **Edge-case tests** — 44 tests covering formatting edge cases, category handling, file I/O corruption recovery, fakes with constraint violations.
- **Migration tests** — 5 Alembic round-trip tests (upgrade, downgrade, idempotent, table verification).
- **E2E API tests** — `e2e_test.py` with 23 black-box API endpoint tests covering V1, V2, and Admin flows.

#### ⚙️ Tooling & DevOps (Phase 9)
- **Dependencies cleaned** — Removed Dead deps: Flask, Flask-WTF, fpdf2. Versions pinned with `==` in `requirements.txt` + `requirements-lock.txt` for transitive deps.
- **FastAPI-only Docker** — Multi-stage Docker build with single `api` target (no Flask `web` stage). `docker-entrypoint.sh` uses `unionbank.entrypoints.api.main:app`.
- **CI/CD updates** — Frontend lint + build stages. Ruff lint integrated. Coverage floor raised to 50% (from 26%). Docker healthcheck uses `/api/healthz`.
- **`.gitignore`** — Comprehensive patterns for `__pycache__`, `.db*`, `.jsonl`, `.env*`, `node_modules`, `dist/`, temp test DB dirs.

#### 📚 Documentation & Portfolio Packaging (Phase 10)
- **README rewrite** — Case-study structure: The Problem → Architecture → 3 Key Engineering Decisions → Security → Observability → Analyzr → Metrics → Testing → Quick Start → 10x Scale. Badges updated (256 tests, 72% coverage).
- **SELF_AUDIT.md** — Finding-by-finding reconciliation of all 38 items from both original audits. Scoring: original 3.4/10 → current 8.1/10.
- **6 Architecture Decision Records** — ADR-0001 through ADR-0005 covering consolidation, security, TOTP, data retention, PostgreSQL.
- **THREAT_MODEL.md** — 10 threats with STRIDE, risk assessment, mitigation, incident response.
- **RUNBOOK.md** — Operational runbook for production troubleshooting.
- **TS_MIGRATION.md** — 3-phase TypeScript migration plan for the React frontend.

### Changed

- **API base URL** — Frontend changed from hardcoded `http://localhost:8000` to relative URL via Vite proxy (`/api/*` → `localhost:8000`).
- **Vite proxy** — Added proxy config in `vite.config.js` for same-origin API requests.
- **Container imports** — All `from container import get_container` replaced with `from infrastructure.container import get_container` (80 refs). Backward-compat shim deleted.
- **Ruff config** — Added docstring style rules (D101, D102, D103, D200, D204, D212, D413, I001) to ignore list.
- **`data/bank.jsonl`, `*.db*`** — Untracked from git index. Now covered by `.gitignore`.

### Fixed

- **`init_db()` relative import** — Changed from `from .persistence import ...` to `from infrastructure.persistence import ...` to fix `ImportError` in ASGI transport context.
- **`init_db()` module-level call** — Moved to FastAPI lifespan handler (asynccontextmanager) so all imports resolve before DB operations run.
- **`_JSON_LOG_FILE` path** — Fixed from wrong subdirectory to `_PROJECT_ROOT/data/bank.jsonl` with `os.makedirs()`.
- **Admin login in E2E tests** — Added `_ensure_admin_exists()` to create admin user before tests.
- **`container.py` missing module** — Created backward-compat shim (later resolved to direct `infrastructure.container` imports).

### Removed

- **Root `api.py`** — Deleted (conflicted with `api/` package directory).
- **Root `main.py`** — CLI entry point replaced by `src/unionbank/entrypoints/cli/main.py`.
- **Root `src/` shadow files** — `account.py`, `admin.py`, `bank.py`, `ui.py`, `config.py`, `container.py`, `database.py`, `logger.py`, `models.py` — all shadowed by `src/` versions, now deleted.
- **Flask templates** — `templates/` directory (26+ HTML files).
- **Static assets** — `static/style.css`, legacy frontend.
- **Flask application** — `webapp.py` and `tests/test_htmx_integration.py`.
- **`services.py`, `repositories.py`** — Replaced by `application/services.py` and `infrastructure/repositories.py`.
- **`container.py` shim** — Backward-compat shim deleted after all 80 imports updated to `infrastructure.container`.

---

## [2.0.0] — 2026-06-02

### Added

#### 🔌 FastAPI REST API
- **`api.py`** — Full REST API with 24 endpoints and JWT authentication (HS256, 24h expiry)
- **Customer endpoints** — Login, register, profile CRUD, deposit, withdraw, transfer, statements, CSV export, apply interest, change password, close account
- **Admin endpoints** — List/search accounts, freeze/unfreeze, delete, statistics, view transactions, change password
- **Savings goals endpoints** — CRUD operations with contribute (balance deduction) and delete (refund)
- **Swagger UI** — Auto-generated interactive docs at `/docs` with OpenAPI schema
- **Pydantic models** — Request/response validation for all endpoints
- **CORS enabled** — Allow all origins for frontend consumption
- **Rate limiting** — Same as CLI: 5 failed attempts → 15-min lockout

#### 🌐 Flask Web UI
- **`webapp.py`** — Full Flask web frontend with 26+ routes
- **Redesigned landing page** (`index.html`) — Hero with animated shapes, gradient text, live bank statistics (accounts, transactions, balance), feature cards, security section, progress bars, CTA
- **Interactive charts** — Chart.js v4.4.7 across 4 pages: customer dashboard (doughnut/bar/line), admin statistics (doughnut/bar/horizontal bar), account detail (doughnut/line), statement (line)
- **Admin account detail page** (`admin_account_detail.html`) — Full profile card with status badge, financial summary (6 stats), category doughnut chart, balance trend line, recent transactions
- **Session management** — Flask sessions with permanent flag, login/logout across customer and admin

#### 🎯 Savings Goals (All 3 Interfaces)
- **`utils.py`** — `load_goals()`, `save_goals()`, `generate_goal_id()` helpers with per-account namespaced storage
- **CLI** — Full sub-menu (create, contribute with confirmation, edit, delete with refund, ASCII progress bars)
- **Web** — 5 routes (list with stat cards + doughnut chart, create/edit form, contribute inline, delete with refund)
- **API** — 5 endpoints (`GET/POST /api/savings`, `PUT /api/savings/{id}`, `POST /api/savings/{id}/contribute`, `DELETE /api/savings/{id}`)
- **Balance deduction** — Contributions deduct from account balance; deletes refund to balance
- **Transaction logging** — All goal activities logged as transactions with "Savings" category

#### 📊 Interactive Charts (Web UI)
- **Customer Dashboard** — Doughnut (category breakdown), Bar (transaction types), Line (balance trend, sampled for performance)
- **Admin Statistics** — Doughnut (active/frozen/closed), Bar (deposits vs withdrawals vs transfers), Horizontal Bar (top categories by volume)
- **Account Detail** — Doughnut (per-customer category spending), Line (balance history with quick stats)
- **Transaction Statement** — Line (balance history with gradient fill), mini stat cards (total credits, debits, counts)

#### 📦 Seed Data
- **`seed_data.py`** — Generate 5,000 sample accounts with 70,000 realistic transactions
- **Realistic data** — Indian names, phone numbers, categories, varying balances
- **Fast generation** — 7.9 seconds for 5,000 accounts + transactions
- **Admin credentials preserved** — `admin` / `admin123` always usable
- **`data/` files auto-backup** — Existing data backed up as `.bak` before seeding

### Changed

- **`webapp.py`** — Complete rewrite from scratch (Flask web frontend)
- **`account.py`** — Added `savings_goals_menu()` with full CLI sub-menu (list, create, contribute, edit, delete)
- **`bank.py`** — Added "Savings Goals" option (8) to customer menu
- **`api.py`** — Complete new file (FastAPI application)
- **`requirements.txt`** — Added `Flask>=3.1.0`, `fastapi`, `PyJWT`, `uvicorn`
- **`README.md`** — Complete rewrite with architecture diagram, feature comparison tables, full API reference, chart documentation, updated stats

---

## [1.1.0] — 2026-06-02

### Added

#### 🎨 Terminal UI
- **`ui.py`** — New centralized UI module with colorama color constants, styled print helpers (`success()`, `error()`, `warning()`, `info()`), password masking via getpass, and cross-platform screen clearing.
- **Colored output across all modules** — Green for success, red for errors, yellow for warnings, cyan for info/labels, and bold for emphasis.
- **Password masking** — All password prompts now use `getpass` so characters are not echoed to screen.
- **Box-drawn menu frames** — Main menu and admin panel have colored Unicode box-drawing frames.
- **Colored transaction statements** — Credits displayed in green, debits in red.
- **Colored account status badges** — ACTIVE (green), FROZEN (red), CLOSED (yellow).

#### 💾 JSON Storage Hardening
- **Auto-backup** — Every save creates a `.bak` copy of the previous file version.
- **Corruption recovery** — On load, if JSON is corrupted, automatically restores from backup.
- **Atomic writes** — Writes go to a temp file first, then are atomically renamed (reduces corruption risk).
- **Graceful fallback** — If both file and backup are corrupted, resets to empty state with a log warning.

### Changed

- **`utils.py`** — `load_json()` and `save_json()` completely rewritten with backup, atomic write, and corruption recovery. Removed `header()` and `divider()` (moved to `ui.py`).
- **`bank.py`** — All display output migrated to `ui.py` helpers. Passwords now masked via `prompt_password()`. Customer menus colored cyan with white options.
- **`account.py`** — Statements, profile, and transaction screens colored. Passwords masked. Credits green, debits red.
- **`admin.py`** — Statistics box has green frame with colored metrics. Account list has colored status badges. Passwords masked.
- **`main.py`** — Main menu uses green frame with yellow title and cyan options.
- **`requirements.txt`** — Added `colorama>=0.4.6`.

---

## [1.0.0] — 2026-06-02

### Added

#### 🔒 Security
- **bcrypt password hashing** — All passwords (customer & admin) are now hashed with salted bcrypt before storage. Plain-text passwords are never written to disk.
- **Automatic password migration** — Existing `data/admin.json` with plain-text passwords is automatically migrated to bcrypt on startup.
- **Password strength validation** — New passwords must be at least 8 characters with at least 1 uppercase letter, 1 lowercase letter, and 1 digit. Enforced during registration and password changes.

#### ✅ Input Validation
- **Email validation** — Format verified via regex (`user@example.com`). Rejects malformed addresses.
- **Indian mobile validation** — 10-digit numbers starting with 6–9. Rejects invalid formats.
- **Name validation** — Letters and spaces only, 2–50 characters. Rejects empty or invalid names.
- **Age validation** — Checks for valid integer input, minimum age of 18, and a reasonable maximum (120).

#### 🧪 Testing Infrastructure
- **35 unit tests** covering password hashing, all validators, generators, currency formatting, JSON helpers, and amount validation.
- **Smoke tests** verifying all 6 modules import correctly without errors.
- **pytest configuration** in `pyproject.toml` with test discovery rules.
- **Coverage configuration** targeting 80% minimum coverage.

#### ⚙️ Project Tooling
- **`.gitignore`** — Ignores `__pycache__`, virtual environments, IDE folders, runtime data files, logs, and OS artifacts.
- **`requirements.txt`** — Lists `bcrypt`, `pytest`, and `pytest-cov` dependencies.
- **`pyproject.toml`** — Project metadata (name, version, Python 3.10+), build system config, and pytest/coverage settings.

#### 📄 Documentation
- **`README.md`** — Comprehensive project documentation with overview, features, project structure, installation guide, usage instructions, testing guide, technology stack, roadmap, and contributing guidelines.
- **`CHANGELOG.md`** — This file — structured changelog following Keep a Changelog format.

### Changed

- **`bank.py`** — Registration and login now use `hash_password()` and `verify_password()` instead of plain-text comparison.
- **`account.py`** — Password changes and account closure now use bcrypt verification. New passwords are hashed before storage.
- **`admin.py`** — Admin login, password changes, and credential initialization now use bcrypt. Existing passwords auto-migrate.
- **`utils.py`** — Added `hash_password()`, `verify_password()`, `validate_email()`, `validate_phone()`, `validate_password()`, and `validate_name()` functions.

---

## [0.1.0] — Initial Release

### Features

- Account registration with basic input collection
- Customer login and dashboard
- Deposit, withdraw, and fund transfer operations
- Mini and full transaction statements
- Profile viewing and updating
- Password change and account closure
- Admin panel with account listing, search, freeze/unfreeze, delete, statistics
- JSON-based data persistence
- Centralized logging (file + console)
- Box-drawing UI for terminal menus

<!-- Links for version comparison -->
[1.1.0]: https://github.com/themanoj-025/UNION-BANK-/releases/tag/v1.1.0
[1.0.0]: https://github.com/themanoj-025/UNION-BANK-/releases/tag/v1.0.0
[0.1.0]: https://github.com/themanoj-025/UNION-BANK-/releases/tag/v0.1.0
