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
        filters = BeneficiarioFilters(departamento_codigo="GUA")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] == 9
        for item in result["items"]:
            assert item["departamento_code"] == "GUA"

    def test_filtro_municipio(self):
        filters = BeneficiarioFilters(municipio_codigo="GUA-01")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] == 5
        for item in result["items"]:
            assert item["municipio_code"] == "GUA-01"

    def test_filtro_sexo_jefe(self):
        filters = BeneficiarioFilters(sexo_jefe="F")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] == 20
        for item in result["items"]:
            assert item["genero"] == "F"

    def test_filtro_rango_ipm(self):
        filters = BeneficiarioFilters(ipm_min=0.7, ipm_max=0.9)
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] > 0
        for item in result["items"]:
            assert 0.7 <= item["ipm"] <= 0.9

    def test_filtro_con_menores_5(self):
        filters = BeneficiarioFilters(tiene_menores_5=True)
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

    def test_filtro_departamento_y_sexo(self):
        filters = BeneficiarioFilters(departamento_codigo="GUA", sexo_jefe="F")
        result = list_beneficiarios(filters, offset=0, limit=100)
        assert result["total"] > 0
        for item in result["items"]:
            assert item["departamento_code"] == "GUA"
            assert item["genero"] == "F"


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
        filters = BeneficiarioFilters(departamento_codigo="GUA")
        stats = get_beneficiario_stats(filters)
        assert stats["total"] == 9
        assert "Guatemala" in stats["por_departamento"]


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
        filters = BeneficiarioFilters(departamento_codigo="GUA")
        enriched = get_filtered_enriched(filters)
        assert len(enriched) == 9
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
        filters = BeneficiarioFilters(sexo_jefe="F")
        enriched = get_filtered_enriched(filters)
        assert len(enriched) == 20
        buf = generate_pdf(enriched)
        data = buf.read()
        assert len(data) > 0
        assert data[:4] == b"%PDF"
