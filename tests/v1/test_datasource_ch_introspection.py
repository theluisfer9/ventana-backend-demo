"""
Tests for ClickHouse introspection endpoints.
These endpoints require a mocked ClickHouse client.
"""
import pytest


class TestChTablesEndpoint:
    """GET /api/v1/datasources/ch-tables"""

    def test_returns_table_list(self, authenticated_ch_client):
        resp = authenticated_ch_client.get("/api/v1/datasources/ch-tables")
        assert resp.status_code == 200
        tables = resp.json()["data"]
        assert isinstance(tables, list)
        assert len(tables) > 0
        assert any("rsh." in t for t in tables)

    def test_tables_are_prefixed(self, authenticated_ch_client):
        resp = authenticated_ch_client.get("/api/v1/datasources/ch-tables")
        tables = resp.json()["data"]
        for table in tables:
            assert table.startswith("rsh.")


class TestChColumnsEndpoint:
    """GET /api/v1/datasources/ch-columns?table=..."""

    def test_returns_columns_for_valid_table(self, authenticated_ch_client):
        resp = authenticated_ch_client.get("/api/v1/datasources/ch-columns?table=rsh.vw_beneficios_x_hogar")
        assert resp.status_code == 200
        columns = resp.json()["data"]
        assert isinstance(columns, list)
        assert len(columns) > 0
        assert "name" in columns[0]
        assert "type" in columns[0]

    def test_columns_include_expected_names(self, authenticated_ch_client):
        resp = authenticated_ch_client.get("/api/v1/datasources/ch-columns?table=rsh.vw_beneficios_x_hogar")
        columns = resp.json()["data"]
        names = [c["name"] for c in columns]
        assert "hogar_id" in names
        assert "prog_fodes" in names

    def test_missing_table_param_returns_422(self, authenticated_ch_client):
        resp = authenticated_ch_client.get("/api/v1/datasources/ch-columns")
        assert resp.status_code == 422

    def test_invalid_table_name_returns_400(self, authenticated_ch_client):
        resp = authenticated_ch_client.get("/api/v1/datasources/ch-columns?table=DROP TABLE foo")
        assert resp.status_code == 400
