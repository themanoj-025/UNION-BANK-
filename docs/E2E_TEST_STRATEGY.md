# E2E Test Strategy — Union Bank Management System

## Overview

This document outlines the end-to-end (E2E) testing strategy for the Union Bank
Management System. The E2E tests use **Playwright** (via `pytest-playwright`) to
drive a real browser against a fully deployed backend stack (FastAPI + PostgreSQL)
to verify the system works as a whole.

## Test Architecture

```
┌──────────────┐     ┌──────────────┐     ┌────────────┐     ┌───────────┐
│  Playwright  │────▶│  React App   │────▶│  FastAPI   │────▶│ Postgres  │
│  (Node.js)   │     │  (Vite dev)  │     │  (uvicorn) │     │  (test)   │
└──────────────┘     └──────────────┘     └────────────┘     └───────────┘
                           │                                        │
                           └──── httpOnly cookies ──────────────────┘
```

- **Browser**: Chromium (headless in CI, headed for local debugging)
- **Backend**: FastAPI running against a dedicated test PostgreSQL database
- **Seeding**: A fresh database is seeded before each test suite run
- **Teardown**: Database is dropped after each suite run

## Test Categories

### 1. Customer Flows (happy path)

| Flow | Steps | Assertions |
|------|-------|------------|
| **Register → Login → Deposit → Transfer → Withdraw → Logout** | 1. Navigate to `/signup`, fill form, submit<br>2. Navigate to `/login`, fill credentials, submit<br>3. Navigate to `/deposit`, enter amount, confirm<br>4. Navigate to `/transfer`, enter target + amount, confirm<br>5. Navigate to `/withdraw`, enter amount, confirm<br>6. Click logout | - Registration redirects to login<br>- Login redirects to dashboard<br>- Balance reflects deposit<br>- Transfer deducts from sender<br>- Withdraw deducts from balance<br>- Logout redirects to home |

### 2. Admin Flows (happy path)

| Flow | Steps | Assertions |
|------|-------|------------|
| **Admin Login → View Accounts → Freeze → Verify → Unfreeze** | 1. Navigate to `/admin/login`, fill credentials<br>2. Navigate to `/admin/accounts`, verify list renders<br>3. Click "Freeze" on an active account<br>4. Attempt to login as frozen customer (should fail)<br>5. Navigate back to admin, "Unfreeze" the account<br>6. Attempt to login as customer (should succeed) | - Admin dashboard loads with stats<br>- Accounts table displays rows<br>- Freeze confirmation dialog appears<br>- Frozen customer cannot transact<br>- Unfreeze restores access |

### 3. Loan Flows

| Flow | Steps | Assertions |
|------|-------|------------|
| **Customer applies → Admin approves → EMI payment** | 1. Login as customer, navigate to `/loans`<br>2. Submit loan application<br>3. Login as admin, navigate to `/admin/loans`<br>4. Approve the pending loan<br>5. Login as customer, verify loan is active<br>6. Pay an EMI | - Application confirmation message shown<br>- Loan appears in admin's pending tab<br>- Loan status changes to ACTIVE<br>- EMI payment reduces remaining amount |
| **Customer applies → Admin rejects** | 1. Login as customer, apply for a loan<br>2. Login as admin, reject with reason<br>3. Login as customer, verify status | - Loan status is REJECTED<br>- Admin's rejection reason is visible |

### 4. Savings Goals Flow

| Flow | Steps | Assertions |
|------|-------|------------|
| **Create goal → Contribute → Delete goal** | 1. Login as customer, navigate to `/savings`<br>2. Create a new savings goal<br>3. Contribute an amount to the goal<br>4. Delete the goal | - Goal appears with progress bar<br>- Balance decreases by contribution amount<br>- Deletion refunds the amount |
| **Goal completion** | 1. Create a small goal (e.g., $100)<br>2. Contribute until goal is met<br>3. Verify completion status | - Goal shows as "Completed"<br>- Progress bar reaches 100% |

### 5. Security Flows

| Flow | Steps | Assertions |
|------|-------|------------|
| **CSRF protection** | 1. Login and capture cookies<br>2. Submit a deposit POST without CSRF token<br>3. Submit with valid CSRF token | - Request without token is rejected (if cookie present)<br>- Request with token succeeds |
| **Rate limiting** | 1. Login as customer<br>2. Make 6 consecutive deposit/withdraw requests<br>3. Verify 6th request is rate-limited | - 6th request returns 429 status<br>- Response includes `Retry-After` header |
| **Unauthorized access** | 1. Visit protected routes without logging in<br>2. Visit admin routes without admin role | - Redirected to login page<br>- Admin routes return 401/redirect |

