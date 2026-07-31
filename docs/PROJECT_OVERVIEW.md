# UNION-BANK- — Project Overview

## 1. Project Title
**Union Bank Management System** — A multi-interface banking application with CLI (console), Flask web frontend with HTMX, and FastAPI REST API for managing customer accounts, transactions, loans, savings goals, and administrative controls.

## 2. Executive Summary
Union Bank Management System is a feature-rich banking application that provides three interfaces: a rich terminal-based CLI with colored output, a modern Flask web application with Chart.js visualizations and dark/light theme, and a FastAPI REST API with OpenAPI documentation. It supports the full customer banking lifecycle — account registration, deposits, withdrawals, fund transfers, transaction history, CSV export, monthly interest calculation, savings goals, and loan management — alongside an admin panel for account oversight, freeze/unfreeze, deletion, statistics, loan approval, and PDF report generation.

The system uses **SQLite** as its primary database with **SQLAlchemy ORM**, a **dependency injection container**, a **repository pattern** for data access, and a **service layer** for business logic. All three interfaces (CLI, Web, API) share the same data layer, ensuring consistency across all access points.

## 3. Problem Statement
Small financial institutions and educational projects need a comprehensive banking system that demonstrates core banking operations (account management, transactions, admin controls) across multiple interface types (CLI, web, API) while maintaining data integrity through ACID transactions, proper layering, and dependency injection.

## 4. Objectives
- Provide complete banking operations: registration, deposits, withdrawals, transfers, loans
- Support multiple interfaces (CLI, web, API) sharing the same business logic and data layer
- Enable administrative oversight (account freeze/unfreeze, deletion, statistics, loan approval)
- Offer financial planning tools (savings goals, interest calculation, loan management)
- Generate reports (CSV export, PDF bank statistics)
- Ensure data integrity with ACID SQLite transactions, WAL mode, and foreign keys
- Include security features (rate limiting, password hashing, JWT auth, CSP nonces, audit logging)
- Follow clean architecture principles (Domain → Application → Infrastructure)

## 5. Key Features
- **Account management:** Registration, profile update, password change, account closure
- **Transactions:** Deposit, withdraw, transfer between accounts with categorized tracking
- **Transaction history:** Mini statement (last 5), full statement, CSV export, paginated queries
- **Interest calculation:** Monthly interest at 3.5% p.a.
- **Savings goals:** Create, edit, delete goals; contribute from balance; progress tracking with visual bars
- **Loan management:** Apply, approve/reject, EMI payments, loan status tracking
- **Admin panel:** View all accounts, search, freeze/unfreeze, delete accounts, transaction overview
- **Admin statistics:** Account status breakdown, financial summary, category analysis with charts
- **PDF report generation:** Bank-wide statistics report with tables and bar charts
- **In-app notifications:** Real-time alerts for deposits, withdrawals, transfers, loans, account changes
- **Audit logging:** Immutable append-only log of all admin actions
- **Web charts:** Category doughnut chart, transaction type bar chart, balance trend line chart
- **Dark/light theme:** Theme toggle with persistent preference
- **Rate limiting:** Account lockout after 5 failed attempts (15-minute cooldown)
- **Session management:** Automatic timeout after 5 minutes of inactivity
- **Data integrity:** SQLite WAL mode, foreign keys, connection pooling, ACID transactions

## 6. System Architecture

```
User Access Options
    ├── CLI (main.py → bank.py / account.py / admin.py)
    │     └── Console menu system (rich colored output)
    │
    ├── Flask Web (webapp.py) + HTMX
    │     └── Jinja2 templates + Chart.js visualizations + partial updates
    │
    └── FastAPI (api/) + V2 envelope
          └── REST endpoints + Swagger docs + JWT auth
                │
                ▼
          Application Services (application/services.py)
            ├── AuthService          — Login, register, JWT, rate limiting
            ├── AccountService       — Profile, password, balance
            ├── TransactionService   — Deposit, withdraw, transfer, interest
            ├── AdminService         — Freeze, delete, statistics, audit
            ├── LoanService          — Apply, approve, reject, EMI
            └── SavingsGoalService   — CRUD, contribute, progress
                │
                ▼
          Repository Layer (infrastructure/repositories.py)
            ├── AccountRepository
            ├── TransactionRepository
            ├── AdminRepository
            ├── SavingsGoalRepository
            ├── LoanRepository
            ├── LoginAttemptRepository
            ├── TokenVersionRepository
            ├── NotificationRepository
            ├── NotificationPreferenceRepository
            └── AuditLogRepository
                │
                ▼
          SQLite Database (union_bank.db)
            ├── accounts            — Customer account records
            ├── transactions        — Transaction history
            ├── admin_users         — Admin credentials
            ├── login_attempts      — Rate limiting tracker
            ├── savings_goals       — Customer savings goals
            ├── loans               — Loan applications & status
            ├── notifications       — In-app notification alerts
            ├── notification_preferences — Per-account notification settings
            ├── token_versions      — JWT token invalidation
            └── audit_log           — Admin action audit trail
```

