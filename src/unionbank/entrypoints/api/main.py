"""main.py  –  FastAPI REST API for Union Bank Management System.

Canonical location: src/unionbank/entrypoints/api/main.py

Provides a complete REST API with JWT authentication for both customers
and administrators. All business logic is reused from the existing modules.

Run with (Docker):
    uvicorn unionbank.entrypoints.api.main:app --reload --host 0.0.0.0 --port 8000

Then open http://localhost:8000/docs for interactive API documentation.
"""

import csv
import io
import logging
import os

# ── Project path setup (MUST be before any src/ imports) ─────────────────────
import secrets
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

import jwt
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

# This file lives at: src/unionbank/entrypoints/api/main.py
# The project root is 4 directories up from here.
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_FILE_DIR))))

_SRC_DIR = os.path.join(_PROJECT_ROOT, 'src')
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Add src/unionbank/ to sys.path (for utils.analyzr_core, domain.*, etc.)
_UNIONBANK_DIR = os.path.join(_SRC_DIR, 'unionbank')
if _UNIONBANK_DIR not in sys.path:
    sys.path.insert(0, _UNIONBANK_DIR)

# Add src/unionbank/entrypoints/ to sys.path (so 'api.common' resolves)
_API_PARENT = os.path.join(_UNIONBANK_DIR, 'entrypoints')
if _API_PARENT not in sys.path:
    sys.path.insert(0, _API_PARENT)

if _FILE_DIR not in sys.path:
    sys.path.insert(0, _FILE_DIR)

# ── Observability helpers ──────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
#  FastAPI Application
# ═══════════════════════════════════════════════════════════════════════════════
from contextlib import asynccontextmanager

# ── Shared JWT auth helpers (used by v1 and v2 routers) ───────────────────
from api.common import (
    _get_verifying_key,
    create_token_pair,
    get_current_admin,
    get_current_customer,
    revoke_refresh_token,
    verify_refresh_token,
)
from api.common import (
    get_account_status as _get_account_status,
)

# ── V2 API router (envelope-wrapped endpoints) ───────────────────────────────
from api.v2 import router as v2_router
from config import settings
from infrastructure.metrics import MetricsMiddleware, metrics_response
from logger import clear_context, get_request_id, logger, set_account_context, set_request_id

