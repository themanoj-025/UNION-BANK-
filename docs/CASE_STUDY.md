# Engineering Case Studies — Union Bank Management System

> *Four deep dives into the hardest engineering decisions in this project. Each case study follows the **Problem → Constraint → Decision → Trade-off** format that senior engineering interviews test for.*

---

## Table of Contents

1. [Atomic Transfers Under Concurrency](#1-atomic-transfers-under-concurrency)
2. [Architecture Consolidation — From Chaos to One Canonical Tree](#2-architecture-consolidation)
3. [Security Defense in Depth — Beyond JWTs](#3-security-defense-in-depth)
4. [Testing Strategy — From 26% to 73% Without Coverage Padding](#4-testing-strategy)

---

## 1. Atomic Transfers Under Concurrency

### The Problem

A fund transfer is not a single operation. It's a sequence:

```
debit(sender_account, amount)     # Step 1
credit(receiver_account, amount)  # Step 2
```

If the application crashes between Step 1 and Step 2 — process killed, power failure, network timeout — the money is debited from the sender but never reaches the receiver. The money has disappeared from the system.

This is the most critical correctness problem in a banking application. It's also the hardest to test, because you need to simulate a crash at exactly the wrong moment.

### Constraints

- **SQLite local database** — No distributed transaction coordinator, no two-phase commit. SQLite guarantees atomicity within a single connection, but only if you use its transaction mechanism correctly.
- **Concurrent access** — Multiple users can trigger transfers simultaneously. Without proper locking, two transfers could read the same balance, both approve, and both write — creating money from nothing.
- **No external transaction manager** — The application manages its own transactions. There's no JTA, no XA, no distributed saga framework.

### Decision

**Wrap the entire transfer in a single SQLAlchemy `begin_nested()` savepoint:**

```python
# src/unionbank/application/services.py (simplified)
def transfer(self, sender_acc_no, receiver_acc_no, amount):
    with self.session.begin_nested():  # Atomic savepoint
        sender = self.account_repo.get_by_number(sender_acc_no)
        receiver = self.account_repo.get_by_number(receiver_acc_no)

        if sender.balance < amount:
            raise InsufficientFundsError()

        sender.balance -= amount
        receiver.balance += amount

        # Both transaction records created inside the same savepoint
        debit_txn = Transaction(account=sender_acc_no, amount=-amount, ...)
        credit_txn = Transaction(account=receiver_acc_no, amount=amount, ...)

        self.session.add_all([debit_txn, credit_txn])

    # If anything above fails, the savepoint rolls back everything.
    # The session itself commits the outer transaction.
```

For concurrent safety, SQLite is configured with WAL (Write-Ahead Logging) mode, which allows concurrent reads during writes and serializes writes through a single writer lock.

### Proof: Fault-Injection Test

The test that proves this works is a **crash-mid-transfer** scenario:

```python
def test_crash_mid_transfer_does_not_lose_money(self):
    initial_sender = self.account_repo.get_by_number(sender_acc).balance
    initial_receiver = self.account_repo.get_by_number(receiver_acc).balance

    # Attempt transfer with a mock that raises after debit
    with mock.patch.object(self.session, 'commit', side_effect=RuntimeError("crash")):
        with pytest.raises(RuntimeError):
            self.txn_service.transfer(sender_acc, receiver_acc, 1000)

    # Assert: money is conserved — neither side changed
    assert self.account_repo.get_by_number(sender_acc).balance == initial_sender
    assert self.account_repo.get_by_number(receiver_acc).balance == initial_receiver
```

The savepoint rolls back on the simulated crash, leaving both accounts unchanged. Without the savepoint, the sender would be debited and the receiver never credited.

### Concurrency Proof: 10 Parallel Transfers

```python
def test_concurrent_transfers_conserve_money(self):
    accounts = [self.create_account(balance=2000) for _ in range(5)]
    total = sum(a.balance for a in accounts)

    def transfer_pair():
        a, b = random.sample(accounts, 2)
        try:
            self.txn_service.transfer(a.account_number, b.account_number, 100)
        except:
            pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(transfer_pair) for _ in range(10)]
        concurrent.futures.wait(futures)

    # Assert: total money is conserved
    new_total = sum(self.account_repo.get_by_number(a.account_number).balance
                    for a in accounts)
    assert new_total == total  # Money conserved
```

### Trade-offs

| Pro | Con |
|-----|-----|
| Atomicity guarantee — money never disappears | Savepoints add ~2-5% overhead per transaction |
| Simple to understand and audit | SQLite write lock serializes concurrent transfers |
| Testable via fault injection | Not a distributed solution — doesn't handle multi-service transactions |
| Works with both SQLite and PostgreSQL | Requires careful session management |

### What I'd Do Differently at Scale

At 100,000+ users, SQLite's write lock becomes a bottleneck. The migration path is:
1. PostgreSQL with serializable isolation level
2. Retry logic for serialization failures (PostgreSQL retries transparently)
3. PgBouncer connection pooling for connection management

The protocol-based repository layer makes this a configuration change, not a code change.

---

## 2. Architecture Consolidation — From Chaos to One Canonical Tree

### The Problem

The codebase had three overlapping generations of code:

```
root/
├── account.py          ← Flask/JSON era
├── bank.py             ← Flask/JSON era
├── admin.py            ← Flask/JSON era
├── config.py           ← Flask/JSON era
├── utils.py            ← Flask/JSON era (2000+ line god module)
│
├── api.py              ← FastAPI era (newer)
├── api/__init__.py     ← FastAPI era (shim)
├── api/common.py       ← FastAPI era
│
├── src/
│   ├── account.py      ← SQLAlchemy era (third copy)
│   ├── admin.py        ← SQLAlchemy era
│   ├── domain/         ← SQLAlchemy era
│   ├── application/    ← SQLAlchemy era
│   └── infrastructure/ ← SQLAlchemy era
```

Two independent audits confirmed: **"Which copy is even live is not obvious from the outside."** Phantom features existed — TOTP fields were defined in the database model but the verification code was never wired. The metrics middleware was imported but never attached.

This is the kind of technical debt that kills maintainability. A new engineer joining the project would spend days figuring out which files are actually used.

### Constraints

- **No budget for a rewrite** — The business logic works. The goal is to make the codebase honest, not to rewrite it.
- **Must work at every commit** — Every intermediate state must pass tests. No "big bang" renames that break everything for a week.
- **Evidence-based** — Decisions about what's DEAD vs. LIVE must be based on import-graph tracing, not memory or assumptions.

### Decision

**Forensic inventory with import-graph tracing:**

1. Classify every Python file as LIVE, DEAD, or AMBIGUOUS
2. For AMBIGUOUS files, trace every import to determine if they're reachable
3. Delete DEAD files immediately (tests prove nothing breaks)
4. For AMBIGUOUS-with-fixes files, either fix them (wire them in) or delete them

**Example classification:**

```python
# docs/INVENTORY.md
| Module | Classification | Evidence |
|--------|---------------|----------|
| root/account.py | 🔴 DEAD | `grep -r "from account import\|import account" *.py` → zero hits |
| src/account.py | 🟢 LIVE | Imported by src/bank.py, which is imported by main.py |
| api/common.py | 🟢 LIVE | Imported by api.py, which is the FastAPI entry point |
```

**Results:**
- 9 root-level .py files deleted (DEAD)
- 5 root-level directories deleted (shadowed by src/)
- 2 src/ files/directories deleted (unreachable)
- TOTP 2FA completed (was phantom — fields existed, verification didn't)
- stale `WsgiMetricsMiddleware` removed (was imported but never used)

### Trade-offs

| Pro | Con |
|-----|-----|
| Zero ambiguity — one canonical tree for all code | Inventory document must be maintained |
| Dead code deletion reduces surface area for bugs | Potential (but testable) risk of deleting something thought dead |
| Phantom features either work or are removed | Takes upfront time to trace import graphs |
| New engineers understand the architecture in minutes | Not glamorous — looks like cleanup, not feature work |

### What This Unlocked

The consolidation was a prerequisite for every subsequent phase:
- **Security audit** couldn't be done when the same bug existed in three copies
- **Async migration** would have been impossible with duplicate modules
- **Testing** coverage numbers were meaningless when code existed in multiple locations

---

## 3. Security Defense in Depth

### The Problem

The original implementation used:
- JWT tokens stored in `localStorage` (vulnerable to XSS)
- No CSRF protection
- No rate limiting on money-movement endpoints
- Static IP-based rate limiting (bypassable via IP rotation)
- No 2FA enforcement

A single XSS vulnerability in the frontend would expose every user's auth token. A CSRF attack could forge transfers. A rate-limit bypass via IP rotation could brute-force passwords.

### Constraints

- **Budget-friendly** — No paid services (Auth0, Okta, AWS Cognito). Everything must use open-source libraries.
- **Testable** — Every security control must have an automated test.
- **Defense in depth** — Multiple independent layers. A failure in one doesn't compromise the system.

### Decision

**Seven-layer security architecture:**

#### Layer 1: Token Storage
Migrated from `localStorage` to **httpOnly, Secure, SameSite=Strict cookies**. The frontend can't access the token via JavaScript — eliminating XSS-based token theft.

```javascript
// BEFORE (vulnerable)
localStorage.setItem('access_token', token);

// AFTER (secure)
// Backend sets httpOnly cookie — JS cannot read it
response.cookie('access_token', token, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict'
});
```

#### Layer 2: CSRF Protection
httpOnly cookies reopen CSRF as an attack vector. Added **double-submit cookie pattern**:
- Backend sets a CSRF token cookie (readable by JS)
- Frontend reads the cookie and sends it as a custom header (`X-CSRF-Token`)
- Backend validates header matches cookie

```javascript
// Frontend reads CSRF cookie and sends as header
const csrfToken = getCookie('csrf_token');
await axios.post('/api/v2/transfer', data, {
    headers: { 'X-CSRF-Token': csrfToken }
});
```

#### Layer 3: Account-Based Rate Limiting
IP-based rate limiting is bypassable via IP rotation (VPN, botnet). Added **per-account rate limiting** in Redis:

```python
# Maximum 5 money-movement operations per account per hour
key = f"rate_limit:account:{account_number}:money_movement"
current = redis.incr(key)
if current == 1:
    redis.expire(key, 3600)
if current > 5:
    raise RateLimitExceededError()
```

This closes the IP-rotation bypass — the limit follows the account, not the IP.

#### Layer 4: Refresh Token Rotation
Refresh tokens are:
- **Hashed with bcrypt** before storage (not reversible encryption — even if DB is compromised, tokens can't be used)
- **Rotated on each use** — the old token is revoked when a new one is issued
- **Expired after 7 days** — limited window of usefulness if compromised
- **Token versioning** — password change increments the version, invalidating all existing tokens

#### Layer 5: TOTP 2FA
TOTP secrets are **encrypted with Fernet** (symmetric encryption with a key from `TOTP_ENCRYPT_KEY` env var). Admin login requires TOTP verification after password validation.

#### Layer 6: Security Headers
```python
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["Content-Security-Policy"] = "default-src 'self'"
```

#### Layer 7: Automated Security Testing
```python
# SQL injection attempt — should be rejected
response = client.post("/api/v2/login", json={
    "account_number": "'; DROP TABLE accounts; --",
    "password": "test1234"
})
assert response.status_code == 401  # Not 500

# CSRF token omission — should be rejected
response = client.post("/api/v2/transfer", json={...}, headers={})
assert response.status_code == 403  # Forbidden
```

### Trade-offs

| Pro | Con |
|-----|-----|
| Defense in depth — no single point of failure | More code to maintain |
| Every layer is independently testable | httpOnly cookies require CSRF strategy |
| No paid services — fully self-contained | More complex local setup (Redis required for rate limiting) |
| Security tests in CI prevent regressions | False positives possible (e.g., rate limiting in tests) |

---

## 4. Testing Strategy — From 26% to 73% Without Coverage Padding

### The Problem

The original project had 26% test coverage, concentrated on CLI utility functions. The critical business logic — services, transfers, admin operations, loans — was completely untested.

Coverage percentages are easy to pad. Testing the trivial getters and setters raises the number but adds zero confidence. The goal was to raise coverage to 73% *while testing the right things*.

### Constraints

- **No coverage padding** — Every test must test a real behavior or invariant, not just exist to raise the percentage.
- **No mocking** — The project uses protocol-based fakes instead of mocks. Mocks couple tests to implementation details; fakes test the same code paths as production.
- **Must catch regressions** — The tests must survive refactoring. They should break only when behavior changes.

### Decision

**Three-pronged testing strategy:**

#### 1. Property-Based Tests (Hypothesis)

Instead of testing specific examples, assert invariants that must *always* be true:

```python
@given(st.floats(min_value=0.01, max_value=10000), st.floats(min_value=0.01, max_value=10000))
def test_transfer_preserves_total_money(balance_a, balance_b):
    """Money conservation: total before == total after."""
    acc_a = create_account(balance=Decimal(str(balance_a)))
    acc_b = create_account(balance=Decimal(str(balance_b)))
    total_before = acc_a.balance + acc_b.balance

    amount = min(balance_a, balance_b) / 2  # Ensure sufficient funds
    service.transfer(acc_a.number, acc_b.number, Decimal(str(amount)))

    total_after = acc_a.balance + acc_b.balance
    assert total_after == total_before
```

Property-based tests find edge cases that example-based tests miss — floating point precision, boundary conditions, concurrent state.

#### 2. Concurrency Tests

The hardest correctness problem in a banking application is concurrency. The test fires 10 simultaneous transfers and asserts money conservation:

```python
def test_10_concurrent_transfers():
    accounts = [create_account(2000) for _ in range(5)]
    total = sum(a.balance for a in accounts)

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(random_transfer, accounts) for _ in range(10)]
        wait(futures)

    assert total_money(accounts) == total  # Money conserved
```

This test found a real bug in the original implementation — without atomic savepoints, concurrent transfers could create money.

#### 3. Protocol-Based Fakes

Instead of mocking:

```python
# Production: real database
container.account_repo = SqlAlchemyAccountRepository(session)

# Test: in-memory fake (implements same Protocol)
container.account_repo = FakeAccountRepository()
```

The test exercises the **same service code** that runs in production. The only difference is the repository implementation. This means:
- The service logic is fully tested
- Repository-specific behavior (transaction handling, SQL) is tested separately
- Tests run in milliseconds (no database needed)
- Refactoring the service doesn't break tests (they test behavior, not implementation)

### Results

| Metric | Before | After |
|--------|--------|-------|
| Test count | ~100 | 386 (376 backend + 10 frontend) |
| Coverage | 26% | 73% |
| Property-based tests | 0 | 5 invariants + stateful machine |
| Concurrency tests | 0 | 10-parallel-transfer test |
| Security tests | 0 | SQLi, XSS, CSRF, JWT, password leak |
| Frontend tests | 0 | 10 (Vitest + React Testing Library) |
| Mutation tests | 0 | mutmut report in CI |
| Fuzz tests | 0 | schemathesis against OpenAPI spec |
| Migration tests | 0 | 5 Alembic round-trip tests |
| CI jobs | 2 | 10 (unit, integration, frontend, security, mutation, fuzz, docker, secrets, commitlint, postgres) |

### Trade-offs

| Pro | Con |
|-----|-----|
| Property-based tests find edge cases example tests miss | Harder to write and debug (shrinking output can be cryptic) |
| Protocol-based fakes are faster than real database | Need to maintain fake implementations alongside real ones |
| Concurrency tests prove correctness under load | Flaky in CI if timing-dependent (mitigated by careful design) |
| No coverage padding — every test tests a real behavior | Lower coverage than padded alternatives — but more useful |

---

*These case studies are designed to demonstrate senior engineering judgment in interviews. Each one follows the same structure: identify a real problem, understand the constraints, make a defensible decision, acknowledge the trade-offs, and provide evidence it works.*

---

*Last updated: 2026-07-17*
