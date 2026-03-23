from unittest.mock import MagicMock

from main import app
from api.v1.config.database import get_ch_client
def _mock_query_builder_ch_client(count=2, rows=None, col_names=None):
    client = MagicMock()
    count_result = MagicMock()
    count_result.result_rows = [[count]]
    data_result = MagicMock()
    data_result.column_names = col_names or ["hogar_id", "departamento"]
    data_result.result_rows = rows or [[1, "Guatemala"], [2, "Escuintla"]]
    client.query = MagicMock(side_effect=[count_result, data_result])
    return client


class TestAuditEvents:
    def test_beneficiarios_list_registers_audit_event(
        self,
        authenticated_ch_client,
    ):
        response = authenticated_ch_client.get(
            "/api/v1/beneficiarios/",
            params={"limit": 5, "departamento_codigo": "01"},
        )
        assert response.status_code == 200

        audit_response = authenticated_ch_client.get(
            "/api/v1/audit-events/",
            params={"module": "beneficiarios"},
        )
        assert audit_response.status_code == 200
        items = audit_response.json()["data"]
        assert len(items) == 1
        assert items[0]["event_type"] == "query"
        assert items[0]["action"] == "list"
        assert items[0]["module"] == "beneficiarios"
        assert items[0]["username"] == "admin"
        assert items[0]["institution_name"] == "Test Institution"
        assert items[0]["query_params"]["departamento_codigo"] == "01"
        assert items[0]["status"] == "success"

    def test_beneficiarios_export_registers_audit_event(
        self,
        authenticated_ch_client,
    ):
        response = authenticated_ch_client.get(
            "/api/v1/beneficiarios/export/csv",
            params={"departamento_codigo": "01"},
        )
        assert response.status_code == 200

        audit_response = authenticated_ch_client.get(
            "/api/v1/audit-events/",
            params={"module": "beneficiarios", "event_type": "export"},
        )
        assert audit_response.status_code == 200
        items = audit_response.json()["data"]
        assert len(items) == 1
        assert items[0]["action"] == "export_csv"
        assert items[0]["payload_summary"]["format"] == "csv"

    def test_query_builder_execute_registers_audit_event(
        self,
        authenticated_admin_client,
        db_session,
        test_institution,
    ):
        from tests.v1.test_query_routes import _seed_datasource

        datasource = _seed_datasource(db_session, institution_id=test_institution.id)
        mock_ch = _mock_query_builder_ch_client()

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            response = authenticated_admin_client.post(
                "/api/v1/queries/execute",
                json={
                    "datasource_id": str(datasource.id),
                    "columns": ["hogar_id", "departamento"],
                    "filters": [],
                    "offset": 0,
                    "limit": 10,
                },
            )
            assert response.status_code == 200

            audit_response = authenticated_admin_client.get(
                "/api/v1/audit-events/",
                params={"module": "query_builder"},
            )
            assert audit_response.status_code == 200
            items = audit_response.json()["data"]
            assert len(items) == 1
            assert items[0]["event_type"] == "query"
            assert items[0]["action"] == "execute"
            assert items[0]["result_count"] == 2
            assert items[0]["resource_label"] == "Datasource: Query Test DS"
        finally:
            app.dependency_overrides.pop(get_ch_client, None)


class TestSystemCatalogs:
    def test_admin_can_create_catalog_and_item(self, authenticated_admin_client):
        create_catalog = authenticated_admin_client.post(
            "/api/v1/system-catalogs/",
            json={
                "code": "dashboard_quick_links",
                "name": "Accesos rápidos dashboard",
                "description": "Links administrables para la portada",
            },
        )
        assert create_catalog.status_code == 201
        catalog = create_catalog.json()["data"]
        assert catalog["code"] == "dashboard_quick_links"

        create_item = authenticated_admin_client.post(
            f"/api/v1/system-catalogs/{catalog['id']}/items",
            json={
                "code": "beneficiarios",
                "name": "Beneficiarios",
                "description": "Acceso al módulo de beneficiarios",
                "value": {"path": "/beneficiarios", "icon": "beneficiaries"},
                "display_order": 10,
            },
        )
        assert create_item.status_code == 201
        item = create_item.json()["data"]
        assert item["code"] == "beneficiarios"
        assert item["value"]["path"] == "/beneficiarios"

        list_catalogs = authenticated_admin_client.get("/api/v1/system-catalogs/")
        assert list_catalogs.status_code == 200
        assert len(list_catalogs.json()["data"]) == 1

        list_items = authenticated_admin_client.get(
            f"/api/v1/system-catalogs/{catalog['id']}/items"
        )
        assert list_items.status_code == 200
        items = list_items.json()["data"]
        assert len(items) == 1
        assert items[0]["display_order"] == 10

    def test_unauthenticated_user_cannot_manage_system_catalogs(self, client):
        response = client.get("/api/v1/system-catalogs/")
        assert response.status_code in (401, 403)
