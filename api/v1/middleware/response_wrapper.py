import json
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class ResponseWrapperMiddleware(BaseHTTPMiddleware):
    # Headers que deben preservarse (CORS, etc.)
    _PASSTHROUGH_PREFIXES = ("access-control-",)

    def _carry_headers(self, original_response, new_response):
        """Copia headers CORS del response original al nuevo."""
        for key, value in original_response.headers.items():
            if any(key.lower().startswith(p) for p in self._PASSTHROUGH_PREFIXES):
                new_response.headers[key] = value
        return new_response

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.path == "/openapi.json":
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            original_data = json.loads(body)
        except json.JSONDecodeError:
            original_data = body.decode()

        if (
            isinstance(original_data, dict)
            and {"result", "message", "data"}.issubset(original_data)
        ):
            new_resp = JSONResponse(content=original_data, status_code=response.status_code)
            return self._carry_headers(response, new_resp)

        wrapped = {
            "result": True,
            "message": "OK",
            "data": original_data,
        }

        new_resp = JSONResponse(content=wrapped, status_code=response.status_code)
        return self._carry_headers(response, new_resp)
