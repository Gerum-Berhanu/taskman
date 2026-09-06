import hashlib
import secrets
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def generate_refresh_token() -> str:
    # ~32 bytes -> url-safe string; fine to send to clients
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """
    Why SHA-256 here:
    - Deterministic: same input -> same hash -> exact DB lookup / unique index
    - Fast: refresh happens often; argon2/bcrypt would be needlessly slow
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()