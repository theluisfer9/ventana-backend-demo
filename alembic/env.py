from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import URL
from alembic import context
from api.v1.config.database import BasePG
from decouple import config as env_config

# Import all models to register them with SQLAlchemy metadata
from api.v1.models import (
    Institution,
    Permission,
    Role,
    role_permissions,
    User,
    UserSession,
    Ticket,
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = BasePG.metadata

# Build database URL
env_mode = env_config("ENV", default="LOCAL")

user = env_config(f"{env_mode}_DB_USERNAME", default="")
pwd = env_config(f"{env_mode}_DB_PASSWORD", default="")
host = env_config(f"{env_mode}_DB_CONTAINER_NAME", default="")
port = env_config(f"{env_mode}_DB_PORT", default="5432")
name = env_config(f"{env_mode}_DB_NAME", default="")

if not all([user, pwd, host, name]):
    raise RuntimeError("Faltan variables de DB para construir sqlalchemy.url")

# Build URL properly handling special characters in password
db_url = URL.create(
    drivername="postgresql+psycopg2",
    username=user,
    password=pwd,
    host=host,
    port=int(port),
    database=name,
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=str(db_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
