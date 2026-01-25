from fastapi import Query
from typing import Optional
from typing_extensions import Annotated
from datetime import date
from uuid import UUID

from api.v1.schemas.user import UserFilters


def user_filters_dep(
    role_id: Annotated[
        Optional[UUID],
        Query(description="Filtrar por ID de rol")
    ] = None,
    institution_id: Annotated[
        Optional[UUID],
        Query(description="Filtrar por ID de institución")
    ] = None,
    is_active: Annotated[
        Optional[bool],
        Query(description="Filtrar por estado activo/inactivo")
    ] = None,
    is_verified: Annotated[
        Optional[bool],
        Query(description="Filtrar por estado de verificación")
    ] = None,
    search: Annotated[
        Optional[str],
        Query(description="Buscar en email, username, nombre")
    ] = None,
    created_from: Annotated[
        Optional[date],
        Query(description="Creado desde (YYYY-MM-DD)")
    ] = None,
    created_to: Annotated[
        Optional[date],
        Query(description="Creado hasta (YYYY-MM-DD)")
    ] = None,
) -> UserFilters:
    """Dependency for user listing filters"""
    return UserFilters(
        role_id=role_id,
        institution_id=institution_id,
        is_active=is_active,
        is_verified=is_verified,
        search=search,
        created_from=created_from,
        created_to=created_to,
    )
