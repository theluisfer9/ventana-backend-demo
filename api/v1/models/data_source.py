from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.v1.config.database import BasePG
import uuid
import enum


class ColumnDataType(str, enum.Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"


class ColumnCategory(str, enum.Enum):
    DIMENSION = "DIMENSION"
    MEASURE = "MEASURE"
    INTERVENTION = "INTERVENTION"
    GEO = "GEO"


class DataSource(BasePG):
    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    ch_table = Column(String(200), nullable=False)
    base_filter = Column(Text, nullable=True)
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    institution = relationship("Institution", backref="data_sources")
    columns_def = relationship(
        "DataSourceColumn",
        back_populates="data_source",
        cascade="all, delete-orphan",
        order_by="DataSourceColumn.display_order",
    )
    saved_queries = relationship("SavedQuery", back_populates="data_source")

    def __repr__(self):
        return f"<DataSource {self.code}>"


class DataSourceColumn(BasePG):
    __tablename__ = "data_source_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    datasource_id = Column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    column_name = Column(String(100), nullable=False)
    label = Column(String(200), nullable=False)
    data_type = Column(SAEnum(ColumnDataType), nullable=False, default=ColumnDataType.TEXT)
    category = Column(SAEnum(ColumnCategory), nullable=False, default=ColumnCategory.DIMENSION)
    is_selectable = Column(Boolean, default=True)
    is_filterable = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    data_source = relationship("DataSource", back_populates="columns_def")

    def __repr__(self):
        return f"<DataSourceColumn {self.column_name}>"


class SavedQuery(BasePG):
    __tablename__ = "saved_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    datasource_id = Column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(200), nullable=False)
    selected_columns = Column(JSONB, nullable=False, default=list)
    filters = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="saved_queries")
    data_source = relationship("DataSource", back_populates="saved_queries")

    def __repr__(self):
        return f"<SavedQuery {self.name}>"
