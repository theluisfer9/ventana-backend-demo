from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.v1.config.database import BasePG
import uuid


class UserQueryCheckpoint(BasePG):
    __tablename__ = "user_query_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module = Column(String(100), nullable=False)
    scope = Column(String(100), nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="query_checkpoints")

    __table_args__ = (
        UniqueConstraint("user_id", "module", "scope"),
    )

    def __repr__(self):
        return f"<UserQueryCheckpoint {self.user_id} {self.module}:{self.scope}>"
