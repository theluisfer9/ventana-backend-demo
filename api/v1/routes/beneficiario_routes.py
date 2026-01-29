from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from typing import List

from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.dependencies.beneficiario_dependency import beneficiario_filters_dep
from api.v1.auth.permissions import PermissionCode
from api.v1.schemas.beneficiario import (
    BeneficiarioFilters,
    BeneficiarioOut,
    BeneficiarioResumen,
    BeneficiarioStats,
    DashboardStats,
    PaginatedBeneficiarios,
    CatalogosResponse,
    MunicipioOut,
)
from api.v1.services.beneficiario import (
    list_beneficiarios,
    get_beneficiario_by_id,
    get_beneficiario_stats,
    get_dashboard_stats,
    get_catalogos,
    get_municipios_by_departamento,
    get_filtered_enriched,
)
from api.v1.services.beneficiario.export import generate_excel, generate_pdf

router = APIRouter(prefix="/beneficiarios", tags=["Beneficiarios"])


@router.get("/catalogos", response_model=CatalogosResponse)
def catalogos(
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
):
    """Obtener todos los catalogos de filtros."""
    return get_catalogos()


@router.get("/catalogos/municipios", response_model=List[MunicipioOut])
def municipios_por_departamento(
    departamento_code: str = Query(..., description="Codigo de departamento"),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
):
    """Obtener municipios por departamento (cascada)."""
    return get_municipios_by_departamento(departamento_code)


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
):
    """Estadisticas de resumen para el dashboard."""
    return get_dashboard_stats()


@router.get("/stats", response_model=BeneficiarioStats)
def stats(
    filters: BeneficiarioFilters = Depends(beneficiario_filters_dep),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
):
    """Estadisticas agregadas segun filtros aplicados."""
    return get_beneficiario_stats(filters)


@router.get("/export/excel")
def export_excel(
    filters: BeneficiarioFilters = Depends(beneficiario_filters_dep),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_EXPORT)),
):
    """Exportar beneficiarios filtrados a Excel (.xlsx)."""
    enriched = get_filtered_enriched(filters)
    buf = generate_excel(enriched)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="beneficiarios_{ts}.xlsx"'},
    )


@router.get("/export/pdf")
def export_pdf(
    filters: BeneficiarioFilters = Depends(beneficiario_filters_dep),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_EXPORT)),
):
    """Exportar beneficiarios filtrados a PDF."""
    enriched = get_filtered_enriched(filters)
    buf = generate_pdf(enriched)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="beneficiarios_{ts}.pdf"'},
    )


@router.get("/", response_model=PaginatedBeneficiarios)
def listar(
    filters: BeneficiarioFilters = Depends(beneficiario_filters_dep),
    offset: int = Query(0, ge=0, description="Offset para paginacion"),
    limit: int = Query(20, ge=1, le=100, description="Limite de resultados"),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
):
    """Lista paginada de beneficiarios con filtros."""
    return list_beneficiarios(filters, offset=offset, limit=limit)


@router.get("/{beneficiario_id}", response_model=BeneficiarioOut)
def detalle(
    beneficiario_id: int,
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
):
    """Detalle de un beneficiario por ID."""
    result = get_beneficiario_by_id(beneficiario_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beneficiario no encontrado",
        )
    return result