### 6. Edge Case / Error Flows

| Flow | Steps | Assertions |
|------|-------|------------|
| **Insufficient balance** | 1. Login with a low-balance account<br>2. Attempt to withdraw/transfer > balance | - Error message displayed<br>- Balance unchanged |
| **Invalid login** | 1. Attempt login with wrong password<br>2. Attempt login with non-existent account | - Error message displayed<br>- No redirect to dashboard |
| **Form validation** | 1. Submit registration with weak password<br>2. Submit with mismatched passwords<br>3. Submit with invalid email | - Specific validation errors shown<br>- Form not submitted |
| **Account closing** | 1. Login as customer<br>2. Navigate to profile, close account<br>3. Attempt to login again | - Account closure confirmed<br>- Login returns "account not found" |

## Test Implementation Plan

### Directory Structure

```
tests/
  e2e/
    __init__.py
    conftest.py           # Playwright fixtures, DB seeding, auth helpers
    test_customer_flows.py
    test_admin_flows.py
    test_loan_flows.py
    test_savings_flows.py
    test_security_flows.py
    test_error_flows.py
```

### Key Fixtures (`conftest.py`)

```python
@pytest.fixture(scope="session")
def browser_context(browser):
    """Create a browser context with JavaScript enabled."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
    )
    yield context
    context.close()

@pytest.fixture
def customer_page(browser_context, seeded_db):
    """Return a logged-in customer page."""
    page = browser_context.new_page()
    # Navigate to login, fill credentials, submit
    page.goto(f"{BASE_URL}/login")
    page.fill("[name='account_number']", TEST_CUSTOMER_ACCOUNT)
    page.fill("[name='password']", TEST_CUSTOMER_PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/dashboard")
    yield page
    page.close()

@pytest.fixture(scope="session")
def seeded_db():
    """Seed the test database with known test data."""
    # Run Alembic migrations then seed data
    subprocess.run(["alembic", "upgrade", "head"])
    subprocess.run(["python", "seed_data.py"])
    yield
    # Teardown: drop and recreate
    subprocess.run(["alembic", "downgrade", "base"])
```

### Running Tests

```bash
# Local (headed browser, visible)
pytest tests/e2e/ --headed --slowmo 500

# CI (headless, parallel)
pytest tests/e2e/ -n auto --tracing=retain-on-failure

# With specific browser
pytest tests/e2e/ --browser=firefox

# Generate trace for failed tests
pytest tests/e2e/ --tracing=on
```

## CI Integration

The E2E test suite runs in GitHub Actions as a separate job:

```yaml
e2e-tests:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:16
      env:
        POSTGRES_DB: union_bank_test
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
      ports:
        - 5432:5432
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - uses: actions/setup-node@v4
      with:
        node-version: "20"
    - run: pip install -e ".[dev]"
    - run: pip install pytest-playwright
    - run: playwright install chromium
    - run: |
        DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/union_bank_test
        alembic upgrade head
        cd frontend && npm ci && npx vite --port 5173 &
        cd .. && uvicorn unionbank.entrypoints.api.main:app --port 8000 &
        sleep 5
        pytest tests/e2e/ -v
```

## Priority Matrix

| Priority | Flow | Why |
|----------|------|-----|
| **P0** | Register → Login → Deposit → Transfer → Withdraw | Core banking functionality |
| **P0** | Admin login → Freeze → Verify → Unfreeze | Access control critical |
| **P1** | Loan application → Approval → EMI | Revenue-generating feature |
| **P1** | CSRF / Rate limiting / Auth bypass | Security verification |
| **P2** | Savings goals CRUD | Secondary feature |
| **P2** | Edge cases (insufficient balance, validation) | Error handling verification |

## Notes

- E2E tests are **slow** (~2-5 minutes per suite) — they complement unit/integration tests,
  not replace them
- Each E2E test should be independently runnable with a fresh seed
- Tests should use `data-testid` attributes where possible (add them during frontend
  refactoring) for reliable element selectors
- Screenshots are captured on failure for CI debugging
