# Referencia de Endpoints

Todos los endpoints están bajo el prefijo `/api/v1`. Las respuestas JSON están envueltas en el sobre estándar:

```json
{
  "result": true,
  "message": "OK",
  "data": { ... }
}
```

Los errores siguen la misma estructura con `result: false` y el detalle en `data.detail`.

---

## Autenticación — `/api/v1/auth`

### `POST /auth/login`
Autentica al usuario y genera un par de tokens JWT.

**Body:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña123"
}
```

**Respuesta exitosa (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errores:** `401` — Credenciales inválidas.

---

### `POST /auth/refresh`
Renueva el par de tokens usando el refresh token activo.

**Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Respuesta (200):** Mismo schema que `/login`.

**Errores:** `401` — Token inválido o expirado.

---

### `POST /auth/logout`
Revoca todas las sesiones activas del usuario. Requiere Bearer token.

**Respuesta (200):**
```json
{ "message": "Sesión cerrada. 2 sesiones revocadas." }
```

---

### `GET /auth/me`
Retorna el perfil del usuario autenticado.

**Respuesta (200):**
```json
{
  "id": "uuid",
  "email": "usuario@ejemplo.com",
  "username": "jdoe",
  "first_name": "Juan",
  "last_name": "Doe",
  "role": { "code": "ANALYST", "name": "Analista" },
  "permissions": ["beneficiaries:read", "reports:read"],
  "institution": { "id": "uuid", "name": "FODES" }
}
```

---

### `PUT /auth/me`
Actualiza datos del perfil del usuario autenticado (nombre, teléfono, etc.).

**Body:** Campos opcionales `first_name`, `last_name`, `phone`.

---

### `PUT /auth/me/password`
Cambia la contraseña. Invalida todas las sesiones activas.

**Body:**
```json
{
  "current_password": "anterior",
  "new_password": "nueva_contraseña_segura"
}
```

---

## Usuarios — `/api/v1/users`

> Todos requieren el header `Authorization: Bearer <token>` con los permisos indicados.

### `GET /users/`
Lista paginada de usuarios con filtros opcionales.

**Permisos:** `users:read`

**Query params:**
| Param | Tipo | Descripción |
|-------|------|-------------|
| `page` | int | Número de página (default: 1) |
| `size` | int | Tamaño de página (default: 20) |
| `email` | string | Filtrar por email (substring) |
| `username` | string | Filtrar por username |
| `is_active` | bool | Filtrar por estado activo/inactivo |
| `institution_id` | UUID | Filtrar por institución |
| `role_id` | UUID | Filtrar por rol |

**Respuesta (200):** `Page<UserOut>` con paginación.

---

### `POST /users/`
Crea un nuevo usuario.

**Permisos:** `users:create`

**Body:**
```json
{
  "email": "nuevo@ejemplo.com",
  "username": "nuevo_usuario",
  "password": "contraseña_segura",
  "first_name": "Nombre",
  "last_name": "Apellido",
  "role_id": "uuid-del-rol",
  "institution_id": "uuid-de-la-institucion"
}
```

**Errores:** `400` — Email o username ya existe.

---

### `GET /users/{user_id}`
Obtiene un usuario por UUID. **Permisos:** `users:read`

---

### `PUT /users/{user_id}`
Actualiza datos de un usuario. **Permisos:** `users:update`

---

### `DELETE /users/{user_id}`
Soft-delete: desactiva el usuario y revoca sus sesiones. **Permisos:** `users:delete`

No permite eliminar la propia cuenta. Retorna `400` si se intenta.

---

### `PUT /users/{user_id}/activate`
Reactiva un usuario desactivado. **Permisos:** `users:update`

---

### `DELETE /users/{user_id}/sessions`
Revoca todas las sesiones activas de un usuario. **Permisos:** `users:update`

---

## Roles y Permisos — `/api/v1/roles`

> Todos requieren **`roles:manage`**.

### `GET /roles/`
Lista todos los roles del sistema.

**Respuesta:**
```json
[
  {
    "id": "uuid",
    "code": "ADMIN",
    "name": "Administrador",
    "is_system": true,
    "permissions": [
      { "id": "uuid", "code": "users:read", "name": "Ver usuarios" }
    ]
  }
]
```

---

### `POST /roles/`
Crea un nuevo rol. **Body:** `{ "code": "NUEVO_ROL", "name": "...", "description": "..." }`

**Errores:** `400` — Código de rol ya existe.

---

### `GET /roles/permissions`
Lista todos los permisos disponibles en el sistema.

---

### `GET /roles/{role_id}`
Obtiene un rol con sus permisos.

---

### `PUT /roles/{role_id}`
Actualiza nombre o código de un rol.

---

### `DELETE /roles/{role_id}`
Elimina un rol. Solo funciona con roles no del sistema (`is_system = false`).

**Errores:** `400` — No se pueden eliminar roles del sistema.

---

### `PUT /roles/{role_id}/permissions`
Reemplaza el set de permisos de un rol.

**Body:**
```json
{ "permission_ids": ["uuid1", "uuid2", "uuid3"] }
```

---

### `GET /roles/{role_id}/datasources`
Lista los DataSources asignados a un rol.

---

### `PUT /roles/{role_id}/datasources`
Reemplaza los DataSources asignados a un rol.

**Body:**
```json
{ "datasource_ids": ["uuid1", "uuid2"] }
```

---

## Instituciones — `/api/v1/institutions`

### `GET /institutions/`
Lista instituciones. Los admins ven todas; usuarios regulares solo ven su propia institución.

**Permisos:** Usuario autenticado.

**Query params:** `include_inactive=true` (solo admins).

---

### `POST /institutions/`
Crea una nueva institución. **Permisos:** `users:create`

**Body:**
```json
{
  "code": "NUEVA_INST",
  "name": "Nombre Institución",
  "description": "Descripción opcional"
}
```

---

### `GET /institutions/{institution_id}`
Obtiene una institución por UUID. **Permisos:** Usuario autenticado.

---

### `PUT /institutions/{institution_id}`
Actualiza una institución. **Permisos:** `users:update`

---

### `DELETE /institutions/{institution_id}`
Soft-delete de institución. **Permisos:** `users:delete`

---

### `GET /institutions/{institution_id}/api-tokens`
Lista los API tokens de integración de la institución.

**Permisos:** `users:read`

**Respuesta:**
```json
[
  {
    "id": "uuid",
    "name": "Token para sistema X",
    "token_prefix": "vtk_abc12345",
    "is_active": true,
    "expires_at": "2027-01-01T00:00:00Z",
    "last_used_at": null
  }
]
```

---

### `POST /institutions/{institution_id}/api-tokens`
Genera un nuevo API token. El token en texto plano solo se retorna **una vez**.

**Permisos:** `users:update`

**Body:**
```json
{
  "name": "Token para sistema X",
  "expires_in_days": 365
}
```

**Respuesta (201):**
```json
{
  "id": "uuid",
  "name": "Token para sistema X",
  "token_prefix": "vtk_abc12345",
  "token": "vtk_abc12345_<resto_del_token_completo>",
  "is_active": true,
  "expires_at": "2027-03-25T00:00:00Z"
}
```

> ⚠️ Guarda el campo `token` inmediatamente. No puede recuperarse posteriormente.

---

### `DELETE /institutions/{institution_id}/api-tokens/{token_id}`
Revoca un API token. **Permisos:** `users:delete`

---

## Beneficiarios RSH — `/api/v1/beneficiarios`

> Consultan ClickHouse. Requieren `beneficiaries:read` o `beneficiaries:export`.

### `GET /beneficiarios/catalogos`
Catálogos para poblar filtros del frontend.

**Respuesta:**
```json
{
  "departamentos": [{ "code": "01", "name": "Guatemala" }],
  "clasificaciones_ipm": ["Pobre", "No pobre"],
  "clasificaciones_pmt": [...],
  "clasificaciones_nbi": [...],
  "areas": ["Urbana", "Rural"],
  "niveles_inseguridad": [...],
  "comunidades_linguisticas": [...],
  "pueblos": [...],
  "fuentes_agua": [...],
  "tipos_sanitario": [...],
  "tipos_alumbrado": [...],
  "combustibles_cocina": [...]
}
```

---

### `GET /beneficiarios/catalogos/municipios?departamento_codigo=01`
Municipios del departamento indicado (cascada).

---

### `GET /beneficiarios/catalogos/lugares-poblados?municipio_codigo=0101`
Lugares poblados del municipio indicado (cascada).

---

### `GET /beneficiarios/municipios/actualizados`
Municipios con datos nuevos desde la última consulta del usuario (sistema de checkpoints). Actualiza el checkpoint automáticamente.

**Respuesta:**
```json
{
  "last_checked_at": "2026-03-20T10:00:00Z",
  "checked_at": "2026-03-25T12:00:00Z",
  "total": 3,
  "items": [
    {
      "code": "0105",
      "name": "Mixco",
      "departamento": "Guatemala",
      "ultima_actualizacion": "2026-03-22T00:00:00Z"
    }
  ]
}
```

---

### `GET /beneficiarios/dashboard`
Estadísticas globales: total hogares, departamentos, distribución geográfica, inseguridad alimentaria.

---

### `GET /beneficiarios/stats`
Estadísticas agregadas aplicando los mismos filtros que el listado.

**Filtros disponibles** (query params):
| Param | Descripción |
|-------|-------------|
| `departamento_codigo` | Código de departamento |
| `municipio_codigo` | Código de municipio |
| `lugar_poblado_codigo` | Código de lugar poblado |
| `area` | `"Urbana"` / `"Rural"` |
| `ipm_gt_clasificacion` | Clasificación IPM |
| `pmt_clasificacion` | Clasificación PMT |
| `nbi_clasificacion` | Clasificación NBI |
| `nivel_inseguridad_alimentaria` | Nivel de inseguridad |
| `comunidad_linguistica` | Comunidad lingüística |
| `pueblo` | Pueblo (Maya, Ladino, etc.) |
| `jefatura_femenina` | `true`/`false` |

---

### `GET /beneficiarios/listado/municipio-comunidad`
Lista beneficiarios agrupados por municipio → comunidad. Diseñado para impresión/PDF.

---

### `GET /beneficiarios/export/excel`
Exporta beneficiarios filtrados a `.xlsx` (hasta 10,000 registros). Si supera el umbral genera `.zip`.

**Permisos:** `beneficiaries:export`

---

### `GET /beneficiarios/export/csv`
Exporta a CSV. **Permisos:** `beneficiaries:export`

---

### `GET /beneficiarios/export/pdf`
Exporta a PDF (máx. 5,000 registros). **Permisos:** `beneficiaries:export`

---

### `GET /beneficiarios/`
Lista paginada de hogares.

**Query params:** `offset` (default 0), `limit` (default 20, máx 100) + filtros de stats.

---

### `GET /beneficiarios/{hogar_id}`
Detalle completo del hogar.

---

### `GET /beneficiarios/{hogar_id}/personas`
Personas del hogar (id numérico del hogar).

---

### `GET /beneficiarios/{hogar_id}/vivienda`
Vivienda, servicios básicos, bienes y seguridad alimentaria del hogar.

---

## Consulta Institucional — `/api/v1/consulta`

> Vista de datos scoped al universo institucional del usuario. Requiere usuario autenticado con institución asignada.

### `GET /consulta/preset`
Configuración del preset de la institución del usuario (columnas, tabla, filtros, etiquetas).

---

### `GET /consulta/dashboard`
Dashboard institucional: hogares, personas, departamentos cubiertos y conteo por tipo de intervención.

---

### `GET /consulta/catalogos`
Catálogo de departamentos filtrado al universo de la institución.

---

### `GET /consulta/`
Lista paginada de hogares del universo institucional. Acepta los mismos filtros que `/beneficiarios/`.

---

### `GET /consulta/{hogar_id}`
Detalle del hogar verificando que pertenezca al universo de la institución.

---

## Integración M2M — `/api/v1/integration/consulta`

> Autenticación exclusiva mediante **API Token** (`Authorization: Bearer <api_token>`). Para sistemas externos.

### `GET /integration/consulta/preset`
Preset institucional de la institución dueña del token.

---

### `GET /integration/consulta/`
Lista paginada del universo institucional. Mismos filtros que `/consulta/`. Máx. 100 registros por página.

---

## DataSources — `/api/v1/datasources`

> Gestión administrativa de fuentes de datos ClickHouse.

### `GET /datasources/`
Lista datasources accesibles. Admins ven todos; usuarios institucionales ven los de su institución o asignados a su rol.

---

### `POST /datasources/`
Crea un datasource y auto-descubre sus columnas desde ClickHouse (`DESCRIBE TABLE`).

**Permisos:** `datasources:manage`

**Body:**
```json
{
  "code": "RSH_HOGARES",
  "name": "Hogares RSH",
  "ch_table": "rsh.vw_hogares",
  "base_filter_columns": [],
  "base_filter_logic": "OR",
  "institution_id": null,
  "description": "Vista principal de hogares RSH"
}
```

---

### `GET /datasources/ch-tables`
Lista las tablas disponibles en ClickHouse (esquema `rsh`). **Permisos:** `datasources:manage`

---

### `GET /datasources/ch-columns?table=rsh.vw_hogares`
Lista columnas de una tabla ClickHouse específica con sus tipos.

---

### `POST /datasources/{ds_id}/auto-discover`
Sincroniza columnas del datasource con ClickHouse. Solo agrega columnas nuevas, no duplica.

---

### `GET /datasources/{ds_id}`
Obtiene datasource con todas sus columnas definidas.

---

### `PUT /datasources/{ds_id}`
Actualiza metadatos del datasource. **Permisos:** `datasources:manage`

---

### `DELETE /datasources/{ds_id}`
Desactiva (soft-delete) el datasource. **Permisos:** `datasources:manage`

---

### `POST /datasources/{ds_id}/columns`
Agrega manualmente una columna al datasource.

**Body:**
```json
{
  "column_name": "ig3_departamento",
  "label": "Departamento",
  "data_type": "TEXT",
  "category": "GEO",
  "is_selectable": true,
  "is_filterable": true,
  "is_groupable": true
}
```

**Tipos de dato:** `TEXT`, `INTEGER`, `FLOAT`

**Categorías:** `DIMENSION`, `MEASURE`, `GEO`, `INTERVENTION`

---

### `PUT /datasources/{ds_id}/columns/{col_id}`
Actualiza metadatos de una columna (label, descripción, flags de selección/filtrado/agrupación).

---

### `DELETE /datasources/{ds_id}/columns/{col_id}`
Elimina una columna del datasource.

---

## Query Builder — `/api/v1/queries`

### `GET /queries/datasources`
Lista datasources accesibles con sus columnas disponibles.

**Permisos:** `databases:read` o `reports:read`

---

### `POST /queries/execute`
Ejecuta una consulta ad-hoc.

**Permisos:** `databases:read` o `reports:read`

**Body:**
```json
{
  "datasource_id": "uuid",
  "columns": ["ig3_departamento", "ig4_municipio", "ipm_gt"],
  "filters": [
    {
      "column": "ig3_codigo_departamento",
      "operator": "=",
      "value": "01"
    }
  ],
  "group_by": ["ig3_departamento"],
  "aggregations": [
    { "function": "COUNT", "column": "*" },
    { "function": "AVG", "column": "ipm_gt" }
  ],
  "agrupar": true,
  "offset": 0,
  "limit": 100
}
```

**Operadores de filtro disponibles:** `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `in`, `between`

