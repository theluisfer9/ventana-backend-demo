from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from api.v1.models.ticket import TicketStatus

class TicketCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None

class TicketFilters(BaseModel):
    estado: Optional[List[TicketStatus]] = None
    creado_desde: Optional[date] = None
    creado_hasta: Optional[date] = None
    buscar: Optional[str] = None

class TicketOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TicketStatus
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)



