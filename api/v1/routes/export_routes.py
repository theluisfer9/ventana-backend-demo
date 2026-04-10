"""
Background export jobs — PDF y Excel se generan en background.

Endpoints:
  POST /exports/           → crea job, retorna job_id
  GET  /exports/{job_id}   → status del job
  GET  /exports/{job_id}/download → descarga el archivo
"""
import logging
import os
import threading
import tempfile
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from api.v1.config.database import get_sync_db_pg, PGSyncSessionLocal, get_clickhouse_client
from api.v1.dependencies.auth_dependency import get_current_user
from api.v1.models.user import User
from api.v1.models.export_job import ExportJob, ExportJobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queries/exports", tags=["Exports"])

# Directory for temp export files
_EXPORT_DIR = os.path.join(tempfile.gettempdir(), "ventana_exports")
os.makedirs(_EXPORT_DIR, exist_ok=True)


# ── Schemas ──────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    datasource_id: UUID | None = None
    columns: list[str] = []
    filters: list[dict] = []
    agrupar: bool = False
    formato: str  # "pdf", "excel", "csv"
    group_by: list[str] = []
    aggregations: list[dict] = []
    saved_query_id: UUID | None = None  # If set, export a saved query instead


class ExportJobOut(BaseModel):
    job_id: UUID
    status: str
    filename: str | None = None
    error: str | None = None
    created_at: str | None = None


# ── Background worker ────────────────────────────────────────────────

