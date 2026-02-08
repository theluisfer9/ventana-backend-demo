from pydantic import BaseModel
from typing import Optional


# ── Catalogos ─────────────────────────────────────────────────────────

class CatalogoItem(BaseModel):
    code: str
    name: str


class CatalogosResponse(BaseModel):
    """Catalogos dinamicos derivados de los datos RSH reales."""
    departamentos: list[CatalogoItem] = []
    clasificaciones_ipm: list[str] = []
    clasificaciones_pmt: list[str] = []
    clasificaciones_nbi: list[str] = []
    areas: list[str] = []
    niveles_inseguridad: list[str] = []
    fases: list[str] = []
    comunidades_linguisticas: list[str] = []
    pueblos: list[str] = []
    fuentes_agua: list[str] = []
    tipos_sanitario: list[str] = []
    tipos_alumbrado: list[str] = []
    combustibles_cocina: list[str] = []


class MunicipioItem(BaseModel):
    code: str
    name: str


class LugarPobladoItem(BaseModel):
    code: str
    name: str


# ── Filtros ───────────────────────────────────────────────────────────

class BeneficiarioFilters(BaseModel):
    """Filtros para consulta de hogares/beneficiarios RSH."""
    # Geograficos
    departamento_codigo: Optional[str] = None
    municipio_codigo: Optional[str] = None
    lugar_poblado_codigo: Optional[str] = None
    area: Optional[str] = None
    # Jefe de hogar
    sexo_jefe: Optional[str] = None
    # Pobreza
    ipm_min: Optional[float] = None
    ipm_max: Optional[float] = None
    ipm_clasificacion: Optional[str] = None
    pmt_clasificacion: Optional[str] = None
    nbi_clasificacion: Optional[str] = None
    # Demograficos (requieren JOIN con hogares_datos_demograficos)
    tiene_menores_5: Optional[bool] = None
    tiene_adultos_mayores: Optional[bool] = None
    tiene_embarazadas: Optional[bool] = None
    tiene_discapacidad: Optional[bool] = None
    # Inseguridad alimentaria (requiere JOIN con hogares_inseguridad_alimentaria)
    nivel_inseguridad: Optional[str] = None
    # Servicios basicos (requieren JOIN con entrevista_hogares)
    fuente_agua: Optional[str] = None
    tipo_sanitario: Optional[str] = None
    alumbrado: Optional[str] = None
    combustible_cocina: Optional[str] = None
    # Bienes del hogar (requieren JOIN con entrevista_hogares)
    tiene_internet: Optional[bool] = None
    tiene_computadora: Optional[bool] = None
    tiene_refrigerador: Optional[bool] = None
    # Hacinamiento (requiere JOIN con entrevista_hogares)
    con_hacinamiento: Optional[bool] = None
    # Educacion y empleo (requieren subquery en entrevista_personas)
    con_analfabetismo: Optional[bool] = None
    con_menores_sin_escuela: Optional[bool] = None
    sin_empleo: Optional[bool] = None
    # Busqueda
    buscar: Optional[str] = None
    # Temporal
    anio: Optional[int] = None
    # Fase intervencion
    fase: Optional[str] = None


# ── Beneficiario resumen (para listados) ──────────────────────────────

class BeneficiarioResumen(BaseModel):
    """Vista resumida de un hogar para listados paginados."""
    hogar_id: int
    cui_jefe_hogar: Optional[int] = None
    nombre_completo: str = ""
    sexo_jefe_hogar: str = ""
    departamento: str = ""
    departamento_codigo: str = ""
    municipio: str = ""
    municipio_codigo: str = ""
    lugar_poblado: str = ""
    area: str = ""
    numero_personas: int = 0
    hombres: int = 0
    mujeres: int = 0
    ipm_gt: float = 0.0
    ipm_gt_clasificacion: str = ""
    pmt: float = 0.0
    pmt_clasificacion: str = ""
    nbi: float = 0.0
    nbi_clasificacion: str = ""


# ── Beneficiario detalle ──────────────────────────────────────────────

class BeneficiarioDetalle(BeneficiarioResumen):
    """Vista detallada de un hogar con datos demograficos y alimentarios."""
    # Geolocalizacion
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    direccion: str = ""
    # Contacto
    celular_jefe: Optional[int] = None
    cui_madre: Optional[int] = None
    nombre_madre: str = ""
    # Fase
    fase: str = ""
    fase_estado: str = ""
    anio: Optional[int] = None
    # Demograficos (de hogares_datos_demograficos)
    total_personas: Optional[int] = None
    menores_5: Optional[int] = None
    adultos_mayores: Optional[int] = None
    personas_embarazadas: Optional[int] = None
    personas_con_dificultad: Optional[int] = None
    tipo_jefatura: str = ""
    comunidad_linguistica: str = ""
    pueblo_de_pertenencia: str = ""
    # Inseguridad alimentaria (de hogares_inseguridad_alimentaria)
    nivel_inseguridad_alimentaria: str = ""
    puntos_elcsa: Optional[int] = None
    # Conteos por grupo etario
    primera_infancia: Optional[int] = None
    ninos: Optional[int] = None
    adolescentes: Optional[int] = None
    jovenes: Optional[int] = None
    adultos: Optional[int] = None


# ── Paginacion ────────────────────────────────────────────────────────

class PaginatedBeneficiarios(BaseModel):
    items: list[BeneficiarioResumen]
    total: int
    offset: int
    limit: int


# ── Estadisticas ──────────────────────────────────────────────────────

class DepartamentoCount(BaseModel):
    departamento: str
    codigo: str
    cantidad: int


class ClasificacionCount(BaseModel):
    clasificacion: str
    cantidad: int


class BeneficiarioStats(BaseModel):
    """Estadisticas agregadas para filtros aplicados."""
    total: int = 0
    promedio_ipm: float = 0.0
    total_mujeres_jefas: int = 0
    total_hombres_jefes: int = 0
    total_personas: int = 0
    total_hombres: int = 0
    total_mujeres: int = 0
    por_departamento: list[DepartamentoCount] = []
    por_ipm_clasificacion: list[ClasificacionCount] = []


# ── Dashboard ─────────────────────────────────────────────────────────

class InseguridadCount(BaseModel):
    nivel: str
    cantidad: int


class DashboardStats(BaseModel):
    """Estadisticas globales para el dashboard principal."""
    total_hogares: int = 0
    departamentos_cubiertos: int = 0
    municipios_cubiertos: int = 0
    promedio_ipm: float = 0.0
    total_personas: int = 0
    hogares_pobres: int = 0
    hogares_no_pobres: int = 0
    por_departamento: list[DepartamentoCount] = []
    inseguridad_alimentaria: list[InseguridadCount] = []
