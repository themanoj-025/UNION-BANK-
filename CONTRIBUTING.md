# Contributing to Union Bank Management System

Thank you for your interest in contributing! This project is a production-grade banking API portfolio showcase. All contributions should match the engineering standards demonstrated in the codebase.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Branch Strategy](#branch-strategy)
- [Conventional Commits](#conventional-commits)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Release Process](#release-process)
- [Security](#security)

---

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

---

## Getting Started

### Prerequisites

- **Python 3.11+** — required for backend services
- **Node.js 20+** — required for frontend and git tooling (husky, commitlint)
- **Docker** (optional) — for containerized development

### Setup (3 minutes)

```bash
# 1. Clone and enter the repository
git clone https://github.com/themanoj-025/UNION-BANK-.git
cd UNION-BANK-

# 2. Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install backend dependencies
pip install -e .
pip install -r requirements.txt

# 4. Install git hooks and tooling
npm install

# 5. Copy environment config (optional for development)
cp .env.example .env

# 6. Run tests to verify setup
python -m pytest tests/ -v --tb=short
```

### Install Git Hooks

Husky is configured via `npm install` (step 4 above). Verify hooks are active:

```bash
npx husky
```

This installs:
- **commit-msg** — runs `commitlint` to enforce [Conventional Commits](#conventional-commits)

---

## Project Structure

```
├── src/unionbank/             # Canonical Python package
│   ├── domain/                # Pure domain entities, enums, interest logic
│   ├── application/           # Services + protocol interfaces
│   │   ├── services.py        # Business logic (transfers, auth, loans)
│   │   ├── async_services.py  # Async variants (migration in progress)
│   │   ├── interfaces.py      # Protocol-based DI contracts
│   │   └── notifications.py   # Notification service
│   ├── infrastructure/        # Repositories, DB, cache, metrics
│   │   ├── repositories.py    # SQLAlchemy repositories
│   │   ├── database.py        # Engine/session management
│   │   ├── cache.py           # Redis + NullCache
│   │   ├── persistence.py     # Models, mappers, base
│   │   ├── mappers.py         # Domain ↔ ORM mapping
│   │   └── container.py       # DI container wiring
│   ├── entrypoints/           # API + CLI
│   │   ├── api/               # FastAPI routes (v1, v2)
│   │   │   ├── main.py        # FastAPI app + lifespan
│   │   │   ├── v2.py          # V2 envelope-wrapped router
│   │   │   ├── models.py      # Pydantic request/response models
│   │   │   └── common.py      # Auth helpers, rate limiting
│   │   └── cli/               # CLI entry points
│   ├── utils/                 # Auth, formatting, validation, analyzr
│   └── config.py              # Settings (env-driven via pydantic-settings)
│
├── frontend/                  # React SPA
├── tests/                     # Backend test suite (375+ tests)
├── docs/                      # ADRs, threat model, runbook, self-audit
│   ├── adr/                   # Architecture Decision Records
│   ├── SELF_AUDIT.md          # Audit reconciliation
│   ├── THREAT_MODEL.md        # Security analysis
│   └── RUNBOOK.md             # Incident response
├── monitoring/                # Prometheus + Grafana configs
├── k8s/                       # Kubernetes manifests (reference)
├── scripts/                   # Docker entrypoint, load testing, analyzr
│
├── .husky/                    # Git hooks (commitlint)
├── commitlint.config.js       # Commit message linting rules
├── package.json               # Root-level git tooling
├── pyproject.toml             # Python project metadata
└── Dockerfile                 # Multi-stage build
```

**Key architectural principle:** Clean layering with dependency inversion — domain has zero infrastructure imports, application depends on protocols, infrastructure implements protocols.

---

## Branch Strategy

We use a **trunk-based development** model with short-lived feature branches:

```
main                     ← Always deployable, protected
├── feat/my-feature      ← New features
├── fix/bug-description  ← Bug fixes
├── refactor/area        ← Refactoring
├── docs/topic           ← Documentation
├── test/area            ← Test additions
└── chore/area           ← Tooling, CI, dependencies
```

**Rules:**
- `main` is always green — all CI jobs must pass
- Branch off `main`, merge back via Pull Request
- Squash-merge into `main` (keeps history clean)
- Delete the branch after merge
- Never push directly to `main`

---

## Conventional Commits

Every commit message **must** follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): description

[optional body]
[optional footer]
```

**Allowed types:**

| Type     | When to Use                          | Version Bump |
|----------|--------------------------------------|--------------|
| `feat`   | A new feature                        | minor        |
| `fix`    | A bug fix                            | patch        |
| `refactor` | Code change that neither fixes nor adds | patch    |
| `docs`   | Documentation only                    | patch        |
| `test`   | Adding or correcting tests            | patch        |
| `chore`  | Tooling, CI, dependency changes       | patch        |
| `style`  | Formatting, linting (no logic change) | patch        |
| `perf`   | Performance improvement               | patch        |

**Scopes** (use one): `api`, `cli`, `frontend`, `auth`, `db`, `ci`, `docs`, `tests`, `infra`, `deps`, `analyzr`

**Examples:**

```
feat(auth): add account-based rate limiting on money-movement endpoints

Implement per-account rate limiter in Redis that tracks deposits,
withdrawals, and transfers separately from the IP-based limiter.
Max 5 operations per account per hour.

Closes #143
```

```
fix(api): correct health endpoint to check DB connectivity

Previously returned 200 even when database was unreachable.
Now runs SELECT 1 and returns 503 on failure.
```

```
chore(deps): pin fastapi to >=0.115.0 in requirements.txt
```

**Enforcement:** `commitlint` runs as a `commit-msg` git hook (via husky) AND in CI. Invalid commit messages are rejected.

---

## Development Workflow

### 1. Pick an Issue

Check the [Issues](https://github.com/themanoj-025/UNION-BANK-/issues) tab for open tasks. Comment to claim one.

### 2. Create a Branch

```bash
git checkout main
git pull origin main
git checkout -b feat/your-feature-name
```

### 3. Make Changes

- Follow [coding standards](#coding-standards) below
- Add or update tests for your changes
- Keep changes focused and minimal

### 4. Commit

```bash
git add <files>
git commit -m "feat(scope): your message here"
```

If `commitlint` rejects your message, fix the format and retry.

### 5. Push and Open a PR

```bash
git push origin feat/your-feature-name
```

Then open a Pull Request against `main` with:
- **Clear title** following Conventional Commits format
- **Description** of what changed and why
- **Related issue** number (e.g., `Closes #42`)

### 6. CI Checks

All PRs must pass these CI jobs:

| Job | Required | Description |
|-----|----------|-------------|
| Backend tests (3.11, 3.12) | ✅ | Full pytest suite |
| Frontend tests | ✅ | Vitest + React Testing Library |
| Frontend lint + build | ✅ | oxlint + Vite build |
| Security tests | ✅ | Password leak, JWT, SQLi |
| Docker build | ✅ | Multi-stage build verification |

**Non-blocking** (reported but allowed to fail): mutation testing, schemathesis fuzz, link checks.

---

## Coding Standards

### Python

- **Format:** Ruff (configured in `pyproject.toml`)
- **Type hints:** Required on all function signatures
- **Docstrings:** Google style for public APIs
- **Imports:** Standard library → third-party → project (`unionbank.*`)
- **No circular imports:** Use Protocol-based DI to break cycles
- **No bare `except: pass`:** Caught by CI — always log exceptions

### Frontend (React/JSX)

- **Format:** oxlint (configured in `frontend/.oxlintrc.json`)
- **Components:** Functional components with hooks
- **State management:** React context + hooks (no Redux)
- **API calls:** Via `api.js` axios client (typed via zod schemas)

### Domain Purity

The `domain/` package must have **zero imports** from outside `domain/` and the Python stdlib:

```python
# ✅ Good — domain/interest.py
def calculate_monthly_interest(balance: float, annual_rate_pct: float = 3.5) -> float:
    ...

# ❌ Bad — domain/ must not import config, infrastructure, or application
from unionbank.config import settings  # BANNED in domain/
```

---

## Testing

### Backend Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov --cov-report=term

# Run specific test file
python -m pytest tests/test_services.py -v

# Run security tests
python -m pytest tests/test_security.py tests/test_password_leak.py -v
```

### Frontend Tests

```bash
cd frontend
npm test               # Vitest run
npm run test:watch    # Watch mode
```

### Test Targets

| Test File | What It Covers |
|-----------|---------------|
| `test_services.py` | Service layer business logic |
| `test_features.py` | Feature-level integration |
| `test_api_integration.py` | API endpoint end-to-end |
| `test_integration.py` | Database integration + concurrency |
| `test_property_based.py` | Hypothesis property-based invariants |
| `test_edge_cases.py` | Error paths and boundary conditions |
| `test_security.py` | Security vulnerability tests |
| `test_password_leak.py` | Password hash leak detection |
| `test_smoke.py` | Module import verification |
| `test_analyzr.py` | Natural-language search engine |
| `test_migrations.py` | Alembic upgrade/downgrade |

### Coverage Target

- **Overall:** ≥ 65% (backend)
- **Critical files** (`services.py`, `repositories.py`): ≥ 80%
- **Frontend:** > 0 tests per component with conditional rendering

---

## Submitting a Pull Request

1. Ensure your branch is up to date with `main`:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. Run the full test suite locally:
   ```bash
   python -m pytest tests/
   cd frontend && npm test
   ```

3. Push your branch and open a PR against `main`.

4. In the PR description:
   - Explain **what** changed and **why**
   - Reference any related issues
   - Note any breaking changes
   - Add screenshots for UI changes

5. Wait for CI checks to pass and address any review feedback.

---

## Release Process

1. All Phase/feature work is merged to `main`
2. Create a new version tag:
   ```bash
   git tag -a v2.3.0 -m "feat: add CSV export API"
   git push origin v2.3.0
   ```
3. Update `CHANGELOG.md` with the new version entry
4. GitHub Actions builds and tags the release automatically

---

## Security

- **No secrets in code:** Use environment variables and `.env` (gitignored)
- **No passwords in API responses:** Enforced by `test_password_leak.py`
- **Report vulnerabilities:** Open a GitHub Issue with the "security" label
- See [SECURITY.md](SECURITY.md) for the full policy and [THREAT_MODEL.md](docs/THREAT_MODEL.md) for the threat analysis

---

## Questions?

Open a [Discussion](https://github.com/themanoj-025/UNION-BANK-/discussions) or ask in an Issue. We're happy to help!
