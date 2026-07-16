<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.135%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-d71f00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/UNION-BANK-/ci.yml?branch=main&label=CI&logo=github" alt="CI">
  <img src="https://img.shields.io/badge/tests-256%20passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-72%25-yellowgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
</p>

<br>

<h1 align="center">
  🏦 Union Bank Management System
</h1>

<p align="center">
  <em>A production-grade banking API with concurrent-safe transactions, defense-in-depth security, and full observability — built as a senior engineering portfolio showcase.</em>
</p>

<p align="center">
  <a href="#-the-problem">The Problem</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-key-engineering-decisions">Key Decisions</a> •
  <a href="#-security-defense-in-depth">Security</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-metrics">Metrics</a> •
  <a href="docs/SELF_AUDIT.md">Self-Audit</a>
</p>

<br>

---

## 🎯 The Problem

> **How do you build a banking system that is safe, observable, and extensible — without over-engineering it?**

This project started as a CLI tool and evolved into a full-stack banking management system. The core challenges addressed:

| Challenge | Approach |
|-----------|----------|
| **Concurrent transfers** | SQLite WAL mode + atomic transactions prevent lost updates |
| **Token security** | DB-backed refresh tokens with versioning → invalidate all sessions on password change |
| **Defense in depth** | Rate limiting + account lockout + TOTP 2FA + CSRF middleware + security headers |
| **Data integrity** | Soft-delete for accounts (preserves transaction history), idempotency keys prevent double-spend |
| **Observability** | Structured JSON logging + Prometheus metrics + health/readiness probes + request tracing |
| **Testability** | Protocol-based repositories → full DI container → swap fakes for real DB in tests |
| **Natural-language search** | Offline, deterministic transaction search — no LLM dependency, no API costs |

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

- **1 service layer, 1 repository layer** — no dual architecture. All business logic in `application/services.py`, all data access through `infrastructure/repositories.py`. [ADR-0001](docs/ADR-0001-consolidate-service-layer.md)
- **Protocol-based DI** — repositories implement protocols from `application/interfaces.py`, making them swappable for fakes in tests.
- **Versioned API** — `/api/v1/` (legacy, deprecated) and `/api/v2/` (current, envelope-wrapped) coexist with clear deprecation headers.
- **Security by design** — token versioning, TOTP 2FA, CSRF middleware, security headers. [ADR-0002](docs/ADR-0002-security-hardening.md)

---

## 🔑 Key Engineering Decisions

> *Three portfolio-ready talking points that demonstrate senior engineering judgment.*

### 1️⃣ Data Integrity: I Found & Fixed a Compliance-Shaped Bug

**The problem:** The original implementation used hard-deletes that cascaded to destroy all associated transaction records when an account was deleted. For a banking domain, this is a regulatory issue — transaction records must be preserved for auditability.

**The fix:** Replaced hard-deletes with **soft-delete** using a `deleted_at` timestamp. Default queries filter out soft-deleted records, but the data remains recoverable. Additionally, all money-movement endpoints now accept an **idempotency key** — if a client retries with the same key, the server returns the cached result instead of re-executing, preventing double-spend scenarios.

```python
# Test: concurrent retry with idempotency key
# Proves that the money only moves once even with race conditions
result1 = txn_service.deposit(acc_no, 1000, idempotency_key="key-1")
result2 = txn_service.deposit(acc_no, 1000, idempotency_key="key-1")
assert result1.success and result2.success
assert account.balance == initial + 1000  # Not +2000
```

**ADR:** [ADR-0004](docs/ADR-0004-data-retention.md) — Data retention and idempotency.

---

### 2️⃣ Architecture: I Made the Codebase Honest About What It Does

**The problem:** The original codebase had three generations of code layered on top of each other: an old Flask/JSON system at root, a newer SQLAlchemy system at root, and a third copy in `src/`. Two independent audits confirmed that "which copy is even live is not obvious from the outside." Phantom features (TOTP fields that never verified, metrics middleware never wired) added to the confusion.

**The fix:** A forensic inventory (Phase -1) classified every module as LIVE, DEAD, or AMBIGUOUS using import-graph tracing. All dead code was deleted. All phantom features were either completed (TOTP 2FA now fully enforced on admin login) or removed (stale `WsgiMetricsMiddleware`). The result is one canonical tree with zero ambiguity.

**Deliverable:** `docs/INVENTORY.md` — zero AMBIGUOUS entries, with full evidence trail.

**ADR:** [ADR-0001](docs/ADR-0001-consolidate-service-layer.md) — Service layer consolidation.

---

### 3️⃣ Correctness: I Proved Money Movement Is Concurrency-Safe

**The problem:** Banking operations are the hardest correctness problem in this domain. An incorrect implementation loses money.

