# Glossary — UNION-BANK-: Shared Vocabulary

|Field|Value|
|---|---|
|Version|v0.1|
|Last Updated|2026-08-06|
|Owner|Tech Writer|
|Status|Approved|

|Term|Definition|
|---|---|
|Savepoint (begin_nested)|Nested DB transaction point enabling full rollback on failure|
|Atomic transfer|All-or-nothing money movement; no partial write survives crash|
|Money conservation|Invariant: total funds unchanged by transfers|
|Fault injection|Test that kills a process mid-operation to prove atomicity|
|Envelope (ApiResponse[T])|v2 response wrapper: success + data + error|
|httpOnly cookie|Token cookie inaccessible to JS (anti-XSS)|
|SameSite=Strict|Cookie sent only on same-site requests|
|CSRF double-submit|Cookie + matching header required on state changes|
|Refresh rotation|Old refresh token invalidated on each use|
|Token family|Group of refresh tokens; reuse of any revokes all|
|TOTP|Time-based one-time password (2FA)|
|Token versioning|User-scoped version that invalidates all tokens on change|
|Account lockout|Freeze after 5 failed attempts (15 min)|
|Cursor pagination|SQL-level paging via opaque cursor (flat memory)|
|Circuit breaker|Fails-fast wrapper for notifications|
|Idempotency key|Client-supplied key preventing duplicate operations|
|Alembic|Migration tool; SQLite↔PostgreSQL round-trip tested|
|Analyzr|Natural-language search utility (53 tests)|
|Inventory|docs/INVENTORY.md — forensic module classification|
|ADR|Architecture Decision Record|
|Audit score|SELF_AUDIT.md rubric: 3.8 → 8.1/10|

## Related Documents

|Document|Relationship|
|---|---|
|[PRD.md](../product/PRD.md)|Feature vocabulary|
|[TechSpec.md](../technical/TechSpec.md)|Technical terms|
|[AppFlow.md](../design/AppFlow.md)|Screen-level terms|
|[Schema.md](../technical/Schema.md)|Data terms (TBL-*)|
|[ImplementationPlan.md](../project/ImplementationPlan.md)|Task vocabulary|
|[Tracker.md](../project/Tracker.md)|Status terms|
|[Rules.md](../project/Rules.md)|Convention terms|
|[API.md](../technical/API.md)|API vocabulary|
|[SecurityAndCompliance.md](../technical/SecurityAndCompliance.md)|Security terms|
|[Testing.md](../technical/Testing.md)|Test vocabulary|
|[Deployment.md](../technical/Deployment.md)|Ops terms|
|[RiskRegister.md](../project/RiskRegister.md)|Risk vocabulary|
