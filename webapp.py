"""
webapp.py  –  Flask web frontend for Union Bank Management System.

Run with:  python webapp.py
Then open http://localhost:5000 in your browser.
"""

import csv
import io
import os
import sys
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_file,
)
from flask_wtf.csrf import CSRFProtect

# PDF generation (fpdf2)
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ── Import existing business logic ───────────────────────────────────────────
from utils import (
    generate_account_number, now_str, fmt_currency,
    hash_password, verify_password, validate_email, validate_phone,
    validate_password, validate_name,
    check_login_locked, record_failed_login, reset_login_attempts,
    export_transactions_to_csv, generate_csv_filename,
    calculate_monthly_interest, TRANSACTION_CATEGORIES,
    load_json, save_json, load_goals, save_goals, generate_goal_id,
    ACCOUNTS_FILE, TRANSACTIONS_FILE, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES,
    mask_account_number, mask_sensitive_data,
)
from account import Account
from admin import Admin, ADMIN_FILE
from services import (
    process_deposit, process_withdraw, process_transfer,
    process_close_account, process_apply_interest,
    process_freeze_account, process_unfreeze_account,
    process_delete_account, get_bank_statistics,
    admin_authenticate,
)
from database import init_db

init_db()


# ── Font path for PDF generation ─────────────────────────────────────────
PDF_FONT_PATH = os.path.join(
    os.environ.get("SystemRoot", "C:\\Windows"),
    "Fonts", "arial.ttf",
)

# ── App setup ────────────────────────────────────────────────────────────────
from config import settings
app = Flask(__name__)
app.secret_key = settings.FLASK_SECRET_KEY

# ── CSRF Protection ───────────────────────────────────────────────────────────
csrf = CSRFProtect(app)

# Disable CSRF in testing mode so tests can POST without tokens
if settings.TESTING:
    app.config["WTF_CSRF_ENABLED"] = False


# ── Security Headers ──────────────────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    """Add security headers to every response."""
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), interest-cohort=()"
    )
    # Content-Security-Policy — no 'unsafe-inline'; Chart.js loaded from CDN
    nonce = get_request_nonce()
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'nonce-{nonce}'; "
        "style-src 'self' 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=' https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    return response


# ═══════════════════════════════════════════════════════════════════════════════
#  Rate Limiting (in-memory, per-endpoint, per-IP)
# ═══════════════════════════════════════════════════════════════════════════════

from collections import defaultdict
from functools import wraps
import time
import secrets
import re


# ── PII-safe logging helper — re-exported from utils/formatting.py ──────────
# mask_account_number() and mask_sensitive_data() are imported from utils above.


# ── CSP nonce generator ───────────────────────────────────────────────────
def _get_csp_nonce() -> str:
    """Generate a cryptographically random nonce for CSP."""
    return secrets.token_hex(16)


# ── Thread-local nonce storage for request-scoped nonces ──────────────────
import threading
_request_nonce = threading.local()


def set_request_nonce():
    """Set a CSP nonce for the current request."""
    _request_nonce.value = _get_csp_nonce()


def get_request_nonce() -> str:
    """Get the current request's CSP nonce."""
    return getattr(_request_nonce, "value", _get_csp_nonce())


# ── Generate CSP nonce before every request ────────────────────────────────
@app.before_request
def set_csp_nonce_for_request():
    """Set a fresh CSP nonce before each request is processed.
    Also pass it to templates via Flask's g object.
    """
    set_request_nonce()
    from flask import g
    g.csp_nonce = get_request_nonce()

_rate_limits: dict[str, list[float]] = defaultdict(list)


def rate_limit(limit: int, per_seconds: int = 60, key_prefix: str = ""):
    """
    Decorator: limit the number of POST requests to a route.

    Uses in-memory tracking keyed by ``endpoint:client_ip``.
    GET requests (form display) are NOT counted — only POST (form submission).

    Args:
        limit:       Maximum requests allowed within the window
        per_seconds: Duration of the sliding window in seconds
        key_prefix:  Optional prefix for the rate-limit key (e.g. "admin_")

    Usage:
        @app.route("/deposit", methods=["GET", "POST"])
        @rate_limit(limit=10, per_seconds=60)
        def deposit():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.method == "POST":
                # Disable in testing mode so tests don't get rate-limited
                if settings.TESTING:
                    return f(*args, **kwargs)

                key = f"{key_prefix}{request.endpoint}:{request.remote_addr or 'local'}"
                now = time.time()
                window_start = now - per_seconds

                # Prune expired entries (defaultdict handles missing keys)
                _rate_limits[key] = [
                    ts for ts in _rate_limits[key]
                    if ts > window_start
                ]

                # Enforce limit
                if len(_rate_limits[key]) >= limit:
                    flash(
                        f"Too many requests. Please wait {per_seconds // 60} minute(s) before trying again."
                        if per_seconds >= 60
                        else "Too many requests. Please slow down.",
                        "error",
                    )
                    return redirect(url_for(request.endpoint, **request.view_args or {}))

                _rate_limits[key].append(now)

            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── Helper functions ─────────────────────────────────────────────────────────

def login_required(f):
    """Decorator: require a logged-in customer."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if "account_number" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Decorator: require admin login."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


