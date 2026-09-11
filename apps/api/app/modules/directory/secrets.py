import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def cipher() -> Fernet:
    if not settings.directory_encryption_key:
        raise ValueError("DIRECTORY_ENCRYPTION_KEY is not configured on the server")
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.directory_encryption_key.encode()).digest())
    return Fernet(key)


def encrypt(value: str) -> str:
    return cipher().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return cipher().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Directory secret cannot be decrypted with the configured key") from exc
