"""file_io.py  –  JSON file persistence with corruption recovery and atomic writes.
"""

import json
import os
import shutil
import tempfile

# ── Data directory: respect env override for test isolation ───────────────────
_data_dir = os.environ.get(
    "UNION_BANK_DATA_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
)
ACCOUNTS_FILE = os.path.join(_data_dir, "accounts.json")
TRANSACTIONS_FILE = os.path.join(_data_dir, "transactions.json")
LOGIN_ATTEMPTS_FILE = os.path.join(_data_dir, "login_attempts.json")
SAVINGS_GOALS_FILE = os.path.join(_data_dir, "savings_goals.json")
ADMIN_FILE = os.path.join(_data_dir, "admin.json")


# ─────────────────────────────────────────────
#  JSON helpers (hardened with auto-backup)
# ─────────────────────────────────────────────

def _backup_path(filepath: str) -> str:
    """Return the backup file path (same directory, .bak extension)."""
    return filepath + ".bak"


def _get_logger():
    from unionbank.utils.logger import logger
    return logger


def load_json(filepath: str) -> dict:
    """Load JSON file safely with corruption recovery.
    Returns empty dict if file is missing, empty, or corrupted.
    On corruption, attempts to restore from backup.
    """
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, ValueError, IOError) as e:
        log = _get_logger()
        log.error(f"Corrupted JSON file detected: {filepath} — {e}")

        # Attempt recovery from backup
        backup = _backup_path(filepath)
        if os.path.exists(backup):
            log.info(f"Attempting recovery from backup: {backup}")
            try:
                with open(backup, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        with open(filepath, "w", encoding="utf-8") as fw:
                            json.dump(data, fw, indent=4)
                        log.info(f"Recovered {filepath} from backup successfully.")
                        return data
            except (json.JSONDecodeError, IOError):
                log.error(f"Backup file also corrupted: {backup}")

        log.warning(f"Resetting corrupted file to empty: {filepath}")
        save_json(filepath, {})
        return {}


def save_json(filepath: str, data) -> None:
    """Persist data to JSON file atomically with auto-backup.
    - Creates a .bak copy of the previous version before overwriting
    - Writes to a temp file first, then atomically renames (reduces corruption)
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    if os.path.exists(filepath):
        try:
            shutil.copy2(filepath, _backup_path(filepath))
        except (IOError, shutil.Error) as e:
            _get_logger().warning(f"Failed to create backup for {filepath}: {e}")

    try:
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json",
            prefix=os.path.basename(filepath) + ".",
            dir=os.path.dirname(filepath),
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(fd)

        os.replace(tmp_path, filepath)
    except (IOError, OSError) as e:
        _get_logger().error(f"Failed to save {filepath}: {e}")
        raise
