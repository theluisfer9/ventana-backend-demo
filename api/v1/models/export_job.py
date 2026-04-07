import uuid
import enum
from sqlalchemy import Column, String, DateTime, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from api.v1.config.database import BasePG


class ExportJobStatus(str, enum.Enum):
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class ExportJob(BasePG):
    __tablename__ = "export_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(SAEnum(ExportJobStatus), default=ExportJobStatus.PROCESSING, nullable=False)
    formato = Column(String(10), nullable=False)
    filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    media_type = Column(String(100), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
