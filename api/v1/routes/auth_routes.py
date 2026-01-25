from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from api.v1.config.database import get_sync_db_pg
from api.v1.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    CurrentUser,
    ProfileUpdate,
)
from api.v1.schemas.user import PasswordChange
from api.v1.services.auth import (
    authenticate_user,
    create_user_session,
    refresh_user_tokens,
    revoke_all_user_sessions,
    get_current_user_info,
)
from api.v1.services.user import update_user_password
from api.v1.dependencies.auth_dependency import (
    get_current_user,
    get_client_ip,
    get_user_agent,
)
from api.v1.models.user import User
from api.v1.auth.password import verify_password

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_sync_db_pg),
):
    """
    Autenticar usuario y obtener tokens de acceso.
    """
    user = authenticate_user(db, login_data.email, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    return create_user_session(db, user, ip_address, user_agent)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_sync_db_pg),
):
    """
    Renovar tokens usando el refresh token.
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    result = refresh_user_tokens(
        db,
        refresh_data.refresh_token,
        ip_address,
        user_agent,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de actualización inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return result


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db_pg),
):
    """
    Cerrar sesión (revocar todas las sesiones del usuario).
    """
    count = revoke_all_user_sessions(db, str(current_user.id))
    return {"message": f"Sesión cerrada. {count} sesiones revocadas."}


@router.get("/me", response_model=CurrentUser)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener información del usuario autenticado.
    """
    return get_current_user_info(current_user)


@router.put("/me", response_model=CurrentUser)
def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db_pg),
):
    """
    Actualizar perfil del usuario autenticado.
    """
    for key, value in profile_data.model_dump(exclude_unset=True).items():
        setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)

    return get_current_user_info(current_user)


@router.put("/me/password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db_pg),
):
    """
    Cambiar contraseña del usuario autenticado.
    """
    # Verify current password
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario no tiene contraseña configurada (usa autenticación externa)",
        )

    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta",
        )

    # Update password
    update_user_password(db, current_user, password_data.new_password)

    # Revoke all sessions
    revoke_all_user_sessions(db, str(current_user.id))

    return {"message": "Contraseña actualizada. Por favor, inicie sesión nuevamente."}
