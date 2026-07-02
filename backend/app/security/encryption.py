import base64
import hashlib

from cryptography.fernet import Fernet

from app.config.settings import get_settings


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret_key.encode()).digest())
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
