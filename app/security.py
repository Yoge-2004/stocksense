import hashlib
import secrets
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Secure password hashing using SHA-256 with salt."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000
    )
    return f"{salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against salt$hash string."""
    try:
        salt, stored_hash = hashed_password.split("$", 1)
        expected_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100_000
        ).hex()
        return hmac.compare_digest(stored_hash, expected_hash)
    except Exception:
        return False

def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP for password reset."""
    return "".join(secrets.choice("0123456789") for _ in range(length))
