"""Mapea filas ClickHouse a diccionarios de beneficiario."""
from decimal import Decimal


def _safe_float(val) -> float:
    """Convierte Decimal/None a float."""
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


def _safe_str(val) -> str:
    """Limpia strings de ClickHouse (trim FixedString)."""
    if val is None:
        return ""
    return str(val).strip()


def row_to_beneficiario_resumen(row: dict) -> dict:
    """Convierte una fila del query principal a formato resumen."""
    return {
        "hogar_id": row["hogar_id"],
        "cui_jefe_hogar": row.get("cui_jefe_hogar"),
        "nombre_completo": _safe_str(row.get("nombre_jefe_hogar")),
        "sexo_jefe_hogar": _safe_str(row.get("sexo_jefe_hogar")),
        "departamento": _safe_str(row.get("departamento")),
        "departamento_codigo": _safe_str(row.get("departamento_codigo")),
        "municipio": _safe_str(row.get("municipio")),
        "municipio_codigo": _safe_str(row.get("municipio_codigo")),
        "lugar_poblado": _safe_str(row.get("lugar_poblado")),
        "area": _safe_str(row.get("area")),
        "numero_personas": row.get("numero_personas", 0) or 0,
        "hombres": row.get("hombres", 0) or 0,
        "mujeres": row.get("mujeres", 0) or 0,
        "ipm_gt": _safe_float(row.get("ipm_gt")),
        "ipm_gt_clasificacion": _safe_str(row.get("ipm_gt_clasificacion")),
        "pmt": _safe_float(row.get("pmt")),
        "pmt_clasificacion": _safe_str(row.get("pmt_clasificacion")),
        "nbi": _safe_float(row.get("nbi")),
        "nbi_clasificacion": _safe_str(row.get("nbi_clasificacion")),
    }


def row_to_beneficiario_detalle(row: dict) -> dict:
    """Convierte fila con JOINs a formato detalle completo."""
    base = row_to_beneficiario_resumen(row)
    base.update({
        "latitud": row.get("geolocalizacion_vivienda_latitud"),
        "longitud": row.get("geolocalizacion_vivienda_longitud"),
        "direccion": _safe_str(row.get("direccion_vivienda")),
        "celular_jefe": row.get("celular_jefe_hogar"),
        "cui_madre": row.get("cui_madre"),
        "nombre_madre": _safe_str(row.get("nombre_madre")),
        "fase": _safe_str(row.get("fase")),
        "fase_estado": _safe_str(row.get("fase_estado")),
        "anio": int(row["anio"]) if row.get("anio") else None,
        # Demograficos (de JOIN con hogares_datos_demograficos)
        "total_personas": row.get("total_personas"),
        "menores_5": row.get("p_0_5"),
        "adultos_mayores": row.get("adultos_mayores"),
        "personas_embarazadas": row.get("personas_embarazadas"),
        "personas_con_dificultad": row.get("personas_con_dificultad"),
        "tipo_jefatura": _safe_str(row.get("tipo_jefatura")),
        "comunidad_linguistica": _safe_str(row.get("comunidad_linguistica")),
        "pueblo_de_pertenencia": _safe_str(row.get("pueblo_de_pertenencia")),
        # Inseguridad alimentaria (de JOIN con hogares_inseguridad_alimentaria)
        "nivel_inseguridad_alimentaria": _safe_str(row.get("nivel_inseguridad_alimentaria")),
        "puntos_elcsa": row.get("puntos_elcsa"),
        # Conteos por grupo etario
        "primera_infancia": row.get("primera_infancia"),
        "ninos": row.get("ninos"),
        "adolescentes": row.get("adolescentes"),
        "jovenes": row.get("jovenes"),
        "adultos": row.get("adultos"),
    })
    return base
