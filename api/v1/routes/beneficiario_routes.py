from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from api.v1.config.database import get_ch_client
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.dependencies.beneficiario_dependency import beneficiario_filters_dep
from api.v1.auth.permissions import PermissionCode
from api.v1.schemas.persona import PersonaResumen
from api.v1.schemas.vivienda import ViviendaDetalle
from api.v1.schemas.beneficiario import (
    BeneficiarioFilters,
    BeneficiarioDetalle,
    BeneficiarioResumen,
    BeneficiarioStats,
    DashboardStats,
    PaginatedBeneficiarios,
    CatalogosResponse,
    CatalogoItem,
    MunicipioItem,
    LugarPobladoItem,
)
from api.v1.services.rsh.queries import (
    query_beneficiarios_lista,
    query_beneficiario_detalle,
    query_stats,
    query_dashboard,
    query_catalogos,
    query_municipios,
    query_lugares_poblados,
    query_personas_hogar,
    query_vivienda_hogar,
)
from api.v1.services.rsh.mappers import (
    row_to_beneficiario_resumen,
    row_to_beneficiario_detalle,
    row_to_persona,
    row_to_vivienda,
)
from api.v1.services.beneficiario.export import generate_excel, generate_pdf

router = APIRouter(prefix="/beneficiarios", tags=["Beneficiarios"])


@router.get("/catalogos")
def catalogos(
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Obtener catalogos de filtros desde datos RSH."""
    raw = query_catalogos(client)
    return CatalogosResponse(
        departamentos=[
            CatalogoItem(code=d["codigo"], name=d["nombre"])
            for d in raw["departamentos"]
        ],
        clasificaciones_ipm=raw["clasificaciones_ipm"],
        clasificaciones_pmt=raw["clasificaciones_pmt"],
        clasificaciones_nbi=raw["clasificaciones_nbi"],
        areas=raw["areas"],
        niveles_inseguridad=raw["niveles_inseguridad"],
        fases=raw["fases"],
        comunidades_linguisticas=raw["comunidades_linguisticas"],
        pueblos=raw["pueblos"],
        fuentes_agua=raw.get("fuentes_agua", []),
        tipos_sanitario=raw.get("tipos_sanitario", []),
        tipos_alumbrado=raw.get("tipos_alumbrado", []),
        combustibles_cocina=raw.get("combustibles_cocina", []),
    )


@router.get("/catalogos/municipios")
def municipios_por_departamento(
    departamento_codigo: str = Query(..., description="Codigo de departamento"),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Obtener municipios por departamento (cascada)."""
    raw = query_municipios(client, departamento_codigo)
    return [MunicipioItem(code=m["codigo"], name=m["nombre"]) for m in raw]


@router.get("/catalogos/lugares-poblados")
def lugares_poblados_por_municipio(
    municipio_codigo: str = Query(..., description="Codigo de municipio"),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Obtener lugares poblados por municipio (cascada)."""
    raw = query_lugares_poblados(client, municipio_codigo)
    return [LugarPobladoItem(code=lp["codigo"], name=lp["nombre"]) for lp in raw]


@router.get("/dashboard")
def dashboard(
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Estadisticas globales para el dashboard."""
    raw = query_dashboard(client)
    return DashboardStats(
        total_hogares=raw.get("total_hogares", 0),
        departamentos_cubiertos=raw.get("total_departamentos", 0),
        municipios_cubiertos=raw.get("total_municipios", 0),
        promedio_ipm=float(raw.get("ipm_promedio", 0) or 0),
        total_personas=raw.get("total_personas", 0),
        hogares_pobres=0,  # TODO: add when classification data available
        hogares_no_pobres=0,
        por_departamento=[
            {"departamento": d["departamento"], "codigo": d["departamento_codigo"], "cantidad": d["cantidad_hogares"]}
            for d in raw.get("top_departamentos", [])
        ],
        inseguridad_alimentaria=[
            {"nivel": i["nivel_inseguridad_alimentaria"], "cantidad": i["cantidad_hogares"]}
            for i in raw.get("distribucion_inseguridad_alimentaria", [])
        ],
    )


@router.get("/stats")
def stats(
    filters: BeneficiarioFilters = Depends(beneficiario_filters_dep),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Estadisticas agregadas segun filtros."""
    filter_kwargs = filters.model_dump(exclude_none=True)
    raw = query_stats(client, **filter_kwargs)
    return BeneficiarioStats(
        total=raw.get("total_hogares", 0),
        promedio_ipm=float(raw.get("ipm_promedio", 0) or 0),
        total_mujeres_jefas=raw.get("hogares_jefatura_femenina", 0),
        total_hombres_jefes=raw.get("hogares_jefatura_masculina", 0),
        total_personas=raw.get("total_personas", 0),
        total_hombres=raw.get("total_hombres", 0),
        total_mujeres=raw.get("total_mujeres", 0),
        por_departamento=[
            {"departamento": d["departamento"], "codigo": d["departamento_codigo"], "cantidad": d["cantidad_hogares"]}
            for d in raw.get("distribucion_departamentos", [])
        ],
        por_ipm_clasificacion=[
            {"clasificacion": c["ipm_gt_clasificacion"], "cantidad": c["cantidad_hogares"]}
            for c in raw.get("distribucion_ipm", [])
        ],
    )


@router.get("/export/excel")
def export_excel(
    filters: BeneficiarioFilters = Depends(beneficiario_filters_dep),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_EXPORT)),
    client=Depends(get_ch_client),
):
    """Exportar beneficiarios filtrados a Excel (.xlsx)."""
    filter_kwargs = filters.model_dump(exclude_none=True)
    rows, _ = query_beneficiarios_lista(client, offset=0, limit=10000, **filter_kwargs)
    items = [row_to_beneficiario_resumen(r) for r in rows]
    buf = generate_excel(items)
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
    client=Depends(get_ch_client),
):
    """Exportar beneficiarios filtrados a PDF."""
    filter_kwargs = filters.model_dump(exclude_none=True)
    rows, _ = query_beneficiarios_lista(client, offset=0, limit=5000, **filter_kwargs)
    items = [row_to_beneficiario_resumen(r) for r in rows]
    buf = generate_pdf(items)
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
    client=Depends(get_ch_client),
):
    """Lista paginada de beneficiarios con filtros."""
    filter_kwargs = filters.model_dump(exclude_none=True)
    rows, total = query_beneficiarios_lista(client, offset=offset, limit=limit, **filter_kwargs)
    items = [row_to_beneficiario_resumen(r) for r in rows]
    return PaginatedBeneficiarios(items=items, total=total, offset=offset, limit=limit)


@router.get("/{hogar_id}/personas", response_model=list[PersonaResumen])
def get_personas_hogar(
    hogar_id: int,
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Obtener todas las personas de un hogar."""
    rows = query_personas_hogar(client, hogar_id)
    return [row_to_persona(r) for r in rows]


@router.get("/{hogar_id}/vivienda", response_model=ViviendaDetalle)
def vivienda_hogar(
    hogar_id: int,
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Detalle de vivienda, servicios, bienes y seguridad alimentaria de un hogar."""
    row = query_vivienda_hogar(client, hogar_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vivienda no encontrada",
        )
    return row_to_vivienda(row)


@router.get("/{hogar_id}")
def detalle(
    hogar_id: int,
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Detalle de un hogar por ID."""
    result = query_beneficiario_detalle(client, hogar_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hogar no encontrado",
        )
    return row_to_beneficiario_detalle(result)
