from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from api.v1.utils.validations import get_custom_validation_message

def error_template(message: str, status_code: int, data=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "result": False,
            "message": message,
            "data": data,
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_template(message=exc.detail, status_code=exc.status_code)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    custom_message = get_custom_validation_message(exc)
    if custom_message:
        return error_template(
            message=custom_message,
            status_code=400,
            data=[]
        )

    return error_template(
        message="Error de validación",
        status_code=422,
        data=exc.errors()
    )

async def global_exception_handler(request: Request, exc: Exception):
    return error_template(
        message=f"Error inesperado: {str(exc)}",
        status_code=500
    )