## 7. Tech Stack
| Category | Technology |
|---|---|
| **Language** | Python 3.10+ |
| **Web Framework** | Flask 3.1+ with HTMX |
| **API Framework** | FastAPI 0.135+ |
| **CLI** | Terminal menu system (custom) |
| **Auth** | bcrypt (password hashing), PyJWT (API tokens, HS256/RS256) |
| **Database** | SQLite 3 with WAL mode |
| **ORM** | SQLAlchemy 2.0+ |
| **Migrations** | Alembic |
| **DI Container** | Custom container (container.py) |
| **Visualization** | Chart.js 4.4+ (web), CSS (styled tables) |
| **PDF Generation** | fpdf2 |
| **CSV Export** | Python csv module |
| **Validation** | Custom validators (regex-based) + Pydantic |
| **Testing** | pytest + Hypothesis |
| **Caching** | Redis (optional) |
| **Deployment** | Docker (multi-stage), Docker Compose, Gunicorn/Uvicorn |
| **Observability** | Structured logging, Prometheus metrics |

## 8. Folder Structure
```
UNION-BANK-/
├── domain/                      # Domain Layer
│   └── entities.py              # Pure entities (Account, Transaction, Loan, etc.)
│
├── application/                 # Application Layer
│   ├── interfaces.py            # Repository protocols (ABCs)
│   ├── services.py              # Business logic (6 service classes)
│   └── notifications.py         # Notification service
│
├── infrastructure/              # Infrastructure Layer
│   ├── database.py              # SQLAlchemy engine, sessions, init_db()
│   ├── persistence.py           # ORM models (SQLAlchemy declarative)
│   ├── repositories.py          # 10 SQLAlchemy repository implementations
│   ├── cache.py                 # Redis cache layer
│   └── metrics.py               # Prometheus metrics middleware
│
├── container.py                 # Dependency Injection Container
│
├── main.py                      # CLI entry point
├── bank.py                      # Customer menu system
├── account.py                   # Account operations
├── admin.py                     # Admin panel
│
├── webapp.py                    # Flask web application (40+ routes)
├── api/                         # FastAPI REST API
│   ├── __init__.py              # App with CORS, middleware
│   ├── models.py                # Pydantic models
│   ├── common.py                # Shared auth dependencies
│   └── v2.py                    # V2 API with ApiResponse envelope
│
├── utils/                       # Utilities
│   ├── auth.py                  # Password hashing, JWT, rate limiting
│   ├── formatting.py            # Currency, ID generation, CSV export
│   ├── validation.py            # Email, phone, password, name validation
│   ├── file_io.py               # Legacy JSON helpers (migration scripts only)
│   └── savings.py               # Legacy goal helpers (migration scripts only)
│
├── config.py                    # Centralized configuration
├── database.py                  # Legacy DB init (compatibility)
├── logger.py                    # Structured logging
├── seed_data.py                 # Generate sample data
│
├── templates/                   # Jinja2 HTML templates (28 files)
├── static/style.css             # 900+ lines of CSS
│
├── tests/                       # Test suite (139 tests)
│   ├── conftest.py              # Pytest fixtures
│   ├── fakes.py                 # Fake repositories for unit testing
│   ├── test_smoke.py            # Import verification
│   ├── test_utils.py            # Utility unit tests
│   ├── test_features.py         # Feature tests
│   ├── test_services.py         # Service unit tests
│   ├── test_integration.py      # Repository/service integration
│   ├── test_property_based.py   # Property-based tests
│   ├── test_api_integration.py  # FastAPI TestClient tests
│   └── test_htmx_integration.py # Flask HTMX integration tests
│
├── alembic/                     # Database migrations
├── scripts/                     # Docker entrypoint, JSON migration
├── Dockerfile                   # Multi-stage build
├── docker-compose.yml           # Service orchestration
├── Makefile                     # Docker convenience commands
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Project metadata + pytest config
└── .env.example                 # Environment variable template
```

