#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#  docker-entrypoint.sh  —  Union Bank Docker entrypoint
# ═══════════════════════════════════════════════════════════════════════════════
#  Runs before the main application to ensure the environment is ready:
#    1. Wait for Redis (if configured)
#    2. Run database migrations / seed
#    3. Start the application server
#
#  Usage:
#    ENTRYPOINT_TARGET=api    → starts uvicorn  (FastAPI)
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

info()  { echo -e "${CYAN}ℹ${NC}  $*"; }
ok()    { echo -e "${GREEN}✓${NC}  $*"; }
fail()  { echo -e "${RED}✗${NC}  $*"; }


# ── 1. Wait for Redis (if REDIS_URL is set) ─────────────────────────────────
if [ -n "${REDIS_URL:-}" ]; then
    info "Waiting for Redis at ${REDIS_URL}…"
    # Extract host and port from REDIS_URL (redis://host:port/db)
    REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/redis:\/\/\([^:]*\).*/\1/p')
    REDIS_PORT=$(echo "$REDIS_URL" | sed -n 's/redis:\/\/[^:]*:\([0-9]*\).*/\1/p')
    REDIS_HOST="${REDIS_HOST:-redis}"
    REDIS_PORT="${REDIS_PORT:-6379}"

    for i in $(seq 1 30); do
        if timeout 1 bash -c "echo > /dev/tcp/${REDIS_HOST}/${REDIS_PORT}" 2>/dev/null; then
            ok "Redis is ready (${REDIS_HOST}:${REDIS_PORT})"
            break
        fi
        if [ "$i" -eq 30 ]; then
            fail "Redis not reachable after 30s — starting without cache"
        fi
        sleep 1
    done
fi


# ── 2. Initialize database ──────────────────────────────────────────────────
info "Initializing database…"
python -c "
from database import init_db
init_db()
print('  ✓ Database initialized')
" 2>&1 | while read -r line; do echo "  ${line}"; done
ok "Database ready"


# ── 3. Run migrations (if any pending) ───────────────────────────────────────
if [ -d "alembic/versions" ] && ls alembic/versions/*.py &>/dev/null 2>&1; then
    info "Running Alembic migrations…"
    alembic upgrade head 2>&1 || info "No migrations to run"
    ok "Migrations up to date"
fi


# ── 4. Start the application server ────────────────────────────────────────
echo ""
echo -e "  ${BOLD}═══════════════════════════════════════════${NC}"
echo -e "  ${BOLD}   🏦  Union Bank Management System${NC}"
echo -e "  ${BOLD}═══════════════════════════════════════════${NC}"
echo ""

case "${ENTRYPOINT_TARGET:-api}" in
    api|*)
        info "Starting FastAPI server (uvicorn) on port 8000…"
        exec uvicorn \
            api:app \
            --host 0.0.0.0 \
            --port 8000 \
            --workers "${UVICORN_WORKERS:-4}" \
            --proxy-headers \
            --forwarded-allow-ips '*'
        ;;
esac
