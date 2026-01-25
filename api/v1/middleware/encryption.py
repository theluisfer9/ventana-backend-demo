from __future__ import annotations
import os, json, base64
from decouple import config
from typing import Optional, Set, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class ResponseEncryptionMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app,
            *,
            enabled: Optional[bool] = None,
            key_b64: Optional[str] = None,
            exclude_paths: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.enabled = config("RESPONSE_ENCRYPTION_ENABLED", cast=bool, default=False) if enabled is None else enabled
        self.exclude_paths = exclude_paths or {"/docs", "/redoc", "/openapi.json", "/healthz"}
        if not self.enabled:
            self.key = None
            return
        kb64 = key_b64 or config("RESPONSE_ENCRYPTION_KEY_B64", default=None)
        if not kb64:
            raise RuntimeError("Encryption enabled pero falta RESPONSE_ENCRYPTION_KEY_B64")
        self.key = base64.urlsafe_b64decode(kb64)
        if len(self.key) not in (16, 24, 32):
            raise RuntimeError("RESPONSE_ENCRYPTION_KEY_B64 debe ser 128/192/256 bits")

    async def dispatch(self, request, call_next):
        if not self.enabled or request.url.path in self.exclude_paths or request.headers.get(
                "x-bypass-encryption") == "1":
            return await call_next(request)

        resp = await call_next(request)

        body = b""
        async for chunk in resp.body_iterator:
            body += chunk

        aad = f"{request.method}:{request.url.path}".encode()
        nonce = os.urandom(12)
        ct = AESGCM(self.key).encrypt(nonce, body, aad)

        envelope: Dict[str, Any] = {
            "enc": True,
            "v": 1,
            "data": base64.urlsafe_b64encode(ct).decode(),
        }
        new_body = json.dumps(envelope).encode("utf-8")

        headers = dict(resp.headers)
        headers["content-type"] = "application/json; charset=utf-8"
        headers["x-encrypted"] = "1"
        headers.pop("content-length", None)
        headers.pop("content-encoding", None)

        return Response(
            content=new_body,
            status_code=resp.status_code,
            headers=headers,
            media_type="application/json",
        )
