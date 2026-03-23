import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from api.v1.config.database import BasePG


class AuditEvent(BasePG):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    module = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_method = Column(String(16), nullable=True)
    request_path = Column(Text, nullable=True)
    query_params = Column(JSONB, nullable=False, default=dict, server_default="{}")
    payload_summary = Column(JSONB, nullable=False, default=dict, server_default="{}")
    summary_text = Column(Text, nullable=True)
    result_count = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="success", server_default="success")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", backref="audit_events")
    institution = relationship("Institution", backref="audit_events")

    @property
    def username(self) -> str | None:
        if self.user:
            return self.user.username
        return None

    @property
    def user_full_name(self) -> str | None:
        if self.user:
            return self.user.full_name
        return None

    @property
    def institution_name(self) -> str | None:
        if self.institution:
            return self.institution.name
        return None

    def __repr__(self):
        return f"<AuditEvent {self.event_type}:{self.module}:{self.action}>"
