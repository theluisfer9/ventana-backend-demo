from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.v1.auth.permissions import PermissionCode
from api.v1.config.database import get_sync_db_pg
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.models.user import User
from api.v1.schemas.system_catalog import (
    SystemCatalogCreate,
    SystemCatalogItemCreate,
    SystemCatalogItemOut,
    SystemCatalogItemUpdate,
    SystemCatalogOut,
    SystemCatalogUpdate,
)
from api.v1.services.system_catalog import (
    create_catalog_item,
    create_system_catalog,
    get_all_system_catalogs,
    get_catalog_item_by_code,
    get_catalog_item_by_id,
    get_catalog_items,
    get_system_catalog_by_code,
    get_system_catalog_by_id,
    update_catalog_item,
    update_system_catalog,
)

router = APIRouter(prefix="/system-catalogs", tags=["Catálogos del Sistema"])


@router.get("/", response_model=list[SystemCatalogOut])
def list_system_catalogs(
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.SYSTEM_CONFIG)),
):
    return get_all_system_catalogs(db)


@router.post("/", response_model=SystemCatalogOut, status_code=status.HTTP_201_CREATED)
def create_new_system_catalog(
    catalog_data: SystemCatalogCreate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.SYSTEM_CONFIG)),
):
    if get_system_catalog_by_code(db, catalog_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un catálogo con este código",
        )
    return create_system_catalog(db, catalog_data)


@router.put("/{catalog_id}", response_model=SystemCatalogOut)
def update_existing_system_catalog(
    catalog_id: UUID,
    catalog_data: SystemCatalogUpdate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.SYSTEM_CONFIG)),
):
    catalog = get_system_catalog_by_id(db, catalog_id)
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catálogo no encontrado",
        )
    if catalog_data.code and catalog_data.code != catalog.code:
        if get_system_catalog_by_code(db, catalog_data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un catálogo con este código",
            )
    return update_system_catalog(db, catalog, catalog_data)


@router.get("/{catalog_id}/items", response_model=list[SystemCatalogItemOut])
def list_system_catalog_items(
    catalog_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.SYSTEM_CONFIG)),
):
    catalog = get_system_catalog_by_id(db, catalog_id)
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catálogo no encontrado",
        )
    return get_catalog_items(db, catalog_id)


@router.post(
    "/{catalog_id}/items",
    response_model=SystemCatalogItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_new_system_catalog_item(
    catalog_id: UUID,
    item_data: SystemCatalogItemCreate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.SYSTEM_CONFIG)),
):
    catalog = get_system_catalog_by_id(db, catalog_id)
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catálogo no encontrado",
        )
    if get_catalog_item_by_code(db, catalog_id, item_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un item con este código en el catálogo",
        )
    return create_catalog_item(db, catalog_id, item_data)


@router.put("/{catalog_id}/items/{item_id}", response_model=SystemCatalogItemOut)
def update_existing_system_catalog_item(
    catalog_id: UUID,
    item_id: UUID,
    item_data: SystemCatalogItemUpdate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.SYSTEM_CONFIG)),
):
    catalog = get_system_catalog_by_id(db, catalog_id)
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catálogo no encontrado",
        )
    item = get_catalog_item_by_id(db, item_id)
    if not item or item.catalog_id != catalog_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item no encontrado",
        )
    if item_data.code and item_data.code != item.code:
        if get_catalog_item_by_code(db, catalog_id, item_data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un item con este código en el catálogo",
            )
    return update_catalog_item(db, item, item_data)
