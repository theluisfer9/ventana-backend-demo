from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.v1.models.institution import Institution
from api.v1.models.institution_api_token import InstitutionApiToken


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_institution_api_token(
    db: Session,
    institution: Institution,
    name: str,
    expires_in_days: int | None = None,
) -> tuple[InstitutionApiToken, str]:
    raw_secret = secrets.token_urlsafe(32)
    token = f"inst_{raw_secret}"
    prefix = token[:16]
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    api_token = InstitutionApiToken(
        institution_id=institution.id,
        name=name,
        token_prefix=prefix,
        token_hash=_hash_token(token),
        expires_at=expires_at,
        is_active=True,
    )
    db.add(api_token)
    db.commit()
    db.refresh(api_token)
    return api_token, token


def list_institution_api_tokens(db: Session, institution_id) -> list[InstitutionApiToken]:
    stmt = (
        select(InstitutionApiToken)
        .where(InstitutionApiToken.institution_id == institution_id)
        .order_by(InstitutionApiToken.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def revoke_institution_api_token(db: Session, institution_id, token_id) -> bool:
    stmt = select(InstitutionApiToken).where(
        InstitutionApiToken.id == token_id,
        InstitutionApiToken.institution_id == institution_id,
    )
    api_token = db.execute(stmt).scalar_one_or_none()
    if not api_token:
        return False
    api_token.is_active = False
    db.commit()
    return True


def authenticate_institution_api_token(db: Session, token: str) -> tuple[InstitutionApiToken, Institution]:
    prefix = token[:16]
    stmt = (
        select(InstitutionApiToken)
        .join(Institution, Institution.id == InstitutionApiToken.institution_id)
        .where(InstitutionApiToken.token_prefix == prefix)
    )
    api_token = db.execute(stmt).scalar_one_or_none()
    if not api_token or not api_token.institution or not api_token.institution.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token institucional inválido")
    if not api_token.is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token institucional expirado o revocado")
    if not hmac.compare_digest(api_token.token_hash, _hash_token(token)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token institucional inválido")

    api_token.last_used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(api_token)
    return api_token, api_token.institution
