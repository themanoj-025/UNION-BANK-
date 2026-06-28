# UNION-BANK- — Project Overview

## 1. Project Title
**Union Bank Management System** — A multi-interface banking application with CLI (console), Flask web frontend, and FastAPI REST API for managing customer accounts, transactions, and administrative controls.

## 2. Executive Summary
Union Bank Management System is a feature-rich banking application that provides three interfaces: a rich terminal-based CLI with colored output, a modern Flask web application with Chart.js visualizations and dark/light theme, and a FastAPI REST API with OpenAPI documentation. It supports the full customer banking lifecycle — account registration, deposits, withdrawals, fund transfers, transaction history, CSV export, monthly interest calculation, and savings goals — alongside an admin panel for account oversight, freeze/unfreeze, deletion, statistics, and PDF report generation. The system uses JSON file-based storage with atomic writes, automatic backups, and corruption recovery.

## 3. Problem Statement
Small financial institutions and educational projects need a comprehensive banking system that demonstrates core banking operations (account management, transactions, admin controls) across multiple interface types (CLI, web, API) while maintaining data integrity through atomic file operations and backup recovery.

## 4. Objectives
- Provide complete banking operations: registration, deposits, withdrawals, transfers
- Support multiple interfaces (CLI, web, API) sharing the same business logic
- Enable administrative oversight (account freeze/unfreeze, deletion, statistics)
- Offer financial planning tools (savings goals, interest calculation)
- Generate reports (CSV export, PDF bank statistics)
- Ensure data integrity with atomic file writes and corruption recovery
- Include security features (rate limiting, password hashing, session management)

## 5. Key Features
- **Account management:** Registration, profile update, password change, account closure
- **Transactions:** Deposit, withdraw, transfer between accounts with categorized tracking
- **Transaction history:** Mini statement (last 5), full statement, CSV export
- **Interest calculation:** Monthly interest at 3.5% p.a.
- **Savings goals:** Create, edit, delete goals; contribute from balance; progress tracking with visual bars
- **Admin panel:** View all accounts, search, freeze/unfreeze, delete accounts, transaction overview
- **Admin statistics:** Account status breakdown, financial summary, category analysis with charts
- **PDF report generation:** Bank-wide statistics report with tables and bar charts
- **Web charts:** Category doughnut chart, transaction type bar chart, balance trend line chart
- **Dark/light theme:** Theme toggle with persistent preference
- **Rate limiting:** Account lockout after 5 failed attempts (15-minute cooldown)
- **Session management:** Automatic timeout after 5 minutes of inactivity
- **Data integrity:** Atomic JSON writes with automatic .bak backups and corruption recovery

## 6. System Architecture
```
User Access Options
    ├── CLI (main.py → bank.py / admin.py)
    │     └── Console menu system (rich colored output)
    │
    ├── Flask Web (webapp.py)
    │     └── Jinja2 templates + Chart.js visualizations
    │
    └── FastAPI (api.py)
          └── REST endpoints + Swagger docs
                │
                ▼
          Shared Business Logic
            ├── account.py (Account class)
            ├── bank.py (Bank class — CLI interactions)
            ├── admin.py (Admin class — CLI interactions)
            └── utils.py (data layer, validation, hashing)
                │
                ▼
          JSON File Storage
            ├── data/accounts.json
            ├── data/transactions.json
            ├── data/login_attempts.json
            └── data/savings_goals.json
```

## 7. Tech Stack
| Category | Technology |
|---|---|
| **Language** | Python 3.x |
| **Web Framework** | Flask (web frontend) |
| **API Framework** | FastAPI |
| **CLI** | Terminal menu system (custom) |
| **Auth** | bcrypt (password hashing), PyJWT (API tokens) |
| **Data Storage** | JSON files (4 separate files) |
| **Visualization** | Chart.js (web), CSS (styled tables) |
| **PDF Generation** | fpdf2 |
| **CSV Export** | Python csv module |
| **Validation** | Custom validators (regex-based) |
| **Testing** | pytest |
| **Deployment** | Standalone Python (no Docker/cloud config) |

## 8. Architecture Diagram
See Section 6 — shared business logic layer (account.py, utils.py) consumed by all three interfaces, with JSON file-based persistence.

