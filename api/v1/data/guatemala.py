"""
Catalogos geograficos e institucionales de Guatemala (datos hardcoded para demo).
"""

# ── Departamentos ──────────────────────────────────────────────────────
DEPARTAMENTOS = [
    {"code": "GUA", "name": "Guatemala"},
    {"code": "QUE", "name": "Quetzaltenango"},
    {"code": "HUE", "name": "Huehuetenango"},
    {"code": "AVE", "name": "Alta Verapaz"},
    {"code": "SOL", "name": "Solola"},
    {"code": "CHI", "name": "Chimaltenango"},
    {"code": "TOT", "name": "Totonicapan"},
    {"code": "SMA", "name": "San Marcos"},
]

# ── Municipios (2 por departamento) ───────────────────────────────────
MUNICIPIOS = [
    # Guatemala
    {"code": "GUA-01", "name": "Guatemala",          "departamento_code": "GUA"},
    {"code": "GUA-02", "name": "Mixco",              "departamento_code": "GUA"},
    # Quetzaltenango
    {"code": "QUE-01", "name": "Quetzaltenango",     "departamento_code": "QUE"},
    {"code": "QUE-02", "name": "Coatepeque",         "departamento_code": "QUE"},
    # Huehuetenango
    {"code": "HUE-01", "name": "Huehuetenango",      "departamento_code": "HUE"},
    {"code": "HUE-02", "name": "Santa Eulalia",      "departamento_code": "HUE"},
    # Alta Verapaz
    {"code": "AVE-01", "name": "Coban",              "departamento_code": "AVE"},
    {"code": "AVE-02", "name": "San Pedro Carcha",   "departamento_code": "AVE"},
    # Solola
    {"code": "SOL-01", "name": "Solola",             "departamento_code": "SOL"},
    {"code": "SOL-02", "name": "Panajachel",         "departamento_code": "SOL"},
    # Chimaltenango
    {"code": "CHI-01", "name": "Chimaltenango",      "departamento_code": "CHI"},
    {"code": "CHI-02", "name": "Tecpan Guatemala",   "departamento_code": "CHI"},
    # Totonicapan
    {"code": "TOT-01", "name": "Totonicapan",        "departamento_code": "TOT"},
    {"code": "TOT-02", "name": "Momostenango",       "departamento_code": "TOT"},
    # San Marcos
    {"code": "SMA-01", "name": "San Marcos",         "departamento_code": "SMA"},
    {"code": "SMA-02", "name": "San Pedro Sacatepequez", "departamento_code": "SMA"},
]

# ── Instituciones ─────────────────────────────────────────────────────
INSTITUCIONES = [
    {"code": "MIDES",   "name": "Ministerio de Desarrollo Social"},
    {"code": "MAGA",    "name": "Ministerio de Agricultura, Ganaderia y Alimentacion"},
    {"code": "MSPAS",   "name": "Ministerio de Salud Publica y Asistencia Social"},
    {"code": "MINEDUC", "name": "Ministerio de Educacion"},
    {"code": "FODES",   "name": "Fondo de Desarrollo Social"},
]

# ── Tipos de intervencion ─────────────────────────────────────────────
TIPOS_INTERVENCION = [
    {"code": "TMC",      "name": "Transferencia Monetaria Condicionada"},
    {"code": "AA",       "name": "Asistencia Alimentaria"},
    {"code": "BE",       "name": "Beca Educativa"},
    {"code": "AS",       "name": "Atencion en Salud"},
    {"code": "MV",       "name": "Mejoramiento de Vivienda"},
    {"code": "IA",       "name": "Insumos Agricolas"},
]

# ── Niveles de privacion ──────────────────────────────────────────────
NIVELES_PRIVACION = [
    {"code": "extrema",  "name": "Pobreza Extrema"},
    {"code": "alta",     "name": "Pobreza Alta"},
    {"code": "media",    "name": "Pobreza Media"},
    {"code": "baja",     "name": "Pobreza Baja"},
]
