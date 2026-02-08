"""
Tests para endpoints RSH de beneficiarios con mock ClickHouse.
"""
import pytest

BASE = "/api/v1/beneficiarios"


# ========================= TestCatalogos ============================

class TestCatalogos:
    """Tests para endpoints de catalogos."""

    def test_catalogos(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(f"{BASE}/catalogos")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "departamentos" in data
        assert len(data["departamentos"]) > 0
        assert "code" in data["departamentos"][0]
        assert "name" in data["departamentos"][0]
        assert "clasificaciones_ipm" in data
        assert "clasificaciones_pmt" in data
        assert "clasificaciones_nbi" in data
        assert "areas" in data
        assert "niveles_inseguridad" in data
        assert "fases" in data
        assert "comunidades_linguisticas" in data
        assert "pueblos" in data
        assert "fuentes_agua" in data
        assert "tipos_sanitario" in data
        assert "tipos_alumbrado" in data
        assert "combustibles_cocina" in data

    def test_municipios_por_departamento(self, authenticated_ch_client, mock_ch):
        # Usar un departamento que existe en el dataset
        depto = mock_ch.dataset.hogares[0]["departamento_codigo"]
        resp = authenticated_ch_client.get(
            f"{BASE}/catalogos/municipios",
            params={"departamento_codigo": depto},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        assert "code" in data[0]
        assert "name" in data[0]

    def test_lugares_poblados_por_municipio(self, authenticated_ch_client, mock_ch):
        muni = mock_ch.dataset.hogares[0]["municipio_codigo"]
        resp = authenticated_ch_client.get(
            f"{BASE}/catalogos/lugares-poblados",
            params={"municipio_codigo": muni},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        assert "code" in data[0]
        assert "name" in data[0]


# ========================= TestDashboard ============================

class TestDashboard:
    """Tests para el endpoint de dashboard."""

    def test_dashboard(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(f"{BASE}/dashboard")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_hogares"] == len(mock_ch.dataset.hogares)
        assert data["departamentos_cubiertos"] > 0
        assert data["municipios_cubiertos"] > 0
        assert data["promedio_ipm"] > 0
        assert data["total_personas"] > 0
        assert isinstance(data["por_departamento"], list)
        assert isinstance(data["inseguridad_alimentaria"], list)


# ========================= TestStats ================================

class TestStats:
    """Tests para el endpoint de estadisticas."""

    def test_stats_sin_filtros(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(f"{BASE}/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == len(mock_ch.dataset.hogares)
        assert data["promedio_ipm"] > 0
        assert data["total_personas"] > 0
        assert data["total_hombres"] > 0
        assert data["total_mujeres"] > 0
        assert isinstance(data["por_departamento"], list)
        assert isinstance(data["por_ipm_clasificacion"], list)

    def test_stats_con_filtro_departamento(self, authenticated_ch_client, mock_ch):
        depto = mock_ch.dataset.hogares[0]["departamento_codigo"]
        resp = authenticated_ch_client.get(
            f"{BASE}/stats",
            params={"departamento_codigo": depto},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] > 0
        # Total filtrado debe ser <= total general
        assert data["total"] <= len(mock_ch.dataset.hogares)

    def test_stats_con_filtro_ipm(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(
            f"{BASE}/stats",
            params={"ipm_clasificacion": "Pobre"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] > 0


# ========================= TestLista ================================

class TestLista:
    """Tests para el listado paginado de beneficiarios."""

    def test_lista_default(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(f"{BASE}/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert data["total"] == len(mock_ch.dataset.hogares)
        assert len(data["items"]) <= data["limit"]

    def test_lista_paginacion(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(
            f"{BASE}/",
            params={"offset": 0, "limit": 5},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 5
        assert data["offset"] == 0
        assert data["limit"] == 5

    def test_lista_paginacion_offset(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(
            f"{BASE}/",
            params={"offset": 5, "limit": 5},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 5
        assert data["offset"] == 5

    def test_lista_con_filtro_departamento(self, authenticated_ch_client, mock_ch):
        depto = mock_ch.dataset.hogares[0]["departamento_codigo"]
        resp = authenticated_ch_client.get(
            f"{BASE}/",
            params={"departamento_codigo": depto},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] > 0
        for item in data["items"]:
            assert item["departamento_codigo"] == depto

    def test_lista_item_schema(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(
            f"{BASE}/",
            params={"limit": 1},
        )
        assert resp.status_code == 200
        item = resp.json()["data"]["items"][0]
        assert "hogar_id" in item
        assert "nombre_completo" in item
        assert "departamento" in item
        assert "municipio" in item
        assert "ipm_gt" in item
        assert "ipm_gt_clasificacion" in item
        assert "numero_personas" in item


# ========================= TestDetalle ==============================

class TestDetalle:
    """Tests para el detalle de un beneficiario."""

    def test_detalle_existente(self, authenticated_ch_client, mock_ch):
        hogar_id = mock_ch.dataset.get_first_hogar_id()
        resp = authenticated_ch_client.get(f"{BASE}/{hogar_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hogar_id"] == hogar_id
        assert "nombre_completo" in data
        assert "departamento" in data
        assert "ipm_gt" in data
        # Campos de detalle (del JOIN con demograficos)
        assert "comunidad_linguistica" in data
        assert "pueblo_de_pertenencia" in data
        # Campos de inseguridad alimentaria
        assert "nivel_inseguridad_alimentaria" in data

    def test_detalle_no_existente(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(f"{BASE}/{mock_ch.dataset.get_nonexistent_hogar_id()}")
        assert resp.status_code == 404


# ========================= TestPersonas =============================

class TestPersonas:
    """Tests para personas de un hogar."""

    def test_personas_hogar(self, authenticated_ch_client, mock_ch):
        hogar_id = mock_ch.dataset.get_first_hogar_id()
        resp = authenticated_ch_client.get(f"{BASE}/{hogar_id}/personas")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        persona = data[0]
        assert "personas_id" in persona
        assert "nombre_completo" in persona
        assert "genero" in persona
        assert "edad" in persona
        assert "parentesco" in persona
        assert "sabe_leer_escribir" in persona

    def test_personas_hogar_inexistente(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(f"{BASE}/{mock_ch.dataset.get_nonexistent_hogar_id()}/personas")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == []


# ========================= TestVivienda =============================

class TestVivienda:
    """Tests para vivienda de un hogar."""

    def test_vivienda_hogar(self, authenticated_ch_client, mock_ch):
        hogar_id = mock_ch.dataset.get_first_hogar_id()
        resp = authenticated_ch_client.get(f"{BASE}/{hogar_id}/vivienda")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "condicion_vivienda" in data
        assert "tipo_vivienda" in data
        assert "material_paredes" in data
        assert "fuente_agua" in data
        assert "tipo_sanitario" in data
        assert "alumbrado" in data
        # Bienes
        assert "radio" in data
        assert "internet" in data
        assert "computadora" in data
        # Seguridad alimentaria
        assert "preocupacion_alimentos" in data
        assert "adulto_sin_alimentacion_saludable" in data

    def test_vivienda_hogar_inexistente(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(f"{BASE}/{mock_ch.dataset.get_nonexistent_hogar_id()}/vivienda")
        assert resp.status_code == 404


# ========================= TestExport ===============================

class TestExport:
    """Tests para exportacion Excel y PDF."""

    def test_export_excel(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(f"{BASE}/export/excel")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert len(resp.content) > 0

    def test_export_excel_con_filtro(self, authenticated_ch_client, mock_ch):
        depto = mock_ch.dataset.hogares[0]["departamento_codigo"]
        resp = authenticated_ch_client.get(
            f"{BASE}/export/excel",
            params={"departamento_codigo": depto},
        )
        assert resp.status_code == 200
        assert len(resp.content) > 0

    def test_export_pdf(self, authenticated_ch_client, mock_ch):
        resp = authenticated_ch_client.get(f"{BASE}/export/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert len(resp.content) > 0

    def test_export_pdf_con_filtro(self, authenticated_ch_client, mock_ch):
        depto = mock_ch.dataset.hogares[0]["departamento_codigo"]
        resp = authenticated_ch_client.get(
            f"{BASE}/export/pdf",
            params={"departamento_codigo": depto},
        )
        assert resp.status_code == 200
        assert len(resp.content) > 0


# ========================= TestMappers ==============================

class TestMappers:
    """Tests unitarios de las funciones row_to_* (sin HTTP)."""

    def test_row_to_beneficiario_resumen(self, mock_ch):
        from api.v1.services.rsh.mappers import row_to_beneficiario_resumen
        hogar = mock_ch.dataset.hogares[0]
        result = row_to_beneficiario_resumen(hogar)
        assert result["hogar_id"] == hogar["hogar_id"]
        assert result["nombre_completo"] == hogar["nombre_jefe_hogar"].strip()
        assert result["departamento"] == hogar["departamento"]
        assert isinstance(result["ipm_gt"], float)

    def test_row_to_beneficiario_detalle(self, mock_ch):
        from api.v1.services.rsh.mappers import row_to_beneficiario_detalle
        hogar = mock_ch.dataset.hogares[0]
        demo = mock_ch.dataset.get_demografico(hogar["hogar_id"])
        inseg = mock_ch.dataset.get_inseguridad(hogar["hogar_id"])
        merged = {**hogar, **demo, **inseg}
        result = row_to_beneficiario_detalle(merged)
        assert result["hogar_id"] == hogar["hogar_id"]
        assert "comunidad_linguistica" in result
        assert "nivel_inseguridad_alimentaria" in result
        assert result["anio"] in [2023, 2024]

    def test_row_to_persona(self, mock_ch):
        from api.v1.services.rsh.mappers import row_to_persona
        persona = mock_ch.dataset.personas[0]
        result = row_to_persona(persona)
        assert result["personas_id"] == persona["personas_id"]
        assert len(result["nombre_completo"]) > 0
        assert "genero" in result
        assert "parentesco" in result
        assert "sabe_leer_escribir" in result

    def test_row_to_vivienda(self, mock_ch):
        from api.v1.services.rsh.mappers import row_to_vivienda
        viv = mock_ch.dataset.viviendas[0]
        result = row_to_vivienda(viv)
        assert "condicion_vivienda" in result
        assert "tipo_vivienda" in result
        assert "fuente_agua" in result
        assert "radio" in result
        assert "preocupacion_alimentos" in result
        assert isinstance(result["personas_hogar"], int)
