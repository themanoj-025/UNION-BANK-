# UNION-BANK- — Architecture

```mermaid
graph TB
    subgraph Interfaces ["User Interfaces"]
        A[CLI - main.py + ui.py]
        B[Flask Web - webapp.py]
        C[FastAPI API - api.py]
    end

    subgraph Auth ["Authentication"]
        D[bank.py - Login/Auth]
        E[JWT Token (API)]
        F[Flask Session (Web)]
        G[bcrypt Verify (CLI)]
        H[Rate Limiter<br/>5 fails → 15min lockout]
    end

    subgraph Core ["Core Business Logic"]
        I[bank.py]
        J[account.py]
        K[admin.py]
    end

    subgraph Storage ["JSON File Storage"]
        L[data/accounts.json]
        M[data/transactions.json]
        N[data/savings_goals.json]
        O[backup.py]
    end

    Interfaces --> Auth
    Interfaces --> Core
    Auth --> Core
    Core --> Storage
    Auth --> H
```

## Key Patterns

- **Three interfaces**: CLI (Rich library), Flask web (HTML templates), FastAPI (REST with JWT)
- **JSON storage**: File-based with automatic `.bak` backup before every write
- **Corruption recovery**: `load_json()` falls back to `.bak` if primary file is corrupted
- **Rate limiting**: 5 failed login attempts → 15-minute lockout (persisted in `login_attempts.json`)
- **Session timeout**: 5 minutes inactivity → auto-logout on both CLI and web interfaces
- **Account freeze**: Admin can freeze/unfreeze accounts, blocking all transactions
- **Coverage gate**: `--cov-fail-under=80` enforces minimum 80% test coverage
