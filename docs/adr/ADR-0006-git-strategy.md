# ADR-0006: Git Strategy — Branching, Commits, and Releases

**Status:** Adopted  
**Date:** 2026-07-17  
**Driver:** Phase 8 — Git Hygiene  

---

## Context

The project had no consistent git strategy: commits were generic ("migration"), there were no semver tags beyond the pre-audit baseline, and the contribution guide was outdated. For a portfolio project that should demonstrate senior engineering process, the commit history itself should read as professional work.

## Decision

### 1. Branch Strategy: Trunk-Based with Feature Branches

```
main                ← Always deployable, protected
├── feat/*          ← Feature branches (merged via PR)
├── fix/*           ← Bugfix branches
├── refactor/*      ← Refactoring branches
├── docs/*          ← Documentation branches
├── test/*          ← Test-only branches
└── chore/*         ← Chore/tooling branches
```

**Rules:**
- `main` is always green (all CI jobs pass)
- Feature branches branch off `main`, merge back via PR
- No direct pushes to `main` (PR required)
- Squash-merge or regular merge with meaningful message
- Delete branch after merge

### 2. Conventional Commits

Every commit message from Phase 8 forward **must** follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): description

[optional body]
[optional footer]
```

**Types:**
| Type | Usage |
|------|-------|
| `feat` | New feature (minor version bump) |
| `fix` | Bug fix (patch version bump) |
| `refactor` | Code change that neither fixes nor adds |
| `docs` | Documentation only |
| `test` | Test addition or correction |
| `chore` | Tooling, CI, dependencies |
| `style` | Formatting, linting (no logic change) |

**Scopes (examples):** `api`, `cli`, `frontend`, `auth`, `db`, `ci`, `docs`, `tests`, `infra`

**Enforcement:** `commitlint` with `@commitlint/config-conventional` runs as a `commit-msg` git hook (via husky). CI also runs `commitlint` on PR commits.

### 3. Release Strategy: Semver with Tagged Releases

```
v<major>.<minor>.<patch>
```

- Tags are created after each completed phase (or significant milestone)
- CHANGELOG.md follows [Keep a Changelog](https://keepachangelog.com/) format
- Release notes are generated from commit messages between tags

**Current release:** `v2.2.0` (Phase 1–7 complete)

### 4. CI Gating

All PRs must pass the following CI jobs as named checks:
- `backend-tests` (Python 3.11 + 3.12)
- `frontend-tests` (Vitest)
- `frontend-lint` (oxlint)
- `frontend-build` (Vite)
- `security-tests`
- `docker-build`

Non-blocking (reported but allowed to fail):
- `mutation-testing` (mutmut)
- `schemathesis-fuzz`
- `secrets-check`
- `link-check`

### 5. Commit Style Guidelines

- First line ≤ 72 characters (hard limit: 100)
- Body wrapped at 72 characters
- Use imperative mood ("fix auth" not "fixed auth" or "fixes auth")
- Reference issues/PRs in footer: `Closes #42`, `Refs #123`

## Consequences

**Positive:**
- Commit history becomes a readable changelog
- Automated release notes from commits
- CI enforces consistency without manual oversight
- PRs tell a clear story to reviewers

**Negative:**
- Overhead of committing with proper format (mitigated by commitlint hints)
- Requires rebasing historical commits is not feasible for existing history

**Mitigation:**
- `commitlint` provides helpful error messages on invalid commits
- Pre-commit hook catches issues before push
- `git log --oneline` becomes instantly readable after adoption date

---

## Compliance

Start date: 2026-07-17 (Phase 8 implementation date)

All commits after this date MUST follow Conventional Commits format. Historical commits are documented in CHANGELOG.md but not retroactively modified.

Enforcement:
- `.husky/commit-msg` — commitlint pre-commit hook
- `.github/workflows/commitlint.yml` — CI check on PR commits
- `commitlint.config.js` — configuration file at repo root

---

*Approved by: Engineering team (Phase 8)*
