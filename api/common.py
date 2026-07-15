"""
api/common.py  –  Shared JWT authentication helpers.

Extracted from api.py so that both api.py (v1) and api/v2.py (v2)
can import these without circular dependencies.

api.py           → imports router from api/v2.py
api/v2.py        → imports auth helpers from api/common.py
api/common.py    → no dependency on api.py or api/v2.py
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config import settings

# ═══════════════════════════════════════════════════════════════════════════════
#  JWT Configuration
# ═══════════════════════════════════════════════════════════════════════════════

JWT_SECRET = settings.JWT_SECRET
JWT_PRIVATE_KEY = settings.JWT_PRIVATE_KEY
JWT_PUBLIC_KEY = settings.JWT_PUBLIC_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
JWT_REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

# ═══════════════════════════════════════════════════════════════════════════════
#  Security scheme (shared between v1 and v2)
# ═══════════════════════════════════════════════════════════════════════════════

security = HTTPBearer()


# ═══════════════════════════════════════════════════════════════════════════════
#  JWT Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════


def _get_signing_key() -> str:
    """Return the key used for SIGNING (private key for RS256, secret for HS256)."""
    if JWT_ALGORITHM == "RS256" and JWT_PRIVATE_KEY:
        return JWT_PRIVATE_KEY
    return JWT_SECRET


def _get_verifying_key() -> str:
    """Return the key used for VERIFYING (public key for RS256, secret for HS256)."""
    if JWT_ALGORITHM == "RS256" and JWT_PUBLIC_KEY:
        return JWT_PUBLIC_KEY
    return JWT_SECRET


def _get_token_version(account_number: str) -> int:
    """Fetch the current token version for an account from the DB."""
    try:
        from container import get_container
        c = get_container()
        return c.token_version_repo().get_version(account_number)
    except Exception:
        from logger import logger
        logger.warning("Failed to fetch token version", exc_info=True)
        return 0


def _generate_refresh_token_id() -> str:
    """Generate a unique refresh token ID."""
    import uuid
    return f"ref_{uuid.uuid4().hex[:24]}"


def create_token(subject: str, role: str, token_type: str = "access") -> str:
    """Create a JWT token (access or refresh).

    Access tokens are short-lived (default 15 minutes).
    Refresh tokens live longer (default 7 days).

    Access tokens include a token_version claim for invalidation on password change.
    """
    now = datetime.now(timezone.utc)
    if token_type == "refresh":
        expiry = now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        expiry = now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": expiry,
    }

    # Only access tokens carry the token_version (refresh tokens are validated via DB)
    if token_type == "access":
        payload["token_version"] = _get_token_version(subject)

    return jwt.encode(payload, _get_signing_key(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Returns the payload dict."""
    try:
        payload = jwt.decode(token, _get_verifying_key(), algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_token_pair(subject: str, role: str) -> dict:
    """Create an access + refresh token pair.

    The refresh token is persisted in the DB (not just in-memory),
    enabling revocation, expiry tracking, and rotation.
    """
    access_token = create_token(subject, role, token_type="access")
    refresh_token_id = _generate_refresh_token_id()
    refresh_token = create_token(subject + ":" + refresh_token_id, role, token_type="refresh")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    # Persist refresh token in the DB
    try:
        from container import get_container
        from domain.entities import RefreshToken
        c = get_container()
        token_entity = RefreshToken(
            token_id=refresh_token_id,
            account_number=subject,
            role=role,
            expires_at=expires_at,
        )
        c.refresh_token_repo().create(token_entity)
        c.refresh_token_repo().commit()
    except Exception:
        from logger import logger
        logger.warning(
            "Failed to persist refresh token — falling back to memory-only",
            exc_info=True,
        )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "refresh_token_id": refresh_token_id,
        "token_type": "bearer",
        "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def revoke_refresh_token(refresh_token_id: str) -> bool:
    """Revoke a refresh token so it can no longer be used."""
    try:
        from container import get_container
        c = get_container()
        return c.refresh_token_repo().revoke(refresh_token_id)
    except Exception:
        from logger import logger
        logger.warning("Failed to revoke refresh token", exc_info=True)
        return False


def verify_refresh_token(refresh_token: str) -> Optional[dict]:
    """Verify a refresh token and return the subject + role if valid."""
    try:
        payload = jwt.decode(refresh_token, _get_verifying_key(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None

        sub = payload.get("sub", "")
        if ":" not in sub:
            return None
        account_number, token_id = sub.rsplit(":", 1)

        # Check DB for the refresh token
        from container import get_container
        c = get_container()
        token_data = c.refresh_token_repo().get(token_id)
        if token_data is None or token_data.revoked_at is not None:
            return None

        return {"account_number": account_number, "role": payload.get("role")}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Token version validation helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _check_token_version(payload: dict) -> None:
    """Check that the token's version matches the current version in the DB.

    This invalidates all existing JWTs when a password is changed.
    """
    token_version = payload.get("token_version", 0)
    current_version = _get_token_version(payload.get("sub", ""))
    if token_version != current_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Auth Dependencies (used by both v1 and v2 routers)
# ═══════════════════════════════════════════════════════════════════════════════


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Dependency: extract and validate a customer JWT token."""
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required.",
        )

    # Validate token version (invalidates JWTs on password change)
    _check_token_version(payload)

    acc_no = payload.get("sub")
    from container import get_container
    domain_account = get_container().account_repo().get(acc_no)
    if not domain_account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists.",
        )
    return {
        "account_number": domain_account.account_number,
        "name": domain_account.name,
        "age": domain_account.age,
        "gender": domain_account.gender,
        "mobile": domain_account.mobile,
        "email": domain_account.email,
        "balance": float(domain_account.balance),
        "is_active": domain_account.is_active,
        "is_frozen": domain_account.is_frozen,
        "created_at": str(domain_account.created_at)[:19],
    }


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Dependency: extract and validate an admin JWT token."""
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    # Validate token version (invalidates JWTs on password change)
    _check_token_version(payload)

    return {"username": payload.get("sub")}


def get_account_status(data: dict) -> str:
    """Return status string for an account."""
    if data.get("is_frozen", False):
        return "frozen"
    if not data.get("is_active", True):
        return "closed"
    return "active"
