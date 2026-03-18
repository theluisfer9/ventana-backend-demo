from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.v1.config.database import get_ch_client
from api.v1.config.institutional_presets import INSTITUTIONAL_PRESETS
from api.v1.dependencies.consulta_dependency import consulta_filters_dep
from api.v1.dependencies.institution_api_token_dependency import get_current_api_institution
from api.v1.models.institution import Institution
from api.v1.schemas.consulta import (
    ConsultaFilters,
    PaginatedConsulta,
    InstitutionPresetInfo,
)
from api.v1.services.consulta.queries import query_consulta_lista
from api.v1.services.consulta.mappers import row_to_beneficio_resumen

router = APIRouter(prefix="/integration/consulta", tags=["Integración API"])


def _get_preset_for_institution(institution: Institution) -> tuple[str, dict]:
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institución no válida",
        )
    preset = INSTITUTIONAL_PRESETS.get(institution.code)
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No existe configuración de consulta para la institución {institution.code}",
        )
    return institution.code, preset


def _extract_intervention_filters(request: Request, preset: dict) -> dict:
    intervention_filters = {}
    for col in preset["intervention_columns"]:
        val = request.query_params.get(col)
        if val is not None and val.lower() in ("true", "1", "yes"):
            intervention_filters[col] = True
    return intervention_filters


@router.get("/preset", response_model=InstitutionPresetInfo)
def get_integration_preset(
    institution: Institution = Depends(get_current_api_institution),
):
    code, preset = _get_preset_for_institution(institution)
    return InstitutionPresetInfo(
        institution_code=code,
        name=preset["name"],
        table=preset["table"],
        columns=preset["columns"],
        intervention_columns=preset["intervention_columns"],
        allowed_filters=preset["allowed_filters"],
        labels=preset["labels"],
    )


@router.get("/", response_model=PaginatedConsulta)
def listar_integracion(
    request: Request,
    filters: ConsultaFilters = Depends(consulta_filters_dep),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados"),
    institution: Institution = Depends(get_current_api_institution),
    client=Depends(get_ch_client),
):
    _, preset = _get_preset_for_institution(institution)
    interv_cols = preset["intervention_columns"]

    filter_kwargs = filters.model_dump(exclude_none=True)
    filter_kwargs.update(_extract_intervention_filters(request, preset))

    rows, total = query_consulta_lista(
        client,
        preset["base_filter_columns"],
        preset["base_filter_logic"],
        interv_cols,
        offset=offset,
        limit=limit,
        **filter_kwargs,
    )
    items = [row_to_beneficio_resumen(r, interv_cols) for r in rows]
    return PaginatedConsulta(items=items, total=total, offset=offset, limit=limit)
