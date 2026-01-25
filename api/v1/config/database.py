from collections.abc import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from decouple import config
from typing import Optional, Generator
from api.utils import (
    validar_env_var_bool,
    validar_env_var_string,
    validar_env_var_number,
    validar_env_var_requeridas,
)

env_mode = config("ENV", default="LOCAL")


def build_pg_sync_url() -> Optional[URL | str]:
    """
    Construye la URL de conexión SINCRONA a PostgreSQL.
    Variables de entorno esperadas (análogas a las de PG async):
      {ENV}_DB_ACTIVA_PG_SYNC (bool)  -> activa/desactiva esta conexión
      {ENV}_DB_URL_PG_SYNC (str)      -> URL completa opcional; si viene, se usa tal cual
      {ENV}_DB_USERNAME
      {ENV}_DB_PASSWORD
      {ENV}_DB_CONTAINER_NAME
      {ENV}_DB_PORT
      {ENV}_DB_NAME
    """
    activa = validar_env_var_bool(
        validar_env_var_string(f"{env_mode}_DB_ACTIVA", "false")
    )
    if not activa:
        return None

    # si el usuario da una URL completa, úsala (ej: postgresql+psycopg://user:pass@host:5432/dbname)
    url = validar_env_var_string(f"{env_mode}_DB_URL", "")
    if url:
        return url

    # De lo contrario, construir desde piezas (reutilizamos las mismas claves base del async PG)
    validar_env_var_requeridas(
        [
            f"{env_mode}_DB_USERNAME",
            f"{env_mode}_DB_PASSWORD",
            f"{env_mode}_DB_CONTAINER_NAME",
            f"{env_mode}_DB_PORT",
            f"{env_mode}_DB_NAME",
        ]
    )

    return URL.create(
        # Recomendado: psycopg (v3). Para psycopg2 usar: "postgresql+psycopg2"
        drivername="postgresql+psycopg2",
        username=validar_env_var_string(f"{env_mode}_DB_USERNAME"),
        password=validar_env_var_string(f"{env_mode}_DB_PASSWORD"),
        host=validar_env_var_string(f"{env_mode}_DB_CONTAINER_NAME"),
        port=validar_env_var_number(f"{env_mode}_DB_PORT"),
        database=validar_env_var_string(f"{env_mode}_DB_NAME"),
    )

def build_pg_async_url() -> Optional[URL | str]:
    activa = validar_env_var_bool(
        validar_env_var_string(f"{env_mode}_DB_ACTIVA", "false")
    )
    if not activa:
        return None

    url = validar_env_var_string(f"{env_mode}_DB_URL", "")
    if url:
        return url

    validar_env_var_requeridas(
        [
            f"{env_mode}_DB_USERNAME",
            f"{env_mode}_DB_PASSWORD",
            f"{env_mode}_DB_CONTAINER_NAME",
            f"{env_mode}_DB_PORT",
            f"{env_mode}_DB_NAME",
        ]
    )

    return URL.create(
        drivername="postgresql+asyncpg",
        username=validar_env_var_string(f"{env_mode}_DB_USERNAME"),
        password=validar_env_var_string(f"{env_mode}_DB_PASSWORD"),
        host=validar_env_var_string(f"{env_mode}_DB_CONTAINER_NAME"),
        port=validar_env_var_number(f"{env_mode}_DB_PORT"),
        database=validar_env_var_string(f"{env_mode}_DB_NAME"),
    )

def build_sql_url() -> Optional[URL | str]:
    activa = validar_env_var_bool(
        validar_env_var_string(f"{env_mode}_DB_ACTIVA_SQL", "false")
    )
    if not activa:
        return None

    url = validar_env_var_string(f"{env_mode}_DB_SQL_URL", "")
    if url:
        return url

    validar_env_var_requeridas(
        [
            f"{env_mode}_DB_USERNAME_SQL",
            f"{env_mode}_DB_PASSWORD_SQL",
            f"{env_mode}_DB_PORT_SQL",
            f"{env_mode}_DB_NAME_SQL",
        ]
    )

    driver: str = (
        validar_env_var_string(f"{env_mode}_DB_SQL_ODBC_DRIVER")
        or "ODBC Driver 17 for SQL Server"
    )

    return URL.create(
        drivername="mssql+pyodbc",
        username=validar_env_var_string(f"{env_mode}_DB_USERNAME_SQL"),
        password=validar_env_var_string(f"{env_mode}_DB_PASSWORD_SQL"),
        host=validar_env_var_string(f"{env_mode}_DB_CONTAINER_NAME_SQL"),
        port=validar_env_var_number(f"{env_mode}_DB_PORT_SQL"),
        database=validar_env_var_string(f"{env_mode}_DB_NAME_SQL"),
        query={
            "driver": driver,
        },
    )

_pg_sync_url = build_pg_sync_url()
_pg_async_url = build_pg_async_url()
_sql_url = build_sql_url()

pg_sync_engine = (
    create_engine(
        _pg_sync_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    if _pg_sync_url
    else None
)

pg_async_engine = (
    create_async_engine(_pg_async_url, echo=False, future=True)
    if _pg_async_url
    else None
)
sql_engine = (
    create_engine(_sql_url, echo=False, pool_pre_ping=True, pool_recycle=1800)
    if _sql_url
    else None
)

PGSyncSessionLocal = (
    sessionmaker(autocommit=False, autoflush=False, bind=pg_sync_engine)
    if pg_sync_engine
    else None
)
SessionLocalPG = PGSyncSessionLocal
PGAsyncSessionLocal = (
    async_sessionmaker(pg_async_engine, expire_on_commit=False)
    if pg_async_engine
    else None
)

SQLSessionLocal = (
    sessionmaker(autocommit=False, autoflush=False, bind=sql_engine)
    if sql_engine
    else None
)

BasePG = declarative_base()
BaseSQL = declarative_base()

def get_sync_db_pg() -> Generator[Session, None, None]:
    if PGSyncSessionLocal is None:
        raise RuntimeError(
            f"PostgreSQL (síncrono) no está activo (revisa {env_mode}_DB_ACTIVA) o falta configuración."
        )
    db = PGSyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db_pg() -> AsyncGenerator[AsyncSession, None]:
    if PGAsyncSessionLocal is None:
        raise RuntimeError(
            f"PostgreSQL (asíncrono) no está activo (revisa {env_mode}_DB_ACTIVA) o falta configuración."
        )
    async with PGAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_db_sql() -> Generator:
    if SQLSessionLocal is None:
        raise RuntimeError(
            f"SQL Server no está activo (revisa {env_mode}_DB_SQL_ACTIVA) o falta configuración."
        )
    db = SQLSessionLocal()
    try:
        yield db
    finally:
        db.close()