from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.v1.config.database import get_sync_db_pg
from api.v1.services.institution_api_token import authenticate_institution_api_token

security = HTTPBearer(auto_error=False)


def get_current_api_institution(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_sync_db_pg),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token institucional requerido",
        )
    _, institution = authenticate_institution_api_token(db, credentials.credentials)
    return institution
