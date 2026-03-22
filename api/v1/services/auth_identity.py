from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from api.v1.models.user import User
from api.v1.services.keycloak_auth import KeycloakIdentity


def resolve_user_from_keycloak_identity(
    db: Session, identity: KeycloakIdentity
) -> User | None:
    stmt = select(User).where(User.keycloak_id == identity.subject)
    user = db.execute(stmt).scalar_one_or_none()

    if user is None and identity.email:
        stmt = select(User).where(
            or_(User.email == identity.email, User.username == identity.email)
        )
        user = db.execute(stmt).scalar_one_or_none()
        if user and not user.keycloak_id:
            user.keycloak_id = identity.subject

    if user is None and identity.username:
        stmt = select(User).where(User.username == identity.username)
        user = db.execute(stmt).scalar_one_or_none()
        if user and not user.keycloak_id:
            user.keycloak_id = identity.subject

    if user is None:
        return None

    updated = False
    if identity.email and user.email != identity.email:
        user.email = identity.email
        updated = True
    if identity.username and user.username != identity.username:
        user.username = identity.username
        updated = True
    if identity.first_name and user.first_name != identity.first_name:
        user.first_name = identity.first_name
        updated = True
    if identity.last_name and user.last_name != identity.last_name:
        user.last_name = identity.last_name
        updated = True
    if user.keycloak_id != identity.subject:
        user.keycloak_id = identity.subject
        updated = True

    if updated:
        db.commit()
        db.refresh(user)

    return user
