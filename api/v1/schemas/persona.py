from pydantic import BaseModel
from typing import Optional


class PersonaResumen(BaseModel):
    """Vista de una persona del hogar desde entrevista_personas."""
    personas_id: int
    correlativo: int = 0
    cui: Optional[int] = None
    nombre_completo: str = ""
    genero: str = ""
    fecha_nacimiento: Optional[str] = None
    edad: int = 0
    estado_civil: str = ""
    celular: Optional[int] = None
    parentesco: str = ""
    pueblo: str = ""
    comunidad_linguistica: str = ""
    idioma_materno: str = ""
    # Discapacidades
    dificultad_ver: str = ""
    dificultad_oir: str = ""
    dificultad_caminar: str = ""
    dificultad_recordar: str = ""
    dificultad_cuidado_personal: str = ""
    dificultad_entender: str = ""
    # Salud
    embarazada: str = ""
    # Educacion
    sabe_leer_escribir: str = ""
    inscrito_escuela: str = ""
    nivel_educativo: str = ""
    # Empleo
    actividad_principal: str = ""
    tiene_ingreso: str = ""
