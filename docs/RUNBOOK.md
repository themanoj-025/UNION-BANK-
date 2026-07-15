# Runbook: Union Bank Management System

**Version:** 2.0.0  
**Last Updated:** July 2026  
**Primary Contact:** Union Bank Dev Team  

---

## 1. Service Overview

Union Bank is a banking management system consisting of:
- **FastAPI REST API** (port 8000)
- **React SPA Frontend** (served via Vite/NGINX)
- **SQLite Database** (single file, `data/union_bank.db`)
- **Redis Cache** (optional, for production)

### Topology

```
Internet → Reverse Proxy (NGINX/Caddy)
  ├── /api/* → FastAPI (port 8000)
  └── /* → React SPA (static files)
              └── FastAPI (API calls)
```

---

## 2. Deployment Procedure

### Prerequisites
- Docker & Docker Compose installed
- `.env` file with all required environment variables
- Access to the Git repository

### Standard Deployment

```bash
# 1. Pull latest code
git pull origin main

# 2. Build and start
docker compose up -d --build

# 3. Verify
curl http://localhost:8000/api/health
curl http://localhost:8000/api/readyz

# 4. Check logs
docker compose logs -f --tail=50 api
```

### Production Deployment

```bash
# 1. Pull and build
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# 2. Stop old containers, start new ones
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --wait

# 3. Verify health
curl -f http://localhost:8000/api/healthz && echo "Healthy"
curl -f http://localhost:8000/api/readyz && echo "Ready"

# 4. Clean up old images
docker image prune -f
```

---

## 3. Rollback Procedure

### Standard Rollback

```bash
# 1. Revert to previous tag
git checkout v2.0.0

# 2. Rebuild and restart
docker compose up -d --build

# 3. Verify
curl http://localhost:8000/api/health
```

### Database Rollback (Alembic)

```bash
# Check current revision
alembic current

# Rollback one step
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# View history
alembic history
```

### Data Recovery

SQLite database is stored at `data/union_bank.db`. Backups are created automatically by the backup script.

```bash
# Restore from backup
cp data/backups/union_bank_$(date -d "1 day ago" +%Y%m%d).db data/union_bank.db
```

---

## 4. Monitoring & Alerting

### Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /api/health` | General health check | `{"status": "healthy"}` |
| `GET /api/healthz` | K8s liveness probe | `{"status": "alive"}` |
| `GET /api/readyz` | K8s readiness probe | `{"status": "ready", "database": "connected"}` |

### Metrics

Prometheus metrics available at `GET /metrics`.

**Key metrics to watch:**
- `union_bank_requests_total` — request rate by endpoint
- `union_bank_request_duration_seconds` — p95/p99 latency
- `union_bank_errors_total` — error rate by type
- `union_bank_db_queries_total` — database load
- `union_bank_cache_hits_total` — cache effectiveness

### Logging

All logs are written to:
- `data/bank.log` — Text format (DEBUG+)
- `data/bank.jsonl` — JSON format (INFO+)

Log structure (JSON):
```json
{
  "timestamp": "2026-07-15T12:00:00.000000Z",
  "level": "INFO",
  "logger": "union_bank",
  "message": "Deposit processed",
  "request_id": "a1b2c3d4e5f6...",
  "account": "1234567890",
  "extra": {"amount": 500.00, "type": "DEPOSIT"}
}
```

---

## 5. Incident Response Procedures

### IR-01: API Is Down / Not Responding

**Symptoms:**
- `curl http://localhost:8000/api/health` returns connection refused or timeout
- Users see 502/503 errors

**Severity:** Critical

**Steps:**
1. Check if the process is running:
   ```bash
   docker ps | grep union-bank-api
   ```
2. Check logs for crash:
   ```bash
   docker compose logs --tail=100 api
   ```
3. Check resource usage:
   ```bash
   docker stats union-bank-api
   ```
4. If OOM-killed, increase memory limits in `docker-compose.yml`
5. Restart the service:
   ```bash
   docker compose restart api
   ```
6. If persistent, rollback (see Section 3)

### IR-02: Database Is Corrupted

**Symptoms:**
- `GET /api/readyz` returns 503
- SQLite errors in logs: `database disk image is malformed`

**Severity:** Critical

**Steps:**
1. Stop the API to prevent further writes:
   ```bash
   docker compose stop api
   ```
2. Take a copy of the corrupted DB:
   ```bash
   cp data/union_bank.db data/union_bank.db.corrupted
   ```
3. Run integrity check:
   ```bash
   sqlite3 data/union_bank.db "PRAGMA integrity_check;"
   ```