def get_account() -> Account | None:
    """Load the logged-in customer's Account object from SQLite (via container)."""
    acc_no = session.get("account_number")
    if not acc_no:
        return None

    from container import get_container
    domain_account = get_container().account_repo().get(acc_no)
    if not domain_account:
        session.pop("account_number", None)
        return None

    # Convert DomainAccount back to old Account format for backward compat
    data = {
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
    return Account(data)


# ── Public routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Landing page — show bank overview with live statistics."""
    if session.get("account_number"):
        return redirect(url_for("dashboard"))
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    # Gather live statistics via the container (no JSON reads)
    from container import get_container
    s = get_container().admin_service().get_statistics()

    stats = {
        "total_accounts": s["total_customers"],
        "total_txns": s["total_txns"],
        "total_balance": s["total_balance"],
        "active": s["active"],
    }

    return render_template("index.html", stats=stats, fmt_currency=fmt_currency)


# ── Customer auth ────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
@rate_limit(limit=10, per_seconds=60)
def login():
    """Customer login page."""
    if request.method == "POST":
        acc_no = request.form.get("account_number", "").strip()
        password = request.form.get("password", "")

        # Rate limiting check
        is_locked, remaining = check_login_locked(acc_no)
        if is_locked:
            flash(
                f"Account locked due to too many failed attempts. "
                f"Try again in {remaining} minute(s).",
                "error",
            )
            return render_template("login.html")

        accounts = load_json(ACCOUNTS_FILE)

        if acc_no not in accounts:
            flash("Account not found.", "error")
            return render_template("login.html")

        data = accounts[acc_no]

        if data.get("is_frozen", False):
            flash("Your account has been frozen. Please contact the bank.", "error")
            return render_template("login.html")

        if not data.get("is_active", True):
            flash("This account has been closed.", "error")
            return render_template("login.html")

        if not verify_password(password, data["password"]):
            remaining_attempts = record_failed_login(acc_no)
            if remaining_attempts > 0:
                flash(
                    f"Incorrect password. {remaining_attempts} attempt(s) "
                    f"remaining before lockout.",
                    "error",
                )
            else:
                flash(
                    f"Incorrect password. Account locked for "
                    f"{LOGIN_LOCKOUT_MINUTES} minutes.",
                    "error",
                )
            return render_template("login.html")

        # Success
        reset_login_attempts(acc_no)
        session["account_number"] = acc_no
        session.permanent = True
        flash(f"Welcome back, {data['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
@rate_limit(limit=5, per_seconds=60)
def register():
    """New account registration."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age_str = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        mobile = request.form.get("mobile", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # Validate
        if not validate_name(name):
            flash("Name must be 2-50 characters (letters and spaces only).", "error")
            return render_template("register.html", form=request.form)

        try:
            age = int(age_str)
            if age < 18 or age > 120:
                flash("Age must be between 18 and 120.", "error")
                return render_template("register.html", form=request.form)
        except ValueError:
            flash("Invalid age.", "error")
            return render_template("register.html", form=request.form)

        if not validate_phone(mobile):
            flash("Invalid mobile number. Must be 10 digits starting with 6-9.", "error")
            return render_template("register.html", form=request.form)

        if not validate_email(email):
            flash("Invalid email format.", "error")
            return render_template("register.html", form=request.form)

        valid_pwd, pwd_msg = validate_password(password)
        if not valid_pwd:
            flash(pwd_msg, "error")
            return render_template("register.html", form=request.form)

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html", form=request.form)

        # Create account
        acc_no = generate_account_number()
        data = {
            "account_number": acc_no,
            "name": name,
            "age": age,
            "gender": gender,
            "mobile": mobile,
            "email": email,
            "password": hash_password(password),
            "balance": 0.0,
            "is_active": True,
            "is_frozen": False,
            "created_at": now_str(),
        }
        account = Account(data)
        account.save()

        flash(
            f"Registration successful! Your account number is {acc_no}.",
            "success",
        )
        return redirect(url_for("login"))

    return render_template("register.html")


# ── Customer dashboard ───────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    """Customer dashboard — account overview with charts."""
    acc = get_account()
    if not acc:
        flash("Account not found. Please log in again.", "error")
        return redirect(url_for("login"))

    # Load transactions for charts
    from container import get_container
    c = get_container()
    domain_txns = c.transaction_repo().get_by_account(acc.account_number)
    records = [{
        "txn_id": t.txn_id,
        "timestamp": str(t.timestamp)[:19],
        "type": t.type.value,
        "amount": float(t.amount),
        "balance": float(t.balance),
        "description": t.description,
        "category": t.category,
        "target_account": t.target_account,
    } for t in domain_txns]

    # Category breakdown pie chart
    category_counts = {}
    category_amounts = {}
    for t in records:
        cat = t.get("category", "General")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        category_amounts[cat] = category_amounts.get(cat, 0) + abs(t["amount"])

    # Balance trend line chart (sample points for large datasets)
    balance_dates = []
    balance_values = []
    max_points = 50
    step = max(1, len(records) // max_points)
    sampled = records[::step]
    if len(records) > 0 and sampled[-1] != records[-1]:
        sampled.append(records[-1])
    for t in sampled:
        balance_dates.append(t.get("timestamp", "")[:10])
        balance_values.append(t["balance"])

    # Transaction type breakdown
    type_counts = {"DEPOSIT": 0, "WITHDRAW": 0, "TRANSFER_OUT": 0, "TRANSFER_IN": 0, "INTEREST": 0}
    for t in records:
        txn_type = t["type"]
        if txn_type in type_counts:
            type_counts[txn_type] += 1

    chart_data = {
        "category_labels": list(category_counts.keys()),
        "category_counts": list(category_counts.values()),
        "category_amounts": [round(v, 2) for v in category_amounts.values()],
        "balance_dates": balance_dates,
        "balance_values": balance_values,
        "type_labels": list(type_counts.keys()),
        "type_counts": list(type_counts.values()),
    }

    return render_template(
        "dashboard.html",
        acc=acc,
        fmt_currency=fmt_currency,
        chart_data=chart_data,
        total_txns=len(records),
    )


@app.route("/deposit", methods=["GET", "POST"])
@login_required
@rate_limit(limit=10, per_seconds=60)
def deposit():
    """Deposit money."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", "0"))
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Invalid amount. Please enter a positive number.", "error")
            return render_template("deposit.html", acc=acc)

        category = request.form.get("category", "General")
        result = process_deposit(acc.account_number, amount, category)
        if result.success:
            acc.balance = result.data["balance"]
            flash(result.message, "success")
        else:
            flash(result.message, "error")
        return redirect(url_for("dashboard"))

    return render_template(
        "deposit.html",
        acc=acc,
        categories=TRANSACTION_CATEGORIES,
    )


