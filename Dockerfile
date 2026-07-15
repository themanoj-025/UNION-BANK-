# ═══════════════════════════════════════════════════════════════════════════════
#  UNION BANK MANAGEMENT SYSTEM  —  Dockerfile
# ═══════════════════════════════════════════════════════════════════════════════
#  Multi-stage build:
#    - base:     shared Python environment with all dependencies
#    - api:      FastAPI REST API (port 8000)
#    - dev:      Development with hot-reload
#
#  Usage:
#    docker build --target api -t union-bank/api .
#    docker compose up        # runs api + Redis
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 0: Base Python image ──────────────────────────────────────────────
FROM python:3.11-slim AS base

LABEL org.opencontainers.image.title="Union Bank Management System"
LABEL org.opencontainers.image.description="FastAPI REST API for banking operations"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.licenses="MIT"

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specs first (leverage Docker layer caching)
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (includes src/ directory)
COPY . .

# Create data directory
RUN mkdir -p /app/data && chmod +x scripts/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Default health check (uses liveness probe)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/healthz')" || exit 1


# ── Stage 1: FastAPI (production) ────────────────────────────────────────────
FROM base AS api

ENV ENTRYPOINT_TARGET=api
CMD ["sh", "-c", "exec scripts/docker-entrypoint.sh"]


# ── Stage 2: Development (hot-reload) ────────────────────────────────────────
FROM base AS dev

RUN pip install --no-cache-dir watchfiles

ENV ENTRYPOINT_TARGET=api
CMD ["sh", "-c", "exec scripts/docker-entrypoint.sh"]
