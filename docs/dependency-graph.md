# Dependency Graph — UNION-BANK-

## Module Dependency Map

```
main.py (Entry Point)
  ├── webapp.py
  │     ├── bank.py
  │     │     ├── account.py
  │     │     ├── utils.py
  │     │     └── logger.py
  │     ├── account.py
  │     │     ├── utils.py
  │     │     └── logger.py
  │     ├── admin.py
  │     │     ├── bank.py
  │     │     ├── account.py
  │     │     ├── utils.py
  │     │     └── logger.py
  │     ├── api.py
  │     │     ├── bank.py
  │     │     ├── account.py
  │     │     ├── utils.py
  │     │     └── logger.py
  │     ├── utils.py
  │     └── logger.py
  │
  └── ui.py (CLI)
        ├── bank.py
        ├── account.py
        ├── utils.py
        └── logger.py

seed_data.py
  ├── bank.py
  └── account.py

tests/
  ├── conftest.py
  ├── test_features.py → bank.py, account.py
  ├── test_smoke.py → webapp.py
  └── test_utils.py → utils.py
```

## External Dependencies
| Package | Used By | Purpose |
|---------|---------|---------|
| flask | webapp.py | Web framework |
| rich | ui.py | Terminal UI / CLI |
| pytest | tests/ | Testing |
| werkzeug | webapp.py | Password hashing |

## Critical / High-Impact Files
- **bank.py**: Core banking logic — highest impact, most dependencies
- **webapp.py**: Web routes and controllers — central hub
- **utils.py**: Shared utilities — used by nearly every module
- **account.py**: Account management — critical for auth

## Dependency Levels
| Level | Files | Description |
|-------|-------|-------------|
| 0 (Core) | bank.py, utils.py, logger.py | Foundation modules |
| 1 (Mid) | account.py, admin.py | Business logic modules |
| 2 (High) | webapp.py, api.py, ui.py | Interface modules |
| 3 (Entry) | main.py | Application entry point |
