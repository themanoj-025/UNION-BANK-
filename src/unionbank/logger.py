"""logger.py  –  Shim re-exporting from utils.logger for backward compatibility.

After the Phase 1 god-module split, the logger module moved to
src/unionbank/utils/logger.py. This stub exists so that legacy imports
like ``from logger import logger`` continue to work while the codebase
is gradually updated to ``from utils.logger import logger``.
"""

from unionbank.utils.logger import (  # noqa: F401
    LOG_FILE,
    JsonFormatter,
    clear_context,
    get_account_context,
    get_request_id,
    log_with_context,
    logger,
    set_account_context,
    set_request_id,
)