@app.route("/withdraw", methods=["GET", "POST"])
@login_required
@rate_limit(limit=10, per_seconds=60)
def withdraw():
    """Withdraw money."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", "0"))
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Invalid amount. Please enter a positive number.", "error")
            return render_template("withdraw.html", acc=acc)

        if amount > acc.balance:
            flash("Insufficient balance!", "error")
            return render_template("withdraw.html", acc=acc)

        category = request.form.get("category", "General")
        result = process_withdraw(acc.account_number, amount, category)
        if result.success:
            acc.balance = result.data["balance"]
            flash(result.message, "success")
        else:
            flash(result.message, "error")
        return redirect(url_for("dashboard"))

    return render_template(
        "withdraw.html",
        acc=acc,
        categories=TRANSACTION_CATEGORIES,
    )


@app.route("/transfer", methods=["GET", "POST"])
@login_required
@rate_limit(limit=10, per_seconds=60)
def transfer():
    """Transfer funds to another account."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    recipient = None
    if request.method == "POST":
        target_acc_no = request.form.get("target_account", "").strip()
        try:
            amount = float(request.form.get("amount", "0"))
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Invalid amount. Please enter a positive number.", "error")
            return render_template("transfer.html", acc=acc, recipient=None)

        category = request.form.get("category", "General")

        accounts = load_json(ACCOUNTS_FILE)

        if target_acc_no not in accounts:
            flash("Recipient account not found.", "error")
            return render_template("transfer.html", acc=acc, recipient=None)

        if target_acc_no == acc.account_number:
            flash("Cannot transfer to your own account.", "error")
            return render_template("transfer.html", acc=acc, recipient=None)

        target_data = accounts[target_acc_no]
        if target_data.get("is_frozen"):
            flash("Recipient account is frozen.", "error")
            return render_template("transfer.html", acc=acc, recipient=None)
        if not target_data.get("is_active", True):
            flash("Recipient account is closed.", "error")
            return render_template("transfer.html", acc=acc, recipient=None)

        if amount > acc.balance:
            flash("Insufficient balance!", "error")
            return render_template("transfer.html", acc=acc, recipient=None)

        # Check if confirmation step
        if "confirm" not in request.form:
            # Show confirmation
            recipient = target_data
            return render_template(
                "transfer.html",
                acc=acc,
                recipient=recipient,
                amount=amount,
                category=category,
                target_acc_no=target_acc_no,
            )

        # ═══════════════════════════════════════════════════════════════
        #  ATOMIC TRANSFER — via service layer
        # ═══════════════════════════════════════════════════════════════
        result = process_transfer(
            sender_acc_no=acc.account_number,
            receiver_acc_no=target_acc_no,
            amount=amount,
            category=category,
        )

        if result.success:
            acc.balance = result.sender_balance
            flash(
                f"{fmt_currency(amount)} transferred to {target_data['name']} "
                f"({target_acc_no}) successfully!",
                "success",
            )
        else:
            flash(result.error_message, "error")
            return render_template("transfer.html", acc=acc, recipient=None)

        return redirect(url_for("dashboard"))

    return render_template("transfer.html", acc=acc, recipient=None)


@app.route("/statement")
@login_required
def statement():
    """Full transaction statement with chart data."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    from container import get_container
    c = get_container()
    domain_txns = c.transaction_repo().get_by_account(acc.account_number)
    records = [{
        "txn_id": t.txn_id,
        "timestamp": str(t.timestamp)[:19],
        "type": t.type.value,
        "amount": float(t.amount),
        "balance": float(t.balance),
        "description": t.description,
        "category": t.category,
        "target_account": t.target_account,
    } for t in domain_txns]

    # Compute credit/debit stats
    total_credits = sum(t["amount"] for t in records
                        if t["type"] in ("DEPOSIT", "TRANSFER_IN", "INTEREST"))
    total_debits = sum(t["amount"] for t in records
                       if t["type"] in ("WITHDRAW", "TRANSFER_OUT"))
    credit_count = sum(1 for t in records
                       if t["type"] in ("DEPOSIT", "TRANSFER_IN", "INTEREST"))

    # Sample balance data for chart (max 50 points)
    max_points = 50
    step = max(1, len(records) // max_points)
    sampled_records = records[::step]
    if records and sampled_records[-1] != records[-1]:
        sampled_records.append(records[-1])

    return render_template(
        "statement.html",
        acc=acc,
        records=records,
        fmt_currency=fmt_currency,
        total_credits=round(total_credits, 2),
        total_debits=round(total_debits, 2),
        credit_count=credit_count,
        sampled_records=sampled_records,
    )


@app.route("/export-csv")
@login_required
def export_csv():
    """Download transaction history as CSV."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    from container import get_container
    c = get_container()
    domain_txns = c.transaction_repo().get_by_account(acc.account_number)
    records = [{
        "txn_id": t.txn_id,
        "timestamp": str(t.timestamp)[:19],
        "type": t.type.value,
        "amount": float(t.amount),
        "balance": float(t.balance),
        "description": t.description,
        "category": t.category,
        "target_account": t.target_account,
    } for t in domain_txns]

    if not records:
        flash("No transactions to export.", "warning")
        return redirect(url_for("statement"))

    # Generate CSV in memory
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
    filename = f"statement_{acc.account_number}.csv"
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/apply-interest", methods=["GET", "POST"])
@login_required
@rate_limit(limit=5, per_seconds=60)
def apply_interest():
    """Apply monthly interest."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    # GET request -> show confirmation
    if request.method == "GET":
        interest = calculate_monthly_interest(acc.balance)
        if interest <= 0:
            flash("No interest to apply (balance is zero or negative).", "info")
            return redirect(url_for("dashboard"))
        return render_template(
            "apply_interest.html",
            acc=acc,
            interest=interest,
            fmt_currency=fmt_currency,
        )

    # POST request -> apply interest (atomic)
    result = process_apply_interest(acc.account_number, acc.balance)
    if result.success:
        acc.balance = result.data["balance"]
        flash(result.message, "success")
    else:
        flash(result.message, "info" if "No interest" in result.message else "error")
    return redirect(url_for("dashboard"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
@rate_limit(limit=10, per_seconds=60)
def profile():
    """View and update profile."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age_str = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        mobile = request.form.get("mobile", "").strip()
        email = request.form.get("email", "").strip()

        if name:
            if not validate_name(name):
                flash("Invalid name. Must be 2-50 characters (letters and spaces only).", "error")
                return redirect(url_for("profile"))
            acc.name = name

        if age_str:
            try:
                age = int(age_str)
                acc.age = age
            except ValueError:
                flash("Invalid age - keeping current.", "warning")

        if gender:
            acc.gender = gender

        if mobile:
            if not validate_phone(mobile):
                flash("Invalid mobile number. Must be 10 digits starting with 6-9.", "error")
                return redirect(url_for("profile"))
            acc.mobile = mobile

        if email:
            if not validate_email(email):
                flash("Invalid email format.", "error")
                return redirect(url_for("profile"))
            acc.email = email

        acc.save()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", acc=acc)


@app.route("/change-password", methods=["GET", "POST"])
@login_required
@rate_limit(limit=5, per_seconds=60)
def change_password():
    """Change account password."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    if request.method == "POST":
        old_pwd = request.form.get("current_password", "")
        new_pwd = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not verify_password(old_pwd, acc.password):
            flash("Incorrect current password.", "error")
            return render_template("change_password.html")

        valid_pwd, pwd_msg = validate_password(new_pwd)
        if not valid_pwd:
            flash(pwd_msg, "error")
            return render_template("change_password.html")

        if new_pwd != confirm:
            flash("Passwords do not match.", "error")
            return render_template("change_password.html")

        acc.password = hash_password(new_pwd)
        acc.save()
        flash("Password changed successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("change_password.html")


# ── Savings Goals ────────────────────────────────────────────────────────

@app.route("/savings")
@login_required
def savings_goals():
    """View and manage savings goals."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    goals = load_goals(acc.account_number)
    total_saved = sum(g["current_amount"] for g in goals)
    total_target = sum(g["target_amount"] for g in goals)
    completed = sum(1 for g in goals if g.get("is_completed"))

    return render_template(
        "savings_goals.html",
        acc=acc,
        goals=goals,
        fmt_currency=fmt_currency,
        total_saved=total_saved,
        total_target=total_target,
        completed=completed,
    )


