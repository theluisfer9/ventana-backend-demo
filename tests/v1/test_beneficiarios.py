"""
Tests para el modulo de beneficiarios (demo con datos hardcoded).
TDD: estos tests se escriben ANTES de la implementacion.
"""
import pytest
from io import BytesIO

from api.v1.schemas.beneficiario import BeneficiarioFilters


# =====================================================================
# HELPER: importar service functions
# =====================================================================
from api.v1.services.beneficiario import (
    list_beneficiarios,
    get_beneficiario_by_id,
    get_beneficiario_stats,
    get_dashboard_stats,
    get_catalogos,
    get_municipios_by_departamento,
    get_filtered_enriched,
)
from api.v1.services.beneficiario.export import generate_excel, generate_pdf


# =====================================================================
# SERVICE TESTS: funciones puras sobre listas en memoria
# =====================================================================

class TestBeneficiarioServicePagination:
    """Tests de paginacion del servicio."""

    def test_list_sin_filtros_retorna_todos(self):
        filters = BeneficiarioFilters()
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] == 40
        assert len(result["items"]) == 40

    def test_list_con_limit(self):
        filters = BeneficiarioFilters()
        result = list_beneficiarios(filters, offset=0, limit=10)
        assert result["total"] == 40
        assert len(result["items"]) == 10

    def test_list_segunda_pagina(self):
        filters = BeneficiarioFilters()
        result = list_beneficiarios(filters, offset=10, limit=10)
        assert result["total"] == 40
        assert len(result["items"]) == 10
        # First item should be id=11 (11th record)
        assert result["items"][0]["id"] == 11


class TestBeneficiarioServiceFilters:
    """Tests de filtros individuales del servicio."""

    def test_filtro_departamento(self):
        filters = BeneficiarioFilters(departamento_code="GUA")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] == 5
        for item in result["items"]:
            assert item["departamento_code"] == "GUA"

    def test_filtro_municipio(self):
        filters = BeneficiarioFilters(municipio_code="GUA-01")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] == 3
        for item in result["items"]:
            assert item["municipio_code"] == "GUA-01"

    def test_filtro_genero_femenino(self):
        filters = BeneficiarioFilters(genero="F")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] == 20
        for item in result["items"]:
            assert item["genero"] == "F"

    def test_filtro_rango_edad(self):
        filters = BeneficiarioFilters(edad_min=60, edad_max=80)
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] > 0
        for item in result["items"]:
            assert 60 <= item["edad"] <= 80

    def test_filtro_nivel_privacion(self):
        filters = BeneficiarioFilters(nivel_privacion="extrema")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] > 0
        for item in result["items"]:
            assert item["nivel_privacion"] == "extrema"

    def test_filtro_rango_ipm(self):
        filters = BeneficiarioFilters(ipm_min=0.7, ipm_max=0.9)
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] > 0
        for item in result["items"]:
            assert 0.7 <= item["ipm"] <= 0.9

    def test_filtro_institucion(self):
        filters = BeneficiarioFilters(institucion_code="MIDES")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] > 0
        for item in result["items"]:
            institucion_codes = [i["institucion_code"] for i in item["intervenciones"]]
            assert "MIDES" in institucion_codes

    def test_filtro_sin_intervencion(self):
        filters = BeneficiarioFilters(sin_intervencion=True)
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] > 0
        for item in result["items"]:
            assert len(item["intervenciones"]) == 0

    def test_filtro_con_menores_5(self):
        filters = BeneficiarioFilters(con_menores_5=True)
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] > 0
        for item in result["items"]:
            assert item["menores_5"] > 0

    def test_busqueda_por_nombre(self):
        filters = BeneficiarioFilters(buscar="Maria Isabel")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] >= 1
        nombres = [item["nombre_completo"] for item in result["items"]]
        assert any("Maria" in n and "Isabel" in n for n in nombres)


