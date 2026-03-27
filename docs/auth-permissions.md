# Autenticación y Autorización

## Descripción General

El sistema implementa dos mecanismos de autenticación y un modelo de autorización basado en roles (RBAC):

1. **JWT Bearer Token** — Para usuarios del sistema (frontend, dashboards)
2. **API Token** — Para integraciones machine-to-machine (M2M)
3. **RBAC** — Control de acceso basado en roles y permisos

---

## Autenticación con JWT

### Flujo de autenticación

```
1. POST /api/v1/auth/login  { email, password }
   ↓
2. Verificar credenciales en PostgreSQL (passlib/bcrypt)
   ↓
3. Crear sesión en tabla user_sessions (access_jti + refresh_jti)
   ↓
4. Retornar { access_token, refresh_token, token_type, expires_in }
   ↓
5. Cliente usa: Authorization: Bearer <access_token>
```

### Estructura del JWT (Access Token)

```json
{
  "sub": "uuid-del-usuario",
  "exp": 1743000000,
  "iat": 1742998200,
  "jti": "uuid-unico-del-token",
  "type": "access",
  "role": "ADMIN"
}
```

| Campo | Descripción |
|-------|-------------|
| `sub` | UUID del usuario |
| `exp` | Timestamp de expiración |
| `jti` | JWT ID único (permite invalidar el token individualmente) |
| `type` | `"access"` o `"refresh"` |
| `role` | Código del rol del usuario |

### Configuración de tiempos

```env
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30  # Access token: 30 minutos
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7     # Refresh token: 7 días
```

### Renovación de tokens

```
POST /api/v1/auth/refresh  { refresh_token }
↓
Verificar que el jti del refresh token existe en user_sessions (no revocado)
↓
Crear nueva sesión (nuevos JTI)
↓
Eliminar la sesión anterior
↓
Retornar nuevos { access_token, refresh_token }
```

### Invalidación de sesiones

- **Logout individual:** `POST /auth/logout` — elimina todas las sesiones del usuario
- **Cambio de contraseña:** `PUT /auth/me/password` — elimina todas las sesiones + fuerza re-login
- **Desactivación de usuario:** `DELETE /users/{id}` — elimina todas las sesiones

### Verificación de token en cada request

La dependencia `get_current_user` se ejecuta en cada endpoint protegido:

```python
# Flujo simplificado de get_current_user
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(...)):
    payload = decode_token(token)          # Verificar firma JWT
    user_id = payload.get("sub")
    jti = payload.get("jti")
    
    # Verificar que la sesión existe en BD (no fue revocada)
    session = db.query(UserSession).filter(
        UserSession.access_jti == jti,
        UserSession.user_id == user_id,
        UserSession.is_active == True,
    ).first()
    
    if not session:
        raise HTTPException(401, "Sesión revocada")
    
    return db.query(User).filter(User.id == user_id).first()
```

---

## Autenticación con API Token (M2M)

Para integraciones de sistemas externos que no tienen sesión de usuario.

### Generación de tokens

```
POST /api/v1/institutions/{id}/api-tokens
↓
secrets.token_urlsafe(32)  →  token en texto plano (retornado UNA VEZ)
↓
hashlib.sha256(token)      →  almacenado en BD
↓
Prefijo legible: "vtk_" + primeros 8 chars del hash en hex
```

### Uso del token

```http
GET /api/v1/integration/consulta/
Authorization: Bearer vtk_abc12345_<resto_del_token>
```

### Verificación

La dependencia `get_current_api_institution` extrae el token del header, calcula su SHA-256, busca en `institution_api_tokens` y verifica:
- Hash coincide
- `is_active = true`
- `expires_at IS NULL OR expires_at > now()`

Retorna la `Institution` asociada al token.

---

## Sistema RBAC

### Modelo de datos

```
Institution (1) ──── (N) User (N) ──── (1) Role (N) ──── (N) Permission
                                              │
                                              └── (N) RoleDataSource (N) ──── DataSource
```

- Un usuario pertenece a exactamente **una institución** (opcional) y **un rol**
- Un rol tiene múltiples **permisos**
- Un rol también puede tener acceso a múltiples **DataSources** (Query Builder)

### Roles predefinidos del sistema

Los roles del sistema (`is_system = true`) no pueden eliminarse.

#### `ADMIN` — Administrador
Acceso total al sistema.

| Permiso | Descripción |
|---------|-------------|
| `users:read` | Ver usuarios |
| `users:create` | Crear usuarios |
| `users:update` | Actualizar usuarios |
| `users:delete` | Eliminar/desactivar usuarios |
| `roles:manage` | Gestionar roles y permisos |
| `beneficiaries:read` | Ver datos RSH |
| `beneficiaries:export` | Exportar datos RSH |
| `databases:read` | Leer datasources |
| `databases:manage` | Gestionar datasources |
| `datasources:manage` | Configurar datasources |
| `reports:read` | Ver reportes |
| `reports:advanced` | Reportes avanzados |
| `reports:create` | Crear/guardar consultas |
| `system:config` | Configuración del sistema (Super Admin) |
| `system:monitor` | Monitoreo del sistema |
| `system:audit` | Auditoría del sistema |

#### `ANALYST` — Analista
Enfocado en análisis de datos.

