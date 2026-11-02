"""Password hashing, refresh-token, and registration OTP helpers."""

import hashlib
import hmac
import secrets

from pwdlib import PasswordHash

from app.core.config import settings


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


def generate_registration_otp(
    length: int = settings.registration_otp_length,
) -> str:
    """Create a numeric registration OTP (cryptographically strong digits)."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def hash_registration_otp(otp: str) -> str:
    """SHA-256 digest of an OTP for Redis storage (same rationale as refresh)."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def verify_registration_otp(plain: str, otp_hash: str) -> bool:
    """Return True if the plaintext OTP matches the stored SHA-256 digest.
    
    == on strings can leak information via timing: it often returns as soon as it finds a mismatch, 
    so an attacker measuring response time might learn how much of the secret matched.

    hmac.compare_digest is a constant-time compare. 
    It always looks at the whole value so timing doesn't help guess the digest (or OTP).
    """
    return hmac.compare_digest(hash_registration_otp(plain), otp_hash)