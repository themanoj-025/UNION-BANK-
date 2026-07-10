# Architecture — UNION-BANK-

## System Architecture

```
User/Admin (Browser or CLI)
       │
       ├── Flask Web App (webapp.py) ────── Web Interface
       │         │
       │         ├── Routes (decorated in webapp.py)
       │         ├── Templates (templates/*.html)
       │         ├── Static (static/style.css)
       │         │
       │         ├── bank.py ───── Core banking operations
       │         ├── account.py ── Account management
       │         ├── admin.py ──── Admin functions
       │         ├── api.py ────── REST API layer
       │         │
       │         └── utils.py ─── Shared utilities
       │
       ├── CLI / TUI (ui.py) ────────────── Terminal Interface
       │         └── Rich library for terminal UI
       │
       └── Storage Layer
                 └── JSON files (accounts, transactions, users)
```

## Architecture Overview
- **Dual-interface**: Flask web app + Rich CLI/TUI
- **Pattern**: Simple layered architecture (Controller → Logic → Storage)
- **Storage**: JSON file-based (no database server required)
- **Auth**: Custom session-based authentication

## Component Responsibilities
| Component | File | Role |
|-----------|------|------|
| Entry Point | main.py | Application startup |
| Web Controller | webapp.py | Flask routes and request handling |
| Core Banking | bank.py | Business logic for banking operations |
| Account Mgmt | account.py | Account CRUD operations |
| Admin | admin.py | Administrative controls |
| API | api.py | REST API endpoints |
| CLI UI | ui.py | Rich terminal UI |
| Utilities | utils.py | Helper functions |
| Logging | logger.py | Application logging |
| Seeding | seed_data.py | Demo data generation |

## Design Decisions
- JSON storage for simplicity (no database setup)
- Flask for web framework (lightweight, well-known)
- Rich for CLI (modern terminal UI)
- Template-based rendering for web
- Separate admin module for privileged operations
