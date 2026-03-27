# Modelo de Datos

## Base de Datos PostgreSQL

Todas las tablas operacionales residen en PostgreSQL y son gestionadas mediante modelos SQLAlchemy con el `BasePG` declarativo.

---

## Diagrama Entidad-Relación

```
┌───────────────┐    ┌──────────────────┐    ┌──────────────┐
│  institutions │    │      users        │    │    roles     │
│───────────────│    │──────────────────│    │──────────────│
│ id (PK)       │◄───│ institution_id FK│    │ id (PK)      │
│ code (UNQ)    │    │ id (PK)          │───►│ code (UNQ)   │
│ name          │    │ email (UNQ)      │    │ name         │
│ description   │    │ username (UNQ)   │    │ description  │
│ is_active     │    │ password_hash    │    │ is_system    │
│ created_at    │    │ first_name       │    │ created_at   │
│ updated_at    │    │ last_name        │    └──────┬───────┘
└───────┬───────┘    │ phone            │           │
        │            │ role_id (FK)     │    ┌──────▼───────────┐
        │            │ is_active        │    │  role_permissions │
        │            │ is_verified      │    │──────────────────│
        │            │ keycloak_id      │    │ role_id (FK, PK) │
        │            │ created_by (FK)  │    │ permission_id FK │
        │            │ created_at       │    └──────────────────┘
        │            │ updated_at       │           │
        │            │ last_login       │    ┌──────▼───────┐
        │            └────────┬─────────┘    │  permissions │
        │                     │              │──────────────│
        │              ┌──────▼──────────┐   │ id (PK)      │
        │              │  user_sessions   │   │ code (UNQ)   │
        │              │─────────────────│   │ name         │
        │              │ id (PK)          │   │ module       │
        │              │ user_id (FK)     │   │ description  │
        │              │ token_jti (UNQ)  │   └──────────────┘
        │              │ ip_address       │
        │              │ user_agent       │
        │              │ expires_at       │
        │              │ revoked_at       │
        │              │ created_at       │
        │              └──────────────────┘
        │
        │  ┌────────────────────────┐
        └─►│ institution_api_tokens │
           │────────────────────────│
           │ id (PK)                │
           │ institution_id (FK)    │
           │ name                   │
           │ token_prefix (IDX)     │
           │ token_hash             │
           │ is_active              │
           │ expires_at             │
           │ last_used_at           │
           │ created_at             │
           └────────────────────────┘

┌────────────────┐   ┌────────────────────────┐
│  data_sources  │   │   data_source_columns   │
│────────────────│   │────────────────────────│
│ id (PK)        │◄──│ datasource_id (FK)      │
│ code (UNQ)     │   │ id (PK)                 │
│ name           │   │ column_name             │
│ description    │   │ label                   │
│ ch_table       │   │ description             │
│ base_filter_   │   │ data_type (enum)        │
│   columns JSON │   │ category (enum)         │
│ base_filter_   │   │ is_selectable           │
│   logic        │   │ is_filterable           │
│ institution_id │   │ is_groupable            │
│ is_active      │   │ display_order           │
│ created_at     │   │ created_at              │
└──────┬─────────┘   └────────────────────────┘
       │
       │   ┌─────────────────────┐
       │   │   role_datasources  │  (tabla pivote)
       │   │─────────────────────│
       └───│ datasource_id FK PK │
           │ role_id (FK, PK)    │
           └─────────────────────┘

┌─────────────────────────────────────────────┐
│               saved_queries                  │
│─────────────────────────────────────────────│
│ id (PK)                                      │
│ user_id (FK → users)                         │
│ datasource_id (FK → data_sources)            │
│ institution_id (FK → institutions, nullable) │
│ name                                         │
│ description                                  │
│ selected_columns (JSONB: string[])           │
│ filters (JSONB: FilterObject[])              │
│ group_by (JSONB: string[])                   │
│ aggregations (JSONB: AggregationObject[])    │
│ is_shared                                    │
│ agrupar                                      │
│ created_at                                   │
│ updated_at                                   │
└─────────────────────────────────────────────┘

┌──────────────────────────────────┐
│      user_query_checkpoints      │
│──────────────────────────────────│
│ id (PK)                          │
│ user_id (FK → users)             │
│ module (ej: "beneficiarios")     │
│ scope  (ej: "municipios_actuali")│
│ last_checked_at                  │
│ UNIQUE (user_id, module, scope)  │
└──────────────────────────────────┘
```

---

## Entidades

### `institutions`
Instituciones gubernamentales que usan el sistema.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador único |
| `code` | VARCHAR(50) UNIQUE | Código corto (ej: `FODES`, `MAGA`, `MIDES`) |
| `name` | VARCHAR(200) | Nombre completo |
| `description` | TEXT | Descripción opcional |
| `is_active` | BOOLEAN | Estado activo/inactivo |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Última actualización |

---