## 9. Module Overview

### 9.1 Domain Layer (`domain/entities.py`)
Pure domain entities with no framework or database dependencies. All monetary values use `Decimal` — never `float` — to avoid precision loss. Timestamps are timezone-aware `datetime` objects.

**Entities:**
- `Account` — Customer account with balance, status (active/frozen/closed), computed properties (`can_transact`, `status`)
- `Transaction` — Append-only log of all account activity with type enum (DEPOSIT, WITHDRAW, TRANSFER_OUT, TRANSFER_IN, INTEREST, LOAN_DISBURSEMENT, LOAN_REPAYMENT)
- `SavingsGoal` — Customer savings goal with progress tracking (`progress_pct`, `remaining`)
- `Loan` — Loan application with EMI calculation, status tracking, progress monitoring
- `AdminUser` — Admin user with role-based access
- `LoginAttempt` — Rate limiting tracker with lockout computation
- `TokenVersion` — JWT token invalidation via version tracking
- `Notification` — In-app notification with type and read status
- `NotificationPreference` — Per-account notification channel preferences
- `ServiceResult` / `TransferResult` — Standardized result types for all service operations

### 9.2 Application Layer (`application/`)

**Interfaces (`interfaces.py`):**
Repository protocols (ABCs) that define the contract between application and infrastructure layers. No concrete DB code lives here. Includes `KeysetPage` for cursor-based pagination.

**Services (`services.py`):**
Six service classes implementing business logic:

1. **`AuthService`** — Customer registration, customer login, admin login, rate limiting, JWT token management
2. **`AccountService`** — Profile management, password changes, account closure, balance queries
3. **`TransactionService`** — Deposit, withdraw, transfer (atomic), interest calculation, statements, pagination
4. **`AdminService`** — Account list/search, freeze/unfreeze, delete, statistics, audit logging
5. **`LoanService`** — Loan application, approval (with fund disbursement), rejection, EMI payment, loan statistics
6. **`SavingsGoalService`** — Goal CRUD, contribution (with balance deduction), deletion (with refund)

**Notifications (`notifications.py`):**
`NotificationService` — In-app notification management for all transaction types, account changes, and loan events.

### 9.3 Infrastructure Layer (`infrastructure/`)

**Database (`database.py`):**
- SQLAlchemy engine with lazy creation (picks up current `DATA_DIR`)
- Thread-local session management
- `atomic_session()` context manager for ACID transactions
- WAL mode, foreign keys, busy timeout pragmas
- Connection pooling (pool_size=5, max_overflow=10)

**Persistence (`persistence.py`):**
SQLAlchemy ORM models mapping to SQLite tables:
- `AccountModel`, `TransactionModel`, `AdminModel`, `SavingsGoalModel`, `LoanModel`
- `LoginAttemptModel`, `TokenVersionModel`, `AuditLogModel`
- `NotificationModel`, `NotificationPreferenceModel`

**Repositories (`repositories.py`):**
10 SQLAlchemy repository implementations:
1. `SqlAlchemyAccountRepository` — CRUD, search, balance queries, status counts
2. `SqlAlchemyTransactionRepository` — CRUD, pagination (offset + keyset), category totals
3. `SqlAlchemyAdminRepository` — CRUD, password updates
4. `SqlAlchemySavingsGoalRepository` — CRUD, contribution tracking
5. `SqlAlchemyLoanRepository` — CRUD, status filtering, financial totals
6. `SqlAlchemyLoginAttemptRepository` — Rate limiting, lockout management
7. `SqlAlchemyTokenVersionRepository` — JWT version tracking
8. `SqlAlchemyNotificationRepository` — CRUD, read tracking
9. `SqlAlchemyNotificationPreferenceRepository` — Per-account preferences
10. `SqlAlchemyAuditLogRepository` — Append-only audit trail

