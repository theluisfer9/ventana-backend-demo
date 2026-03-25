from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any
from urllib.parse import urljoin

import httpx
from decouple import config

from api.v1.services.keycloak_auth import (
    KEYCLOAK_DOMAIN,
    KEYCLOAK_REALM,
    is_keycloak_enabled,
)


logger = logging.getLogger(__name__)

KEYCLOAK_ADMIN_CLIENT_ID = config("KEYCLOAK_ADMIN_CLIENT_ID", default="")
KEYCLOAK_ADMIN_CLIENT_SECRET = config("KEYCLOAK_ADMIN_CLIENT_SECRET", default="")
KEYCLOAK_ADMIN_REALM = config("KEYCLOAK_ADMIN_REALM", default=KEYCLOAK_REALM)
KEYCLOAK_ADMIN_USERNAME = config("KEYCLOAK_ADMIN_USERNAME", default="")
KEYCLOAK_ADMIN_PASSWORD = config("KEYCLOAK_ADMIN_PASSWORD", default="")

_TOKEN_CACHE: dict[str, Any] = {"token": None, "expires_at": None}
_TOKEN_LOCK = Lock()


def _cached_token_is_valid() -> bool:
    expires_at = _TOKEN_CACHE.get("expires_at")
    return bool(
        _TOKEN_CACHE.get("token")
        and expires_at
        and expires_at > datetime.now(timezone.utc)
    )


def _token_url() -> str:
    return (
        f"{KEYCLOAK_DOMAIN}/realms/{KEYCLOAK_ADMIN_REALM}"
        "/protocol/openid-connect/token"
    )


def _admin_base_url() -> str:
    return f"{KEYCLOAK_DOMAIN}/admin/realms/{KEYCLOAK_REALM}"


def _admin_users_url() -> str:
    return f"{_admin_base_url()}/users"


def get_admin_access_token() -> str:
    if _cached_token_is_valid():
        return _TOKEN_CACHE["token"]

    with _TOKEN_LOCK:
        if _cached_token_is_valid():
            return _TOKEN_CACHE["token"]

        if (
            not KEYCLOAK_ADMIN_CLIENT_ID
            and KEYCLOAK_ADMIN_USERNAME
            and KEYCLOAK_ADMIN_PASSWORD
        ):
            response = httpx.post(
                _token_url(),
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": KEYCLOAK_ADMIN_USERNAME,
                    "password": KEYCLOAK_ADMIN_PASSWORD,
                },
                timeout=15.0,
            )
        elif KEYCLOAK_ADMIN_CLIENT_ID and KEYCLOAK_ADMIN_CLIENT_SECRET:
            response = httpx.post(
                _token_url(),
                data={
                    "grant_type": "client_credentials",
                    "client_id": KEYCLOAK_ADMIN_CLIENT_ID,
                    "client_secret": KEYCLOAK_ADMIN_CLIENT_SECRET,
                },
                timeout=15.0,
            )
        else:
            raise RuntimeError(
                "Faltan credenciales de admin para Keycloak. "
                "Configura KEYCLOAK_ADMIN_CLIENT_ID/SECRET o "
                "KEYCLOAK_ADMIN_USERNAME/PASSWORD."
            )

        response.raise_for_status()
        payload = response.json()
        token = payload["access_token"]
        expires_in = payload.get("expires_in", 300)
        _TOKEN_CACHE["token"] = token
        _TOKEN_CACHE["expires_at"] = datetime.now(timezone.utc) + timedelta(
            seconds=max(expires_in - 30, 10)
        )
        return token


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {get_admin_access_token()}",
        "Content-Type": "application/json",
    }


def build_user_payload(
    *,
    email: str,
    username: str,
    first_name: str,
    last_name: str,
    enabled: bool,
) -> dict[str, Any]:
    return {
        "email": email,
        "username": username,
        "firstName": first_name,
        "lastName": last_name,
        "enabled": enabled,
        "emailVerified": True,
        "requiredActions": ["UPDATE_PASSWORD"],
    }


def set_temporary_password(user_id: str, temporary_password: str) -> None:
    response = httpx.put(
        urljoin(f"{_admin_users_url()}/", f"{user_id}/reset-password"),
        headers=_auth_headers(),
        json={
            "type": "password",
            "temporary": True,
            "value": temporary_password,
        },
        timeout=15.0,
    )
    response.raise_for_status()


def create_keycloak_user(
    *,
    email: str,
    username: str,
    first_name: str,
    last_name: str,
    temporary_password: str | None = None,
    password: str | None = None,
    enabled: bool = True,
) -> str | None:
    if not is_keycloak_enabled():
        logger.info("Keycloak no habilitado, omitiendo creación de usuario")
        return None

    response = httpx.post(
        _admin_users_url(),
        headers=_auth_headers(),
        json=build_user_payload(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            enabled=enabled,
        ),
        timeout=15.0,
    )
    response.raise_for_status()

    location = response.headers.get("Location", "")
    keycloak_id = location.rstrip("/").split("/")[-1] if location else None
    if not keycloak_id:
        keycloak_id = _find_keycloak_user_id(username=username)

    secret = temporary_password if temporary_password is not None else password
    if keycloak_id and secret:
        set_temporary_password(keycloak_id, secret)

    if keycloak_id:
        _assign_realm_role(keycloak_id, "login_access")

    return keycloak_id


def update_keycloak_user(
    user_id: str,
    *,
    email: str | None = None,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    enabled: bool | None = None,
) -> bool:
    if not is_keycloak_enabled() or not user_id:
        return False

    payload: dict[str, Any] = {}
    if email is not None:
        payload["email"] = email
    if username is not None:
        payload["username"] = username
    if first_name is not None:
        payload["firstName"] = first_name
    if last_name is not None:
        payload["lastName"] = last_name
    if enabled is not None:
        payload["enabled"] = enabled
    if email is not None or username is not None or first_name is not None or last_name is not None:
        payload["emailVerified"] = True

    if not payload:
        return False

    response = httpx.put(
        f"{_admin_users_url()}/{user_id}",
        headers=_auth_headers(),
        json=payload,
        timeout=15.0,
    )
    response.raise_for_status()
    return True


def disable_keycloak_user(user_id: str) -> bool:
    return update_keycloak_user(user_id, enabled=False)


def enable_keycloak_user(user_id: str) -> bool:
    return update_keycloak_user(user_id, enabled=True)


def _assign_realm_role(user_id: str, role_name: str) -> bool:
    try:
        role_response = httpx.get(
            f"{_admin_base_url()}/roles/{role_name}",
            headers=_auth_headers(),
            timeout=10.0,
        )
        if role_response.status_code != 200:
            return False

        role = role_response.json()
        assign_response = httpx.post(
            f"{_admin_users_url()}/{user_id}/role-mappings/realm",
            headers=_auth_headers(),
            json=[{"id": role["id"], "name": role["name"]}],
            timeout=10.0,
        )
        assign_response.raise_for_status()
        return True
    except Exception:
        logger.warning(
            "No se pudo asignar rol '%s' al usuario %s",
            role_name,
            user_id,
            exc_info=True,
        )
        return False


def _find_keycloak_user_id(*, username: str) -> str | None:
    response = httpx.get(
        _admin_users_url(),
        params={"username": username, "exact": "true"},
        headers=_auth_headers(),
        timeout=10.0,
    )
    response.raise_for_status()
    users = response.json()
    if users:
        return users[0].get("id")
    return None
