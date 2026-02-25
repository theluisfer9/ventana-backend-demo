"""
Unit tests for the query engine: validators and SQL builder.
No database or HTTP client needed — pure function tests.
"""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from api.v1.services.query_engine.validators import validate_columns, validate_filters, validate_group_by
from api.v1.services.query_engine.engine import build_select, build_select_grouped, build_group_by, build_where, execute_query
from api.v1.models.data_source import ColumnDataType, ColumnCategory


# ==================== Helpers ====================

def _make_col(name, label=None, data_type=ColumnDataType.TEXT,
              category=ColumnCategory.DIMENSION,
              is_selectable=True, is_filterable=True, is_groupable=False):
    col = MagicMock()
    col.column_name = name
    col.label = label or name.replace("_", " ").title()
    col.data_type = data_type
    col.category = category
    col.is_selectable = is_selectable
    col.is_filterable = is_filterable
    col.is_groupable = is_groupable
    col.display_order = 0
    return col


SAMPLE_COLUMNS = [
    _make_col("hogar_id", data_type=ColumnDataType.INTEGER),
    _make_col("departamento"),
    _make_col("municipio"),
    _make_col("estufa_mejorada", data_type=ColumnDataType.BOOLEAN,
              category=ColumnCategory.INTERVENTION),
    _make_col("total_personas", data_type=ColumnDataType.INTEGER,
              category=ColumnCategory.MEASURE, is_filterable=False),
    _make_col("internal_code", is_selectable=False, is_filterable=False),
]


# ==================== validate_columns ====================

class TestValidateColumns:
    def test_valid_columns_returned(self):
        result = validate_columns(["hogar_id", "departamento"], SAMPLE_COLUMNS)
        assert len(result) == 2
        assert result[0].column_name == "hogar_id"
        assert result[1].column_name == "departamento"

    def test_unknown_column_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_columns(["no_existe"], SAMPLE_COLUMNS)
        assert exc_info.value.status_code == 400
        assert "no_existe" in exc_info.value.detail

    def test_non_selectable_column_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_columns(["internal_code"], SAMPLE_COLUMNS)
        assert exc_info.value.status_code == 400
        assert "internal_code" in exc_info.value.detail

    def test_non_selectable_allowed_when_check_disabled(self):
        result = validate_columns(
            ["internal_code"], SAMPLE_COLUMNS, check_selectable=False
        )
        assert len(result) == 1

    def test_empty_list_returns_empty(self):
        result = validate_columns([], SAMPLE_COLUMNS)
        assert result == []


# ==================== validate_filters ====================

class TestValidateFilters:
    def test_valid_filter_passes(self):
        filters = [{"column": "departamento", "op": "eq", "value": "01"}]
        validate_filters(filters, SAMPLE_COLUMNS)  # no exception

    def test_unknown_filter_column_raises(self):
        filters = [{"column": "ghost", "op": "eq", "value": "x"}]
        with pytest.raises(HTTPException) as exc_info:
            validate_filters(filters, SAMPLE_COLUMNS)
        assert exc_info.value.status_code == 400

    def test_non_filterable_column_raises(self):
        filters = [{"column": "total_personas", "op": "gt", "value": 3}]
        with pytest.raises(HTTPException) as exc_info:
            validate_filters(filters, SAMPLE_COLUMNS)
        assert exc_info.value.status_code == 400
        assert "total_personas" in exc_info.value.detail

    def test_multiple_filters_all_valid(self):
        filters = [
            {"column": "departamento", "op": "eq", "value": "01"},
            {"column": "municipio", "op": "like", "value": "mix"},
        ]
        validate_filters(filters, SAMPLE_COLUMNS)

    def test_empty_filters_passes(self):
        validate_filters([], SAMPLE_COLUMNS)


# ==================== build_select ====================

class TestBuildSelect:
    def test_single_column(self):
        cols = [_make_col("hogar_id")]
        assert build_select(cols) == "hogar_id"

    def test_multiple_columns(self):
        cols = [_make_col("hogar_id"), _make_col("departamento"), _make_col("municipio")]
        assert build_select(cols) == "hogar_id, departamento, municipio"


# ==================== build_where ====================