# ── Import existing business logic ───────────────────────────────────────────
from utils import (
    LOGIN_LOCKOUT_MINUTES,
    MAX_LOGIN_ATTEMPTS,
    TRANSACTION_CATEGORIES,
    calculate_monthly_interest,
    fmt_currency,
    generate_account_number,
    hash_password,
    now_str,
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
    verify_password,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on startup and clean up on shutdown.

    Using a lifespan handler instead of module-level init_db() call
    ensures that all imports are fully resolved and __package__ is
    set correctly before any database operations run.
    """
    from database import init_db
    init_db()
    yield
    # No shutdown cleanup needed for SQLite


app = FastAPI(lifespan=lifespan,
    title="Union Bank API",
    description=(
        "REST API for the Union Bank Management System.\n\n"
        "**API Versions**\n"
        "- `/api/v1/` — Legacy endpoints (bare response models, backward compatible)\n"
        "- `/api/v2/` — Current endpoints with standardised `ApiResponse[T]` envelope\n\n"
        "All endpoints return JSON. Authentication uses Bearer JWT tokens.\n"
        "Use `/docs` for interactive API documentation."
    ),
    version="2.0.0",
    contact={"name": "Union Bank Dev Team"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    terms_of_service="https://union-bank.example.com/terms",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "v2 - Auth",
            "description": "Authentication and token management (v2 envelope)",
        },
        {
            "name": "v2 - Account",
            "description": "Customer account profile and management (v2 envelope)",
        },
        {
            "name": "v2 - Transactions",
            "description": "Deposit, withdraw, transfer, and statements (v2 envelope)",
        },
        {
            "name": "v2 - Savings Goals",
            "description": "Create, contribute to, and manage savings goals (v2 envelope)",
        },
        {
            "name": "v2 - Admin",
            "description": "Admin operations: account oversight and statistics (v2 envelope)",
        },
        {
            "name": "v2 - Utilities",
            "description": "Health check and category listing (v2 envelope)",
        },
    ],
)

# ── Request ID + logging context middleware ────────────────────────────────
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Assign a unique request ID and set up logging context for each request."""
    request_id = request.headers.get("X-Request-ID") or secrets.token_hex(16)
    set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        clear_context()


# ── Prometheus metrics middleware ───────────────────────────────────────────
app.add_middleware(MetricsMiddleware)


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

# ── CSRF Protection Middleware ───────────────────────────────────────────────
class CSRFProtectMiddleware(BaseHTTPMiddleware):
    """Validate Origin/Referer on state-changing requests (defense in depth).

    Since the API uses Bearer tokens in Authorization headers (not cookies),
    it is inherently immune to traditional CSRF attacks. This middleware adds
    an extra layer of defense by logging suspicious cross-origin requests.

    To enable strict blocking (not recommended for Bearer-token APIs):
        settings.ENABLE_CSRF_BLOCK = True
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    async def dispatch(self, request: Request, call_next):
        if request.method not in self.SAFE_METHODS:
            origin = request.headers.get("Origin", "")
            referer = request.headers.get("Referer", "")

            if origin or referer:
                allowed_origins = set(settings.CORS_ALLOWED_ORIGINS)
                is_valid = False
                if origin in allowed_origins:
                    is_valid = True
                if referer:
                    for allowed in allowed_origins:
                        if referer.startswith(allowed):
                            is_valid = True
                            break
                if not is_valid:
                    logger.warning(
                        "Cross-origin request blocked",
                        extra={
                            "method": request.method,
                            "path": request.url.path,
                            "origin": origin or "(missing)",
                            "referer": referer or "(missing)",
                        }
                    )

        response = await call_next(request)
        return response

app.add_middleware(CSRFProtectMiddleware)


# ── CORS — restricted to configured origins ──────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Uvicorn access log configuration (module-level, applies in ALL run modes) ─
# Route access logs through the structured JSON logger for observability.
# Uses bank.jsonl (the JSON log file) so all structured logs live together.
from logger import JsonFormatter

# Use _PROJECT_ROOT (computed in bootstrap above) for a path that works
# whether main.py is imported directly or via ASGI transport.
_JSON_LOG_DIR = os.path.join(_PROJECT_ROOT, 'data')
os.makedirs(_JSON_LOG_DIR, exist_ok=True)
_JSON_LOG_FILE = os.path.join(_JSON_LOG_DIR, "bank.jsonl")
_access_json_handler = logging.FileHandler(_JSON_LOG_FILE, encoding="utf-8")
_access_json_handler.setFormatter(JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S.%fZ"))
_access_json_handler.setLevel(logging.INFO)

# Uvicorn access logger — JSON to bank.jsonl, no console (keeps terminal clean)
_uvicorn_logger = logging.getLogger("uvicorn.access")
_uvicorn_logger.handlers = []  # Replace default handlers
_uvicorn_logger.addHandler(_access_json_handler)
_uvicorn_logger.propagate = False

# Uvicorn error logger — console only (stderr errors should be visible)
_uvicorn_error_logger = logging.getLogger("uvicorn.error")
_uvicorn_error_logger.propagate = False

# Mount the V2 router
# Note: V2 endpoints handle their own errors via _err() helper raising HTTPException
# with the ApiResponse dict as the detail. We do NOT register global exception handlers
# here because they would override FastAPI's default error format for V1 endpoints
# (which the frontend expects as {"detail": "message"}).
app.include_router(v2_router)

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
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6, description="TOTP code (required if 2FA is enabled)")


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
    account_number: Optional[str] = None  # For admin views that show transactions across accounts


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
    version: str = "2.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
#  Auth Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/login", response_model=TokenResponse, deprecated=True)
@limiter.limit("10/minute")
def customer_login(request: Request, req: LoginRequest):
    response = Response()
    response.headers["Sunset"] = "Sat, 31 Jan 2027 23:59:59 GMT"
    response.headers["Deprecation"] = "true"
    """Authenticate a customer and return a JWT access + refresh token pair."""
    from infrastructure.container import get_container
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

    from infrastructure.container import get_container
    c = get_container()
    result = c.auth_service().customer_register(
        name=req.name, age=req.age, gender=req.gender,
        mobile=req.mobile, email=req.email, password=req.password,
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    return MessageResponse(
        message=result.message,
    )


@app.post("/api/auth/admin-login", response_model=TokenResponse)
@limiter.limit("10/minute")
def admin_login(request: Request, req: AdminLoginRequest):
    """Authenticate as admin and return a JWT access + refresh token pair."""
    from infrastructure.container import get_container
    c = get_container()

    auth_result = c.auth_service().admin_login(req.username, req.password)
    if not auth_result.success:
        if "locked" in auth_result.message.lower():
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=auth_result.message)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=auth_result.message)

    # Check TOTP 2FA if enabled
    admin_user = c.admin_repo().get_by_username(req.username)
    if admin_user and admin_user.totp_enabled:
        if not req.totp_code:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="Two-factor authentication is enabled. Please provide your TOTP code.",
            )
        import pyotp
        totp = pyotp.TOTP(admin_user.totp_secret)
        if not totp.verify(req.totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP code.",
            )

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

    from infrastructure.container import get_container
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

    from infrastructure.container import get_container
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

    from infrastructure.container import get_container
    result = get_container().account_service().close_account(acc_no, req.password)
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
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
    result = get_container().transaction_service().deposit(
        acc_no=acc_no, amount=Decimal(str(req.amount)), category=req.category
    )
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
    from infrastructure.container import get_container
    result = get_container().transaction_service().withdraw(
        acc_no=acc_no, amount=Decimal(str(req.amount)), category=req.category
    )
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

    from infrastructure.container import get_container
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

    result = c.transaction_service().transfer(
        sender_acc_no=acc_no,
        receiver_acc_no=target_acc_no,
        amount=Decimal(str(req.amount)),
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
    from infrastructure.container import get_container
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
            account_number=t.account_number,
        )
        for t in domain_txns
    ]


@app.get("/api/account/statements/mini", response_model=list[TransactionOut])
@limiter.limit("30/minute")
def get_mini_statement(request: Request, customer: dict = Depends(get_current_customer)):
    """Get the last 5 transactions (mini statement)."""
    acc_no = customer["account_number"]
    from infrastructure.container import get_container
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
            account_number=t.account_number,
        )
        for t in domain_txns
    ]


@app.get("/api/account/export-csv")
@limiter.limit("10/minute")
def export_csv(request: Request, customer: dict = Depends(get_current_customer)):
    """Download transaction history as a CSV file."""
    acc_no = customer["account_number"]
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
    domain_account = get_container().account_repo().get(acc_no)
    if not domain_account:
        raise HTTPException(status_code=404, detail="Account not found.")

    result = get_container().transaction_service().apply_interest(acc_no)
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
def admin_view_accounts(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: dict = Depends(get_current_admin),
):
    """View all registered accounts with pagination (admin only)."""
    from infrastructure.container import get_container
    from infrastructure.cache import get_cache

    cache = get_cache()
    cache_key = f"admin:accounts:page:{page}:per:{per_page}"

    # Try cache first
    cached = cache.get_json(cache_key)
    if cached is not None:
        return [AccountListItem(**item) for item in cached]

    domain_accounts = get_container().admin_service().list_accounts()

    # Paginate in memory (acceptable for admin panels with moderate account counts)
    total = len(domain_accounts)
    start = (page - 1) * per_page
    end = start + per_page
    page_accounts = domain_accounts[start:end]

    result = [
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
        for a in page_accounts
    ]

    # Cache for 60 seconds (stale data acceptable for admin list views)
    cache.set_json(cache_key, [item.model_dump() for item in result], ttl=60)

    return result


@app.get("/api/admin/accounts/search", response_model=list[AccountListItem])
@limiter.limit("30/minute")
def admin_search_accounts(
    request: Request,
    q: str = Query(..., min_length=1, description="Search by account number or name"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: dict = Depends(get_current_admin),
):
    """Search accounts by account number or name (admin only)."""
    from infrastructure.container import get_container
    from infrastructure.cache import get_cache

    cache = get_cache()
    cache_key = f"admin:accounts:search:{q}:page:{page}:per:{per_page}"

    cached = cache.get_json(cache_key)
    if cached is not None:
        return [AccountListItem(**item) for item in cached]

    domain_accounts = get_container().admin_service().search_accounts(q)

    total = len(domain_accounts)
    start = (page - 1) * per_page
    end = start + per_page
    page_accounts = domain_accounts[start:end]

    result = [
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
        for a in page_accounts
    ]

    cache.set_json(cache_key, [item.model_dump() for item in result], ttl=60)

    return result


@app.post("/api/admin/accounts/{acc_no}/freeze", response_model=MessageResponse)
@limiter.limit("10/minute")
def admin_freeze_account(
    request: Request,
    acc_no: str,
    admin: dict = Depends(get_current_admin),
):
    """Freeze a customer account (admin only)."""
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
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
    from infrastructure.container import get_container
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


@app.get("/api/admin/transactions", response_model=list[TransactionOut])
@limiter.limit("30/minute")
def admin_view_transactions(
    request: Request,
    account: Optional[str] = Query(None, description="Filter by account number"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=500, description="Items per page"),
    admin: dict = Depends(get_current_admin),
):
    """View all transactions, optionally filtered by account (admin only).

    Returns a flat array (not grouped by account) for easier client-side processing.
    Use the `account_number` field to group on the client side.
    Paginated via offset-based pagination.
    """
    from infrastructure.container import get_container
    c = get_container()

    if account:
        domain_txns, total = c.transaction_service().get_paginated_transactions(
            acc_no=account, page=page, per_page=per_page
        )
    else:
        domain_txns, total = c.transaction_service().get_paginated_transactions(
            page=page, per_page=per_page
        )

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
            account_number=t.account_number,
        )
        for t in domain_txns
    ]


@app.put("/api/admin/password", response_model=MessageResponse)
@limiter.limit("5/minute")
def admin_change_password(
    request: Request,
    req: AdminChangePasswordRequest,
    admin: dict = Depends(get_current_admin),
):
    """Change the admin password (admin only)."""
    username = admin.get("username")
    from infrastructure.container import get_container
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
        from logger import logger
        logger.warning("Failed to revoke old refresh token during rotation", exc_info=True)

    tokens = create_token_pair(subject=result["account_number"], role=result["role"])
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role=result["role"],
        expires_in=tokens["expires_in"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  TOTP 2FA Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_uri: str
    manual: str


class TOTPVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class TOTPStatusResponse(BaseModel):
    enabled: bool


@app.get("/api/admin/2fa/status", response_model=TOTPStatusResponse)
@limiter.limit("30/minute")
def admin_totp_status(request: Request, admin: dict = Depends(get_current_admin)):
    """Check if 2FA is enabled for the current admin."""
    username = admin.get("username")
    from infrastructure.container import get_container
    c = get_container()
    admin_user = c.admin_repo().get_by_username(username)
    return TOTPStatusResponse(enabled=bool(admin_user and admin_user.totp_enabled))


@app.get("/api/admin/2fa/setup", response_model=TOTPSetupResponse)
@limiter.limit("5/minute")
def admin_totp_setup(request: Request, admin: dict = Depends(get_current_admin)):
    """Generate a new TOTP secret and provisioning URI for the admin user."""
    import pyotp
    username = admin.get("username")

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=username,
        issuer_name="Union Bank Admin",
    )

    # Store the secret temporarily (not enabled until verified)
    from infrastructure.container import get_container
    c = get_container()
    admin_user = c.admin_repo().get_by_username(username)
    if admin_user:
        c.admin_repo().update_totp(username, secret, False)
        c.admin_repo().commit()

    return TOTPSetupResponse(
        secret=secret,
        qr_uri=provisioning_uri,
        manual=f"otpauth://totp/Union%20Bank%20Admin:{username}?secret={secret}&issuer=Union%20Bank%20Admin",
    )


@app.post("/api/admin/2fa/verify", response_model=MessageResponse)
@limiter.limit("10/minute")
def admin_totp_verify(
    request: Request,
    req: TOTPVerifyRequest,
    admin: dict = Depends(get_current_admin),
):
    """Verify a TOTP code to enable 2FA for the admin account."""
    import pyotp
    username = admin.get("username")

    from infrastructure.container import get_container
    c = get_container()
    admin_user = c.admin_repo().get_by_username(username)
    if not admin_user or not admin_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No TOTP secret generated. Call GET /api/admin/2fa/setup first.",
        )

    totp = pyotp.TOTP(admin_user.totp_secret)
    if not totp.verify(req.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Please try again.",
        )

    c.admin_repo().update_totp(username, admin_user.totp_secret, True)
    c.admin_repo().commit()

    return MessageResponse(message="Two-factor authentication enabled successfully.")


@app.post("/api/admin/2fa/disable", response_model=MessageResponse)
@limiter.limit("5/minute")
def admin_totp_disable(
    request: Request,
    req: TOTPVerifyRequest,
    admin: dict = Depends(get_current_admin),
):
    """Disable 2FA for the admin account (requires current TOTP code)."""
    import pyotp
    username = admin.get("username")

    from infrastructure.container import get_container
    c = get_container()
    admin_user = c.admin_repo().get_by_username(username)
    if not admin_user or not admin_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled.",
        )

    totp = pyotp.TOTP(admin_user.totp_secret)
    if not totp.verify(req.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code.",
        )

    c.admin_repo().update_totp(username, None, False)
    c.admin_repo().commit()

    return MessageResponse(message="Two-factor authentication disabled.")


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


@app.get("/api/healthz")
def liveness_probe():
    """Kubernetes liveness probe — returns 200 if the process is alive."""
    return {"status": "alive"}


@app.get("/api/readyz")
def readiness_probe():
    """Kubernetes readiness probe — checks database connectivity."""
    from infrastructure.database import get_session
    from sqlalchemy import text
    try:
        session = get_session()
        session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "database": str(e)},
        )


@app.get("/metrics")
def metrics_endpoint():
    """Prometheus metrics endpoint. Scraped by Prometheus or any metrics collector."""
    from fastapi.responses import Response
    content, content_type = metrics_response()
    return Response(content=content, media_type=content_type)


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  Union Bank API - FastAPI")
    print("=" * 50)
    print("  Docs   : http://localhost:8000/docs")
    print("  OpenAPI: http://localhost:8000/openapi.json")
    print("  Metrics: http://localhost:8000/metrics")
    print("  Health : http://localhost:8000/api/health")
    print("  Ctrl+C to stop")
    print("=" * 50)

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, access_log=True)
