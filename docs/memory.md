# MEMORY.md — UNION-BANK-

## Project Overview
UNION-BANK- is a comprehensive banking management system with a Flask web application and CLI interface. It supports account management, transactions (deposit, withdraw, transfer), admin dashboard, savings goals, and administrative controls (freeze accounts, interest application, statistics).

## Business Purpose
Provide a digital banking platform for users to manage accounts, perform transactions, and track savings, while administrators can oversee operations, manage users, and generate reports.

## Tech Stack
| Category | Technology |
|----------|------------|
| Language | Python |
| Web Framework | Flask |
| CLI Framework | Rich (TUI) |
| Data Storage | JSON file-based |
| Logging | Custom logger |
| Testing | pytest |
| Styling | Custom CSS (static/style.css) |
| Templates | Jinja2 (Flask) |

## Repository Structure
```
UNION-BANK-/
├── main.py              # Entry point (Flask app runner)
├── webapp.py            # Flask web application
├── bank.py              # Core banking logic
├── account.py           # Account management
├── admin.py             # Admin functionality
├── api.py               # REST API endpoints
├── ui.py                # CLI/TUI interface (Rich)
├── utils.py             # Utility functions
├── logger.py            # Logging configuration
├── seed_data.py         # Seed/demo data generator
├── static/style.css     # Web styles
├── templates/           # Jinja2 HTML templates
├── tests/               # Test suite
└── requirements.txt     # Dependencies
```

## Key Features
- User registration and login
- Deposit, withdraw, transfer between accounts
- Transaction history and statements
- Admin dashboard with user management
- Account freeze/unfreeze
- Interest application
- Savings goals tracking
- Statistics and reporting
- CLI interface with Rich TUI
- REST API endpoints

## Data Flow
```
User/Admin Browser
       ↓
  Flask Web App (webapp.py)
       ↓
  Business Logic (bank.py, account.py, admin.py)
       ↓
  JSON File Storage
       ↓
  Response rendered via Jinja2 templates
```
