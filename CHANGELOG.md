# Changelog

All notable changes to the **Union Bank Management System** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
[1.1.0]: https://github.com/yourusername/union-bank/releases/tag/v1.1.0
[1.0.0]: https://github.com/yourusername/union-bank/releases/tag/v1.0.0
[0.1.0]: https://github.com/yourusername/union-bank/releases/tag/v0.1.0
