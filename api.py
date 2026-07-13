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
    load_json, save_json, generate_account_number, now_str, fmt_currency,
    hash_password, verify_password, validate_email, validate_phone,
    validate_password, validate_name,
    check_login_locked, record_failed_login, reset_login_attempts,
    calculate_monthly_interest, TRANSACTION_CATEGORIES,
    load_goals, save_goals, generate_goal_id,
    ACCOUNTS_FILE, TRANSACTIONS_FILE, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES,
)
from account import Account
from admin import ADMIN_FILE
from services import (
    process_deposit, process_withdraw, process_transfer,
    process_close_account, process_apply_interest,
    process_freeze_account, process_unfreeze_account,
    process_delete_account, get_bank_statistics,
    admin_authenticate,
    create_savings_goal, contribute_to_goal, delete_savings_goal,
)
from database import init_db

init_db()

# ═══════════════════════════════════════════════════════════════════════════════
#  JWT Configuration — loaded from centralized config
# ═══════════════════════════════════════════════════════════════════════════════

from config import settings
JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_EXPIRY_HOURS = settings.JWT_EXPIRY_HOURS

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
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
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
    token_type: str = "bearer"
    role: str


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
#  JWT Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════

def create_token(subject: str, role: str) -> str:
    """Create a JWT access token."""
    payload = {
        "sub": subject,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Returns the payload dict."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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
    accounts = load_json(ACCOUNTS_FILE)
    if acc_no not in accounts:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists.",
        )
    return accounts[acc_no]


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
    """Authenticate a customer and return a JWT access token."""
    acc_no = req.account_number
    password = req.password

    # Rate limiting
    is_locked, remaining = check_login_locked(acc_no)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked. Try again in {remaining} minute(s).",
        )

    accounts = load_json(ACCOUNTS_FILE)
    if acc_no not in accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    data = accounts[acc_no]

    if data.get("is_frozen", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is frozen. Please contact the bank.",
        )

    if not data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been closed.",
        )

    if not verify_password(password, data["password"]):
        remaining_attempts = record_failed_login(acc_no)
        if remaining_attempts > 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Incorrect password. {remaining_attempts} attempt(s) remaining.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Incorrect password. Account locked for {LOGIN_LOCKOUT_MINUTES} minutes.",
            )

    reset_login_attempts(acc_no)
    token = create_token(subject=acc_no, role="customer")
    return TokenResponse(access_token=token, role="customer")


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
    """Authenticate as admin and return a JWT access token."""
    username = req.username
    password = req.password

    lock_key = f"admin_{username}"
    is_locked, remaining = check_login_locked(lock_key)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Admin account locked. Try again in {remaining} minute(s).",
        )

    auth_result = admin_authenticate(username, password)
    if auth_result.success:
        reset_login_attempts(lock_key)
        token = create_token(subject=username, role="admin")
        return TokenResponse(access_token=token, role="admin")

    remaining_attempts = record_failed_login(lock_key)
    if remaining_attempts > 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials. {remaining_attempts} attempt(s) remaining.",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Admin account locked for {LOGIN_LOCKOUT_MINUTES} minutes.",
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
    accounts = load_json(ACCOUNTS_FILE)
    data = accounts[acc_no]

    if req.name is not None:
        if not validate_name(req.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid name. Must be 2-50 characters (letters and spaces only).",
            )
        data["name"] = req.name

    if req.age is not None:
        data["age"] = req.age

    if req.gender is not None:
        data["gender"] = req.gender

    if req.mobile is not None:
        if not validate_phone(req.mobile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mobile number. Must be 10 digits starting with 6-9.",
            )
        data["mobile"] = req.mobile

    if req.email is not None:
        if not validate_email(req.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format.",
            )
        data["email"] = req.email

    accounts[acc_no] = data
    save_json(ACCOUNTS_FILE, accounts)

    return ProfileResponse(
        account_number=data["account_number"],
        name=data["name"],
        age=data["age"],
        gender=data["gender"],
        mobile=data["mobile"],
        email=data["email"],
        balance=data["balance"],
        balance_formatted=fmt_currency(data["balance"]),
        status=_get_account_status(data),
        created_at=data.get("created_at", "N/A"),
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
    accounts = load_json(ACCOUNTS_FILE)
    data = accounts[acc_no]

    if not verify_password(req.current_password, data["password"]):
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

    data["password"] = hash_password(req.new_password)
    accounts[acc_no] = data
    save_json(ACCOUNTS_FILE, accounts)

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
    # Refresh balance from file
    accounts = load_json(ACCOUNTS_FILE)
    data = accounts[customer["account_number"]]
    return BalanceResponse(
        account_number=data["account_number"],
        name=data["name"],
        balance=data["balance"],
        balance_formatted=fmt_currency(data["balance"]),
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
    accounts = load_json(ACCOUNTS_FILE)
    data = accounts[acc_no]

    # Validate category
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
    accounts = load_json(ACCOUNTS_FILE)
    data = accounts[acc_no]

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
    accounts = load_json(ACCOUNTS_FILE)
    data = accounts[acc_no]

    target_acc_no = req.target_account

    if target_acc_no not in accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient account not found.",
        )

    if target_acc_no == acc_no:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to your own account.",
        )

    target_data = accounts[target_acc_no]
    if target_data.get("is_frozen"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recipient account is frozen.",
        )
    if not target_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recipient account is closed.",
        )

    if req.amount > data["balance"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Available: {fmt_currency(data['balance'])}",
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
        message=f"{fmt_currency(req.amount)} transferred to {target_data['name']} "
                f"({target_acc_no}). New balance: {fmt_currency(result.sender_balance)}",
    )


