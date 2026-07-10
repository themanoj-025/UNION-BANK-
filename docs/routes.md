# Routes — UNION-BANK-

## Flask Web Routes (`webapp.py`)

### Public Routes
| Route | Method | Purpose | Auth |
|-------|--------|---------|------|
| `/` | GET | Landing page with bank statistics | No |
| `/login` | GET, POST | Customer login | No |
| `/register` | GET, POST | New account registration | No |
| `/logout` | GET | Logout (customer or admin) | No |

### Customer Routes
| Route | Method | Purpose | Auth |
|-------|--------|---------|------|
| `/dashboard` | GET | Customer dashboard with charts | Login |
| `/deposit` | GET, POST | Deposit money with category | Login |
| `/withdraw` | GET, POST | Withdraw money with category | Login |
| `/transfer` | GET, POST | Transfer funds (with confirmation step) | Login |
| `/statement` | GET | Full transaction statement with chart data | Login |
| `/export-csv` | GET | Download transaction history as CSV | Login |
| `/apply-interest` | GET, POST | Apply monthly interest | Login |
| `/profile` | GET, POST | View and update profile | Login |
| `/change-password` | GET, POST | Change password | Login |
| `/savings` | GET | View savings goals | Login |
| `/savings/new` | GET, POST | Create savings goal | Login |
| `/savings/<goal_id>/edit` | GET, POST | Edit savings goal | Login |
| `/savings/<goal_id>/contribute` | POST | Contribute to savings goal | Login |
| `/savings/<goal_id>/delete` | POST | Delete savings goal (refunds balance) | Login |
| `/close-account` | POST | Close account (requires "CLOSE" confirmation) | Login |

### Admin Routes
| Route | Method | Purpose | Auth |
|-------|--------|---------|------|
| `/admin/login` | GET, POST | Admin login | No |
| `/admin/dashboard` | GET | Admin dashboard | Admin |
| `/admin/accounts` | GET | View all accounts | Admin |
| `/admin/accounts/<acc_no>` | GET | Account detail with summary + chart data | Admin |
| `/admin/search` | GET, POST | Search accounts by number or name | Admin |
| `/admin/freeze` | GET, POST | Freeze/unfreeze account (with confirmation) | Admin |
| `/admin/delete` | GET, POST | Delete account (requires "DELETE" confirmation) | Admin |
| `/admin/statistics` | GET | Bank statistics with charts | Admin |
| `/admin/statistics/pdf` | GET | Download PDF report of bank statistics | Admin |
| `/admin/transactions` | GET, POST | View all transactions (filter by account) | Admin |
| `/admin/change-password` | GET, POST | Change admin password | Admin |

---

## FastAPI REST API (`api.py`)
Base URL: `http://localhost:8000`

### Auth Endpoints
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| POST | `/api/auth/login` | Customer login → JWT token | No |
| POST | `/api/auth/register` | Create new customer account | No |
| POST | `/api/auth/admin-login` | Admin login → JWT token | No |

### Customer Account Endpoints
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| GET | `/api/account/profile` | Get profile details | JWT |
| PUT | `/api/account/profile` | Update profile (name, age, gender, mobile, email) | JWT |
| POST | `/api/account/change-password` | Change password | JWT |
| POST | `/api/account/close` | Close account (requires "CLOSE" + password) | JWT |
| GET | `/api/account/balance` | Get current balance | JWT |
| POST | `/api/account/deposit` | Deposit money (amount, category) | JWT |
| POST | `/api/account/withdraw` | Withdraw money (amount, category) | JWT |
| POST | `/api/account/transfer` | Transfer funds (target_account, amount, category) | JWT |
| GET | `/api/account/statements` | Full statement (newest first) | JWT |
| GET | `/api/account/statements/mini` | Mini statement (last 5 transactions) | JWT |
| GET | `/api/account/export-csv` | Download statement as CSV | JWT |
| POST | `/api/account/apply-interest` | Apply monthly interest (3.5% p.a.) | JWT |

### Savings Goals Endpoints
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| GET | `/api/savings` | List savings goals with summary | JWT |
| POST | `/api/savings` | Create savings goal | JWT |
| PUT | `/api/savings/{goal_id}` | Update savings goal | JWT |
| POST | `/api/savings/{goal_id}/contribute` | Contribute to goal | JWT |
| DELETE | `/api/savings/{goal_id}` | Delete goal (refunds to balance) | JWT |

### Admin Endpoints
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| GET | `/api/admin/accounts` | List all accounts | JWT (Admin) |
| GET | `/api/admin/accounts/search?q=` | Search accounts by number or name | JWT (Admin) |
| POST | `/api/admin/accounts/{acc_no}/freeze` | Freeze account | JWT (Admin) |
| POST | `/api/admin/accounts/{acc_no}/unfreeze` | Unfreeze account | JWT (Admin) |
| DELETE | `/api/admin/accounts/{acc_no}` | Permanently delete account + transactions | JWT (Admin) |
| GET | `/api/admin/statistics` | Bank-wide statistics | JWT (Admin) |
| GET | `/api/admin/transactions?account=` | View all transactions (optional filter) | JWT (Admin) |
| PUT | `/api/admin/password` | Change admin password | JWT (Admin) |

### Utility Endpoints
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| GET | `/api/categories` | List all transaction categories | No |
| GET | `/api/health` | Health check | No |
