# Contributing to UNION-BANK-

Thank you for your interest in contributing to the Union Bank Management System!

## Getting Started

### Prerequisites
- Python 3.x
- pip

### Setup
1. Fork and clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   (Optional for production — development defaults work without modification.)

### Running the Applications

**CLI interface:**
```bash
python main.py
```

**Flask web app:**
```bash
python webapp.py
```
Available at `http://localhost:5000`.

**FastAPI server:**
```bash
uvicorn api:app --reload
```
API docs at `http://localhost:8000/docs`.

### Environment Variables
| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | Dev secret (change in production) | JWT signing secret for FastAPI |
| `FLASK_SECRET_KEY` | Random 24 bytes | Flask session secret |

## Code Style

- Follow PEP 8 conventions.
- Use 4-space indentation.
- Add docstrings to public functions and classes.
- Use descriptive variable names.
- Keep functions focused and single-purpose.

## Project Architecture

This project has **three interfaces sharing one business logic layer:**

### Interfaces
- **CLI:** `main.py` → `bank.py` (Bank class), `admin.py` (Admin class) — console menu system
- **Web:** `webapp.py` — Flask application with Jinja2 templates
- **API:** `api.py` — FastAPI REST API with JWT auth

### Shared Business Logic
- **`account.py`** — `Account` class: all banking operations (deposit, withdraw, transfer, etc.)
- **`utils.py`** — JSON file operations, validation, hashing, rate limiting, session management
- **`logger.py`** — Logging configuration

### Templates & Static
- **`templates/`** — 20+ Jinja2 HTML templates
- **`static/style.css`** — Web app styles (light + dark theme)

## Running Tests

```bash
pytest
```

Test files are in `tests/`:
- `test_features.py` — Tests for rate limiting, CSV export, interest calculation, account operations
- `test_smoke.py` — Module import verification

When adding new features, please add corresponding tests.

## Submitting Changes

1. Create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```
2. Make focused, minimal changes.
3. Ensure new features work across all three interfaces (CLI, Web, API) where applicable.
4. Run tests and verify they pass.
5. If adding new API endpoints, add corresponding Flask routes and CLI menu options.
6. Commit with a descriptive message:
   - Format: `type(scope): description`
   - Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
   - Example: `feat(savings): add recurring deposit option`
   - Example: `fix(api): correct JWT expiry handling`
7. Push and open a Pull Request.

## Reporting Issues

Include in your report:
- Steps to reproduce
- Which interface is affected (CLI, Web, API)
- Error messages and logs
- Environment (OS, Python version)

## Adding Features Across All Interfaces

When adding a new feature, it should ideally work across all three interfaces:

1. **Business logic:** Add the method to `account.py` (or create a new service module).
2. **CLI:** Add a menu option in `bank.py` (customer) or `admin.py` (admin).
3. **Web:** Add a route in `webapp.py` and a template in `templates/`.
4. **API:** Add an endpoint in `api.py` with JWT authentication.
5. **Validation:** Add input validation in `utils.py`.
6. **Tests:** Add test cases in `tests/test_features.py`.

### Data Storage
- All data is stored in JSON files in the `data/` directory.
- Use `utils.py` functions for atomic file operations (`load_json`, `save_json`).
- New data entities should follow the existing JSON file pattern with automatic .bak backups.

### JSON File Guidelines
- Use atomic writes (temp file + rename) to prevent corruption.
- Keep file operations in `utils.py` — don't directly open JSON files elsewhere.
- Add appropriate validation before writing data.
- Handle corrupted files gracefully (auto-recover from .bak).

## Pre-commit Hooks

A `.pre-commit-config.yaml` file is present. To install:
```bash
pip install pre-commit
pre-commit install
```

## Security Notes

- **DO NOT** hardcode default secrets (`JWT_SECRET` has a dev default — change in production).
- **DO NOT** store passwords in plain text — always use bcrypt hashing.
- Keep CORS restricted in production (`allow_origins=["*"]` is for development only).
- Rate limiting is enforced at 5 failed attempts with a 15-minute lockout.
- Sessions automatically expire after 5 minutes of inactivity.

## Code of Conduct

This project and everyone participating in it is governed by the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.