@app.get("/api/account/statements", response_model=list[TransactionOut])
@limiter.limit("30/minute")
def get_full_statement(request: Request, customer: dict = Depends(get_current_customer)):
    """Get the full transaction statement (newest first)."""
    acc_no = customer["account_number"]
    txns = load_json(TRANSACTIONS_FILE)
    records = txns.get(acc_no, [])

    return [
        TransactionOut(
            txn_id=t.get("txn_id", ""),
            timestamp=t.get("timestamp", ""),
            type=t.get("type", ""),
            amount=t.get("amount", 0),
            balance=t.get("balance", 0),
            description=t.get("description", ""),
            category=t.get("category", "General"),
            target_account=t.get("target_account"),
        )
        for t in reversed(records)
    ]


@app.get("/api/account/statements/mini", response_model=list[TransactionOut])
@limiter.limit("30/minute")
def get_mini_statement(request: Request, customer: dict = Depends(get_current_customer)):
    """Get the last 5 transactions (mini statement)."""
    acc_no = customer["account_number"]
    txns = load_json(TRANSACTIONS_FILE)
    records = txns.get(acc_no, [])
    last5 = records[-5:]

    return [
        TransactionOut(
            txn_id=t.get("txn_id", ""),
            timestamp=t.get("timestamp", ""),
            type=t.get("type", ""),
            amount=t.get("amount", 0),
            balance=t.get("balance", 0),
            description=t.get("description", ""),
            category=t.get("category", "General"),
            target_account=t.get("target_account"),
        )
        for t in reversed(last5)
    ]


