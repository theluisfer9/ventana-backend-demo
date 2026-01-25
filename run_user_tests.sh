#!/bin/bash
# Script para ejecutar tests de usuarios y autenticación

echo "======================================"
echo "Tests de Usuarios y Autenticación"
echo "======================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que estamos en el directorio correcto
if [ ! -f "pytest.ini" ]; then
    echo -e "${RED}Error: Debe ejecutar este script desde el directorio backend${NC}"
    exit 1
fi

# Función para ejecutar tests con descripción
run_test() {
    local description=$1
    local command=$2

    echo -e "${BLUE}$description${NC}"
    echo "Comando: $command"
    echo "--------------------------------------"

    eval $command
    local exit_code=$?

    echo ""

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ Tests pasaron exitosamente${NC}"
    else
        echo -e "${RED}✗ Tests fallaron${NC}"
    fi

    echo ""
    echo ""

    return $exit_code
}

# Opciones del script
case "${1:-all}" in
    "users")
        run_test "Ejecutando tests de usuarios..." \
                 "python -m pytest tests/v1/test_users.py -v"
        ;;

    "auth")
        run_test "Ejecutando tests de autenticación..." \
                 "python -m pytest tests/v1/test_auth.py -v"
        ;;

    "services")
        echo -e "${BLUE}Ejecutando tests de servicios (usuarios y auth)${NC}"
        echo "--------------------------------------"
        python -m pytest tests/v1/test_users.py::TestUserServices tests/v1/test_auth.py::TestAuthServices -v
        ;;

    "routes")
        echo -e "${BLUE}Ejecutando tests de rutas (usuarios y auth)${NC}"
        echo "--------------------------------------"
        python -m pytest tests/v1/test_users.py::TestUserRoutes tests/v1/test_auth.py::TestAuthRoutes -v
        ;;

    "coverage")
        echo -e "${BLUE}Ejecutando tests con cobertura de código${NC}"
        echo "--------------------------------------"
        python -m pytest tests/v1/test_users.py tests/v1/test_auth.py \
            --cov=api/v1/services/user \
            --cov=api/v1/services/auth \
            --cov=api/v1/routes/user_routes \
            --cov=api/v1/routes/auth_routes \
            --cov-report=term-missing \
            --cov-report=html

        echo ""
        echo -e "${GREEN}Reporte HTML generado en: htmlcov/index.html${NC}"
        ;;

    "quick")
        echo -e "${BLUE}Ejecutando tests rápidos (sin verbosidad)${NC}"
        echo "--------------------------------------"
        python -m pytest tests/v1/test_users.py tests/v1/test_auth.py -q
        ;;

    "failed")
        echo -e "${BLUE}Re-ejecutando solo tests que fallaron${NC}"
        echo "--------------------------------------"
        python -m pytest tests/v1/test_users.py tests/v1/test_auth.py --lf -v
        ;;

    "parallel")
        echo -e "${BLUE}Ejecutando tests en paralelo${NC}"
        echo "--------------------------------------"
        if python -m pytest --help | grep -q "\-n"; then
            python -m pytest tests/v1/test_users.py tests/v1/test_auth.py -n auto -v
        else
            echo -e "${RED}Error: pytest-xdist no está instalado${NC}"
            echo "Instalar con: pip install pytest-xdist"
            exit 1
        fi
        ;;

    "all"|*)
        echo -e "${BLUE}Ejecutando todos los tests de usuarios y autenticación${NC}"
        echo "--------------------------------------"
        python -m pytest tests/v1/test_users.py tests/v1/test_auth.py -v
        exit_code=$?

        echo ""
        echo "======================================"
        if [ $exit_code -eq 0 ]; then
            echo -e "${GREEN}✓ TODOS LOS TESTS PASARON${NC}"
        else
            echo -e "${RED}✗ ALGUNOS TESTS FALLARON${NC}"
        fi
        echo "======================================"

        exit $exit_code
        ;;
esac

echo ""
echo "Opciones disponibles:"
echo "  ./run_user_tests.sh [opción]"
echo ""
echo "Opciones:"
echo "  all       - Ejecutar todos los tests (default)"
echo "  users     - Solo tests de usuarios"
echo "  auth      - Solo tests de autenticación"
echo "  services  - Solo tests de servicios"
echo "  routes    - Solo tests de rutas/endpoints"
echo "  coverage  - Ejecutar con reporte de cobertura"
echo "  quick     - Ejecutar sin verbosidad"
echo "  failed    - Re-ejecutar solo tests fallidos"
echo "  parallel  - Ejecutar en paralelo (requiere pytest-xdist)"