### `users`
Usuarios del sistema.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador único |
| `email` | VARCHAR(255) UNIQUE | Correo electrónico |
| `username` | VARCHAR(100) UNIQUE | Nombre de usuario |
| `password_hash` | VARCHAR(255) NULL | Hash bcrypt de la contraseña (NULL si usa Keycloak) |
| `first_name` | VARCHAR(100) | Nombre |
| `last_name` | VARCHAR(100) | Apellido |
| `phone` | VARCHAR(20) | Teléfono (opcional) |
| `role_id` | UUID FK → roles | Rol del usuario |
| `institution_id` | UUID FK → institutions NULL | Institución (opcional) |
| `created_by` | UUID FK → users NULL | Usuario que lo creó |
| `is_active` | BOOLEAN | Estado activo |
| `is_verified` | BOOLEAN | Email verificado |
| `keycloak_id` | VARCHAR(255) UNIQUE NULL | ID en Keycloak (integración SSO futura) |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `last_login` | TIMESTAMPTZ | Último inicio de sesión |

---

### `roles`
Roles del sistema RBAC.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador único |
| `code` | VARCHAR(50) UNIQUE | Código (ej: `ADMIN`, `ANALYST`) |
| `name` | VARCHAR(100) | Nombre descriptivo |
| `description` | TEXT NULL | Descripción |
| `is_system` | BOOLEAN | `true` = rol del sistema (no eliminable) |
| `created_at` | TIMESTAMPTZ | Fecha de creación |

---

### `permissions`
Permisos granulares del sistema.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador único |
| `code` | VARCHAR(100) UNIQUE | Código (ej: `users:read`) |
| `name` | VARCHAR(100) | Nombre legible |
| `description` | TEXT NULL | Descripción |
| `module` | VARCHAR(50) | Módulo al que pertenece |
| `created_at` | TIMESTAMPTZ | Fecha de creación |

---

### `role_permissions` *(tabla pivote)*

| Columna | Tipo |
|---------|------|
| `role_id` | UUID FK → roles (PK) |
| `permission_id` | UUID FK → permissions (PK) |

---

### `user_sessions`
Sesiones activas de los usuarios (tokens JWT registrados).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador |
| `user_id` | UUID FK → users | Usuario propietario |
| `token_jti` | VARCHAR(255) UNIQUE | JTI del token activo |
| `ip_address` | VARCHAR(45) NULL | IP del cliente al hacer login |
| `user_agent` | VARCHAR(500) NULL | User-Agent del cliente |
| `expires_at` | TIMESTAMPTZ | Fecha de expiración del token |
| `revoked_at` | TIMESTAMPTZ NULL | Fecha de revocación (si fue cerrada la sesión) |
| `created_at` | TIMESTAMPTZ | Fecha de creación |

---

### `institution_api_tokens`
Tokens de integración M2M para sistemas externos.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador |
| `institution_id` | UUID FK → institutions | Institución propietaria |
| `name` | VARCHAR(200) | Nombre/propósito del token |
| `token_prefix` | VARCHAR(32) IDX | Prefijo legible (ej: `vtk_abc123`) |
| `token_hash` | VARCHAR(128) | SHA-256 del token completo |
| `is_active` | BOOLEAN | Estado activo |
| `expires_at` | TIMESTAMPTZ NULL | Fecha de expiración (NULL = no expira) |
| `last_used_at` | TIMESTAMPTZ NULL | Último uso registrado |
| `created_at` | TIMESTAMPTZ | Fecha de creación |

---

### `data_sources`
Fuentes de datos ClickHouse configurables.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador |
| `code` | VARCHAR(50) UNIQUE | Código identificador |
| `name` | VARCHAR(200) | Nombre descriptivo |
| `description` | TEXT NULL | Descripción |
| `ch_table` | VARCHAR(200) | Tabla ClickHouse (ej: `rsh.vw_hogares`) |
| `base_filter_columns` | JSONB | Lista de columnas de filtro base (scoping) |
| `base_filter_logic` | VARCHAR(3) | `"OR"` o `"AND"` para combinar filtros base |
| `institution_id` | UUID FK NULL | Institución propietaria (NULL = global) |
| `is_active` | BOOLEAN | Estado activo |

---

### `data_source_columns`
Definición de las columnas de cada datasource.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador |
| `datasource_id` | UUID FK → data_sources | DataSource padre |
| `column_name` | VARCHAR(100) | Nombre exacto en ClickHouse |
| `label` | VARCHAR(200) | Nombre legible para el frontend |
| `description` | TEXT NULL | Descripción de la columna |
| `data_type` | ENUM | `TEXT`, `INTEGER`, `FLOAT`, `BOOLEAN` |
| `category` | ENUM | `DIMENSION`, `MEASURE`, `GEO`, `INTERVENTION` |
| `is_selectable` | BOOLEAN | Puede ser seleccionada en consultas |
| `is_filterable` | BOOLEAN | Puede ser usada como filtro |
| `is_groupable` | BOOLEAN | Puede ser usada en GROUP BY |
| `display_order` | INTEGER | Orden de visualización |

**Categorías de columnas:**
- `DIMENSION` — Atributos descriptivos (clasificaciones, tipos, nombres)
- `MEASURE` — Valores numéricos (IPM, PMT, conteos)
- `GEO` — Datos geográficos (departamento, municipio, lugar poblado)
- `INTERVENTION` — Columnas binarias (0/1) de programas/intervenciones

