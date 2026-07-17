<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.135%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-d71f00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-7.2-DC382D?logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/UNION-BANK-/ci.yml?branch=main&label=CI&logo=github" alt="CI">
  <img src="https://img.shields.io/badge/tests-386%20passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-73%25-yellowgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
</p>

<br>

<h1 align="center">
  🏦 Union Bank Management System
</h1>

<p align="center">
  <em>A concurrent-safe banking API with atomic transactions, defense-in-depth security (JWT + TOTP 2FA + CSRF), async SQLAlchemy (SQLite/PostgreSQL), Prometheus observability, and 386 tests — built as a senior software engineering portfolio.</em>
</p>

<p align="center">
  <a href="#-what-this-demonstrates">What This Demonstrates</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-engineering-case-studies">Case Studies</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-metrics">Metrics</a> •
  <a href="docs/SELF_AUDIT.md">Self-Audit</a>
</p>

<br>

---

## 🎯 What This Demonstrates

> *Five engineering skills that map directly to senior-level interviews.*

| # | Skill | Evidence in This Project |
|---|-------|--------------------------|
| 1 | **Atomic financial transactions under concurrency** | Crash-mid-transfer test proves no partial write survives. 10 parallel transfers with `ThreadPoolExecutor` verify money conservation — no lost updates, no double-spending. [See the test →](tests/test_integration.py) |
| 2 | **Defense-in-depth security architecture** | RS256 JWT + TOTP 2FA + httpOnly cookies + refresh token rotation + CSRF double-submit + account-based rate limiting + SQL injection test fixtures. Every layer is independently testable. |
| 3 | **Async migration strategy** | Synchronous → async SQLAlchemy migration without downtime. Hot paths (transfer, deposit, withdraw) converted first. Protocol-based DI means swapping implementations is a configuration change. |
| 4 | **Database evolution at scale** | SQLite local dev → PostgreSQL production via Alembic. CHECK constraints enforced at both DB and app level (defense in depth). Pagination moved from in-memory slicing to SQL-level cursor pagination — flat memory usage from 100 to 10,000 accounts. |
| 5 | **Observability & production readiness** | Prometheus metrics (request rate, error rate, p95 latency, cache hit ratio) + structured JSON logging + health/readiness probes + Grafana dashboard + Kubernetes manifests. Everything needed to run in production. |

---

## 🏗 Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React SPA)"]
        REACT[React 19 + Vite]
        AXIOS[Axios API Client<br/>httpOnly Cookies + CSRF]
    end

    subgraph API["API Layer (FastAPI)"]
        V2[/api/v2/ Envelope API]
        V1[/api/v1/ Legacy API]
        MID[Middleware:<br/>Rate Limiting · CSRF ·<br/>Security Headers · Tracing]
        AUTH[JWT + TOTP 2FA<br/>Refresh Token Rotation]
    end

    subgraph App["Application Layer"]
        AS[AuthService]
        TS[TransactionService<br/>Atomic transfers]
        ADMS[AdminService]
        LS[LoanService]
        NOTIF[Notification Service<br/>Circuit Breaker]
    end

    subgraph Repos["Repository Layer"]
        AR[AccountRepository]
        TR[TransactionRepository]
        LR[LoanRepository]
        SR[SavingsRepository]
        RR[RefreshTokenRepository]
    end

    subgraph Infra["Infrastructure"]
        DB[(PostgreSQL / SQLite<br/>Alembic Migrations)]
        CACHE[(Redis Cache<br/>60s TTL + Invalidate-on-Write)]
        PROM[Prometheus /metrics]
        LOG[JSON Logger → bank.jsonl]
    end

    subgraph DI["DI Container"]
        CONTAINER[protocol-based wiring<br/>repos → services]
    end

    REACT --> AXIOS
    AXIOS --> V2
    AXIOS --> V1
    V2 --> MID
    V1 --> MID
    MID --> AUTH
    AUTH --> AS
    V2 --> TS
    V2 --> ADMS
    V2 --> LS
    TS --> NOTIF
    AS --> AR
    TS --> TR
    TS --> AR
    ADMS --> AR
    ADMS --> TR
    LS --> LR
    AS --> RR
    AR --> DB
    TR --> DB
    LR --> DB
    RR --> DB
    SR --> DB
    AR --> CACHE
    TR --> CACHE

    CONTAINER -.-> AS
    CONTAINER -.-> TS
    CONTAINER -.-> ADMS
    CONTAINER -.-> LS
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Protocol-based DI** | Repositories implement protocols from `application/interfaces.py` → swappable for fakes in tests. No mock library needed. |
| **Versioned API** | `/api/v1/` (legacy, deprecated) and `/api/v2/` (current, envelope-wrapped `ApiResponse[T]`) coexist with clear deprecation headers. |
| **Domain purity** | `domain/` has zero imports outside `domain/` and stdlib. Configuration is injected, not imported. |
| **One canonical tree** | After forensic inventory deleted all dead code, there is exactly one copy of every module. Zero ambiguity. |

