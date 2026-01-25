import json
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class ResponseWrapperMiddleware(BaseHTTPMiddleware):
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
            return JSONResponse(content=original_data, status_code=response.status_code)

        wrapped = {
            "result": True,
            "message": "OK",
            "data": original_data,
        }

        return JSONResponse(content=wrapped, status_code=response.status_code)
