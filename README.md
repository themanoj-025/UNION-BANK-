<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.135%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-d71f00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/UNION-BANK-/ci.yml?branch=main&label=CI&logo=github" alt="CI">
  <img src="https://img.shields.io/badge/tests-143%20passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
</p>

<br>

<h1 align="center">
  🏦 Union Bank Management System
</h1>

<p align="center">
  <em>A production-grade banking API with concurrency-safe transactions, defense-in-depth security, and full observability — built as a senior engineering portfolio showcase.</em>
</p>

<p align="center">
  <a href="#-the-problem">The Problem</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-key-engineering-decisions">Key Decisions</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-metrics">Metrics</a> •
  <a href="#-what-id-do-differently-at-10x-scale">10x Scale</a>
</p>

<br>

---

## 🎯 The Problem

> **How do you build a banking system that is safe, observable, and extensible — without over-engineering it?**

This project explores that question by building a full-stack banking management system from the ground up. It started as a CLI tool and evolved into a FastAPI REST API with a React SPA frontend, Redis caching, structured logging, Prometheus metrics, TOTP-based 2FA, and a dependency-injected service architecture.

The core challenges addressed:

| Challenge | Approach |
|-----------|----------|
| **Concurrent transfers** | SQLite WAL mode + atomic transactions prevent lost updates |
| **Token security** | DB-backed refresh tokens with versioning → invalidate all sessions on password change |
| **Defense in depth** | Rate limiting + account lockout + TOTP 2FA + CSRF middleware + security headers |
| **Observability** | Structured JSON logging + Prometheus metrics + health/readiness probes |
| **Testability** | Protocol-based repositories → full DI container → swap fakes for real DB in tests |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        UNION BANK API                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐    │
│  │  React SPA   │   │   FastAPI REST   │   │   CLI (main.py)  │    │
│  │  (frontend)  │   │   (port 8000)    │   │   (admin ops)    │    │
│  └──────┬───────┘   └───────┬──────────┘   └───────┬──────────┘    │
│         │                  │                       │               │
│         └──────────────────┼───────────────────────┘               │
│                            │                                       │
│               ┌────────────▼────────────┐                         │
│               │   Application Layer     │  AuthService,           │
│               │   (application/)        │  TransactionService,    │
│               │                         │  AdminService           │
│               └────────────┬────────────┘                         │
│                            │                                       │
│               ┌────────────▼────────────┐                         │
│               │   Repository Layer      │  10 SQLAlchemy repos    │
│               │   (infrastructure/)     │  Protocol-based DI      │
│               └────────────┬────────────┘                         │
│                            │                                       │
│          ┌─────────────────┼──────────────────┐                   │
│          ▼                 ▼                  ▼                   │
│   ┌────────────┐   ┌──────────────┐   ┌──────────────┐           │
│   │  SQLite DB │   │  Redis Cache │   │  Prometheus  │           │
│   │  (WAL mode)│   │  (optional)  │   │  /metrics    │           │
│   └────────────┘   └──────────────┘   └──────────────┘           │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              DI Container (container.py)                 │      │
│  │  Wires services → repositories → database/session       │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐      │
│  │  Domain      │   │  Alembic     │   │  Security        │      │
│  │  Entities    │   │  Migrations  │   │  JWT + TOTP 2FA  │      │
│  └──────────────┘   └──────────────┘   └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

- **1 service layer, 1 repository layer** — no dual architecture. All business logic lives in `application/services.py` and all data access goes through `infrastructure/repositories.py`. See [ADR-0001](docs/ADR-0001-consolidation.md).
- **Protocol-based DI** — repositories implement protocols from `application/interfaces.py`, making them swappable for fakes in tests. The container wires everything together.
- **Versioned API** — `/api/v1/` (legacy, deprecated) and `/api/v2/` (current, envelope-wrapped) coexist with clear deprecation headers.
- **Security by design** — token versioning, TOTP 2FA, CSRF middleware, security headers. See [ADR-0002](docs/ADR-0002-security-hardening.md).

---

## 🔑 Key Engineering Decisions

### 1. Concurrency-Safe Transactions

Banking operations are the hardest correctness problem in this domain. An incorrect implementation can lose money.

**Approach:** Each transfer runs inside a single SQLite transaction with WAL mode enabled. SQLite's serialized locking ensures that concurrent writes are sequenced. The transfer service:
1. Debits the sender within the transaction
2. Credits the receiver within the same transaction
3. Creates both transaction records atomically

