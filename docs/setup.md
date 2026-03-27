# Guía de Configuración y Despliegue

## Requisitos del Sistema

| Componente | Versión mínima |
|-----------|----------------|
| Python | 3.11 |
| PostgreSQL | 15+ |
| ClickHouse | 23+ |
| Docker & Docker Compose | 20+ / 2.x |

---

## Entorno de Desarrollo

### 1. Clonar el repositorio

```bash
git clone <repo-url>
cd ventana-backend-demo
```

### 2. Crear entorno virtual

```bash
python -m venv .venv

# Activar en Linux/macOS
source .venv/bin/activate

# Activar en Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Levantar PostgreSQL con Docker

```bash
docker-compose up -d
```

Esto inicia un contenedor `ventana_magica_db` con:
- Usuario: `dev_pnud`
- Contraseña: `M1d3sPnud@`
- Base de datos: `db_ventana_pnud`
- Puerto: `5432`

### 5. Configurar variables de entorno

El archivo `.env` controla toda la configuración. La variable `ENV` determina qué bloque de variables se usa (`LOCAL` o `PROD`).

```bash
# El archivo .env ya existe en el repositorio.
# Modifica los valores según tu entorno local.
nano .env
```

Consulta la [referencia completa de variables de entorno](#referencia-de-variables-de-entorno) al final de este documento.

### 6. Ejecutar migraciones

```bash
alembic upgrade head
```

Esto crea todas las tablas y carga el seed inicial de roles y permisos.

### 7. Crear usuario administrador

```bash
python scripts/create_admin.py
```

### 8. (Opcional) Cargar datos de datasources de ejemplo

```bash
python scripts/seed_data_sources.py
```

### 9. Iniciar el servidor

```bash
uvicorn main:app --reload --port 8000
```

**URLs disponibles:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## Migraciones de Base de Datos

El proyecto usa [Alembic](https://alembic.sqlalchemy.org/) para gestionar el esquema de PostgreSQL.

### Comandos frecuentes

```bash
# Ver estado actual de migraciones
alembic current

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Aplicar una migración específica
alembic upgrade <revision_id>

# Revertir la última migración
alembic downgrade -1

# Crear una nueva migración (auto-generada desde modelos)
alembic revision --autogenerate -m "descripcion del cambio"

# Ver historial de migraciones
alembic history
```

### Orden de migraciones

Las migraciones se ejecutan en orden por su `revision` y `down_revision`. El orden actual:

1. `087ed57181ee` — Tabla de tickets
2. `001_users_auth` — Tablas de usuarios, roles, permisos, instituciones, sesiones
3. `002_seed_roles_permissions` — Seed de roles y permisos del sistema
4. `df2585f09ea6` — DataSources y columnas
5. `604001d39dc6` — Flags `is_groupable` y `group_by`
6. `b7b4921cf417` — Structured base filter
7. `2e6a9bda8c33` — `institution_id`, `is_shared` en consultas
8. `282a99637c4d` — Descripción en datasources y columnas
9. `e7d4a1f3c9ab` — Institution API tokens
10. `f2c91b6e4d10` — Permiso `datasources:manage` en seed
11. `c1a2f7c9e5b4` — User query checkpoints

---

## Ejecutar Tests

### Tests unitarios e integración

```bash
# Todos los tests
pytest

# Tests de un módulo específico
pytest tests/v1/test_auth.py
pytest tests/v1/test_users.py

# Con output detallado
pytest -v

# Con cobertura (requiere pytest-cov)
pytest --cov=api --cov-report=html
```

### Base de datos de tests

Los tests usan una base de datos PostgreSQL separada. Configura la variable en tu `.env`:

```env
TEST_DATABASE_URL=postgresql+psycopg2://dev_pnud:M1d3sPnud%40@127.0.0.1:5432/db_ventana_pnud_test
```

La base de datos de tests se crea y elimina automáticamente en cada test (`scope="function"` con `create_all` / `drop_all`).

### Script de tests de usuarios

```bash
bash run_user_tests.sh
# Opciones: all | users | auth | roles | institutions | beneficiarios
bash run_user_tests.sh users
```

---

## Despliegue en Producción

### Dockerfile

```dockerfile
FROM python:3.11.9
WORKDIR /usr/src/apikit
COPY ./api ./api
COPY requirements.txt requirements.txt
COPY main.py main.py
COPY .env .env
RUN pip3 install -r requirements.txt
```

Construir y ejecutar:

```bash
docker build -t ventana-backend .
docker run -p 8000:8000 ventana-backend uvicorn main:app --host 0.0.0.0 --port 8000
```

### Proxy reverso con Traefik

El archivo `traefik-config.yml` configura Traefik como proxy inverso con TLS:

```yaml
# traefik-config.yml
tls:
  certificates:
    - certFile: "/certs/fullchain.crt"
      keyFile: "/certs/wildcard.key"
