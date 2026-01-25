from sqlalchemy import Column, String, Text, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.v1.config.database import BasePG
import uuid


# Association table for Role-Permission many-to-many relationship
role_permissions = Table(
    "role_permissions",
    BasePG.metadata,
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)


class Role(BasePG):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        backref="roles",
        lazy="selectin",
    )
    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role {self.code}: {self.name}>"

    def has_permission(self, permission_code: str) -> bool:
        """Check if role has a specific permission"""
        return any(p.code == permission_code for p in self.permissions)