**Funciones de agregación:** `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`

**Respuesta:**
```json
{
  "items": [...],
  "total": 150,
  "offset": 0,
  "limit": 100,
  "columns_meta": [
    { "column_name": "ig3_departamento", "label": "Departamento", "data_type": "TEXT" }
  ]
}
```

---

### `POST /queries/execute/export?formato=csv|excel|pdf`
Ejecuta y exporta en el formato especificado. Límites: CSV ilimitado, Excel 1M filas, PDF 50K filas.

---

### `POST /queries/execute/export/csv`
Exporta a CSV streaming.

---

### `POST /queries/execute/export/excel`
Exporta a Excel (ZIP con múltiples hojas si supera umbral).

---

### `POST /queries/execute/export/pdf`
Exporta a PDF (ZIP).

---

### `POST /queries/saved`
Guarda una consulta con nombre. Soporta compartir a nivel institucional.

**Permisos:** `reports:create`

**Body adicional respecto a `/execute`:**
```json
{
  "name": "Hogares pobres en Guatemala",
  "description": "...",
  "is_shared": true,
  "institution_id": "uuid-de-la-institucion"
}
```

---

### `GET /queries/saved`
Lista consultas guardadas visibles al usuario:
- Admin: todas
- Admin institucional: propias + compartidas de su institución
- Usuario: solo las propias

