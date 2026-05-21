import os
import logging
from cryptography.fernet import Fernet
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Fernet cipher. Generate a fallback key for development if none provided.
if not settings.ENCRYPTION_KEY:
    logger.warning(
        "ENCRYPTION_KEY not set in configuration! Generating a temporary fallback key."
    )
    # For local dev safety, generate a transient key
    fallback_key = Fernet.generate_key()
    fernet_cipher = Fernet(fallback_key)
else:
    try:
        fernet_cipher = Fernet(settings.ENCRYPTION_KEY.encode())
    except Exception as e:
        logger.error(f"Invalid ENCRYPTION_KEY format. Generating fallback. Error: {e}")
        fernet_cipher = Fernet(Fernet.generate_key())


def encrypt_token(token: str) -> str:
    """Encrypt a string token at rest."""
    if not token:
        return ""
    return fernet_cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token."""
    if not encrypted_token:
        return ""
    try:
        return fernet_cipher.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt token: {e}")
        raise ValueError("Decryption failed. Invalid key or corrupted payload.")
