"""
Keycloak Admin REST API client.

Permite crear, actualizar y desactivar usuarios en Keycloak
de forma sincronizada con la base de datos local.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

import httpx
from decouple import config

from api.v1.services.keycloak_auth import (
    KEYCLOAK_DOMAIN,
    KEYCLOAK_REALM,
    is_keycloak_enabled,
)

logger = logging.getLogger(__name__)

# Client confidencial separado para Admin API
KEYCLOAK_ADMIN_CLIENT_ID = config("KEYCLOAK_ADMIN_CLIENT_ID", default="")
KEYCLOAK_ADMIN_CLIENT_SECRET = config("KEYCLOAK_ADMIN_CLIENT_SECRET", default="")

# ── Token cache ──────────────────────────────────────────────────────

_TOKEN_CACHE: dict[str, Any] = {"token": None, "expires_at": None}
_TOKEN_LOCK = Lock()


def _get_admin_token() -> str | None:
    """Obtiene un access token via client_credentials grant."""
    if not is_keycloak_enabled() or not KEYCLOAK_ADMIN_CLIENT_SECRET:
        return None

    # Check cache
    if (
        _TOKEN_CACHE["token"]
        and _TOKEN_CACHE["expires_at"]
        and _TOKEN_CACHE["expires_at"] > datetime.now(timezone.utc)
    ):
        return _TOKEN_CACHE["token"]

    with _TOKEN_LOCK:
        # Double check after lock
        if (
            _TOKEN_CACHE["token"]
            and _TOKEN_CACHE["expires_at"]
            and _TOKEN_CACHE["expires_at"] > datetime.now(timezone.utc)
        ):
            return _TOKEN_CACHE["token"]

        token_url = (
            f"{KEYCLOAK_DOMAIN}/realms/{KEYCLOAK_REALM}"
            f"/protocol/openid-connect/token"
        )
        resp = httpx.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": KEYCLOAK_ADMIN_CLIENT_ID,
                "client_secret": KEYCLOAK_ADMIN_CLIENT_SECRET,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        payload = resp.json()

        _TOKEN_CACHE["token"] = payload["access_token"]
        # Refresh 30s before expiry
        expires_in = payload.get("expires_in", 300)
        _TOKEN_CACHE["expires_at"] = datetime.now(timezone.utc) + timedelta(
            seconds=max(expires_in - 30, 10)
        )
        return _TOKEN_CACHE["token"]


def _admin_base_url() -> str:
    return f"{KEYCLOAK_DOMAIN}/admin/realms/{KEYCLOAK_REALM}"


def _auth_headers() -> dict[str, str]:
    token = _get_admin_token()
    if not token:
        raise RuntimeError("No se pudo obtener token de admin de Keycloak")
    return {"Authorization": f"Bearer {token}"}


# ── CRUD ─────────────────────────────────────────────────────────────


def create_keycloak_user(
    *,
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    password: str | None = None,
    enabled: bool = True,
) -> str | None:
    """Crea un usuario en Keycloak y retorna su ID (sub).

    Returns None si Keycloak no esta habilitado o no hay secret.
    Raises en caso de error HTTP.
    """
    if not is_keycloak_enabled() or not KEYCLOAK_ADMIN_CLIENT_SECRET:
        logger.info("Keycloak no habilitado, omitiendo creacion de usuario")
        return None

    user_payload: dict[str, Any] = {
        "username": username,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "enabled": enabled,
        "emailVerified": True,
    }

    if password:
        user_payload["credentials"] = [
            {
                "type": "password",
                "value": password,
                "temporary": True,
            }
        ]

    resp = httpx.post(
        f"{_admin_base_url()}/users",
        json=user_payload,
        headers=_auth_headers(),
        timeout=10.0,
    )
    resp.raise_for_status()

    # Keycloak retorna 201 con Location header que contiene el ID
    location = resp.headers.get("Location", "")
    keycloak_id = location.rsplit("/", 1)[-1] if location else None

    if not keycloak_id:
        # Fallback: buscar por username
        keycloak_id = _find_keycloak_user_id(username=username)

    # Asignar rol login_access para que pueda entrar al frontend
    if keycloak_id:
        _assign_realm_role(keycloak_id, "login_access")

    logger.info("Usuario creado en Keycloak: %s (id=%s)", username, keycloak_id)
    return keycloak_id


def update_keycloak_user(
    keycloak_id: str,
    *,
    username: str | None = None,
    email: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    enabled: bool | None = None,
) -> bool:
    """Actualiza un usuario en Keycloak. Retorna True si se actualizo."""
    if not is_keycloak_enabled() or not KEYCLOAK_ADMIN_CLIENT_SECRET:
        return False

    if not keycloak_id:
        logger.warning("No se puede actualizar usuario sin keycloak_id")
        return False

    payload: dict[str, Any] = {}
    if username is not None:
        payload["username"] = username
    if email is not None:
        payload["email"] = email
    if first_name is not None:
        payload["firstName"] = first_name
    if last_name is not None:
        payload["lastName"] = last_name
    if enabled is not None:
        payload["enabled"] = enabled

    if not payload:
        return False

    resp = httpx.put(
        f"{_admin_base_url()}/users/{keycloak_id}",
        json=payload,
        headers=_auth_headers(),
        timeout=10.0,
    )
    resp.raise_for_status()

    logger.info("Usuario actualizado en Keycloak: %s", keycloak_id)
    return True


def disable_keycloak_user(keycloak_id: str) -> bool:
    """Desactiva un usuario en Keycloak (soft delete)."""
    if not keycloak_id:
        return False
    return update_keycloak_user(keycloak_id, enabled=False)


def enable_keycloak_user(keycloak_id: str) -> bool:
    """Reactiva un usuario en Keycloak."""
    if not keycloak_id:
        return False
    return update_keycloak_user(keycloak_id, enabled=True)


def _assign_realm_role(keycloak_id: str, role_name: str) -> bool:
    """Asigna un rol de realm a un usuario en Keycloak."""
    try:
        headers = _auth_headers()
        # Obtener el rol por nombre
        resp = httpx.get(
            f"{_admin_base_url()}/roles/{role_name}",
            headers=headers,
            timeout=10.0,
        )
        if resp.status_code != 200:
            logger.warning("Rol '%s' no encontrado en Keycloak", role_name)
            return False

        role = resp.json()

        # Asignar al usuario
        resp2 = httpx.post(
            f"{_admin_base_url()}/users/{keycloak_id}/role-mappings/realm",
            json=[{"id": role["id"], "name": role["name"]}],
            headers=headers,
            timeout=10.0,
        )
        resp2.raise_for_status()
        logger.info("Rol '%s' asignado a usuario %s", role_name, keycloak_id)
        return True
    except Exception:
        logger.warning(
            "No se pudo asignar rol '%s' al usuario %s",
            role_name,
            keycloak_id,
            exc_info=True,
        )
        return False


def _find_keycloak_user_id(*, username: str) -> str | None:
    """Busca un usuario por username y retorna su ID."""
    if not is_keycloak_enabled() or not KEYCLOAK_ADMIN_CLIENT_SECRET:
        return None

    resp = httpx.get(
        f"{_admin_base_url()}/users",
        params={"username": username, "exact": "true"},
        headers=_auth_headers(),
        timeout=10.0,
    )
    resp.raise_for_status()
    users = resp.json()
    if users:
        return users[0].get("id")
    return None
