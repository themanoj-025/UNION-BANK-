# RUNBOOK — Union Bank API

> **Version:** 2.0.0
> **Last Updated:** 2026-07-16

---

## Table of Contents

1. [Service Overview](#1-service-overview)
2. [Health & Readiness Probes](#2-health--readiness-probes)
3. [Metrics & Monitoring](#3-metrics--monitoring)
4. [Logging](#4-logging)
5. [Database](#5-database)
6. [Common Scenarios & Troubleshooting](#6-common-scenarios--troubleshooting)
7. [Deployment](#7-deployment)
8. [Security Incidents](#8-security-incidents)

---

## 1. Service Overview

Union Bank API is a FastAPI application providing REST endpoints for banking operations.

| Component | Details |
|-----------|---------|
| **Service** | union-bank-api (FastAPI) |
| **Port** | 8000 |
| **Database** | SQLite (`data/union_bank.db`) or PostgreSQL (via `DATABASE_URL`) |
| **Cache** | Redis (optional, configured via `REDIS_URL`) |
| **Logging** | Structured JSON → `data/bank.jsonl`, Text → `data/bank.log` |
| **Metrics** | Prometheus → `/metrics` endpoint |

### Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Customer | (account number from seed data) | `Seed@123` |
| Admin | `admin` | `admin123` |

---

## 2. Health & Readiness Probes

### Liveness Probe — `/api/healthz`

Returns 200 if the process is alive. No dependencies checked.

```json
{"status": "alive"}
```

### Readiness Probe — `/api/readyz`

Returns 200 if the database connection is healthy, 503 otherwise.

```json
{"status": "ready", "database": "connected"}
```

```json
{"status": "not ready", "database": "<error message>"}
```

### Health Check — `/api/health`

Returns basic service metadata (v2 envelope).

```json
{"status": "healthy", "service": "Union Bank API", "version": "2.0.0"}
```

### Docker Compose Healthcheck

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/healthz')"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

---

## 3. Metrics & Monitoring

### Prometheus Endpoint

```
GET /metrics
```

Produces Prometheus text format. Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'union-bank-api'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
```

### Available Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `union_bank_requests_total` | Counter | method, endpoint, status | Total HTTP requests |
| `union_bank_request_duration_seconds` | Histogram | method, endpoint | Request latency buckets |
| `union_bank_inflight_requests` | Gauge | method | Current in-flight requests |
| `union_bank_errors_total` | Counter | type, endpoint | Application errors by type |
| `union_bank_active_sessions` | Gauge | — | Active user sessions |
| `union_bank_db_queries_total` | Counter | operation | Database query count |
| `union_bank_cache_hits_total` | Counter | cache | Cache hit count |
| `union_bank_cache_misses_total` | Counter | cache | Cache miss count |

### Suggested Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| High Error Rate | `rate(union_bank_errors_total[5m]) > 0.1` | Warning |
| High Latency | `p95(union_bank_request_duration_seconds) > 2s` | Warning |
| Service Down | `up{job="union-bank-api"} == 0` | Critical |
| Many In-flight | `union_bank_inflight_requests > 100` | Warning |

---

## 4. Logging

### Log Files

| File | Format | Level | Content |
|------|--------|-------|---------|
| `data/bank.log` | Text (`[timestamp] LEVEL message`) | DEBUG+ | Full application logs |
| `data/bank.jsonl` | JSON (one object per line) | INFO+ | Structured logs with request_id, account context |

### JSON Log Format

```json
{
  "timestamp": "2026-07-16T12:34:56.789Z",
  "level": "INFO",
  "logger": "union_bank",
  "message": "Deposit processed",
  "request_id": "abc123def456...",
  "account": "2828115163",
  "extra": {
    "amount": 5000.0,
    "category": "Salary"
  }
}
```

### Request Context

Every authenticated request includes:
- `request_id` — Unique ID per request (from `X-Request-ID` header or auto-generated)
- `account` — Account number for customer requests, username for admin requests (set automatically by JWT auth dependencies)

### Log Levels

| Level | Usage |
|-------|-------|
| DEBUG | Fine-grained internal flow (file only) |
| INFO | Normal operations (login, deposit, transfer, etc.) |
| WARNING | Suspicious/notable events (bad password, frozen account, CSRF warning) |
| ERROR | Unexpected failures (DB errors, external service failures) |
| CRITICAL | Admin actions (freeze, delete, close account) |

### Viewing Logs

```bash
# Tail application logs
tail -f data/bank.log

# Tail JSON structure logs
tail -f data/bank.jsonl | python -m json.tool --json-lines

# Search for a specific request
grep "REQ-abc123" data/bank.jsonl

# Find all errors in the last hour
grep '"ERROR"' data/bank.jsonl | grep "$(date -d '1 hour ago' +%Y-%m-%dT%H)"
```

---

## 5. Database

### SQLite (Default)

Located at `data/union_bank.db`. Uses WAL mode for concurrent reads.

```bash
# Connect
sqlite3 data/union_bank.db

# Check integrity
PRAGMA integrity_check;

# Get database stats
PRAGMA page_count;
PRAGMA page_size;
```

### PostgreSQL (Optional)

Set `DATABASE_URL` environment variable to switch:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/union_bank
```

### Migrations

Managed via Alembic:

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View history
alembic history
```

### Backup

```bash
# SQLite backup
sqlite3 data/union_bank.db ".backup 'backups/bank_$(date +%Y%m%d).db'"

# PostgreSQL backup
pg_dump union_bank > backups/bank_$(date +%Y%m%d).sql
```

---

## 6. Common Scenarios & Troubleshooting

### Scenario: API won't start

**Symptoms:** `ModuleNotFoundError`, port in use, database locked

**Checklist:**

1. **Port conflict:** Check if port 8000 is in use
   ```bash
   netstat -ano | findstr :8000
   ```

2. **Python path:** Ensure `src/` is on `sys.path` (look for module import errors)

3. **Database lock:** SQLite file may be locked by another process
   ```bash
   # Delete SQLite WAL files (safe if no process is writing)
   del data/union_bank.db-wal data/union_bank.db-shm
   ```

4. **Missing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Scenario: Rate limiting too aggressive

**Symptoms:** `429 Too Many Requests` during development

**Fix:** Set `UNION_BANK_TESTING=1` to disable rate limiting, or increase limits in `config.py`.

### Scenario: Slow response times

**Checklist:**

1. **Database queries:** Check `data/bank.log` for slow queries
2. **Cache configuration:** Ensure Redis is running if `REDIS_URL` is configured
3. **Missing indexes:** Run `EXPLAIN QUERY PLAN` on slow queries
4. **Large admin lists:** Use `page` and `per_page` parameters on admin endpoints

### Scenario: Metrics not appearing

**Symptom:** `/metrics` returns empty or only default metrics

**Fix:** Verify `prometheus-client` is installed. The `/metrics` endpoint should show `union_bank_*` metrics after the first request.

### Scenario: Logs not writing to `bank.jsonl`

**Checklist:**

1. Verify `data/` directory exists and is writable
2. Check log level — `bank.jsonl` captures INFO+; DEBUG messages go to `bank.log` only
3. Check disk space:
   ```bash
   df -h data/
   ```

### Scenario: Redis cache unavailable

**Behavior:** The application degrades gracefully — cache misses are treated as "no data" rather than errors. Operations still work without Redis.

**Check:** If Redis is expected but unavailable:
```bash
# Verify Redis is running
redis-cli ping
# Expected: PONG
```

---

## 7. Deployment

### Docker

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f api

# Run tests
docker compose run --rm api python -m pytest tests/ -v
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | Yes | — | 32+ char random string for JWT signing |
| `FLASK_SECRET_KEY` | No | (auto) | Legacy, kept for Alembic |
| `DATABASE_URL` | No | SQLite path | PostgreSQL connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string |
| `CORS_ALLOWED_ORIGINS` | No | localhost:5173,5000,8000 | Comma-separated allowed origins |
| `JWT_PRIVATE_KEY` | No | — | RS256 private key |
| `JWT_PUBLIC_KEY` | No | — | RS256 public key |
| `UNION_BANK_TESTING` | No | 0 | Set to `1` to disable rate limiting |

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /api/healthz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 15

readinessProbe:
  httpGet:
    path: /api/readyz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
```

---

## 8. Security Incidents

### Suspected Credential Compromise

1. **Immediately:** Change the compromised account password
2. **Invalidate all sessions:** Password change auto-increments the token version, invalidating all existing JWTs
3. **Verify:** Check `data/bank.jsonl` for suspicious activity from that account
4. **Rotate:** If admin credentials were compromised, also rotate `JWT_SECRET` in environment

### Rate Limit Attack

1. Check `data/bank.jsonl` for repeated 429 responses from the same IP:
   ```bash
   grep '"status":429' data/bank.jsonl | grep -o '"request_id":"[^"]*"' | sort | uniq -c | sort -rn
   ```
2. If persistent, add the offending IP to a firewall blocklist
3. For development: adjust limits in `config.py` or set `UNION_BANK_TESTING=1`

### Database Corruption

1. **Stop the API:** Prevent further writes
2. **Restore from backup:**
   ```bash
   cp backups/bank_20260716.db data/union_bank.db
   ```
3. **Restart the API**
4. **Investigate cause:** Check logs for the period before corruption

### TOTP 2FA Issues (Admin)

If admin locked out due to 2FA:

1. Direct database update to disable 2FA:
   ```bash
   sqlite3 data/union_bank.db "UPDATE admins SET totp_secret = NULL, totp_enabled = 0 WHERE username = 'admin';"
   ```
2. Admin can re-enroll in 2FA after logging in

---

## Appendices

### A. Directory Structure

```
data/
├── bank.log          # Text application logs
├── bank.jsonl        # Structured JSON logs
├── union_bank.db     # SQLite database
└── union_bank.db-wal # SQLite WAL file (auto-managed)

docs/
└── RUNBOOK.md        # This file

backups/              # Manual database backups
```

### B. Related Documentation

| Document | Purpose |
|----------|---------|
| `docs/THREAT_MODEL.md` | Security threat model and mitigations |
| `docs/ARCHITECTURE.md` | System architecture and data flow |
| `docs/ADR-0005-database-migration.md` | Database migration strategy |
| `docs/PERFORMANCE.md` | Performance characteristics and benchmarks |
| `README.md` | Project overview and quick start |
