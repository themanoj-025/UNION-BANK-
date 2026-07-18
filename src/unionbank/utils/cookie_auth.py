"""
cookie_auth.py  –  httpOnly cookie-based token storage with CSRF protection.

Replaces localStorage token storage with Secure, httpOnly, SameSite=Strict cookies.
CSRF protection uses the double-submit cookie pattern: a random CSRF token is set
in a readable cookie and must be echoed back in a custom header on state-changing
requests.

Design decisions:
- Access token: httpOnly cookie (not readable by JS), SameSite=Strict, Secure in prod
- Refresh token: httpOnly cookie, SameSite=Strict, Secure in prod
- CSRF token: readable cookie (not httpOnly) + custom header X-CSRF-Token
- Role: stored in a non-sensitive cookie for UI routing decisions
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Request, Response


# ═══════════════════════════════════════════════════════════════════════════════
#  Cookie names
# ═══════════════════════════════════════════════════════════════════════════════

ACCESS_TOKEN_COOKIE = "ub_access_token"
REFRESH_TOKEN_COOKIE = "ub_refresh_token"
CSRF_TOKEN_COOKIE = "ub_csrf_token"
CSRF_TOKEN_HEADER = "X-CSRF-Token"
ROLE_COOKIE = "ub_user_role"


# ═══════════════════════════════════════════════════════════════════════════════
#  Cookie helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _is_secure(request: Request) -> bool:
    """Determine if cookies should be Secure (HTTPS only)."""
    # In production behind a reverse proxy, X-Forwarded-Proto tells us
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto:
        return forwarded_proto == "https"
    return request.url.scheme == "https"


def generate_csrf_token() -> str:
    """Generate a cryptographically random CSRF token."""
    return secrets.token_hex(32)


def set_auth_cookies(
    response: Response,
    request: Request,
    access_token: str,
    refresh_token: Optional[str] = None,
    role: Optional[str] = None,
) -> None:
    """
    Set httpOnly auth cookies on the response.

    Args:
        response:  FastAPI Response object to set cookies on.
        request:   FastAPI Request (used to detect HTTPS for Secure flag).
        access_token:  JWT access token.
        refresh_token: JWT refresh token (optional).
        role:  User role for UI routing (optional).
    """
    secure = _is_secure(request)

    # Access token cookie — httpOnly, not accessible to JS
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=15 * 60,  # 15 minutes (matches access token TTL)
        path="/",
    )

    # Refresh token cookie — httpOnly, longer-lived
    if refresh_token:
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE,
            value=refresh_token,
            httponly=True,
            secure=secure,
            samesite="strict",
            max_age=7 * 24 * 3600,  # 7 days (matches refresh token TTL)
            path="/",
        )

    # CSRF token cookie — NOT httpOnly (must be readable by JS for double-submit)
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_TOKEN_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=secure,
        samesite="strict",
        max_age=15 * 60,  # Same as access token
        path="/",
    )

    # Role cookie — readable by JS for UI routing decisions
    if role:
        response.set_cookie(
            key=ROLE_COOKIE,
            value=role,
            httponly=False,
            secure=secure,
            samesite="strict",
            max_age=15 * 60,
            path="/",
        )


def clear_auth_cookies(response: Response) -> None:
    """Clear all auth cookies (on logout)."""
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/")
    response.delete_cookie(key=CSRF_TOKEN_COOKIE, path="/")
    response.delete_cookie(key=ROLE_COOKIE, path="/")


def get_token_from_cookies(request: Request, cookie_name: str = ACCESS_TOKEN_COOKIE) -> Optional[str]:
    """Extract a token from cookies."""
    return request.cookies.get(cookie_name)


def validate_csrf_token(request: Request) -> bool:
    """
    Validate the CSRF double-submit token.

    Compares the X-CSRF-Token header against the ub_csrf_token cookie.
    Returns True if valid, False otherwise.

    Note: This uses constant-time comparison to prevent timing attacks.
    """
    cookie_token = request.cookies.get(CSRF_TOKEN_COOKIE, "")
    header_token = request.headers.get(CSRF_TOKEN_HEADER, "")

    if not cookie_token or not header_token:
        return False

    return secrets.compare_digest(cookie_token, header_token)


def is_safe_method(method: str) -> bool:
    """Check if the HTTP method is safe (no CSRF protection needed)."""
    return method in ("GET", "HEAD", "OPTIONS")
