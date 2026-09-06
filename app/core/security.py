import hashlib
import secrets
from uuid import UUID

from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def generate_refresh_token() -> str:
    # ~32 bytes -> url-safe string; fine to send to clients
    return secrets.token_urlsafe(32)


def build_refresh_token(family_id: UUID) -> str:
    """Opaque refresh token: `{family_id}.{secret}` for session lookup + reuse checks."""
    return f"{family_id}.{generate_refresh_token()}"


def extract_family_id(token: str) -> UUID:
    """Parse family id from a `{family_id}.{secret}` refresh token."""
    family_part, sep, secret = token.partition(".")
    if not sep or not family_part or not secret:
        raise ValueError("invalid refresh token format")
    return UUID(family_part)


def hash_refresh_token(token: str) -> str:
    """
    Why SHA-256 here:
    - Deterministic: same input -> same hash -> exact DB lookup / unique index
    - Fast: refresh happens often; argon2/bcrypt would be needlessly slow
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
