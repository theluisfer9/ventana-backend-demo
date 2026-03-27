# Arquitectura del Sistema

## Diagrama de alto nivel

```
┌──────────────────────────────────────────────────────────────────┐
│                          Clientes                                 │
│         Frontend Web        |       Sistemas Externos (M2M)       │
│      (JWT Bearer Token)     |          (API Token)                │
└──────────────────┬──────────────────────┬────────────────────────┘
                   │                      │
                   ▼                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Traefik (TLS)                             │
│                     Proxy inverso HTTPS                          │
└──────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                   FastAPI Application (Uvicorn)                  │
│                                                                   │
│   Middlewares (en orden de ejecución):                           │
│   1. CORS                                                         │
│   2. ResponseWrapperMiddleware   ← Envuelve JSON en {result,data}│
│   3. ResponseEncryptionMiddleware ← AES-GCM (opcional)           │
│                                                                   │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│   │  /auth   │  │  /users  │  │  /roles  │  │ /institutions│   │
│   └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
│   ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│   │ /beneficiarios │  │  /consulta   │  │ /integration/... │   │
│   └────────────────┘  └──────────────┘  └──────────────────┘   │
│   ┌─────────────┐  ┌───────────┐  ┌──────────────────────┐     │
│   │ /datasources│  │ /queries  │  │      /dashboard       │     │
│   └─────────────┘  └───────────┘  └──────────────────────┘     │
└──────────────┬───────────────────────────┬───────────────────────┘
               │                           │
               ▼                           ▼
  ┌────────────────────┐      ┌──────────────────────────┐
  │     PostgreSQL 16  │      │   ClickHouse (RSH)        │
  │                    │      │                           │
  │  - users           │      │  - rsh.vw_hogares         │
  │  - roles           │      │  - rsh.vw_personas        │
  │  - permissions     │      │  - rsh.vw_viviendas       │
  │  - institutions    │      │  - rsh.vw_beneficios_x_   │
  │  - user_sessions   │      │    hogar                  │
  │  - data_sources    │      │  - (otras vistas RSH)     │
  │  - saved_queries   │      │                           │
  │  - tickets         │      └──────────────────────────┘
  └────────────────────┘
```

---

## Componentes principales

### 1. Capa de Transporte — Middlewares

El orden de middleware en `main.py` es significativo ya que se ejecuta en pila (LIFO para response):

#### `ResponseWrapperMiddleware`
Normaliza todas las respuestas JSON a un sobre estándar:

```json
{
  "result": true,
  "message": "OK",
  "data": { ... }
}
```

Las respuestas que no son JSON (streaming de archivos) pasan sin modificar. Las rutas de Swagger (`/openapi.json`) también se omiten.

#### `ResponseEncryptionMiddleware`
Cifrado opcional de respuestas usando **AES-256-GCM**. Se activa con `RESPONSE_ENCRYPTION_ENABLED=true`. Cuando está habilitado, el cuerpo de la respuesta se cifra y se envuelve en:

```json
{
  "enc": true,
  "v": 1,
  "data": "<base64url del ciphertext+tag>"
}
```

Se incluye `aad` (Additional Authenticated Data) con `METHOD:PATH` para prevenir replay attacks entre endpoints.

---

### 2. Capa de Autenticación

El sistema soporta dos modos de autenticación:

#### A. JWT Bearer Token (usuarios del sistema)
- Al hacer login (`POST /auth/login`) se generan dos tokens:
  - **Access token**: expira en 30 minutos (configurable), contiene `sub` (user_id), `role`, `jti`
  - **Refresh token**: expira en 7 días, almacenado en la tabla `user_sessions`
- La sesión activa se guarda en PostgreSQL. Al hacer logout se eliminan todas las sesiones.
- El access token se verifica en cada request mediante la dependencia `get_current_user`.

#### B. API Token (integración M2M)
- Las instituciones pueden generar tokens de integración desde `/institutions/{id}/api-tokens`
- El token se genera con `secrets.token_urlsafe(32)` y se almacena como **hash SHA-256**
- Los tokens tienen prefijo legible (ej: `vtk_XXXXXXXX`) y fecha de expiración opcional
- Se autentican mediante el header `Authorization: Bearer <token>` en rutas `/integration/*`

---

### 3. Capa de Autorización — RBAC

Se implementa un sistema de **Role-Based Access Control** en dos niveles:

#### Nivel 1: Permisos por rol
Cada usuario tiene exactamente un rol. Cada rol tiene un conjunto de permisos. Los permisos se verifican con la dependencia `RequirePermission(PermissionCode.XXX)`.

```
Usuario ──► Rol ──► Permisos[]
```

Roles del sistema por defecto:
- `ADMIN` — Acceso total al sistema
- `ANALYST` — Lectura y exportación de datos, gestión de reportes
- `INSTITUTIONAL` — Solo lectura y exportación de beneficiarios

