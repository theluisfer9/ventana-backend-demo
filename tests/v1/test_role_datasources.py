"""
Integration tests for role-datasource assignment endpoints.
"""
import pytest
from uuid import uuid4
from api.v1.models.data_source import DataSource, DataSourceColumn, ColumnDataType, ColumnCategory, RoleDataSource
from api.v1.models.role import Role


def _seed_datasource(db_session, code="RD_DS", name="Test DS", is_active=True):
    ds = DataSource(
        code=code, name=name, ch_table="rsh.test_table",
        base_filter_columns=[], base_filter_logic="OR", is_active=is_active,
    )
    db_session.add(ds)
    db_session.flush()
    col = DataSourceColumn(
        datasource_id=ds.id, column_name="col1", label="Col 1",
        data_type=ColumnDataType.TEXT, category=ColumnCategory.DIMENSION,
        is_selectable=True, is_filterable=True, display_order=1,
    )
    db_session.add(col)
    db_session.commit()
    db_session.refresh(ds)
    return ds


class TestRoleDataSources:
    def test_assign_and_get_datasources(self, authenticated_admin_client, db_session):
        ds1 = _seed_datasource(db_session, code="RD_DS1", name="DS 1")
        ds2 = _seed_datasource(db_session, code="RD_DS2", name="DS 2")

        role = db_session.query(Role).filter(Role.code == "ADMIN").first()
        assert role is not None

        # Assign — PUT now returns the updated list
        resp = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": [str(ds1.id), str(ds2.id)]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        codes = [d["code"] for d in data]
        assert "RD_DS1" in codes
        assert "RD_DS2" in codes

        # GET returns same
        resp = authenticated_admin_client.get(f"/api/v1/roles/{role.id}/datasources")
        assert resp.status_code == 200
        data = resp.json()["data"]
        codes = [d["code"] for d in data]
        assert "RD_DS1" in codes
        assert "RD_DS2" in codes

    def test_replace_datasources(self, authenticated_admin_client, db_session):
        ds1 = _seed_datasource(db_session, code="RP_DS1", name="DS 1")
        ds2 = _seed_datasource(db_session, code="RP_DS2", name="DS 2")

        role = db_session.query(Role).filter(Role.code == "ADMIN").first()

        # Assign both
        authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": [str(ds1.id), str(ds2.id)]},
        )

        # Replace with only ds2
        resp = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": [str(ds2.id)]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["code"] == "RP_DS2"

    def test_clear_all_datasources(self, authenticated_admin_client, db_session):
        ds = _seed_datasource(db_session, code="CLR_DS", name="DS Clear")
        role = db_session.query(Role).filter(Role.code == "ADMIN").first()

        # Assign one
        authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": [str(ds.id)]},
        )

        # Clear all
        resp = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": []},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_nonexistent_role_returns_404(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(f"/api/v1/roles/{uuid4()}/datasources")
        assert resp.status_code == 404

    def test_nonexistent_datasource_returns_400(self, authenticated_admin_client, db_session):
        role = db_session.query(Role).filter(Role.code == "ADMIN").first()
        resp = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": [str(uuid4())]},
        )
        assert resp.status_code == 400

    def test_inactive_datasource_returns_400(self, authenticated_admin_client, db_session):
        ds = _seed_datasource(db_session, code="INACT_DS", name="Inactive", is_active=False)
        role = db_session.query(Role).filter(Role.code == "ADMIN").first()
        resp = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": [str(ds.id)]},
        )
        assert resp.status_code == 400

    def test_invalid_uuid_returns_422(self, authenticated_admin_client, db_session):
        role = db_session.query(Role).filter(Role.code == "ADMIN").first()
        resp = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": ["not-a-uuid"]},
        )
        assert resp.status_code == 422

    def test_duplicate_ids_deduplicated(self, authenticated_admin_client, db_session):
        ds = _seed_datasource(db_session, code="DUP_DS", name="Dup DS")
        role = db_session.query(Role).filter(Role.code == "ADMIN").first()
        resp = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": [str(ds.id), str(ds.id)]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