@app.get("/api/account/export-csv")
@limiter.limit("10/minute")
def export_csv(request: Request, customer: dict = Depends(get_current_customer)):
    """Download transaction history as a CSV file."""
    acc_no = customer["account_number"]
    txns = load_json(TRANSACTIONS_FILE)
    records = txns.get(acc_no, [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Transaction ID", "Date/Time", "Type", "Amount",
                      "Balance", "Description", "Category"])
    for t in records:
        sign = "+" if t["type"] in ("DEPOSIT", "TRANSFER_IN") else "-"
        writer.writerow([
            t.get("txn_id", ""),
            t.get("timestamp", ""),
            t.get("type", ""),
            f"{sign}{t['amount']}",
            t.get("balance", ""),
            t.get("description", ""),
            t.get("category", "General"),
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
    goals = load_goals(acc_no)

    goal_list = []
    for g in goals:
        pct = round((g["current_amount"] / g["target_amount"] * 100), 1) if g["target_amount"] > 0 else 0
        goal_list.append(SavingsGoalOut(
            goal_id=g["goal_id"],
            name=g["name"],
            target_amount=g["target_amount"],
            current_amount=g["current_amount"],
            target_date=g.get("target_date"),
            created_at=g["created_at"],
            is_completed=g.get("is_completed", False),
            progress_pct=pct,
        ))

    total_saved = sum(g["current_amount"] for g in goals)
    total_target = sum(g["target_amount"] for g in goals)
    completed = sum(1 for g in goals if g.get("is_completed"))

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
    goals = load_goals(acc_no)

    goal = {
        "goal_id": generate_goal_id(),
        "name": req.name,
        "target_amount": round(req.target_amount, 2),
        "current_amount": 0.0,
        "target_date": req.target_date,
        "created_at": now_str(),
        "is_completed": False,
    }
    goals.append(goal)
    save_goals(acc_no, goals)

    return SavingsGoalOut(
        goal_id=goal["goal_id"],
        name=goal["name"],
        target_amount=goal["target_amount"],
        current_amount=goal["current_amount"],
        target_date=goal.get("target_date"),
        created_at=goal["created_at"],
        is_completed=False,
        progress_pct=0.0,
    )


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
    goals = load_goals(acc_no)

    goal = next((g for g in goals if g["goal_id"] == goal_id), None)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    if req.name is not None:
        goal["name"] = req.name
    if req.target_amount is not None:
        goal["target_amount"] = round(req.target_amount, 2)
    if req.target_date is not None:
        goal["target_date"] = req.target_date

    goal["is_completed"] = goal["current_amount"] >= goal["target_amount"]
    save_goals(acc_no, goals)

    pct = round((goal["current_amount"] / goal["target_amount"] * 100), 1) if goal["target_amount"] > 0 else 0
    return SavingsGoalOut(
        goal_id=goal["goal_id"],
        name=goal["name"],
        target_amount=goal["target_amount"],
        current_amount=goal["current_amount"],
        target_date=goal.get("target_date"),
        created_at=goal["created_at"],
        is_completed=goal["is_completed"],
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
    accounts = load_json(ACCOUNTS_FILE)
    data = accounts[acc_no]

    goals = load_goals(acc_no)
    goal = next((g for g in goals if g["goal_id"] == goal_id), None)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    if req.amount > data["balance"]:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: {fmt_currency(data['balance'])}",
        )

    # Transfer from balance to goal
    account = Account(data)
    account.balance -= req.amount
    account.save()
    account.log_transaction("TRANSFER_OUT", req.amount,
                             f"Savings goal: {goal['name']}",
                             category="Savings")

    goal["current_amount"] += req.amount
    if goal["current_amount"] >= goal["target_amount"]:
        goal["is_completed"] = True

    save_goals(acc_no, goals)

    pct = round((goal["current_amount"] / goal["target_amount"] * 100), 1) if goal["target_amount"] > 0 else 0
    return SavingsGoalOut(
        goal_id=goal["goal_id"],
        name=goal["name"],
        target_amount=goal["target_amount"],
        current_amount=goal["current_amount"],
        target_date=goal.get("target_date"),
        created_at=goal["created_at"],
        is_completed=goal["is_completed"],
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
    accounts = load_json(ACCOUNTS_FILE)
    data = accounts[acc_no]

    goals = load_goals(acc_no)
    goal = next((g for g in goals if g["goal_id"] == goal_id), None)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    # Refund to balance
    if goal["current_amount"] > 0:
        account = Account(data)
        account.balance += goal["current_amount"]
        account.save()
        account.log_transaction("DEPOSIT", goal["current_amount"],
                                 f"Refund from deleted goal: {goal['name']}",
                                 category="Savings")

    goals.remove(goal)
    save_goals(acc_no, goals)

    return MessageResponse(
        message=f"Goal '{goal['name']}' deleted. Amount refunded."
    )


@app.post("/api/account/apply-interest", response_model=MessageResponse)
@limiter.limit("5/minute")
def apply_interest(request: Request, customer: dict = Depends(get_current_customer)):
    """Apply monthly interest (3.5% p.a.) using an atomic SQLite transaction."""
    acc_no = customer["account_number"]
    accounts = load_json(ACCOUNTS_FILE)
    data = accounts[acc_no]

    result = process_apply_interest(acc_no, data["balance"])
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
    accounts = load_json(ACCOUNTS_FILE)
    return [
        AccountListItem(
            account_number=a["account_number"],
            name=a["name"],
            balance=a["balance"],
            balance_formatted=fmt_currency(a["balance"]),
            status=_get_account_status(a),
            mobile=a.get("mobile", ""),
            email=a.get("email", ""),
            age=a.get("age", 0),
            gender=a.get("gender", ""),
            created_at=a.get("created_at", "N/A"),
        )
        for a in accounts.values()
    ]


@app.get("/api/admin/accounts/search", response_model=list[AccountListItem])
@limiter.limit("30/minute")
def admin_search_accounts(
    request: Request,
    q: str = Query(..., min_length=1, description="Search by account number or name"),
    admin: dict = Depends(get_current_admin),
):
    """Search accounts by account number or name (admin only)."""
    accounts = load_json(ACCOUNTS_FILE)
    query = q.lower()
    results = [
        a for a in accounts.values()
        if query in a["account_number"].lower() or query in a["name"].lower()
    ]
    return [
        AccountListItem(
            account_number=a["account_number"],
            name=a["name"],
            balance=a["balance"],
            balance_formatted=fmt_currency(a["balance"]),
            status=_get_account_status(a),
            mobile=a.get("mobile", ""),
            email=a.get("email", ""),
            age=a.get("age", 0),
            gender=a.get("gender", ""),
            created_at=a.get("created_at", "N/A"),
        )
        for a in results
    ]


@app.post("/api/admin/accounts/{acc_no}/freeze", response_model=MessageResponse)
@limiter.limit("10/minute")
def admin_freeze_account(
    request: Request,
    acc_no: str,
    admin: dict = Depends(get_current_admin),
):
    """Freeze a customer account (admin only)."""
    accounts = load_json(ACCOUNTS_FILE)

    if acc_no not in accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    acc = accounts[acc_no]
    if not acc.get("is_active", True) and not acc.get("is_frozen", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is permanently closed – cannot modify.",
        )

    if acc.get("is_frozen", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account {acc_no} is already frozen.",
        )

    result = process_freeze_account(acc_no)
    if not result.success:
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
    accounts = load_json(ACCOUNTS_FILE)

    if acc_no not in accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    acc = accounts[acc_no]
    if not acc.get("is_frozen", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account {acc_no} is not frozen.",
        )

    result = process_unfreeze_account(acc_no)
    if not result.success:
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
    accounts = load_json(ACCOUNTS_FILE)

    if acc_no not in accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    acc_name = accounts[acc_no]["name"]
    result = process_delete_account(acc_no)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)

    return MessageResponse(message=result.message)


@app.get("/api/admin/statistics", response_model=StatisticsResponse)
@limiter.limit("30/minute")
def admin_statistics(request: Request, admin: dict = Depends(get_current_admin)):
    """View bank-wide statistics (admin only)."""
    s = get_bank_statistics()

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
    txns = load_json(TRANSACTIONS_FILE)
    result = {}

    for acc_no, records in txns.items():
        if account and acc_no != account:
            continue
        result[acc_no] = [
            {
                "txn_id": t.get("txn_id", ""),
                "timestamp": t.get("timestamp", ""),
                "type": t.get("type", ""),
                "amount": t.get("amount", 0),
                "balance": t.get("balance", 0),
                "description": t.get("description", ""),
                "category": t.get("category", "General"),
                "target_account": t.get("target_account"),
            }
            for t in records
        ]

    return result


@app.put("/api/admin/password", response_model=MessageResponse)
@limiter.limit("5/minute")
def admin_change_password(
    request: Request,
    req: AdminChangePasswordRequest,
    admin: dict = Depends(get_current_admin),
):
    """Change the admin password (admin only)."""
    creds = load_json(ADMIN_FILE)

    if not verify_password(req.current_password, creds["password"]):
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

    creds["password"] = hash_password(req.new_password)
    save_json(ADMIN_FILE, creds)

    return MessageResponse(message="Admin password changed successfully.")


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
