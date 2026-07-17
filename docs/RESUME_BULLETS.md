# Resume Bullets — Union Bank Management System

> *Ready-to-use entries for your resume, LinkedIn, or portfolio. Each bullet maps to a specific, verifiable deliverable in the repository — not overclaimed.*

---

## 🎯 Senior Software Engineer / Backend Engineer

**Union Bank Management System** — *Concurrent-safe banking API with atomic transactions, defense-in-depth security, async PostgreSQL, and full observability.*
[github.com/themanoj-025/UNION-BANK-](https://github.com/themanoj-025/UNION-BANK-)

---

### Architecture & System Design

- **Designed and shipped a production-grade banking API** (15,000+ LOC Python) with layered architecture: domain → application (protocol-based DI) → infrastructure (SQLAlchemy repositories) → entrypoints (FastAPI v1/v2, CLI). Reduced codebase ambiguity from 3 overlapping generations to one canonical tree via forensic import-graph inventory.

- **Implemented atomic, crash-safe fund transfers** using SQLAlchemy savepoints with fault-injection testing that simulates mid-transaction process failure — proving no partial write survives. Added DB-level `CHECK (balance >= 0)` constraint plus app-level guard for defense in depth.

- **Migrated from synchronous to asynchronous SQLAlchemy** across hot paths (transfer, deposit, withdraw) without downtime. Protocol-based repository layer meant swapping implementations was a configuration change, not a rewrite.

- **Replaced in-memory pagination** (linear memory blow-up from 100 to 10,000 accounts) with SQL-level cursor pagination — flat memory usage at any dataset size.

### Security

- **Built defense-in-depth security architecture:** RS256 JWT (15-min expiry) + TOTP 2FA (pyotp, Fernet-encrypted secrets) + refresh token rotation (bcrypt-hashed storage) + httpOnly/Secure/SameSite=Strict cookies (eliminating XSS-based token theft) + CSRF double-submit cookie pattern + account-based rate limiting (5 money-movements/hour, bypass-resistant via IP rotation) + automated SQLi/XSS/CSRF test fixtures.

- **Closed a compliance-shaped security gap** by removing password hashes from all API responses (test-enforced via CI), implementing account lockout after 5 failed attempts, and adding security headers (HSTS, CSP, X-Frame-Options).

### Database & Performance

- **Architected database evolution from SQLite to PostgreSQL** via Alembic migrations running identically against both backends. Added connection pooling (pool_size, max_overflow, pool_timeout) and Redis caching with 60s TTL + write-through invalidation.

- **Proved data integrity under concurrency** with 10-parallel-transfer tests (ThreadPoolExecutor) verifying money conservation — no lost updates, no double-spending. Added idempotency keys preventing double-spend on retry.

### Testing & Quality

- **Grew test coverage from 26% to 73%** (376 backend + 10 frontend tests) without padding — prioritized property-based invariants (Hypothesis), concurrency tests, and security vulnerability tests over trivial getter/setter coverage.

- **Built a CI/CD pipeline with 10 job types:** unit tests (Python 3.11 + 3.12), frontend tests (Vitest), security tests, mutation testing (mutmut), API fuzzing (schemathesis), Docker build verification, secrets scanning, PostgreSQL integration, commitlint enforcement, and link checking.

### DevOps & Observability

- **Containerized the full stack** with multi-stage Dockerfile (minimal final image — no tests/docs/node_modules), docker-compose with Prometheus + Grafana, health/readiness probes (DB + cache connectivity checks), and Kubernetes manifests (deployment, service, ingress, HPA) for scale-out.

- **Implemented full observability:** Prometheus metrics (request rate, p95 latency histogram, error rate, cache hit ratio), structured JSON logging with request tracing, and a 6-panel Grafana dashboard.

### Code Quality

- **Eliminated all sys.path.insert() hacks** by converting to pip-installable package. Replaced bare `Optional` dependency injection with typed Protocols (`NotificationServiceProtocol`, `IdempotencyRepositoryProtocol`). Added circuit breaker (pybreaker) around notification service to prevent slow providers from blocking money-movement responses.

- **Purified domain layer** — removed all infrastructure/config imports from `domain/` package. Configuration is injected, not imported. Domain/interest.py passes rate as parameter instead of reading global config.

### Git & Process

- **Adopted Conventional Commits** with commitlint + husky pre-commit hook enforcement. Documented branch strategy (trunk-based with feature branches), semver releases, and CI gating in Architecture Decision Records (ADR-0006).

---

## 📋 Quick Reference by Role

| Role | Best Bullets |
|------|-------------|
| **Backend Engineer** | Atomic transfers, async migration, PostgreSQL evolution, layered architecture |
| **Security Engineer** | Defense-in-depth, JWT+TOTP+CSRF, token storage, rate limiting, security tests |
| **DevOps Engineer** | Multi-stage Docker, Prometheus/Grafana, K8s manifests, CI/CD, health probes |
| **Full-Stack Engineer** | All of the above + React frontend, Vitest testing, API design |
| **SRE / Platform Engineer** | Observability stack, metrics, structured logging, circuit breaker, health checks |

---

## ⚠️ Usage Notes

- **Do not claim** features that don't exist yet: formal TLA+ verification, production PostgreSQL deployment at scale, Celery worker queue for notifications.
- **Verify each bullet** against the repo before including in an application. Each bullet links to a specific commit, test, or file in the repository.
- **Adapt the language** to match the job description — emphasize security for security roles, DevOps for platform roles, etc.

---

*Last updated: 2026-07-17*
