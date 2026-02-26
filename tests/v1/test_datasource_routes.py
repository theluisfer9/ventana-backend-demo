"""
Integration tests for DataSource admin CRUD routes (/api/v1/datasources).
Uses authenticated_admin_client which bypasses RequirePermission.
"""
import pytest
from uuid import uuid4


class TestDataSourceCRUD:
    """Full lifecycle: create, list, get, update, soft-delete."""

    def _create_ds(self, client, code="TEST_DS", name="Test DataSource"):
        return client.post("/api/v1/datasources/", json={
            "code": code,
            "name": name,
            "ch_table": "rsh.test_table",
            "base_filter_columns": ["prog_test"],
            "base_filter_logic": "OR",
        })

    def test_create_datasource(self, authenticated_admin_client):
        resp = self._create_ds(authenticated_admin_client)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["code"] == "TEST_DS"
        assert data["name"] == "Test DataSource"
        assert data["ch_table"] == "rsh.test_table"
        assert data["base_filter_columns"] == ["prog_test"]
        assert data["base_filter_logic"] == "OR"
        assert data["is_active"] is True
        assert data["columns"] == []

    def test_create_datasource_no_filter(self, authenticated_admin_client):
        resp = authenticated_admin_client.post("/api/v1/datasources/", json={
            "code": "NO_FILTER",
            "name": "No Filter DS",
            "ch_table": "rsh.test_table",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["base_filter_columns"] == []
        assert data["base_filter_logic"] == "OR"

    def test_create_duplicate_code_returns_409(self, authenticated_admin_client):
        self._create_ds(authenticated_admin_client, code="DUP")
        resp = self._create_ds(authenticated_admin_client, code="DUP")
        assert resp.status_code == 409

    def test_list_datasources(self, authenticated_admin_client):
        self._create_ds(authenticated_admin_client, code="DS_A", name="Alpha")
        self._create_ds(authenticated_admin_client, code="DS_B", name="Beta")
        resp = authenticated_admin_client.get("/api/v1/datasources/")
        assert resp.status_code == 200
        items = resp.json()["data"]
        codes = [ds["code"] for ds in items]
        assert "DS_A" in codes
        assert "DS_B" in codes
        ds_a = next(ds for ds in items if ds["code"] == "DS_A")
        assert ds_a["ch_table"] == "rsh.test_table"
        assert ds_a["base_filter_columns"] == ["prog_test"]

    def test_get_datasource(self, authenticated_admin_client):
        create_resp = self._create_ds(authenticated_admin_client)
        ds_id = create_resp.json()["data"]["id"]
        resp = authenticated_admin_client.get(f"/api/v1/datasources/{ds_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["code"] == "TEST_DS"

    def test_get_nonexistent_returns_404(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(f"/api/v1/datasources/{uuid4()}")
        assert resp.status_code == 404

    def test_update_datasource(self, authenticated_admin_client):
        create_resp = self._create_ds(authenticated_admin_client)
        ds_id = create_resp.json()["data"]["id"]
        resp = authenticated_admin_client.put(f"/api/v1/datasources/{ds_id}", json={
            "name": "Updated Name",
            "base_filter_columns": ["prog_new", "prog_other"],
            "base_filter_logic": "AND",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "Updated Name"
        assert data["base_filter_columns"] == ["prog_new", "prog_other"]
        assert data["base_filter_logic"] == "AND"

    def test_delete_datasource_soft_deletes(self, authenticated_admin_client):
        create_resp = self._create_ds(authenticated_admin_client)
        ds_id = create_resp.json()["data"]["id"]
        resp = authenticated_admin_client.delete(f"/api/v1/datasources/{ds_id}")
        assert resp.status_code == 204
        # Still accessible but inactive
        get_resp = authenticated_admin_client.get(f"/api/v1/datasources/{ds_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["is_active"] is False


class TestDataSourceColumnCRUD:
    """Column management within a data source."""

    def _create_ds_with_columns(self, client):
        ds_resp = client.post("/api/v1/datasources/", json={
            "code": "COL_TEST",
            "name": "Column Test DS",
            "ch_table": "rsh.test",
        })
        ds_id = ds_resp.json()["data"]["id"]
        return ds_id

    def test_create_column(self, authenticated_admin_client):
        ds_id = self._create_ds_with_columns(authenticated_admin_client)
        resp = authenticated_admin_client.post(f"/api/v1/datasources/{ds_id}/columns", json={
            "column_name": "hogar_id",
            "label": "Hogar ID",
            "data_type": "INTEGER",
            "category": "DIMENSION",
            "is_selectable": True,
            "is_filterable": True,
            "display_order": 1,
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["column_name"] == "hogar_id"
        assert data["label"] == "Hogar ID"
        assert data["data_type"] == "INTEGER"
        assert data["category"] == "DIMENSION"

    def test_update_column(self, authenticated_admin_client):
        ds_id = self._create_ds_with_columns(authenticated_admin_client)
        col_resp = authenticated_admin_client.post(f"/api/v1/datasources/{ds_id}/columns", json={
            "column_name": "depto",
            "label": "Departamento",
            "data_type": "TEXT",
            "category": "GEO",
        })
        col_id = col_resp.json()["data"]["id"]
        resp = authenticated_admin_client.put(
            f"/api/v1/datasources/{ds_id}/columns/{col_id}",
            json={"label": "Depto Actualizado", "is_selectable": False},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["label"] == "Depto Actualizado"
        assert data["is_selectable"] is False

    def test_delete_column(self, authenticated_admin_client):
        ds_id = self._create_ds_with_columns(authenticated_admin_client)
        col_resp = authenticated_admin_client.post(f"/api/v1/datasources/{ds_id}/columns", json={
            "column_name": "temp_col",
            "label": "Temporal",
        })
        col_id = col_resp.json()["data"]["id"]
        resp = authenticated_admin_client.delete(f"/api/v1/datasources/{ds_id}/columns/{col_id}")
        assert resp.status_code == 204

    def test_delete_nonexistent_column_returns_404(self, authenticated_admin_client):
        ds_id = self._create_ds_with_columns(authenticated_admin_client)
        resp = authenticated_admin_client.delete(f"/api/v1/datasources/{ds_id}/columns/{uuid4()}")
        assert resp.status_code == 404

    def test_columns_appear_in_datasource_get(self, authenticated_admin_client):
        ds_id = self._create_ds_with_columns(authenticated_admin_client)
        authenticated_admin_client.post(f"/api/v1/datasources/{ds_id}/columns", json={
            "column_name": "col_a",
            "label": "Column A",
            "display_order": 1,
        })
        authenticated_admin_client.post(f"/api/v1/datasources/{ds_id}/columns", json={
            "column_name": "col_b",
            "label": "Column B",
            "display_order": 2,
        })
        resp = authenticated_admin_client.get(f"/api/v1/datasources/{ds_id}")
        columns = resp.json()["data"]["columns"]
        assert len(columns) == 2
        assert columns[0]["column_name"] == "col_a"
        assert columns[1]["column_name"] == "col_b"