---

### `role_datasources` *(tabla pivote)*
Asignación de DataSources a roles (para control de acceso en Query Builder).

| Columna | Tipo |
|---------|------|
| `role_id` | UUID FK → roles (PK) |
| `datasource_id` | UUID FK → data_sources (PK) |

---

### `saved_queries`
Consultas del Query Builder guardadas por los usuarios.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador |
| `user_id` | UUID FK → users | Usuario creador |
| `datasource_id` | UUID FK → data_sources | DataSource de la consulta |
| `institution_id` | UUID FK NULL | Institución destino (si es compartida) |
| `name` | VARCHAR(200) | Nombre de la consulta |
| `description` | TEXT NULL | Descripción |
| `selected_columns` | JSONB | `["col1", "col2", ...]` |
| `filters` | JSONB | `[{"column":"...", "operator":"=", "value":"..."}]` |
| `group_by` | JSONB | `["col1", ...]` |
| `aggregations` | JSONB | `[{"function":"COUNT", "column":"*"}]` |
| `is_shared` | BOOLEAN | Si está compartida a la institución |
| `agrupar` | BOOLEAN | Si usa modo agrupado geográfico |
| `created_at` | TIMESTAMPTZ | Fecha de creación |

---

### `user_query_checkpoints`
Registra la última vez que un usuario ejecutó cierto tipo de consulta (para detectar datos nuevos).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UUID PK | Identificador |
| `user_id` | UUID FK → users | Usuario |
| `module` | VARCHAR(100) | Módulo (ej: `"beneficiarios"`) |
| `scope` | VARCHAR(100) | Scope específico (ej: `"municipios_actualizados"`) |
| `last_checked_at` | TIMESTAMPTZ | Última vez que se consultó |
| `UNIQUE` | — | (`user_id`, `module`, `scope`) |

---

### `tickets` *(Legacy)*
Tabla de tickets de soporte.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER PK AUTOINCREMENT | Identificador |
| `title` | VARCHAR | Título |
| `description` | TEXT | Descripción |
| `status` | VARCHAR | Estado del ticket |
| `created_at` | TIMESTAMP | Fecha de creación |

---

## Base de Datos ClickHouse (RSH)

El Registro Social de Hogares vive en ClickHouse. El acceso es de **solo lectura** desde la aplicación.

### Vistas principales consultadas

| Vista | Descripción |
|-------|-------------|
| `rsh.vw_hogares` | Datos generales de hogares (IPM, PMT, NBI, jefatura, área) |
| `rsh.vw_personas` | Personas miembros del hogar (edad, sexo, etnia, educación) |
| `rsh.vw_viviendas` | Características de la vivienda, servicios y bienes |
| `rsh.vw_beneficios_x_hogar` | Hogares con sus intervenciones/programas por institución |

### Columnas clave en `vw_hogares` / `vw_beneficios_x_hogar`

| Columna | Descripción |
|---------|-------------|
| `hogar_id` | ID único del hogar (INTEGER) |
| `ig3_departamento` | Nombre del departamento |
| `ig3_codigo_departamento` | Código del departamento (2 dígitos) |
| `ig4_municipio` | Nombre del municipio |
| `ig4_codigo_municipio` | Código del municipio (4 dígitos) |
| `ig6_lugar_poblado` | Lugar poblado |
| `ig8_area` | `"Urbana"` / `"Rural"` |
| `personas` | Total de personas en el hogar |
| `hombres` / `mujeres` | Conteo por sexo |
| `ipm_gt` | Índice de Pobreza Multidimensional |
| `ipm_gt_clasificacion` | Clasificación IPM (`"Pobre"`, `"No pobre"`, etc.) |
| `pmt` | Proxy Means Test score |
| `nbi` | Necesidades Básicas Insatisfechas score |
| `jefatura_femenina` | `1` si el jefe del hogar es mujer |
| `prog_fodes` | `1` si el hogar está en el universo FODES |
| `prog_maga` | `1` si el hogar está en el universo MAGA |
| `prog_mides` | `1` si el hogar está en el universo MIDES |
| `estufa_mejorada`, `ecofiltro`, `letrina`, etc. | Intervenciones específicas por programa |

---

## JSONB — Estructura de los campos JSON

### `saved_queries.filters`
```json
[
  {
    "column": "ig3_codigo_departamento",
    "operator": "=",
    "value": "01"
  },
  {
    "column": "ipm_gt",
    "operator": ">=",
    "value": 0.4
  }
]
```

### `saved_queries.aggregations`
```json
[
  { "function": "COUNT", "column": "*" },
  { "function": "AVG",   "column": "ipm_gt" },
  { "function": "SUM",   "column": "personas" }
]
```

### `data_sources.base_filter_columns`
```json
["prog_fodes"]
```
Con `base_filter_logic: "OR"`, genera: `WHERE prog_fodes = 1`

Con múltiples columnas y lógica `"OR"`: `WHERE col_a = 1 OR col_b = 1`