class TestBeneficiarioServiceFiltersCombinados:
    """Tests de filtros combinados."""

    def test_filtro_departamento_y_genero(self):
        filters = BeneficiarioFilters(departamento_code="GUA", genero="F")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] > 0
        for item in result["items"]:
            assert item["departamento_code"] == "GUA"
            assert item["genero"] == "F"

    def test_filtro_imposible_resultado_vacio(self):
        filters = BeneficiarioFilters(
            departamento_code="GUA",
            nivel_privacion="extrema",
            genero="M",
        )
        result = list_beneficiarios(filters, offset=0, limit=100)
        # No male in GUA with extrema (only id=5 is F with extrema in GUA)
        assert result["total"] == 0
        assert len(result["items"]) == 0


class TestBeneficiarioServiceDetalle:
    """Tests de detalle de beneficiario."""

    def test_detalle_existente(self):
        result = get_beneficiario_by_id(1)
        assert result is not None
        assert result["id"] == 1
        assert result["dpi"] == "1234567890101"

    def test_detalle_inexistente(self):
        result = get_beneficiario_by_id(9999)
        assert result is None

    def test_detalle_nombres_enriquecidos(self):
        result = get_beneficiario_by_id(1)
        assert "nombre_completo" in result
        assert "Maria" in result["nombre_completo"]
        assert "Lopez" in result["nombre_completo"]
        # Tiene nombres de departamento y municipio
        assert "departamento" in result
        assert "municipio" in result
        assert result["departamento"] == "Guatemala"


class TestBeneficiarioServiceStats:
    """Tests de estadisticas."""

    def test_stats_sin_filtro(self):
        filters = BeneficiarioFilters()
        stats = get_beneficiario_stats(filters)
        assert stats["total"] == 40
        assert stats["promedio_ipm"] > 0
        assert stats["genero_f"] + stats["genero_m"] == 40
        assert "por_nivel_privacion" in stats
        assert "por_departamento" in stats

    def test_stats_con_filtro(self):
        filters = BeneficiarioFilters(departamento_code="GUA")
        stats = get_beneficiario_stats(filters)
        assert stats["total"] == 5
        assert "Guatemala" in stats["por_departamento"]

    def test_stats_vacio(self):
        filters = BeneficiarioFilters(
            departamento_code="GUA", nivel_privacion="extrema", genero="M"
        )
        stats = get_beneficiario_stats(filters)
        assert stats["total"] == 0
        assert stats["promedio_ipm"] == 0


class TestBeneficiarioServiceDashboard:
    """Tests del dashboard."""

    def test_dashboard_retorna_datos_validos(self):
        stats = get_dashboard_stats()
        assert stats["total_beneficiarios"] == 40
        assert stats["departamentos_cubiertos"] == 8
        assert 0 <= stats["cobertura_intervenciones"] <= 100
        assert stats["promedio_ipm"] > 0
        assert len(stats["por_departamento"]) == 8
        assert len(stats["top_intervenciones"]) > 0


class TestBeneficiarioServiceCatalogos:
    """Tests de catalogos."""

    def test_catalogos_completos(self):
        catalogos = get_catalogos()
        assert len(catalogos["departamentos"]) == 8
        assert len(catalogos["instituciones"]) == 5
        assert len(catalogos["tipos_intervencion"]) == 6
        assert len(catalogos["niveles_privacion"]) == 4

    def test_municipios_por_departamento(self):
        municipios = get_municipios_by_departamento("GUA")
        assert len(municipios) == 2
        codes = [m["code"] for m in municipios]
        assert "GUA-01" in codes
        assert "GUA-02" in codes

    def test_municipios_departamento_invalido(self):
        municipios = get_municipios_by_departamento("INEXISTENTE")
        assert len(municipios) == 0


# =====================================================================
# ROUTE INTEGRATION TESTS (con authenticated_admin_client)
# =====================================================================

