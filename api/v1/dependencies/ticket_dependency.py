from fastapi import Query
from typing_extensions import Annotated
from api.v1.schemas.ticket import TicketFilters
from api.v1.models.ticket import TicketStatus
from typing import Optional, List
from datetime import date

def filters_dep(
    estado: Annotated[
        Optional[List[TicketStatus]],
        Query()
    ] = None,
    creado_desde: Annotated[
        Optional[date],
        Query(description="Fecha (>=) YYYY-MM-DD")
    ] = None,
    creado_hasta: Annotated[
        Optional[date],
        Query(description="Fecha (<=) YYYY-MM-DD")
    ] = None,
    buscar: Annotated[
        Optional[str],
        Query(description="Texto a buscar en el título o descripción")
    ] = None,
) -> TicketFilters:
    return TicketFilters(
        estado=estado,
        creado_desde=creado_desde,
        creado_hasta=creado_hasta,
        buscar=buscar,
    )