| Permiso |
|---------|
| `beneficiaries:read` |
| `beneficiaries:export` |
| `databases:read` |
| `reports:read` |
| `reports:advanced` |
| `reports:create` |

#### `INSTITUTIONAL` — Usuario Institucional
Acceso básico de solo lectura.

| Permiso |
|---------|
| `beneficiaries:read` |
| `beneficiaries:export` |
| `reports:read` |

### Dependencias de autorización

#### `RequirePermission(PermissionCode.XXX)`
Verifica que el usuario tenga exactamente ese permiso. Si no, retorna `403 Forbidden`.

```python
@router.get("/users/")
def list_users(
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_READ))
):
    ...
```

#### `RequireAnyPermission([PermissionCode.A, PermissionCode.B])`
Permite el acceso si el usuario tiene **al menos uno** de los permisos listados.

```python
# El Query Builder acepta databases:read O reports:read
_query_permission = RequireAnyPermission([
    PermissionCode.DATABASES_READ,
    PermissionCode.REPORTS_READ,
])
```

#### `get_current_active_user`
Solo verifica que el usuario esté autenticado y activo (`is_active = true`), sin requerir permisos específicos.

#### `get_current_user`
Lo mismo que `get_current_active_user` pero sin verificar el estado activo (para casos donde un usuario desactivado aún necesita ciertos endpoints).

### Verificación de permisos a nivel de objeto

Además de los permisos de rol, existe scoping a nivel de datos:

#### Scoping institucional en DataSources
```python
def _get_user_datasource(ds_id, user, db):
    # Admin → acceso total
    # Usuario con institución → puede acceder a datasources de su institución
    # Usuario sin institución → solo datasources asignados a su rol (RoleDataSource)
```

#### Scoping institucional en Consultas Guardadas
```python
def _can_access_saved_query(sq, user):
    if _is_admin(user): return True
    if sq.user_id == user.id: return True           # Es el creador
    if sq.is_shared and sq.institution_id == user.institution_id: return True  # Compartida a su institución
    return False
```

---

## Códigos de Permiso — Referencia Completa

```python
class PermissionCode(str, Enum):
    # Gestión de usuarios
    USERS_READ    = "users:read"
    USERS_CREATE  = "users:create"
    USERS_UPDATE  = "users:update"
    USERS_DELETE  = "users:delete"

    # Gestión de roles
    ROLES_MANAGE  = "roles:manage"

    # Datos RSH
    BENEFICIARIES_READ   = "beneficiaries:read"
    BENEFICIARIES_EXPORT = "beneficiaries:export"

    # Bases de datos y datasources
    DATABASES_READ    = "databases:read"
    DATABASES_MANAGE  = "databases:manage"
    DATASOURCES_MANAGE = "datasources:manage"

    # Reportes y consultas
    REPORTS_READ     = "reports:read"
    REPORTS_ADVANCED = "reports:advanced"
    REPORTS_CREATE   = "reports:create"

    # Sistema
    SYSTEM_CONFIG  = "system:config"   # Identifica al Super Admin
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_AUDIT   = "system:audit"
```

### Mapa de permisos por endpoint

| Grupo | Permiso requerido |
|-------|------------------|
| `GET /users/`, `GET /users/{id}` | `users:read` |
| `POST /users/` | `users:create` |
| `PUT /users/{id}`, `DELETE /users/{id}/sessions` | `users:update` |
| `DELETE /users/{id}` | `users:delete` |
| `*/roles/*` | `roles:manage` |
| `POST /institutions/` | `users:create` |
| `PUT /institutions/{id}` | `users:update` |
| `DELETE /institutions/{id}` | `users:delete` |
| `GET /institutions/{id}/api-tokens` | `users:read` |
| `POST /institutions/{id}/api-tokens` | `users:update` |
| `DELETE /institutions/{id}/api-tokens/{id}` | `users:delete` |
| `GET /beneficiarios/*` | `beneficiaries:read` |
| `GET /beneficiarios/export/*` | `beneficiaries:export` |
| `GET /queries/*`, `POST /queries/execute` | `databases:read` OR `reports:read` |
| `POST /queries/saved`, `PUT/DELETE /queries/saved/{id}` | `reports:create` |
| `GET /datasources/*` | Usuario autenticado (scoping por institución/rol) |
| `POST/PUT/DELETE /datasources/*` | `datasources:manage` |
| `GET /dashboard/` | Usuario autenticado (respuesta según rol) |

---

## Seguridad adicional

### Protección contra contraseñas comprometidas
Las contraseñas se almacenan con **bcrypt** (factor de trabajo 12 rounds por defecto de passlib). No se almacenan en texto plano en ningún punto.

### Cifrado de respuestas (AES-256-GCM)
Cuando `RESPONSE_ENCRYPTION_ENABLED=true`, todas las respuestas JSON se cifran con AES-256-GCM. El cliente debe conocer la clave para descifrar. Se incluye AAD con `METHOD:PATH` para prevenir que un ciphertext de un endpoint sea reutilizado en otro.

### Rate limiting
No implementado en la capa de aplicación. Se recomienda configurar rate limiting en Traefik para los endpoints de autenticación (`/auth/login`, `/auth/refresh`).

### CORS
Configurado en `main.py` con lista explícita de orígenes permitidos. En producción, ajustar a los dominios exactos del frontend.