def _run_export_job(job_id: UUID, user_id: UUID, body: dict):
    """Runs in a background thread. Creates its own DB session."""
    db = PGSyncSessionLocal()
    try:
        job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
        if not job:
            return

        # Import here to avoid circular imports
        from api.v1.models.data_source import DataSource, RoleDataSource
        from api.v1.models.user import User as UserModel
        from sqlalchemy.orm import joinedload

        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            job.status = ExportJobStatus.ERROR
            job.error = "Usuario no encontrado"
            db.commit()
            return

        from api.v1.models.data_source import DataSource, SavedQuery
        from api.v1.services.query_engine.engine import execute_query_export
        from api.v1.services.query_engine.validators import (
            validate_columns, validate_filters, validate_group_by, validate_aggregations,
        )
        from api.v1.routes.query_routes import _ensure_geo_columns

        formato = body["formato"]
        saved_query_id = body.get("saved_query_id")
        report_title = "Consulta"

        # Resolve datasource, columns, filters from saved query or from body
        if saved_query_id:
            sq = (
                db.query(SavedQuery)
                .options(joinedload(SavedQuery.data_source).joinedload(DataSource.columns_def))
                .filter(SavedQuery.id == saved_query_id)
                .first()
            )
            if not sq:
                job.status = ExportJobStatus.ERROR
                job.error = "Consulta guardada no encontrada"
                db.commit()
                return
            ds = sq.data_source
            columns = sq.selected_columns or []
            filters = sq.filters or []
            group_by = sq.group_by or []
            aggregations = sq.aggregations or []
            agrupar = sq.agrupar
            if sq.name:
                report_title = sq.name
        else:
            ds = (
                db.query(DataSource)
                .options(joinedload(DataSource.columns_def))
                .filter(DataSource.id == body["datasource_id"], DataSource.is_active == True)
                .first()
            )
            if not ds:
                job.status = ExportJobStatus.ERROR
                job.error = "DataSource no encontrado"
                db.commit()
                return
            columns = body["columns"]
            agrupar = body.get("agrupar", False)
            filters = body.get("filters", [])
            group_by = body.get("group_by", [])
            aggregations = body.get("aggregations", [])
            if ds.name:
                report_title = ds.name

        if agrupar:
            columns = _ensure_geo_columns(columns, ds.columns_def)

        # Para PDF, incluir 'familia' si existe en el datasource
        if formato == "pdf":
            col_names = {c.column_name for c in ds.columns_def}
            if "familia" in col_names and "familia" not in columns:
                columns.append("familia")

        validated_cols = validate_columns(columns, ds.columns_def)
        validate_filters(filters, ds.columns_def)
        if group_by:
            validate_group_by(group_by, ds.columns_def)
        if aggregations:
            validate_aggregations(aggregations, ds.columns_def)

        # Row limits
        limits = {"csv": 2_000_000_000, "excel": 1_000_000, "pdf": 50_000}
        row_limit = limits.get(formato, 50_000)

        client = get_clickhouse_client()
        rows = execute_query_export(
            client, ds, validated_cols, filters, row_limit,
            group_by=group_by or None,
            aggregations=aggregations or None,
        )

        # Build columns_meta from validated DataSourceColumn objects
        columns_meta = [
            {
                "column_name": col.column_name,
                "label": col.label,
                "data_type": col.data_type.value if col.data_type else "TEXT",
            }
            for col in validated_cols
        ]

        # Generate file
        from api.v1.services.query_engine.export import (
            generate_pdf_zip, generate_pdf_chunked_zip,
            generate_excel_zip, generate_excel_chunked_zip,
            generate_csv_streaming,
        )

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        if formato == "csv":
            # CSV: write chunks to file
            filename = f"consulta_{ts}.csv"
            filepath = os.path.join(_EXPORT_DIR, f"{job_id}.csv")
            with open(filepath, "wb") as f:
                for chunk in generate_csv_streaming(rows, columns_meta):
                    f.write(chunk)
            media_type = "text/csv; charset=utf-8"

        elif formato == "excel":
            filename = f"consulta_{ts}.zip"
            filepath = os.path.join(_EXPORT_DIR, f"{job_id}.zip")
            if agrupar:
                buf = generate_excel_zip(rows, columns_meta, title=report_title)
            else:
                buf = generate_excel_chunked_zip(rows, columns_meta, title=report_title)
            with open(filepath, "wb") as f:
                f.write(buf.getvalue())
            media_type = "application/zip"

        elif formato == "pdf":
            filename = f"consulta_{ts}.zip"
            filepath = os.path.join(_EXPORT_DIR, f"{job_id}.zip")
            if agrupar:
                buf = generate_pdf_zip(rows, columns_meta, title=report_title)
            else:
                buf = generate_pdf_chunked_zip(rows, columns_meta, title=report_title)
            with open(filepath, "wb") as f:
                f.write(buf.getvalue())
            media_type = "application/zip"
        else:
            job.status = ExportJobStatus.ERROR
            job.error = f"Formato no soportado: {formato}"
            db.commit()
            return

        # Mark done
        job.status = ExportJobStatus.DONE
        job.filename = filename
        job.file_path = filepath
        job.media_type = media_type
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info("Export job %s completed: %s (%d rows)", job_id, filename, len(rows))

        # Registrar audit event de la exportacion
        try:
            from api.v1.services.audit import (
                log_audit_event,
                build_query_audit_payload,
                build_query_audit_summary,
            )

            payload_summary = build_query_audit_payload(
                datasource=ds,
                selected_columns=[c.column_name for c in validated_cols],
                filters=filters,
                group_by=group_by or [],
                aggregations=aggregations or [],
                agrupar=agrupar,
                format=formato,
            )
            log_audit_event(
                db,
                event_type="export",
                module="query_builder",
                action=f"export_{formato}",
                user=user,
                request=None,
                resource_type="datasource",
                resource_id=str(ds.id),
                payload_summary=payload_summary,
                summary_text=build_query_audit_summary(
                    payload_summary,
                    event_type="export",
                    result_count=len(rows),
                ),
                result_count=len(rows),
            )
        except Exception:
            logger.exception("Failed to log audit for export job %s", job_id)

    except Exception as e:
        logger.exception("Export job %s failed", job_id)
        try:
            job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
            if job:
                job.status = ExportJobStatus.ERROR
                job.error = str(e)[:500]
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/", response_model=ExportJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_export_job(
    body: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db_pg),
):
    """Crea un job de exportacion en background. Retorna job_id inmediatamente."""
    if body.formato not in ("pdf", "excel", "csv"):
        raise HTTPException(status_code=400, detail="Formato debe ser pdf, excel o csv")

    job = ExportJob(
        user_id=current_user.id,
        formato=body.formato,
        status=ExportJobStatus.PROCESSING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Launch background thread
    thread = threading.Thread(
        target=_run_export_job,
        args=(job.id, current_user.id, body.model_dump(mode="json")),
        daemon=True,
    )
    thread.start()

    return ExportJobOut(
        job_id=job.id,
        status=job.status.value,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


@router.get("/{job_id}", response_model=ExportJobOut)
def get_export_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db_pg),
):
    """Consulta el estado de un job de exportacion."""
    job = db.query(ExportJob).filter(
        ExportJob.id == job_id,
        ExportJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    return ExportJobOut(
        job_id=job.id,
        status=job.status.value,
        filename=job.filename,
        error=job.error,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


@router.get("/{job_id}/download")
def download_export(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db_pg),
):
    """Descarga el archivo generado por un job completado."""
    job = db.query(ExportJob).filter(
        ExportJob.id == job_id,
        ExportJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if job.status != ExportJobStatus.DONE:
        raise HTTPException(status_code=400, detail=f"Job en estado: {job.status.value}")

    if not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(
        path=job.file_path,
        filename=job.filename,
        media_type=job.media_type or "application/octet-stream",
    )
