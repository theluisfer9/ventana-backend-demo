from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from api.v1.models.institution import Institution
from api.v1.schemas.institution import InstitutionCreate, InstitutionUpdate


def get_institution_by_id(db: Session, institution_id: UUID) -> Optional[Institution]:
    """Get an institution by ID"""
    return db.get(Institution, institution_id)


def get_institution_by_code(db: Session, code: str) -> Optional[Institution]:
    """Get an institution by code"""
    stmt = select(Institution).where(Institution.code == code)
    return db.execute(stmt).scalar_one_or_none()


def get_all_institutions(db: Session, include_inactive: bool = False) -> List[Institution]:
    """Get all institutions"""
    stmt = select(Institution)
    if not include_inactive:
        stmt = stmt.where(Institution.is_active == True)
    stmt = stmt.order_by(Institution.name)
    return list(db.execute(stmt).scalars().all())


def create_institution(
    db: Session,
    institution_data: InstitutionCreate,
) -> Institution:
    """Create a new institution"""
    institution = Institution(**institution_data.model_dump())
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


def update_institution(
    db: Session,
    institution: Institution,
    update_data: InstitutionUpdate,
) -> Institution:
    """Update an existing institution"""
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(institution, key, value)

    db.commit()
    db.refresh(institution)
    return institution


def delete_institution(db: Session, institution: Institution, soft_delete: bool = True) -> bool:
    """Delete an institution. By default performs soft delete (deactivation)."""
    if soft_delete:
        institution.is_active = False
        db.commit()
    else:
        db.delete(institution)
        db.commit()
    return True