## 9. Folder Structure
```
UNION-BANK-/
├── main.py                    # Entry point for CLI application
├── bank.py                    # Bank class — CLI menu system
├── account.py                 # Account model — all banking operations
├── admin.py                   # Admin class — CLI admin panel
├── api.py                     # FastAPI REST API
├── webapp.py                  # Flask web application
├── logger.py                  # Logging configuration
├── utils.py                   # Data layer, validators, helpers
├── ui.py                      # CLI UI utilities (colors, formatting)
├── seed_data.py               # Seed data for testing/demo
├── pyproject.toml             # Project metadata + dependencies
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── data/                      # JSON storage directory (created at runtime)
├── static/
│   └── style.css              # Web app styles (light + dark theme)
├── templates/                 # Flask Jinja2 templates
│   ├── base.html              # Base layout (navbar, footer, flash messages)
│   ├── index.html             # Landing page with hero + features + testimonials
│   ├── login.html             # Customer login
│   ├── register.html          # Customer registration
│   ├── dashboard.html         # Customer dashboard with charts
│   ├── deposit.html           # Deposit form
│   ├── withdraw.html          # Withdraw form
│   ├── transfer.html          # Transfer form with confirmation
│   ├── statement.html         # Full statement with chart
│   ├── profile.html           # Profile view/edit
│   ├── change_password.html   # Change password form
│   ├── savings_goals.html     # Savings goals overview
│   ├── savings_goal_form.html # Create/edit goal form
│   ├── apply_interest.html    # Interest confirmation
│   ├── admin_login.html       # Admin login
│   ├── admin_dashboard.html   # Admin overview
│   ├── admin_accounts.html    # All accounts list
│   ├── admin_account_detail.html# Single account detail with charts
│   ├── admin_search.html      # Account search
│   ├── admin_freeze.html      # Freeze/unfreeze control
│   ├── admin_delete.html      # Account deletion
│   ├── admin_statistics.html  # Bank statistics with charts
│   ├── admin_transactions.html# All transactions view
│   └── admin_change_password.html # Admin password change
├── tests/
│   ├── test_features.py       # Feature tests (rate limiting, CSV, interest, etc.)
│   ├── test_smoke.py          # Module import tests
│   └── conftest.py            # Pytest fixtures
├── start.bat                  # Windows start script
└── test.bat                   # Windows test script
```

## 10. Module Overview
- **account.py:** `Account` class — core banking operations (deposit, withdraw, transfer, balance check, statement, profile management, password change, account closure, CSV export, savings goals CRUD, interest application)
- **bank.py:** `Bank` class — CLI menu system for registration, login, dashboard navigation, transaction menus, profile settings
- **admin.py:** `Admin` class — CLI admin panel (view accounts, freeze/unfreeze, delete, statistics)
- **api.py:** FastAPI REST API with JWT auth — mirrors all banking operations as REST endpoints with Pydantic validation
- **webapp.py:** Flask web application — customer and admin web interfaces with session-based auth, Chart.js dashboards, PDF report generation
- **utils.py:** JSON file operations (load/save with atomic writes + backup recovery), ID generation, password hashing (bcrypt), rate limiting, session management, input validation (email, phone, password, name), CSV export, interest calculation, transaction categories
- **ui.py:** Terminal UI utilities (colors via ANSI codes, formatted headers/divider, prompt helpers)
- **logger.py:** Python logging configuration

## 11. Database Overview
Not applicable — this project uses JSON file-based storage. Four JSON files in the `data/` directory:
- **accounts.json:** Keyed by account number. Stores account details (name, age, gender, mobile, email, hashed password, balance, is_active, is_frozen, created_at)
- **transactions.json:** Keyed by account number. Array of transaction records (txn_id, type, amount, balance after, description, timestamp, category, optional target_account)
- **login_attempts.json:** Keyed by account number or admin username. Tracks failed login counts and lockout timestamps
- **savings_goals.json:** Keyed by account number. Array of savings goals (goal_id, name, target_amount, current_amount, target_date, created_at, is_completed)

## 12. API Overview
### FastAPI (api.py) — 22+ endpoints

**Auth:**
- `POST /api/auth/login` — Customer login, returns JWT
- `POST /api/auth/register` — New account registration
- `POST /api/auth/admin-login` — Admin login, returns JWT

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

