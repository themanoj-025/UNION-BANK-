# Glossary — UNION-BANK-: Shared Vocabulary

| Field | Value |
|---|---|
| Version | v0.1 |
| Last Updated | 2026-08-06 |
| Owner | Tech Writer |
| Status | Approved |

| Term | Definition |
|---|---|
| Savepoint (begin_nested) | Nested DB transaction point enabling full rollback on failure |
| Atomic transfer | All-or-nothing money movement; no partial write survives crash |
| Money conservation | Invariant: total funds unchanged by transfers |
| Fault injection | Test that kills a process mid-operation to prove atomicity |
| Envelope (ApiResponse[T]) | v2 response wrapper: success + data + error |
| httpOnly cookie | Token cookie inaccessible to JS (anti-XSS) |
| SameSite=Strict | Cookie sent only on same-site requests |
| CSRF double-submit | Cookie + matching header required on state changes |
| Refresh rotation | Old refresh token invalidated on each use |
| Token family | Group of refresh tokens; reuse of any revokes all |
| TOTP | Time-based one-time password (2FA) |
| Token versioning | User-scoped version that invalidates all tokens on change |
| Account lockout | Freeze after 5 failed attempts (15 min) |
| Cursor pagination | SQL-level paging via opaque cursor (flat memory) |
| Circuit breaker | Fails-fast wrapper for notifications |
| Idempotency key | Client-supplied key preventing duplicate operations |
| Alembic | Migration tool; SQLite↔PostgreSQL round-trip tested |
| Analyzr | Natural-language search utility (53 tests) |
| Inventory | docs/INVENTORY.md — forensic module classification |
| ADR | Architecture Decision Record |
| Audit score | SELF_AUDIT.md rubric: 3.8 → 8.1/10 |

## Related Documents

| Document | Relationship |
|---|---|
| [PRD.md](PRD.md) | Feature vocabulary |
| [TechSpec.md](TechSpec.md) | Technical terms |
| [AppFlow.md](AppFlow.md) | Screen-level terms |
| [Schema.md](Schema.md) | Data terms (TBL-*) |
| [ImplementationPlan.md](ImplementationPlan.md) | Task vocabulary |
| [Tracker.md](Tracker.md) | Status terms |
| [Rules.md](Rules.md) | Convention terms |
| [API.md](API.md) | API vocabulary |
| [SecurityAndCompliance.md](SecurityAndCompliance.md) | Security terms |
| [Testing.md](Testing.md) | Test vocabulary |
| [Deployment.md](Deployment.md) | Ops terms |
| [RiskRegister.md](RiskRegister.md) | Risk vocabulary |
