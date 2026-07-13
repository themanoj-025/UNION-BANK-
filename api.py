"""
api.py  –  FastAPI REST API for Union Bank Management System.

Provides a complete REST API with JWT authentication for both customers
and administrators. All business logic is reused from the existing modules.

Run with:
    uvicorn api:app --reload --host 0.0.0.0 --port 8000

Then open http://localhost:8000/docs for interactive API documentation.
"""

import csv
import io
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

import jwt
from fastapi import (
    FastAPI, HTTPException, Depends, status, Query, Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

# ── Project path setup ──────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ── Import existing business logic ───────────────────────────────────────────
from utils import (
    generate_account_number, now_str, fmt_currency,
    hash_password, verify_password, validate_email, validate_phone,
    validate_password, validate_name,
    calculate_monthly_interest, TRANSACTION_CATEGORIES,
    MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES,
)
from services import (
    process_deposit, process_withdraw, process_transfer,
    process_close_account, process_apply_interest,
)
from database import init_db

init_db()

# ═══════════════════════════════════════════════════════════════════════════════
#  JWT Configuration — RS256 asymmetric signing with short-lived tokens
# ═══════════════════════════════════════════════════════════════════════════════

from config import settings

# For RS256 (asymmetric), the private key signs tokens and public key verifies them.
# For HS256 fallback (symmetric), the same secret is used for both operations.
JWT_SECRET = settings.JWT_SECRET
JWT_PRIVATE_KEY = settings.JWT_PRIVATE_KEY
JWT_PUBLIC_KEY = settings.JWT_PUBLIC_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
JWT_REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

# Refresh token storage (in-memory for now; backed by DB for production)
_refresh_tokens: dict[str, dict] = {}  # token_id -> {account_number, role, expires_at, revoked_at}

# ═══════════════════════════════════════════════════════════════════════════════
#  FastAPI Application
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Union Bank API",
    description=(
        "REST API for the Union Bank Management System. "
        "Supports customer banking operations and an admin control panel. "
        "Use `/docs` for interactive API documentation."
    ),
    version="1.0.0",
    contact={"name": "Union Bank Dev Team"},
)

