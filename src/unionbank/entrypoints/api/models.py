"""api/models.py  –  Shared Pydantic models for the Union Bank REST API.

Includes the generic ApiResponse[T] envelope type and all request/response
models used by v1 and v2 endpoints.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════════
#  Structured Error Codes
# ═══════════════════════════════════════════════════════════════════════════════


class ErrorCode(str, Enum):
    """Standardised error codes clients can handle programmatically.

    Format: ER### where:
        ER0xx = Auth errors
        ER1xx = Validation errors
        ER2xx = Account errors
        ER3xx = Transaction errors
        ER4xx = Loan errors
        ER5xx = Admin/System errors
        ER9xx = Unknown/Internal errors

    Error responses include the code in the meta field:
        { "success": false, "error": "Insufficient balance.",
          "meta": { "error_code": "ER301" } }
    """

    # ── Auth errors (ER0xx) ────────────────────────────────────────────────
    AUTH_INVALID_CREDENTIALS = "ER001"
    AUTH_ACCOUNT_LOCKED = "ER002"
    AUTH_TOKEN_EXPIRED = "ER003"
    AUTH_TOKEN_INVALID = "ER004"
    AUTH_FORBIDDEN = "ER005"
    AUTH_REFRESH_INVALID = "ER006"

    # ── Validation errors (ER1xx) ──────────────────────────────────────────
    VALIDATION_NAME = "ER101"
    VALIDATION_EMAIL = "ER102"
    VALIDATION_PHONE = "ER103"
    VALIDATION_PASSWORD = "ER104"
    VALIDATION_PASSWORD_MISMATCH = "ER105"
    VALIDATION_AMOUNT = "ER106"
    VALIDATION_CONFIRM = "ER107"

    # ── Account errors (ER2xx) ─────────────────────────────────────────────
    ACCOUNT_NOT_FOUND = "ER201"
    ACCOUNT_FROZEN = "ER202"
    ACCOUNT_CLOSED = "ER203"
    ACCOUNT_ALREADY_FROZEN = "ER204"
    ACCOUNT_ALREADY_CLOSED = "ER205"
    ACCOUNT_NOT_FROZEN = "ER206"

    # ── Transaction errors (ER3xx) ─────────────────────────────────────────
    TXN_INSUFFICIENT_BALANCE = "ER301"
    TXN_SELF_TRANSFER = "ER302"
    TXN_RECIPIENT_NOT_FOUND = "ER303"
    TXN_RECIPIENT_FROZEN = "ER304"
    TXN_RECIPIENT_CLOSED = "ER305"
    TXN_NO_INTEREST = "ER306"

    # ── Loan errors (ER4xx) ────────────────────────────────────────────────
    LOAN_NOT_FOUND = "ER401"
    LOAN_NOT_PENDING = "ER402"
    LOAN_INVALID_TYPE = "ER403"
    LOAN_AMOUNT_RANGE = "ER404"
    LOAN_TENURE_RANGE = "ER405"
    LOAN_RATE_RANGE = "ER406"
    LOAN_ACCOUNT_MISMATCH = "ER407"

    # ── Admin/System errors (ER5xx) ────────────────────────────────────────
    ADMIN_NOT_FOUND = "ER501"
    ADMIN_INVALID_PASSWORD = "ER502"
    RATE_LIMIT_EXCEEDED = "ER503"
    GOAL_NOT_FOUND = "ER504"
    SAVINGS_INSUFFICIENT = "ER505"

    # ── Unknown/Internal (ER9xx) ───────────────────────────────────────────
    INTERNAL_ERROR = "ER901"
    UNKNOWN = "ER999"


# ═══════════════════════════════════════════════════════════════════════════════
#  Generic API Response Envelope
# ═══════════════════════════════════════════════════════════════════════════════

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Generic API response envelope.

    Every v2 endpoint returns a standardised wrapper with:
      success  – boolean indicating operation success.
      data     – the response payload (null on error).
      error    – human-readable error message (null on success).
      meta     – optional metadata (pagination cursors, error_code, timestamps, etc.).

    Example (success):
      { "success": true, "data": { "balance": 2500.00 }, "error": null, "meta": null }

    Example (error):
      { "success": false, "data": null, "error": "Insufficient balance.",
        "meta": { "error_code": "ER301" } }
    """

    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Pagination meta
# ═══════════════════════════════════════════════════════════════════════════════


class PageMeta(BaseModel):
    """Pagination metadata included in ApiResponse.meta for list endpoints."""

    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 1


class KeysetMeta(BaseModel):
    """Keyset (cursor) pagination metadata for ApiResponse.meta."""

    cursor: Optional[str] = None
    has_more: bool = False
    cursor_key: str = "timestamp"


