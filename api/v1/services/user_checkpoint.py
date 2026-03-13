from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.v1.models.user_query_checkpoint import UserQueryCheckpoint


def get_user_query_checkpoint(
    db: Session,
    user_id,
    module: str,
    scope: str,
) -> UserQueryCheckpoint | None:
    stmt = select(UserQueryCheckpoint).where(
        UserQueryCheckpoint.user_id == user_id,
        UserQueryCheckpoint.module == module,
        UserQueryCheckpoint.scope == scope,
    )
    return db.execute(stmt).scalar_one_or_none()


def upsert_user_query_checkpoint(
    db: Session,
    user_id,
    module: str,
    scope: str,
    checked_at: datetime,
) -> UserQueryCheckpoint:
    checkpoint = get_user_query_checkpoint(db, user_id, module, scope)
    if checkpoint is None:
        checkpoint = UserQueryCheckpoint(
            user_id=user_id,
            module=module,
            scope=scope,
            last_checked_at=checked_at,
        )
        db.add(checkpoint)
    else:
        checkpoint.last_checked_at = checked_at

    db.commit()
    db.refresh(checkpoint)
    return checkpoint
