from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from api.v1.config.database import get_ch_client, get_sync_db_pg
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.dependencies.beneficiario_dependency import beneficiario_filters_dep
from api.v1.auth.permissions import PermissionCode
from api.v1.schemas.persona import PersonaResumen
from api.v1.schemas.vivienda import ViviendaDetalle
from api.v1.schemas.beneficiario import (
    BeneficiarioFilters,
    BeneficiarioDetalle,
    BeneficiarioListadoComunidadItem,
    BeneficiarioResumen,
    BeneficiarioStats,
    DashboardStats,
    PaginatedBeneficiarios,
    CatalogosResponse,
    CatalogoItem,
    MunicipioItem,
    MunicipioActualizadoItem,
    MunicipiosActualizadosResponse,
    LugarPobladoItem,
    ComunidadListadoGroup,
    ListadoMunicipioComunidadResponse,
    MunicipioListadoGroup,
)
from api.v1.services.rsh.queries import (
    query_beneficiarios_lista,
    query_beneficiario_detalle,
    query_listado_municipio_comunidad,
    query_stats,
    query_dashboard,
    query_catalogos,
    query_municipios,
    query_municipios_actualizados,
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
from api.v1.services.beneficiario.export import (
    EXCEL_ZIP_THRESHOLD,
    generate_csv,
    generate_excel,
    generate_excel_grouped_zip,
    generate_pdf,
)
from api.v1.services.user_checkpoint import (
    get_user_query_checkpoint,
    upsert_user_query_checkpoint,
)

router = APIRouter(prefix="/beneficiarios", tags=["Beneficiarios"])


def _build_listado_municipio_comunidad(rows: list[dict]) -> ListadoMunicipioComunidadResponse:
    municipios: dict[tuple[str, str], dict] = {}
    total_comunidades = 0

    for row in rows:
        municipio_key = (str(row.get("departamento_codigo", "")).strip(), str(row.get("municipio_codigo", "")).strip())
        comunidad = str(row.get("comunidad") or row.get("lugar_poblado") or "").strip()

        if municipio_key not in municipios:
            municipios[municipio_key] = {
                "departamento": str(row.get("departamento", "")).strip(),
                "departamento_codigo": str(row.get("departamento_codigo", "")).strip(),
                "municipio": str(row.get("municipio", "")).strip(),
                "municipio_codigo": str(row.get("municipio_codigo", "")).strip(),
                "comunidades": {},
            }

        comunidades = municipios[municipio_key]["comunidades"]
        if comunidad not in comunidades:
            comunidades[comunidad] = []
            total_comunidades += 1

        resumen = row_to_beneficiario_resumen(row)
        comunidades[comunidad].append(BeneficiarioListadoComunidadItem(**resumen, comunidad=comunidad))

    items = []
    total_beneficiarios = 0

    for municipio in municipios.values():
        comunidades = []
        municipio_total = 0
        for comunidad, beneficiarios in municipio["comunidades"].items():
            municipio_total += len(beneficiarios)
            comunidades.append(
                ComunidadListadoGroup(
                    comunidad=comunidad,
                    total_beneficiarios=len(beneficiarios),
                    beneficiarios=beneficiarios,
                )
            )

        total_beneficiarios += municipio_total
        items.append(
            MunicipioListadoGroup(
                departamento=municipio["departamento"],
                departamento_codigo=municipio["departamento_codigo"],
                municipio=municipio["municipio"],
                municipio_codigo=municipio["municipio_codigo"],
                total_beneficiarios=municipio_total,
                comunidades=comunidades,
            )
        )

    return ListadoMunicipioComunidadResponse(
        total_municipios=len(items),
        total_comunidades=total_comunidades,
        total_beneficiarios=total_beneficiarios,
        items=items,
    )


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


@router.get("/municipios/actualizados", response_model=MunicipiosActualizadosResponse)
def municipios_actualizados(
    db=Depends(get_sync_db_pg),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Obtiene municipios actualizados desde la última consulta registrada del usuario."""
    module = "beneficiarios"
    scope = "municipios_actualizados"
    checked_at = datetime.now(timezone.utc)

    checkpoint = get_user_query_checkpoint(db, current_user.id, module, scope)
    last_checked_at = checkpoint.last_checked_at if checkpoint else None

    items = []
    if last_checked_at is not None:
        raw = query_municipios_actualizados(client, last_checked_at)
        items = [
            MunicipioActualizadoItem(
                code=m["codigo"],
                name=m["nombre"],
                departamento=m["departamento"],
                departamento_codigo=m["departamento_codigo"],
                fase_estado=m["fase_estado"],
                ultima_actualizacion=m["ultima_actualizacion"],
            )
            for m in raw
        ]

    upsert_user_query_checkpoint(db, current_user.id, module, scope, checked_at)

    return MunicipiosActualizadosResponse(
        last_checked_at=last_checked_at,
        checked_at=checked_at,
        total=len(items),
        items=items,
    )


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


@router.get("/listado/municipio-comunidad", response_model=ListadoMunicipioComunidadResponse)
def listado_municipio_comunidad(
    filters: BeneficiarioFilters = Depends(beneficiario_filters_dep),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_READ)),
    client=Depends(get_ch_client),
):
    """Listado agrupado por municipio y lugar poblado para impresión/exportación."""
    filter_kwargs = filters.model_dump(exclude_none=True)
    rows = query_listado_municipio_comunidad(client, **filter_kwargs)
    return _build_listado_municipio_comunidad(rows)


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
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if len(items) > EXCEL_ZIP_THRESHOLD:
        buf = generate_excel_grouped_zip(items)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="beneficiarios_{ts}.zip"'},
        )

    buf = generate_excel(items)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="beneficiarios_{ts}.xlsx"'},
    )


@router.get("/export/csv")
def export_csv(
    filters: BeneficiarioFilters = Depends(beneficiario_filters_dep),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_EXPORT)),
    client=Depends(get_ch_client),
):
    """Exportar beneficiarios filtrados a CSV."""
    filter_kwargs = filters.model_dump(exclude_none=True)
    rows, _ = query_beneficiarios_lista(client, offset=0, limit=10000, **filter_kwargs)
    items = [row_to_beneficiario_resumen(r) for r in rows]
    buf = generate_csv(items)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        buf,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="beneficiarios_{ts}.csv"'},
    )


@router.get("/export/pdf")
def export_pdf(
    filters: BeneficiarioFilters = Depends(beneficiario_filters_dep),
    current_user=Depends(RequirePermission(PermissionCode.BENEFICIARIES_EXPORT)),
    client=Depends(get_ch_client),
):
    """Exportar beneficiarios filtrados a PDF."""
    filter_kwargs = filters.model_dump(exclude_none=True)
    rows = query_listado_municipio_comunidad(client, **filter_kwargs)
    items = [row_to_beneficiario_resumen(r) | {"comunidad": r.get("comunidad", "")} for r in rows]
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
