from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.v1.config.database import get_ch_client
from api.v1.config.institutional_presets import INSTITUTIONAL_PRESETS
from api.v1.dependencies.auth_dependency import get_current_active_user
from api.v1.dependencies.consulta_dependency import consulta_filters_dep
from api.v1.models.user import User
from api.v1.schemas.consulta import (
    ConsultaFilters,
    PaginatedConsulta,
    ConsultaDashboardStats,
    ConsultaCatalogosResponse,
    CatalogoItem,
    InstitutionPresetInfo,
    IntervencionCount,
)
from api.v1.services.consulta.queries import (
    query_consulta_lista,
    query_consulta_detalle,
    query_consulta_dashboard,
    query_consulta_catalogos,
)
from api.v1.services.consulta.mappers import (
    row_to_beneficio_resumen,
    row_to_beneficio_detalle,
)

router = APIRouter(prefix="/consulta", tags=["Consulta Institucional"])


def _get_preset(user: User) -> tuple[str, dict]:
    """
    Lee institution.code del usuario y devuelve el preset correspondiente.
    Raises 403 si el usuario no tiene institucion o no existe preset.
    """
    institution = user.institution
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene institucion asignada",
        )
    code = institution.code
    preset = INSTITUTIONAL_PRESETS.get(code)
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No existe configuracion de consulta para la institucion {code}",
        )
    return code, preset


def _extract_intervention_filters(request: Request, preset: dict) -> dict:
    """Extrae filtros de intervenciones de los query params segun el preset."""
    intervention_filters = {}
    for col in preset["intervention_columns"]:
        val = request.query_params.get(col)
        if val is not None and val.lower() in ("true", "1", "yes"):
            intervention_filters[col] = True
    return intervention_filters


@router.get("/preset", response_model=InstitutionPresetInfo)
def get_preset_info(
    current_user: User = Depends(get_current_active_user),
):
    """Devuelve la configuracion del preset institucional del usuario."""
    code, preset = _get_preset(current_user)
    return InstitutionPresetInfo(
        institution_code=code,
        name=preset["name"],
        table=preset["table"],
        columns=preset["columns"],
        intervention_columns=preset["intervention_columns"],
        allowed_filters=preset["allowed_filters"],
        labels=preset["labels"],
    )


@router.get("/dashboard", response_model=ConsultaDashboardStats)
def dashboard(
    current_user: User = Depends(get_current_active_user),
    client=Depends(get_ch_client),
):
    """Estadisticas del dashboard institucional."""
    code, preset = _get_preset(current_user)
    interv_cols = preset["intervention_columns"]
    raw = query_consulta_dashboard(client, preset["base_filter"], interv_cols)

    por_intervencion = []
    intervenciones = raw.get("intervenciones", {})
    for col in interv_cols:
        label = preset["labels"].get(col, col)
        por_intervencion.append(
            IntervencionCount(intervencion=label, cantidad=int(intervenciones.get(col, 0)))
        )

    return ConsultaDashboardStats(
        total_hogares=raw.get("total_hogares", 0),
        departamentos_cubiertos=raw.get("total_departamentos", 0),
        municipios_cubiertos=raw.get("total_municipios", 0),
        total_personas=raw.get("total_personas", 0),
        por_departamento=[
            {"departamento": d["departamento"], "codigo": d["departamento_codigo"], "cantidad": d["cantidad_hogares"]}
            for d in raw.get("top_departamentos", [])
        ],
        por_intervencion=por_intervencion,
    )


@router.get("/catalogos", response_model=ConsultaCatalogosResponse)
def catalogos(
    current_user: User = Depends(get_current_active_user),
    client=Depends(get_ch_client),
):
    """Obtener catalogos de filtros scoped a la institucion."""
    code, preset = _get_preset(current_user)
    raw = query_consulta_catalogos(client, preset["base_filter"])
    return ConsultaCatalogosResponse(
        departamentos=[
            CatalogoItem(code=d["codigo"], name=d["nombre"])
            for d in raw["departamentos"]
        ],
    )


@router.get("/", response_model=PaginatedConsulta)
def listar(
    request: Request,
    filters: ConsultaFilters = Depends(consulta_filters_dep),
    offset: int = Query(0, ge=0, description="Offset para paginacion"),
    limit: int = Query(20, ge=1, le=100, description="Limite de resultados"),
    current_user: User = Depends(get_current_active_user),
    client=Depends(get_ch_client),
):
    """Lista paginada de hogares con filtros institucionales."""
    code, preset = _get_preset(current_user)
    interv_cols = preset["intervention_columns"]

    filter_kwargs = filters.model_dump(exclude_none=True)
    filter_kwargs.update(_extract_intervention_filters(request, preset))

    rows, total = query_consulta_lista(
        client, preset["base_filter"], interv_cols,
        offset=offset, limit=limit, **filter_kwargs
    )
    items = [row_to_beneficio_resumen(r, interv_cols) for r in rows]
    return PaginatedConsulta(items=items, total=total, offset=offset, limit=limit)


@router.get("/{hogar_id}")
def detalle(
    hogar_id: int,
    current_user: User = Depends(get_current_active_user),
    client=Depends(get_ch_client),
):
    """Detalle de un hogar scoped a la institucion."""
    code, preset = _get_preset(current_user)
    interv_cols = preset["intervention_columns"]
    result = query_consulta_detalle(
        client, preset["base_filter"], interv_cols, hogar_id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hogar no encontrado en el ambito de su institucion",
        )
    return row_to_beneficio_detalle(result, interv_cols)
