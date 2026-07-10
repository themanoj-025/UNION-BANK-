# Database Map — UNION-BANK-

## Database Type
**JSON File Storage** — No SQL database. All data stored as JSON files on disk.

## Storage Files
| File | Type | Purpose |
|------|------|---------|
| `accounts.json` | JSON | User account data |
| `transactions.json` | JSON | Transaction records |
| `users.json` | JSON | User profiles and auth data |
| `admins.json` | JSON | Admin accounts |

## Entity: User
| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique user ID |
| username | string | Login username |
| password_hash | string | Hashed password |
| name | string | Full name |
| email | string | Email address |
| phone | string | Phone number |
| created_at | datetime | Account creation date |

## Entity: Account
| Field | Type | Description |
|-------|------|-------------|
| account_id | string | Unique account number |
| user_id | string | Owner user ID (FK → User) |
| balance | float | Current balance |
| account_type | string | savings / checking |
| status | string | active / frozen / closed |
| interest_rate | float | Interest rate (savings) |
| created_at | datetime | Account opened date |

## Entity: Transaction
| Field | Type | Description |
|-------|------|-------------|
| transaction_id | string | Unique transaction ID |
| from_account | string | Source account (FK → Account) |
| to_account | string | Destination account (FK → Account) |
| amount | float | Transaction amount |
| type | string | deposit / withdraw / transfer / interest |
| timestamp | datetime | Transaction time |
| description | string | Optional note |

## Entity: Savings Goal
| Field | Type | Description |
|-------|------|-------------|
| goal_id | string | Unique goal ID |
| account_id | string | Linked account (FK → Account) |
| name | string | Goal name |
| target_amount | float | Savings target |
| current_amount | float | Current savings |
| deadline | date | Target date |
| status | string | active / completed / cancelled |

## Entity: Admin
| Field | Type | Description |
|-------|------|-------------|
| admin_id | string | Unique admin ID |
| username | string | Admin login |
| password_hash | string | Hashed password |

## Relationships
```
User (1) ──── has ──── Account (1..N)
Account (1) ──── has ──── Transaction (0..N)
Account (1) ──── has ──── Savings Goal (0..N)
Admin (1) ──── manages ──── Account (0..N)
```
