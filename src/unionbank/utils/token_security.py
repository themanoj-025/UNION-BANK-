"""token_security.py – Token security utilities for Phase 3 hardening.

Provides:
- SHA-256 hashing for refresh token IDs (prevents plaintext storage in DB)
- Fernet symmetric encryption for TOTP secrets (defense-in-depth)

Design decisions:
- Refresh token IDs use SHA-256 rather than bcrypt because they are already
  high-entropy random values (24 hex chars from UUID4). Bcrypt's deliberate
  slowness is unnecessary here and would add ~300ms per token operation.
- TOTP secrets use Fernet (AES-128-CBC + HMAC-SHA256) because they are
  low-entropy base32 strings that could be brute-forced if the DB is leaked.
  The encryption key is loaded from TOKEN_ENCRYPTION_KEY env var.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  Refresh Token ID Hashing (SHA-256)
# ═══════════════════════════════════════════════════════════════════════════════


def hash_token_id(token_id: str) -> str:
    """Hash a refresh token ID with SHA-256 for safe storage in the DB.

    The raw token_id is embedded in the JWT (subject field) and sent by the
    client. We never store the raw value — only this hash — so a DB leak
    cannot be used to replay refresh tokens.
    """
    return hashlib.sha256(token_id.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
#  TOTP Secret Encryption (Fernet / AES-128-CBC)
# ═══════════════════════════════════════════════════════════════════════════════

_fernet_instance = None


def _get_fernet():
    """Lazy-init the Fernet cipher from the TOKEN_ENCRYPTION_KEY env var."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    from unionbank.config import settings
    key = settings.TOKEN_ENCRYPTION_KEY
    if not key:
        logger.warning(
            "TOKEN_ENCRYPTION_KEY not set — TOTP secrets stored in plaintext. "
            "Set the env var for production deployments."
        )
        return None

    try:
        from cryptography.fernet import Fernet
        _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
        return _fernet_instance
    except Exception:
        logger.error("Failed to initialize Fernet cipher", exc_info=True)
        return None


def encrypt_totp_secret(secret: Optional[str]) -> Optional[str]:
    """Encrypt a TOTP secret for storage in the DB.

    Returns None if secret is None (2FA disabled).
    Falls back to plaintext if TOKEN_ENCRYPTION_KEY is not set (dev mode).
    """
    if secret is None:
        return None

    fernet = _get_fernet()
    if fernet is None:
        # Dev/test mode — store plaintext with a prefix so we can detect it
        return f"plain:{secret}"

    try:
        encrypted = fernet.encrypt(secret.encode("utf-8")).decode("utf-8")
        return f"enc:{encrypted}"
    except Exception:
        logger.error("Failed to encrypt TOTP secret", exc_info=True)
        return f"plain:{secret}"


def decrypt_totp_secret(encrypted_secret: Optional[str]) -> Optional[str]:
    """Decrypt a TOTP secret retrieved from the DB.

    Handles three formats:
    - "enc:<fernet-ciphertext>" — encrypted with Fernet (production)
    - "plain:<secret>" — plaintext fallback (dev/test mode)
    - bare string — legacy plaintext (pre-encryption migration)
    """
    if encrypted_secret is None:
        return None

    if encrypted_secret.startswith("enc:"):
        ciphertext = encrypted_secret[4:]  # strip "enc:" prefix
        fernet = _get_fernet()
        if fernet is None:
            logger.error("Cannot decrypt TOTP secret — TOKEN_ENCRYPTION_KEY not set")
            return None
        try:
            return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except Exception:
            logger.error("Failed to decrypt TOTP secret", exc_info=True)
            return None

    if encrypted_secret.startswith("plain:"):
        return encrypted_secret[6:]  # strip "plain:" prefix

    # Legacy bare string — treat as plaintext (pre-encryption data)
    logger.warning("TOTP secret stored as bare plaintext — will re-encrypt on next update")
    return encrypted_secret