---

### `GET /queries/saved/{query_id}`
Detalle completo de una consulta guardada.

---

### `PUT /queries/saved/{query_id}`
Actualiza una consulta. Solo el creador, admin o admin institucional (dentro de su institución).

---

### `DELETE /queries/saved/{query_id}`
Elimina una consulta guardada.

---

### `POST /queries/saved/{query_id}/execute`
Ejecuta una consulta guardada con paginación.

**Query params:** `offset`, `limit`

---

### `GET /queries/saved/{query_id}/export/csv`
Exporta una consulta guardada a CSV.

---

### `GET /queries/saved/{query_id}/export/excel`
Exporta a Excel (ZIP).

---

### `GET /queries/saved/{query_id}/export/pdf`
Exporta a PDF (ZIP).

---

## Dashboard — `/api/v1/dashboard`

### `GET /dashboard/`
Dashboard unificado que retorna datos según el rol del usuario.

**Query params:**
| Param | Descripción |
|-------|-------------|
| `departamento` | Código de departamento para filtrar (solo dashboard institucional) |

**Comportamiento:**
- **Super Admin** (`system:config`): estadísticas globales del sistema (usuarios, instituciones, consultas guardadas) + totales RSH + distribuciones de pobreza IPM/PMT/NBI + comparativas por institución.
- **Usuario institucional**: estadísticas scoped a su institución (hogares, personas, municipios, distribución de pobreza, intervenciones).

---

## Tickets — `/api/v1/tickets` *(Legacy)*

> Sin autenticación requerida.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/tickets/` | Crea un ticket |
| `GET` | `/tickets/` | Lista paginada con filtros |
| `GET` | `/tickets/{ticket_id}` | Obtiene un ticket por ID |
| `PUT` | `/tickets/{ticket_id}` | Actualiza un ticket |

---

## Empleados — `/api/v1/empleados` *(Legacy)*

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/empleados/{unidad_id}` | Lista empleados de una unidad (paginado, consulta SQL Server/SQLite) |

---

## Códigos de error estándar

| Código | Descripción |
|--------|-------------|
| `400` | Datos de entrada inválidos o regla de negocio violada |
| `401` | No autenticado o token inválido/expirado |
| `403` | Autenticado pero sin permisos para la operación |
| `404` | Recurso no encontrado |
| `409` | Conflicto (ej: código duplicado) |
| `422` | Error de validación de schema Pydantic |
| `500` | Error interno del servidor |
