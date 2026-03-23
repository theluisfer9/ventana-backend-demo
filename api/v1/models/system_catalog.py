import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from api.v1.config.database import BasePG


class SystemCatalog(BasePG):
    __tablename__ = "system_catalogs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship(
        "SystemCatalogItem",
        back_populates="catalog",
        cascade="all, delete-orphan",
        order_by="SystemCatalogItem.display_order",
    )

    def __repr__(self):
        return f"<SystemCatalog {self.code}>"


class SystemCatalogItem(BasePG):
    __tablename__ = "system_catalog_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_id = Column(
        UUID(as_uuid=True),
        ForeignKey("system_catalogs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    value = Column(JSONB, nullable=False, default=dict, server_default="{}")
    display_order = Column(Integer, nullable=False, default=0, server_default="0")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    catalog = relationship("SystemCatalog", back_populates="items")

    __table_args__ = (
        UniqueConstraint("catalog_id", "code", name="uq_system_catalog_items_catalog_code"),
    )

    def __repr__(self):
        return f"<SystemCatalogItem {self.code}>"
