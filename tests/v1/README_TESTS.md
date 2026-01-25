# Tests de Usuario y Autenticación

Este directorio contiene tests completos para los módulos de usuarios y autenticación del backend FastAPI.

## Estructura de Tests

### `test_users.py`
Tests completos para el módulo de usuarios:

**Servicios testeados:**
- `get_user_by_id()` - Obtener usuario por UUID
- `get_user_by_email()` - Búsqueda por email
- `get_user_by_username()` - Búsqueda por username
- `create_user()` - Crear usuario con/sin password
- `update_user()` - Actualizar datos de usuario
- `update_user_password()` - Cambiar contraseña
- `delete_user()` - Soft/hard delete
- `get_all_users()` - Listar con paginación y filtros
- `activate_user()` - Reactivar usuario
- `verify_user()` - Marcar como verificado

**Endpoints testeados:**
- `GET /users/` - Listar usuarios paginados
- `POST /users/` - Crear usuario
- `GET /users/{user_id}` - Obtener usuario
- `PUT /users/{user_id}` - Actualizar usuario
- `DELETE /users/{user_id}` - Desactivar usuario
- `PUT /users/{user_id}/activate` - Activar usuario
- `DELETE /users/{user_id}/sessions` - Revocar sesiones

**Casos de prueba:**
- CRUD completo de usuarios
- Validación de email/username únicos
- Filtros y paginación (role, institution, active, verified, search, date range)
- Soft delete vs hard delete
- Activación/verificación de usuarios
- Manejo de errores (404, 400)
- Edge cases y validación de datos

### `test_auth.py`
Tests completos para el módulo de autenticación:

**Servicios testeados:**
- `authenticate_user()` - Validar credenciales
- `create_user_session()` - Generar JWT tokens
- `refresh_user_tokens()` - Renovar tokens
- `revoke_session()` - Revocar sesión por JTI
- `revoke_all_user_sessions()` - Cerrar todas las sesiones
- `get_current_user_info()` - Info del usuario autenticado

**Endpoints testeados:**
- `POST /auth/login` - Autenticación
- `POST /auth/refresh` - Renovar tokens
- `POST /auth/logout` - Cerrar sesión
- `GET /auth/me` - Perfil actual
- `PUT /auth/me` - Actualizar perfil
- `PUT /auth/me/password` - Cambiar contraseña

**Casos de prueba:**
- Login exitoso y fallido
- Autenticación con usuarios inactivos
- Autenticación con usuarios sin password (Keycloak)
- Refresh token válido e inválido
- Tokens revocados/expirados
- Logout y revocación de sesiones
- Cambio de contraseña
- Perfil del usuario autenticado
- Gestión de sesiones concurrentes
- Validación de seguridad

## Fixtures Disponibles

### Fixtures de Base de Datos
- `db_session` - Sesión de base de datos para operaciones directas
- `client` - Cliente de prueba FastAPI
- `prepare_db` - Auto-fixture que crea/elimina el esquema de BD

### Fixtures de Datos de Prueba
- `test_permissions` - Permisos de prueba (users:read, users:create, etc.)
- `test_roles` - Roles de prueba (ADMIN, ANALYST)
- `test_institution` - Institución de prueba
- `test_admin_user` - Usuario administrador activo y verificado
- `test_regular_user` - Usuario analista activo y verificado
- `test_inactive_user` - Usuario inactivo y no verificado

### Fixtures de Autenticación
- `mock_current_user` - Usuario mock para override de dependencias
- `authenticated_admin_client` - Cliente con admin autenticado
- `mock_permission_dependency` - Mock para RequirePermission

## Ejecutar Tests

### Ejecutar todos los tests de usuarios
```bash
cd /home/lralda/pnud/ventana-magica/backend
pytest tests/v1/test_users.py -v
```

### Ejecutar todos los tests de autenticación
```bash
pytest tests/v1/test_auth.py -v
```