# ── Rate Limiting ────────────────────────────────────────────────────────────
# Disabled in testing mode so integration tests don't get rate-limited
limiter = Limiter(
    key_func=get_remote_address,
    enabled=not settings.TESTING,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Security Headers Middleware ───────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ── CORS — restricted to configured origins ──────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ═══════════════════════════════════════════════════════════════════════════════
#  Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════════

# ── Auth Models ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    account_number: str = Field(..., description="10-digit account number")
    password: str = Field(..., min_length=1, description="Account password")


class RegisterRequest(BaseModel):
    name: str = Field(..., description="Full name (2-50 chars, letters/spaces only)")
    age: int = Field(..., ge=18, le=120, description="Age (18-120)")
    gender: str = Field(..., description="Gender")
    mobile: str = Field(..., description="10-digit mobile number starting with 6-9")
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password: min 8 chars, upper+lower+digit")
    confirm_password: str = Field(..., description="Must match password")


class AdminLoginRequest(BaseModel):
    username: str = Field(..., description="Admin username")
    password: str = Field(..., min_length=1, description="Admin password")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    role: str
    expires_in: Optional[int] = None


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Transaction Models ───────────────────────────────────────────────────────

class TransactionRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Positive transaction amount")
    category: str = Field(default="General", description="Transaction category")


class TransferRequest(BaseModel):
    target_account: str = Field(..., description="Recipient account number")
    amount: float = Field(..., gt=0, description="Transfer amount")
    category: str = Field(default="General", description="Transaction category")


# ── Account Models ───────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=18, le=120)
    gender: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None


class CloseAccountRequest(BaseModel):
    confirm_text: str = Field(..., description="Must be 'CLOSE'")
    password: str


class AdminChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


# ── Response Models ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    status: str = "success"


class BalanceResponse(BaseModel):
    account_number: str
    name: str
    balance: float
    balance_formatted: str


class ProfileResponse(BaseModel):
    account_number: str
    name: str
    age: int
    gender: str
    mobile: str
    email: str
    balance: float
    balance_formatted: str
    status: str
    created_at: str


class TransactionOut(BaseModel):
    txn_id: str
    timestamp: str
    type: str
    amount: float
    balance: float
    description: str
    category: str
    target_account: Optional[str] = None


class AccountListItem(BaseModel):
    account_number: str
    name: str
    balance: float
    balance_formatted: str
    status: str
    mobile: str
    email: str
    age: int
    gender: str
    created_at: str


class StatisticsResponse(BaseModel):
    total_customers: int
    active_accounts: int
    frozen_accounts: int
    closed_accounts: int
    total_balance: float
    total_balance_formatted: str
    total_deposits: float
    total_withdrawals: float
    total_transfers: float
    total_transactions: int


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "Union Bank API"
    version: str = "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
#  JWT Helper Functions — RS256 (asymmetric) or HS256 (symmetric fallback)
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import timezone


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


def _generate_refresh_token_id() -> str:
    """Generate a unique refresh token ID."""
    import uuid
    return f"ref_{uuid.uuid4().hex[:24]}"


def create_token(subject: str, role: str, token_type: str = "access") -> str:
    """Create a JWT token (access or refresh).

    Access tokens are short-lived (default 15 minutes).
    Refresh tokens live longer (default 7 days).
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

    The refresh token can be used to get a new access token without
    requiring the user to re-authenticate.
    """
    access_token = create_token(subject, role, token_type="access")
    refresh_token_id = _generate_refresh_token_id()
    refresh_token = create_token(subject + ":" + refresh_token_id, role, token_type="refresh")

    # Store refresh token metadata for revocation tracking
    now = datetime.now(timezone.utc)
    _refresh_tokens[refresh_token_id] = {
        "account_number": subject,
        "role": role,
        "expires_at": now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "revoked_at": None,
    }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "refresh_token_id": refresh_token_id,
        "token_type": "bearer",
        "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def revoke_refresh_token(refresh_token_id: str) -> bool:
    """Revoke a refresh token so it can no longer be used."""
    if refresh_token_id in _refresh_tokens:
        _refresh_tokens[refresh_token_id]["revoked_at"] = datetime.now(timezone.utc)
        return True
    return False


def verify_refresh_token(refresh_token: str) -> Optional[dict]:
    """Verify a refresh token and return the subject + role if valid."""
    try:
        payload = jwt.decode(refresh_token, _get_verifying_key(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None

        # Extract refresh_token_id from subject (format: "account_number:refresh_token_id")
        sub = payload.get("sub", "")
        if ":" not in sub:
            return None
        account_number, token_id = sub.rsplit(":", 1)

        # Check if revoked
        token_data = _refresh_tokens.get(token_id)
        if token_data is None or token_data["revoked_at"] is not None:
            return None

        return {"account_number": account_number, "role": payload.get("role")}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


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
        "password": domain_account.password,
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
    return {"username": payload.get("sub")}


def _get_account_status(data: dict) -> str:
    """Return status string for an account."""
    if data.get("is_frozen", False):
        return "frozen"
    if not data.get("is_active", True):
        return "closed"
    return "active"


# ═══════════════════════════════════════════════════════════════════════════════
#  Auth Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def customer_login(request: Request, req: LoginRequest):
    """Authenticate a customer and return a JWT access + refresh token pair."""
    from container import get_container
    c = get_container()

    # Use container's auth service for DB-backed authentication
    auth_result = c.auth_service().customer_login(req.account_number, req.password)
    if not auth_result.success:
        if "locked" in auth_result.message.lower():
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=auth_result.message)
        if "not found" in auth_result.message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=auth_result.message)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=auth_result.message)

    # Create access + refresh token pair
    tokens = create_token_pair(subject=req.account_number, role="customer")
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="customer",
        expires_in=tokens["expires_in"],
    )


