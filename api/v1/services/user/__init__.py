from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_

from api.v1.models.user import User
from api.v1.schemas.user import UserCreate, UserCreateByAdmin, UserUpdate, UserFilters
from api.v1.auth.password import hash_password


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    """Get a user by ID"""
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get a user by email"""
    stmt = select(User).where(User.email == email)
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get a user by username"""
    stmt = select(User).where(User.username == username)
    return db.execute(stmt).scalar_one_or_none()


def create_user(
    db: Session,
    user_data: UserCreate | UserCreateByAdmin,
    created_by: Optional[UUID] = None,
) -> User:
    """
    Create a new user.
    """
    data = user_data.model_dump(exclude={"password"})

    # Hash password if provided
    password = getattr(user_data, "password", None)
    if password:
        data["password_hash"] = hash_password(password)

    if created_by:
        data["created_by"] = created_by

    user = User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user: User,
    update_data: UserUpdate,
) -> User:
    """
    Update an existing user.
    """
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


def update_user_password(db: Session, user: User, new_password: str) -> User:
    """
    Update user's password.
    """
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User, soft_delete: bool = True) -> bool:
    """
    Delete a user. By default performs soft delete (deactivation).
    """
    if soft_delete:
        user.is_active = False
        db.commit()
    else:
        db.delete(user)
        db.commit()
    return True


def _compile_user_filters(filters: UserFilters) -> list:
    """Compile user filters into SQLAlchemy conditions"""
    conditions = []

    if filters.role_id:
        conditions.append(User.role_id == filters.role_id)

    if filters.institution_id:
        conditions.append(User.institution_id == filters.institution_id)

    if filters.is_active is not None:
        conditions.append(User.is_active == filters.is_active)

    if filters.is_verified is not None:
        conditions.append(User.is_verified == filters.is_verified)

    if filters.search:
        search_term = f"%{filters.search}%"
        conditions.append(
            or_(
                User.email.ilike(search_term),
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
            )
        )

    if filters.created_from:
        conditions.append(User.created_at >= filters.created_from)

    if filters.created_to:
        conditions.append(User.created_at <= filters.created_to)

    return conditions


def get_all_users(
    db: Session,
    offset: int,
    limit: int,
    filters: UserFilters,
) -> Tuple[List[User], int]:
    """
    Get all users with pagination and filters.
    """
    conditions = _compile_user_filters(filters)

    base_query = select(User).where(*conditions).order_by(User.created_at.desc())

    items = list(
        db.execute(base_query.offset(offset).limit(limit)).scalars().all()
    )

    count_stmt = select(func.count()).select_from(
        select(User.id).where(*conditions).subquery()
    )
    total: int = db.execute(count_stmt).scalar_one()

    return items, total


def activate_user(db: Session, user: User) -> User:
    """Activate a user"""
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def verify_user(db: Session, user: User) -> User:
    """Mark user as verified"""
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user
