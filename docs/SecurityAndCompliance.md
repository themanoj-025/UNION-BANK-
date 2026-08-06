# SecurityAndCompliance — UNION-BANK-: Security & Compliance

| Field | Value |
|---|---|
| Version | v0.1 |
| Last Updated | 2026-08-06 |
| Owner | Security Engineer |
| Status | Approved |

---

## 1. Threat Model (STRIDE)

| Threat | Asset | Mitigation |
|---|---|---|
| Spoofing | User identity | RS256 JWT + TOTP 2FA + token versioning |
| Tampering | Money/balance | Atomic savepoints, row locks, CHECK constraints, optimistic versioning |
| Repudiation | Transfers/admin actions | Transaction ledger + admin audit tracking |
| Info disclosure | PII/financial | httpOnly cookies, TLS, encryption at rest, log masking |
| DoS | API | IP rate limiting + account rate limiting + lockout |
| Elevation | Admin role | TOTP-enforced admin login + role checks |
| CSRF | State changes | Double-submit cookie + header |
| XSS | Client session | httpOnly cookies (no localStorage) + CSP + input validation |
| SQLi | DB | Parameterized queries + Pydantic validation + test fixtures |

Full model: `docs/THREAT_MODEL.md`.

## 2. Auth & Authz

| Layer | Policy |
|---|---|
| Access token | RS256 JWT, 15 min, httpOnly Secure SameSite=Strict cookie |
| Refresh token | 7-day, bcrypt-hashed at rest, rotated per use, family revocation on reuse |
| 2FA | TOTP (pyotp), enrollment + confirm flow, enforced on admin |
| CSRF | Double-submit: cookie + `X-CSRF-Token` header on all state changes |
| Lockout | 5 failed logins → 15-min freeze (per account) |
| Rate limit | IP-based (all endpoints) + account-based (5 money ops/hr) |

## 3. Data Classification

| Class | Examples | Handling |
|---|---|---|
| Credentials | password hashes, TOTP secrets, refresh hashes | Argon2/bcrypt, never logged |
| PII | email | Encrypted at rest, masked in logs |
| Financial | balances, transactions | Encrypted at rest (volume), role-scoped access |
| Public | loan rates, health | No restriction |

## 4. Encryption Standards

- Transit: TLS 1.2+ (prod ingress).
- At rest: volume encryption (DB).
- Tokens: RS256 signatures; refresh tokens bcrypt-hashed (ADR-0002).

## 5. Compliance Checklist

- [ ] Defense in depth documented in ADR-0002 + THREAT_MODEL.md
- [ ] SQLi/XSS/CSRF fixtures run in CI
- [ ] Secret scan job in CI (10 jobs)
- [ ] Data retention + idempotency policy (ADR-0004)
- [ ] `except: pass` banned by CI grep
- [ ] Portfolio scope: no regulated financial compliance claims (not PCI/SOC2-scoped)

## 6. Incident Response (Outline) — see docs/RUNBOOK.md

1. Detect: alert on metrics (5xx, auth failures, lockouts).
2. Triage: identify surface (auth, money movement, infra).
3. Mitigate: revoke token families, freeze accounts, roll back deploy.
4. Recover: verify ledger consistency (money conservation invariant).
5. Postmortem: update THREAT_MODEL + Tracker changelog ≤ 48h.

## 7. Related Documents

| Document | Relationship |
|---|---|
| API.md | Auth endpoints |
| Rules.md | Security baseline (Section 6) |
| RiskRegister.md | Security risks |
| Schema.md | Sensitive data map |