class TestBeneficiarioRoutesList:
    """Tests de integracion del endpoint de lista."""

    def test_list_sin_filtros(self, authenticated_admin_client):
        resp = authenticated_admin_client.get("/api/v1/beneficiarios/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 40
        assert len(data["items"]) > 0

    def test_list_filtro_departamento(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(
            "/api/v1/beneficiarios/?departamento_code=GUA"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5

    def test_list_paginacion(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(
            "/api/v1/beneficiarios/?offset=0&limit=5"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 40
        assert len(data["items"]) == 5


class TestBeneficiarioRoutesDetalle:
    """Tests de integracion del endpoint de detalle."""

    def test_detalle_existente(self, authenticated_admin_client):
        resp = authenticated_admin_client.get("/api/v1/beneficiarios/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == 1
        assert "nombre_completo" in data

    def test_detalle_404(self, authenticated_admin_client):
        resp = authenticated_admin_client.get("/api/v1/beneficiarios/9999")
        assert resp.status_code == 404


class TestBeneficiarioRoutesStats:
    """Tests de integracion del endpoint de stats."""

    def test_stats_sin_filtro(self, authenticated_admin_client):
        resp = authenticated_admin_client.get("/api/v1/beneficiarios/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 40

    def test_stats_con_filtro(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(
            "/api/v1/beneficiarios/stats?departamento_code=QUE"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5


class TestBeneficiarioRoutesDashboard:
    """Tests de integracion del dashboard."""

    def test_dashboard(self, authenticated_admin_client):
        resp = authenticated_admin_client.get("/api/v1/beneficiarios/dashboard")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_beneficiarios"] == 40
        assert data["departamentos_cubiertos"] == 8


class TestBeneficiarioRoutesCatalogos:
    """Tests de integracion de catalogos."""

    def test_catalogos(self, authenticated_admin_client):
        resp = authenticated_admin_client.get("/api/v1/beneficiarios/catalogos")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["departamentos"]) == 8

    def test_municipios_cascada(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(
            "/api/v1/beneficiarios/catalogos/municipios?departamento_code=GUA"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2


class TestBeneficiarioRoutesBusqueda:
    """Tests de integracion de busqueda."""

    def test_busqueda_por_nombre(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(
            "/api/v1/beneficiarios/?buscar=Maria"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1


# =====================================================================
# EXPORT SERVICE TESTS
# =====================================================================

class TestBeneficiarioExportExcel:
    """Tests de generacion de Excel."""

    def test_excel_sin_filtro(self):
        filters = BeneficiarioFilters()
        enriched = get_filtered_enriched(filters)
        buf = generate_excel(enriched)
        assert isinstance(buf, BytesIO)
        data = buf.read()
        assert len(data) > 0
        # Los archivos xlsx comienzan con el magic number PK (ZIP)
        assert data[:2] == b"PK"

    def test_excel_con_filtro(self):
        filters = BeneficiarioFilters(departamento_code="GUA")
        enriched = get_filtered_enriched(filters)
        assert len(enriched) == 5
        buf = generate_excel(enriched)
        data = buf.read()
        assert len(data) > 0
        assert data[:2] == b"PK"


class TestBeneficiarioExportPdf:
    """Tests de generacion de PDF."""

    def test_pdf_sin_filtro(self):
        filters = BeneficiarioFilters()
        enriched = get_filtered_enriched(filters)
        buf = generate_pdf(enriched)
        assert isinstance(buf, BytesIO)
        data = buf.read()
        assert len(data) > 0
        # Los PDFs comienzan con %PDF
        assert data[:4] == b"%PDF"

    def test_pdf_con_filtro(self):
        filters = BeneficiarioFilters(genero="F")
        enriched = get_filtered_enriched(filters)
        assert len(enriched) == 20
        buf = generate_pdf(enriched)
        data = buf.read()
        assert len(data) > 0
        assert data[:4] == b"%PDF"


# =====================================================================
# EXPORT ROUTE INTEGRATION TESTS
# =====================================================================

class TestBeneficiarioRoutesExport:
    """Tests de integracion de los endpoints de exportacion."""

    def test_export_excel_sin_filtro(self, authenticated_admin_client):
        resp = authenticated_admin_client.get("/api/v1/beneficiarios/export/excel")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert resp.content[:2] == b"PK"

    def test_export_excel_con_filtro(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(
            "/api/v1/beneficiarios/export/excel?departamento_code=GUA"
        )
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]

    def test_export_pdf_sin_filtro(self, authenticated_admin_client):
        resp = authenticated_admin_client.get("/api/v1/beneficiarios/export/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_export_pdf_con_filtro(self, authenticated_admin_client):
        resp = authenticated_admin_client.get(
            "/api/v1/beneficiarios/export/pdf?genero=F"
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
