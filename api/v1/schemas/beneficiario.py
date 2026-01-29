from pydantic import BaseModel, Field
from typing import Optional, List


# ── Catalogos ─────────────────────────────────────────────────────────

class CatalogoOut(BaseModel):
    code: str
    name: str


class MunicipioOut(BaseModel):
    code: str
    name: str
    departamento_code: str


class CatalogosResponse(BaseModel):
    departamentos: List[CatalogoOut]
    instituciones: List[CatalogoOut]
    tipos_intervencion: List[CatalogoOut]
    niveles_privacion: List[CatalogoOut]


# ── Filtros ───────────────────────────────────────────────────────────

class BeneficiarioFilters(BaseModel):
    # Geograficos
    departamento_code: Optional[str] = None
    municipio_code: Optional[str] = None
    # Intervencion
    institucion_code: Optional[str] = None
    tipo_intervencion_code: Optional[str] = None
    sin_intervencion: Optional[bool] = None
    # Demograficos
    genero: Optional[str] = None
    edad_min: Optional[int] = None
    edad_max: Optional[int] = None
    miembros_hogar_min: Optional[int] = None
    miembros_hogar_max: Optional[int] = None
    con_menores_5: Optional[bool] = None
    con_adultos_mayores: Optional[bool] = None
    # Pobreza
    nivel_privacion: Optional[str] = None
    ipm_min: Optional[float] = None
    ipm_max: Optional[float] = None
    # Busqueda
    buscar: Optional[str] = None


# ── Intervencion ──────────────────────────────────────────────────────

class IntervencionOut(BaseModel):
    institucion_code: str
    institucion_name: str
    tipo_code: str
    tipo_name: str


# ── Beneficiario resumen (para lista) ────────────────────────────────

class BeneficiarioResumen(BaseModel):
    id: int
    dpi: str
    nombre_completo: str
    genero: str
    edad: int
    departamento: str
    municipio: str
    ipm: float
    nivel_privacion: str
    num_intervenciones: int


# ── Beneficiario detalle ─────────────────────────────────────────────

class BeneficiarioOut(BaseModel):
    id: int
    dpi: str
    primer_nombre: str
    segundo_nombre: str
    primer_apellido: str
    segundo_apellido: str
    nombre_completo: str
    genero: str
    fecha_nacimiento: str
    edad: int
    departamento_code: str
    departamento: str
    municipio_code: str
    municipio: str
    miembros_hogar: int
    menores_5: int
    adultos_mayores: int
    ipm: float
    nivel_privacion: str
    intervenciones: List[IntervencionOut]


# ── Paginacion ────────────────────────────────────────────────────────

class PaginatedBeneficiarios(BaseModel):
    items: List[BeneficiarioResumen]
    total: int
    offset: int
    limit: int


# ── Stats ─────────────────────────────────────────────────────────────

class BeneficiarioStats(BaseModel):
    total: int
    promedio_ipm: float
    genero_f: int
    genero_m: int
    hogares_con_menores: int
    hogares_con_adultos_mayores: int
    por_nivel_privacion: dict
    por_departamento: dict


# ── Dashboard ─────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_beneficiarios: int
    departamentos_cubiertos: int
    cobertura_intervenciones: float = Field(
        description="Porcentaje de beneficiarios con al menos una intervencion"
    )
    promedio_ipm: float
    por_departamento: dict
    top_intervenciones: List[dict]