---

## 🔬 Engineering Case Studies

> *Four deep dives into the hardest engineering decisions in this project — written in the Problem → Constraint → Decision → Trade-off format that senior engineering interviews test for. [Read the full case studies →](docs/CASE_STUDY.md)*

### 1️⃣ Data Integrity: Why I Test by Killing the Process Mid-Transfer

<details>
<summary><strong>The Problem</strong> — A crash between debiting one account and crediting another destroys money.</summary>

**Constraint:** Banking transactions are all-or-nothing. If the server crashes between `debit(sender)` and `credit(receiver)`, the money disappears from the system. SQLite (the local database) has no distributed transaction coordinator.

**Decision:** Wrap the entire transfer in a single SQLAlchemy `begin_nested()` savepoint. The debit, credit, and both transaction records happen inside one atomic database transaction. If anything fails at any point — process kill, constraint violation, network timeout — the savepoint rolls back everything.

**Trade-off:** Savepoints add a small overhead per transaction (~2-5% in local benchmarks). At scale, this is negligible compared to the cost of a single reconciliation incident. The real limitation is SQLite's write lock — under high concurrency, transfers serialize. This is acceptable for a portfolio project and would be eliminated by migrating to PostgreSQL (Phase 2 lays the groundwork).

**Proof:** A fault-injection test starts a transfer, kills the process mid-way, and asserts the database state is consistent — either both sides updated or neither. [See the test →](tests/test_integration.py)
</details>

### 2️⃣ Architecture: I Made the Codebase Honest About What It Does

<details>
<summary><strong>The Problem</strong> — Three generations of overlapping code with no indication which was live.</summary>

**Constraint:** The project had accumulated code from multiple development sessions: a Flask/JSON system at root, a newer SQLAlchemy system also at root, and a third copy in `src/`. Two independent audits confirmed that "which copy is even live is not obvious from the outside." Phantom features (TOTP fields that never verified, metrics middleware never wired) added to the confusion.

**Decision:** A forensic inventory classified every module as LIVE, DEAD, or AMBIGUOUS using import-graph tracing. All dead code was deleted. All phantom features were either completed (TOTP 2FA now enforced on admin login) or removed. The result is one canonical tree with zero ambiguity — documented in `docs/INVENTORY.md`.

**Trade-off:** Deleting dead code is low-risk (the tests tell you if something breaks) but requires discipline to maintain. The inventory document needs periodic updates. The alternative — leaving dead code with "maybe this is important" notes — is what causes the problem in the first place.

**Deliverable:** `docs/INVENTORY.md` — zero AMBIGUOUS entries, with full import-graph evidence for every classification.
</details>

### 3️⃣ Testing Strategy: From 26% to 73% Coverage Without Padding

<details>
<summary><strong>The Problem</strong> — The original project had 26% coverage, concentrated on CLI utilities. Business logic (services, transfers, admin operations) was untested.</summary>

**Constraint:** Adding coverage to untested business logic is risky — you might lock in bugs as expected behavior. The solution is to write tests that assert *invariants* (e.g., "total money is conserved") rather than specific return values, so they catch regressions even when the implementation changes.

**Decision:** Three-pronged testing strategy:
1. **Property-based tests** (Hypothesis) — Assert invariants that must always be true: money conservation, non-negative balances, idempotency. These find edge cases that example-based tests miss.
2. **Concurrency tests** (ThreadPoolExecutor) — Fire 10 simultaneous transfers and assert total money is conserved. This found a real bug in the original implementation.
3. **Protocol-based fakes** — Instead of mocking, swap real repositories for fake implementations that implement the same protocol. The test uses the same service code as production.