**Savings Goals:**
- `GET /api/savings` — List goals with summary
- `POST /api/savings` — Create goal
- `PUT /api/savings/{goal_id}` — Update goal
- `POST /api/savings/{goal_id}/contribute` — Contribute to goal
- `DELETE /api/savings/{goal_id}` — Delete goal

**Admin:**
- `GET /api/admin/accounts` — List all accounts
- `GET /api/admin/accounts/search?q=` — Search accounts
- `POST /api/admin/accounts/{acc_no}/freeze` — Freeze account
- `POST /api/admin/accounts/{acc_no}/unfreeze` — Unfreeze account
- `DELETE /api/admin/accounts/{acc_no}` — Delete account
- `GET /api/admin/statistics` — Bank statistics
- `GET /api/admin/transactions` — All transactions
- `PUT /api/admin/password` — Change admin password

**Utility:**
- `GET /api/categories` — List transaction categories
- `GET /api/health` — Health check

### Flask Web (webapp.py) — 20+ routes
Matching set of route handlers for the web interface, rendering Jinja2 templates instead of JSON.

## 13. Authentication & Authorization
- **CLI:** Password verification via bcrypt, no session persistence
- **Flask Web:** Session-based auth (customer + admin separate), bcrypt password verification
- **FastAPI:** JWT token-based (HS256, 24-hour expiry), separate customer and admin token types
- **Rate limiting:** 5 failed attempts → 15-minute lockout (per account or admin username)
- **Session timeout:** 5 minutes of inactivity (CLI and web)
- **Roles:** Customer (self-service) and Admin (full system access)

## 14. Data Flow
1. **Registration flow:** User fills form → validate all fields → hash password with bcrypt → generate unique 10-digit account number → save to accounts.json → display account number
2. **Deposit flow:** User enters amount + category → load account from accounts.json → update balance → save atomically → log transaction to transactions.json → display new balance
3. **Transfer flow:** Validate recipient exists, not frozen, not self → debit sender → credit recipient → log both transactions → atomic saves
4. **Statement flow:** Load transactions.json → filter by account number → sort by timestamp → display reversed (newest first)
5. **Rate limiting flow:** On failed login → load login_attempts.json → increment count → if count >= 5, set lockout_until = now + 15 min → on successful login, reset count to 0

## 15. Request Lifecycle
**CLI:** User input → main_menu() → Bank/Admin method → Account method → utils (file I/O) → display result
**Web:** HTTP request → Flask route → decorator (login_required/admin_required) → Account method → utils → render_template
**API:** HTTP request → FastAPI route → JWT dependency → Account method → utils → Pydantic response

## 16. External Integrations
No external services or third-party APIs are integrated. All functionality is implemented using Python standard libraries plus bcrypt, PyJWT, and fpdf2.

## 17. Environment Variables
| Variable | Purpose |
|---|---|
| `JWT_SECRET` | JWT signing secret for FastAPI (defaults to dev secret) |
| `FLASK_SECRET_KEY` | Flask session secret (defaults to random 24 bytes) |

## 18. Configuration
- JSON file paths defined as constants in `utils.py` (ACCOUNTS_FILE, TRANSACTIONS_FILE, etc.)
- Rate limiting constants: MAX_LOGIN_ATTEMPTS=5, LOGIN_LOCKOUT_MINUTES=15
- Session timeout: SESSION_TIMEOUT_SECONDS=300 (5 minutes)
- Interest rate: SAVINGS_INTEREST_RATE=3.5 (% p.a.)
- Transaction categories: 13 predefined categories
- Password validation rules: min 8 chars, 1 uppercase, 1 lowercase, 1 digit

## 19. Security Measures
- **Password hashing:** bcrypt with salt for all passwords
- **Rate limiting:** Account locks after 5 failed attempts (15-minute cooldown)
- **Session timeout:** Automatic logout after 5 minutes inactivity
- **JWT auth:** API uses signed tokens with expiry (24 hours)
- **Input validation:** Email, phone (Indian format), password strength, name format
- **Atomic file writes:** Temp file + rename pattern prevents corruption
- **Automatic backups:** .bak files created before every write
- **Corruption recovery:** load_json falls back to backup if primary file is corrupted
- **CORS:** API allows all origins (development-grade, should be restricted in production)

