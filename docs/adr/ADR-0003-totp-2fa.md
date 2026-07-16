# ADR-0003: TOTP 2FA Completion

**Status:** Implemented  
**Date:** 2026-07-16  
**Author:** Union Bank Dev Team  
**Deciders:** Architecture Review Board  

---

## Context

The original codebase had TOTP 2FA fields (`totp_secret`, `totp_enabled`) on the Admin entity, repository methods (`update_totp()`), and API setup/verify/disable endpoints — but the login flow never checked TOTP before issuing a JWT. This was a **phantom feature**: advertised in the data model and API surface, but non-functional.

Two independent security audits flagged this as a critical finding. The question was: **complete the implementation or remove it?**

## Decision

**Complete the TOTP 2FA implementation end-to-end.** The feature was already partially built (data model, repository, endpoints). The missing piece was the enforcement during login — adding that completed the feature without requiring a new design.

## Implementation

### Changes Made

1. **Admin login (`api.py` / `api/v2.py`):** After password verification succeeds, check `admin_user.totp_enabled`. If enabled, require a valid TOTP code before issuing tokens. Returns `428 Precondition Required` if the code is missing, `401 Unauthorized` if invalid.

2. **Enrollment flow:**
   - `GET /api/admin/2fa/setup` — Generates a new TOTP secret, returns provisioning URI and QR code parameters
   - `POST /api/admin/2fa/verify` — Verifies a 6-digit code to enable 2FA
   - `GET /api/admin/2fa/status` — Checks if 2FA is enabled for the current admin

3. **Disabling:** `POST /api/admin/2fa/disable` — Requires the current TOTP code to disable (anti-lockout protection).

4. **No customer 2FA:** TOTP was explicitly scoped to admin accounts only, following the principle of least privilege for the most sensitive role.

### Technical Details

- **Library:** `pyotp` (TOTP implementation, RFC 6238 compliant)
- **Valid window:** ±1 interval (30 seconds) — allows for minor clock skew
- **Secret storage:** `totp_secret` (VARCHAR, nullable) and `totp_enabled` (BOOLEAN) on the `admins` table
- **Secret generation:** `pyotp.random_base32()` — cryptographically random 32-character base32 secret

## Consequences

### Positive

- **Completed security feature** — no more phantom functionality
- **Defense in depth** — even if admin password is compromised, attacker needs TOTP code to log in
- **Minimal code change** — reused existing data model and endpoints
- **Backward compatible** — admin accounts without 2FA continue to work as before

### Negative

- **TOTP only for admin** — customer accounts do not have 2FA (acceptable for current scope)
- **No backup codes** — if admin loses access to their TOTP device, the database must be manually updated to disable 2FA (documented in RUNBOOK.md)
- **QR code not rendered** — the provisioning URI is returned as a string; the frontend is responsible for rendering it as a QR code (e.g., using `qrcode.js`)

## Alternatives Considered

1. **Remove the feature entirely** — Simpler, but would lose a valuable security control. Rejected because TOTP 2FA is an expected feature for admin panels in banking applications.

2. **Use WebAuthn / FIDO2** — More secure (phishing-resistant), but significantly more complex to implement and requires browser support. Deferred as a future enhancement.

3. **Email-based 2FA** — Easier for users, but less secure (email can be intercepted). Rejected for admin accounts where security is the priority.

## References

- [RFC 6238: TOTP: Time-Based One-Time Password Algorithm](https://datatracker.ietf.org/doc/html/rfc6238)
- [THREAT_MODEL.md — T8: TOTP 2FA Bypass](../THREAT_MODEL.md)
- [RUNBOOK.md — TOTP 2FA recovery procedure](../RUNBOOK.md)
