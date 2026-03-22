from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

import httpx
from decouple import config
from jose import JWTError, jwt


KEYCLOAK_DOMAIN = config("KEYCLOAK_DOMAIN", default="").rstrip("/")
KEYCLOAK_REALM = config("KEYCLOAK_REALM", default="")
KEYCLOAK_CLIENT_ID = config("KEYCLOAK_CLIENT_ID", default="")
KEYCLOAK_AUDIENCE = config("KEYCLOAK_AUDIENCE", default="")
KEYCLOAK_VERIFY_AUDIENCE = config(
    "KEYCLOAK_VERIFY_AUDIENCE", default=True, cast=bool
)
KEYCLOAK_JWKS_CACHE_TTL = config("KEYCLOAK_JWKS_CACHE_TTL", default=300, cast=int)

_JWKS_CACHE: dict[str, Any] = {"keys": None, "expires_at": None}
_JWKS_LOCK = Lock()


@dataclass
class KeycloakIdentity:
    subject: str
    email: str | None
    username: str | None
    first_name: str | None
    last_name: str | None
    full_name: str | None
    payload: dict[str, Any]


def is_keycloak_enabled() -> bool:
    return bool(KEYCLOAK_DOMAIN and KEYCLOAK_REALM and KEYCLOAK_CLIENT_ID)


def get_keycloak_issuer() -> str:
    return f"{KEYCLOAK_DOMAIN}/realms/{KEYCLOAK_REALM}"


def get_keycloak_jwks_url() -> str:
    return f"{get_keycloak_issuer()}/protocol/openid-connect/certs"


def _cached_keys_are_valid() -> bool:
    expires_at = _JWKS_CACHE.get("expires_at")
    return bool(
        _JWKS_CACHE.get("keys")
        and expires_at
        and expires_at > datetime.now(timezone.utc)
    )


def get_keycloak_public_keys() -> list[dict[str, Any]]:
    if not is_keycloak_enabled():
        return []

    if _cached_keys_are_valid():
        return _JWKS_CACHE["keys"]

    with _JWKS_LOCK:
        if _cached_keys_are_valid():
            return _JWKS_CACHE["keys"]

        response = httpx.get(get_keycloak_jwks_url(), timeout=10.0)
        response.raise_for_status()
        payload = response.json()
        keys = payload.get("keys", [])
        _JWKS_CACHE["keys"] = keys
        _JWKS_CACHE["expires_at"] = datetime.now(timezone.utc).replace(
            microsecond=0
        ) + timedelta(seconds=KEYCLOAK_JWKS_CACHE_TTL)
        return keys


def _select_jwk(token: str) -> dict[str, Any] | None:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        return None

    kid = header.get("kid")
    if not kid:
        return None

    for key in get_keycloak_public_keys():
        if key.get("kid") == kid:
            return key
    return None


def verify_keycloak_token(token: str) -> dict[str, Any] | None:
    if not is_keycloak_enabled():
        return None

    jwk_key = _select_jwk(token)
    if not jwk_key:
        return None

    audience = KEYCLOAK_AUDIENCE or KEYCLOAK_CLIENT_ID

    options = {"verify_aud": KEYCLOAK_VERIFY_AUDIENCE}
    try:
        return jwt.decode(
            token,
            jwk_key,
            algorithms=["RS256"],
            issuer=get_keycloak_issuer(),
            audience=audience if KEYCLOAK_VERIFY_AUDIENCE else None,
            options=options,
        )
    except JWTError:
        return None


def extract_keycloak_identity(payload: dict[str, Any]) -> KeycloakIdentity | None:
    subject = payload.get("sub")
    if not subject:
        return None

    return KeycloakIdentity(
        subject=subject,
        email=payload.get("email"),
        username=payload.get("preferred_username"),
        first_name=payload.get("given_name"),
        last_name=payload.get("family_name"),
        full_name=payload.get("name"),
        payload=payload,
    )