#### Nivel 2: Scoping institucional
Los usuarios institucionales solo ven datos de su institución. Este scoping se aplica en:
- `GET /institutions/` — Solo retorna su propia institución
- `GET /datasources/` — Filtra por `institution_id`
- `GET /consulta/*` — Filtra ClickHouse por el preset institucional
- `GET /queries/*` — Accede a DataSources de su institución o asignados a su rol

---

### 4. Capa de Datos — Dual Database

#### PostgreSQL (operacional)
Gestiona todos los datos del sistema: usuarios, roles, permisos, instituciones, sesiones, consultas guardadas. Se accede mediante SQLAlchemy ORM con sesiones síncronas (psycopg2).

#### ClickHouse (analítico)
Almacena el **Registro Social de Hogares (RSH)** con millones de registros de hogares, personas y beneficios. Se accede mediante `clickhouse-connect` de forma directa (sin ORM). Las queries se construyen con concatenación segura de strings validados contra listas blancas (sin SQL injection por parámetros de usuario).

---

### 5. Sistema de Presets Institucionales

El archivo `api/v1/config/institutional_presets.py` define la vista de datos para cada institución:

```python
INSTITUTIONAL_PRESETS = {
    "FODES": {
        "table": "rsh.vw_beneficios_x_hogar",
        "base_filter_columns": ["prog_fodes"],  # Columnas de filtro base (OR/AND)
        "base_filter_logic": "OR",
        "columns": [...],            # Columnas a mostrar en la lista
        "intervention_columns": [...], # Columnas binarias de intervenciones
        "allowed_filters": [...],    # Filtros permitidos para el usuario
        "labels": {...},             # Nombres legibles para el frontend
    },
    "MAGA": { ... },
    "MIDES": { ... },
}
```

Cuando un usuario de la institución `FODES` consulta `/consulta/`, la query ClickHouse incluye automáticamente `WHERE prog_fodes = 1`, limitando los resultados al universo FODES.

---

### 6. Query Builder (Motor de Consultas Ad-hoc)

Permite a usuarios con permisos `databases:read` o `reports:read` construir consultas sobre cualquier DataSource al que tengan acceso. Soporta:

- **Selección de columnas** — de las columnas marcadas como `is_selectable`
- **Filtros dinámicos** — columnas marcadas como `is_filterable`, con operadores: `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `in`, `between`
- **Agrupación y agregaciones** — `GROUP BY` + funciones `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` sobre columnas `is_groupable`
- **Exportación** — CSV (streaming), Excel (ZIP por chunks), PDF (ZIP)
- **Guardar consultas** — Se persisten en PostgreSQL con opción de compartir a nivel institucional

La seguridad del motor está garantizada por:
1. **Validación de columnas**: solo se permiten columnas que existen en `DataSourceColumn` para ese datasource
2. **Identificadores seguros**: la tabla ClickHouse se valida con `_safe_identifier()` (regex `^[a-zA-Z0-9_.]+$`)
3. **Parámetros vinculados**: los valores de filtros se pasan como parámetros a `clickhouse-connect`, nunca interpolados

---

### 7. Sistema de Exportación

Implementado con `StreamingResponse` para evitar cargar todos los datos en memoria:

| Formato | Librería | Límite | Estrategia |
|---------|----------|--------|-----------|
| CSV | stdlib `csv` | Sin límite práctico | Streaming por chunks |
| Excel | openpyxl | 1,000,000 filas | Múltiples hojas en ZIP quando supera umbral |
| PDF | fpdf2 | 50,000 filas | Múltiples archivos en ZIP |

Para beneficiarios RSH se usa un límite fijo de 10,000 registros en exportación directa. Para el Query Builder los límites son configurables por formato.

---

## Flujo de una request típica

```
1. Cliente envía: GET /api/v1/beneficiarios/?departamento=01
   Header: Authorization: Bearer <access_token>

2. Traefik → FastAPI

3. CORS middleware valida origen

4. Router /beneficiarios/ ejecuta la función handler

5. Dependencia get_current_user:
   a. Extrae JWT del header
   b. Verifica firma y expiración
   c. Valida que la sesión exista en PostgreSQL (no revocada)
   d. Carga el usuario con su rol y permisos

6. Dependencia RequirePermission(BENEFICIARIES_READ):
   a. Verifica que el usuario tenga el permiso
   b. Si no → 403 Forbidden

7. Handler ejecuta query_beneficiarios_lista(client, departamento="01")
   → Genera SQL ClickHouse con WHERE y parámetros seguros

8. ClickHouse retorna rows

9. Mapper transforma rows en schema Pydantic BeneficiarioResumen[]

10. ResponseWrapperMiddleware:
    {result: true, message: "OK", data: {items: [...], total: N}}

11. (Si cifrado activo) ResponseEncryptionMiddleware: AES-GCM

12. Cliente recibe respuesta 200
```
