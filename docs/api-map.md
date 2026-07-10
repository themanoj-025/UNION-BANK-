# API Map — UNION-BANK-

## FastAPI REST API (`api.py`)

### Auth Endpoints
| Method | Route | Input | Output | Purpose |
|--------|-------|-------|--------|---------|
| POST | `/api/auth/login` | `{ account_number, password }` | `{ access_token, token_type, role }` | Customer login → JWT |
| POST | `/api/auth/register` | `{ name, age, gender, mobile, email, password, confirm_password }` | `{ message, status }` | Register new customer |
| POST | `/api/auth/admin-login` | `{ username, password }` | `{ access_token, token_type, role }` | Admin login → JWT |

### Customer Account Endpoints (all require JWT)
| Method | Route | Input | Output | Purpose |
|--------|-------|-------|--------|---------|
| GET | `/api/account/profile` | — | `{ account_number, name, balance, status, ... }` | Get profile |
| PUT | `/api/account/profile` | `{ name?, age?, gender?, mobile?, email? }` | `{ account_number, name, balance, status, ... }` | Update profile |
| POST | `/api/account/change-password` | `{ current_password, new_password, confirm_password }` | `{ message, status }` | Change password |
| POST | `/api/account/close` | `{ confirm_text: "CLOSE", password }` | `{ message, status }` | Close account |
| GET | `/api/account/balance` | — | `{ account_number, name, balance, balance_formatted }` | Get balance |
| POST | `/api/account/deposit` | `{ amount, category? }` | `{ message, status }` | Deposit money |
| POST | `/api/account/withdraw` | `{ amount, category? }` | `{ message, status }` | Withdraw money |
| POST | `/api/account/transfer` | `{ target_account, amount, category? }` | `{ message, status }` | Transfer funds |
| GET | `/api/account/statements` | — | `[ { txn_id, timestamp, type, amount, balance, ... } ]` | Full statement |
| GET | `/api/account/statements/mini` | — | `[ { txn_id, timestamp, type, amount, balance, ... } ]` | Mini statement (last 5) |
| GET | `/api/account/export-csv` | — | CSV file download | Export statement |
| POST | `/api/account/apply-interest` | — | `{ message, status }` | Apply monthly interest |

### Savings Goals Endpoints (all require JWT)
| Method | Route | Input | Output | Purpose |
|--------|-------|-------|--------|---------|
| GET | `/api/savings` | — | `{ total_goals, completed, total_saved, goals[] }` | List goals |
| POST | `/api/savings` | `{ name, target_amount, target_date? }` | `{ goal_id, name, target_amount, ... }` | Create goal |
| PUT | `/api/savings/{goal_id}` | `{ name?, target_amount?, target_date? }` | `{ goal_id, name, target_amount, progress_pct, ... }` | Update goal |
| POST | `/api/savings/{goal_id}/contribute` | `{ amount }` | `{ goal_id, current_amount, progress_pct, ... }` | Contribute to goal |
| DELETE | `/api/savings/{goal_id}` | — | `{ message, status }` | Delete goal (refunds balance) |

### Admin Endpoints (all require JWT with admin role)
| Method | Route | Input | Output | Purpose |
|--------|-------|-------|--------|---------|
| GET | `/api/admin/accounts` | — | `[ { account_number, name, balance, status, ... } ]` | List all accounts |
| GET | `/api/admin/accounts/search` | `q` (query param) | `[ { account_number, name, balance, status, ... } ]` | Search accounts |
| POST | `/api/admin/accounts/{acc_no}/freeze` | — | `{ message, status }` | Freeze account |
| POST | `/api/admin/accounts/{acc_no}/unfreeze` | — | `{ message, status }` | Unfreeze account |
| DELETE | `/api/admin/accounts/{acc_no}` | — | `{ message, status }` | Permanently delete account |
| GET | `/api/admin/statistics` | — | `{ total_customers, active_accounts, frozen_accounts, total_balance, ... }` | Bank statistics |
| GET | `/api/admin/transactions` | `account?` (query param) | `{ acc_no: [transactions] }` | View transactions |
| PUT | `/api/admin/password` | `{ current_password, new_password, confirm_password }` | `{ message, status }` | Change admin password |

### Utility
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| GET | `/api/categories` | `[ "General", "Food", "Transport", ... ]` | No |
| GET | `/api/health` | `{ status, service, version }` | No |

## Flask Web App Internal Logic (`webapp.py`)
The Flask app uses the same business logic modules:
- `utils.py` — JSON file I/O helpers (load_json, save_json), password hashing, validation
- `account.py` — Account class (save, log_transaction)
- `admin.py` — Admin credentials

## Authentication Details
- **Web**: Session-based via Flask session cookies
- **API**: JWT tokens (HS256, 24h expiry) with Bearer auth
- **Rate Limiting**: Login attempts tracked per account (max attempts → lockout timer)
- **Admin**: Separate login endpoint + role check in JWT payload