### 9.4 Dependency Injection Container (`container.py`)
Wires together all dependencies using factory methods. All dependencies flow inward: interfaces → application services → infrastructure repos.

**Container methods:**
- `account_repo()`, `transaction_repo()`, `admin_repo()`, etc. — Repository factories
- `auth_service()`, `account_service()`, `transaction_service()`, etc. — Service factories
- `notification_service()`, `notification_sender()` — Notification infrastructure
- `get_session()`, `close_session()` — Session management
- `reset_container()` — Testing support (closes sessions, disposes engine)

### 9.5 CLI Interface (`main.py`, `bank.py`, `account.py`, `admin.py`)
Terminal-based menu system with colored output (colorama).

- `main.py` — Entry point, main menu loop
- `bank.py` — Customer login, registration, dashboard, transaction menus
- `account.py` — Transaction operations, statements, profile, savings goals, loans
- `admin.py` — Admin login, account management, statistics, loan approval

### 9.6 Web Frontend (`webapp.py` + `templates/`)
Flask application with 40+ routes, HTMX partial updates, and Chart.js visualizations.

**Key features:**
- Session-based auth (customer + admin separate)
- HTMX partial rendering for balance refresh, search, notifications
- Chart.js dashboards (4 chart types across 4 pages)
- CSRF protection (Flask-WTF)
- CSP nonces (per-request cryptographic randomness)
- Security headers (X-Frame-Options, HSTS, etc.)
- Rate limiting (in-memory, per-endpoint, per-IP)
- PDF report generation (fpdf2)

### 9.7 REST API (`api/`)
FastAPI application with JWT authentication, Pydantic validation, and Swagger documentation.

- `api/__init__.py` — FastAPI app with CORS, middleware, route registration
- `api/models.py` — Pydantic request/response models
- `api/common.py` — Shared auth dependencies (JWT verification, role checking)
- `api/v2.py` — V2 API with standardized `ApiResponse` envelope (`{success, data, error}`)

## 10. Database Schema

### 10.1 Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `accounts` | Customer accounts | account_number (PK), name, balance, is_active, is_frozen |
| `transactions` | Transaction history | txn_id (PK), account_number (FK), type, amount, balance |
| `admin_users` | Admin credentials | id (PK), username (unique), password (bcrypt) |
| `login_attempts` | Rate limiting | key (PK), count, lockout_until |
| `savings_goals` | Customer goals | goal_id (PK), account_number (FK), target_amount, current_amount |
| `loans` | Loan applications | loan_id (PK), account_number (FK), principal_amount, status |
| `notifications` | In-app alerts | notif_id (PK), account_number (FK), type, title, is_read |
| `notification_preferences` | Notification settings | account_number (PK), in_app_enabled, email_enabled |
| `token_versions` | JWT invalidation | account_number (PK), version |
| `audit_log` | Admin audit trail | id (PK), actor, action, target, timestamp |

### 10.2 Relationships
- `accounts.account_number` ← `transactions.account_number` (one-to-many)
- `accounts.account_number` ← `savings_goals.account_number` (one-to-many)
- `accounts.account_number` ← `loans.account_number` (one-to-many)
- `accounts.account_number` ← `notifications.account_number` (one-to-many)
- `accounts.account_number` ← `notification_preferences.account_number` (one-to-one)
- `accounts.account_number` ← `token_versions.account_number` (one-to-one)

### 10.3 SQLite Configuration
- **WAL mode** — Concurrent reads, crash-safe writes
- **Foreign keys** — Enforced via `PRAGMA foreign_keys=ON`
- **Busy timeout** — 5 seconds (`PRAGMA busy_timeout=5000`)
- **Connection pooling** — pool_size=5, max_overflow=10, pool_pre_ping=True

## 11. API Overview

### FastAPI REST API — 40+ endpoints

**Auth:**
- `POST /api/auth/login` — Customer login → JWT (access + refresh)
- `POST /api/auth/register` — New account registration
- `POST /api/auth/admin-login` — Admin login → JWT
- `POST /api/auth/refresh` — Refresh access token

