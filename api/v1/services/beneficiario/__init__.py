"""
Servicio de beneficiarios: funciones puras sobre listas en memoria.
No requiere BD — opera sobre datos hardcoded.
"""
from typing import Optional, List

from api.v1.data.beneficiarios import BENEFICIARIOS
from api.v1.data.guatemala import (
    DEPARTAMENTOS,
    MUNICIPIOS,
    INSTITUCIONES,
    TIPOS_INTERVENCION,
    NIVELES_PRIVACION,
)
from api.v1.schemas.beneficiario import BeneficiarioFilters


# ── Lookups ───────────────────────────────────────────────────────────

_DEPTO_MAP = {d["code"]: d["name"] for d in DEPARTAMENTOS}
_MUNI_MAP = {m["code"]: m["name"] for m in MUNICIPIOS}
_INST_MAP = {i["code"]: i["name"] for i in INSTITUCIONES}
_TIPO_MAP = {t["code"]: t["name"] for t in TIPOS_INTERVENCION}


def _enrich(b: dict) -> dict:
    """Enriquece un beneficiario raw con nombres legibles."""
    nombre_completo = (
        f"{b['primer_nombre']} {b['segundo_nombre']} "
        f"{b['primer_apellido']} {b['segundo_apellido']}"
    )
    intervenciones = [
        {
            "institucion_code": iv["institucion_code"],
            "institucion_name": _INST_MAP.get(iv["institucion_code"], ""),
            "tipo_code": iv["tipo_code"],
            "tipo_name": _TIPO_MAP.get(iv["tipo_code"], ""),
        }
        for iv in b["intervenciones"]
    ]
    return {
        **b,
        "nombre_completo": nombre_completo,
        "departamento": _DEPTO_MAP.get(b["departamento_code"], ""),
        "municipio": _MUNI_MAP.get(b["municipio_code"], ""),
        "intervenciones": intervenciones,
        "num_intervenciones": len(b["intervenciones"]),
    }


# ── Filtrado ──────────────────────────────────────────────────────────

def _apply_filters(data: list, filters: BeneficiarioFilters) -> list:
    result = data

    if filters.departamento_codigo:
        result = [b for b in result if b["departamento_code"] == filters.departamento_codigo]

    if filters.municipio_codigo:
        result = [b for b in result if b["municipio_code"] == filters.municipio_codigo]

    if filters.sexo_jefe:
        result = [b for b in result if b["genero"] == filters.sexo_jefe]

    if filters.tiene_menores_5:
        result = [b for b in result if b["menores_5"] > 0]

    if filters.tiene_adultos_mayores:
        result = [b for b in result if b["adultos_mayores"] > 0]

    if filters.ipm_min is not None:
        result = [b for b in result if b["ipm"] >= filters.ipm_min]

    if filters.ipm_max is not None:
        result = [b for b in result if b["ipm"] <= filters.ipm_max]

    if filters.buscar:
        term = filters.buscar.lower()
        def _matches(b):
            full = f"{b['primer_nombre']} {b['segundo_nombre']} {b['primer_apellido']} {b['segundo_apellido']}".lower()
            return term in full or term in b["dpi"]
        result = [b for b in result if _matches(b)]

    return result


# ── Public API ────────────────────────────────────────────────────────

def get_filtered_enriched(filters: BeneficiarioFilters) -> list[dict]:
    """Retorna TODOS los beneficiarios filtrados y enriquecidos (sin paginacion)."""
    filtered = _apply_filters(BENEFICIARIOS, filters)
    return [_enrich(b) for b in filtered]


def list_beneficiarios(
    filters: BeneficiarioFilters,
    offset: int = 0,
    limit: int = 20,
) -> dict:
    filtered = _apply_filters(BENEFICIARIOS, filters)
    total = len(filtered)
    page = filtered[offset:offset + limit]
    items = [_enrich(b) for b in page]
    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


def get_beneficiario_by_id(beneficiario_id: int) -> Optional[dict]:
    for b in BENEFICIARIOS:
        if b["id"] == beneficiario_id:
            return _enrich(b)
    return None


def get_beneficiario_stats(filters: BeneficiarioFilters) -> dict:
    filtered = _apply_filters(BENEFICIARIOS, filters)
    total = len(filtered)

    if total == 0:
        return {
            "total": 0,
            "promedio_ipm": 0,
            "genero_f": 0,
            "genero_m": 0,
            "hogares_con_menores": 0,
            "hogares_con_adultos_mayores": 0,
            "por_nivel_privacion": {},
            "por_departamento": {},
        }

    promedio_ipm = round(sum(b["ipm"] for b in filtered) / total, 4)
    genero_f = sum(1 for b in filtered if b["genero"] == "F")
    genero_m = sum(1 for b in filtered if b["genero"] == "M")
    hogares_con_menores = sum(1 for b in filtered if b["menores_5"] > 0)
    hogares_con_adultos_mayores = sum(1 for b in filtered if b["adultos_mayores"] > 0)

    por_nivel = {}
    for b in filtered:
        nivel = b["nivel_privacion"]
        por_nivel[nivel] = por_nivel.get(nivel, 0) + 1

    por_depto = {}
    for b in filtered:
        depto_name = _DEPTO_MAP.get(b["departamento_code"], b["departamento_code"])
        por_depto[depto_name] = por_depto.get(depto_name, 0) + 1

    return {
        "total": total,
        "promedio_ipm": promedio_ipm,
        "genero_f": genero_f,
        "genero_m": genero_m,
        "hogares_con_menores": hogares_con_menores,
        "hogares_con_adultos_mayores": hogares_con_adultos_mayores,
        "por_nivel_privacion": por_nivel,
        "por_departamento": por_depto,
    }


def get_dashboard_stats() -> dict:
    total = len(BENEFICIARIOS)
    deptos = set(b["departamento_code"] for b in BENEFICIARIOS)
    con_intervencion = sum(1 for b in BENEFICIARIOS if len(b["intervenciones"]) > 0)
    cobertura = round((con_intervencion / total) * 100, 1) if total > 0 else 0
    promedio_ipm = round(sum(b["ipm"] for b in BENEFICIARIOS) / total, 4) if total > 0 else 0

    por_depto = {}
    for b in BENEFICIARIOS:
        depto_name = _DEPTO_MAP.get(b["departamento_code"], b["departamento_code"])
        por_depto[depto_name] = por_depto.get(depto_name, 0) + 1

    # Top intervenciones: contar por tipo
    tipo_count = {}
    for b in BENEFICIARIOS:
        for iv in b["intervenciones"]:
            tipo_name = _TIPO_MAP.get(iv["tipo_code"], iv["tipo_code"])
            tipo_count[tipo_name] = tipo_count.get(tipo_name, 0) + 1

    top_intervenciones = sorted(
        [{"name": k, "count": v} for k, v in tipo_count.items()],
        key=lambda x: x["count"],
        reverse=True,
    )

    return {
        "total_beneficiarios": total,
        "departamentos_cubiertos": len(deptos),
        "cobertura_intervenciones": cobertura,
        "promedio_ipm": promedio_ipm,
        "por_departamento": por_depto,
        "top_intervenciones": top_intervenciones,
    }


def get_catalogos() -> dict:
    return {
        "departamentos": DEPARTAMENTOS,
        "instituciones": INSTITUCIONES,
        "tipos_intervencion": TIPOS_INTERVENCION,
        "niveles_privacion": NIVELES_PRIVACION,
    }


def get_municipios_by_departamento(departamento_code: str) -> list:
    return [
        m for m in MUNICIPIOS
        if m["departamento_code"] == departamento_code
    ]
