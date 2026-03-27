# Ventana Backend — Documentación Técnica

[![Python](https://img.shields.io/badge/Python-3.11.9-yellow?logo=python)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.14-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)](https://www.postgresql.org/)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-RSH-orange)](https://clickhouse.com/)
[![Pytest](https://img.shields.io/badge/Pytest-8.4.1-red?logo=pytest)](https://docs.pytest.org/)

API REST para el sistema **Ventana Mágica** — plataforma de gestión y consulta de beneficiarios del Registro Social de Hogares (RSH) de Guatemala. Permite a instituciones gubernamentales consultar, filtrar y exportar datos de hogares según su alcance institucional.

---

## Tabla de Contenidos

- [Visión General](#visión-general)
- [Inicio Rápido](#inicio-rápido)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Stack Tecnológico](#stack-tecnológico)
- [Documentación Detallada](#documentación-detallada)

---

## Visión General

El backend expone una API REST bajo `/api/v1` compuesta por los siguientes módulos principales:

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Autenticación | `/auth` | Login, refresh token, logout, perfil de usuario |
| Usuarios | `/users` | CRUD de usuarios del sistema |
| Roles y Permisos | `/roles` | Gestión de roles RBAC y sus permisos |
| Instituciones | `/institutions` | CRUD de instituciones + API tokens M2M |
| Beneficiarios RSH | `/beneficiarios` | Consulta de hogares del RSH desde ClickHouse |
| Consulta Institucional | `/consulta` | Vista de datos scoped al universo de la institución |
| Integración M2M | `/integration/consulta` | Acceso vía API Token para sistemas externos |
| DataSources (Admin) | `/datasources` | Gestión de fuentes de datos ClickHouse |
| Query Builder | `/queries` | Consultas ad-hoc y guardadas sobre datasources |
| Dashboard | `/dashboard` | Estadísticas globales e institucionales |

---

## Inicio Rápido

### 1. Requisitos previos

- Python 3.11+
- PostgreSQL 16 (o Docker)
- Acceso al servidor ClickHouse RSH

### 2. Clonar e instalar

```bash
git clone <repo-url>
cd ventana-backend-demo

python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Edita el archivo `.env` con los valores de tu entorno. Variables mínimas necesarias:

```env
ENV=LOCAL
JWT_SECRET_KEY=<clave-minimo-32-chars>

# PostgreSQL
LOCAL_DB_ACTIVA=true
LOCAL_DB_USERNAME=dev_pnud
LOCAL_DB_PASSWORD=<password>
LOCAL_DB_CONTAINER_NAME=localhost
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=db_ventana_pnud

# ClickHouse
LOCAL_CH_ACTIVA=true
LOCAL_CH_HOST=<host>
LOCAL_CH_PORT=8123
LOCAL_CH_USER=<usuario>
LOCAL_CH_PASSWORD=<password>
LOCAL_CH_DATABASE=rsh
```

### 4. Levantar PostgreSQL con Docker

```bash
docker-compose up -d
```

### 5. Ejecutar migraciones

```bash
alembic upgrade head
```

### 6. Iniciar el servidor

```bash
uvicorn main:app --reload
```

Swagger UI disponible en: `http://localhost:8000/docs`

---

## Estructura del Proyecto

```
ventana-backend-demo/
├── main.py                        # Punto de entrada: monta la app, routers y middlewares
├── alembic.ini                    # Configuración de Alembic
├── requirements.txt               # Dependencias Python
├── docker-compose.yml             # PostgreSQL en Docker para desarrollo
├── dockerfile                     # Imagen de la API
├── traefik-config.yml             # Configuración del proxy reverso Traefik
├── pytest.ini                     # Configuración de Pytest
│
├── alembic/
│   └── versions/                  # Migraciones de base de datos
│
├── api/
│   ├── config/
│   │   └── app.py                 # APP_NAME, VERSION
│   ├── utils/                     # Validación de variables de entorno
│   └── v1/
│       ├── auth/
│       │   ├── jwt_handler.py     # Creación y verificación de JWT
│       │   ├── password.py        # Hash y verificación de contraseñas (bcrypt)
│       │   └── permissions.py     # PermissionCode enum + ROLE_PERMISSIONS
│       ├── config/
│       │   ├── database.py        # Conexiones a PostgreSQL, SQL Server y ClickHouse
│       │   └── institutional_presets.py  # Presets de consulta por institución
│       ├── dependencies/          # Dependencias de FastAPI (auth, permisos, filtros)
│       ├── handlers/              # Manejadores globales de excepciones
│       ├── middleware/
│       │   ├── response_wrapper.py       # Envuelve respuestas en {result, message, data}
│       │   └── encryption.py             # Cifrado AES-GCM opcional de respuestas
│       ├── models/                # Modelos SQLAlchemy (PostgreSQL)
│       ├── routes/                # Routers y definición de endpoints HTTP
│       ├── schemas/               # Schemas Pydantic (validación y serialización)
│       ├── services/              # Lógica de negocio
│       │   ├── rsh/               # Queries RSH sobre ClickHouse
│       │   ├── consulta/          # Queries institucionales sobre ClickHouse
│       │   ├── query_engine/      # Motor de consultas ad-hoc
│       │   ├── dashboard/         # Queries del dashboard
│       │   └── ...                # Servicios por dominio
│       └── utils/
│
├── scripts/                       # Scripts de seed y administración
├── tests/
│   └── v1/
│       ├── conftest.py            # Fixtures (BD de prueba PostgreSQL)
│       └── test_*.py              # Tests por dominio
└── docs/                          # Documentación técnica
```

---

## Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Framework web | FastAPI | 0.115.14 |
| ORM | SQLAlchemy | 2.0.41 |
| Migraciones | Alembic | 1.16.5 |
| BD operacional | PostgreSQL | 16 |
| BD analítica | ClickHouse | — |
| Autenticación | python-jose + passlib/bcrypt | 3.3.0 / 1.7.4 |
| Cifrado respuestas | cryptography (AES-GCM) | 45.0.6 |
| Exportación | openpyxl + fpdf2 | 3.1.5 / 2.8.3 |
| Validación schemas | Pydantic | 2.11.7 |
| Paginación | fastapi-pagination | 0.14.0 |
| Testing | pytest + httpx | 8.4.1 / 0.28.1 |
| Servidor ASGI | Uvicorn | 0.35.0 |
| Proxy reverso | Traefik | v3 |

---

## Documentación Detallada

| Documento | Descripción |
|-----------|-------------|
| [docs/architecture.md](docs/architecture.md) | Arquitectura del sistema, flujo de datos y componentes clave |
| [docs/setup.md](docs/setup.md) | Configuración completa del entorno de desarrollo y producción |
| [docs/auth-permissions.md](docs/auth-permissions.md) | Sistema JWT, RBAC, roles y permisos |
| [docs/api-endpoints.md](docs/api-endpoints.md) | Referencia de todos los endpoints con ejemplos |
| [docs/data-model.md](docs/data-model.md) | Modelo de datos, entidades y relaciones |
