from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.v1.schemas.ticket import TicketCreate, TicketOut, TicketUpdate, TicketFilters
from api.v1.dependencies.ticket_dependency import filters_dep
from api.v1.services.ticket import (
    get_ticket_by_id,
    get_all_tickets,
    generate_ticket,
    update_ticket_by_id,
)
from api.v1.config.database import get_sync_db_pg
from fastapi_pagination import Page
from fastapi_pagination import Params
from fastapi_pagination import create_page

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=TicketOut)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_sync_db_pg)):
    return generate_ticket(db, ticket)


@router.get("/", response_model=Page[TicketOut])
def retrieve_all_tickets(
    db: Session = Depends(get_sync_db_pg),
    params: Params = Depends(),
    filters: TicketFilters = Depends(filters_dep),
):
    offset = (params.page - 1) * params.size
    limit = params.size
    items, total = get_all_tickets(db, offset, limit, filters)
    return create_page(items, total=total, params=params)


@router.get("/{ticket_id}", response_model=TicketOut)
def retrieve_a_ticket_by_id(
    ticket_id: int, db: Session = Depends(get_sync_db_pg)
):
    ticket = get_ticket_by_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


@router.put("/{ticket_id}", response_model=TicketOut)
def update_a_ticket_by_id(
    ticket_id: int, ticket: TicketUpdate, db: Session = Depends(get_sync_db_pg)
):
    updated = update_ticket_by_id(db, ticket_id, ticket)
    if updated is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return updated