## 20. Logging & Monitoring
Custom logger in `logger.py` with:
- Timestamped log entries at DEBUG, INFO, WARNING, ERROR, CRITICAL levels
- Logged events: account registration, login success/failure, password changes, transactions (with amounts), account closure, freeze/unfreeze, admin actions
- Logs are printed to stdout (visible in terminal)

No external monitoring, metrics collection, or alerting.

## 21. Error Handling
- **CLI:** try/except in main loop with user-friendly error messages and colored error output
- **Web:** Flask flash messages for success/error/warning/info with auto-dismiss animation
- **API:** FastAPI HTTPException with appropriate status codes and detail messages
- **Data layer:** Silent recovery from corrupted JSON files with automatic backup restoration

## 22. Performance Optimizations
- **Atomic writes:** Temp file + os.replace prevents partial writes
- **Backup recovery:** Automatic fallback to .bak on corruption
- **Direct JSON access:** No ORM overhead — direct dict access
- No caching, no connection pooling, no async processing (not needed for JSON file storage)

## 23. Deployment Architecture
- **Standalone Python:** No containerization. Run directly with Python 3.x.
- **CLI:** `python main.py`
- **Web:** `python webapp.py` (Flask on port 5000)
- **API:** `uvicorn api:app --host 0.0.0.0 --port 8000`
- No Dockerfile, no cloud-specific configs, no deployment scripts beyond `start.bat`

## 24. Testing Strategy
- **Framework:** pytest
- **Test files:** 2 test modules (test_features.py, test_smoke.py) in tests/
- **Coverage:** Rate limiting, session management, CSV export, interest calculation, transaction categories, account model methods, module import smoke tests
- No CI pipeline configured

## 25. Development Workflow
No CONTRIBUTING.md found. Git pre-commit hook configured (`.pre-commit-config.yaml`). No documented conventions for branches or commits.

## 26. Known Limitations
- **JSON file storage:** Not suitable for concurrent users; no ACID transactions; loading entire dataset into memory
- **No database:** No indexing, no query optimization, no concurrent write handling
- **Password in registration:** Passwords are visible during CLI registration (no masking)
- **Admin credentials:** Admin credentials are stored in a JSON file (ADMIN_FILE), which is a security concern
- **Default secrets:** JWT_SECRET defaults to a hardcoded dev secret — must be changed for production
- **CORS wide open:** `allow_origins=["*"]` — should be restricted in production
- **No HTTPS:** All communication is plain HTTP
- **Single user files:** Not designed for multi-server or clustered deployment

## 27. Future Roadmap
No documented roadmap found. CHANGELOG.md exists but content was not read. Code evidence suggests:
- Enhanced mobile responsiveness
- Additional financial analytics
- Two-factor authentication

## 28. Troubleshooting
- **Data file corrupted:** The system automatically recovers from .bak backup. If both are corrupted, delete the JSON files and restart — they will be recreated empty.
- **Forgot admin password:** Edit `data/admin.json` (or equivalent admin credential file) to reset the hashed password.
- **Login locked:** Wait 15 minutes for the lockout to expire, or delete `data/login_attempts.json`.
- **Interest calculation not applying:** Ensure balance is positive. Interest rate is 3.5% p.a.

## 29. FAQ
- **How to run the CLI?** `python main.py`
- **How to run the web app?** `python webapp.py` and open http://localhost:5000
- **How to run the API?** `uvicorn api:app --reload` and open http://localhost:8000/docs for Swagger
- **How to reset all data?** Delete the `data/` directory — JSON files will be recreated on next startup.
- **How to change interest rate?** Edit `SAVINGS_INTEREST_RATE` in `utils.py`.
- **How to add a new transaction category?** Add to the `TRANSACTION_CATEGORIES` list in `utils.py`.

## 30. Contributing Guidelines
Not yet defined. No CONTRIBUTING.md file exists in the repository.

## 31. License
No license file found in the repository root.

## 32. Maintainers & Contacts
No author/maintainer information specified in source files. The repository is located at `F:\GITHUB\UNION-BANK-` on the local filesystem.
