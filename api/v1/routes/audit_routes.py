from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.v1.auth.permissions import PermissionCode
from api.v1.config.database import get_sync_db_pg
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.models.audit_event import AuditEvent
from api.v1.models.user import User
from api.v1.schemas.audit_event import AuditEventOut

router = APIRouter(prefix="/audit-events", tags=["Auditoría"])


@router.get("/", response_model=list[AuditEventOut])
def list_audit_events(
    module: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.SYSTEM_AUDIT)),
):
    query = db.query(AuditEvent)
    if module:
        query = query.filter(AuditEvent.module == module)
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    return query.order_by(AuditEvent.created_at.desc()).limit(limit).all()
