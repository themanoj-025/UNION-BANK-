# ADR-0001: Consolidate to a Single Service Layer

## Status

Accepted (implemented July 15, 2026)

## Context

The codebase had two parallel and independent service/repository layers:

1. **Old layer** (`services.py`, `repositories.py` at project root) — standalone functions that created their own DB sessions, performed business logic, and returned result types. Used primarily by the CLI interface (`bank.py`, `account.py`, `admin.py`) and some v1 API endpoints.

2. **New layer** (`application/services.py`, `infrastructure/repositories.py`) — protocol-based, class-based services and repositories wired through a dependency injection container (`container.py`). Used by the v2 API and some v1 API endpoints.

The old layer was a legacy of the JSON-file-based era and was never fully migrated. This created several problems:

- **Bugs fixed in one layer were not fixed in the other.** For example, a security fix in `application/services.py`'s `close_account()` method would leave the old `services.py`'s `process_close_account()` still vulnerable.
- **Duplicate code** — `_utcnow()` was copy-pasted across 6 files. `_map_account()` and `_map_transaction()` existed in both layers.
- **Developer confusion** — New contributors couldn't tell which layer was canonical.
- **Inconsistent behavior** — The old layer used `float` for monetary values in some places while the new layer used `Decimal`.

## Decision

Delete the old `services.py` and `repositories.py` files entirely. Migrate all callers (CLI, v1 API) to use the container-based services from `application/services.py` and `infrastructure/repositories.py`.

### Migration summary

| Caller | Old import | New usage |
|--------|-----------|-----------|
| `api.py` (v1) | `from services import process_deposit, ...` | `container.transaction_service().deposit(...)` |
| `account.py` (CLI) | `from services import process_deposit, ...` | `container.transaction_service().deposit(...)` |
| `scripts/migrate_json_to_sqlite.py` | `from repositories import AccountRepository, ...` | `from infrastructure.repositories import SqlAlchemyAccountRepository, ...` |

### Dead code discovered

The old `services.py` contained 8 functions that were already unused:

- `get_bank_statistics()` — admin.py already used `container.admin_service().get_statistics()`
- `process_freeze_account()` — admin.py already used `container.admin_service().freeze_account()`
- `process_unfreeze_account()` — admin.py already used `container.admin_service().unfreeze_account()`
- `process_delete_account()` — admin.py already used `container.admin_service().delete_account()`
- `admin_authenticate()` — admin.py already used `container.auth_service().admin_login()`
- `create_savings_goal()` — account.py already used `container.savings_goal_service().create_goal()`
- `contribute_to_goal()` — account.py already used `container.savings_goal_service().contribute()`
- `delete_savings_goal()` — account.py already used `container.savings_goal_service().delete_goal()`

## Alternatives Considered

### Keep both layers with a deprecation wrapper
Rejected because it would have maintained the maintenance burden without clear benefit. The old layer had few callers, making a direct migration straightforward.

### Incrementally migrate function-by-function
Rejected because it would leave the codebase in a half-migrated state for weeks. A coordinated cutover was feasible since all callers were identified and could be updated simultaneously.

## Consequences

**Positive:**
- Single canonical service layer — reduced maintenance burden
- All monetary operations consistently use `Decimal`
- All DB access goes through the DI container
- Reduced codebase size (~400 lines deleted)
- All tests pass after migration

**Negative:**
- CLI now depends on the DI container, making it slightly harder to test in isolation (though the fake repositories in `tests/fakes.py` mitigate this)
- The migration required touching 4 files simultaneously (api.py, account.py, scripts/migrate_json_to_sqlite.py, plus deleting the old files)

## Related Artifacts

- [Architecture diagram](../CURRENT_STATE.md)
- [Service layer code](../application/services.py)
- [Repository layer code](../infrastructure/repositories.py)
