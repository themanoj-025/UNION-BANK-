"""
utils  –  Utility package for Union Bank Management System.

This package splits the old monolithic utils.py into focused sub-modules:
  - file_io.py:      JSON load/save with corruption recovery, file path constants
  - validation.py:   Input validation (email, phone, password, name)
  - formatting.py:   Currency formatting, timestamps, ID generators, CLI input helpers
  - savings.py:      Savings goals persistence  - hashing.py:      Password hashing (bcrypt)
  - rate_limit.py:    Rate limiting + session management
  - csv_export.py:    CSV export for transaction statements
  - categories.py:    Transaction category selection (CLI helper)
  - interest.py:      Interest calculation

All functions are re-exported here for backward compatibility."""

from .validation import (
    validate_email,
    validate_phone,
    validate_password,
    validate_name,
)

from .formatting import (
    fmt_currency,
    now_str,
    generate_account_number,
    generate_transaction_id,
    generate_goal_id,
    generate_loan_id,
    generate_notification_id,
    calculate_emi,
    get_float,
    get_int,
    mask_account_number,
    mask_sensitive_data,
)

from .hashing import (
    hash_password,
    verify_password,
)

from .rate_limit import (
    MAX_LOGIN_ATTEMPTS,
    LOGIN_LOCKOUT_MINUTES,
    SESSION_TIMEOUT_SECONDS,
    check_login_locked,
    record_failed_login,
    reset_login_attempts,
    check_session_timeout,
    get_session_timeout_seconds,
)

from .csv_export import (
    export_transactions_to_csv,
    generate_csv_filename,
)

from .categories import (
    TRANSACTION_CATEGORIES,
    get_category_choice,
)

from domain.interest import (
    SAVINGS_INTEREST_RATE,
    calculate_monthly_interest,
)