@app.post("/api/auth/register", response_model=MessageResponse)
@limiter.limit("5/minute")
def customer_register(request: Request, req: RegisterRequest):
    """Register a new customer account."""
    # Validate fields
    if not validate_name(req.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must be 2-50 characters (letters and spaces only).",
        )
    if not validate_phone(req.mobile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mobile number. Must be 10 digits starting with 6-9.",
        )
    if not validate_email(req.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format.",
        )
    valid_pwd, pwd_msg = validate_password(req.password)
    if not valid_pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pwd_msg,
        )
    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    acc_no = generate_account_number()
    data = {
        "account_number": acc_no,
        "name": req.name,
        "age": req.age,
        "gender": req.gender,
        "mobile": req.mobile,
        "email": req.email,
        "password": hash_password(req.password),
        "balance": 0.0,
        "is_active": True,
        "is_frozen": False,
        "created_at": now_str(),
    }
    account = Account(data)
    account.save()

    return MessageResponse(
        message=f"Account created successfully! Account number: {acc_no}",
    )


@app.post("/api/auth/admin-login", response_model=TokenResponse)
@limiter.limit("10/minute")
def admin_login(request: Request, req: AdminLoginRequest):
    """Authenticate as admin and return a JWT access + refresh token pair."""
    from container import get_container
    c = get_container()

    auth_result = c.auth_service().admin_login(req.username, req.password)
    if not auth_result.success:
        if "locked" in auth_result.message.lower():
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=auth_result.message)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=auth_result.message)

    tokens = create_token_pair(subject=req.username, role="admin")
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="admin",
        expires_in=tokens["expires_in"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Customer Account Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/account/profile", response_model=ProfileResponse)
@limiter.limit("30/minute")
def get_profile(request: Request, customer: dict = Depends(get_current_customer)):
    """Get the authenticated customer's profile details."""
    return ProfileResponse(
        account_number=customer["account_number"],
        name=customer["name"],
        age=customer["age"],
        gender=customer["gender"],
        mobile=customer["mobile"],
        email=customer["email"],
        balance=customer["balance"],
        balance_formatted=fmt_currency(customer["balance"]),
        status=_get_account_status(customer),
        created_at=customer.get("created_at", "N/A"),
    )


@app.put("/api/account/profile", response_model=ProfileResponse)
@limiter.limit("10/minute")
def update_profile(
    request: Request,
    req: UpdateProfileRequest,
    customer: dict = Depends(get_current_customer),
):
    """Update the authenticated customer's profile details."""
    acc_no = customer["account_number"]

    from container import get_container
    c = get_container()
    domain_account = c.account_repo().get(acc_no)
    if not domain_account:
        raise HTTPException(status_code=404, detail="Account not found.")

    if req.name is not None:
        if not validate_name(req.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid name. Must be 2-50 characters (letters and spaces only).",
            )
        domain_account.name = req.name

    if req.age is not None:
        domain_account.age = req.age

    if req.gender is not None:
        domain_account.gender = req.gender

    if req.mobile is not None:
        if not validate_phone(req.mobile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mobile number. Must be 10 digits starting with 6-9.",
            )
        domain_account.mobile = req.mobile

    if req.email is not None:
        if not validate_email(req.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format.",
            )
        domain_account.email = req.email

    c.account_repo().update(domain_account)
    c.account_repo().commit()

    return ProfileResponse(
        account_number=domain_account.account_number,
        name=domain_account.name,
        age=domain_account.age,
        gender=domain_account.gender,
        mobile=domain_account.mobile,
        email=domain_account.email,
        balance=float(domain_account.balance),
        balance_formatted=fmt_currency(float(domain_account.balance)),
        status=_get_account_status({
            "is_frozen": domain_account.is_frozen,
            "is_active": domain_account.is_active,
        }),
        created_at=str(domain_account.created_at)[:19],
    )


@app.post("/api/account/change-password", response_model=MessageResponse)
@limiter.limit("5/minute")
def change_password(
    request: Request,
    req: ChangePasswordRequest,
    customer: dict = Depends(get_current_customer),
):
    """Change the authenticated customer's password."""
    acc_no = customer["account_number"]

    from container import get_container
    c = get_container()
    domain_account = c.account_repo().get(acc_no)
    if not domain_account:
        raise HTTPException(status_code=404, detail="Account not found.")

    if not verify_password(req.current_password, domain_account.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password.",
        )

    valid_pwd, pwd_msg = validate_password(req.new_password)
    if not valid_pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pwd_msg,
        )

    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    domain_account.password = hash_password(req.new_password)
    c.account_repo().update(domain_account)
    c.account_repo().commit()

    return MessageResponse(message="Password changed successfully.")


