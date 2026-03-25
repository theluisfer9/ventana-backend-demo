"""
Integration tests for query builder routes (/api/v1/queries).
Uses authenticated_admin_client + mocked ClickHouse for execute endpoints.
"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from main import app
from api.v1.config.database import get_ch_client, get_sync_db_pg
from api.v1.models.data_source import (
    DataSource, DataSourceColumn, ColumnDataType, ColumnCategory, RoleDataSource, SavedQuery, SavedQueryRole,
)
from api.v1.models.user import User
from api.v1.auth.password import hash_password


# ==================== Helpers ====================

def _seed_datasource(db_session, institution_id=None, code="QRY_DS"):
    """Seed a DataSource with 3 columns directly in DB."""
    ds = DataSource(
        code=code,
        name="Query Test DS",
        ch_table="rsh.test_table",
        base_filter_columns=["prog_test"],
        base_filter_logic="OR",
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


def _seed_user(db_session, role_id, institution_id=None, username="queryuser", email=None):
    user = User(
        id=uuid4(),
        email=email or f"{username}@test.com",
        username=username,
        password_hash=hash_password("User123!"),
        first_name=username.capitalize(),
        last_name="User",
        role_id=role_id,
        institution_id=institution_id,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


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


def _override_unused_ch():
    """Provide a harmless ClickHouse dependency for validation-only tests."""
    client = MagicMock()
    client.query = MagicMock()
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

    def test_role_assigned_datasource_is_listed_even_without_matching_institution(
        self,
        authenticated_regular_client,
        db_session,
        test_regular_user,
    ):
        ds = _seed_datasource(db_session, institution_id=None, code="ROLE_ONLY_DS")
        db_session.add(RoleDataSource(role_id=test_regular_user.role_id, datasource_id=ds.id))
        db_session.commit()

        resp = authenticated_regular_client.get("/api/v1/queries/datasources")

        assert resp.status_code == 200
        assert [item["code"] for item in resp.json()["data"]] == ["ROLE_ONLY_DS"]


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
        mock_ch = _override_unused_ch()

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = self._execute(
                authenticated_admin_client, ds.id, ["no_existe"]
            )
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

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
        mock_ch = _override_unused_ch()

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = self._execute(authenticated_admin_client, uuid4(), ["hogar_id"])
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

    def test_execute_with_agrupar_false_does_not_inject_geo_columns(
        self,
        authenticated_admin_client,
        db_session,
        test_institution,
    ):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        mock_ch = _mock_ch_client(
            count=1,
            rows=[[1]],
            col_names=["hogar_id"],
        )

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = authenticated_admin_client.post("/api/v1/queries/execute", json={
                "datasource_id": str(ds.id),
                "columns": ["hogar_id"],
                "filters": [],
                "offset": 0,
                "limit": 10,
                "agrupar": False,
            })
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert [c["column_name"] for c in data["columns_meta"]] == ["hogar_id"]
        finally:
            app.dependency_overrides.pop(get_ch_client, None)


# ==================== Save / List / Get / Delete Queries ====================

class TestSavedQueries:
    def _save_query(self, client, ds_id, name="Mi Consulta", role_ids=None):
        return client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds_id),
            "name": name,
            "selected_columns": ["hogar_id", "departamento"],
            "filters": [{"column": "departamento", "op": "eq", "value": "01"}],
            "role_ids": role_ids or [],
        })

    def test_save_query(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        resp = self._save_query(authenticated_admin_client, ds.id)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "Mi Consulta"
        assert "id" in data
        assert data["role_names"] == []

    def test_save_query_persists_agrupar(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        resp = authenticated_admin_client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds.id),
            "name": "Sin agrupar",
            "selected_columns": ["hogar_id"],
            "filters": [],
            "agrupar": False,
        })
        assert resp.status_code == 201
        query_id = resp.json()["data"]["id"]

        get_resp = authenticated_admin_client.get(f"/api/v1/queries/saved/{query_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()["data"]
        assert data["agrupar"] is False
        assert data["selected_columns"] == ["hogar_id"]

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
        assert all("agrupar" in q for q in items)

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
        assert data["agrupar"] is True

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

    def test_update_saved_query_persists_agrupar(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        save_resp = self._save_query(authenticated_admin_client, ds.id)
        query_id = save_resp.json()["data"]["id"]

        resp = authenticated_admin_client.put(f"/api/v1/queries/saved/{query_id}", json={
            "agrupar": False,
            "selected_columns": ["hogar_id"],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["agrupar"] is False
        assert data["selected_columns"] == ["hogar_id"]

    def test_save_with_invalid_column_returns_400(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        resp = authenticated_admin_client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds.id),
            "name": "Bad Query",
            "selected_columns": ["fake_col"],
            "filters": [],
        })
        assert resp.status_code == 400

    def test_save_with_empty_selected_columns_returns_400(
        self,
        authenticated_admin_client,
        db_session,
        test_institution,
    ):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        resp = authenticated_admin_client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds.id),
            "name": "No Columns",
            "selected_columns": [],
            "filters": [],
        })
        assert resp.status_code == 400

    def test_save_group_by_without_aggregations_returns_400(
        self,
        authenticated_admin_client,
        db_session,
        test_institution,
    ):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        for col in ds.columns_def:
            if col.column_name == "departamento":
                col.is_groupable = True
        db_session.commit()

        resp = authenticated_admin_client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds.id),
            "name": "Grouped Incomplete",
            "selected_columns": ["hogar_id", "departamento"],
            "filters": [],
            "group_by": ["departamento"],
            "aggregations": [],
        })
        assert resp.status_code == 400

    def test_save_aggregations_without_group_by_returns_400(
        self,
        authenticated_admin_client,
        db_session,
        test_institution,
    ):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        resp = authenticated_admin_client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds.id),
            "name": "Agg Incomplete",
            "selected_columns": ["hogar_id", "departamento"],
            "filters": [],
            "group_by": [],
            "aggregations": [{"column": "*", "function": "COUNT"}],
        })
        assert resp.status_code == 400

    def test_save_query_persists_assigned_roles(
        self,
        authenticated_admin_client,
        db_session,
        test_roles,
    ):
        ds = _seed_datasource(db_session, institution_id=None)
        resp = authenticated_admin_client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds.id),
            "name": "Role Scoped Query",
            "selected_columns": ["hogar_id", "departamento"],
            "filters": [],
            "role_ids": [str(test_roles["analyst"].id)],
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["role_names"] == ["Analista"]

    def test_creator_can_see_own_query_without_role_assignment(
        self,
        db_session,
        test_roles,
        test_institution,
        authenticated_regular_client,
        test_regular_user,
    ):
        ds = _seed_datasource(db_session, institution_id=None, code="OWN_QUERY_DS")
        db_session.add(RoleDataSource(role_id=test_regular_user.role_id, datasource_id=ds.id))
        db_session.commit()

        saved_query = SavedQuery(
            user_id=test_regular_user.id,
            datasource_id=ds.id,
            name="Solo mia",
            selected_columns=["hogar_id"],
            filters=[],
            group_by=[],
            aggregations=[],
            agrupar=True,
            institution_id=None,
            is_shared=False,
        )
        db_session.add(saved_query)
        db_session.commit()

        resp = authenticated_regular_client.get("/api/v1/queries/saved")

        assert resp.status_code == 200
        assert [item["name"] for item in resp.json()["data"]] == ["Solo mia"]

    def test_assigned_role_can_execute_but_not_edit_query(
        self,
        db_session,
        authenticated_regular_client,
        test_regular_user,
    ):
        ds = _seed_datasource(db_session, institution_id=None, code="ROLE_EXEC_DS")
        db_session.add(RoleDataSource(role_id=test_regular_user.role_id, datasource_id=ds.id))
        creator = _seed_user(
            db_session,
            role_id=test_regular_user.role_id,
            institution_id=None,
            username="creator",
            email="creator@test.com",
        )
        saved_query = SavedQuery(
            user_id=creator.id,
            datasource_id=ds.id,
            name="Asignada a analista",
            selected_columns=["hogar_id", "departamento"],
            filters=[],
            group_by=[],
            aggregations=[],
            agrupar=True,
            institution_id=None,
            is_shared=False,
        )
        db_session.add(saved_query)
        db_session.flush()
        db_session.add(SavedQueryRole(saved_query_id=saved_query.id, role_id=test_regular_user.role_id))
        db_session.commit()
        query_id = str(saved_query.id)

        mock_ch = _mock_ch_client(
            count=1,
            rows=[[1, "Guatemala"]],
            col_names=["hogar_id", "departamento"],
        )

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            execute_resp = authenticated_regular_client.post(f"/api/v1/queries/saved/{query_id}/execute")
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

        update_resp = authenticated_regular_client.put(
            f"/api/v1/queries/saved/{query_id}",
            json={"name": "No deberia poder"},
        )

        assert execute_resp.status_code == 200
        assert update_resp.status_code == 403

    def test_unassigned_role_cannot_access_query(
        self,
        db_session,
        test_roles,
        test_institution,
        authenticated_regular_client,
        authenticated_admin_client,
    ):
        outsider = _seed_user(
            db_session,
            role_id=test_roles["analyst"].id,
            institution_id=None,
            username="outsider",
            email="outsider@test.com",
        )
        ds = _seed_datasource(db_session, institution_id=None, code="LOCKED_DS")
        save_resp = authenticated_admin_client.post("/api/v1/queries/saved", json={
            "datasource_id": str(ds.id),
            "name": "Privada",
            "selected_columns": ["hogar_id"],
            "filters": [],
        })
        assert save_resp.status_code == 201
        query_id = save_resp.json()["data"]["id"]

        from api.v1.dependencies.auth_dependency import get_current_user, get_token_from_header
        from api.v1.dependencies.permission_dependency import RequirePermission

        def override_get_db():
            yield db_session

        def override_get_current_user():
            return outsider

        def override_get_token():
            return "mock_token"

        original_call = RequirePermission.__call__

        def mock_call(self, current_user=None):
            return outsider

        RequirePermission.__call__ = mock_call
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_token_from_header] = override_get_token
        app.dependency_overrides[get_sync_db_pg] = override_get_db

        try:
            with TestClient(app) as client:
                resp = client.get(f"/api/v1/queries/saved/{query_id}")
        finally:
            RequirePermission.__call__ = original_call
            app.dependency_overrides.clear()

        assert resp.status_code == 404


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
        mock_ch = _override_unused_ch()

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = authenticated_admin_client.post(f"/api/v1/queries/saved/{uuid4()}/execute")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_ch_client, None)


# ==================== Execute with GROUP BY ====================

class TestExecuteGroupBy:
    def test_execute_with_group_by(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        # Make departamento groupable
        for col in ds.columns_def:
            if col.column_name == "departamento":
                col.is_groupable = True
        db_session.commit()

        mock_ch = _mock_ch_client(
            count=2,
            rows=[["Guatemala", 100], ["Escuintla", 50]],
            col_names=["departamento", "count"],
        )

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = authenticated_admin_client.post("/api/v1/queries/execute", json={
                "datasource_id": str(ds.id),
                "columns": ["departamento"],
                "filters": [],
                "group_by": ["departamento"],
                "aggregations": [{"column": "*", "function": "COUNT"}],
                "offset": 0,
                "limit": 10,
            })
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["total"] == 2
            assert len(data["columns_meta"]) == 2
            assert data["columns_meta"][1]["column_name"] == "count"
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

    def test_execute_non_groupable_column_returns_400(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        mock_ch = _override_unused_ch()

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = authenticated_admin_client.post("/api/v1/queries/execute", json={
                "datasource_id": str(ds.id),
                "columns": ["hogar_id"],
                "filters": [],
                "group_by": ["hogar_id"],
                "aggregations": [{"column": "*", "function": "COUNT"}],
                "offset": 0,
                "limit": 10,
            })
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

    def test_group_by_without_aggregations_returns_400(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        for col in ds.columns_def:
            if col.column_name == "departamento":
                col.is_groupable = True
        db_session.commit()
        mock_ch = _override_unused_ch()

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = authenticated_admin_client.post("/api/v1/queries/execute", json={
                "datasource_id": str(ds.id),
                "columns": ["departamento"],
                "filters": [],
                "group_by": ["departamento"],
                "aggregations": [],
                "offset": 0,
                "limit": 10,
            })
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

    def test_aggregations_without_group_by_returns_400(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        mock_ch = _override_unused_ch()

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = authenticated_admin_client.post("/api/v1/queries/execute", json={
                "datasource_id": str(ds.id),
                "columns": ["departamento"],
                "filters": [],
                "group_by": [],
                "aggregations": [{"column": "*", "function": "COUNT"}],
                "offset": 0,
                "limit": 10,
            })
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

    def test_invalid_aggregation_column_returns_400(self, authenticated_admin_client, db_session, test_institution):
        ds = _seed_datasource(db_session, institution_id=test_institution.id)
        for col in ds.columns_def:
            if col.column_name == "departamento":
                col.is_groupable = True
        db_session.commit()
        mock_ch = _override_unused_ch()

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            resp = authenticated_admin_client.post("/api/v1/queries/execute", json={
                "datasource_id": str(ds.id),
                "columns": ["departamento"],
                "filters": [],
                "group_by": ["departamento"],
                "aggregations": [{"column": "*", "function": "COUNT"}, {"column": "no_existe", "function": "SUM"}],
                "offset": 0,
                "limit": 10,
            })
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_ch_client, None)