A [concurrency test](tests/test_integration.py#L306) fires 10 simultaneous transfers and asserts that the total money is conserved — no lost updates, no double-spending.

### 2. Token Versioning (Invalidate JWTs on Password Change)

Most JWT implementations have no mechanism to revoke a stolen token before it expires. This project solves that with versioned tokens:

- Each account has a `token_version` column in the database
- JWTs encode the token version at issuance
- Every request validates that the token's version matches the database version
- Password change → increments `token_version` → all existing JWTs become invalid

This means changing your password instantly logs out all other sessions.

### 3. Defense-in-Depth Security

| Layer | Protection |
|-------|-----------|
| **JWT** | RS256 signing, short-lived (15 min), token versioning |
| **Refresh tokens** | DB-backed, rotated on use, expiring after 7 days |
| **Rate limiting** | Account-aware (per-account lockout after 5 failed attempts) + IP-based (slowapi) |
| **2FA** | TOTP-based (pyotp), supported for admin accounts |
| **CSRF** | Origin/Referer validation middleware (defense in depth for Bearer-token API) |
| **Headers** | HSTS, X-Frame-Options, X-Content-Type-Options, CSP, Permissions-Policy |

See the full [Threat Model](docs/THREAT_MODEL.md) and [Security ADR](docs/ADR-0002-security-hardening.md) for a detailed analysis.

### 4. Observability

Structured JSON logging with request IDs, Prometheus metrics (request rate, latency, errors), and separate health/readiness probes. See [RUNBOOK.md](docs/RUNBOOK.md) for incident response procedures.

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/themanoj-025/UNION-BANK-.git
cd UNION-BANK-

# 2. Start everything (API + Redis)
docker compose up -d

# 3. Seed demo data (optional)
docker compose exec api python seed_data.py

# 4. Open the app
open http://localhost:8000/docs   # API docs
```

**Local dev (no Docker):**
```bash
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create admin user
python main.py create-admin

# Start the API
uvicorn api:app --reload --port 8000

# Start the frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Demo Credentials

| Role | Credentials |
|------|------------|
| **Admin** | `python main.py create-admin` (creates one-time) |
| **Customer** | Register via `/signup` or `python seed_data.py` |

---

## 📊 Metrics

| Metric | Value |
|--------|-------|
| **Total tests** | 143 passing |
| **Test coverage** | ~78% (backend) |
| **Concurrent transfer safety** | Verified — no lost updates across 10 simultaneous transfers |
| **Load test baseline** | See [scripts/load-test/](scripts/load-test/) for locust test |

### Concurrency Test (highest-signal test)

```python
# tests/test_integration.py :: TestConcurrentTransfers
# Fires 10 transfers in parallel from the same account.
# Asserts: total money conserved, no lost updates.

@concurrent_futures(max_workers=10)
def concurrency_test():
    ...
    assert updated_sender.balance == expected_sender
    assert updated_receiver.balance == expected_receiver
    assert total == Decimal("10000.00")  # Money conserved
```

---

## 🧪 Testing Strategy

| Test Type | Tool | Coverage |
|-----------|------|----------|
| Unit tests | pytest | Service layer with fakes |
| Integration tests | pytest + real SQLite | Repository + service flows |
| Concurrency tests | pytest + ThreadPoolExecutor | Race condition verification |
| Security tests | pytest | JWT tampering, expired tokens, SQL injection |
| Frontend tests | Vitest + RTL | Login, transfer, statement (planned) |

Run: `python -m pytest tests/ -v`

---

## 🗂 Project Structure

```
src/
├── domain/              # Domain entities & enums
├── application/         # Service layer + protocols
├── infrastructure/      # Repositories, DB, cache, metrics
├── interfaces/api/      # FastAPI routes (v1, v2)
├── interfaces/cli/      # CLI admin tool
├── utils/               # Auth, formatting, validation
├── container.py         # DI container
└── config.py            # Settings (env-driven)

frontend/                # React SPA
tests/                   # All tests
docs/                    # ADRs, threat model, runbook, ER diagram
scripts/                 # Docker entrypoint, load test
```

---

## 🚢 What I'd Do Differently at 10x Scale

If this system needed to handle 100,000+ users, here's what would change:

1. **SQLite → PostgreSQL** — SQLite's write lock becomes a bottleneck under concurrent load. PostgreSQL with PgBouncer connection pooling handles this trivially. See [ADR-0003](docs/ADR-0003-database-migration.md) (planning).

2. **Cursor pagination everywhere** — Offset pagination gets expensive past page 100 on large tables. The keyset-based cursor pagination in `get_paginated_keyset()` is the foundation — just needs to be the default for all list endpoints.

3. **Dedicated cache layer** — Redis is wired in but used only for admin statistics and account lists. A production system would cache account lookups aggressively, with a clear invalidation strategy (write-through cache for account data, TTL-based for aggregate stats).

4. **Async workers for notifications** — Email/SMS notifications are currently in-process. At scale, these should be async background jobs (Celery + Redis queue) to avoid blocking the request handler.

5. **Read replicas** — With SQLite this doesn't apply, but with Postgres: one primary writer + N read replicas for statement queries. The protocol-based repository layer makes this a configuration change, not a code change.

6. **Full audit trail** — The current audit log tracks admin actions only. A production banking system needs an immutable audit trail of every balance-changing operation, with cryptographic chaining (hash-linked logs).

7. **Formal verification of money math** — Property-based tests (hypothesis) for transfer invariants are a good start, but at scale I'd want a formal specification of the transfer atomicity contract using TLA+ or similar.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [ADR-0001](docs/ADR-0001-consolidation.md) | Service layer consolidation |
| [ADR-0002](docs/ADR-0002-security-hardening.md) | Token strategy, 2FA, CSRF |
| [THREAT_MODEL.md](docs/THREAT_MODEL.md) | Security threat analysis |
| [RUNBOOK.md](docs/RUNBOOK.md) | Incident response procedures |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Load test results (planned) |

---

## 📄 License

[MIT](LICENSE) — feel free to use this as a portfolio reference.
