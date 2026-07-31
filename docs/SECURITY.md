# Security Policy for UNION-BANK-

## Reporting a Vulnerability

If you discover a security vulnerability in the Union Bank Management System, please report it privately.

**How to report:**
- Open a private security advisory on GitHub (if this repository is public).
- Email **manojjana.0025@gmail.com** directly. This contact is also listed in our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- If neither channel works, open a standard issue with the label `security` without including exploit details.

**Expectations:**
- We will acknowledge receipt within 5 business days.
- We will provide an assessment and expected fix timeline within 10 business days.
- Please refrain from public disclosure until a fix is released.

## Security Measures

### Implemented
- **Password hashing:** All passwords are hashed using bcrypt with salt before storage. Plain-text passwords are never stored.
- **Rate limiting:** Account lockout after 5 failed login attempts (15-minute cooldown). Tracked per account or admin username in `login_attempts.json`.
- **Session timeout:** Automatic logout after 5 minutes of inactivity (CLI and web interfaces).
- **JWT authentication (API):** FastAPI uses signed JWT tokens (HS256) with 24-hour expiry. Separate customer and admin token types.
- **Session-based auth (Web):** Flask sessions with server-side secret key.
- **Input validation:** Regex-based validation for email (format), phone (Indian format), password strength (min 8 chars, uppercase, lowercase, digit), and name format.
- **Atomic file writes:** JSON files are written using a temp-file-then-rename pattern to prevent data corruption on crash.
- **Automatic backups:** `.bak` files are created before every write operation.
- **Corruption recovery:** The `load_json` function automatically falls back to `.bak` backup if the primary JSON file is corrupted.
- **Account freeze:** Admin can freeze/unfreeze accounts, preventing all transactions.
- **Logging:** All sensitive operations (login successes/failures, transactions, password changes, account closure, admin actions) are logged with timestamps.

### Not Implemented
- **No HTTPS:** All communication is plain HTTP. Deploy behind a reverse proxy with TLS for production.
- **CORS wide open:** API `allow_origins=["*"]` — should be restricted in production.
- **Password masking:** CLI registration shows passwords as plain text (no masking).
- **Admin credentials in JSON:** Admin credentials are stored in a JSON file — a security concern.
- **Default JWT secret:** `JWT_SECRET` defaults to a hardcoded development secret. **Must be changed in production.**
- **No 2FA:** Two-factor authentication is not implemented.
- **No CAPTCHA:** No bot protection on registration or login forms.

## Authentication & Authorization

### Interfaces
| Interface | Auth Method | Session |
|---|---|---|
| CLI | Password (bcrypt verify) | In-memory (process lifetime) |
| Flask Web | Flask sessions (bcrypt verify) | Cookie-based, 5-min timeout |
| FastAPI API | JWT (HS256, 24h expiry) | Token-based |

### Role Model
| Role | Access |
|---|---|
| Customer | Self-service (own account, transactions, savings goals) |
| Admin | Full system access (all accounts, freeze/delete, statistics, reports) |

### Rate Limiting
- 5 failed login attempts → 15-minute lockout.
- Tracked per account number (customer) or username (admin).
- Lockout persists across application restarts (stored in `login_attempts.json`).

## Environment Variables

| Variable | Sensitivity | Notes |
|---|---|---|
| `JWT_SECRET` | **Critical** | JWT signing secret. **Change from default before production.** |
| `FLASK_SECRET_KEY` | High | Flask session signing key. Auto-generated if not set. |

## Data Storage Security

This project uses JSON file-based storage in the `data/` directory:

| File | Contents | Sensitivity |
|---|---|---|
| `accounts.json` | Account details, bcrypt password hashes, balances | **Critical** |
| `transactions.json` | Full transaction history | High |
| `login_attempts.json` | Failed login tracking | Medium |
| `savings_goals.json` | Savings goal data | Low |
| `admin.json` (if used) | Admin credentials | **Critical** |

**Important:** These JSON files are **unencrypted** and should have restricted filesystem permissions (`chmod 600` on Linux). The `data/` directory should not be publicly accessible.

## Deployment Security

1. **Change default secrets:** Edit `JWT_SECRET` in `.env` or environment. The default dev secret is publicly known.
2. **Restrict CORS:** Change `allow_origins=["*"]` in `api.py` to specific origins.
3. **Enable HTTPS:** Deploy behind nginx/Caddy with TLS. The Flask and FastAPI servers do not natively support HTTPS.
4. **Firewall:** Restrict access to port 5000 (Flask) and port 8000 (FastAPI) to trusted networks.
5. **Admin credentials:** Change default admin password immediately on first deployment.
6. **Regular backups:** The automatic `.bak` files provide basic recovery. Implement off-site backups for production use.

## Dependency Security

Regularly audit dependencies:

```bash
pip-audit -r requirements.txt
```

Key packages to monitor:
- `bcrypt` — Password hashing (keep updated for CVE patches).
- `PyJWT` — JWT implementation.
- `flask` — Web framework.
- `fastapi` / `uvicorn` — API server.
- `fpdf2` — PDF generation library.