**The fix:** Each transfer runs inside a single SQLite transaction with WAL mode enabled. SQLite's serialized locking ensures concurrent writes are sequenced. The transfer service debits the sender, credits the receiver, and creates both transaction records atomically.

A concurrency test fires **10 simultaneous transfers** and asserts that total money is conserved — no lost updates, no double-spending:

```python
@concurrent_futures(max_workers=10)
def concurrency_test():
    ...
    assert updated_sender.balance == expected_sender
    assert updated_receiver.balance == expected_receiver
    assert total == Decimal("10000.00")  # Money conserved
```

**Tests:**
- `tests/test_integration.py::TestConcurrentTransfers` — 10 parallel transfers
- `tests/test_edge_cases.py` — idempotency prevents double-spend under concurrent retry
- `tests/test_property_based.py` — property-based invariants (hypothesis) for money conservation

---

## 🛡 Security: Defense in Depth

| Layer | Protection |
|-------|-----------|
| **JWT** | RS256 signing, short-lived (15 min), token versioning (password change → all sessions invalidated) |
| **Refresh tokens** | DB-backed, rotated on use (old token revoked on each refresh), expiring after 7 days |
| **Rate limiting** | Account-aware lockout (5 failed attempts → 15 min freeze) + IP-based (slowapi) on all endpoints |
| **2FA** | TOTP-based (pyotp), fully implemented for admin accounts with enroll/verify/disable endpoints |
| **CSRF** | Origin/Referer validation middleware (defense in depth for Bearer-token API) |
| **Headers** | HSTS, X-Frame-Options, X-Content-Type-Options, CSP, Permissions-Policy, X-XSS-Protection |
| **Password hash** | Removed from all API responses (test-enforced via `test_password_leak.py`) |
| **Exception handling** | All errors logged with context — bare `except: pass` banned by CI grep-check |

See the full [Threat Model](docs/THREAT_MODEL.md) and [Security ADR](docs/ADR-0002-security-hardening.md).

---

## 🔬 Observability & Monitoring

| Feature | Implementation |
|---------|---------------|
| **Structured logging** | JSON format → `bank.jsonl` with request_id, account context, and level |
| **Request tracing** | Every request gets a unique `X-Request-ID` propagated through logs |
| **Prometheus metrics** | Request rate, latency (histogram), in-flight requests, error rate, cache hit/miss |
| **Health probes** | `/api/healthz` (liveness), `/api/readyz` (readiness with DB check) |
| **UVicron access logs** | Routed through the same structured JSON logger |

See [RUNBOOK.md](docs/RUNBOOK.md) for incident response and troubleshooting.

---

## 🔍 Natural-Language Search (Analyzr)

Analyzr is a **zero-dependency, offline, deterministic** transaction search engine. It translates plain English into structured filters using pattern matching — no LLM costs, no API latency.

**Example queries:**
- `"show me large deposits last month"` → type=DEPOSIT, amount=above average, time=last_month
- `"what did I spend on food this month?"` → type=WITHDRAW, category=Food & Dining, time=this_month
- `"find suspicious transactions over ₹10,000"` → type=all, amount=large, time=last_90_days

**Architecture:**
1. `classify_intent()` — regex matching against 20+ intent templates
2. `extract_amount_range()` — parses over/under/between with currency prefixes
3. `compute_time_window()` — converts "this month", "last 90 days" to date ranges
4. `execute_query()` — orchestrates pipeline with DB-backed search

**Design:** No external API calls, deterministic, composable, extensible.

**53 unit tests** cover every intent pattern, amount format, and time window edge case.

---

## 📊 Metrics

| Metric | Value |
|--------|-------|
| **Total tests** | 256 passing |
| **Test coverage** | 72% (backend) |
| **Property-based tests** | 5 hypothesis invariants + stateful money machine |
| **Edge-case tests** | 44 tests (formatting, categories, file I/O, fakes, services) |
| **Migration tests** | 5 Alembic round-trip tests |
| **Analyzr tests** | 53 unit tests for natural-language search |
| **Concurrency test** | 10 parallel transfers — verified no lost updates |
| **Original score** | 3.8/10 and 5.3/10 (two independent audits) |
| **Current score** | 8.1/10 (see [Self-Audit](docs/SELF_AUDIT.md)) |

---

## 🧪 Testing Strategy

| Test Type | Tool | What It Covers |
|-----------|------|----------------|
| Unit tests | pytest | Service layer with protocol-based fakes |
| Integration tests | pytest + real SQLite | Repository + service end-to-end flows |
| Concurrency tests | pytest + ThreadPoolExecutor | Race conditions, no lost updates |
| Security tests | pytest | Password leak, JWT tampering, expired tokens, SQL injection |
| Property-based | hypothesis | Transfer invariants, stateful money machine |
| Migration tests | pytest + Alembic | Upgrade/downgrade round-trip, table verification |
| Edge-case tests | pytest | 44 tests for formatting, categories, file I/O, error paths |
| Analyzr tests | pytest | 53 tests for intent detection, amount parsing, time windows |

