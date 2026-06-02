"""
logger.py  –  Centralised logging for Union Bank.

Log levels used:
  DEBUG   – fine-grained internal flow (not shown in console)
  INFO    – normal operations (login, deposit, transfer …)
  WARNING – suspicious / notable events (bad password, frozen acc …)
  ERROR   – unexpected failures
  CRITICAL– admin actions (freeze, delete, close account)

Log file  : data/bank.log
Console   : WARNING and above only (keeps terminal clean)
"""

import logging
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "data", "bank.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ── formatter ────────────────────────────────────────────────────────────────
_fmt = logging.Formatter(
    fmt="[%(asctime)s]  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── file handler  (DEBUG+) ────────────────────────────────────────────────────
_fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)

# ── console handler  (WARNING+) ──────────────────────────────────────────────
_ch = logging.StreamHandler()
_ch.setLevel(logging.WARNING)
_ch.setFormatter(_fmt)

# ── root logger ───────────────────────────────────────────────────────────────
logger = logging.getLogger("union_bank")
logger.setLevel(logging.DEBUG)
logger.addHandler(_fh)
logger.addHandler(_ch)
# prevent duplicate handlers if module is reloaded
logger.propagate = False
