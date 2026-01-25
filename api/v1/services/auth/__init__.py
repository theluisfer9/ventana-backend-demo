from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from api.v1.models.user import User
from api.v1.models.user_session import UserSession
from api.v1.auth.password import verify_password
from api.v1.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_token_expiry_seconds,
)
from api.v1.schemas.auth import TokenResponse, CurrentUser


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.

    Returns:
        User if authentication successful, None otherwise
    """
    stmt = select(User).where(User.email == email, User.is_active == True)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        return None

    if not user.password_hash:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def create_user_session(
    db: Session,
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TokenResponse:
    """
    Create a new session for a user and return tokens.
    """
    # Create access token
    access_token, access_jti, access_expires = create_access_token(
        user_id=str(user.id),
        role_code=user.role.code if user.role else None,
    )

    # Create refresh token
    refresh_token, refresh_jti, refresh_expires = create_refresh_token(
        user_id=str(user.id)
    )

    # Store session in database
    session = UserSession(
        user_id=user.id,
        token_jti=refresh_jti,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=refresh_expires,
    )
    db.add(session)

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
    )


def refresh_user_tokens(
    db: Session,
    refresh_token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[TokenResponse]:
    """
    Refresh user tokens using a valid refresh token.
    """
    # Verify refresh token
    payload = verify_token(refresh_token, token_type="refresh")
    if not payload:
        return None

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not jti or not user_id:
        return None

    # Check if session exists and is valid
    stmt = select(UserSession).where(
        UserSession.token_jti == jti,
        UserSession.revoked_at == None,
    )
    session = db.execute(stmt).scalar_one_or_none()

    if not session or not session.is_valid:
        return None

    # Get user
    user = db.get(User, user_id)
    if not user or not user.is_active:
        return None

    # Revoke old session
    session.revoked_at = datetime.now(timezone.utc)

    # Create new session
    return create_user_session(db, user, ip_address, user_agent)


def revoke_session(db: Session, token_jti: str) -> bool:
    """
    Revoke a session by its token JTI.
    """
    stmt = select(UserSession).where(UserSession.token_jti == token_jti)
    session = db.execute(stmt).scalar_one_or_none()

    if not session:
        return False

    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True


def revoke_all_user_sessions(db: Session, user_id: str) -> int:
    """
    Revoke all active sessions for a user.

    Returns:
        Number of sessions revoked
    """
    stmt = select(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.revoked_at == None,
    )
    sessions = db.execute(stmt).scalars().all()

    count = 0
    now = datetime.now(timezone.utc)
    for session in sessions:
        session.revoked_at = now
        count += 1

    db.commit()
    return count


def get_current_user_info(user: User) -> CurrentUser:
    """
    Build CurrentUser response from User model.
    """
    permissions = []
    if user.role:
        permissions = [p.code for p in user.role.permissions]

    return CurrentUser(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        role_code=user.role.code if user.role else "",
        role_name=user.role.name if user.role else "",
        institution_code=user.institution.code if user.institution else None,
        institution_name=user.institution.name if user.institution else None,
        permissions=permissions,
    )