```bash
python -m pytest tests/ -v
```

---

## 🚀 Quick Start

```bash
# Docker (recommended)
docker compose up -d
docker compose exec api python seed_data.py
open http://localhost:8000/docs

# Local dev
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python main.py create-admin          # Create admin user
PYTHONPATH=src uvicorn unionbank.entrypoints.api.main:app --reload --port 8000

cd frontend
npm install
npm run dev
```

### Demo Credentials

| Role | How to Access |
|------|---------------|
| **Admin** | `python main.py create-admin` (creates one-time) |
| **Customer** | Register via `/signup` or `python seed_data.py` |

---

## 🚢 What I'd Do Differently at 10x Scale

If this system needed to handle 100,000+ users, here's what would change:

1. **SQLite → PostgreSQL** — SQLite's write lock becomes a bottleneck under concurrent load. PostgreSQL with PgBouncer connection pooling handles this trivially. [ADR-0005](docs/ADR-0005-database-migration.md)

2. **Cursor pagination everywhere** — Offset pagination gets expensive past page 100. The keyset-based cursor pagination in `get_paginated_keyset()` is the foundation — just needs to be the default for all list endpoints.

3. **Dedicated cache layer** — Redis is wired in but only for admin statistics. A production system would cache account lookups aggressively with write-through invalidation.

4. **Async workers for notifications** — Email/SMS notifications are in-process. At scale, these should be background jobs (Celery + Redis queue) to avoid blocking request handlers.

5. **Read replicas** — With Postgres: one primary writer + N read replicas for statement queries. The protocol-based repository layer makes this a configuration change.

6. **Immutable audit trail** — The current audit log tracks admin actions only. A production banking system needs hash-linked, append-only audit of every balance change.

7. **Formal verification of money math** — Property-based tests are a good start. At scale I'd want a TLA+ specification of the transfer atomicity contract.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [ADR-0001](docs/ADR-0001-consolidate-service-layer.md) | Service layer consolidation — one canonical tree |
| [ADR-0002](docs/ADR-0002-security-hardening.md) | Token strategy, 2FA, CSRF — defense in depth |
| [ADR-0003](docs/adr/ADR-0003-totp-2fa.md) | TOTP 2FA completion (enrollment, verification, login enforcement) |
| [ADR-0004](docs/ADR-0004-data-retention.md) | Data retention — soft-delete + idempotency for compliance |
| [ADR-0005](docs/ADR-0005-database-migration.md) | PostgreSQL migration path via Alembic |
| [INVENTORY.md](docs/INVENTORY.md) | Forensic inventory — all modules classified (live/dead/ambiguous) |
| [THREAT_MODEL.md](docs/THREAT_MODEL.md) | Security threat analysis and mitigation |
| [RUNBOOK.md](docs/RUNBOOK.md) | Incident response procedures and troubleshooting |
| [SELF_AUDIT.md](docs/SELF_AUDIT.md) | Finding-by-finding reconciliation against both original audits |
| [TS_MIGRATION.md](docs/TS_MIGRATION.md) | Frontend TypeScript migration plan |

---

## 🗂 Project Structure

```
src/
├── unionbank/             # Canonical package
│   ├── domain/            # Pure domain entities & enums
│   ├── application/       # Service layer + protocols
│   ├── infrastructure/    # Repositories, DB, cache, metrics
│   ├── entrypoints/       # FastAPI routes (v1, v2), CLI
│   ├── utils/             # Auth, formatting, validation, analyzr
│   ├── container.py       # DI container
│   └── config.py          # Settings (env-driven)
│
├── database.py            # Shim → infrastructure/database.py
├── models.py              # Shim → infrastructure/models.py
└── entrypoints/           # Root-level (api.py, main.py)

frontend/                  # React SPA (TypeScript migration in progress)
tests/                     # All 256 tests (pytest)
docs/                      # ADRs, threat model, runbook, self-audit
scripts/                   # Docker entrypoint, analyzr, load testing
```

---

## 📄 License

[MIT](LICENSE) — Use this as a portfolio reference. Contributions welcome.

---

<p align="center">
  <sub>Built with FastAPI, SQLAlchemy, React, SQLite, Redis, and Prometheus.</sub>
  <br>
  <sub>Two independent audits rated the original codebase 3.8/10 and 5.3/10. Current rating: 8.1/10.</sub>
</p>
