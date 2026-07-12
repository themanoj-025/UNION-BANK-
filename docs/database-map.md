# Database Map — UNION-BANK-

## Database Type
**JSON File Storage** — No SQL database. All data stored as JSON files on disk.

## Storage Files
| File | Type | Purpose |
|------|------|---------|
| `accounts.json` | JSON | Customer account data (name, balance, hashed password, status) |
| `transactions.json` | JSON | Transaction records per account |
| `login_attempts.json` | JSON | Rate-limiting tracker (failed attempts, lockout timestamps) |
| `savings_goals.json` | JSON | Per-account savings goal data |
| `admin.json` | JSON | Admin credentials (bcrypt-hashed password) |

## Entity: Account (stored in accounts.json keys)
| Field | Type | Description |
|-------|------|-------------|
| account_number | string (10-digit) | Unique account number (key) |
| name | string | Full name |
| age | int | Age (18-120) |
| gender | string | Gender |
| mobile | string | 10-digit Indian mobile |
| email | string | Email address |
| password | string | bcrypt-hashed password |
| balance | float | Current balance |
| is_active | bool | Whether account is active |
| is_frozen | bool | Whether account is frozen by admin |
| created_at | string (ISO datetime) | Account creation date |

## Entity: Transaction (stored in transactions.json, keyed by account_number)
| Field | Type | Description |
|-------|------|-------------|
| txn_id | string (TXN-XXXXXXXX) | Unique transaction ID |
| type | string | DEPOSIT / WITHDRAW / TRANSFER_OUT / TRANSFER_IN / INTEREST |
| amount | float | Transaction amount |
| description | string | Human-readable note |
| balance | float | Running balance after this transaction |
| timestamp | string (ISO datetime) | Transaction time |
| category | string | Transaction category (from 13 predefined) |
| target_account | string (optional) | For transfers, the other account involved |

## Entity: Savings Goal (stored in savings_goals.json, keyed by account_number)
| Field | Type | Description |
|-------|------|-------------|
| goal_id | string (GOAL-XXXXXXXX) | Unique goal ID |
| name | string | Goal name |
| target_amount | float | Savings target |
| current_amount | float | Current savings |
| target_date | string (optional) | Target date (YYYY-MM-DD) |
| created_at | string (ISO datetime) | When the goal was created |
| is_completed | bool | Whether goal has been achieved |

## Relationships
```
[Account] 1 ──── has ──── N [Transaction]    (via transactions.json[account_number])
[Account] 1 ──── has ──── N [SavingsGoal]     (via savings_goals.json[account_number])
[Account] 1 ──── references via transfer ──── [Account]  (via target_account in TRANSFER_OUT/TRANSFER_IN)
```
