<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.1%2B-000?logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/FastAPI-0.135%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Chart.js-4.4%2B-FF6384?logo=chartdotjs&logoColor=white" alt="Chart.js">
  <a href="https://github.com/themanoj-025/UNION-BANK-/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/UNION-BANK-/ci.yml?branch=main&label=CI&logo=github" alt="CI"></a>
  <img src="https://img.shields.io/badge/tests-58%20passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <a href="https://github.com/themanoj-025/UNION-BANK-/security/dependabot"><img src="https://img.shields.io/badge/dependabot-enabled-025E8C?logo=dependabot" alt="Dependabot"></a>
  <img src="https://img.shields.io/badge/database-JSON-orange" alt="JSON Storage">
  <img src="https://img.shields.io/badge/seed_data-5,000%20accounts-success" alt="Seed Data">
</p>

<h1 align="center">
  🏦 Union Bank Management System
</h1>

<p align="center">
  <strong>A full-stack banking application</strong> — <em>CLI · Flask Web UI · FastAPI REST API</em>
</p>

<p align="center">
  <i>Register accounts · Deposit & withdraw · Transfer funds · Admin panel · Rate limiting · CSV export · Interest calculation · Interactive charts · REST API with JWT auth</i>
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

### Default Credentials

| Role | Username | Password |
|------|----------|----------|
| 👤 **Customer** | (any account number from `data/accounts.json`) | `Seed@123` *(if seeded)* |
| 🛡️ **Admin** | `admin` | `admin123` |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        UNION BANK SYSTEM                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   CLI    │    │  Flask Web   │    │  FastAPI     │              │
│  │  (main)  │    │  (webapp)    │    │  REST API    │              │
│  │          │    │              │    │              │              │
│  │ Terminal │    │  HTML/CSS/JS │    │  JWT Auth    │              │
│  │ Menus    │    │  Chart.js    │    │  Swagger     │              │
│  └────┬─────┘    └──────┬───────┘    └──────┬────────┘              │
│       │                 │                   │                       │
│       └─────────────────┼───────────────────┘                       │
│                         │                                           │
│            ┌────────────▼────────────┐                              │
│            │   Business Logic        │                              │
│            │   (bank.py, account.py, │                              │
│            │    admin.py, utils.py)  │                              │
│            └────────────┬────────────┘                              │
│                         │                                           │
│            ┌────────────▼────────────┐                              │
│            │   Data Layer            │                              │
│            │   JSON files            │                              │
│            │   (atomic writes,       │                              │
│            │    auto backups)        │                              │
│            └─────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input → [CLI / Web / API] → Bank/Admin/Account methods
                                    ↓
                              utils.py (validation, hashing)
                                    ↓
                              load_json / save_json (atomic writes)
                                    ↓
                              data/*.json files (with .bak backups)
                                    ↓
                              logger.py (audit trail to bank.log)
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
| **Session Timeout** | ✅ 5 mins | ❌ (browser session) | ✅ 24h JWT expiry |

### 🛡️ Admin Features

| Feature | 🖥️ CLI | 🌐 Web UI | 🔌 REST API |
|---------|---------|-----------|-------------|
| **Admin Login** | ✅ Password mask | ✅ Rate-limited | ✅ `POST /api/auth/admin-login` (JWT) |
| **View All Accounts** | ✅ Table w/ status | ✅ Table w/ links | ✅ `GET /api/admin/accounts` |
| **Account Detail** | ❌ | ✅ Full profile + charts + transactions | ❌ (use search or list) |
| **Search Account** | ✅ By number/name | ✅ Search form | ✅ `GET /api/admin/accounts/search?q=` |
| **Freeze / Unfreeze** | ✅ With confirm | ✅ Confirmation | ✅ `POST /api/admin/accounts/{no}/freeze` |
| **Delete Account** | ✅ Permanent | ✅ Type DELETE | ✅ `DELETE /api/admin/accounts/{no}` |
| **Bank Statistics** | ✅ Numbers only | ✅ Stats + charts | ✅ `GET /api/admin/statistics` |
| **View Transactions** | ✅ Filtered | ✅ Filtered table | ✅ `GET /api/admin/transactions` |
| **Change Admin Password** | ✅ Verified | ✅ Strength check | ✅ `PUT /api/admin/password` |

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
| 🚫 **Rate Limiting** | 5 attempts → 15-min lockout | Per-account + admin tracking |
| ⏱️ **Session Timeout** | Auto-logout | 5 mins CLI, 24h JWT |
| 💾 **Atomic Writes** | Temp file + `os.replace()` | No JSON corruption |
| 🔄 **Auto Backup** | `.bak` before every save | Corruption recovery |
| 🔐 **JWT Auth** | HS256 with 24h expiry | Customer + admin role separation |
| 🛠️ **CSV BOM** | UTF-8 with BOM | Excel-compatible ₹ symbols |
| 📝 **Audit Logging** | 5 log levels | File DEBUG+, console WARNING+ |

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

**Admin:**
- `GET /api/admin/accounts` — List all accounts
- `GET /api/admin/accounts/search?q=` — Search accounts
- `POST /api/admin/accounts/{no}/freeze` — Freeze
- `POST /api/admin/accounts/{no}/unfreeze` — Unfreeze
- `DELETE /api/admin/accounts/{no}` — Delete
- `GET /api/admin/statistics` — Bank statistics
- `GET /api/admin/transactions?account=` — Filtered transactions
- `PUT /api/admin/password` — Change admin password

**Utility:**
- `GET /api/categories` — List transaction categories
- `GET /api/health` — Health check

All endpoints return JSON responses with proper HTTP status codes (200, 400, 401, 403, 404, 429).

---

## 🧪 Testing

```bash
# Run all 58 tests
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov --cov-report=term

# Generate HTML coverage report
python -m pytest tests/ --cov --cov-report=html
# → Open htmlcov/index.html in your browser
```

### Test Suite

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_smoke.py` | 6 | Module import verification |
| `test_utils.py` | 29 | Validation, hashing, JSON I/O, generators |
| `test_features.py` | 23 | Rate limiting, CSV export, interest, categories, session mgmt |

All **58 tests pass** with 100% pass rate.

---

## 📁 Project Structure

```
union-bank/
│
├── 🖥️ APPLICATION CORE
│   ├── main.py              # CLI entry point & main menu loop
│   ├── bank.py              # Bank class: registration, login, customer dashboards
│   ├── account.py           # Account model: transactions, statements, profile, export
│   ├── admin.py             # Admin panel: manage, search, freeze, delete, statistics
│   ├── utils.py             # Core utilities: JSON I/O, validation, hashing, rate limiting
│   ├── ui.py                # Terminal UI: colorama colors, styled helpers
│   └── logger.py            # Centralized logging (file + console)
│
├── 🌐 WEB FRONTEND (Flask)
│   ├── webapp.py            # Flask application (26 routes)
│   ├── templates/           # Jinja2 HTML templates (21 files)
│   │   ├── base.html        # Base layout with Chart.js CDN
│   │   ├── index.html       # Redesigned landing page with live stats
│   │   ├── dashboard.html   # Customer dashboard with charts
│   │   ├── admin_account_detail.html  # Customer detail page with charts
│   │   ├── admin_statistics.html      # Bank statistics with charts
│   │   ├── statement.html   # Transaction statement with balance chart
│   │   └── ...              # (login, register, deposit, withdraw, etc.)
│   └── static/
│       └── style.css        # 900+ lines of professional CSS
│
├── 🔌 REST API (FastAPI)
│   └── api.py               # FastAPI application (24 endpoints, JWT auth)
│
├── 📦 DATA
│   ├── data/                 # Runtime data (auto-created, gitignored)
│   │   ├── accounts.json    # Customer account records
│   │   ├── transactions.json# Transaction history
│   │   ├── admin.json       # Admin credentials (bcrypt hashed)
│   │   ├── login_attempts.json # Rate limiting tracker
│   │   └── bank.log         # Audit log
│   └── seed_data.py         # Generate 5,000 sample accounts
│
├── 🧪 TESTS
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_smoke.py    # 6 import tests
│   │   ├── test_utils.py    # 29 unit tests
│   │   └── test_features.py # 23 feature tests
│   └── ...
│
├── ⚙️ CONFIGURATION
│   ├── requirements.txt     # Python dependencies
│   ├── pyproject.toml       # Project metadata & pytest config
│   ├── .gitignore
│   ├── .pre-commit-config.yaml
│   └── .github/workflows/ci.yml  # GitHub Actions CI
│
├── 🚀 SCRIPTS
│   ├── start.bat            # Windows one-click launcher
│   └── test.bat             # Windows one-click test runner
│
└── 📄 README.md             # This file
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
| Chart.js | 4.4+ | Interactive charts & graphs |
| Jinja2 | (built-in) | Template engine |
| CSS3 | — | Responsive design |

### REST API
| Technology | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.135+ | REST API framework |
| Uvicorn | 0.44+ | ASGI server |
| PyJWT | 2.12+ | JWT token auth |
| Pydantic | (built-in) | Request/response validation |
| Swagger UI | (built-in) | Interactive API docs |

### Data & Storage
| Technology | Purpose |
|-----------|---------|
| JSON files | Human-readable persistence |
| Atomic writes | Corruption prevention |
| Auto `.bak` backups | Data recovery |

### Testing & CI
| Technology | Purpose |
|-----------|---------|
| pytest | Test framework |
| pytest-cov | Coverage reporting |
| Ruff | Linting & formatting |
| GitHub Actions | CI/CD pipeline |

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
| **Python Files** | 9 (core) + 4 (tests) + 3 (web) |
| **HTML Templates** | 21 |
| **CSS Lines** | 900+ |
| **API Endpoints** | 24 |
| **Total Tests** | 58 |
| **Test Pass Rate** | 100% |
| **Seed Data** | 5,000 accounts, 70,000 transactions |
| **Security Layers** | 9 (bcrypt, validation, rate limit, session, JWT, atomic writes, backup, recovery, logging) |
| **Dependencies** | 8 (bcrypt, colorama, flask, fastapi, uvicorn, PyJWT, pytest, pytest-cov) |
| **Default Admin Password** | `admin123` |
| **Default Customer Password** | `Seed@123` |

---

## 🤝 Contributing

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

Please ensure:
- ✅ All **58 tests pass** (`pytest tests/ -v`)
- ✅ **New features have tests** covering happy path + edge cases
- ✅ **No lint errors** (`ruff check .`)
- ✅ Code follows existing **project conventions**

---

## 📄 License

This project is licensed under the **MIT License**.

---

<p align="center">
  <sub>Made with ❤️ — Python, Flask, FastAPI, and Chart.js</sub>
  <br>
  <sub>Union Bank Management System v2.0.0</sub>
</p>

---

## 📖 Documentation

For comprehensive codebase intelligence and architecture documentation, see the [`docs/`](docs/) folder:

| File | Description |
|------|-------------|
| [`memory.md`](memory.md) | Complete project brain — purpose, tech stack, features, data flow |
| [`docs/architecture.md`](docs/architecture.md) | System architecture diagram + layered breakdown |
| [`docs/routes.md`](docs/routes.md) | Full route table (Flask web + FastAPI REST) |
| [`docs/api-map.md`](docs/api-map.md) | Complete API inventory with endpoints, inputs, outputs |
| [`docs/database-map.md`](docs/database-map.md) | Database schema, entities, fields, relationships |
| [`docs/dependency-graph.md`](docs/dependency-graph.md) | Module dependency map + critical files |
