from pydantic import BaseModel
from typing import Optional


# ── Shared models ────────────────────────────────────────────────────

class DepartamentoCount(BaseModel):
    departamento: str
    codigo: str
    cantidad: int


class ClasificacionCount(BaseModel):
    clasificacion: str
    cantidad: int


class PobrezaDepartamentoItem(BaseModel):
    departamento: str
    codigo: str
    clasificacion: str
    cantidad: int


class InseguridadCount(BaseModel):
    nivel: str
    cantidad: int


class SexoCount(BaseModel):
    sexo: str
    cantidad: int


class InstitutionUsersCount(BaseModel):
    institution: str
    code: str
    usuarios: int
    consultas: int


class InstitutionBeneficiariosCount(BaseModel):
    institution: str
    code: str
    potenciales_beneficiarios: int


# ── Super Admin Dashboard ────────────────────────────────────────────

class AdminDashboardStats(BaseModel):
    """Dashboard completo para Super Admin."""
    # Sistema
    total_instituciones: int = 0
    total_usuarios: int = 0
    total_consultas_guardadas: int = 0
    usuarios_por_institucion: list[InstitutionUsersCount] = []
    beneficiarios_por_institucion: list[InstitutionBeneficiariosCount] = []

    # Datos generales RSH
    total_hogares: int = 0
    total_personas: int = 0
    departamentos_cubiertos: int = 0
    municipios_cubiertos: int = 0
    lugares_poblados: int = 0

    # Municipios estado
    municipios_finalizados: int = 0
    municipios_en_progreso: int = 0

    # Pobreza / IPM / PMT / NBI
    promedio_ipm: float = 0.0
    promedio_pmt: float = 0.0
    promedio_nbi: float = 0.0
    por_ipm_clasificacion: list[ClasificacionCount] = []
    por_nbi_clasificacion: list[ClasificacionCount] = []
    por_pmt_clasificacion: list[ClasificacionCount] = []

    # Pobreza por departamento
    ipm_por_departamento: list[PobrezaDepartamentoItem] = []
    pmt_por_departamento: list[PobrezaDepartamentoItem] = []
    nbi_por_departamento: list[PobrezaDepartamentoItem] = []

    # Sexo beneficiarios
    personas_por_sexo: list[SexoCount] = []

    # Geográfico
    por_departamento: list[DepartamentoCount] = []

    # Inseguridad alimentaria
    inseguridad_alimentaria: list[InseguridadCount] = []


# ── Institutional Dashboard ──────────────────────────────────────────

class InstitutionalDashboardStats(BaseModel):
    """Dashboard para Admin Institucional y Usuario Institucional."""
    institution_name: str = ""
    institution_code: str = ""

    # Datos generales (scoped a la institucion)
    total_hogares: int = 0
    total_personas: int = 0
    departamentos_cubiertos: int = 0
    municipios_cubiertos: int = 0
    lugares_poblados: int = 0

    # Municipios estado
    municipios_finalizados: int = 0
    municipios_en_progreso: int = 0

    # Pobreza / IPM / PMT / NBI
    promedio_ipm: float = 0.0
    promedio_pmt: float = 0.0
    promedio_nbi: float = 0.0
    por_ipm_clasificacion: list[ClasificacionCount] = []
    por_nbi_clasificacion: list[ClasificacionCount] = []
    por_pmt_clasificacion: list[ClasificacionCount] = []

    # Pobreza por departamento
    ipm_por_departamento: list[PobrezaDepartamentoItem] = []
    pmt_por_departamento: list[PobrezaDepartamentoItem] = []
    nbi_por_departamento: list[PobrezaDepartamentoItem] = []

    # Sexo beneficiarios
    personas_por_sexo: list[SexoCount] = []

    # Geográfico
    por_departamento: list[DepartamentoCount] = []

    # Inseguridad alimentaria
    inseguridad_alimentaria: list[InseguridadCount] = []

    # Bonos e intervenciones (solo las de la institucion)
    bonos: dict[str, int] = {}
    bonos_por_departamento: list[dict] = []

    # Consultas de la institucion
    total_consultas: int = 0
    total_fuentes_datos: int = 0
