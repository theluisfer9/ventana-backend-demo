from unittest.mock import MagicMock

from main import app
from api.v1.config.database import get_ch_client


def _mock_ch_client(count=2, rows=None, col_names=None):
    client = MagicMock()
    count_result = MagicMock()
    count_result.result_rows = [[count]]
    data_result = MagicMock()
    data_result.column_names = col_names or [
        "hogar_id",
        "ig3_departamento",
        "ig3_codigo_departamento",
        "ig4_municipio",
        "ig4_codigo_municipio",
        "ig6_lugar_poblado",
        "ig8_area",
        "personas",
        "hombres",
        "mujeres",
        "ipm_gt",
        "ipm_gt_clasificacion",
        "estufa_mejorada",
        "ecofiltro",
        "letrina",
        "repello",
        "piso",
    ]
    data_result.result_rows = rows or [
        [1, "Guatemala", "01", "Guatemala", "0101", "Zona 1", "Urbano", 4, 2, 2, 0.4, "Pobre", 1, 0, 0, 0, 1],
        [2, "Escuintla", "05", "Escuintla", "0501", "Centro", "Urbano", 3, 1, 2, 0.2, "No pobre", 0, 1, 0, 0, 0],
    ]
    client.query = MagicMock(side_effect=[count_result, data_result])
    return client


class TestInstitutionApiTokens:
    def test_create_list_and_revoke_api_token(self, authenticated_admin_client, test_institution):
        create_resp = authenticated_admin_client.post(
            f"/api/v1/institutions/{test_institution.id}/api-tokens",
            json={"name": "Token Integracion", "expires_in_days": 30},
        )
        assert create_resp.status_code == 201
        created = create_resp.json()["data"]
        assert created["name"] == "Token Integracion"
        assert created["token"].startswith("inst_")

        list_resp = authenticated_admin_client.get(
            f"/api/v1/institutions/{test_institution.id}/api-tokens"
        )
        assert list_resp.status_code == 200
        items = list_resp.json()["data"]
        assert len(items) == 1
        assert items[0]["token_prefix"] == created["token_prefix"]

        revoke_resp = authenticated_admin_client.delete(
            f"/api/v1/institutions/{test_institution.id}/api-tokens/{created['id']}"
        )
        assert revoke_resp.status_code == 200

    def test_integration_consulta_requires_token(self, client):
        resp = client.get("/api/v1/integration/consulta/preset")
        assert resp.status_code == 401

    def test_integration_consulta_with_valid_token(
        self,
        authenticated_admin_client,
        test_institution,
        db_session,
    ):
        test_institution.code = "FODES"
        db_session.commit()

        create_resp = authenticated_admin_client.post(
            f"/api/v1/institutions/{test_institution.id}/api-tokens",
            json={"name": "Token Integracion"},
        )
        token = create_resp.json()["data"]["token"]
        mock_ch = _mock_ch_client()

        def override_ch():
            yield mock_ch

        app.dependency_overrides[get_ch_client] = override_ch
        try:
            preset_resp = authenticated_admin_client.get(
                "/api/v1/integration/consulta/preset",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert preset_resp.status_code == 200
            preset = preset_resp.json()["data"]
            assert preset["institution_code"] == "FODES"

            list_resp = authenticated_admin_client.get(
                "/api/v1/integration/consulta/",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert list_resp.status_code == 200
            data = list_resp.json()["data"]
            assert data["total"] == 2
            assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.pop(get_ch_client, None)

    def test_integration_consulta_rejects_revoked_token(
        self,
        authenticated_admin_client,
        test_institution,
        db_session,
    ):
        test_institution.code = "FODES"
        db_session.commit()

        create_resp = authenticated_admin_client.post(
            f"/api/v1/institutions/{test_institution.id}/api-tokens",
            json={"name": "Token Revocable"},
        )
        created = create_resp.json()["data"]
        token = created["token"]

        authenticated_admin_client.delete(
            f"/api/v1/institutions/{test_institution.id}/api-tokens/{created['id']}"
        )

        resp = authenticated_admin_client.get(
            "/api/v1/integration/consulta/preset",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
