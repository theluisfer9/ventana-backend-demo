from fastapi import Query
from typing import Optional
from typing_extensions import Annotated

from api.v1.schemas.consulta import ConsultaFilters


def consulta_filters_dep(
    departamento_codigo: Annotated[Optional[str], Query(description="Codigo de departamento")] = None,
    municipio_codigo: Annotated[Optional[str], Query(description="Codigo de municipio")] = None,
    buscar: Annotated[Optional[str], Query(description="Buscar por ID hogar")] = None,
) -> ConsultaFilters:
    return ConsultaFilters(
        departamento_codigo=departamento_codigo,
        municipio_codigo=municipio_codigo,
        buscar=buscar,
    )