@app.post("/api/account/close", response_model=MessageResponse)
@limiter.limit("3/minute")
def close_account(
    request: Request,
    req: CloseAccountRequest,
    customer: dict = Depends(get_current_customer),
):
    """Close the authenticated customer's account."""
    acc_no = customer["account_number"]

    if req.confirm_text != "CLOSE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please type 'CLOSE' to confirm.",
        )

    if not verify_password(req.password, customer["password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password.",
        )

    result = process_close_account(acc_no, req.password, customer["password"])
    if not result.success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    return MessageResponse(message=result.message)


# ═══════════════════════════════════════════════════════════════════════════════
#  Customer Transaction Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/account/balance", response_model=BalanceResponse)
@limiter.limit("30/minute")
def get_balance(request: Request, customer: dict = Depends(get_current_customer)):
    """Get the current account balance."""
    from container import get_container
    domain_account = get_container().account_repo().get(customer["account_number"])
    if not domain_account:
        raise HTTPException(status_code=404, detail="Account not found.")
    return BalanceResponse(
        account_number=domain_account.account_number,
        name=domain_account.name,
        balance=float(domain_account.balance),
        balance_formatted=fmt_currency(float(domain_account.balance)),
    )


@app.post("/api/account/deposit", response_model=MessageResponse)
@limiter.limit("10/minute")
def deposit_money(
    request: Request,
    req: TransactionRequest,
    customer: dict = Depends(get_current_customer),
):
    """Deposit money into the authenticated customer's account."""
    acc_no = customer["account_number"]
    result = process_deposit(acc_no, req.amount, req.category)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    return MessageResponse(message=result.message)


@app.post("/api/account/withdraw", response_model=MessageResponse)
@limiter.limit("10/minute")
def withdraw_money(
    request: Request,
    req: TransactionRequest,
    customer: dict = Depends(get_current_customer),
):
    """Withdraw money from the authenticated customer's account."""
    acc_no = customer["account_number"]
    result = process_withdraw(acc_no, req.amount, req.category)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    return MessageResponse(message=result.message)


@app.post("/api/account/transfer", response_model=MessageResponse)
@limiter.limit("10/minute")
def transfer_funds(
    request: Request,
    req: TransferRequest,
    customer: dict = Depends(get_current_customer),
):
    """Transfer funds to another account."""
    acc_no = customer["account_number"]
    target_acc_no = req.target_account

    from container import get_container
    c = get_container()

    sender = c.account_repo().get(acc_no)
    if not sender:
        raise HTTPException(status_code=404, detail="Sender account not found.")

    receiver = c.account_repo().get(target_acc_no)
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient account not found.",
        )

    if target_acc_no == acc_no:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to your own account.",
        )

    if receiver.is_frozen:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recipient account is frozen.",
        )
    if not receiver.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recipient account is closed.",
        )

    if req.amount > float(sender.balance):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Available: {fmt_currency(float(sender.balance))}",
        )

    result = process_transfer(
        sender_acc_no=acc_no,
        receiver_acc_no=target_acc_no,
        amount=req.amount,
        category=req.category,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message,
        )

    return MessageResponse(
        message=f"{fmt_currency(req.amount)} transferred to {receiver.name} "
                f"({target_acc_no}). New balance: {fmt_currency(float(result.sender_balance))}",
    )