**Trade-off:** Property-based tests are harder to write and debug than example-based tests. When a property fails, the shrinking output can be cryptic. The investment pays back when refactoring — property tests catch regressions that would require hundreds of example tests to cover.

**Results:** 386 tests (376 backend + 10 frontend), 73% coverage, 5 hypothesis invariants, 10-transfer concurrency test, security tests for SQLi/XSS/CSRF, Alembic migration round-trip tests.
</details>

### 4️⃣ Security: Defense in Depth (Not Just Authentication)

<details>
<summary><strong>The Problem</strong> — The original implementation used JWT tokens stored in localStorage with no CSRF protection, no refresh token rotation, and no rate limiting on money-movement endpoints.</summary>

**Constraint:** Banking APIs are a high-value target. A single vulnerability — XSS reading localStorage, CSRF forging a transfer, rate-limit bypass allowing brute force — could compromise user accounts. The solution is defense in depth: multiple independent security layers so that a failure in one doesn't compromise the system.

**Decision:**
1. **Token storage:** Migrated from localStorage to httpOnly, Secure, SameSite=Strict cookies. This eliminates XSS-based token theft.
2. **CSRF:** Added double-submit cookie pattern — every state-changing request must include a CSRF token that matches the cookie. This closes the CSRF vulnerability that cookie-based auth reopens.
3. **Rate limiting:** Account-based (max 5 money-movement ops/hour) in addition to IP-based. A bypass via IP rotation doesn't work — the limit follows the account.
4. **Refresh tokens:** Stored in DB with bcrypt hashing (not reversible encryption), rotated on each use, expired after 7 days. Password change invalidates all tokens.

**Trade-off:** httpOnly cookies require a CSRF strategy, which adds complexity to the frontend (must read token from cookie, send as header). The trade-off is worth it because httpOnly cookies are the industry standard for token storage — localStorage is universally recognized as insecure for auth tokens.

**Verification:** SQL injection attempt fixtures, XSS payload fixtures in text fields, CSRF token omission tests — all automated in CI.
</details>

---

## 🛡 Security Architecture

| Layer | Protection | Status |
|-------|-----------|--------|
| **Authentication** | RS256 JWT (15 min) + refresh token rotation (7 days) + token versioning | ✅ |
| **2FA** | TOTP-based (pyotp) — enrollment, verification, login enforcement for admin | ✅ |
| **Token storage** | httpOnly, Secure, SameSite=Strict cookies (not localStorage) | ✅ |
| **CSRF** | Double-submit cookie pattern | ✅ |
| **Rate limiting** | Account-based (5 money-movements/hour) + IP-based (slowapi) on all endpoints | ✅ |
| **Input validation** | SQL injection fixtures, XSS payload fixtures, Pydantic model validation | ✅ |
| **Headers** | HSTS, X-Frame-Options, X-Content-Type-Options, CSP, Permissions-Policy | ✅ |
| **Exception safety** | Bare `except: pass` banned by CI grep-check — all errors logged with context | ✅ |
| **Account lockout** | 5 failed attempts → 15-minute freeze (per-account) | ✅ |

[Full Threat Model →](docs/THREAT_MODEL.md) • [Security ADR →](docs/ADR-0002-security-hardening.md)

---

## 📊 Metrics

| Metric | Value |
|--------|-------|
| **Backend tests** | 376 passing |
| **Frontend tests** | 10 passing (Vitest + React Testing Library) |
| **Test coverage** | 73% (backend) |
| **Property-based tests** | 5 hypothesis invariants + stateful money machine |
| **Concurrency test** | 10 parallel transfers — verified no lost updates |
| **Security tests** | SQLi, XSS, CSRF, JWT tampering, password leak |
| **Migration tests** | 5 Alembic round-trip tests |
| **Analyzr tests** | 53 unit tests for natural-language search |
| **Python LOC** | ~15,000 |
| **Frontend components** | 15+ React components |
| **CI jobs** | 10 (backend, frontend, security, mutation, fuzz, docker, secrets, commitlint, postgres) |
| **Audit improvement** | [3.8 → 8.1/10](docs/SELF_AUDIT.md) |

---

## 🧪 Testing Strategy

