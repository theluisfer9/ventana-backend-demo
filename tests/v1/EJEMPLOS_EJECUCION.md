# Ejemplos de Ejecución de Tests

Este documento contiene ejemplos prácticos de cómo ejecutar los tests de usuarios y autenticación.

## Setup Inicial

Antes de ejecutar los tests, asegúrate de:

1. Estar en el directorio backend:
```bash
cd /home/lralda/pnud/ventana-magica/backend
```

2. Tener las dependencias instaladas:
```bash
pip install pytest pytest-cov
```

3. Verificar que pytest funciona:
```bash
pytest --version
```

## Ejecución Básica

### Ejecutar TODOS los tests de usuarios y autenticación
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py -v
```

Salida esperada:
```
tests/v1/test_users.py::TestUserServices::test_get_user_by_id_success PASSED
tests/v1/test_users.py::TestUserServices::test_get_user_by_email_success PASSED
...
============= 77 passed in 5.23s =============
```

### Usar el script de ejecución
```bash
./run_user_tests.sh
```

## Ejecutar Tests Específicos

### Solo tests de usuarios
```bash
pytest tests/v1/test_users.py -v
```

### Solo tests de autenticación
```bash
pytest tests/v1/test_auth.py -v
```

### Solo una clase de tests
```bash
# Solo servicios de usuario
pytest tests/v1/test_users.py::TestUserServices -v

# Solo rutas de usuario
pytest tests/v1/test_users.py::TestUserRoutes -v

# Solo servicios de auth
pytest tests/v1/test_auth.py::TestAuthServices -v
```

### Solo un test específico
```bash
# Test específico por nombre completo
pytest tests/v1/test_users.py::TestUserServices::test_create_user_with_password -v

# Test de autenticación específico
pytest tests/v1/test_auth.py::TestAuthRoutes::test_login_success -v
```

### Tests que contienen una palabra clave
```bash
# Todos los tests que contienen "password"
pytest tests/v1/ -k "password" -v

# Todos los tests que contienen "delete"
pytest tests/v1/ -k "delete" -v

# Todos los tests que contienen "filter"
pytest tests/v1/ -k "filter" -v
```

## Opciones de Output

### Modo verboso (detallado)
```bash
pytest tests/v1/test_users.py -v
```

### Modo silencioso (solo resumen)
```bash
pytest tests/v1/test_users.py -q
```

### Mostrar output de prints
```bash
pytest tests/v1/test_users.py -v -s
```

### Mostrar traceback completo en errores
```bash
pytest tests/v1/test_users.py -v --tb=long
```

### Mostrar traceback corto
```bash
pytest tests/v1/test_users.py -v --tb=short
```

### Sin traceback
```bash
pytest tests/v1/test_users.py -v --tb=no
```

## Reporte de Cobertura

### Cobertura básica
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py --cov=api/v1/services/user --cov=api/v1/services/auth
```

### Cobertura con líneas faltantes
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py \
    --cov=api/v1/services/user \
    --cov=api/v1/services/auth \
    --cov-report=term-missing
```

### Cobertura con reporte HTML
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py \
    --cov=api/v1/services/user \
    --cov=api/v1/services/auth \
    --cov=api/v1/routes/user_routes \
    --cov=api/v1/routes/auth_routes \
    --cov-report=html

# Abrir el reporte
firefox htmlcov/index.html  # o tu navegador preferido
```

### Cobertura completa con todos los formatos
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py \
    --cov=api/v1/services \
    --cov=api/v1/routes \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml
```

## Control de Ejecución

### Detener en el primer fallo
```bash
pytest tests/v1/test_users.py -x
```

### Detener después de N fallos
```bash
pytest tests/v1/test_users.py --maxfail=3
```

### Re-ejecutar solo tests que fallaron la última vez
```bash
pytest tests/v1/test_users.py --lf
```

### Re-ejecutar tests que fallaron primero
```bash
pytest tests/v1/test_users.py --ff
```

### Ejecutar nuevo tests primero
```bash
pytest tests/v1/test_users.py --nf
```

## Ejecución Paralela

Requiere `pytest-xdist`:
```bash
pip install pytest-xdist
```

### Ejecución paralela automática (detecta núcleos)
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py -n auto
```

### Especificar número de workers
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py -n 4
```

## Filtros Avanzados

### Ejecutar tests marcados (si usas markers)
```bash
# Si tuvieras markers como @pytest.mark.slow
pytest tests/v1/ -m slow

# Excluir tests marcados
pytest tests/v1/ -m "not slow"
```

### Combinar filtros con expresiones
```bash
# Tests de servicios O que contienen "create"
pytest tests/v1/ -k "Service or create" -v