@app.get("/api/account/statements", response_model=list[TransactionOut])
@limiter.limit("30/minute")
def get_full_statement(request: Request, customer: dict = Depends(get_current_customer)):
    """Get the full transaction statement (newest first)."""
    acc_no = customer["account_number"]
    from container import get_container
    domain_txns = get_container().transaction_repo().get_by_account(acc_no)

    return [
        TransactionOut(
            txn_id=t.txn_id,
            timestamp=str(t.timestamp)[:19],
            type=t.type.value,
            amount=float(t.amount),
            balance=float(t.balance),
            description=t.description,
            category=t.category,
            target_account=t.target_account,
        )
        for t in domain_txns
    ]


@app.get("/api/account/statements/mini", response_model=list[TransactionOut])
@limiter.limit("30/minute")
def get_mini_statement(request: Request, customer: dict = Depends(get_current_customer)):
    """Get the last 5 transactions (mini statement)."""
    acc_no = customer["account_number"]
    from container import get_container
    domain_txns = get_container().transaction_repo().get_mini(acc_no, 5)

    return [
        TransactionOut(
            txn_id=t.txn_id,
            timestamp=str(t.timestamp)[:19],
            type=t.type.value,
            amount=float(t.amount),
            balance=float(t.balance),
            description=t.description,
            category=t.category,
            target_account=t.target_account,
        )
        for t in domain_txns
    ]


@app.get("/api/account/export-csv")
@limiter.limit("10/minute")
def export_csv(request: Request, customer: dict = Depends(get_current_customer)):
    """Download transaction history as a CSV file."""
    acc_no = customer["account_number"]
    from container import get_container
    domain_txns = get_container().transaction_repo().get_by_account(acc_no)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Transaction ID", "Date/Time", "Type", "Amount",
                      "Balance", "Description", "Category"])
    for t in domain_txns:
        sign = "+" if t.type.value in ("DEPOSIT", "TRANSFER_IN") else "-"
        writer.writerow([
            t.txn_id,
            str(t.timestamp)[:19],
            t.type.value,
            f"{sign}{float(t.amount)}",
            float(t.balance),
            t.description,
            t.category or "General",
        ])

    output.seek(0)
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=statement_{acc_no}.csv"},
    )


# ── Savings Goals Models ────────────────────────────────────────────────

class SavingsGoalCreate(BaseModel):
    name: str = Field(..., min_length=2, description="Goal name")
    target_amount: float = Field(..., gt=0, description="Savings target")
    target_date: Optional[str] = Field(None, description="Optional target date (YYYY-MM-DD)")


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = Field(default=None, gt=0)
    target_date: Optional[str] = None


