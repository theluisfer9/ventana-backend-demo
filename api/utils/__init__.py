from datetime import date, datetime, timedelta
from typing import Optional, Any
from decouple import config

def generar_identificador_unico() -> str:
    now = datetime.now()
    return now.strftime("%Y%m%d%H%M%S%f")[:-3]

def validar_env_var_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

def validar_env_var_number(name: str, default: Optional[int] = None) -> Optional[int]:
    raw: Any = config(name, default=None)
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return default
    try:
        return int(str(raw))
    except Exception as e:
        raise ValueError(f"{name} debe ser un entero válido: {raw!r}") from e

def validar_env_var_string(
    name: str, default: Optional[str] = None, allow_blank: bool = False
) -> Optional[str]:
    env_var: Any = config(name, default=default)
    if env_var is None:
        return None
    result = str(env_var)
    if not allow_blank and result.strip() == "":
        return None
    return result

def validar_env_var_requeridas(keys: list[str]) -> Optional[str]:
    missing = [k for k in keys if not validar_env_var_string(k)]
    if missing:
        raise ValueError("Faltan variables requeridas en .env: " + ", ".join(missing))

def convertir_date_a_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time()) + timedelta(days=1)