| Test Type | Tool | What It Covers |
|-----------|------|----------------|
| **Unit tests** | pytest | Service layer with protocol-based fakes |
| **Integration tests** | pytest + real SQLite/Postgres | Repository + service end-to-end flows |
| **Concurrency tests** | pytest + ThreadPoolExecutor | Race conditions, no lost updates |
| **Security tests** | pytest | SQL injection, XSS, CSRF, JWT tampering, password leak |
| **Property-based** | hypothesis | Transfer invariants, stateful money machine |
| **Migration tests** | pytest + Alembic | Upgrade/downgrade round-trip, table verification |
| **Frontend tests** | Vitest + React Testing Library | Conditional rendering, error states, loading states |
| **Fuzz testing** | schemathesis | OpenAPI spec fuzzing against all endpoints |
| **Mutation testing** | mutmut | Report on test suite effectiveness |

```bash
# Run backend tests with coverage
python -m pytest tests/ --cov --cov-report=term

# Run frontend tests
cd frontend && npm test
```

---

## 🚀 Quick Start

**Prerequisites:** Python 3.11+, Node.js 20+

```bash
# 1. Clone & install (Python + git hooks)
git clone https://github.com/themanoj-025/UNION-BANK-.git && cd UNION-BANK-
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e . && pip install -r requirements.txt && npm install

# 2. Start the API (one terminal)
uvicorn unionbank.entrypoints.api.main:app --reload --port 8000

# 3. Start the frontend (second terminal)
cd frontend && npm install && npm run dev

# 4. Open in browser
open http://localhost:5173    # or http://localhost:8000/docs for API docs
```

> 💡 **Live demo** — Deploy with `docker-compose -f docker-compose.prod.yml up` (see [deployment docs](docs/RUNBOOK.md)).

**Demo credentials:**
| Role | Command |
|------|---------|
| **Admin** | `python scripts/docker-entrypoint.sh create-admin` |
| **Customer** | Register via `/signup` or run `python seed_data.py` |

---

## 🚢 What I'd Do Differently at 10x Scale (100,000+ Users)

| Bottleneck | Current Solution | Production Solution |
|-----------|-----------------|-------------------|
| **Write contention** | SQLite WAL mode | PostgreSQL + PgBouncer connection pooling |
| **Pagination perf** | Offset + cursor pagination | Cursor pagination as default for all list endpoints |
| **Cache strategy** | Redis for admin stats only | Write-through cache for account lookups |
| **Async notifications** | In-process circuit breaker | Background workers (Celery + Redis queue) |
| **Read replicas** | Single database | Primary writer + N read replicas (protocol-based repos make this a config change) |
| **Audit trail** | Admin action tracking only | Hash-linked, append-only audit of every balance change |
| **Formal verification** | Property-based tests | TLA+ specification of transfer atomicity contract |

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [ADR-0001](docs/ADR-0001-consolidate-service-layer.md) | Service layer consolidation — one canonical tree |
| [ADR-0002](docs/ADR-0002-security-hardening.md) | Token strategy, 2FA, CSRF |
| [ADR-0003](docs/adr/ADR-0003-totp-2fa.md) | TOTP 2FA completion |
| [ADR-0004](docs/ADR-0004-data-retention.md) | Data retention + idempotency |
| [ADR-0005](docs/ADR-0005-database-migration.md) | PostgreSQL migration path |
| [ADR-0006](docs/adr/ADR-0006-git-strategy.md) | Git strategy, commits, releases |
| [INVENTORY.md](docs/INVENTORY.md) | Forensic module classification |
| [THREAT_MODEL.md](docs/THREAT_MODEL.md) | Security threat analysis |
| [RUNBOOK.md](docs/RUNBOOK.md) | Incident response |
| [CASE_STUDY.md](docs/CASE_STUDY.md) | Engineering deep dives |
| [SELF_AUDIT.md](docs/SELF_AUDIT.md) | Audit reconciliation |

---

## 📄 License

[MIT](LICENSE) — Use this as a portfolio reference. Contributions welcome.

---

<p align="center">
  <sub>FastAPI · SQLAlchemy · React · PostgreSQL · Redis · Prometheus · Grafana · Docker · Kubernetes</sub>
  <br>
  <sub>Built for the Senior Software Engineering portfolio.</sub>
  <br>
  <sub>Two independent audits: 3.8/10 → current: 8.1/10 (<a href="docs/SELF_AUDIT.md">prove it</a>)</sub>
</p>