class SavingsGoalContribute(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to contribute")


class SavingsGoalOut(BaseModel):
    goal_id: str
    name: str
    target_amount: float
    current_amount: float
    target_date: Optional[str] = None
    created_at: str
    is_completed: bool
    progress_pct: float = 0.0


class SavingsGoalsSummary(BaseModel):
    total_goals: int
    completed: int
    total_saved: float
    total_saved_formatted: str
    total_target: float
    total_target_formatted: str
    goals: list[SavingsGoalOut]


# ── Savings Goals Endpoints ──────────────────────────────────────────────

@app.get("/api/savings", response_model=SavingsGoalsSummary)
@limiter.limit("30/minute")
def list_savings_goals(request: Request, customer: dict = Depends(get_current_customer)):
    """List all savings goals for the authenticated customer."""
    acc_no = customer["account_number"]
    from container import get_container
    goals = get_container().savings_goal_repo().get_by_account(acc_no)

    goal_list = []
    for g in goals:
        pct = round((float(g.current_amount) / float(g.target_amount) * 100), 1) if float(g.target_amount) > 0 else 0
        goal_list.append(SavingsGoalOut(
            goal_id=g.goal_id,
            name=g.name,
            target_amount=float(g.target_amount),
            current_amount=float(g.current_amount),
            target_date=g.target_date,
            created_at=str(g.created_at)[:19],
            is_completed=g.is_completed,
            progress_pct=pct,
        ))

    total_saved = sum(float(g.current_amount) for g in goals)
    total_target = sum(float(g.target_amount) for g in goals)
    completed = sum(1 for g in goals if g.is_completed)

    return SavingsGoalsSummary(
        total_goals=len(goals),
        completed=completed,
        total_saved=total_saved,
        total_saved_formatted=fmt_currency(total_saved),
        total_target=total_target,
        total_target_formatted=fmt_currency(total_target),
        goals=goal_list,
    )


@app.post("/api/savings", response_model=SavingsGoalOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_savings_goal(
    request: Request,
    req: SavingsGoalCreate,
    customer: dict = Depends(get_current_customer),
):
    """Create a new savings goal."""
    acc_no = customer["account_number"]
    from container import get_container
    result = get_container().savings_goal_service().create_goal(
        acc_no=acc_no,
        name=req.name,
        target_amount=Decimal(str(req.target_amount)),
        target_date=req.target_date,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    # Fetch the newly created goal
    goals = get_container().savings_goal_repo().get_by_account(acc_no)
    if goals:
        g = goals[-1]
        return SavingsGoalOut(
            goal_id=g.goal_id,
            name=g.name,
            target_amount=float(g.target_amount),
            current_amount=float(g.current_amount),
            target_date=g.target_date,
            created_at=str(g.created_at)[:19],
            is_completed=False,
            progress_pct=0.0,
        )
    raise HTTPException(status_code=500, detail="Failed to create goal.")


@app.put("/api/savings/{goal_id}", response_model=SavingsGoalOut)
@limiter.limit("10/minute")
def update_savings_goal(
    request: Request,
    goal_id: str,
    req: SavingsGoalUpdate,
    customer: dict = Depends(get_current_customer),
):
    """Update a savings goal."""
    acc_no = customer["account_number"]
    from container import get_container
    goal_repo = get_container().savings_goal_repo()

    goal = goal_repo.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    if req.name is not None:
        goal.name = req.name
    if req.target_amount is not None:
        goal.target_amount = Decimal(str(req.target_amount))
    if req.target_date is not None:
        goal.target_date = req.target_date

    goal.is_completed = goal.current_amount >= goal.target_amount
    goal_repo.update(goal)
    goal_repo.commit()

    pct = round((float(goal.current_amount) / float(goal.target_amount) * 100), 1) if float(goal.target_amount) > 0 else 0
    return SavingsGoalOut(
        goal_id=goal.goal_id,
        name=goal.name,
        target_amount=float(goal.target_amount),
        current_amount=float(goal.current_amount),
        target_date=goal.target_date,
        created_at=str(goal.created_at)[:19],
        is_completed=goal.is_completed,
        progress_pct=pct,
    )


@app.post("/api/savings/{goal_id}/contribute", response_model=SavingsGoalOut)
@limiter.limit("10/minute")
def contribute_to_goal(
    request: Request,
    goal_id: str,
    req: SavingsGoalContribute,
    customer: dict = Depends(get_current_customer),
):
    """Contribute money from your balance to a savings goal."""
    acc_no = customer["account_number"]
    from container import get_container
    c = get_container()

    # Check current balance from DB
    domain_acc = c.account_repo().get(acc_no)
    if not domain_acc:
        raise HTTPException(status_code=404, detail="Account not found.")
    if req.amount > float(domain_acc.balance):
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: {fmt_currency(float(domain_acc.balance))}",
        )

    result = c.savings_goal_service().contribute(
        acc_no=acc_no, goal_id=goal_id, amount=Decimal(str(req.amount))
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    # Return updated goal
    goal = c.savings_goal_repo().get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    pct = round((float(goal.current_amount) / float(goal.target_amount) * 100), 1) if float(goal.target_amount) > 0 else 0
    return SavingsGoalOut(
        goal_id=goal.goal_id,
        name=goal.name,
        target_amount=float(goal.target_amount),
        current_amount=float(goal.current_amount),
        target_date=goal.target_date,
        created_at=str(goal.created_at)[:19],
        is_completed=goal.is_completed,
        progress_pct=pct,
    )


@app.delete("/api/savings/{goal_id}", response_model=MessageResponse)
@limiter.limit("5/minute")
def delete_savings_goal(
    request: Request,
    goal_id: str,
    customer: dict = Depends(get_current_customer),
):
    """Delete a savings goal and refund the amount to your balance."""
    acc_no = customer["account_number"]
    from container import get_container
    result = get_container().savings_goal_service().delete_goal(
        acc_no=acc_no, goal_id=goal_id
    )
    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)

    return MessageResponse(message=result.message)


@app.post("/api/account/apply-interest", response_model=MessageResponse)
@limiter.limit("5/minute")
def apply_interest(request: Request, customer: dict = Depends(get_current_customer)):
    """Apply monthly interest (3.5% p.a.) using an atomic SQLite transaction."""
    acc_no = customer["account_number"]
    from container import get_container
    domain_account = get_container().account_repo().get(acc_no)
    if not domain_account:
        raise HTTPException(status_code=404, detail="Account not found.")

    result = process_apply_interest(acc_no, float(domain_account.balance))
    if not result.success:
        if "No interest" in result.message:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.message)

    return MessageResponse(message=result.message)


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/accounts", response_model=list[AccountListItem])
@limiter.limit("30/minute")
def admin_view_accounts(request: Request, admin: dict = Depends(get_current_admin)):
    """View all registered accounts (admin only)."""
    from container import get_container
    domain_accounts = get_container().admin_service().list_accounts()
    return [
        AccountListItem(
            account_number=a.account_number,
            name=a.name,
            balance=float(a.balance),
            balance_formatted=fmt_currency(float(a.balance)),
            status="frozen" if a.is_frozen else ("closed" if not a.is_active else "active"),
            mobile=a.mobile,
            email=a.email,
            age=a.age,
            gender=a.gender,
            created_at=str(a.created_at)[:19],
        )
        for a in domain_accounts
    ]


@app.get("/api/admin/accounts/search", response_model=list[AccountListItem])
@limiter.limit("30/minute")
def admin_search_accounts(
    request: Request,
    q: str = Query(..., min_length=1, description="Search by account number or name"),
    admin: dict = Depends(get_current_admin),
):
    """Search accounts by account number or name (admin only)."""
    from container import get_container
    domain_accounts = get_container().admin_service().search_accounts(q)
    return [
        AccountListItem(
            account_number=a.account_number,
            name=a.name,
            balance=float(a.balance),
            balance_formatted=fmt_currency(float(a.balance)),
            status="frozen" if a.is_frozen else ("closed" if not a.is_active else "active"),
            mobile=a.mobile,
            email=a.email,
            age=a.age,
            gender=a.gender,
            created_at=str(a.created_at)[:19],
        )
        for a in domain_accounts
    ]


@app.post("/api/admin/accounts/{acc_no}/freeze", response_model=MessageResponse)
@limiter.limit("10/minute")
def admin_freeze_account(
    request: Request,
    acc_no: str,
    admin: dict = Depends(get_current_admin),
):
    """Freeze a customer account (admin only)."""
    from container import get_container
    result = get_container().admin_service().freeze_account(
        acc_no=acc_no, actor="admin"
    )
    if not result.success:
        if "not found" in result.message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    return MessageResponse(message=result.message)


@app.post("/api/admin/accounts/{acc_no}/unfreeze", response_model=MessageResponse)
@limiter.limit("10/minute")
def admin_unfreeze_account(
    request: Request,
    acc_no: str,
    admin: dict = Depends(get_current_admin),
):
    """Unfreeze a customer account (admin only)."""
    from container import get_container
    result = get_container().admin_service().unfreeze_account(
        acc_no=acc_no, actor="admin"
    )
    if not result.success:
        if "not found" in result.message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    return MessageResponse(message=result.message)


@app.delete("/api/admin/accounts/{acc_no}", response_model=MessageResponse)
@limiter.limit("5/minute")
def admin_delete_account(
    request: Request,
    acc_no: str,
    admin: dict = Depends(get_current_admin),
):
    """Permanently delete a customer account and all its transactions (admin only)."""
    from container import get_container
    result = get_container().admin_service().delete_account(
        acc_no=acc_no, actor="admin"
    )
    if not result.success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)

    return MessageResponse(message=result.message)


