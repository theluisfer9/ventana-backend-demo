from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from jose import jwt, JWTError
from decouple import config
import uuid

# JWT Configuration
JWT_SECRET_KEY = config("JWT_SECRET_KEY", default="your-secret-key-change-in-production")
JWT_ALGORITHM = config("JWT_ALGORITHM", default="HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = config(
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int
)
JWT_REFRESH_TOKEN_EXPIRE_DAYS = config(
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS", default=7, cast=int
)


def create_access_token(
    user_id: str,
    role_code: Optional[str] = None,
    additional_claims: Optional[dict] = None,
) -> Tuple[str, str, datetime]:
    """
    Create a new access token.

    Returns:
        Tuple of (token, jti, expires_at)
    """
    jti = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "type": "access",
    }

    if role_code:
        payload["role"] = role_code

    if additional_claims:
        payload.update(additional_claims)

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, jti, expires_at


def create_refresh_token(user_id: str) -> Tuple[str, str, datetime]:
    """
    Create a new refresh token.

    Returns:
        Tuple of (token, jti, expires_at)
    """
    jti = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": user_id,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "type": "refresh",
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, jti, expires_at


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Verify a JWT token and check its type.

    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Token payload if valid and correct type, None otherwise
    """
    payload = decode_token(token)

    if payload is None:
        return None

    # Verify token type
    if payload.get("type") != token_type:
        return None

    # Verify expiration (jose already does this, but double-check)
    exp = payload.get("exp")
    if exp:
        if isinstance(exp, (int, float)):
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        else:
            exp_datetime = exp

        if exp_datetime < datetime.now(timezone.utc):
            return None

    return payload


def get_token_expiry_seconds() -> int:
    """Get access token expiry time in seconds"""
    return JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