**Customer Account:**
- `GET /api/account/profile` — Get profile
- `PUT /api/account/profile` — Update profile
- `POST /api/account/change-password` — Change password
- `POST /api/account/close` — Close account

**Transactions:**
- `GET /api/account/balance` — Current balance
- `POST /api/account/deposit` — Deposit money
- `POST /api/account/withdraw` — Withdraw money
- `POST /api/account/transfer` — Transfer funds
- `GET /api/account/statements` — Full transaction history
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
- `POST /api/admin/accounts/{acc_no}/freeze` — Freeze
- `POST /api/admin/accounts/{acc_no}/unfreeze` — Unfreeze
- `DELETE /api/admin/accounts/{acc_no}` — Delete
- `GET /api/admin/statistics` — Bank statistics
- `GET /api/admin/transactions` — All transactions
- `PUT /api/admin/password` — Change admin password
- `GET /api/admin/loans` — List all loans
- `POST /api/admin/loans/{id}/approve` — Approve loan
- `POST /api/admin/loans/{id}/reject` — Reject loan

**Notifications:**
- `GET /api/notifications` — Customer notifications
- `GET /api/notifications/unread-count` — Unread count

**Utility:**
- `GET /api/categories` — List transaction categories
- `GET /api/health` — Health check

### Flask Web (webapp.py) — 40+ routes
Matching set of route handlers for the web interface, rendering Jinja2 templates with HTMX partial updates.

## 12. Authentication & Authorization
- **CLI:** Password verification via bcrypt, session timeout (5 minutes)
- **Flask Web:** Session-based auth (customer + admin separate), bcrypt verification
- **FastAPI:** JWT token-based (HS256 default, RS256 optional), access (15min) + refresh (7d) tokens
- **Rate limiting:** 5 failed attempts → 15-minute lockout (per account or admin username, SQLite-backed)
- **Token invalidation:** Version-based — password change increments token version, invalidating all existing JWTs
- **Roles:** Customer (self-service) and Admin (full system access)

## 13. Data Flow

1. **Registration flow:** User input → validate fields → hash password (bcrypt) → generate unique 10-digit account number → create Account entity → persist via AccountRepository → SQLite
2. **Deposit flow:** User enters amount + category → load account via AccountRepository → update balance → create Transaction entity → persist via TransactionRepository → commit atomically
3. **Transfer flow:** Validate recipient exists and is active → debit sender, credit recipient → create two Transaction entities (TRANSFER_OUT, TRANSFER_IN) → commit atomically
4. **Loan flow:** Validate account → calculate EMI → create Loan entity (PENDING) → admin approves → disburse funds → create LOAN_DISBURSEMENT transaction → update loan status (ACTIVE)
5. **Savings goal contribution:** Validate goal and balance → deduct from account → create TRANSFER_OUT transaction → update goal current_amount → commit atomically
6. **Rate limiting flow:** On failed login → load LoginAttempt via repository → increment count → if count >= 5, set lockout_until = now + 15 min → on success, reset count

## 14. Request Lifecycle

**CLI:** User input → main_menu() → Bank method → Service method → Repository → SQLite → display result

**Web:** HTTP request → Flask route → decorator (login_required/admin_required) → Service method → Repository → SQLite → render_template (or HTMX fragment)

**API:** HTTP request → FastAPI route → JWT dependency → Service method → Repository → SQLite → Pydantic response

## 15. Observability

### Structured Logging
- **Logger:** Custom logger in `logger.py` with timestamped entries
- **Levels:** DEBUG (file only), INFO (file only), WARNING (file + console), ERROR (file + console), CRITICAL (file + console)
- **Events logged:** Account registration, login success/failure, password changes, transactions, account closure, freeze/unfreeze, admin actions, loan operations

### Metrics
- **Prometheus middleware** in `infrastructure/metrics.py` — WSGI middleware for request metrics
- **Request ID tracking** — Unique request ID per request, propagated via X-Request-ID header

### Audit Logging
- **Immutable append-only** audit trail in SQLite
- **Captures:** Actor, action, target, details, IP address, reason, timestamp
- **Used for:** Freeze, unfreeze, delete, password changes, loan approve/reject

## 16. Testing Strategy