@app.route("/savings/new", methods=["GET", "POST"])
@login_required
@rate_limit(limit=10, per_seconds=60)
def savings_goal_new():
    """Create a new savings goal."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        target_str = request.form.get("target_amount", "0")
        date_str = request.form.get("target_date", "")

        if not name or len(name) < 2:
            flash("Goal name must be at least 2 characters.", "error")
            return render_template("savings_goal_form.html", acc=acc)

        try:
            target_amount = float(target_str)
            if target_amount <= 0:
                raise ValueError
        except ValueError:
            flash("Invalid target amount. Please enter a positive number.", "error")
            return render_template("savings_goal_form.html", acc=acc)

        goals = load_goals(acc.account_number)
        goal = {
            "goal_id": generate_goal_id(),
            "name": name,
            "target_amount": round(target_amount, 2),
            "current_amount": 0.0,
            "target_date": date_str,
            "created_at": now_str(),
            "is_completed": False,
        }
        goals.append(goal)
        save_goals(acc.account_number, goals)

        flash(f"Savings goal '{name}' created!", "success")
        return redirect(url_for("savings_goals"))

    return render_template("savings_goal_form.html", acc=acc, goal=None)


@app.route("/savings/<goal_id>/edit", methods=["GET", "POST"])
@login_required
@rate_limit(limit=10, per_seconds=60)
def savings_goal_edit(goal_id):
    """Edit a savings goal."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    goals = load_goals(acc.account_number)
    goal = next((g for g in goals if g["goal_id"] == goal_id), None)
    if not goal:
        flash("Goal not found.", "error")
        return redirect(url_for("savings_goals"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        target_str = request.form.get("target_amount", "0")
        date_str = request.form.get("target_date", "")

        if not name or len(name) < 2:
            flash("Goal name must be at least 2 characters.", "error")
            return render_template("savings_goal_form.html", acc=acc, goal=goal)

        try:
            target_amount = float(target_str)
            if target_amount <= 0:
                raise ValueError
        except ValueError:
            flash("Invalid target amount.", "error")
            return render_template("savings_goal_form.html", acc=acc, goal=goal)

        goal["name"] = name
        goal["target_amount"] = round(target_amount, 2)
        goal["target_date"] = date_str
        goal["is_completed"] = goal["current_amount"] >= goal["target_amount"]
        save_goals(acc.account_number, goals)

        flash(f"Goal '{name}' updated!", "success")
        return redirect(url_for("savings_goals"))

    return render_template("savings_goal_form.html", acc=acc, goal=goal)


@app.route("/savings/<goal_id>/contribute", methods=["POST"])
@login_required
@rate_limit(limit=10, per_seconds=60)
def savings_goal_contribute(goal_id):
    """Contribute to a savings goal."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    goals = load_goals(acc.account_number)
    goal = next((g for g in goals if g["goal_id"] == goal_id), None)
    if not goal:
        flash("Goal not found.", "error")
        return redirect(url_for("savings_goals"))

    try:
        amount = float(request.form.get("amount", "0"))
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Invalid amount. Please enter a positive number.", "error")
        return redirect(url_for("savings_goals"))

    if amount > acc.balance:
        flash("Insufficient balance!", "error")
        return redirect(url_for("savings_goals"))

    # Transfer from account balance to goal
    acc.balance -= amount
    acc.save()
    acc.log_transaction("TRANSFER_OUT", amount,
                         f"Savings goal: {goal['name']}",
                         category="Savings")

    goal["current_amount"] += amount
    if goal["current_amount"] >= goal["target_amount"]:
        goal["is_completed"] = True
        flash(f"🎉 Congratulations! You achieved your savings goal '{goal['name']}'!", "success")
    else:
        flash(f"{fmt_currency(amount)} contributed to '{goal['name']}'!", "success")

    save_goals(acc.account_number, goals)
    return redirect(url_for("savings_goals"))


@app.route("/savings/<goal_id>/delete", methods=["POST"])
@login_required
@rate_limit(limit=5, per_seconds=60, key_prefix="sensitive_")
def savings_goal_delete(goal_id):
    """Delete a savings goal."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    goals = load_goals(acc.account_number)
    goal = next((g for g in goals if g["goal_id"] == goal_id), None)
    if not goal:
        flash("Goal not found.", "error")
        return redirect(url_for("savings_goals"))

    # Refund current amount back to balance
    if goal["current_amount"] > 0:
        acc.balance += goal["current_amount"]
        acc.save()
        acc.log_transaction("DEPOSIT", goal["current_amount"],
                             f"Refund from deleted goal: {goal['name']}",
                             category="Savings")

    goals.remove(goal)
    save_goals(acc.account_number, goals)
    flash(f"Goal '{goal['name']}' deleted. Amount refunded.", "info")
    return redirect(url_for("savings_goals"))


@app.route("/close-account", methods=["POST"])
@login_required
@rate_limit(limit=3, per_seconds=60, key_prefix="sensitive_")
def close_account():
    """Close the account (POST only)."""
    acc = get_account()
    if not acc:
        return redirect(url_for("login"))

    confirm_text = request.form.get("confirm_text", "")
    password = request.form.get("password", "")

    if confirm_text != "CLOSE":
        flash("Please type 'CLOSE' to confirm.", "error")
        return redirect(url_for("profile"))

    if not verify_password(password, acc.password):
        flash("Incorrect password.", "error")
        return redirect(url_for("profile"))

    # Atomic closure via service layer
    result = process_close_account(acc.account_number, password, acc.password)
    if result.success:
        acc.is_active = False
        session.pop("account_number", None)
        flash(result.message, "info")
    else:
        flash(result.message, "error")
    return redirect(url_for("index"))


# ── Admin routes ─────────────────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
@rate_limit(limit=10, per_seconds=60, key_prefix="admin_")
def admin_login():
    """Admin login page."""
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        lock_key = f"admin_{username}"
        is_locked, remaining = check_login_locked(lock_key)
        if is_locked:
            flash(
                f"Admin account locked due to too many failed attempts. "
                f"Try again in {remaining} minute(s).",
                "error",
            )
            return render_template("admin_login.html")

        result = admin_authenticate(username, password)
        if result.success:
            reset_login_attempts(lock_key)
            session["is_admin"] = True
            session.permanent = True
            flash("Admin login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            remaining_attempts = record_failed_login(lock_key)
            if remaining_attempts > 0:
                flash(
                    f"Invalid admin credentials. {remaining_attempts} "
                    f"attempt(s) remaining before lockout.",
                    "error",
                )
            else:
                flash(
                    f"Invalid admin credentials. Admin account locked for "
                    f"{LOGIN_LOCKOUT_MINUTES} minutes.",
                    "error",
                )
            return render_template("admin_login.html")

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Admin dashboard."""
    return render_template("admin_dashboard.html")


@app.route("/admin/accounts")
@admin_required
def admin_accounts():
    """View all accounts (from SQLite via container)."""
    from container import get_container
    domain_accounts = get_container().admin_service().list_accounts()
    accounts = {a.account_number: {
        "account_number": a.account_number,
        "name": a.name,
        "age": a.age,
        "balance": float(a.balance),
        "is_active": a.is_active,
        "is_frozen": a.is_frozen,
        "mobile": a.mobile,
        "email": a.email,
        "created_at": str(a.created_at)[:19],
    } for a in domain_accounts}
    return render_template("admin_accounts.html", accounts=accounts, fmt_currency=fmt_currency)


@app.route("/admin/accounts/<acc_no>")
@admin_required
def admin_account_detail(acc_no):
    """View detailed information for a specific customer account (from SQLite)."""
    from container import get_container
    c = get_container()

    domain_account = c.account_repo().get(acc_no)
    if not domain_account:
        flash("Account not found.", "error")
        return redirect(url_for("admin_accounts"))

    data = {
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

    domain_txns = c.transaction_repo().get_by_account(acc_no)
    records = [{
        "txn_id": t.txn_id,
        "timestamp": str(t.timestamp)[:19],
        "type": t.type.value,
        "amount": float(t.amount),
        "balance": float(t.balance),
        "description": t.description,
        "category": t.category,
        "target_account": t.target_account,
    } for t in reversed(domain_txns)]

    # ── Profile ─────────────────────────────────────
    status = "frozen" if domain_account.is_frozen else ("closed" if not domain_account.is_active else "active")

    # ── Financial summary ────────────────────────────
    total_credits = sum(t["amount"] for t in records
                        if t["type"] in ("DEPOSIT", "TRANSFER_IN", "INTEREST"))
    total_debits = sum(t["amount"] for t in records
                       if t["type"] in ("WITHDRAW", "TRANSFER_OUT"))
    deposit_count = sum(1 for t in records if t["type"] == "DEPOSIT")
    withdraw_count = sum(1 for t in records if t["type"] == "WITHDRAW")
    transfer_out_count = sum(1 for t in records if t["type"] == "TRANSFER_OUT")
    transfer_in_count = sum(1 for t in records if t["type"] == "TRANSFER_IN")

    # ── Category breakdown ───────────────────────────
    category_amounts = {}
    for t in records:
        cat = t.get("category", "General")
        category_amounts[cat] = category_amounts.get(cat, 0) + abs(t["amount"])
    sorted_cats = sorted(category_amounts.items(), key=lambda x: x[1], reverse=True)

    # ── Balance trend (sampled) ─────────────────────
    max_points = 50
    step = max(1, len(records) // max_points)
    sampled_records = records[::step]
    if records and sampled_records[-1] != records[-1]:
        sampled_records.append(records[-1])

    # ── Recent transactions (last 15) ────────────────
    recent = records[-15:]

    summary = {
        "total_credits": round(total_credits, 2),
        "total_debits": round(total_debits, 2),
        "deposit_count": deposit_count,
        "withdraw_count": withdraw_count,
        "transfer_out_count": transfer_out_count,
        "transfer_in_count": transfer_in_count,
        "total_txns": len(records),
    }

    chart_data = {
        "category_labels": [c[0] for c in sorted_cats[:8]],
        "category_amounts": [round(c[1], 2) for c in sorted_cats[:8]],
        "balance_dates": [t.get("timestamp", "")[:10] for t in sampled_records],
        "balance_values": [t["balance"] for t in sampled_records],
    }

    return render_template(
        "admin_account_detail.html",
        acc=data,
        acc_no=acc_no,
        status=status,
        fmt_currency=fmt_currency,
        summary=summary,
        chart_data=chart_data,
        recent=reversed(recent),
    )


@app.route("/admin/search", methods=["GET", "POST"])
@admin_required
def admin_search():
    """Search accounts (from SQLite via container)."""
    results = []
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip().lower()
        from container import get_container
        domain_accounts = get_container().admin_service().search_accounts(query)
        results = [{
            "account_number": a.account_number,
            "name": a.name,
            "age": a.age,
            "gender": a.gender,
            "mobile": a.mobile,
            "email": a.email,
            "balance": float(a.balance),
            "is_active": a.is_active,
            "is_frozen": a.is_frozen,
            "created_at": str(a.created_at)[:19],
        } for a in domain_accounts]
    return render_template("admin_search.html", results=results, query=query, fmt_currency=fmt_currency)


@app.route("/admin/freeze", methods=["GET", "POST"])
@admin_required
@rate_limit(limit=10, per_seconds=60, key_prefix="admin_")
def admin_freeze():
    """Freeze / unfreeze an account (from SQLite via container)."""
    result = None
    if request.method == "POST":
        acc_no = request.form.get("account_number", "").strip()

        from container import get_container
        c = get_container()
        domain_account = c.account_repo().get(acc_no)

        if not domain_account:
            flash("Account not found.", "error")
            return redirect(url_for("admin_freeze"))

        if not domain_account.is_active and not domain_account.is_frozen:
            flash("Account is permanently closed – cannot modify.", "error")
            return render_template("admin_freeze.html", result=None)

        currently_frozen = domain_account.is_frozen
        action = "unfreeze" if currently_frozen else "freeze"

        acc_dict = {
            "account_number": domain_account.account_number,
            "name": domain_account.name,
            "is_active": domain_account.is_active,
            "is_frozen": domain_account.is_frozen,
            "balance": float(domain_account.balance),
        }

        confirm = request.form.get("confirm", "")
        if confirm != "yes":
            return render_template(
                "admin_freeze.html",
                result=None,
                preview_acc=acc_dict,
                acc_no=acc_no,
                action=action,
            )

        if currently_frozen:
            result = process_unfreeze_account(acc_no)
        else:
            result = process_freeze_account(acc_no)

        flash(result.message, "success" if result.success else "error")
        if result.success:
            return render_template("admin_freeze.html", result=result.message)
        return redirect(url_for("admin_freeze"))

    return render_template("admin_freeze.html", result=None)


@app.route("/admin/delete", methods=["GET", "POST"])
@admin_required
@rate_limit(limit=5, per_seconds=60, key_prefix="admin_sensitive_")
def admin_delete():
    """Delete an account (from SQLite via container)."""
    if request.method == "POST":
        acc_no = request.form.get("account_number", "").strip()

        from container import get_container
        c = get_container()
        domain_account = c.account_repo().get(acc_no)

        if not domain_account:
            flash("Account not found.", "error")
            return redirect(url_for("admin_delete"))

        confirm_text = request.form.get("confirm_text", "")

        if confirm_text != "DELETE":
            acc_dict = {
                "account_number": domain_account.account_number,
                "name": domain_account.name,
                "balance": float(domain_account.balance),
            }
            flash("Please type 'DELETE' to confirm.", "error")
            return render_template("admin_delete.html", preview_acc=acc_dict, acc_no=acc_no)

        result = process_delete_account(acc_no)
        flash(result.message, "success" if result.success else "error")
        return redirect(url_for("admin_delete"))

    return render_template("admin_delete.html", preview_acc=None)


@app.route("/admin/statistics")
@admin_required
def admin_statistics():
    """Bank statistics dashboard with charts."""
    s = get_bank_statistics()

    stats = {
        "total_customers": s["total_customers"],
        "active": s["active"],
        "frozen": s["frozen"],
        "closed": s["closed"],
        "total_balance": s["total_balance"],
        "total_dep": s["total_dep"],
        "total_with": s["total_with"],
        "total_trans": s["total_trans"],
        "total_txns": s["total_txns"],
    }

    cats = s["sorted_categories"]
    chart_data = {
        "status_labels": ["Active", "Frozen", "Closed"],
        "status_counts": [s["active"], s["frozen"], s["closed"]],
        "status_colors": ["#2e7d32", "#c62828", "#f57f17"],
        "financial_labels": ["Deposits", "Withdrawals", "Transfers"],
        "financial_values": [round(s["total_dep"], 2), round(s["total_with"], 2), round(s["total_trans"], 2)],
        "financial_colors": ["#4caf50", "#e53935", "#1976d2"],
        "category_labels": [c["name"] for c in cats],
        "category_amounts": [round(c["total"], 2) for c in cats],
    }

    return render_template(
        "admin_statistics.html",
        stats=stats,
        fmt_currency=fmt_currency,
        chart_data=chart_data,
    )


@app.route("/admin/transactions", methods=["GET", "POST"])
@admin_required
def admin_transactions():
    """View all transactions, optionally filtered by account (from SQLite)."""
    from container import get_container
    c = get_container()
    acc_filter = ""
    if request.method == "POST":
        acc_filter = request.form.get("account_number", "").strip()

    if acc_filter:
        domain_txns = c.transaction_repo().get_by_account(acc_filter)
    else:
        domain_txns = c.transaction_repo().get_all()

    # Group by account number for template compatibility
    txns = {}
    for t in domain_txns:
        acc_no = t.account_number
        if acc_no not in txns:
            txns[acc_no] = []
        txns[acc_no].append({
            "txn_id": t.txn_id,
            "timestamp": str(t.timestamp)[:19],
            "type": t.type.value,
            "amount": float(t.amount),
            "balance": float(t.balance),
            "description": t.description,
            "category": t.category,
            "target_account": t.target_account,
        })

    return render_template(
        "admin_transactions.html",
        txns=txns,
        acc_filter=acc_filter,
        fmt_currency=fmt_currency,
    )


@app.route("/admin/change-password", methods=["GET", "POST"])
@admin_required
@rate_limit(limit=5, per_seconds=60, key_prefix="admin_sensitive_")
def admin_change_password():
    """Change admin password (via SQLite)."""
    if request.method == "POST":
        old_pwd = request.form.get("current_password", "")
        new_pwd = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        from container import get_container
        c = get_container()
        admin = c.admin_repo().get_by_username("simon")
        if not admin or not verify_password(old_pwd, admin.password):
            flash("Incorrect current password.", "error")
            return render_template("admin_change_password.html")

        valid_pwd, pwd_msg = validate_password(new_pwd)
        if not valid_pwd:
            flash(pwd_msg, "error")
            return render_template("admin_change_password.html")

        if new_pwd != confirm:
            flash("Passwords do not match.", "error")
            return render_template("admin_change_password.html")

        c.admin_repo().update_password("simon", hash_password(new_pwd))
        c.admin_repo().commit()
        flash("Admin password changed successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_change_password.html")


# ═══════════════════════════════════════════════════════════════════════════════
#  PDF Report Generation
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_admin_pdf(stats: dict, chart_data: dict) -> io.BytesIO:
    """
    Generate a bank statistics report as a PDF in-memory.
    Uses fpdf2 with Arial Unicode font.
    Returns a BytesIO stream ready to be sent to the client.
    """
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("Arial", "", PDF_FONT_PATH, uni=True)
    # Bold font (fall back to regular if bold variant not available)
    bold_path = PDF_FONT_PATH.replace(".ttf", "bd.ttf")
    if os.path.exists(bold_path):
        pdf.add_font("Arial", "B", bold_path, uni=True)
    else:
        pdf.add_font("Arial", "B", PDF_FONT_PATH, uni=True)

    page_w = 210  # A4 width in mm
    margin = 20
    content_w = page_w - 2 * margin

    # ── Helper: format large numbers to crores ──────────────────────────
    def fmt_cr(val):
        """Format a value in Crores."""
        cr = val / 1e7
        return f"₹{cr:,.2f} Cr"

    def fmt_inr(val):
        """Format a value in Indian number format."""
        return f"₹{val:,.2f}"

    # ── Helper: draw a simple horizontal bar ────────────────────────────
    def draw_hbar(x, y, w, h, label, value, max_val, color, fmt_fn=str):
        """Draw a horizontal bar chart segment."""
        pdf.set_fill_color(*color)
        bar_w = (value / max_val) * w if max_val > 0 else 0
        pdf.rect(x, y, max(bar_w, 2), h, style="F")
        pdf.set_font("Arial", "", 9)
        pdf.set_xy(x + max(bar_w, 2) + 2, y + 0.5)
        pdf.cell(60, h, f"{label}: {fmt_fn(value)}")

    def draw_vbar(x, y, w, h, value, max_val, color, label, fmt_fn=str):
        """Draw a vertical bar chart segment."""
        pdf.set_fill_color(*color)
        bar_h = (value / max_val) * h if max_val > 0 else 0
        pdf.rect(x, y + h - bar_h, w, bar_h, style="F")
        # Label below
        pdf.set_font("Arial", "", 8)
        pdf.set_xy(x - 2, y + h + 1)
        pdf.cell(w + 4, 5, label, align="C")
        # Value above
        pdf.set_font("Arial", "B", 7)
        val_str = fmt_fn(value)
        pdf.set_xy(x - 2, y + h - bar_h - 4)
        pdf.cell(w + 4, 4, val_str, align="C")

    # ═══════════════════════════════════════════════════════════════════
    #  PAGE 1 — Title Page
    # ═══════════════════════════════════════════════════════════════════
    pdf.add_page()

    # Top accent bar
    pdf.set_fill_color(26, 35, 126)
    pdf.rect(0, 0, page_w, 8, style="F")

    # Bank name
    pdf.set_y(30)
    pdf.set_font("Arial", "B", 28)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 14, "UNION BANK", align="C", new_x="LMARGIN", new_y="NEXT")

    # Subtitle
    pdf.set_font("Arial", "", 16)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Statistical Report", align="C", new_x="LMARGIN", new_y="NEXT")

    # Decorative line
    pdf.set_draw_color(26, 35, 126)
    pdf.set_line_width(0.5)
    y_line = pdf.get_y() + 5
    pdf.line(margin + 50, y_line, page_w - margin - 50, y_line)

    # Date info
    pdf.set_y(y_line + 15)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(80, 80, 80)
    now = datetime.now().strftime("%d %B %Y at %H:%M")
    pdf.cell(0, 8, f"Generated on: {now}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "Confidential — For authorized personnel only", align="C", new_x="LMARGIN", new_y="NEXT")

    # Key metrics boxes
    pdf.set_y(y_line + 40)
    box_w = (content_w - 12) / 3
    metrics = [
        ("Total Customers", stats["total_customers"], (26, 35, 126)),
        ("Active Accounts", stats["active"], (46, 125, 50)),
        ("Total Balance", fmt_inr(stats["total_balance"]), (255, 152, 0)),
    ]
    for i, (label, value, color) in enumerate(metrics):
        x = margin + i * (box_w + 6)
        pdf.set_fill_color(*color)
        pdf.rect(x, pdf.get_y(), box_w, 28, style="F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "", 8)
        pdf.set_xy(x, pdf.get_y() + 3)
        pdf.cell(box_w, 6, label, align="C")
        pdf.set_font("Arial", "B", 14)
        pdf.set_xy(x, pdf.get_y() + 9)
        pdf.cell(box_w, 10, str(value), align="C")

    # ═══════════════════════════════════════════════════════════════════
    #  PAGE 2 — Account Statistics
    # ═══════════════════════════════════════════════════════════════════
    pdf.add_page()

    # Section header
    pdf.set_fill_color(26, 35, 126)
    pdf.rect(0, 0, page_w, 7, style="F")
    pdf.set_y(12)
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 10, "1. Customer Account Statistics", new_x="LMARGIN", new_y="NEXT")

    # Table
    pdf.set_y(pdf.get_y() + 4)
    col_w = [60, 30, 30, 50]
    headers = ["Category", "Count", "Percentage", "Status"]
    rows = [
        ("Total Customers", stats["total_customers"], 100.0, "All registered accounts"),
        ("Active Accounts", stats["active"],
         round(stats["active"] / max(stats["total_customers"], 1) * 100, 1),
         "Active & unfrozen"),
        ("Frozen Accounts", stats["frozen"],
         round(stats["frozen"] / max(stats["total_customers"], 1) * 100, 1),
         "Temporarily frozen"),
        ("Closed Accounts", stats["closed"],
         round(stats["closed"] / max(stats["total_customers"], 1) * 100, 1),
         "Permanently closed"),
    ]

    # Table header
    pdf.set_fill_color(26, 35, 126)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    x = margin
    for i, (h, w) in enumerate(zip(headers, col_w)):
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(w, 8, f"  {h}", fill=True)
        x += w
    pdf.set_y(pdf.get_y() + 8)

    # Table rows
    pdf.set_text_color(50, 50, 50)
    for i, (label, count, pct, status) in enumerate(rows):
        pdf.set_font("Arial", "B" if i == 0 else "", 9)
        if i % 2 == 0:
            pdf.set_fill_color(240, 243, 255)
        else:
            pdf.set_fill_color(255, 255, 255)
        x = margin
        vals = [str(label), str(count), f"{pct}%", status]
        for v, w in zip(vals, col_w):
            pdf.set_xy(x, pdf.get_y())
            pdf.cell(w, 7, f"  {v}", fill=True)
            x += w
        pdf.set_y(pdf.get_y() + 7)

    # Horizontal bar chart — Account Status
    pdf.set_y(pdf.get_y() + 10)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 8, "Account Status Distribution", new_x="LMARGIN", new_y="NEXT")

    chart_y = pdf.get_y() + 4
    bar_h = 8
    bar_gap = 14
    chart_w = content_w - 20
    max_count = max(stats["active"], stats["frozen"], stats["closed"], 1)

    status_data = [
        ("Active", stats["active"], (46, 125, 50)),
        ("Frozen", stats["frozen"], (198, 40, 40)),
        ("Closed", stats["closed"], (245, 124, 0)),
    ]
    for i, (label, count, color) in enumerate(status_data):
        y = chart_y + i * bar_gap
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.set_xy(margin, y)
        pdf.cell(25, bar_h, label)
        draw_hbar(margin + 25, y, chart_w - 25, bar_h, count, count, max_count, color, str)

    # ═══════════════════════════════════════════════════════════════════
    #  PAGE 3 — Financial Summary
    # ═══════════════════════════════════════════════════════════════════
    pdf.add_page()

    pdf.set_fill_color(26, 35, 126)
    pdf.rect(0, 0, page_w, 7, style="F")
    pdf.set_y(12)
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 10, "2. Financial Summary", new_x="LMARGIN", new_y="NEXT")

    # Financial table
    pdf.set_y(pdf.get_y() + 4)
    fin_col_w = [70, 50, 60]
    fin_headers = ["Metric", "Amount (₹)", "Notes"]
    fin_rows = [
        ("Total Bank Balance", stats["total_balance"], "Across all accounts"),
        ("Total Deposits", stats["total_dep"], "All time"),
        ("Total Withdrawals", stats["total_with"], "All time"),
        ("Total Transfers", stats["total_trans"], "Between accounts"),
        ("Total Transactions", stats["total_txns"], "Across all accounts"),
    ]

    # Table header
    pdf.set_fill_color(26, 35, 126)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    x = margin
    for h, w in zip(fin_headers, fin_col_w):
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(w, 8, f"  {h}", fill=True)
        x += w
    pdf.set_y(pdf.get_y() + 8)

    # Table rows
    pdf.set_text_color(50, 50, 50)
    for i, (label, val, note) in enumerate(fin_rows):
        pdf.set_font("Arial", "B" if i == 0 else "", 9)
        if i % 2 == 0:
            pdf.set_fill_color(232, 245, 233)  # light green
        else:
            pdf.set_fill_color(255, 255, 255)
        x = margin
        vals = [label, fmt_inr(val), note]
        for v, w in zip(vals, fin_col_w):
            pdf.set_xy(x, pdf.get_y())
            pdf.cell(w, 7, f"  {v}", fill=True)
            x += w
        pdf.set_y(pdf.get_y() + 7)

    # Vertical bar chart — Financial Comparison
    pdf.set_y(pdf.get_y() + 10)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 8, "Financial Comparison (Deposits vs Withdrawals vs Transfers)",
             new_x="LMARGIN", new_y="NEXT")

    chart_y = pdf.get_y() + 4
    vbar_w = 28
    vbar_gap = (content_w - 3 * vbar_w) / 4
    vbar_h = 60

    fin_comparison = [
        ("Deposits", stats["total_dep"], (76, 175, 80)),
        ("Withdrawals", stats["total_with"], (229, 57, 53)),
        ("Transfers", stats["total_trans"], (25, 118, 210)),
    ]
    max_fin = max(stats["total_dep"], stats["total_with"], stats["total_trans"], 1)

    for i, (label, val, color) in enumerate(fin_comparison):
        x = margin + vbar_gap + i * (vbar_w + vbar_gap)
        draw_vbar(x, chart_y, vbar_w, vbar_h, val, max_fin, color, label, fmt_cr)

    # ═══════════════════════════════════════════════════════════════════
    #  PAGE 4 — Category Breakdown
    # ═══════════════════════════════════════════════════════════════════
    pdf.add_page()

    pdf.set_fill_color(26, 35, 126)
    pdf.rect(0, 0, page_w, 7, style="F")
    pdf.set_y(12)
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 10, "3. Top Transaction Categories", new_x="LMARGIN", new_y="NEXT")

    cat_labels = chart_data["category_labels"]
    cat_amounts = chart_data["category_amounts"]

    if cat_labels:
        # Category table
        pdf.set_y(pdf.get_y() + 4)
        cat_col_w = [8, 55, 55, 52]
        cat_headers = ["#", "Category", "Total Amount", "Percentage"]
        total_cat_amt = sum(cat_amounts)

        pdf.set_fill_color(26, 35, 126)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 9)
        x = margin
        for h, w in zip(cat_headers, cat_col_w):
            pdf.set_xy(x, pdf.get_y())
            pdf.cell(w, 8, f"  {h}", fill=True)
            x += w
        pdf.set_y(pdf.get_y() + 8)

        pdf.set_text_color(50, 50, 50)
        cat_colors = [
            (76, 175, 80), (33, 150, 243), (255, 152, 0), (233, 30, 99),
            (156, 39, 176), (0, 188, 212), (255, 87, 34), (96, 125, 139),
        ]
        for i, (label, amt) in enumerate(zip(cat_labels, cat_amounts)):
            pct = round(amt / max(total_cat_amt, 1) * 100, 1)
            pdf.set_font("Arial", "", 9)
            if i % 2 == 0:
                pdf.set_fill_color(255, 243, 224)  # light orange
            else:
                pdf.set_fill_color(255, 255, 255)

            # Color indicator dot
            r, g, b = cat_colors[i % len(cat_colors)]
            pdf.set_fill_color(r, g, b)

            x = margin
            vals = [str(i + 1), label, fmt_inr(amt), f"{pct}%"]
            for v, w in zip(vals, cat_col_w):
                pdf.set_xy(x, pdf.get_y())
                pdf.cell(w, 7, f"  {v}", fill=True)
                x += w
            pdf.set_y(pdf.get_y() + 7)

        # Category horizontal bars
        pdf.set_y(pdf.get_y() + 10)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(26, 35, 126)
        pdf.cell(0, 8, "Category Distribution by Volume", new_x="LMARGIN", new_y="NEXT")

        chart_y = pdf.get_y() + 4
        cat_bar_h = 6
        cat_bar_gap = 10
        max_cat_amt = max(cat_amounts) if cat_amounts else 1

        for i, (label, amt) in enumerate(zip(cat_labels, cat_amounts)):
            y = chart_y + i * cat_bar_gap
            if y > 260:  # Page overflow protection
                break
            r, g, b = cat_colors[i % len(cat_colors)]
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(50, 50, 50)
            pdf.set_xy(margin, y)
            pdf.cell(35, cat_bar_h, label[:25])
            draw_hbar(margin + 35, y, content_w - 55, cat_bar_h,
                      amt, amt, max_cat_amt, (r, g, b), fmt_inr)

    # ═══════════════════════════════════════════════════════════════════
    #  Footer on all pages
    # ═══════════════════════════════════════════════════════════════════
    page_count = pdf.page_no()
    for i in range(1, page_count + 1):
        pdf.page = i
        pdf.set_y(285)
        pdf.set_font("Arial", "", 7)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 5, f"Union Bank Management System  |  Page {i} of {page_count}  |  "
                       f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                 align="C")

        # Bottom accent bar
        pdf.set_fill_color(26, 35, 126)
        pdf.rect(0, 295, page_w, 2, style="F")

    # ── Output ────────────────────────────────────────────────────────
    pdf_bytes = pdf.output()
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    return buf


# ── Admin PDF Report Route ───────────────────────────────────────────────────

@app.route("/admin/statistics/pdf")
@admin_required
def admin_statistics_pdf():
    """Download a PDF report of bank statistics."""
    if not HAS_FPDF:
        flash("PDF generation requires fpdf2. Run: pip install fpdf2", "error")
        return redirect(url_for("admin_statistics"))

    from container import get_container
    c = get_container()
    s = c.admin_service().get_statistics()

    stats = {
        "total_customers": s["total_customers"],
        "active": s["active"],
        "frozen": s["frozen"],
        "closed": s["closed"],
        "total_balance": s["total_balance"],
        "total_dep": s["total_dep"],
        "total_with": s["total_with"],
        "total_trans": s["total_trans"],
        "total_txns": s["total_txns"],
    }

    chart_data = {
        "category_labels": [cat["name"] for cat in s["sorted_categories"]],
        "category_amounts": [cat["total"] for cat in s["sorted_categories"]],
    }

    try:
        pdf_buf = _generate_admin_pdf(stats, chart_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return send_file(
            pdf_buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"union_bank_report_{timestamp}.pdf",
        )
    except Exception as e:
        flash(f"Error generating PDF: {e}", "error")
        return redirect(url_for("admin_statistics"))


# ── Logout ───────────────────────────────────────────────────────────────────

@app.route("/logout")
def logout():
    """Log out (customer or admin)."""
    was_admin = session.pop("is_admin", False)
    session.pop("account_number", None)
    if was_admin:
        flash("Admin logged out.", "info")
        return redirect(url_for("admin_login"))
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("  " + "=" * 50)
    print("     UNION BANK - Web Interface")
    print("  " + "=" * 50)
    print("     Open: http://localhost:5000")
    print("     Ctrl+C to stop")
    print("  " + "=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
