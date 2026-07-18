"""
api/v2.py  –  V2 API Router with standardised ApiResponse[T] envelopes.

All endpoints return the same shape:
    { "success": true/false, "data": ..., "error": ..., "meta": ... }

V2 also introduces:
  - Generic error handling (no bare HTTPExceptions)
  - Keyset-cursor pagination for statements
  - Consistent response structure
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import jwt
from unionbank.entrypoints.api.common import (
    _get_verifying_key,
    create_token_pair,
    get_current_admin,
    get_current_customer,
    revoke_refresh_token,
    verify_refresh_token,
)
from unionbank.entrypoints.api.models import (
    AccountListItem,
    AdminLoginRequest,
    AnalyzrQueryRequest,
    ApiResponse,
    BalanceData,
    ChangePasswordRequest,
    CloseAccountRequest,
    EMICalculateRequest,
    EMIPreviewData,
    ErrorCode,
    HealthData,
    KeysetMeta,
    LoanAdminStats,
    LoanApplyRequest,
    LoanOut,
    LoanPayEMIRequest,
    LoanRejectRequest,
    LoanSummaryData,
    LoginRequest,
    MessageData,
    ProfileData,
    RefreshRequest,
    RegisterRequest,
    SavingsGoalContribute,
    SavingsGoalCreate,
    SavingsGoalOut,
    SavingsGoalsSummary,
    StatisticsData,
    TokenData,
    TransactionOut,
    TransactionRequest,
    TransferRequest,
    UpdateProfileRequest,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

router = APIRouter(prefix="/api/v2")


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _get_container():
    """Lazy-import the DI container."""
    from unionbank.infrastructure.container import get_container
    return get_container()


def _fmt_currency(val: float) -> str:
    from unionbank.utils import fmt_currency as _fc
    return _fc(val)


# ═══════════════════════════════════════════════════════════════════════════════
#  Response helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _ok(data, meta: Optional[dict] = None) -> ApiResponse:
    """Build a success response."""
    return ApiResponse(success=True, data=data, meta=meta)


def _err(message: str, status_code: int = 400, error_code: str | None = None):
    """
    Build an error response (raises HTTPException with envelope body).

    Args:
        message:     Human-readable error message.
        status_code: HTTP status code (default 400).
        error_code:  Optional structured ErrorCode for programmatic handling.

    """
    meta = {"error_code": error_code} if error_code else None
    resp = ApiResponse(success=False, error=message, meta=meta)
    raise HTTPException(status_code=status_code, detail=resp.model_dump())


# ── Custom exception handler — returns flat envelope for errors ──────────


# Exception handlers must be added to the FastAPI app instance, not APIRouter
async def v2_http_exception_handler(request, exc: HTTPException):
    """
    Override FastAPI's default exception handler for the v2 router.

    Instead of wrapping the error in {"detail": {...}}, we return the
    ApiResponse envelope directly as the response body.
    """
    from fastapi.responses import JSONResponse

    detail = exc.detail
    if isinstance(detail, dict):
        # Already an ApiResponse dict — pass through directly
        return JSONResponse(status_code=exc.status_code, content=detail)
    # Plain string detail — wrap in standard error envelope
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(success=False, error=str(detail)).model_dump(),
    )

# Exception handlers must be added to the FastAPI app instance, not APIRouter
async def v2_generic_exception_handler(request, exc: Exception):
    """Catch unhandled exceptions and return a 500 envelope response."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False, error="An unexpected error occurred."
        ).model_dump(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Auth Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/auth/login", response_model=ApiResponse[TokenData])
def v2_customer_login(req: LoginRequest, request: Request, response: Response):
    """
    Authenticate a customer and return a JWT access + refresh token pair.

    Tokens are set as httpOnly cookies (primary) and returned in the
    response body (backward compatibility).
    """
    from unionbank.utils.cookie_auth import set_auth_cookies

    c = _get_container()
    auth_result = c.auth_service().customer_login(req.account_number, req.password)

    if not auth_result.success:
        msg = auth_result.message.lower()
        if "locked" in msg:
            _err(auth_result.message, status.HTTP_429_TOO_MANY_REQUESTS, ErrorCode.AUTH_ACCOUNT_LOCKED)
        if "not found" in msg:
            _err(auth_result.message, status.HTTP_404_NOT_FOUND, ErrorCode.ACCOUNT_NOT_FOUND)
        _err(auth_result.message, status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTH_INVALID_CREDENTIALS)

    tokens = create_token_pair(subject=req.account_number, role="customer")

    # Set httpOnly cookies — primary token storage
    set_auth_cookies(
        response=response,
        request=request,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="customer",
    )

    return _ok(TokenData(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="customer",
        expires_in=tokens["expires_in"],
    ))


@router.post("/auth/register", response_model=ApiResponse[MessageData])
def v2_customer_register(req: RegisterRequest):
    """Register a new customer account."""
    from unionbank.utils import validate_email, validate_name, validate_password, validate_phone

    if not validate_name(req.name):
        _err("Name must be 2-50 characters (letters and spaces only).")
    if not validate_phone(req.mobile):
        _err("Invalid mobile number. Must be 10 digits starting with 6-9.")
    if not validate_email(req.email):
        _err("Invalid email format.")
    valid_pwd, pwd_msg = validate_password(req.password)
    if not valid_pwd:
        _err(pwd_msg)
    if req.password != req.confirm_password:
        _err("Passwords do not match.")

    c = _get_container()
    result = c.auth_service().customer_register(
        name=req.name, age=req.age, gender=req.gender,
        mobile=req.mobile, email=req.email, password=req.password,
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/auth/admin-login", response_model=ApiResponse[TokenData])
def v2_admin_login(req: AdminLoginRequest, request: Request, response: Response):
    """
    Authenticate as admin and return a JWT access + refresh token pair.

    Tokens are set as httpOnly cookies (primary) and returned in the
    response body (backward compatibility).
    """
    from unionbank.utils.cookie_auth import set_auth_cookies

    c = _get_container()
    auth_result = c.auth_service().admin_login(req.username, req.password)

    if not auth_result.success:
        msg = auth_result.message.lower()
        if "locked" in msg:
            _err(auth_result.message, status.HTTP_429_TOO_MANY_REQUESTS)
        _err(auth_result.message, status.HTTP_401_UNAUTHORIZED)

    tokens = create_token_pair(subject=req.username, role="admin")

    # Set httpOnly cookies — primary token storage
    set_auth_cookies(
        response=response,
        request=request,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="admin",
    )

    return _ok(TokenData(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="admin",
        expires_in=tokens["expires_in"],
    ))


@router.post("/auth/refresh", response_model=ApiResponse[TokenData])
def v2_refresh_token(request: Request, response: Response, req: Optional[RefreshRequest] = None):
    """
    Exchange a refresh token for a new access + refresh token pair.

    Accepts the refresh token from either:
    1. The request body (backward compatibility)
    2. The ub_refresh_token httpOnly cookie (new cookie-based flow)

    The previous refresh token is revoked (rotation) so it cannot be reused.
    """
    from unionbank.utils.cookie_auth import (
        get_token_from_cookies, set_auth_cookies,
    )
    from unionbank.utils.logger import logger

    # Get refresh token from body or cookie
    refresh_token_value = None
    if req and req.refresh_token:
        refresh_token_value = req.refresh_token
    else:
        refresh_token_value = get_token_from_cookies(request, "ub_refresh_token")

    if not refresh_token_value:
        _err("No refresh token provided.", status.HTTP_401_UNAUTHORIZED)

    result = verify_refresh_token(refresh_token_value)
    if result is None:
        _err("Invalid or expired refresh token.", status.HTTP_401_UNAUTHORIZED)

    # Revoke old refresh token (rotation)
    try:
        old_payload = jwt.decode(
            refresh_token_value,
            _get_verifying_key(),
            algorithms=["RS256", "HS256"],
            options={"verify_exp": False},
        )
        old_sub = old_payload.get("sub", "")
        if ":" in old_sub:
            _, old_token_id = old_sub.rsplit(":", 1)
            revoke_refresh_token(old_token_id)
    except Exception:
        logger.warning("Failed to revoke old refresh token during rotation", exc_info=True)

    tokens = create_token_pair(subject=result["account_number"], role=result["role"])

    # Set new httpOnly cookies
    set_auth_cookies(
        response=response,
        request=request,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role=result["role"],
    )

    return _ok(TokenData(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role=result["role"],
        expires_in=tokens["expires_in"],
    ))


# ═══════════════════════════════════════════════════════════════════════════════
#  Customer Account Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/account/profile", response_model=ApiResponse[ProfileData])
def v2_get_profile(customer: dict = Depends(get_current_customer)):
    """Get the authenticated customer's profile details."""
    from unionbank.entrypoints.api.common import get_account_status

    return _ok(ProfileData(
        account_number=customer["account_number"],
        name=customer["name"],
        age=customer["age"],
        gender=customer["gender"],
        mobile=customer["mobile"],
        email=customer["email"],
        balance=customer["balance"],
        balance_formatted=_fmt_currency(customer["balance"]),
        status=get_account_status(customer),
        created_at=customer.get("created_at", "N/A"),
    ))


@router.put("/account/profile", response_model=ApiResponse[ProfileData])
def v2_update_profile(req: UpdateProfileRequest, customer: dict = Depends(get_current_customer)):
    """Update the authenticated customer's profile details."""
    from unionbank.entrypoints.api.common import get_account_status
    from unionbank.utils import validate_email, validate_name, validate_phone

    acc_no = customer["account_number"]
    c = _get_container()
    domain_account = c.account_repo().get(acc_no)
    if not domain_account:
        _err("Account not found.", status.HTTP_404_NOT_FOUND)

    if req.name is not None:
        if not validate_name(req.name):
            _err("Invalid name. Must be 2-50 characters (letters and spaces only).")
        domain_account.name = req.name
    if req.age is not None:
        domain_account.age = req.age
    if req.gender is not None:
        domain_account.gender = req.gender
    if req.mobile is not None:
        if not validate_phone(req.mobile):
            _err("Invalid mobile number. Must be 10 digits starting with 6-9.")
        domain_account.mobile = req.mobile
    if req.email is not None:
        if not validate_email(req.email):
            _err("Invalid email format.")
        domain_account.email = req.email

    c.account_repo().update(domain_account)
    c.account_repo().commit()

    return _ok(ProfileData(
        account_number=domain_account.account_number,
        name=domain_account.name,
        age=domain_account.age,
        gender=domain_account.gender,
        mobile=domain_account.mobile,
        email=domain_account.email,
        balance=float(domain_account.balance),
        balance_formatted=_fmt_currency(float(domain_account.balance)),
        status=get_account_status({
            "is_frozen": domain_account.is_frozen,
            "is_active": domain_account.is_active,
        }),
        created_at=str(domain_account.created_at)[:19],
    ))


@router.post("/account/change-password", response_model=ApiResponse[MessageData])
def v2_change_password(req: ChangePasswordRequest, customer: dict = Depends(get_current_customer)):
    """Change the authenticated customer's password."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.account_service().change_password(
        acc_no=acc_no, current_pwd=req.current_password, new_pwd=req.new_password
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/account/close", response_model=ApiResponse[MessageData])
def v2_close_account(req: CloseAccountRequest, customer: dict = Depends(get_current_customer)):
    """Close the authenticated customer's account."""
    if req.confirm_text != "CLOSE":
        _err("Please type 'CLOSE' to confirm.")

    from unionbank.utils import verify_password

    acc_no = customer["account_number"]
    c = _get_container()

    domain_account = c.account_repo().get(acc_no)
    if not domain_account:
        _err("Account not found.", status.HTTP_404_NOT_FOUND)

    if not verify_password(req.password, domain_account.password):
        _err("Incorrect password.")

    result = c.account_service().close_account(acc_no=acc_no, password=req.password)
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


# ═══════════════════════════════════════════════════════════════════════════════
#  Customer Transaction Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/account/balance", response_model=ApiResponse[BalanceData])
def v2_get_balance(customer: dict = Depends(get_current_customer)):
    """Get the current account balance."""
    c = _get_container()
    domain_account = c.account_repo().get(customer["account_number"])
    if not domain_account:
        _err("Account not found.", status.HTTP_404_NOT_FOUND)

    return _ok(BalanceData(
        account_number=domain_account.account_number,
        name=domain_account.name,
        balance=float(domain_account.balance),
        balance_formatted=_fmt_currency(float(domain_account.balance)),
    ))


@router.post("/account/deposit", response_model=ApiResponse[MessageData])
def v2_deposit_money(req: TransactionRequest, customer: dict = Depends(get_current_customer)):
    """Deposit money into the authenticated customer's account."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.transaction_service().deposit(
        acc_no=acc_no, amount=Decimal(str(req.amount)), category=req.category,
        idempotency_key=req.idempotency_key,
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/account/withdraw", response_model=ApiResponse[MessageData])
def v2_withdraw_money(req: TransactionRequest, customer: dict = Depends(get_current_customer)):
    """Withdraw money from the authenticated customer's account."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.transaction_service().withdraw(
        acc_no=acc_no, amount=Decimal(str(req.amount)), category=req.category,
        idempotency_key=req.idempotency_key,
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/account/transfer", response_model=ApiResponse[MessageData])
def v2_transfer_funds(req: TransferRequest, customer: dict = Depends(get_current_customer)):
    """Transfer funds to another account."""
    acc_no = customer["account_number"]
    c = _get_container()

    sender = c.account_repo().get(acc_no)
    if not sender:
        _err("Sender account not found.", status.HTTP_404_NOT_FOUND)

    receiver = c.account_repo().get(req.target_account)
    if not receiver:
        _err("Recipient account not found.", status.HTTP_404_NOT_FOUND)

    result = c.transaction_service().transfer(
        sender_acc_no=acc_no,
        receiver_acc_no=req.target_account,
        amount=Decimal(str(req.amount)),
        category=req.category,
        idempotency_key=req.idempotency_key,
    )
    if not result.success:
        _err(result.error_message)

    return _ok(MessageData(
        message=f"{_fmt_currency(req.amount)} transferred to {receiver.name} "
                f"({req.target_account}). New balance: {_fmt_currency(float(result.sender_balance))}"
    ))


@router.get("/account/statements", response_model=ApiResponse[list[TransactionOut]])
def v2_get_full_statement(customer: dict = Depends(get_current_customer)):
    """Get the full transaction statement (newest first)."""
    acc_no = customer["account_number"]
    c = _get_container()
    domain_txns = c.transaction_repo().get_by_account(acc_no)

    return _ok([
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
    ])


@router.get("/account/statements/mini", response_model=ApiResponse[list[TransactionOut]])
def v2_get_mini_statement(customer: dict = Depends(get_current_customer)):
    """Get the last 5 transactions (mini statement)."""
    acc_no = customer["account_number"]
    c = _get_container()
    domain_txns = c.transaction_repo().get_mini(acc_no, 5)

    return _ok([
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
    ])


@router.get("/account/statements/keyset", response_model=ApiResponse[list[TransactionOut]])
def v2_get_statement_keyset(
    cursor: Optional[str] = Query(None, description="Timestamp cursor from previous page"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    customer: dict = Depends(get_current_customer),
):
    """
    Get paginated statement using keyset (cursor-based) pagination.

    More efficient than offset-based pagination on large datasets.
    Include the `cursor` value from the previous page's meta to get the next page.
    """
    acc_no = customer["account_number"]
    c = _get_container()

    cursor_dt: Optional[datetime] = None
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except (ValueError, TypeError):
            _err("Invalid cursor format. Use ISO 8601 timestamp.")

    page = c.transaction_service().get_paginated_keyset(
        acc_no=acc_no, limit=limit, cursor=cursor_dt
    )

    items = [
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
        for t in page.items
    ]

    next_cursor = str(page.cursor) if page.cursor else None
    return _ok(items, meta=KeysetMeta(
        cursor=next_cursor,
        has_more=page.has_more,
        cursor_key=page.cursor_key,
    ).model_dump())


@router.get("/account/export-csv", response_model=None)
def v2_export_csv(customer: dict = Depends(get_current_customer)):
    """Download transaction history as a CSV file."""
    import csv
    import io

    acc_no = customer["account_number"]
    c = _get_container()
    domain_txns = c.transaction_repo().get_by_account(acc_no)

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


# ═══════════════════════════════════════════════════════════════════════════════
#  Savings Goals Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/savings", response_model=ApiResponse[SavingsGoalsSummary])
def v2_list_savings_goals(customer: dict = Depends(get_current_customer)):
    """List all savings goals for the authenticated customer."""
    acc_no = customer["account_number"]
    c = _get_container()
    goals = c.savings_goal_repo().get_by_account(acc_no)

    goal_list = []
    for g in goals:
        pct = round((float(g.current_amount) / float(g.target_amount) * 100), 1) if float(g.target_amount) > 0 else 0
        goal_list.append(SavingsGoalOut(
            goal_id=g.goal_id, name=g.name,
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

    return _ok(SavingsGoalsSummary(
        total_goals=len(goals), completed=completed,
        total_saved=total_saved, total_saved_formatted=_fmt_currency(total_saved),
        total_target=total_target, total_target_formatted=_fmt_currency(total_target),
        goals=goal_list,
    ))


@router.post("/savings", response_model=ApiResponse[SavingsGoalOut], status_code=status.HTTP_201_CREATED)
def v2_create_savings_goal(req: SavingsGoalCreate, customer: dict = Depends(get_current_customer)):
    """Create a new savings goal."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.savings_goal_service().create_goal(
        acc_no=acc_no, name=req.name,
        target_amount=Decimal(str(req.target_amount)),
        target_date=req.target_date,
    )
    if not result.success:
        _err(result.message)

    goals = c.savings_goal_repo().get_by_account(acc_no)
    if goals:
        g = goals[-1]
        return _ok(SavingsGoalOut(
            goal_id=g.goal_id, name=g.name,
            target_amount=float(g.target_amount),
            current_amount=float(g.current_amount),
            target_date=g.target_date,
            created_at=str(g.created_at)[:19],
            is_completed=False, progress_pct=0.0,
        ))
    _err("Failed to create goal.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/savings/{goal_id}/contribute", response_model=ApiResponse[SavingsGoalOut])
def v2_contribute_to_goal(goal_id: str, req: SavingsGoalContribute, customer: dict = Depends(get_current_customer)):
    """Contribute money from your balance to a savings goal."""
    acc_no = customer["account_number"]
    c = _get_container()

    result = c.savings_goal_service().contribute(
        acc_no=acc_no, goal_id=goal_id, amount=Decimal(str(req.amount))
    )
    if not result.success:
        _err(result.message)

    goal = c.savings_goal_repo().get(goal_id)
    if not goal:
        _err("Goal not found.", status.HTTP_404_NOT_FOUND)

    pct = round((float(goal.current_amount) / float(goal.target_amount) * 100), 1) if float(goal.target_amount) > 0 else 0
    return _ok(SavingsGoalOut(
        goal_id=goal.goal_id, name=goal.name,
        target_amount=float(goal.target_amount),
        current_amount=float(goal.current_amount),
        target_date=goal.target_date,
        created_at=str(goal.created_at)[:19],
        is_completed=goal.is_completed, progress_pct=pct,
    ))


@router.delete("/savings/{goal_id}", response_model=ApiResponse[MessageData])
def v2_delete_savings_goal(goal_id: str, customer: dict = Depends(get_current_customer)):
    """Delete a savings goal and refund the amount to your balance."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.savings_goal_service().delete_goal(acc_no=acc_no, goal_id=goal_id)
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


# ═══════════════════════════════════════════════════════════════════════════════
#  Loan Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/loans", response_model=ApiResponse[LoanSummaryData])
def v2_list_loans(customer: dict = Depends(get_current_customer)):
    """List all loans for the authenticated customer."""
    acc_no = customer["account_number"]
    c = _get_container()
    loans = c.loan_service().list_loans(acc_no)

    loan_list = []
    for loan in loans:
        pct = float(loan.amount_paid / loan.principal_amount * 100) if loan.principal_amount > 0 else 0
        remaining_emis = int(loan.remaining_amount / loan.emi_amount) + (1 if loan.remaining_amount % loan.emi_amount > 0 else 0) if loan.emi_amount > 0 else 0
        is_overdue = False
        if loan.next_emi_date and loan.status in ("APPROVED", "ACTIVE"):
            is_overdue = datetime.now(timezone.utc) > loan.next_emi_date

        loan_list.append(LoanOut(
            loan_id=loan.loan_id, account_number=loan.account_number,
            loan_type=loan.loan_type, principal_amount=float(loan.principal_amount),
            interest_rate=float(loan.interest_rate), tenure_months=loan.tenure_months,
            emi_amount=float(loan.emi_amount), amount_paid=float(loan.amount_paid),
            remaining_amount=float(loan.remaining_amount), status=loan.status,
            application_date=str(loan.application_date)[:19],
            approval_date=str(loan.approval_date)[:19] if loan.approval_date else None,
            next_emi_date=str(loan.next_emi_date)[:19] if loan.next_emi_date else None,
            purpose=loan.purpose, admin_notes=loan.admin_notes,
            progress_pct=round(pct, 1), remaining_emis=remaining_emis,
            is_overdue=is_overdue,
        ))

    active_loans = sum(1 for loan in loans if loan.status in ("APPROVED", "ACTIVE"))
    closed_loans = sum(1 for loan in loans if loan.status == "CLOSED")
    total_disbursed = sum(float(loan.principal_amount) for loan in loans if loan.status in ("APPROVED", "ACTIVE", "CLOSED"))
    total_outstanding = sum(float(loan.remaining_amount) for loan in loans if loan.status in ("APPROVED", "ACTIVE"))

    return _ok(LoanSummaryData(
        total_loans=len(loans), active_loans=active_loans,
        closed_loans=closed_loans,
        total_disbursed=total_disbursed,
        total_disbursed_formatted=_fmt_currency(total_disbursed),
        total_outstanding=total_outstanding,
        total_outstanding_formatted=_fmt_currency(total_outstanding),
        loans=loan_list,
    ))


@router.post("/loans/apply", response_model=ApiResponse[MessageData], status_code=status.HTTP_201_CREATED)
def v2_apply_loan(req: LoanApplyRequest, customer: dict = Depends(get_current_customer)):
    """Apply for a new loan."""
    acc_no = customer["account_number"]
    c = _get_container()

    result = c.loan_service().apply_loan(
        acc_no=acc_no,
        loan_type=req.loan_type,
        principal_amount=Decimal(str(req.principal_amount)),
        interest_rate=Decimal(str(req.interest_rate)),
        tenure_months=req.tenure_months,
        purpose=req.purpose,
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.get("/loans/{loan_id}", response_model=ApiResponse[LoanOut])
def v2_get_loan(loan_id: str, customer: dict = Depends(get_current_customer)):
    """Get details of a specific loan."""
    acc_no = customer["account_number"]
    c = _get_container()
    loan = c.loan_service().get_loan(loan_id)

    if not loan:
        _err("Loan not found.", status.HTTP_404_NOT_FOUND)
    if loan.account_number != acc_no:
        _err("Loan not found for this account.", status.HTTP_404_NOT_FOUND)

    pct = float(loan.amount_paid / loan.principal_amount * 100) if loan.principal_amount > 0 else 0
    remaining_emis = int(loan.remaining_amount / loan.emi_amount) + (1 if loan.remaining_amount % loan.emi_amount > 0 else 0) if loan.emi_amount > 0 else 0
    is_overdue = False
    if loan.next_emi_date and loan.status in ("APPROVED", "ACTIVE"):
        is_overdue = datetime.now(timezone.utc) > loan.next_emi_date

    return _ok(LoanOut(
        loan_id=loan.loan_id, account_number=loan.account_number,
        loan_type=loan.loan_type, principal_amount=float(loan.principal_amount),
        interest_rate=float(loan.interest_rate), tenure_months=loan.tenure_months,
        emi_amount=float(loan.emi_amount), amount_paid=float(loan.amount_paid),
        remaining_amount=float(loan.remaining_amount), status=loan.status,
        application_date=str(loan.application_date)[:19],
        approval_date=str(loan.approval_date)[:19] if loan.approval_date else None,
        next_emi_date=str(loan.next_emi_date)[:19] if loan.next_emi_date else None,
        purpose=loan.purpose, admin_notes=loan.admin_notes,
        progress_pct=round(pct, 1), remaining_emis=remaining_emis,
        is_overdue=is_overdue,
    ))


@router.post("/loans/{loan_id}/pay-emi", response_model=ApiResponse[MessageData])
def v2_pay_emi(loan_id: str, req: LoanPayEMIRequest, customer: dict = Depends(get_current_customer)):
    """Pay the monthly EMI for a loan."""
    acc_no = customer["account_number"]
    c = _get_container()

    amount = Decimal(str(req.amount)) if req.amount is not None else None
    result = c.loan_service().pay_emi(
        acc_no=acc_no, loan_id=loan_id, amount=amount
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/loans/calculate-emi", response_model=ApiResponse[EMIPreviewData])
def v2_calculate_emi(req: EMICalculateRequest):
    """Calculate EMI preview without applying for a loan."""
    c = _get_container()
    result = c.loan_service().calculate_emi_preview(
        principal=req.principal, annual_rate=req.annual_rate,
        tenure_months=req.tenure_months,
    )
    return _ok(EMIPreviewData(**result))


# ── Admin: Loan Management ─────────────────────────────────────────────────────


@router.get("/admin/loans", response_model=ApiResponse[LoanAdminStats])
def v2_admin_list_loans(admin: dict = Depends(get_current_admin)):
    """View all loan applications with statistics (admin only)."""
    c = _get_container()
    stats = c.loan_service().get_loan_statistics()

    return _ok(LoanAdminStats(
        total_pending=stats["total_pending"],
        total_approved=stats["total_approved"],
        total_active=stats["total_active"],
        total_closed=stats["total_closed"],
        total_rejected=stats["total_rejected"],
        total_disbursed=stats["total_disbursed"],
        total_disbursed_formatted=_fmt_currency(stats["total_disbursed"]),
        total_outstanding=stats["total_outstanding"],
        total_outstanding_formatted=_fmt_currency(stats["total_outstanding"]),
    ))


@router.get("/admin/loans/pending", response_model=ApiResponse[list[LoanOut]])
def v2_admin_list_pending_loans(admin: dict = Depends(get_current_admin)):
    """View all pending loan applications (admin only)."""
    c = _get_container()
    loans = c.loan_service().list_pending()

    return _ok([
        LoanOut(
            loan_id=loan.loan_id, account_number=loan.account_number,
            loan_type=loan.loan_type, principal_amount=float(loan.principal_amount),
            interest_rate=float(loan.interest_rate), tenure_months=loan.tenure_months,
            emi_amount=float(loan.emi_amount), amount_paid=float(loan.amount_paid),
            remaining_amount=float(loan.remaining_amount), status=loan.status,
            application_date=str(loan.application_date)[:19],
            purpose=loan.purpose,
            progress_pct=0.0, remaining_emis=loan.tenure_months, is_overdue=False,
        )
        for loan in loans
    ])


@router.post("/admin/loans/{loan_id}/approve", response_model=ApiResponse[MessageData])
def v2_admin_approve_loan(loan_id: str, admin: dict = Depends(get_current_admin)):
    """Approve a pending loan application and disburse funds (admin only)."""
    c = _get_container()
    result = c.loan_service().approve_loan(
        loan_id=loan_id, admin_user=admin.get("username", "admin")
    )
    if not result.success:
        if "not found" in result.message.lower():
            _err(result.message, status.HTTP_404_NOT_FOUND)
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/admin/loans/{loan_id}/reject", response_model=ApiResponse[MessageData])
def v2_admin_reject_loan(loan_id: str, req: LoanRejectRequest, admin: dict = Depends(get_current_admin)):
    """Reject a pending loan application (admin only)."""
    c = _get_container()
    result = c.loan_service().reject_loan(
        loan_id=loan_id, reason=req.reason,
        admin_user=admin.get("username", "admin"),
    )
    if not result.success:
        if "not found" in result.message.lower():
            _err(result.message, status.HTTP_404_NOT_FOUND)
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.get("/admin/loans/all", response_model=ApiResponse[list[LoanOut]])
def v2_admin_list_all_loans(admin: dict = Depends(get_current_admin)):
    """View all loan applications (admin only)."""
    c = _get_container()
    loans = c.loan_service().list_all()

    return _ok([
        LoanOut(
            loan_id=loan.loan_id, account_number=loan.account_number,
            loan_type=loan.loan_type, principal_amount=float(loan.principal_amount),
            interest_rate=float(loan.interest_rate), tenure_months=loan.tenure_months,
            emi_amount=float(loan.emi_amount), amount_paid=float(loan.amount_paid),
            remaining_amount=float(loan.remaining_amount), status=loan.status,
            application_date=str(loan.application_date)[:19],
            approval_date=str(loan.approval_date)[:19] if loan.approval_date else None,
            next_emi_date=str(loan.next_emi_date)[:19] if loan.next_emi_date else None,
            purpose=loan.purpose, admin_notes=loan.admin_notes,
            progress_pct=0.0, remaining_emis=0, is_overdue=False,
        )
        for loan in loans
    ])


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/admin/transactions", response_model=ApiResponse[list[TransactionOut]])
def v2_admin_view_transactions(
    account: Optional[str] = Query(None, description="Filter by account number"),
    admin: dict = Depends(get_current_admin),
):
    """
    View all transactions across all accounts (admin only).

    Optionally filter by account number via the `account` query parameter.
    Transactions are returned newest first.
    """
    c = _get_container()
    tx_repo = c.transaction_repo()

    if account:
        domain_txns = tx_repo.get_by_account(account)
    else:
        # Get all transactions — iterate over all accounts
        # TODO: replace with a dedicated paginated query for production
        all_accounts = c.account_repo().get_all()
        domain_txns = []
        for acct in all_accounts:
            domain_txns.extend(tx_repo.get_by_account(acct.account_number))

    # Sort by timestamp descending
    domain_txns.sort(key=lambda t: t.timestamp, reverse=True)

    return _ok([
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
    ])


@router.get("/admin/accounts", response_model=ApiResponse[list[AccountListItem]])
def v2_admin_view_accounts(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    response: Response = None,
    admin: dict = Depends(get_current_admin),
):
    """
    View all registered accounts with pagination (admin only).

    Returns X-Total-Count header for pagination-aware UIs.
    """
    c = _get_container()
    domain_accounts, total = c.admin_service().list_accounts_paginated(
        page=page, per_page=per_page
    )
    response.headers["X-Total-Count"] = str(total)
    return _ok([
        AccountListItem(
            account_number=a.account_number, name=a.name,
            balance=float(a.balance),
            balance_formatted=_fmt_currency(float(a.balance)),
            status="frozen" if a.is_frozen else ("closed" if not a.is_active else "active"),
            mobile=a.mobile, email=a.email, age=a.age, gender=a.gender,
            created_at=str(a.created_at)[:19],
        )
        for a in domain_accounts
    ], meta={"page": page, "per_page": per_page, "total": total})


@router.get("/admin/accounts/search", response_model=ApiResponse[list[AccountListItem]])
def v2_admin_search_accounts(
    q: str = Query(..., min_length=1, description="Search by account number or name"),
    admin: dict = Depends(get_current_admin),
):
    """Search accounts by account number or name (admin only)."""
    c = _get_container()
    domain_accounts = c.admin_service().search_accounts(q)
    return _ok([
        AccountListItem(
            account_number=a.account_number, name=a.name,
            balance=float(a.balance),
            balance_formatted=_fmt_currency(float(a.balance)),
            status="frozen" if a.is_frozen else ("closed" if not a.is_active else "active"),
            mobile=a.mobile, email=a.email, age=a.age, gender=a.gender,
            created_at=str(a.created_at)[:19],
        )
        for a in domain_accounts
    ])


@router.post("/admin/accounts/{acc_no}/freeze", response_model=ApiResponse[MessageData])
def v2_admin_freeze_account(acc_no: str, admin: dict = Depends(get_current_admin)):
    """Freeze a customer account (admin only)."""
    c = _get_container()
    result = c.admin_service().freeze_account(acc_no=acc_no, actor="admin")
    if not result.success:
        if "not found" in result.message.lower():
            _err(result.message, status.HTTP_404_NOT_FOUND)
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/admin/accounts/{acc_no}/unfreeze", response_model=ApiResponse[MessageData])
def v2_admin_unfreeze_account(acc_no: str, admin: dict = Depends(get_current_admin)):
    """Unfreeze a customer account (admin only)."""
    c = _get_container()
    result = c.admin_service().unfreeze_account(acc_no=acc_no, actor="admin")
    if not result.success:
        if "not found" in result.message.lower():
            _err(result.message, status.HTTP_404_NOT_FOUND)
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.delete("/admin/accounts/{acc_no}", response_model=ApiResponse[MessageData])
def v2_admin_delete_account(acc_no: str, admin: dict = Depends(get_current_admin)):
    """Permanently delete a customer account and all its transactions (admin only)."""
    c = _get_container()
    result = c.admin_service().delete_account(acc_no=acc_no, actor="admin")
    if not result.success:
        _err(result.message, status.HTTP_404_NOT_FOUND)

    return _ok(MessageData(message=result.message))


@router.get("/admin/statistics", response_model=ApiResponse[StatisticsData])
def v2_admin_statistics(admin: dict = Depends(get_current_admin)):
    """View bank-wide statistics (admin only)."""
    c = _get_container()
    s = c.admin_service().get_statistics()

    return _ok(StatisticsData(
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
    ))


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/categories", response_model=ApiResponse[list[str]])
def v2_list_categories():
    """List all available transaction categories."""
    from unionbank.application.services import TRANSACTION_CATEGORIES
    return _ok(TRANSACTION_CATEGORIES)


# ═══════════════════════════════════════════════════════════════════════════════
#  Analyzr — Natural-Language Search
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/analyzr/query", response_model=ApiResponse[dict])
def v2_analyzr_query(req: AnalyzrQueryRequest):
    """
    Natural-language transaction search.

    Accepts plain English queries like:
      - "show me large deposits last month"
      - "what did I spend on food this month?"
      - "find suspicious transactions"
      - "show all deposits over 500"

    Translates the query into structured filters using pattern matching,
    executes the search, and returns formatted results.
    No external API calls — translation is deterministic and local.
    """
    from unionbank.utils.analyzr_core import execute_query as analyzr_search

    result = analyzr_search(
        query=req.query,
        account_number=req.account_number,
        max_results=req.max_results,
    )
    return _ok(result)


@router.get("/health", response_model=ApiResponse[HealthData])
def v2_health_check():
    """
    Health check endpoint.

    Checks:
    - Database connectivity (via `SELECT 1`)
    - Cache connectivity (via Redis ping, if configured)
    - Returns a 503 status if any dependency is down
    """
    from datetime import datetime, timezone

    db_status = "connected"
    cache_status = "connected"

    try:
        from unionbank.infrastructure.database import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    try:
        from unionbank.infrastructure.cache import get_cache
        cache = get_cache()
        cache.ping()
    except Exception:
        cache_status = "disconnected"

    overall = "healthy" if db_status == "connected" else "degraded"

    if overall == "degraded":
        from fastapi import status
        _err(
            f"Database: {db_status}, Cache: {cache_status}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return _ok(HealthData(
        status=overall,
        database=db_status,
        cache=cache_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    ))
