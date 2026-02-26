"""Tests for structured base_filter in query engine."""
import pytest
from api.v1.services.query_engine.engine import build_where_from_columns, build_where


class TestBuildWhereFromColumns:
    """Unit tests for build_where_from_columns helper."""

    def test_empty_columns_returns_none(self):
        result = build_where_from_columns([], "OR")
        assert result is None

    def test_single_column(self):
        result = build_where_from_columns(["prog_fodes"], "OR")
        assert result == "prog_fodes = 1"

    def test_multiple_columns_or(self):
        result = build_where_from_columns(["prog_bono_social", "prog_bolsa_social"], "OR")
        assert result == "(prog_bono_social = 1 OR prog_bolsa_social = 1)"

    def test_multiple_columns_and(self):
        result = build_where_from_columns(["prog_fodes", "prog_maga"], "AND")
        assert result == "(prog_fodes = 1 AND prog_maga = 1)"

    def test_single_column_no_parens(self):
        result = build_where_from_columns(["prog_fodes"], "AND")
        assert result == "prog_fodes = 1"

    def test_invalid_column_name_raises(self):
        with pytest.raises(ValueError, match="Identificador SQL no válido"):
            build_where_from_columns(["DROP TABLE foo"], "OR")


class TestBuildWhereWithStructuredFilter:
    """Integration: build_where using structured columns instead of raw string."""

    def test_no_base_filter_no_user_filters(self):
        where, params = build_where(None, None, [], {})
        assert where == "1=1"
        assert params == {}

    def test_structured_filter_only(self):
        where, params = build_where(["prog_fodes"], "OR", [], {})
        assert "prog_fodes = 1" in where
        assert params == {}

    def test_structured_filter_plus_user_filter(self):
        from api.v1.models.data_source import DataSourceColumn, ColumnDataType, ColumnCategory
        import uuid
        col = DataSourceColumn(
            id=uuid.uuid4(),
            datasource_id=uuid.uuid4(),
            column_name="ig3_departamento",
            label="Departamento",
            data_type=ColumnDataType.TEXT,
            category=ColumnCategory.GEO,
        )
        col_map = {"ig3_departamento": col}
        filters = [{"column": "ig3_departamento", "op": "eq", "value": "Guatemala"}]
        where, params = build_where(["prog_fodes"], "OR", filters, col_map)
        assert "prog_fodes = 1" in where
        assert "ig3_departamento" in where
        assert "p_0" in params