class TestBuildWhere:
    def _col_map(self, names=None):
        return {c.column_name: c for c in SAMPLE_COLUMNS if names is None or c.column_name in names}

    def test_no_filters_no_base(self):
        where, params = build_where(None, [], self._col_map())
        assert where == "1=1"
        assert params == {}

    def test_base_filter_only(self):
        where, params = build_where("prog_fodes = 1", [], self._col_map())
        assert where == "prog_fodes = 1"
        assert params == {}

    def test_eq_filter(self):
        filters = [{"column": "departamento", "op": "eq", "value": "01"}]
        where, params = build_where(None, filters, self._col_map())
        assert "departamento = {p_0:String}" in where
        assert params["p_0"] == "01"

    def test_neq_filter(self):
        filters = [{"column": "departamento", "op": "neq", "value": "01"}]
        where, params = build_where(None, filters, self._col_map())
        assert "departamento != {p_0:String}" in where

    def test_gt_lt_gte_lte_integer(self):
        col_map = self._col_map(["hogar_id"])
        for op, sql_op in [("gt", ">"), ("lt", "<"), ("gte", ">="), ("lte", "<=")]:
            filters = [{"column": "hogar_id", "op": op, "value": 100}]
            where, params = build_where(None, filters, col_map)
            assert f"hogar_id {sql_op} {{p_0:Int64}}" in where
            assert params["p_0"] == 100

    def test_like_filter(self):
        filters = [{"column": "municipio", "op": "like", "value": "mix"}]
        where, params = build_where(None, filters, self._col_map())
        assert "municipio ILIKE {p_0:String}" in where
        assert params["p_0"] == "%mix%"

    def test_in_filter(self):
        filters = [{"column": "departamento", "op": "in", "value": ["01", "02", "03"]}]
        where, params = build_where(None, filters, self._col_map())
        assert "departamento IN" in where
        assert params["p_0_0"] == "01"
        assert params["p_0_1"] == "02"
        assert params["p_0_2"] == "03"

    def test_base_filter_plus_user_filters(self):
        filters = [{"column": "departamento", "op": "eq", "value": "01"}]
        where, params = build_where("prog_fodes = 1", filters, self._col_map())
        assert where.startswith("prog_fodes = 1 AND ")
        assert "departamento =" in where

    def test_boolean_type_maps_to_int8(self):
        filters = [{"column": "estufa_mejorada", "op": "eq", "value": 1}]
        where, params = build_where(None, filters, self._col_map())
        assert "Int8" in where


# ==================== execute_query ====================

class TestExecuteQuery:
    def _make_ds(self, base_filter=None):
        ds = MagicMock()
        ds.ch_table = "rsh.beneficios_x_hogar"
        ds.base_filter = base_filter
        ds.columns_def = SAMPLE_COLUMNS
        return ds

    def _make_ch_client(self, count=42, rows=None, col_names=None):
        client = MagicMock()
        count_result = MagicMock()
        count_result.result_rows = [[count]]
        data_result = MagicMock()
        data_result.column_names = col_names or ["hogar_id", "departamento"]
        data_result.result_rows = rows or [[1, "Guatemala"], [2, "Escuintla"]]
        client.query = MagicMock(side_effect=[count_result, data_result])
        return client

    def test_returns_rows_and_total(self):
        ds = self._make_ds()
        ch = self._make_ch_client(count=100, rows=[[1, "Guat"]], col_names=["hogar_id", "departamento"])
        cols = [_make_col("hogar_id", data_type=ColumnDataType.INTEGER), _make_col("departamento")]

        rows, total = execute_query(ch, ds, cols, [], 0, 10)

        assert total == 100
        assert len(rows) == 1
        assert rows[0]["hogar_id"] == 1
        assert rows[0]["departamento"] == "Guat"

    def test_calls_count_and_data_queries(self):
        ds = self._make_ds(base_filter="prog_fodes = 1")
        ch = self._make_ch_client()
        cols = [_make_col("hogar_id", data_type=ColumnDataType.INTEGER)]

        execute_query(ch, ds, cols, [], 0, 20)

        assert ch.query.call_count == 2
        count_sql = ch.query.call_args_list[0][0][0]
        data_sql = ch.query.call_args_list[1][0][0]
        assert "count()" in count_sql
        assert "prog_fodes = 1" in count_sql
        assert "SELECT hogar_id" in data_sql
        assert "LIMIT" in data_sql
        assert "OFFSET" in data_sql

    def test_passes_offset_and_limit(self):
        ds = self._make_ds()
        ch = self._make_ch_client()
        cols = [_make_col("hogar_id", data_type=ColumnDataType.INTEGER)]

        execute_query(ch, ds, cols, [], 40, 20)

        params = ch.query.call_args_list[1][1]["parameters"]
        assert params["_offset"] == 40
        assert params["_limit"] == 20

    def test_filters_included_in_sql(self):
        ds = self._make_ds()
        ch = self._make_ch_client()
        cols = [_make_col("hogar_id", data_type=ColumnDataType.INTEGER)]
        filters = [{"column": "departamento", "op": "eq", "value": "01"}]

        execute_query(ch, ds, cols, filters, 0, 10)

        count_sql = ch.query.call_args_list[0][0][0]
        assert "departamento =" in count_sql


