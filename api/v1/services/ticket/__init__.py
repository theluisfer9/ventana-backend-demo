from sqlalchemy import select, func
from sqlalchemy.orm import Session
from api.v1.models.ticket import Ticket
from api.v1.schemas.ticket import TicketCreate, TicketUpdate, TicketFilters
from typing import Optional
from api.v1.services.ticket.ticket_filters import compile_ticket_filters


def get_all_tickets(
    db: Session,
    offset: int,
    limit: int,
    filters: TicketFilters,
) -> tuple[list[Ticket], int]:

    conds = compile_ticket_filters(filters)

    base_query = select(Ticket).where(*conds).order_by(Ticket.id)

    items = list(
        db.execute(base_query.offset(offset).limit(limit)).scalars().all()
    )

    count_stmt = select(func.count()).select_from(
        select(Ticket.id).where(*conds).subquery()
    )
    total: int = db.execute(count_stmt).scalar_one()

    return items, total


def generate_ticket(db: Session, ticket: TicketCreate) -> Optional[Ticket]:
    new_ticket = Ticket(**ticket.model_dump())
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket


def get_ticket_by_id(db: Session, ticket_id: int) -> Optional[Ticket]:
    return db.get(Ticket, ticket_id)


def update_ticket_by_id(
    db: Session, ticket_id: int, update_data: TicketUpdate
) -> Optional[Ticket]:
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(ticket, key, value)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(ticket)
    return ticket