4. Try recovery:
   ```bash
   sqlite3 data/union_bank.db ".dump" | sqlite3 data/union_bank_recovered.db
   ```
5. If recovery fails, restore from backup
6. Start the API:
   ```bash
   docker compose start api
   ```

### IR-03: Security Incident (Suspected Breach)

**Symptoms:**
- Unexpected admin account creation
- Unusual transaction patterns (large transfers, many failed logins)
- Audit log shows actions from unknown IPs

**Severity:** Critical

**Steps:**
1. **Immediate containment:**
   ```bash
   # Block all traffic (via reverse proxy)
   # Revoke all active sessions (requires DB access)
   ```
2. **Audit the access logs:**
   ```bash
   docker compose logs api | grep -E "401|403|admin" | tail -100
   ```
3. **Audit the database audit log:**
   ```python
   # Connect to DB and query audit_log table
   ```
4. **Rotate secrets:**
   - Change `JWT_SECRET` in `.env`
   - Change all admin passwords
   - Revoke all refresh tokens via `SqlAlchemyRefreshTokenRepository.revoke_all_for_account()`
5. **Document findings** and file a security report

### IR-04: High Latency / Performance Degradation

**Symptoms:**
- API responses > 2 seconds
- `union_bank_request_duration_seconds` p95 > 5s

**Severity:** Medium

**Steps:**
1. Check database query performance:
   ```sql
   -- Check for slow queries (SQLite)
   SELECT * FROM sqlite_stat1;
   ```
2. Check if cache is working:
   ```bash
   # Check Redis connectivity
   docker compose exec redis redis-cli ping
   ```
3. Check for lock contention:
   ```sql
   PRAGMA busy_timeout;  -- Should be 5000ms
   ```
4. Restart the API to clear connection pool:
   ```bash
   docker compose restart api
   ```

### IR-05: Redis Is Down

**Symptoms:**
- Cache-related errors in logs
- Higher DB load (cache misses)

**Severity:** Low (non-critical)

**Steps:**
1. Check Redis:
   ```bash
   docker compose logs redis
   docker compose restart redis
   ```
2. The application will automatically fall back to `NullCache` — no data loss
3. No immediate action required if Redis restarts within minutes

---

## 6. Database Maintenance

### Backup

```bash
# Manual backup
cp data/union_bank.db data/backups/union_bank_$(date +%Y%m%d_%H%M%S).db

# Automated backup (add to cron)
0 2 * * * cp /app/data/union_bank.db /app/data/backups/union_bank_$(date +\\%Y\\%m\\%d).db
```

### Manual Cleanup

```sql
-- Remove expired refresh tokens
DELETE FROM refresh_tokens WHERE expires_at < datetime('now');

-- Archive old notifications (older than 90 days)
DELETE FROM notifications WHERE created_at < datetime('now', '-90 days');

-- Clean up old login attempts
DELETE FROM login_attempts WHERE updated_at < datetime('now', '-7 days');
```

### Common SQLite Commands

```bash
# Vacuum (reclaim space)
sqlite3 data/union_bank.db "VACUUM;"

# Integrity check
sqlite3 data/union_bank.db "PRAGMA integrity_check;"

# Foreign key check
sqlite3 data/union_bank.db "PRAGMA foreign_key_check;"

# Show table sizes
sqlite3 data/union_bank.db "SELECT name, pages FROM sqlite_master;"
```

---

## 7. Emergency Contacts

| Role | Contact |
|------|---------|
| **Dev Team Lead** | dev-team@union-bank.example.com |
| **Security Team** | security@union-bank.example.com |
| **Database Admin** | dba@union-bank.example.com |
| **On-Call Engineer** | See PagerDuty rotation |

---

## 8. Appendices

### A. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | Yes | — | HMAC secret for JWT signing (min 32 chars) |
| `JWT_PRIVATE_KEY` | No | — | RSA private key for RS256 signing |
| `JWT_PUBLIC_KEY` | No | — | RSA public key for RS256 verification |
| `REDIS_URL` | No | — | Redis connection string |
| `CORS_ALLOWED_ORIGINS` | No | localhost:5173 | Comma-separated allowed CORS origins |
| `MAX_LOGIN_ATTEMPTS` | No | 5 | Failed login attempts before lockout |
| `LOGIN_LOCKOUT_MINUTES` | No | 15 | Lockout duration in minutes |

### B. Useful Commands

```bash
# Live log tail (JSON format)
tail -f data/bank.jsonl | python -m json.tool

# Count requests by endpoint
grep -o '"endpoint":"[^"]*"' data/bank.jsonl | sort | uniq -c | sort -rn

# Find errors in last hour
grep -E '"level":"ERROR"' data/bank.jsonl | tail -50
```