```

Ajusta las secciones `routers` y `services` con el dominio de producción.

### Variables críticas en producción

```env
ENV=PROD
JWT_SECRET_KEY=<clave-aleatoria-de-al-menos-64-chars>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Activar cifrado de respuestas (opcional pero recomendado)
RESPONSE_ENCRYPTION_ENABLED=true
RESPONSE_ENCRYPTION_KEY_B64=<clave-AES-256-en-base64url>

# PostgreSQL de producción
PROD_DB_ACTIVA=true
PROD_DB_USERNAME=<usuario-prod>
PROD_DB_PASSWORD=<password-prod>
PROD_DB_CONTAINER_NAME=<host-db>
PROD_DB_PORT=5432
PROD_DB_NAME=<nombre-db>

# ClickHouse de producción
PROD_CH_ACTIVA=true
PROD_CH_HOST=<host-ch>
PROD_CH_PORT=8123
PROD_CH_USER=<usuario-ch>
PROD_CH_PASSWORD=<password-ch>
PROD_CH_DATABASE=rsh
PROD_CH_SECURE=true
```

### Generar clave AES para cifrado

```python
import os, base64
key = os.urandom(32)  # 256 bits
print(base64.urlsafe_b64encode(key).decode())
```

---

## Referencia de Variables de Entorno

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `ENV` | Sí | `LOCAL` | Modo de entorno (`LOCAL` / `PROD`) |
| **JWT** | | | |
| `JWT_SECRET_KEY` | Sí | — | Clave secreta para firmar JWT (mín. 32 chars) |
| `JWT_ALGORITHM` | No | `HS256` | Algoritmo de firma JWT |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Minutos de vigencia del access token |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Días de vigencia del refresh token |
| **Cifrado de respuestas** | | | |
| `RESPONSE_ENCRYPTION_ENABLED` | No | `false` | Habilitar cifrado AES-GCM de respuestas |
| `RESPONSE_ENCRYPTION_KEY_B64` | Condicional | — | Clave AES en base64url (requerida si cifrado activo) |
| **PostgreSQL** | | | |
| `{ENV}_DB_ACTIVA` | No | `false` | Habilitar conexión a PostgreSQL |
| `{ENV}_DB_USERNAME` | Condicional | — | Usuario de la base de datos |
| `{ENV}_DB_PASSWORD` | Condicional | — | Contraseña de la base de datos |
| `{ENV}_DB_CONTAINER_NAME` | Condicional | — | Host del servidor PostgreSQL |
| `{ENV}_DB_PORT` | Condicional | — | Puerto PostgreSQL (generalmente `5432`) |
| `{ENV}_DB_NAME` | Condicional | — | Nombre de la base de datos |
| `{ENV}_DB_URL` | No | — | URL completa (alternativa a las variables individuales) |
| **SQL Server** (legacy) | | | |
| `{ENV}_DB_ACTIVA_SQL` | No | `false` | Habilitar conexión SQL Server |
| `{ENV}_DB_SQL_ODBC_DRIVER` | No | `ODBC Driver 17 for SQL Server` | Driver ODBC |
| **ClickHouse** | | | |
| `{ENV}_CH_ACTIVA` | No | `false` | Habilitar conexión a ClickHouse |
| `{ENV}_CH_HOST` | Condicional | — | Host del servidor ClickHouse |
| `{ENV}_CH_PORT` | Condicional | — | Puerto HTTP de ClickHouse (generalmente `8123`) |
| `{ENV}_CH_USER` | Condicional | — | Usuario ClickHouse |
| `{ENV}_CH_PASSWORD` | Condicional | — | Contraseña ClickHouse |
| `{ENV}_CH_DATABASE` | Condicional | — | Base de datos ClickHouse (ej: `rsh`) |
| `{ENV}_CH_SECURE` | No | `false` | Usar HTTPS para ClickHouse |
| **Tests** | | | |
| `TEST_DATABASE_URL` | No | URL por defecto | URL PostgreSQL para tests |

> `{ENV}` se reemplaza por `LOCAL` o `PROD` según el valor de la variable `ENV`.

---

## CORS

Los orígenes permitidos están configurados en `main.py`:

```python
origins = [
    "http://localhost:3000",
    "http://localhost:3002",
    "http://localhost:8080",
]
```

Para agregar orígenes de producción, modifica esta lista directamente o externaliza la configuración a una variable de entorno.