@app.get("/api/admin/statistics", response_model=StatisticsResponse)
@limiter.limit("30/minute")
def admin_statistics(request: Request, admin: dict = Depends(get_current_admin)):
    """View bank-wide statistics (admin only)."""
    from container import get_container
    s = get_container().admin_service().get_statistics()

    return StatisticsResponse(
        total_customers=s["total_customers"],
        active_accounts=s["active"],
        frozen_accounts=s["frozen"],
        closed_accounts=s["closed"],
        total_balance=s["total_balance"],
        total_balance_formatted=s["total_balance_formatted"],
        total_deposits=s["total_dep"],
        total_withdrawals=s["total_with"],
        total_transfers=s["total_trans"],
        total_transactions=s["total_txns"],
    )


@app.get("/api/admin/transactions")
@limiter.limit("30/minute")
def admin_view_transactions(
    request: Request,
    account: Optional[str] = Query(None, description="Filter by account number"),
    admin: dict = Depends(get_current_admin),
):
    """View all transactions, optionally filtered by account (admin only)."""
    from container import get_container
    repo = get_container().transaction_repo()

    if account:
        domain_txns = repo.get_by_account(account)
    else:
        domain_txns = repo.get_all()

    result = {}
    for t in domain_txns:
        acc_no = t.account_number
        if acc_no not in result:
            result[acc_no] = []
        result[acc_no].append({
            "txn_id": t.txn_id,
            "timestamp": str(t.timestamp)[:19],
            "type": t.type.value,
            "amount": float(t.amount),
            "balance": float(t.balance),
            "description": t.description,
            "category": t.category,
            "target_account": t.target_account,
        })

    return result