### Framework
- **pytest** with fixtures, parametrize, and markers
- **Hypothesis** for property-based testing
- **Coverage:** Target 80%+ with branch coverage

### Test Categories

| Category | Files | Count | Description |
|----------|-------|-------|-------------|
| Smoke | `test_smoke.py` | 6 | Module import verification |
| Unit | `test_utils.py` | 29 | Validation, hashing, ID generators, formatting |
| Feature | `test_features.py` | 23 | Rate limiting, CSV export, interest, categories |
| Service | `test_services.py` | 20 | Service layer with fake repositories |
| Integration | `test_integration.py` | 15 | Container, repository, service integration |
| Property | `test_property_based.py` | 5 | Property-based tests with Hypothesis |
| API | `test_api_integration.py` | 35 | FastAPI TestClient integration tests |
| HTMX | `test_htmx_integration.py` | 6 | Flask test client HTMX integration tests |
| **Total** | | **139** | **100% pass rate** |

### Test Infrastructure
- **Fresh DB per test** — Each test gets a temporary SQLite database
- **Fake repositories** — `tests/fakes.py` provides in-memory implementations for unit testing
- **DI container reset** — `reset_container()` ensures clean state between tests
- **Isolated sessions** — Thread-local sessions prevent cross-test contamination

## 17. Deployment

### Local Development
```bash
pip install -r requirements.txt
python main.py           # CLI
python webapp.py          # Web (port 5000)
uvicorn api:app --reload  # API (port 8000)
```

### Docker
```bash
docker compose up -d      # Web + API + Redis
make up                   # Same via Makefile
```

### Production
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Environment Variables
| Variable | Required | Purpose |
|----------|----------|---------|
| `JWT_SECRET` | Yes | JWT signing secret (32+ chars) |
| `FLASK_SECRET_KEY` | Yes | Flask session signing key |
| `UNION_BANK_DATA_DIR` | No | Custom data directory (default: `./data`) |
| `REDIS_URL` | No | Redis cache URL (optional) |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated allowed origins |

## 18. Migration Notes

### JSON → SQLite Migration (Completed)
The system was originally built with JSON file-based persistence. The migration to SQLite included:

1. **Schema design** — 10 tables with proper foreign keys and indexes
2. **Repository pattern** — 10 SQLAlchemy repositories replacing JSON read/write
3. **Service layer** — 6 services encapsulating all business logic
4. **DI container** — Wiring repositories → services → interfaces
5. **CLI migration** — All menu handlers now use container services
6. **Web migration** — All routes now use container services
7. **API migration** — All endpoints now use container services
8. **Savings goals** — Full migration from JSON to SQLite with service layer
9. **Test migration** — 139 tests with fresh SQLite databases per test

### Migration Script
`scripts/migrate_json_to_sqlite.py` — One-time script to migrate existing JSON data to SQLite.

## 19. Known Limitations
- **SQLite concurrent writes** — Single-writer; acceptable for this application's scale
- **No external monitoring** — Logs are file-based; no Prometheus/Grafana setup included
- **CORS wide open** — Default allows all origins; should be restricted in production
- **No HTTPS** — Must be terminated at reverse proxy level
- **Admin credentials** — Default admin (`admin`/`admin123`) created on first run; should be changed

## 20. Future Roadmap
- **Enhanced mobile responsiveness** — Progressive Web App (PWA) support
- **Two-factor authentication** — TOTP-based 2FA for customer and admin
- **Email/SMS notifications** — Integrate with SendGrid/Twilio via NotificationSenderProtocol
- **Advanced analytics** — Spending patterns, goal projections, loan amortization schedules
- **Multi-currency support** — Currency conversion and multi-currency accounts
- **API rate limiting** — Redis-backed rate limiting for production deployments
- **OpenAPI client generation** — Auto-generate client SDKs from OpenAPI spec
- **Database migrations** — Expand Alembic coverage for schema evolution

## 21. Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Follow the layered architecture: Domain → Application → Infrastructure
4. All database interactions must go through Repository/Service layer
5. Write tests for new features (happy path + edge cases)
6. Ensure all 139 tests pass: `pytest tests/ -v`
7. Submit a Pull Request

## 22. License
MIT License — see [LICENSE](LICENSE) for details.
