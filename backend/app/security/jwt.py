"""JWT generation and verification, plus secure bcrypt password hashing."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
from backend.app.config.settings import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hashes a password with bcrypt and returns a UTF-8 string."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed HS256 JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
