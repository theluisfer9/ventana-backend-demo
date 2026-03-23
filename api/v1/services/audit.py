import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from api.v1.models.audit_event import AuditEvent
from api.v1.models.user import User

logger = logging.getLogger(__name__)


def log_audit_event(
    db: Session,
    *,
    event_type: str,
    module: str,
    action: str,
    user: User | None = None,
    request: Request | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    payload_summary: dict[str, Any] | None = None,
    query_params: dict[str, Any] | None = None,
    result_count: int | None = None,
    status: str = "success",
) -> AuditEvent | None:
    try:
        if request is not None:
            request_query_params = dict(request.query_params)
            request_method = request.method
            request_path = request.url.path
        else:
            request_query_params = {}
            request_method = None
            request_path = None

        audit_event = AuditEvent(
            event_type=event_type,
            module=module,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user.id if user else None,
            institution_id=user.institution_id if user else None,
            request_method=request_method,
            request_path=request_path,
            query_params=query_params if query_params is not None else request_query_params,
            payload_summary=payload_summary or {},
            result_count=result_count,
            status=status,
        )
        db.add(audit_event)
        db.commit()
        db.refresh(audit_event)
        return audit_event
    except Exception:
        db.rollback()
        logger.exception("No se pudo persistir el evento de auditoría")
        return None
