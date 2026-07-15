# ADR-0002: Security Hardening — Token Strategy, 2FA, and CSRF

**Date:** July 2026  
**Status:** Accepted  
**Deciders:** Union Bank Security Team  

---

## Context

The initial audit (scoring 3.8/10) identified several critical security gaps:

1. **Hardcoded admin credentials** — Default "simon/simon123" credentials created at startup
2. **In-memory refresh token storage** — `_refresh_tokens: dict[str, dict]` in `api/common.py` was lost on server restart and couldn't be shared across processes
3. **No token invalidation** — Password changes did not invalidate existing JWTs
4. **No multi-factor authentication** — Admin accounts had no 2FA option
5. **No CSRF protection** — State-changing endpoints had no origin validation

---

## Decision 1: DB-Backed Refresh Tokens

**Decision:** Replace the in-memory `_refresh_tokens` dict with a `refresh_tokens` table in SQLite, accessed via `SqlAlchemyRefreshTokenRepository`.

**Alternatives Considered:**
- **Redis-based storage**: Better performance for high-scale deployments, but adds infrastructure dependency. Chose SQLite for simplicity since the app already uses it.
- **JWT-only (no refresh tokens)**: Simpler but forces users to re-authenticate every 15 minutes. Poor UX.

**Consequences:**
- ✅ Tokens survive server restarts
- ✅ Token revocation through `revoke()` and `revoke_all_for_account()`
- ✅ Expired token cleanup via `clean_expired()`
- ❌ SQLite is not ideal for high-write token storage at scale (10M+ users). Migrate to Redis or Postgres when scaling.

---

## Decision 2: Token Version Validation

**Decision:** Include a `token_version` claim in every access JWT that matches the current version stored in the `token_versions` table. The auth dependencies (`get_current_customer`, `get_current_admin`) validate this on every request.

**Alternatives Considered:**
- **Token blacklist**: Store revoked JWT IDs in a database and check every request. O(n) query growth over time. Rejected in favor of version-based invalidation.
- **Short expiry only**: Relying solely on 15-minute JWT expiry means a stolen token is valid for 15 minutes. Version-based invalidation closes this window immediately on password change.

**Consequences:**
- ✅ Password changes instantly invalidate all existing sessions
- ✅ No unbounded token blacklist table
- ✅ Works well with the existing `TokenVersionModel` infrastructure
- ❌ Requires a DB read on every request (acceptable — the account lookup already does this)
- ❌ Token version is only checked for access tokens (not refresh tokens). Refresh tokens are validated against the DB directly.

---

## Decision 3: TOTP-Based 2FA for Admin Accounts

**Decision:** Add optional TOTP-based two-factor authentication using the `pyotp` library. Admin users can enable/disable 2FA via API endpoints. When enabled, the login flow requires a 6-digit TOTP code.

**Alternatives Considered:**
- **SMS-based 2FA**: Requires SMS infrastructure, prone to SIM-swap attacks. Rejected.
- **Hardware security keys (WebAuthn)**: More secure but requires browser support and hardware. High implementation complexity. Deferred to future.
- **Email-based 2FA**: Weaker than TOTP (email accounts can be compromised). Rejected.

**Consequences:**
- ✅ Significantly reduces risk of admin credential compromise
- ✅ No infrastructure dependencies (TOTP is fully offline)
- ✅ Compatible with authenticator apps (Google Authenticator, Authy, 1Password)
- ❌ TOTP setup requires the admin to be already authenticated (chicken-and-egg for initial setup — mitigated by bootstrap CLI)
- ❌ No backup codes implemented (deferred — user can disable 2FA if they lose access)

---

## Decision 4: CSRF Protection via Origin/Referer Validation

**Decision:** Add a middleware that validates the `Origin` and `Referer` headers on state-changing requests (POST, PUT, DELETE, PATCH). Invalid origins are logged but not blocked by default.

**Rationale:** The API uses Bearer tokens in `Authorization` headers, which are inherently immune to traditional CSRF attacks (cookies are not sent with cross-origin requests). The middleware is a defense-in-depth measure that logs suspicious cross-origin requests for monitoring.

**Alternatives Considered:**
- **Double-submit cookie pattern**: Incompatible with Bearer-token-only auth. Requires cookie-based tokens.
- **SameSite cookies**: Not applicable (no cookies used).
- **No CSRF protection**: Reasonable for Bearer-token APIs. The middleware was added as a lightweight monitoring measure.

**Consequences:**
- ✅ Logs cross-origin origin violations for security monitoring
- ✅ No false positives (requests without Origin/Referer headers from CLI tools are allowed)
- ✅ No impact on the Bearer-token flow
- ❌ Does not block invalid origins (blocking would break CLI clients that don't send Origin headers)

---

## Decision 5: Remove Hardcoded Admin Credentials

**Decision:** Remove the `seed_default_admin()` startup handler from `api.py` and the `_init_admin()` call from `admin.py`. Replace with a CLI bootstrap command: `python main.py create-admin`.

**Alternatives Considered:**
- **First-run setup wizard**: Over-engineered for a CLI-only bootstrap. Rejected.
- **Environment variable admin credentials**: Better than hardcoded but still embeds credentials in configuration. Rejected in favor of interactive bootstrap.

**Consequences:**
- ✅ No hardcoded credentials anywhere in the codebase
- ✅ Admin is prompted for a strong password at creation time
- ✅ Bootstrap command enforces password strength validation
- ❌ First-time users must run the bootstrap command before using the admin panel

---

## Decision Summary

| Decision | Status | Priority | Complexity |
|----------|--------|----------|------------|
| DB-backed refresh tokens | ✅ Implemented | Critical | Medium |
| Token version validation | ✅ Implemented | Critical | Low |
| TOTP 2FA for admins | ✅ Implemented | High | Medium |
| CSRF Origin/Referer logging | ✅ Implemented | Medium | Low |
| Remove hardcoded credentials | ✅ Implemented | Critical | Low |
| THREAT_MODEL.md documentation | ✅ Implemented | Medium | Low |