# ==================== build_select_grouped ====================

class TestBuildSelectGrouped:
    def test_count_star_only(self):
        group_cols = [_make_col("departamento")]
        aggs = [{"column": "*", "function": "COUNT"}]
        result = build_select_grouped(group_cols, aggs)
        assert result == "departamento, COUNT(*) AS count"

    def test_sum_column(self):
        group_cols = [_make_col("departamento")]
        aggs = [
            {"column": "*", "function": "COUNT"},
            {"column": "monto", "function": "SUM"},
        ]
        result = build_select_grouped(group_cols, aggs)
        assert result == "departamento, COUNT(*) AS count, SUM(monto) AS sum_monto"

    def test_multiple_group_cols(self):
        group_cols = [_make_col("departamento"), _make_col("municipio")]
        aggs = [{"column": "*", "function": "COUNT"}]
        result = build_select_grouped(group_cols, aggs)
        assert result == "departamento, municipio, COUNT(*) AS count"


# ==================== build_group_by ====================

class TestBuildGroupBy:
    def test_single_column(self):
        assert build_group_by(["departamento"]) == "departamento"

    def test_multiple_columns(self):
        assert build_group_by(["departamento", "municipio"]) == "departamento, municipio"


# ==================== execute_query with GROUP BY ====================

class TestExecuteQueryGroupBy:
    def _make_ds(self, base_filter=None):
        ds = MagicMock()
        ds.ch_table = "rsh.beneficios_x_hogar"
        ds.base_filter = base_filter
        ds.columns_def = SAMPLE_COLUMNS
        return ds

    def _make_ch_client(self, count=42, rows=None, col_names=None):
        client = MagicMock()
        count_result = MagicMock()
        count_result.result_rows = [[count]]
        data_result = MagicMock()
        data_result.column_names = col_names or ["hogar_id", "departamento"]
        data_result.result_rows = rows or [[1, "Guatemala"], [2, "Escuintla"]]
        client.query = MagicMock(side_effect=[count_result, data_result])
        return client

    def test_execute_with_group_by(self):
        ds = self._make_ds()
        ch = self._make_ch_client(
            count=3,
            rows=[["Guatemala", 100], ["Escuintla", 50], ["Quetzaltenango", 30]],
            col_names=["departamento", "count"],
        )
        cols = [_make_col("departamento")]

        rows, total = execute_query(
            ch, ds, cols, [], 0, 10,
            group_by=["departamento"],
            aggregations=[{"column": "*", "function": "COUNT"}],
        )

        assert total == 3
        assert len(rows) == 3
        # Verify GROUP BY in SQL
        count_sql = ch.query.call_args_list[0][0][0]
        assert "GROUP BY" in count_sql
        data_sql = ch.query.call_args_list[1][0][0]
        assert "GROUP BY departamento" in data_sql
        assert "COUNT(*)" in data_sql


# ==================== validate_group_by ====================

class TestValidateGroupBy:
    def test_valid_groupable_columns(self):
        cols = [
            _make_col("departamento", is_groupable=True),
            _make_col("municipio", is_groupable=True),
            _make_col("monto", category=ColumnCategory.MEASURE, is_groupable=False),
        ]
        result = validate_group_by(["departamento"], cols)
        assert len(result) == 1
        assert result[0].column_name == "departamento"

    def test_non_groupable_column_raises(self):
        cols = [_make_col("monto", category=ColumnCategory.MEASURE, is_groupable=False)]
        with pytest.raises(HTTPException) as exc_info:
            validate_group_by(["monto"], cols)
        assert exc_info.value.status_code == 400

    def test_unknown_column_raises(self):
        cols = [_make_col("departamento", is_groupable=True)]
        with pytest.raises(HTTPException) as exc_info:
            validate_group_by(["no_existe"], cols)
        assert exc_info.value.status_code == 400

    def test_empty_list_returns_empty(self):
        result = validate_group_by([], [_make_col("departamento", is_groupable=True)])
        assert result == []
