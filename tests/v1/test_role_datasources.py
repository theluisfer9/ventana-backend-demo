"""
Integration tests for role-datasource assignment endpoints.
"""
import pytest
from api.v1.models.data_source import DataSource, DataSourceColumn, ColumnDataType, ColumnCategory, RoleDataSource
from api.v1.models.role import Role


def _seed_datasource(db_session, code="RD_DS", name="Test DS"):
    ds = DataSource(
        code=code, name=name, ch_table="rsh.test_table",
        base_filter=None, is_active=True,
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

        # Get admin role
        role = db_session.query(Role).filter(Role.code == "ADMIN").first()
        assert role is not None

        # Assign
        resp = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": [str(ds1.id), str(ds2.id)]},
        )
        assert resp.status_code == 200

        # Get
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
        authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}/datasources",
            json={"datasource_ids": [str(ds2.id)]},
        )

        resp = authenticated_admin_client.get(f"/api/v1/roles/{role.id}/datasources")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["code"] == "RP_DS2"

    def test_nonexistent_role_returns_404(self, authenticated_admin_client):
        from uuid import uuid4
        resp = authenticated_admin_client.get(f"/api/v1/roles/{uuid4()}/datasources")
        assert resp.status_code == 404
