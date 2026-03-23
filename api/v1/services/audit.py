import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from api.v1.models.audit_event import AuditEvent
from api.v1.models.data_source import DataSource, SavedQuery
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
    summary_text: str | None = None,
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
            summary_text=summary_text,
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


def build_query_audit_payload(
    *,
    datasource: DataSource,
    selected_columns: list[str],
    filters: list[dict[str, Any]],
    group_by: list[str] | None = None,
    aggregations: list[dict[str, Any]] | None = None,
    agrupar: bool = True,
    format: str | None = None,
    saved_query: SavedQuery | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "datasource_id": str(datasource.id),
        "datasource_name": datasource.name,
        "selected_columns": selected_columns,
        "filters": filters,
        "group_by": group_by or [],
        "aggregations": aggregations or [],
        "agrupar": agrupar,
    }
    if format:
        payload["format"] = format
    if saved_query is not None:
        payload["query_id"] = str(saved_query.id)
        payload["query_name"] = saved_query.name
    return payload


def build_query_audit_summary(
    payload_summary: dict[str, Any],
    *,
    event_type: str,
    result_count: int | None = None,
) -> str:
    datasource_name = payload_summary.get("datasource_name") or "set de datos"
    selected_columns = payload_summary.get("selected_columns") or []
    filters = payload_summary.get("filters") or []
    query_name = payload_summary.get("query_name")
    export_format = payload_summary.get("format")

    formatted_count = f"{result_count:,}" if result_count is not None else "0"

    if event_type == "export" and export_format:
        if query_name:
            return (
                f'Exportación {str(export_format).upper()} de "{query_name}" '
                f"sobre {datasource_name} con {formatted_count} registros"
            )
        return (
            f"Exportación {str(export_format).upper()} de {datasource_name} "
            f"con {formatted_count} registros"
        )

    return (
        f"Consulta en {datasource_name} con {len(selected_columns)} columnas, "
        f"{len(filters)} filtros y {formatted_count} registros"
    )
