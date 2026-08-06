# Union Bank Management System

> A concurrent-safe banking API with atomic transactions, defense-in-depth security (JWT + TOTP 2FA + CSRF), async SQLAlchemy (SQLite/PostgreSQL), Prometheus observability, and 386 tests.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135%2B-009688.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-d71f00.svg)](https://sqlalchemy.org)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg)](https://postgresql.org)
[![Tests: 386](https://img.shields.io/badge/Tests-386%20passing-brightgreen.svg)](#testing)
[![Coverage: 73%](https://img.shields.io/badge/Coverage-73%25-yellowgreen.svg)](#testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Tech Stack & Core Technologies](#2-tech-stack--core-technologies)
- [3. High-Level Architecture](#3-high-level-architecture)
- [4. Complete Folder Structure Tree](#4-complete-folder-structure-tree)
- [5. Exhaustive File-by-File & Folder-by-Folder Breakdown](#5-exhaustive-file-by-file--folder-by-folder-breakdown)
- [6. Data Models & Schemas](#6-data-models--schemas)
- [7. API Surface](#7-api-surface)
- [8. Configuration & Environment Variables](#8-configuration--environment-variables)
- [9. Build, Run & Deployment Instructions](#9-build-run--deployment-instructions)
- [10. Data & Control Flow Walkthroughs](#10-data--control-flow-walkthroughs)
- [11. Dependency Graph Summary](#11-dependency-graph-summary)
- [12. Testing Strategy](#12-testing-strategy)
- [13. Known Issues, Technical Debt & Assumptions](#13-known-issues-technical-debt--assumptions)
- [14. Glossary](#14-glossary)
- [15. Appendix](#15-appendix)

---

## 1. Executive Summary

**UNION-BANK-** is a senior software engineering portfolio project demonstrating atomic financial transactions under concurrency, defense-in-depth security architecture, async SQLAlchemy migration, database evolution at scale, and full production observability.

**Target users**: Hiring managers evaluating senior engineering skills, and developers learning about banking API patterns.

**What it proves**: Five engineering skills that map directly to senior-level interviews:
1. Atomic financial transactions under concurrency (crash-mid-transfer test)
2. Defense-in-depth security (RS256 JWT + TOTP 2FA + CSRF + rate limiting)
3. Async migration strategy (sync → async SQLAlchemy without downtime)
4. Database evolution (SQLite → PostgreSQL via Alembic)
5. Observability & production readiness (Prometheus + Grafana + structured logging)

**Why it exists**: To demonstrate production-grade banking API engineering with real-world complexity and honest before/after improvement documentation (audit: 3.8 → 8.1/10).

*Note: The 386 tests, 73% coverage, and audit improvement are explicitly documented in the README.*

---

## 2. Tech Stack & Core Technologies

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Language | Python | 3.11+ | Backend |
| API Framework | FastAPI | 0.135+ | REST API with versioned endpoints |
| ORM | SQLAlchemy | 2.0+ | Async database access |
| Database | PostgreSQL | 16 | Production database |
| Database (Dev) | SQLite | — | Local development |
| Migrations | Alembic | 1.13+ | Schema versioning |
| Auth | JWT (RS256) + TOTP 2FA | — | Authentication + 2FA |
| Token Storage | httpOnly cookies | — | Secure token storage |
| CSRF | Double-submit cookie | — | CSRF protection |
| Rate Limiting | SlowAPI | — | Per-account + IP-based |
| Frontend | React 19 + Vite | — | SPA dashboard |
| Cache | Redis | 7.2 | Caching + rate limiting |
| Observability | Prometheus + Grafana | — | Metrics + dashboards |
| Logging | structlog | — | Structured JSON logging |
| Testing | pytest + Hypothesis | — | 386 tests, 73% coverage |
| Property Testing | Hypothesis | — | Transfer invariants |
| Fuzz Testing | schemathesis | — | OpenAPI spec fuzzing |
| Mutation Testing | mutmut | — | Test effectiveness |
| Containerization | Docker + docker-compose | — | Production deployment |
| Kubernetes | k8s manifests | — | Container orchestration |

---

## 3. High-Level Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React SPA)"]
        REACT[React 19 + Vite]
        AXIOS[Axios API Client]
    end
    subgraph API["API Layer (FastAPI)"]
        V2[/api/v2/ Envelope API]
        V1[/api/v1/ Legacy API]
        MID[Middleware: Rate Limiting · CSRF · Security Headers]
        AUTH[JWT + TOTP 2FA]
    end
    subgraph App["Application Layer"]
        AS[AuthService]
        TS[TransactionService]
        ADMS[AdminService]
        LS[LoanService]
    end
    subgraph Repos["Repository Layer"]
        AR[AccountRepository]
        TR[TransactionRepository]
        LR[LoanRepository]
        SR[SavingsRepository]
    end
    subgraph Infra["Infrastructure"]
        DB[(PostgreSQL / SQLite)]
        CACHE[(Redis Cache)]
        PROM[Prometheus /metrics]
    end
    REACT --> AXIOS --> V2 --> MID --> AUTH --> AS
    V2 --> TS --> TR --> DB
    AR --> DB
    AR --> CACHE
```

---

## 4. Complete Folder Structure Tree

```
UNION-BANK-/
├── .dockerignore
├── .editorconfig
├── .env.example
├── .gitattributes
├── .github/
│   ├── CODEOWNERS
│   ├── copilot-instructions.md
│   ├── dependabot.yml
│   ├── ISSUE_TEMPLATE/
│   ├── labeler.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── ci.yml
│       ├── codeql.yml
│       ├── commitlint.yml
│       ├── gitleaks.yml
│       ├── labeler.yml
│       ├── maintenance.yml
│       ├── stale.yml
│       └── welcome.yml
├── .gitignore
├── .husky/
│   ├── commit-msg
│   └── pre-commit
├── .pre-commit-config.yaml
├── .vscode/
│   └── settings.json
├── AGENTS.md
├── AGENTS_FIX.md
├── alembic/
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
│       ├── 808505b8d0f3_initial_migration.py
│       └── bc2a4f8e9d1b_add_balance_check_constraint.py
├── alembic.ini
├── commitlint.config.js
├── docker-compose.prod.yml
├── docker-compose.yml
├── Dockerfile
├── docs/
│   ├── community/
│   ├── decisions/
│   │   ├── ADR-0001-consolidate-codebase.md
│   │   ├── ADR-0002-security-hardening.md
│   │   ├── ADR-0003-totp-2fa.md
│   │   ├── ADR-0004-data-retention.md
│   │   ├── ADR-0005-database-migration.md
│   │   └── ADR-0006-git-strategy.md
│   ├── design/
│   ├── product/
│   ├── project/
│   ├── reference/
│   │   ├── BASELINE_METRICS.md
│   │   ├── CASE_STUDY.md
│   │   ├── E2E_TEST_STRATEGY.md
│   │   ├── INVENTORY.md
│   │   ├── RUNBOOK.md
│   │   ├── SELF_AUDIT.md
│   │   └── THREAT_MODEL.md
│   └── technical/
├── e2e_test.py
├── frontend/
│   ├── .gitignore
│   ├── .oxlintrc.json
│   ├── index.html
│   ├── package.json
│   ├── README.md
│   ├── src/
│   │   ├── api.js
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── components/
│   │   ├── context/AuthContext.jsx
│   │   ├── index.css
│   │   ├── main.jsx
│   │   ├── pages/
│   │   └── test/
│   ├── vite.config.js
│   └── vitest.config.js
├── k8s/
│   ├── deployment.yaml
│   ├── hpa.yaml
│   ├── ingress.yaml
│   └── service.yaml
├── LICENSE
├── Makefile
├── monitoring/
│   ├── grafana/
│   │   └── dashboards/union-bank-dashboard.json
│   └── prometheus.yml
├── package.json
├── PROJECT_ANALYSIS.md
├── PROJECT_OVERVIEW.md
├── pyproject.toml
├── README.md
├── requirements-lock.txt
├── requirements.txt
├── scripts/
│   ├── analyzr.py
│   ├── docker-entrypoint.sh
│   ├── load-test/locustfile.py
│   └── migrate_json_to_sqlite.py
├── seed_data.py
├── src/unionbank/
│   ├── __init__.py
│   ├── application/
│   │   ├── async_services.py
│   │   ├── interfaces.py
│   │   ├── notifications.py
│   │   └── services.py
│   ├── config.py
│   ├── domain/
│   │   ├── clock.py
│   │   ├── entities.py
│   │   └── interest.py
│   ├── entrypoints/
│   │   ├── api/
│   │   │   ├── common.py
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   └── v2.py
│   │   └── cli/
│   │       ├── account.py
│   │       ├── admin.py
│   │       ├── bank.py
│   │       ├── main.py
│   │       └── ui.py
│   ├── infrastructure/
│   │   ├── async_container.py
│   │   ├── async_repositories.py
│   │   ├── backward_compat.py
│   │   ├── cache.py
│   │   ├── container.py
│   │   ├── database.py
│   │   ├── mappers.py
│   │   ├── metrics.py
│   │   ├── persistence.py
│   │   └── repositories.py
│   └── utils/
│       ├── account_rate_limit.py
│       ├── analyzr_core.py
│       ├── categories.py
│       ├── cookie_auth.py
│       ├── csv_export.py
│       ├── file_io.py
│       ├── formatting.py
│       ├── hashing.py
│       ├── logger.py
│       ├── rate_limit.py
│       ├── savings.py
│       ├── token_security.py
│       └── validation.py
├── start.bat
├── test.bat
└── tests/
    ├── conftest.py
    ├── fakes.py
    ├── test_*.py               # 376 backend tests
    └── __init__.py
```

---

## 5. Exhaustive File-by-File & Folder-by-Folder Breakdown

### Core Application

#### `src/unionbank/entrypoints/api/main.py`
- **Purpose**: FastAPI application with versioned API (v1 legacy, v2 envelope-wrapped), middleware chain (rate limiting, CSRF, security headers, tracing), and startup validation.

#### `src/unionbank/application/services.py`
- **Purpose**: Synchronous service layer with atomic transactions using SQLAlchemy `begin_nested()` savepoints.

#### `src/unionbank/application/async_services.py`
- **Purpose**: Async service layer for hot paths (transfer, deposit, withdraw).

#### `src/unionbank/domain/entities.py`
- **Purpose**: Domain entities (Account, Transaction, Loan) with zero external imports.

#### `src/unionbank/infrastructure/repositories.py`
- **Purpose**: Repository pattern with protocol-based DI for testability.

#### `src/unionbank/infrastructure/cache.py`
- **Purpose**: Redis cache with 60s TTL + invalidate-on-write strategy.

---

## 6. Data Models & Schemas

### Account

```json
{
  "id": "int — primary key",
  "name": "str — account holder name",
  "balance": "decimal — current balance",
  "account_type": "str — checking/savings",
  "is_active": "bool",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Transaction

```json
{
  "id": "int — primary key",
  "from_account_id": "int — FK to Account",
  "to_account_id": "int — FK to Account",
  "amount": "decimal — transfer amount",
  "type": "str — transfer/deposit/withdrawal",
  "status": "str — completed/pending/failed",
  "created_at": "datetime"
}
```

---

## 7. API Surface

### v2 API (Current)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v2/auth/login` | User login |
| `POST` | `/api/v2/auth/verify-otp` | TOTP 2FA verification |
| `GET` | `/api/v2/accounts/` | List accounts |
| `POST` | `/api/v2/transfers` | Atomic transfer |
| `GET` | `/api/v2/transactions/` | Transaction history |
| `GET` | `/api/v2/admin/dashboard` | Admin dashboard |
| `GET` | `/metrics` | Prometheus metrics |

---

## 8. Configuration & Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `SECRET_KEY` | JWT signing key | **Yes** |
| `DATABASE_URL` | PostgreSQL connection | Yes (prod) |
| `REDIS_URL` | Redis connection | No |
| `ENCRYPTION_KEY` | Fernet encryption key | Yes |

---

## 9. Build, Run & Deployment Instructions

```bash
# Quick start
git clone https://github.com/themanoj-025/UNION-BANK-.git
cd UNION-BANK-
python -m venv venv && source venv/bin/activate
pip install -e . && pip install -r requirements.txt

# Start API
uvicorn unionbank.entrypoints.api.main:app --reload --port 8000

# Start frontend
cd frontend && npm install && npm run dev

# Docker
docker-compose -f docker-compose.prod.yml up
```

---

## 10. Data & Control Flow Walkthroughs

### Flow 1: Atomic Transfer

1. User initiates transfer via API
2. `TransactionService` acquires savepoint
3. Debit sender account
4. Credit receiver account
5. Create transaction records
6. Commit savepoint (atomic)
7. Invalidate cache
8. Send notification (async, non-blocking)

---

## 11. Dependency Graph Summary

```
entrypoints/api/main.py → application/services.py → infrastructure/repositories.py
application/services.py → domain/entities.py
infrastructure/repositories.py → infrastructure/database.py
infrastructure/cache.py → Redis
```

---

## 12. Testing Strategy

- **Unit tests**: pytest with protocol-based fakes (no mocking)
- **Integration tests**: Real SQLite/PostgreSQL
- **Concurrency tests**: 10 parallel transfers via ThreadPoolExecutor
- **Property-based**: Hypothesis invariants (money conservation)
- **Security tests**: SQLi, XSS, CSRF, JWT tampering
- **Fuzz testing**: schemathesis against OpenAPI spec
- **Mutation testing**: mutmut for test effectiveness

---

## 13. Known Issues, Technical Debt & Assumptions

### Known Issues

1. **SQLite write lock**: Under high concurrency, transfers serialize.
2. **Offset pagination**: Memory usage grows with offset (cursor pagination recommended).

### Technical Debt

1. **v1 API deprecated**: Still present but should be removed.
2. **No audit trail**: Only admin action tracking, not every balance change.

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| **Savepoint** | SQLAlchemy atomic transaction boundary |
| **TOTP** | Time-based One-Time Password for 2FA |
| **CSRF** | Cross-Site Request Forgery |
| **Protocol-based DI** | Dependency injection via Python protocols |
| **Envelope API** | Consistent `{data, error, meta}` response wrapper |

---

## 15. Appendix

### Audit Improvement

| Metric | Before | After |
|--------|--------|-------|
| Audit Score | 3.8/10 | **8.1/10** |
| Tests | ~50 | **386** |
| Coverage | ~26% | **73%** |
| Security Layers | 1 | **8** |

---

*This document was generated as part of a comprehensive project documentation effort. Last updated: August 8, 2026.*