### Ejecutar ambos módulos
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py -v
```

### Ejecutar tests específicos
```bash
# Solo tests de servicios de usuario
pytest tests/v1/test_users.py::TestUserServices -v

# Solo tests de rutas de autenticación
pytest tests/v1/test_auth.py::TestAuthRoutes -v

# Test específico
pytest tests/v1/test_users.py::TestUserServices::test_create_user_with_password -v
```

### Con cobertura de código
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py --cov=api/v1/services/user --cov=api/v1/services/auth --cov=api/v1/routes/user_routes --cov=api/v1/routes/auth_routes --cov-report=html
```

### Opciones útiles
```bash
# Mostrar output detallado
pytest tests/v1/test_users.py -v -s

# Mostrar solo failures
pytest tests/v1/test_users.py --tb=short

# Ejecutar tests en paralelo (requiere pytest-xdist)
pytest tests/v1/test_users.py -n auto

# Ejecutar solo tests que fallaron anteriormente
pytest tests/v1/test_users.py --lf

# Detener en el primer fallo
pytest tests/v1/test_users.py -x
```

## Estructura de Tests

Cada archivo de test sigue esta estructura:

1. **Service Layer Tests** - Tests unitarios de funciones de servicio
   - Pruebas de lógica de negocio
   - Validación de datos
   - Casos edge

2. **Route/API Tests** - Tests de integración de endpoints
   - Validación de respuestas HTTP
   - Validación de schemas
   - Manejo de errores

3. **Edge Cases Tests** - Tests de casos especiales
   - Validaciones de seguridad
   - Condiciones límite
   - Comportamiento inesperado

## Notas Importantes

### Mocking de Permisos
Los tests de rutas usan `@patch` para mockear `RequirePermission` ya que:
- Los tests unitarios deben probar lógica, no autenticación
- Permite tests independientes sin setup complejo de JWT
- Facilita pruebas con diferentes niveles de permisos

### Base de Datos de Test
- Se usa SQLite en memoria (`test.db`)
- Cada test tiene su propia transacción (aislamiento)
- El esquema se crea/elimina automáticamente por test

### Passwords de Test
Todos los usuarios de test tienen passwords predecibles:
- Admin: `Admin123!`
- Regular User: `User123!`
- Inactive User: `Inactive123!`

## Troubleshooting

### Error: "No module named 'api.v1.models.permission'"
Asegúrate de que el modelo Permission existe en `api/v1/models/permission.py`

### Error: "fixture not found"
Verifica que `conftest.py` está en el mismo directorio que los tests

### Error: "Table already exists"
El fixture `prepare_db` debería limpiar la BD automáticamente. Si persiste:
```bash
rm test.db
```

### Tests lentos
Considera usar pytest-xdist para ejecución paralela:
```bash
pip install pytest-xdist
pytest tests/v1/ -n auto
```

## Métricas de Cobertura Esperadas

Estos tests deberían proporcionar:
- **Servicios de Usuario**: >95% de cobertura
- **Servicios de Auth**: >95% de cobertura
- **Rutas de Usuario**: >90% de cobertura
- **Rutas de Auth**: >90% de cobertura

## Agregar Nuevos Tests

Para agregar nuevos tests:

1. Agregar el test en la clase apropiada
2. Usar fixtures existentes cuando sea posible
3. Seguir el patrón AAA (Arrange, Act, Assert)
4. Agregar docstring descriptivo
5. Considerar casos edge y manejo de errores

Ejemplo:
```python
def test_new_feature(self, db_session, test_admin_user):
    """Test description of what is being tested"""
    # Arrange
    test_data = {...}

    # Act
    result = some_function(db_session, test_data)

    # Assert
    assert result.field == expected_value
```

## Integración Continua

Estos tests están diseñados para ejecutarse en CI/CD pipelines:

```yaml
# .github/workflows/tests.yml
- name: Run tests
  run: |
    pytest tests/v1/test_users.py tests/v1/test_auth.py -v --cov --cov-report=xml
```

## Contacto

Para preguntas sobre los tests, contacta al equipo de desarrollo.
