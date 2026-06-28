# UNION-BANK-

## Stack
- **CLI:** Rich-based interactive banking interface
- **Web:** Flask (HTML templates + sessions)
- **API:** FastAPI (JWT auth, CORS)
- **Storage:** JSON file-based (`data/accounts.json`, etc.)
- **Auth:** bcrypt password hashing + JWT tokens
- **Testing:** pytest with coverage (>80% required)

## Dev commands
- `python main.py` — launch CLI interface
- `python webapp.py` — start Flask web server
- `uvicorn api:app --reload` — start FastAPI
- `pytest tests/ -v --cov --cov-fail-under=80` — run tests
- `ruff check .` — lint

## Key conventions
- 4-space indent for Python
- Three interfaces: CLI (`ui.py`), Web (`webapp.py`), API (`api.py`)
- JSON data files in `data/` (auto-backup via `.bak` files)
- Rate limiting: 5 failed attempts → 15-minute lockout
- Session timeout: 5 minutes inactivity
