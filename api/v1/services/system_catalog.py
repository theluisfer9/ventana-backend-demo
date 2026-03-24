from sqlalchemy.orm import Session

from api.v1.models.system_catalog import SystemCatalog, SystemCatalogItem
from api.v1.schemas.system_catalog import (
    SystemCatalogCreate,
    SystemCatalogItemCreate,
    SystemCatalogItemUpdate,
    SystemCatalogUpdate,
)


def get_all_system_catalogs(db: Session) -> list[SystemCatalog]:
    return db.query(SystemCatalog).order_by(SystemCatalog.name.asc()).all()


def get_system_catalog_by_id(db: Session, catalog_id) -> SystemCatalog | None:
    return db.get(SystemCatalog, catalog_id)


def get_system_catalog_by_code(db: Session, code: str) -> SystemCatalog | None:
    return db.query(SystemCatalog).filter(SystemCatalog.code == code).first()


def create_system_catalog(db: Session, catalog_data: SystemCatalogCreate) -> SystemCatalog:
    catalog = SystemCatalog(**catalog_data.model_dump())
    db.add(catalog)
    db.commit()
    db.refresh(catalog)
    return catalog


def update_system_catalog(
    db: Session,
    catalog: SystemCatalog,
    catalog_data: SystemCatalogUpdate,
) -> SystemCatalog:
    for key, value in catalog_data.model_dump(exclude_unset=True).items():
        setattr(catalog, key, value)
    db.commit()
    db.refresh(catalog)
    return catalog


def get_catalog_items(db: Session, catalog_id) -> list[SystemCatalogItem]:
    return (
        db.query(SystemCatalogItem)
        .filter(SystemCatalogItem.catalog_id == catalog_id)
        .order_by(SystemCatalogItem.display_order.asc(), SystemCatalogItem.name.asc())
        .all()
    )


def get_catalog_item_by_id(db: Session, item_id) -> SystemCatalogItem | None:
    return db.get(SystemCatalogItem, item_id)


def get_catalog_item_by_code(db: Session, catalog_id, code: str) -> SystemCatalogItem | None:
    return (
        db.query(SystemCatalogItem)
        .filter(
            SystemCatalogItem.catalog_id == catalog_id,
            SystemCatalogItem.code == code,
        )
        .first()
    )


def create_catalog_item(
    db: Session,
    catalog_id,
    item_data: SystemCatalogItemCreate,
) -> SystemCatalogItem:
    item = SystemCatalogItem(catalog_id=catalog_id, **item_data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_catalog_item(
    db: Session,
    item: SystemCatalogItem,
    item_data: SystemCatalogItemUpdate,
) -> SystemCatalogItem:
    for key, value in item_data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item
