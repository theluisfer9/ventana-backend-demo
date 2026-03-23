from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from api.v1.auth.permissions import PermissionCode
from api.v1.config.database import get_sync_db_pg
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.models.audit_event import AuditEvent
from api.v1.models.data_source import DataSource, SavedQuery
from api.v1.models.user import User
from api.v1.schemas.audit_event import AuditEventOut

router = APIRouter(prefix="/audit-events", tags=["Auditoría"])


def _build_resource_labels(db: Session, events: list[AuditEvent]) -> dict[tuple[str | None, str | None], str]:
    labels: dict[tuple[str | None, str | None], str] = {}

    datasource_ids = [
        event.resource_id
        for event in events
        if event.resource_type == "datasource" and event.resource_id
    ]
    if datasource_ids:
        rows = (
            db.query(DataSource.id, DataSource.name)
            .filter(DataSource.id.in_(datasource_ids))
            .all()
        )
        for ds_id, name in rows:
            labels[("datasource", str(ds_id))] = f"Datasource: {name}"

    saved_query_ids = [
        event.resource_id
        for event in events
        if event.resource_type == "saved_query" and event.resource_id
    ]
    if saved_query_ids:
        rows = (
            db.query(SavedQuery.id, SavedQuery.name)
            .filter(SavedQuery.id.in_(saved_query_ids))
            .all()
        )
        for query_id, name in rows:
            labels[("saved_query", str(query_id))] = f"Saved Query: {name}"

    return labels


@router.get("/", response_model=list[AuditEventOut])
def list_audit_events(
    module: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.SYSTEM_AUDIT)),
):
    query = db.query(AuditEvent).options(
        joinedload(AuditEvent.user),
        joinedload(AuditEvent.institution),
    )
    if module:
        query = query.filter(AuditEvent.module == module)
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    events = query.order_by(AuditEvent.created_at.desc()).limit(limit).all()
    resource_labels = _build_resource_labels(db, events)

    for event in events:
        event.resource_label = resource_labels.get(
            (event.resource_type, event.resource_id),
            event.resource_type,
        )

    return events
