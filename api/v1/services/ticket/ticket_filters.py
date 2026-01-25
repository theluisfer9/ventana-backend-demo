from typing import Any, Callable
from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from api.utils import convertir_date_a_datetime
from api.v1.models.ticket import Ticket
from api.v1.schemas.ticket import TicketFilters

TEXT_SEARCH_COLS: tuple = (Ticket.title, Ticket.description)

FilterBuilder = Callable[[Any], ColumnElement[bool] | None]

FILTERS: dict[str, FilterBuilder] = {
    "estado": lambda v: Ticket.status.in_(v) if v else None,
    "creado_desde": lambda v: Ticket.created_at >= v,
    "creado_hasta": lambda v: Ticket.created_at < convertir_date_a_datetime(v),
    "buscar": lambda v: (
        or_(*[c.ilike(f"%{v}%") for c in TEXT_SEARCH_COLS]) if v else None
    ),
}


def compile_ticket_filters(filters: TicketFilters) -> list[ColumnElement[bool]]:
    data = filters.model_dump(exclude_none=True)
    conds: list[ColumnElement[bool]] = []
    for key, value in data.items():
        builder = FILTERS.get(key)
        if not builder:
            continue
        expr = builder(value)
        if expr is not None:
            conds.append(expr)
    return conds
