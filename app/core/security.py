"""Password hashing and refresh-token helpers."""

import hashlib
import secrets

from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    """Hash a plaintext password for storage."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plaintext password matches the stored hash."""
    return password_hash.verify(plain_password, hashed_password)


def generate_refresh_token() -> str:
    """Create a URL-safe opaque refresh token for the client."""
    # ~32 bytes -> url-safe string; fine to send to clients
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """SHA-256 digest of a refresh token for safe DB lookup.

    Why SHA-256 here:
    - Deterministic: same input -> same hash -> exact DB lookup / unique index
    - Fast: refresh happens often; argon2/bcrypt would be needlessly slow
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
