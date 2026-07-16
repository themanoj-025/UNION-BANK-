# Baseline Versions — Union Bank Management System

**Date:** 2026-07-16
**Commit:** `808492a` (chore: raise CI coverage floor to 50%)
**Tag:** `pre-audit-baseline`

---

## Python Dependencies (requirements.txt — pinned exact)

| Package | Version | Notes |
|---------|---------|-------|
| alembic | 1.18.4 | |
| bcrypt | 5.0.0 | |
| colorama | 0.4.6 | |
| fastapi | 0.109.0 | ⚠️ **Below pyproject.toml minimum (>=0.115.0)** |
| prometheus-client | 0.24.1 | |
| pytest | 9.0.2 | |
| pytest-cov | 7.0.0 | |
| PyJWT | 2.11.0 | |
| pyotp | 2.9.0 | |
| redis | 7.2.0 | |
| slowapi | 0.1.9 | |
| SQLAlchemy | 2.0.46 | |
| uvicorn | 0.27.0 | ⚠️ **Below pyproject.toml minimum (>=0.30.0)** |

### Version Mismatch (requirements.txt vs pyproject.toml)

| Package | requirements.txt | pyproject.toml minimum | Status |
|---------|:----------------:|:----------------------:|:------:|
| fastapi | 0.109.0 | >=0.115.0 | ❌ BELOW minimum |
| uvicorn | 0.27.0 | >=0.30.0 | ❌ BELOW minimum |

### pyproject.toml dependencies NOT in requirements.txt

| Package | pyproject.toml spec | Status |
|---------|-------------------|--------|
| pydantic | >=2.0.0 | Not pinned in requirements.txt |
| python-jose | >=3.3.0 | Not pinned in requirements.txt (PyJWT used instead) |
| passlib | >=1.7.4 | Not pinned in requirements.txt |
| python-multipart | >=0.0.9 | Not pinned in requirements.txt |
| python-dotenv | >=1.0.0 | Not pinned in requirements.txt |
| structlog | >=24.0.0 | Not pinned in requirements.txt |
| pybreaker | >=1.1.0 | Not pinned in requirements.txt |
| httpx | >=0.27.0 | Not pinned in requirements.txt |
| typer | >=0.12.0 | Not pinned in requirements.txt |
| rich | >=13.0.0 | Not pinned in requirements.txt |

---

## Frontend Dependencies (package.json)

| Package | Version | Type |
|---------|---------|------|
| react | ^19.2.7 | dependency |
| react-dom | ^19.2.7 | dependency |
| react-router-dom | ^7.18.1 | dependency |
| axios | ^1.18.1 | dependency |
| framer-motion | ^12.42.2 | dependency |
| lucide-react | ^1.24.0 | dependency |
| flag-icons | ^7.5.0 | dependency |
| vite | ^8.1.1 | devDependency |
| @vitejs/plugin-react | ^6.0.3 | devDependency |
| oxlint | ^1.71.0 | devDependency |
| @types/react | ^19.2.17 | devDependency |
| @types/react-dom | ^19.2.3 | devDependency |

---

## Installed Python Packages (from requirements-lock.txt — subset)

Key transitive dependencies:
| Package | Version |
|---------|---------|
| starlette | 0.35.1 |
| pydantic | 2.12.5 |
| pydantic-core | 2.41.5 |
| cryptography | 46.0.4 |
| passlib | 1.7.4 |
| python-jose | 3.5.0 |
| python-multipart | 0.0.9 |
| python-dotenv | 1.2.1 |
| httpx | 0.28.1 |
| typer | 0.24.0 |
| rich | 14.3.2 |
| sentry-sdk | 2.53.0 |
| coverage | 7.13.4 |
| hypothesis | 6.156.6 |
| werkzeug | 3.0.1 |
| Flask | 3.0.0 |
| flask-cors | 6.0.2 |
| Flask-Login | 0.6.3 |
| Flask-SQLAlchemy | 3.1.1 |
| Flask-WTF | 1.3.0 |
| limits | 5.8.0 |
| psycopg2 | 2.9.11 |

> ⚠️ **Note:** The codebase still has Flask (3.0.0) and related packages installed even though Flask was supposedly removed in Phase 1. These are transitive from requirements-lock.txt.

---

## System Info

| Attribute | Value |
|-----------|-------|
| Python | 3.11+ (via pyproject.toml) |
| Node | determined by frontend build |
| OS | Windows (development) |
| Container | Docker / Docker Compose |
