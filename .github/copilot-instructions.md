# UNION-BANK- — Copilot Instructions

## Code conventions
- Python with 4-space indentation
- Three interfaces: CLI (Rich), Web (Flask), API (FastAPI)
- JSON file-based storage with automatic .bak backups
- bcrypt password hashing + JWT tokens (HS256)
- Ruff for linting, pytest with coverage >80%

## Key commands
- CLI: `python main.py`
- Flask web: `python webapp.py`
- FastAPI: `uvicorn api:app --reload`
- Tests: `pytest tests/ -v --cov --cov-fail-under=80`

## Architecture
- CLI: `ui.py` (Rich-based) + `main.py` (entry)
- Web: `webapp.py` (Flask) + `templates/` (Jinja2)
- API: `api.py` (FastAPI) with JWT auth
- Core: `bank.py` (business logic), `account.py` (account ops)
- Storage: JSON files in `data/` with corruption recovery
- Rate limiting: 5 failed attempts → 15-min lockout
