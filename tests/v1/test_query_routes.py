"""
Integration tests for query builder routes (/api/v1/queries).
Uses authenticated_admin_client + mocked ClickHouse for execute endpoints.
"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from main import app
from api.v1.config.database import get_ch_client
from api.v1.models.data_source import (
    DataSource, DataSourceColumn, ColumnDataType, ColumnCategory,
)


# ==================== Helpers ====================

def _seed_datasource(db_session, institution_id=None, code="QRY_DS"):
    """Seed a DataSource with 3 columns directly in DB."""
    ds = DataSource(
        code=code,
        name="Query Test DS",
        ch_table="rsh.test_table",
        base_filter="prog_test = 1",
        institution_id=institution_id,
        is_active=True,
    )
    db_session.add(ds)
    db_session.flush()

    cols = [
        DataSourceColumn(
            datasource_id=ds.id,
            column_name="hogar_id",
            label="Hogar ID",
            data_type=ColumnDataType.INTEGER,
            category=ColumnCategory.DIMENSION,
            is_selectable=True,
            is_filterable=True,
            display_order=1,
        ),
        DataSourceColumn(
            datasource_id=ds.id,
            column_name="departamento",
            label="Departamento",
            data_type=ColumnDataType.TEXT,
            category=ColumnCategory.GEO,
            is_selectable=True,
            is_filterable=True,
            display_order=2,
        ),
        DataSourceColumn(
            datasource_id=ds.id,
            column_name="estufa",
            label="Estufa Mejorada",
            data_type=ColumnDataType.BOOLEAN,
            category=ColumnCategory.INTERVENTION,
            is_selectable=True,
            is_filterable=True,
            display_order=3,
        ),
    ]
    for c in cols:
        db_session.add(c)
    db_session.commit()
    db_session.refresh(ds)
    return ds


def _mock_ch_client(count=5, rows=None, col_names=None):
    """Create a mock ClickHouse client that returns predictable data."""
    client = MagicMock()
    count_result = MagicMock()
    count_result.result_rows = [[count]]
    data_result = MagicMock()
    data_result.column_names = col_names or ["hogar_id", "departamento"]
    data_result.result_rows = rows or [[1, "Guatemala"], [2, "Escuintla"]]
    client.query = MagicMock(side_effect=[count_result, data_result])
    return client


# ==================== List Available DataSources ====================

class TestListAvailableDataSources:
    def test_returns_active_datasources(self, authenticated_admin_client, db_session, test_institution):
        _seed_datasource(db_session, institution_id=test_institution.id)
        resp = authenticated_admin_client.get("/api/v1/queries/datasources")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        ds = data[0]
        assert ds["code"] == "QRY_DS"
        assert len(ds["columns"]) == 3

    def test_inactive_datasources_hidden(self, authenticated_admin_client, db_session):
        ds = _seed_datasource(db_session, code="INACTIVE_DS")
        ds.is_active = False
        db_session.commit()
        resp = authenticated_admin_client.get("/api/v1/queries/datasources")
        data = resp.json()["data"]
        codes = [d["code"] for d in data]
        assert "INACTIVE_DS" not in codes


# ==================== Execute Ad-Hoc Query ====================

class TestExecuteQuery:
    def _execute(self, client, ds_id, columns, filters=None):
        return client.post("/api/v1/queries/execute", json={
            "datasource_id": str(ds_id),
            "columns": columns,
            "filters": filters or [],
            "offset": 0,
            "limit": 10,
        })

    def test_execute_returns_results(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        mock_ch = _mock_ch_client(
            count=2,
            rows=[[1, "Guatemala"], [2, "Escuintla"]],
            col_names=["hogar_id", "departamento"],
        )

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = self._execute(
                authenticated_admin_client, ds.id, ["hogar_id", "departamento"]
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["total"] == 2
            assert len(data["items"]) == 2
            assert data["items"][0]["hogar_id"] == 1
            assert len(data["columns_meta"]) == 2
            assert data["columns_meta"][0]["label"] == "Hogar ID"
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

    def test_execute_invalid_column_returns_400(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        resp = self._execute(
            authenticated_admin_client, ds.id, ["no_existe"]
        )
        assert resp.status_code == 400

    def test_execute_with_filters(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        mock_ch = _mock_ch_client(count=1, rows=[[1, "Guatemala"]], col_names=["hogar_id", "departamento"])

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = self._execute(
                authenticated_admin_client, ds.id,
                ["hogar_id", "departamento"],
                filters=[{"column": "departamento", "op": "eq", "value": "01"}],
            )
            assert resp.status_code == 200
            # Verify filter was passed to ClickHouse
            count_sql = mock_ch.query.call_args_list[0][0][0]
            assert "departamento =" in count_sql
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

    def test_execute_nonexistent_datasource_returns_404(self, authenticated_admin_client):
        resp = self._execute(authenticated_admin_client, uuid4(), ["hogar_id"])
        assert resp.status_code == 404


# ==================== Save / List / Get / Delete Queries ====================

class TestSavedQueries:
    def _save_query(self, client, ds_id, name="Mi Consulta"):
        return client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds_id),
            "name": name,
            "selected_columns": ["hogar_id", "departamento"],
            "filters": [{"column": "departamento", "op": "eq", "value": "01"}],
        })

    def test_save_query(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        resp = self._save_query(authenticated_admin_client, ds.id)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "Mi Consulta"
        assert "id" in data

    def test_list_saved_queries(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        self._save_query(authenticated_admin_client, ds.id, name="Query A")
        self._save_query(authenticated_admin_client, ds.id, name="Query B")
        resp = authenticated_admin_client.get("/api/v1/queries/saved")
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) == 2
        names = [q["name"] for q in items]
        assert "Query A" in names
        assert "Query B" in names

    def test_get_saved_query(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        save_resp = self._save_query(authenticated_admin_client, ds.id)
        query_id = save_resp.json()["data"]["id"]
        resp = authenticated_admin_client.get(f"/api/v1/queries/saved/{query_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "Mi Consulta"
        assert data["selected_columns"] == ["hogar_id", "departamento"]
        assert len(data["filters"]) == 1

    def test_get_nonexistent_saved_query_returns_404(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(f"/api/v1/queries/saved/{uuid4()}")
        assert resp.status_code == 404

    def test_delete_saved_query(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        save_resp = self._save_query(authenticated_admin_client, ds.id)
        query_id = save_resp.json()["data"]["id"]
        resp = authenticated_admin_client.delete(f"/api/v1/queries/saved/{query_id}")
        assert resp.status_code == 204
        # Confirm deleted
        get_resp = authenticated_admin_client.get(f"/api/v1/queries/saved/{query_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, authenticated_admin_client):
        resp = authenticated_admin_client.delete(f"/api/v1/queries/saved/{uuid4()}")
        assert resp.status_code == 404

    def test_save_with_invalid_column_returns_400(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        resp = authenticated_admin_client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds.id),
            "name": "Bad Query",
            "selected_columns": ["fake_col"],
            "filters": [],
        })
        assert resp.status_code == 400


# ==================== Execute Saved Query ====================

class TestExecuteSavedQuery:
    def test_execute_saved_query(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        save_resp = authenticated_admin_client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds.id),
            "name": "Executable",
            "selected_columns": ["hogar_id", "departamento"],
            "filters": [],
        })
        query_id = save_resp.json()["data"]["id"]

        mock_ch = _mock_ch_client(
            count=3,
            rows=[[1, "Guat"], [2, "Esc"], [3, "Quet"]],
            col_names=["hogar_id", "departamento"],
        )

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = authenticated_admin_client.post(f"/api/v1/queries/saved/{query_id}/execute")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["total"] == 3
            assert len(data["items"]) == 3
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

    def test_execute_nonexistent_saved_query_returns_404(self, authenticated_admin_client):
        resp = authenticated_admin_client.post(f"/api/v1/queries/saved/{uuid4()}/execute")
        assert resp.status_code == 404
