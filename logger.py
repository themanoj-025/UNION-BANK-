"""
logger.py  –  Centralised logging for Union Bank.

Supports both text-based logging (file + console) and structured JSON
logging with automatic request-ID injection for traceability.

Log levels used:
  DEBUG   – fine-grained internal flow (not shown in console)
  INFO    – normal operations (login, deposit, transfer …)
  WARNING – suspicious / notable events (bad password, frozen acc …)
  ERROR   – unexpected failures
  CRITICAL– admin actions (freeze, delete, close account)

Log file  : data/bank.log  (text format, DEBUG+)
Console   : WARNING and above only (keeps terminal clean)

Structured JSON format includes: timestamp, level, logger, message,
request_id (if set), account_number (if set), and any extra context.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Optional

# ── File path ─────────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.dirname(__file__), "data", "bank.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Thread-local context for request-scoped values
# ═══════════════════════════════════════════════════════════════════════════════

_request_context = threading.local()


def set_request_id(request_id: str) -> None:
    """Set a request ID for the current thread (automatically cleaned up)."""
    _request_context.request_id = request_id


def get_request_id() -> Optional[str]:
    """Get the current thread's request ID."""
    return getattr(_request_context, "request_id", None)


def set_account_context(account_number: Optional[str]) -> None:
    """Set an account number context for the current thread."""
    _request_context.account_number = account_number


def get_account_context() -> Optional[str]:
    """Get the current thread's account context."""
    return getattr(_request_context, "account_number", None)


def clear_context() -> None:
    """Clear all thread-local context (call at end of request)."""
    for attr in ("request_id", "account_number"):
        try:
            delattr(_request_context, attr)
        except AttributeError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Structured JSON Formatter
# ═══════════════════════════════════════════════════════════════════════════════


class JsonFormatter(logging.Formatter):
    """Log formatter that outputs JSON objects.

    Adds structured fields including request_id and account_number from
    thread-local context when available. Extra keyword arguments passed
    to the log call are included in the ``extra`` field.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt or "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject request-scoped context from thread-local
        request_id = get_request_id()
        if request_id:
            log_entry["request_id"] = request_id

        account_ctx = get_account_context()
        if account_ctx:
            log_entry["account"] = account_ctx

        # Include extra fields from the log call (e.g. logger.info("msg", extra={"key": "val"}))
        if hasattr(record, "extra") and record.extra:
            log_entry["extra"] = record.extra

        # Include exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


# ═══════════════════════════════════════════════════════════════════════════════
#  Handlers
# ═══════════════════════════════════════════════════════════════════════════════

# ── Text formatter (for file + console) ────────────────────────────────────
_text_fmt = logging.Formatter(
    fmt="[%(asctime)s]  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── JSON formatter (for JSON log file) ─────────────────────────────────────
_json_fmt = JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S.%fZ")

# ── File handler — text format (DEBUG+) ─────────────────────────────────────
_fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_text_fmt)

# ── JSON file handler — structured JSON (INFO+) ────────────────────────────
_JSON_LOG_FILE = os.path.join(os.path.dirname(__file__), "data", "bank.jsonl")
_jfh = logging.FileHandler(_JSON_LOG_FILE, encoding="utf-8")
_jfh.setLevel(logging.INFO)
_jfh.setFormatter(_json_fmt)

# ── Console handler — text format (WARNING+) ────────────────────────────────
_ch = logging.StreamHandler()
_ch.setLevel(logging.WARNING)
_ch.setFormatter(_text_fmt)

# ── Root logger ───────────────────────────────────────────────────────────────
logger = logging.getLogger("union_bank")
logger.setLevel(logging.DEBUG)
logger.addHandler(_fh)
logger.addHandler(_jfh)
logger.addHandler(_ch)
logger.propagate = False


# ═══════════════════════════════════════════════════════════════════════════════
#  Convenience helper — log with extra context dict
# ═══════════════════════════════════════════════════════════════════════════════


def log_with_context(
    level: int,
    message: str,
    *,
    request_id: Optional[str] = None,
    account: Optional[str] = None,
    **extra: Any,
) -> None:
    """Log a message with structured extra context.

    The context dict is separate from the message so the JSON formatter
    can include it as a structured ``extra`` field.

    Usage:
        log_with_context(logging.INFO, "Deposit processed",
                         account="1234567890", amount=500.00, category="Salary")
    """
    record = logger.makeRecord(
        logger.name, level, "", 0, message, (), None,
    )
    record.extra = extra
    if request_id:
        record.request_id = request_id
    if account:
        record.account = account
    logger.handle(record)
