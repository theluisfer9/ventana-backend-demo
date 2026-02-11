from pydantic import BaseModel
from typing import Optional


# -- Filtros ------------------------------------------------------------------

class ConsultaFilters(BaseModel):
    """Filtros geograficos y de busqueda para consulta institucional."""
    departamento_codigo: Optional[str] = None
    municipio_codigo: Optional[str] = None
    buscar: Optional[str] = None


# -- Paginacion ---------------------------------------------------------------

class PaginatedConsulta(BaseModel):
    """Respuesta paginada con items dinamicos (columnas segun preset)."""
    items: list[dict]
    total: int
    offset: int
    limit: int


# -- Dashboard stats ----------------------------------------------------------

class DepartamentoCount(BaseModel):
    departamento: str
    codigo: str
    cantidad: int


class IntervencionCount(BaseModel):
    intervencion: str
    cantidad: int


class ConsultaDashboardStats(BaseModel):
    """Estadisticas del dashboard institucional."""
    total_hogares: int = 0
    departamentos_cubiertos: int = 0
    municipios_cubiertos: int = 0
    total_personas: int = 0
    por_departamento: list[DepartamentoCount] = []
    por_intervencion: list[IntervencionCount] = []


# -- Catalogos ----------------------------------------------------------------

class CatalogoItem(BaseModel):
    code: str
    name: str


class ConsultaCatalogosResponse(BaseModel):
    departamentos: list[CatalogoItem] = []
    municipios: list[CatalogoItem] = []


# -- Preset info --------------------------------------------------------------

class InstitutionPresetInfo(BaseModel):
    """Info del preset institucional para el frontend."""
    institution_code: str
    name: str
    table: str
    columns: list[str]
    intervention_columns: list[str]
    allowed_filters: list[str]
    labels: dict[str, str]
