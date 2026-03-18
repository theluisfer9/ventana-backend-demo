from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.v1.config.database import BasePG
import uuid


class InstitutionApiToken(BasePG):
    __tablename__ = "institution_api_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(200), nullable=False)
    token_prefix = Column(String(32), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    institution = relationship("Institution", backref="api_tokens")

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at is None:
            return True
        from datetime import datetime, timezone

        return self.expires_at > datetime.now(timezone.utc)
