from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import RedirectResponse
from api.config.app import APP_NAME, VERSION
from api.v1.config.database import BaseSQL, sql_engine, BasePG, pg_sync_engine
from api.v1.middleware.response_wrapper import ResponseWrapperMiddleware
from api.v1.middleware.encryption import ResponseEncryptionMiddleware
from fastapi_pagination import add_pagination
from api.v1.handlers.exception_handler import (
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

# Import routes
from api.v1.routes import ticket_routes
from api.v1.routes import employee_routes
from api.v1.routes import auth_routes
from api.v1.routes import user_routes
from api.v1.routes import role_routes
from api.v1.routes import institution_routes

# Import models to register them with SQLAlchemy
from api.v1.models import (
    Institution,
    Permission,
    Role,
    User,
    UserSession,
    Ticket,
)

app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description="API de Pantalla Mágica - Sistema de gestión de beneficiarios",
)

add_pagination(app)

origins = [
    "http://localhost:3000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Middleware de Respuesta ----
app.add_middleware(ResponseWrapperMiddleware)
app.add_middleware(ResponseEncryptionMiddleware)

# ---- Manejadores globales ----
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# ---- API Routes ----
# Auth & Users
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(user_routes.router, prefix="/api/v1")
app.include_router(role_routes.router, prefix="/api/v1")
app.include_router(institution_routes.router, prefix="/api/v1")

# Legacy/Example routes
app.include_router(ticket_routes.router, prefix="/api/v1")
app.include_router(employee_routes.router, prefix="/api/v1")

# Create tables
if sql_engine:
    BaseSQL.metadata.create_all(bind=sql_engine)

if pg_sync_engine:
    BasePG.metadata.create_all(bind=pg_sync_engine)


# Redirect / -> Swagger-UI documentation
@app.get("/")
def main_function():
    return RedirectResponse(url="/docs/")