@app.put("/api/admin/password", response_model=MessageResponse)
@limiter.limit("5/minute")
def admin_change_password(
    request: Request,
    req: AdminChangePasswordRequest,
    admin: dict = Depends(get_current_admin),
):
    """Change the admin password (admin only)."""
    username = admin.get("username")
    from container import get_container
    result = get_container().admin_service().change_admin_password(
        username=username or "admin",
        current_pwd=req.current_password,
        new_pwd=req.new_password,
    )
    if not result.success:
        if "not found" in result.message.lower():
            raise HTTPException(status_code=404, detail=result.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    return MessageResponse(message=result.message)


# ═══════════════════════════════════════════════════════════════════════════════
#  Token Refresh Endpoint
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh_token(request: Request, req: RefreshRequest):
    """Exchange a refresh token for a new access + refresh token pair.

    The previous refresh token is revoked (rotation) so it cannot be reused.
    """
    result = verify_refresh_token(req.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    # Revoke old refresh token (rotation)
    # Extract token_id from the old refresh token and revoke it
    try:
        old_payload = jwt.decode(
            req.refresh_token,
            _get_verifying_key(),
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        old_sub = old_payload.get("sub", "")
        if ":" in old_sub:
            _, old_token_id = old_sub.rsplit(":", 1)
            revoke_refresh_token(old_token_id)
    except Exception:
        pass

    tokens = create_token_pair(subject=result["account_number"], role=result["role"])
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role=result["role"],
        expires_in=tokens["expires_in"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/categories", response_model=list[str])
@limiter.limit("30/minute")
def list_categories(request: Request):
    """List all available transaction categories."""
    return TRANSACTION_CATEGORIES


@app.get("/api/health", response_model=HealthResponse)
@limiter.limit("30/minute")
def health_check(request: Request):
    """Health check endpoint."""
    return HealthResponse()


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  Union Bank API - FastAPI")
    print("=" * 50)
    print(f"  Docs   : http://localhost:8000/docs")
    print(f"  OpenAPI: http://localhost:8000/openapi.json")
    print(f"  Ctrl+C to stop")
    print("=" * 50)
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
