"""Mapea filas ClickHouse de beneficios_x_hogar a diccionarios."""
from decimal import Decimal


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


def _safe_str(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _safe_int(val) -> int:
    if val is None:
        return 0
    return int(val)


def row_to_beneficio_resumen(row: dict, intervention_columns: list[str]) -> dict:
    """Convierte fila de beneficios_x_hogar a formato resumen."""
    result = {
        "hogar_id": row["hogar_id"],
        "departamento": _safe_str(row.get("ig3_departamento")),
        "departamento_codigo": _safe_str(row.get("ig3_departamento_codigo")),
        "municipio": _safe_str(row.get("ig4_municipio")),
        "municipio_codigo": _safe_str(row.get("ig4_municipio_codigo")),
        "lugar_poblado": _safe_str(row.get("ig5_lugar_poblado")),
        "area": _safe_str(row.get("area")),
        "numero_personas": _safe_int(row.get("numero_personas")),
        "hombres": _safe_int(row.get("hombres")),
        "mujeres": _safe_int(row.get("mujeres")),
        "ipm_gt": _safe_float(row.get("ipm_gt")),
        "ipm_gt_clasificacion": _safe_str(row.get("ipm_gt_clasificacion")),
    }
    for col in intervention_columns:
        result[col] = _safe_int(row.get(col))
    return result


def row_to_beneficio_detalle(row: dict, intervention_columns: list[str]) -> dict:
    """Convierte fila a formato detalle (misma estructura para tabla denormalizada)."""
    return row_to_beneficio_resumen(row, intervention_columns)
