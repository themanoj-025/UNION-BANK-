# ═══════════════════════════════════════════════════════════════════════════════
#  UNION BANK MANAGEMENT SYSTEM  —  Dockerfile
# ═══════════════════════════════════════════════════════════════════════════════
#  Multi-stage build:
#    - base:     shared Python environment with all dependencies
#    - web:      Flask web app (port 5000)
#    - api:      FastAPI REST API (port 8000)
#
#  Usage:
#    docker build --target web -t union-bank/web .
#    docker build --target api -t union-bank/api .
#    docker compose up        # runs both + Redis
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 0: Base Python image ──────────────────────────────────────────────
FROM python:3.11-slim AS base

LABEL org.opencontainers.image.title="Union Bank Management System"
LABEL org.opencontainers.image.description="Flask web + FastAPI REST API for banking operations"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.licenses="MIT"

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (minimal — only what Python libs need at compile time)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specs first (leverage Docker layer caching)
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Create data directory (bind-mounted in compose, created here as fallback)
RUN mkdir -p /app/data && chmod +x scripts/docker-entrypoint.sh

# Expose ports
EXPOSE 5000 8000

# Default health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1


# ── Stage 1: Flask Web (production) ──────────────────────────────────────────
FROM base AS web

# Set default env for Flask
ENV FLASK_ENV=production \
    FLASK_DEBUG=0

# Run Flask with gunicorn (production WSGI server) via entrypoint
ENV ENTRYPOINT_TARGET=web
CMD ["sh", "-c", "exec scripts/docker-entrypoint.sh"]


# ── Stage 2: FastAPI (production) ────────────────────────────────────────────
FROM base AS api

# Run FastAPI with uvicorn (production ASGI server) via entrypoint
ENV ENTRYPOINT_TARGET=api
CMD ["sh", "-c", "exec scripts/docker-entrypoint.sh"]


# ── Stage 3: Development (hot-reload for both) ──────────────────────────────
FROM base AS dev

# Install dev dependencies
RUN pip install --no-cache-dir watchfiles

# Default: run the web app with Flask's built-in dev server (hot reload)
ENV ENTRYPOINT_TARGET=web
CMD ["sh", "-c", "exec scripts/docker-entrypoint.sh"]