# Tests de rutas Y que contienen "delete"
pytest tests/v1/ -k "Routes and delete" -v
```

## Debugging

### Entrar en debugger al fallar
```bash
pytest tests/v1/test_users.py --pdb
```

### Entrar en debugger al inicio de cada test
```bash
pytest tests/v1/test_users.py --trace
```

### Mostrar fixtures disponibles
```bash
pytest tests/v1/test_users.py --fixtures
```

### Mostrar setup/teardown de fixtures
```bash
pytest tests/v1/test_users.py --setup-show
```

## Ejemplos de Uso con Script

El script `run_user_tests.sh` simplifica muchas operaciones:

### Todos los tests
```bash
./run_user_tests.sh all
# o simplemente
./run_user_tests.sh
```

### Solo usuarios
```bash
./run_user_tests.sh users
```

### Solo autenticación
```bash
./run_user_tests.sh auth
```

### Solo servicios
```bash
./run_user_tests.sh services
```

### Solo rutas
```bash
./run_user_tests.sh routes
```

### Con cobertura
```bash
./run_user_tests.sh coverage
```

### Modo rápido
```bash
./run_user_tests.sh quick
```

### Solo tests fallidos
```bash
./run_user_tests.sh failed
```

### Paralelo
```bash
./run_user_tests.sh parallel
```

## Integración con IDEs

### VS Code
Agregar en `.vscode/settings.json`:
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests/v1"
    ]
}
```

### PyCharm
1. Ir a Run > Edit Configurations
2. Add > Python tests > pytest
3. Target: Custom
4. Additional Arguments: `-v`
5. Working directory: `/home/lralda/pnud/ventana-magica/backend`

## Watch Mode (auto-rerun)

Requiere `pytest-watch`:
```bash
pip install pytest-watch
```

### Auto-ejecutar en cambios
```bash
ptw tests/v1/test_users.py -- -v
```

## Generación de Reportes

### Reporte JUnit XML (para CI/CD)
```bash
pytest tests/v1/test_users.py tests/v1/test_auth.py --junitxml=report.xml
```

### Reporte JSON
```bash
pip install pytest-json-report
pytest tests/v1/test_users.py tests/v1/test_auth.py --json-report --json-report-file=report.json
```

### Reporte HTML (con pytest-html)
```bash
pip install pytest-html
pytest tests/v1/test_users.py tests/v1/test_auth.py --html=report.html --self-contained-html
```

## Ejemplos de Salidas

### Test exitoso
```
tests/v1/test_users.py::TestUserServices::test_get_user_by_id_success PASSED [1%]
```

### Test fallido
```
tests/v1/test_users.py::TestUserServices::test_get_user_by_id_success FAILED [1%]

================================ FAILURES =================================
_____________ TestUserServices.test_get_user_by_id_success ______________

    def test_get_user_by_id_success(self, db_session, test_admin_user):
        user = get_user_by_id(db_session, test_admin_user.id)
>       assert user is not None
E       AssertionError: assert None is not None

tests/v1/test_users.py:25: AssertionError
```

### Test con warnings
```
tests/v1/test_users.py::TestUserServices::test_get_user_by_id_success PASSED [1%]

================================ warnings =================================
tests/v1/test_users.py::TestUserServices::test_get_user_by_id_success
  /path/to/file.py:10: DeprecationWarning: This is deprecated
```

## Troubleshooting Común

### Error: "ModuleNotFoundError"
```bash
# Asegúrate de estar en el directorio correcto
cd /home/lralda/pnud/ventana-magica/backend

# Verifica PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Error: "fixture not found"
```bash
# Verifica que conftest.py esté en el directorio correcto
ls tests/v1/conftest.py

# Ejecuta con -v para ver fixtures cargadas
pytest tests/v1/test_users.py --fixtures
```

### Tests muy lentos
```bash
# Usa ejecución paralela
pytest tests/v1/ -n auto

# O identifica tests lentos
pytest tests/v1/ --durations=10
```

### Base de datos bloqueada
```bash
# Elimina la base de datos de test
rm test.db
```

## Tips y Mejores Prácticas

1. **Ejecuta tests frecuentemente** mientras desarrollas
2. **Usa -x** para detener en el primer fallo y ahorrar tiempo
3. **Usa --lf** para re-ejecutar solo fallos
4. **Usa -v** siempre para output detallado
5. **Ejecuta cobertura** antes de hacer commit
6. **Usa el script** para comandos comunes
7. **Mantén tests rápidos** (< 0.1s por test idealmente)
8. **Aísla tests** - cada test debe poder ejecutarse independiente

## Ejemplos de Flujo de Trabajo

### Durante desarrollo
```bash
# 1. Ejecutar tests afectados mientras desarrollas
pytest tests/v1/test_users.py::TestUserServices -x -v

# 2. Si falla algo, re-ejecutar solo lo que falló
pytest tests/v1/test_users.py --lf -x -v

# 3. Cuando todo pase, ejecutar suite completa
pytest tests/v1/test_users.py -v
```

### Antes de commit
```bash
# 1. Ejecutar todos los tests
pytest tests/v1/test_users.py tests/v1/test_auth.py -v

# 2. Verificar cobertura
pytest tests/v1/test_users.py tests/v1/test_auth.py --cov=api/v1/services --cov=api/v1/routes --cov-report=term-missing

# 3. Si todo pasa, commit
git add .
git commit -m "Add comprehensive user and auth tests"
```

### En CI/CD
```bash
# GitHub Actions, GitLab CI, etc.
pytest tests/v1/test_users.py tests/v1/test_auth.py -v --cov=api/v1 --cov-report=xml --junitxml=report.xml
```

## Recursos Adicionales

- Documentación de pytest: https://docs.pytest.org/
- pytest-cov: https://pytest-cov.readthedocs.io/
- pytest-xdist: https://pytest-xdist.readthedocs.io/