# ═══════════════════════════════════════════════════════════════════════════════
#  Auth Request Models
# ═══════════════════════════════════════════════════════════════════════════════


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


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token from previous login")


# ═══════════════════════════════════════════════════════════════════════════════
#  Auth Response Models
# ═══════════════════════════════════════════════════════════════════════════════


class TokenData(BaseModel):
    """Payload inside ApiResponse.data for /auth/* endpoints."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    role: str
    expires_in: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Transaction Request Models
# ═══════════════════════════════════════════════════════════════════════════════


class TransactionRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Positive transaction amount")
    category: str = Field(default="General", description="Transaction category")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key for retry-safe operations")


class TransferRequest(BaseModel):
    target_account: str = Field(..., description="Recipient account number")
    amount: float = Field(..., gt=0, description="Transfer amount")
    category: str = Field(default="General", description="Transaction category")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key for retry-safe operations")


# ═══════════════════════════════════════════════════════════════════════════════
#  Account Request Models
# ═══════════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════════
#  Account Response Models
# ═══════════════════════════════════════════════════════════════════════════════


class BalanceData(BaseModel):
    """Account balance payload."""

    account_number: str
    name: str
    balance: float
    balance_formatted: str


class ProfileData(BaseModel):
    """Customer profile payload."""

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


class AccountListItem(BaseModel):
    """Account list item for admin views."""

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


# ═══════════════════════════════════════════════════════════════════════════════
#  Transaction Response Models
# ═══════════════════════════════════════════════════════════════════════════════


class TransactionOut(BaseModel):
    """Single transaction in a statement."""

    txn_id: str
    timestamp: str
    type: str
    amount: float
    balance: float
    description: str
    category: str
    target_account: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Loan Models
# ═══════════════════════════════════════════════════════════════════════════════


class LoanApplyRequest(BaseModel):
    loan_type: str = Field(..., description="Personal, Home, Vehicle, Education, Business")
    principal_amount: float = Field(..., gt=0, description="Desired loan amount")
    interest_rate: float = Field(..., gt=0, le=50, description="Annual interest rate %")
    tenure_months: int = Field(..., gt=0, le=360, description="Loan tenure in months")
    purpose: str = Field(default="", max_length=500, description="Purpose of the loan")


class EMICalculateRequest(BaseModel):
    principal: float = Field(..., gt=0, description="Principal amount")
    annual_rate: float = Field(..., gt=0, le=50, description="Annual interest rate %")
    tenure_months: int = Field(..., gt=0, le=360, description="Tenure in months")


class EMIPreviewData(BaseModel):
    principal: float
    annual_rate: float
    tenure_months: int
    emi: float
    total_payable: float
    total_interest: float


class LoanOut(BaseModel):
    loan_id: str
    account_number: str
    loan_type: str
    principal_amount: float
    interest_rate: float
    tenure_months: int
    emi_amount: float
    amount_paid: float
    remaining_amount: float
    status: str
    application_date: str
    approval_date: Optional[str] = None
    next_emi_date: Optional[str] = None
    purpose: str = ""
    admin_notes: str = ""
    progress_pct: float = 0.0
    remaining_emis: int = 0
    is_overdue: bool = False


class LoanSummaryData(BaseModel):
    total_loans: int
    active_loans: int
    closed_loans: int
    total_disbursed: float
    total_disbursed_formatted: str
    total_outstanding: float
    total_outstanding_formatted: str
    loans: list[LoanOut]


class LoanAdminStats(BaseModel):
    total_pending: int
    total_approved: int
    total_active: int
    total_closed: int
    total_rejected: int
    total_disbursed: float
    total_disbursed_formatted: str
    total_outstanding: float
    total_outstanding_formatted: str


class LoanPayEMIRequest(BaseModel):
    amount: Optional[float] = Field(None, gt=0, description="Amount to pay (defaults to full EMI)")


class LoanRejectRequest(BaseModel):
    reason: str = Field(default="", max_length=500, description="Rejection reason")


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings Goal Models
# ═══════════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Response Models
# ═══════════════════════════════════════════════════════════════════════════════


class StatisticsData(BaseModel):
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


class HealthData(BaseModel):
    status: str = "healthy"
    service: str = "Union Bank API"
    version: str = "2.0.0"
    api_version: str = "v2"


# ═══════════════════════════════════════════════════════════════════════════════
#  Generic "message" payload
# ═══════════════════════════════════════════════════════════════════════════════


class AnalyzrQueryRequest(BaseModel):
    """Natural-language transaction search request."""

    query: str = Field(..., min_length=1, description="Natural-language query (e.g. 'large deposits last month')")
    account_number: Optional[str] = Field(None, description="Account number to scope the search")
    max_results: int = Field(50, ge=1, le=200, description="Maximum number of results")


class MessageData(BaseModel):
    message: str
