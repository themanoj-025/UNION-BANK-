"""infrastructure/metrics.py  –  Prometheus metrics for Union Bank.

Provides a shared set of metric instruments and a convenience middleware
that automatically records request counts, durations, and errors.

Exposes a ``/metrics`` endpoint via the ``MetricsMiddleware`` that can be
mounted on any ASGI app.

Usage (FastAPI):
    app.add_middleware(MetricsMiddleware)

Then add a route for ``/metrics`` that calls ``generate_latest()``.
"""

from __future__ import annotations

import time
from typing import Optional

from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# ── Metric instruments ──────────────────────────────────────────────────────

# Request count by method, endpoint, and status code
REQUESTS_TOTAL = Counter(
    "union_bank_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

# Request duration in seconds (bucketed histogram)
REQUEST_DURATION_SECONDS = Histogram(
    "union_bank_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# In-flight requests gauge (useful for detecting stuck requests)
INFLIGHT_REQUESTS = Gauge(
    "union_bank_inflight_requests",
    "Current number of in-flight HTTP requests",
    labelnames=["method"],
)

# Total errors by type
ERRORS_TOTAL = Counter(
    "union_bank_errors_total",
    "Total application errors",
    labelnames=["type", "endpoint"],
)

# Active user sessions (from login/logout events)
ACTIVE_SESSIONS = Gauge(
    "union_bank_active_sessions",
    "Current number of active user sessions",
)

# Database query count
DB_QUERIES_TOTAL = Counter(
    "union_bank_db_queries_total",
    "Total database queries",
    labelnames=["operation"],
)

# Cache hit/miss
CACHE_HITS = Counter(
    "union_bank_cache_hits_total",
    "Total cache hits",
    labelnames=["cache"],
)

CACHE_MISSES = Counter(
    "union_bank_cache_misses_total",
    "Total cache misses",
    labelnames=["cache"],
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Convenience helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _normalize_endpoint(path: str) -> str:
    """Normalize a request path to a metric-label-friendly endpoint name.

    Strips trailing slashes, removes query strings, and replaces dynamic
    path segments (like account numbers and IDs) with a placeholder.

    Examples:
        /api/v2/account/1234567890/balance  →  /api/v2/account/.../balance
        /api/v2/savings/abc123              →  /api/v2/savings/...
        /api/health                         →  /api/health

    """
    # Remove query string
    path = path.split("?")[0].rstrip("/")

    # Replace UUID-like / hex segments with placeholder
    import re
    parts = path.split("/")
    cleaned = []
    for part in parts:
        # 10-digit account numbers, 24+ char hex IDs
        if (part.isdigit() and len(part) >= 8) or (
            len(part) >= 20 and all(c in "0123456789abcdef" for c in part.lower())
        ):
            cleaned.append("...")
        else:
            cleaned.append(part)
    return "/".join(cleaned) if cleaned else "/"


# ═══════════════════════════════════════════════════════════════════════════════
#  ASGI middleware (for FastAPI / Starlette)
# ═══════════════════════════════════════════════════════════════════════════════


class MetricsMiddleware:
    """ASGI middleware that automatically records Prometheus metrics.

    Tracks request count, duration, in-flight gauge, and error counts.
    Normalises dynamic URL segments for clean label cardinality.

    Usage:
        app.add_middleware(MetricsMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        endpoint = _normalize_endpoint(path)

        # Track in-flight
        INFLIGHT_REQUESTS.labels(method=method).inc()

        start = time.monotonic()
        status_code = 500  # Default if app crashes

        # Wrap send to capture status code
        async def _send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, _send_wrapper)
        except Exception as exc:
            status_code = 500
            ERRORS_TOTAL.labels(type=type(exc).__name__, endpoint=endpoint).inc()
            raise
        finally:
            duration = time.monotonic() - start
            REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
            REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)
            INFLIGHT_REQUESTS.labels(method=method).dec()



# ═══════════════════════════════════════════════════════════════════════════════
#  Convenience: render the /metrics response content
#  (call from your app's route handler)
# ═══════════════════════════════════════════════════════════════════════════════


def metrics_response() -> tuple[str, str]:
    """Return (content, content_type) for the /metrics endpoint.

    Usage (FastAPI):
        @app.get("/metrics")
        def metrics():
            content, content_type = metrics_response()
            return Response(content=content, media_type=content_type)
    """
    return generate_latest(REGISTRY).decode("utf-8"), "text/plain; version=0.0.4"
