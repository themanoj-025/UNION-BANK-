<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.1%2B-000?logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/FastAPI-0.135%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-d71f00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Chart.js-4.4%2B-FF6384?logo=chartdotjs&logoColor=white" alt="Chart.js">
  <a href="https://github.com/themanoj-025/UNION-BANK-/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/UNION-BANK-/ci.yml?branch=main&label=CI&logo=github" alt="CI"></a>
  <img src="https://img.shields.io/badge/tests-139%20passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <img src="https://img.shields.io/badge/database-SQLite_3-brightgreen" alt="SQLite">
</p>

<h1 align="center">
  🏦 Union Bank Management System
</h1>

<p align="center">
  <strong>A full-stack banking application</strong> — <em>CLI · Flask Web UI · FastAPI REST API</em>
</p>

<p align="center">
  <i>Register accounts · Deposit & withdraw · Transfer funds · Loans · Savings goals · Admin panel · Rate limiting · CSV export · Interest calculation · Interactive charts · REST API with JWT auth · In-app notifications</i>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-api-reference">API Reference</a> ·
  <a href="#-testing">Testing</a> ·
  <a href="#-project-structure">Project Structure</a>
</p>

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** ([Download](https://python.org/downloads))
- **pip** (ships with Python)

### Installation

```bash
# 1. Clone
git clone https://github.com/themanoj-025/UNION-BANK-.git
cd UNION-BANK-

# 2. Virtual environment (recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Seed 5,000 sample accounts with transaction history
python seed_data.py
```

### Run the Application

Choose your interface:

| Mode | Command | URL |
|------|---------|-----|
| 🖥️ **CLI (Terminal)** | `python main.py` | Terminal-based menus |
| 🌐 **Web UI (Flask)** | `python webapp.py` | http://localhost:5000 |
| 🔌 **REST API (FastAPI)** | `uvicorn api:app --reload --port 8000` | http://localhost:8000 |
| 📖 **API Docs (Swagger)** | (automatic with API) | http://localhost:8000/docs |

### Docker

```bash
# Start all services (web + API + Redis)
docker compose up -d

# Or use Make targets
make up        # Start all services
make logs      # Follow logs
make test      # Run tests
make down      # Stop all services
```

### Default Credentials

| Role | Username | Password |
|------|----------|----------|
| 👤 **Customer** | (any account number from seed data) | `Seed@123` *(if seeded)* |
| 🛡️ **Admin** | `admin` | `admin123` |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        UNION BANK SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   CLI    │    │  Flask Web   │    │  FastAPI     │                  │
│  │  (main)  │    │  (webapp)    │    │  REST API    │                  │
│  └────┬─────┘    └──────┬───────┘    └──────┬───────┘                  │
│       │                 │                   │                           │
│       └─────────────────┼───────────────────┘                           │
│                         │                                               │
│            ┌────────────▼────────────┐                                  │
│            │   Application Services  │  AuthService, AccountService,   │
│            │   (application/)        │  TransactionService, AdminService│
│            │                         │  LoanService, SavingsGoalService │
│            └────────────┬────────────┘                                  │
│                         │                                               │
│            ┌────────────▼────────────┐                                  │
│            │   Repository Layer      │  10 SQLAlchemy repositories      │
│            │   (infrastructure/)     │  backed by SQLite                │
│            └────────────┬────────────┘                                  │
│                         │                                               │
│            ┌────────────▼────────────┐                                  │
│            │   SQLite Database       │  ACID transactions, WAL mode     │
│            │   (union_bank.db)       │  Foreign keys, connection pooling│
│            └─────────────────────────┘                                  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              Dependency Injection Container                     │    │
│  │              (container.py — wires everything)                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  Domain  │    │  Interfaces  │    │  Alembic     │                  │
│  │ Entities │    │  (Protocols) │    │  Migrations  │                  │
│  └──────────┘    └──────────────┘    └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input → [CLI / Web / API] → Service Layer (business logic)
                                      ↓
                              Repository Layer (data access)
                                      ↓
                              SQLAlchemy ORM → SQLite DB (union_bank.db)
                                      ↓
                              Domain Entities (Account, Transaction, etc.)
```

---

## ✨ Features

### 👤 Customer Features (All Three Interfaces)

| Feature | 🖥️ CLI | 🌐 Web UI | 🔌 REST API |
|---------|---------|-----------|-------------|
| **Account Registration** | ✅ Colored form | ✅ Form with validation | ✅ `POST /api/auth/register` |
| **Secure Login** | ✅ Rate-limited | ✅ Rate-limited | ✅ `POST /api/auth/login` (JWT) |
| **Balance Inquiry** | ✅ Formatted | ✅ Hero card | ✅ `GET /api/account/balance` |
| **Deposit** | ✅ With categories | ✅ Form + dropdown | ✅ `POST /api/account/deposit` |
| **Withdraw** | ✅ Balance check | ✅ Validation | ✅ `POST /api/account/withdraw` |
| **Fund Transfer** | ✅ Confirmation | ✅ 2-step confirm | ✅ `POST /api/account/transfer` |
| **Full Statement** | ✅ Colored table | ✅ Sortable table | ✅ `GET /api/account/statements` |
| **Mini Statement** | ✅ Last 5 txns | ✅ Dashboard widget | ✅ `GET /api/account/statements/mini` |
| **CSV Export** | ✅ File download | ✅ One-click download | ✅ `GET /api/account/export-csv` |
| **Interest (3.5% p.a.)** | ✅ Monthly | ✅ Confirmation page | ✅ `POST /api/account/apply-interest` |
| **Profile Management** | ✅ Inline edit | ✅ Form with validation | ✅ `PUT /api/account/profile` |
| **Change Password** | ✅ Verified | ✅ Strength check | ✅ `POST /api/account/change-password` |
| **Close Account** | ✅ Irreversible | ✅ Danger zone | ✅ `POST /api/account/close` |
| **Savings Goals** | ✅ Full CRUD | ✅ Progress bars | ✅ `GET/POST /api/savings` |
| **Loans** | ✅ Apply, pay EMI | ✅ Apply, view detail | ✅ `POST /api/loans/apply` |
| **Notifications** | — | ✅ In-app notifications | ✅ `GET /api/notifications` |

### 🛡️ Admin Features

| Feature | 🖥️ CLI | 🌐 Web UI | 🔌 REST API |
|---------|---------|-----------|-------------|
| **Admin Login** | ✅ Password mask | ✅ Rate-limited | ✅ `POST /api/auth/admin-login` (JWT) |
| **View All Accounts** | ✅ Table w/ status | ✅ Table w/ links | ✅ `GET /api/admin/accounts` |
| **Account Detail** | ❌ | ✅ Full profile + charts | ❌ |
| **Search Account** | ✅ By number/name | ✅ Search form | ✅ `GET /api/admin/accounts/search?q=` |
| **Freeze / Unfreeze** | ✅ With confirm | ✅ Confirmation | ✅ `POST /api/admin/accounts/{no}/freeze` |
| **Delete Account** | ✅ Permanent | ✅ Type DELETE | ✅ `DELETE /api/admin/accounts/{no}` |
| **Bank Statistics** | ✅ Numbers only | ✅ Stats + charts | ✅ `GET /api/admin/statistics` |
| **View Transactions** | ✅ Filtered | ✅ Filtered table | ✅ `GET /api/admin/transactions` |
| **Change Admin Password** | ✅ Verified | ✅ Strength check | ✅ `PUT /api/admin/password` |
| **Loan Management** | — | ✅ Approve/reject loans | ✅ `POST /api/admin/loans/{id}/approve` |

### 📊 Interactive Charts (Web UI)

| Page | Chart Type | Data Displayed |
|------|-----------|----------------|
| **Customer Dashboard** | Doughnut (category), Bar (types), Line (balance trend) | Spending breakdown, transaction types, balance history |
| **Admin Statistics** | Doughnut (status), Bar (financial), Horizontal Bar (categories) | Account status distribution, deposits vs withdrawals, top categories |
| **Account Detail** | Doughnut (category), Line (balance trend) | Per-customer spending insights |
| **Transaction Statement** | Line (balance history) with gradient fill | Balance change over time with mini stat cards |

### 🔒 Security & Reliability

| Layer | Feature | Details |
|-------|---------|---------|
| 🔑 **Password Storage** | bcrypt hashing | Salted hashes — never plain-text |
| ✅ **Input Validation** | Server-side | Email, mobile (Indian 10-digit), password strength, name |
| 🚫 **Rate Limiting** | 5 attempts → 15-min lockout | Per-account + admin tracking (SQLite-backed) |
| ⏱️ **Session Timeout** | Auto-logout | 5 mins CLI, 24h JWT with refresh tokens |
| 🔐 **JWT Auth** | HS256/RS256 with expiry | Access (15min) + Refresh (7d) tokens |
| 🛡️ **CSP Nonces** | Per-request | Cryptographically random nonces for script/style |
| 📝 **Audit Logging** | Immutable append-only | Admin actions logged with actor, target, timestamp |
| 🔔 **Notifications** | In-app real-time | Deposit, withdraw, transfer, loan, account alerts |
| 💾 **SQLite WAL** | Write-Ahead Logging | Concurrent reads, crash-safe writes |
| 🔄 **Token Invalidation** | Version-based | Password change invalidates all existing JWTs |

### 🏷️ Transaction Categories

13 predefined categories available across all interfaces:

| # | Category | # | Category | # | Category |
|---|----------|---|----------|---|----------|
| 1 | General | 6 | Entertainment | 11 | Investment |
| 2 | Food & Dining | 7 | Health | 12 | Rent |
| 3 | Transport | 8 | Education | 13 | Other |
| 4 | Shopping | 9 | Salary | | |
| 5 | Bills & Utilities | 10 | Savings | | |

---

## 📖 API Reference

The FastAPI REST API is fully documented with Swagger UI. Start the API server and visit:

**http://localhost:8000/docs**

### Authentication

All protected endpoints require a `Bearer` token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

### Endpoint Overview

**Auth:**
- `POST /api/auth/login` — Customer login → JWT
- `POST /api/auth/register` — Register new account
- `POST /api/auth/admin-login` — Admin login → JWT
- `POST /api/auth/refresh` — Refresh access token

**Customer Account:**
- `GET /api/account/profile` — View profile
- `PUT /api/account/profile` — Update profile
- `POST /api/account/change-password` — Change password
- `POST /api/account/close` — Close account

**Customer Transactions:**
- `GET /api/account/balance` — Check balance
- `POST /api/account/deposit` — Deposit
- `POST /api/account/withdraw` — Withdraw
- `POST /api/account/transfer` — Transfer funds
- `GET /api/account/statements` — Full statement
- `GET /api/account/statements/mini` — Last 5 transactions
- `GET /api/account/export-csv` — Download CSV
- `POST /api/account/apply-interest` — Apply interest

**Savings Goals:**
- `GET /api/savings` — List goals with summary
- `POST /api/savings` — Create goal
- `PUT /api/savings/{goal_id}` — Update goal
- `POST /api/savings/{goal_id}/contribute` — Contribute to goal
- `DELETE /api/savings/{goal_id}` — Delete goal

**Loans:**
- `GET /api/loans` — List customer loans
- `POST /api/loans/apply` — Apply for loan
- `GET /api/loans/{loan_id}` — Loan detail
- `POST /api/loans/{loan_id}/pay-emi` — Pay EMI

**Admin:**
- `GET /api/admin/accounts` — List all accounts
- `GET /api/admin/accounts/search?q=` — Search accounts
- `POST /api/admin/accounts/{no}/freeze` — Freeze
- `POST /api/admin/accounts/{no}/unfreeze` — Unfreeze
- `DELETE /api/admin/accounts/{no}` — Delete
- `GET /api/admin/statistics` — Bank statistics
- `GET /api/admin/transactions?account=` — Filtered transactions
- `PUT /api/admin/password` — Change admin password
- `GET /api/admin/loans` — List all loans
- `POST /api/admin/loans/{id}/approve` — Approve loan
- `POST /api/admin/loans/{id}/reject` — Reject loan

**Utility:**
- `GET /api/categories` — List transaction categories
- `GET /api/health` — Health check
- `GET /api/notifications` — Customer notifications
- `GET /api/notifications/unread-count` — Unread count

**V2 API** (ApiResponse envelope):
- All V2 endpoints mirror V1 under `/api/v2/` with standardized `{success, data, error}` envelope.

All endpoints return JSON responses with proper HTTP status codes (200, 400, 401, 403, 404, 422, 429).

---

## 🧪 Testing

```bash
# Run all 139 tests
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov --cov-report=term

# Generate HTML coverage report
python -m pytest tests/ --cov --cov-report=html
# → Open htmlcov/index.html in your browser

# Run specific test files
python -m pytest tests/test_api_integration.py -v
python -m pytest tests/test_htmx_integration.py -v
python -m pytest tests/test_services.py -v
```

### Test Suite

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_smoke.py` | 6 | Module import verification |
| `test_utils.py` | 29 | Validation, hashing, ID generators, formatting |
| `test_features.py` | 23 | Rate limiting, CSV export, interest, categories |
| `test_services.py` | 20 | Service layer unit tests with fake repositories |
| `test_integration.py` | 15 | Container, repository, and service integration |
| `test_property_based.py` | 5 | Property-based tests with Hypothesis |
| `test_api_integration.py` | 35 | FastAPI TestClient integration tests |
| `test_htmx_integration.py` | 6 | Flask test client HTMX integration tests |

All **139 tests pass** with 100% pass rate.

---

## 📁 Project Structure

```
union-bank/
│
├── 🏛️ DOMAIN LAYER
│   └── domain/
│       └── entities.py          # Pure domain entities (Account, Transaction, Loan, etc.)
│
├── 📋 APPLICATION LAYER
│   └── application/
│       ├── interfaces.py        # Repository protocols (ABCs)
│       ├── services.py          # Business logic services (6 services)
│       └── notifications.py     # Notification service
│
├── 🔧 INFRASTRUCTURE LAYER
│   └── infrastructure/
│       ├── database.py          # SQLAlchemy engine, sessions, init_db()
│       ├── persistence.py       # ORM models (SQLAlchemy declarative)
│       ├── repositories.py      # 10 SQLAlchemy repository implementations
│       ├── cache.py             # Redis cache layer
│       └── metrics.py           # Prometheus metrics middleware
│
├── 🔗 DEPENDENCY INJECTION
│   └── container.py             # DI container (wires repos → services → interfaces)
│
├── 🖥️ CLI INTERFACE
│   ├── main.py                  # CLI entry point
│   ├── bank.py                  # Customer menu system
│   ├── account.py               # Account operations (transactions, goals, loans)
│   └── admin.py                 # Admin panel
│
├── 🌐 WEB FRONTEND (Flask + HTMX)
│   ├── webapp.py                # Flask application (40+ routes)
│   ├── templates/               # Jinja2 HTML templates (28 files)
│   │   ├── base.html            # Base layout with Chart.js CDN
│   │   ├── index.html           # Landing page with live stats
│   │   ├── dashboard.html       # Customer dashboard with charts
│   │   ├── admin_account_detail.html  # Customer detail with charts
│   │   ├── admin_statistics.html      # Bank statistics with charts
│   │   ├── statement.html       # Transaction statement with chart
│   │   └── ...
│   └── static/
│       └── style.css            # 900+ lines of professional CSS
│
├── 🔌 REST API (FastAPI)
│   └── api/
│       ├── __init__.py          # FastAPI app with CORS, middleware
│       ├── models.py            # Pydantic request/response models
│       ├── common.py            # Shared auth dependencies
│       └── v2.py                # V2 API with ApiResponse envelope
│
├── 🛠️ UTILITIES
│   └── utils/
│       ├── auth.py              # Password hashing, JWT, rate limiting
│       ├── formatting.py        # Currency, ID generation, CSV export
│       ├── validation.py        # Email, phone, password, name validation
│       ├── file_io.py           # Legacy JSON helpers (migration scripts only)
│       └── savings.py           # Legacy goal helpers (migration scripts only)
│
├── 🗃️ DATABASE
│   ├── config.py                # Centralized configuration
│   ├── database.py              # Legacy DB init (compatibility)
│   ├── seed_data.py             # Generate 5,000 sample accounts
│   └── alembic/                 # Database migrations
│       ├── env.py               # Alembic environment config
│       └── versions/            # Migration scripts
│
├── 🧪 TESTS
│   ├── tests/
│   │   ├── conftest.py          # Pytest fixtures, fresh DB setup
│   │   ├── fakes.py             # Fake repository implementations
│   │   ├── test_smoke.py        # 6 import tests
│   │   ├── test_utils.py        # 29 unit tests
│   │   ├── test_features.py     # 23 feature tests
│   │   ├── test_services.py     # 20 service tests
│   │   ├── test_integration.py  # 15 integration tests
│   │   ├── test_property_based.py  # 5 property-based tests
│   │   ├── test_api_integration.py # 35 API integration tests
│   │   └── test_htmx_integration.py # 6 HTMX integration tests
│   └── ...
│
├── 🐳 DOCKER
│   ├── Dockerfile               # Multi-stage build (web/api/dev)
│   ├── docker-compose.yml       # Orchestration (web + api + redis)
│   ├── docker-compose.prod.yml  # Production overrides
│   └── Makefile                 # Docker convenience commands
│
├── 📊 OBSERVABILITY
│   ├── logger.py                # Structured logging (file + console)
│   └── infrastructure/
│       ├── metrics.py           # Prometheus metrics middleware
│       └── cache.py             # Redis cache integration
│
├── 📄 DOCUMENTATION
│   ├── README.md                # This file
│   ├── PROJECT_OVERVIEW.md      # Comprehensive architecture document
│   ├── CHANGELOG.md             # Version history
│   └── docs/                    # Architecture docs
│       ├── architecture.md
│       ├── routes.md
│       ├── api-map.md
│       ├── database-map.md
│       └── dependency-graph.md
│
├── ⚙️ CONFIGURATION
│   ├── requirements.txt         # Python dependencies
│   ├── pyproject.toml           # Project metadata & pytest config
│   ├── .env.example             # Environment variable template
│   ├── .gitignore
│   ├── .pre-commit-config.yaml
│   └── .github/workflows/       # GitHub Actions CI/CD
│
└── 🚀 SCRIPTS
    ├── start.bat                # Windows one-click launcher
    ├── test.bat                 # Windows one-click test runner
    └── scripts/
        ├── docker-entrypoint.sh # Docker startup script
        └── migrate_json_to_sqlite.py  # JSON → SQLite migration
```

---

## 🛠 Technology Stack

### Core
| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10+ | Core runtime |
| bcrypt | 4.1+ | Password hashing |
| colorama | 0.4+ | Terminal colors (CLI) |

### Web Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| Flask | 3.1+ | Web framework |
| Flask-WTF | 1.2+ | CSRF protection |
| Chart.js | 4.4+ | Interactive charts & graphs |
| Jinja2 | (built-in) | Template engine |
| HTMX | — | Partial page updates |

### REST API
| Technology | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.135+ | REST API framework |
| Uvicorn | 0.32+ | ASGI server |
| PyJWT | 2.9+ | JWT token auth |
| Pydantic | (built-in) | Request/response validation |
| Swagger UI | (built-in) | Interactive API docs |

### Data & Storage
| Technology | Purpose |
|-----------|---------|
| SQLite 3 | ACID database (WAL mode, foreign keys) |
| SQLAlchemy 2.0+ | ORM with connection pooling |
| Alembic | Database migrations |
| Redis | Optional caching layer |

### Docker & DevOps
| Technology | Purpose |
|-----------|---------|
| Docker | Containerization (multi-stage build) |
| Docker Compose | Service orchestration |
| Gunicorn | Production WSGI server |
| GitHub Actions | CI/CD pipeline |

### Testing & Quality
| Technology | Purpose |
|-----------|---------|
| pytest | Test framework |
| pytest-cov | Coverage reporting |
| Hypothesis | Property-based testing |
| Ruff | Linting & formatting |

---

## 📝 Logging System

| Level | File (`data/bank.log`) | Console | Purpose |
|-------|----------------------|---------|---------|
| **DEBUG** | ✅ | ❌ | Internal flow (account saves) |
| **INFO** | ✅ | ❌ | Normal operations (login, deposit, transfer) |
| **WARNING** | ✅ | ✅ | Suspicious events (wrong password, frozen account) |
| **ERROR** | ✅ | ✅ | Unexpected failures |
| **CRITICAL** | ✅ | ✅ | Admin actions (freeze, delete, close account) |

Log format: `[2026-06-02 14:30:22]  INFO      New account registered -> Acc:8352836722  Name:John`

---

## 📊 Current Stats

| Metric | Value |
|--------|-------|
| **Python Files** | 30+ (domain, app, infra, CLI, web, API, utils) |
| **HTML Templates** | 28 |
| **CSS Lines** | 900+ |
| **API Endpoints** | 40+ |
| **Total Tests** | 139 |
| **Test Pass Rate** | 100% |
| **Seed Data** | 5,000 accounts, 70,000 transactions |
| **Security Layers** | 10 (bcrypt, validation, rate limit, JWT, CSP, audit, notifications, WAL, token invalidation, HTTPS-ready) |
| **Dependencies** | 12 (bcrypt, colorama, fastapi, flask, flask-wtf, fpdf2, PyJWT, sqlalchemy, uvicorn, pytest, pytest-cov, slowapi) |

---

## 🤝 Contributing

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

Please ensure:
- ✅ All **139 tests pass** (`pytest tests/ -v`)
- ✅ **New features have tests** covering happy path + edge cases
- ✅ **No lint errors** (`ruff check .`)
- ✅ Code follows existing **project conventions**
- ✅ **All database interactions** go through Repository/Service layer

---

## 📄 License

This project is licensed under the **MIT License**.

---

<p align="center">
  <sub>Made with ❤️ — Python, Flask, FastAPI, SQLAlchemy, and Chart.js</sub>
  <br>
  <sub>Union Bank Management System v2.0.0</sub>
</p>

---

## 📖 Documentation

For comprehensive codebase intelligence and architecture documentation, see the [`docs/`](docs/) folder:

| File | Description |
|------|-------------|
| [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md) | Complete architecture document — every module, layer, entity, API, CLI, HTMX flow, database schema, logging, monitoring, testing strategy, deployment, and future roadmap |
| [`memory.md`](memory.md) | Complete project brain — purpose, tech stack, features, data flow |
| [`docs/architecture.md`](docs/architecture.md) | System architecture diagram + layered breakdown |
| [`docs/routes.md`](docs/routes.md) | Full route table (Flask web + FastAPI REST) |
| [`docs/api-map.md`](docs/api-map.md) | Complete API inventory with endpoints, inputs, outputs |
| [`docs/database-map.md`](docs/database-map.md) | Database schema, entities, fields, relationships |
| [`docs/dependency-graph.md`](docs/dependency-graph.md) | Module dependency map + critical files |
