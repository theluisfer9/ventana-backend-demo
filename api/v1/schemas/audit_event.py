from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    id: UUID
    event_type: str
    module: str
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    user_id: UUID | None = None
    institution_id: UUID | None = None
    request_method: str | None = None
    request_path: str | None = None
    query_params: dict[str, Any]
    payload_summary: dict[str, Any]
    result_count: int | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
