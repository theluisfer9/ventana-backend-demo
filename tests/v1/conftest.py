import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from uuid import uuid4
from dotenv import load_dotenv

from api.v1.models.ticket import BasePG
from api.v1.models.user import User
from api.v1.models.role import Role
from api.v1.models.institution import Institution
from api.v1.models.permission import Permission
from api.v1.models.user_session import UserSession
from api.v1.auth.password import hash_password
from main import app
from api.v1.config.database import get_sync_db_pg

load_dotenv()

# BD de prueba PostgreSQL
SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://dev_pnud:M1d3sPnud%40@127.0.0.1:5432/db_ventana_pnud_test"
)

# Engine y sessionmaker SYNC para PostgreSQL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)
TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

# Preparar esquema antes/despues de cada test
@pytest.fixture(scope="function", autouse=True)
def prepare_db():
    BasePG.metadata.create_all(bind=engine)
    yield
    BasePG.metadata.drop_all(bind=engine)

# DB Session for tests
@pytest.fixture(scope="function")
def db_session(prepare_db):
    """Provides a database session for direct DB operations in tests"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Cliente con override SYNC de la dependencia
@pytest.fixture(scope="function")
def client(prepare_db):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_sync_db_pg] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# ==================== Fixtures de datos de prueba ====================

@pytest.fixture
def test_permissions(db_session):
    """Creates test permissions"""
    permissions = [
        Permission(
            id=uuid4(),
            code="users:read",
            name="Leer usuarios",
            module="users",
        ),
        Permission(
            id=uuid4(),
            code="users:create",
            name="Crear usuarios",
            module="users",
        ),
        Permission(
            id=uuid4(),
            code="users:update",
            name="Actualizar usuarios",
            module="users",
        ),
        Permission(
            id=uuid4(),
            code="users:delete",
            name="Eliminar usuarios",
            module="users",
        ),
        Permission(
            id=uuid4(),
            code="reports:read",
            name="Leer reportes",
            module="reports",
        ),
    ]

    for perm in permissions:
        db_session.add(perm)

    db_session.commit()
    return {p.code: p for p in permissions}


@pytest.fixture
def test_roles(db_session, test_permissions):
    """Creates test roles with permissions"""
    admin_role = Role(
        id=uuid4(),
        code="ADMIN",
        name="Administrador",
        description="Rol de administrador con todos los permisos",
        is_system=True,
    )

    # Add all user permissions to admin
    admin_role.permissions = [
        test_permissions["users:read"],
        test_permissions["users:create"],
        test_permissions["users:update"],
        test_permissions["users:delete"],
    ]

    analyst_role = Role(
        id=uuid4(),
        code="ANALYST",
        name="Analista",
        description="Rol de analista con permisos limitados",
        is_system=True,
    )

    # Add only read permission to analyst
    analyst_role.permissions = [test_permissions["reports:read"]]

    db_session.add(admin_role)
    db_session.add(analyst_role)
    db_session.commit()

    return {"admin": admin_role, "analyst": analyst_role}


@pytest.fixture
def test_institution(db_session):
    """Creates a test institution"""
    institution = Institution(
        id=uuid4(),
        code="TEST_INST",
        name="Test Institution",
        description="Institution for testing",
        is_active=True,
    )

    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    return institution


@pytest.fixture
def test_admin_user(db_session, test_roles, test_institution):
    """Creates a test admin user"""
    admin_user = User(
        id=uuid4(),
        email="admin@test.com",
        username="admin",
        password_hash=hash_password("Admin123!"),
        first_name="Admin",
        last_name="User",
        phone="+1234567890",
        role_id=test_roles["admin"].id,
        institution_id=test_institution.id,
        is_active=True,
        is_verified=True,
    )

    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    return admin_user


@pytest.fixture
def test_regular_user(db_session, test_roles, test_institution):
    """Creates a test regular (analyst) user"""
    user = User(
        id=uuid4(),
        email="user@test.com",
        username="testuser",
        password_hash=hash_password("User123!"),
        first_name="Test",
        last_name="User",
        phone="+0987654321",
        role_id=test_roles["analyst"].id,
        institution_id=test_institution.id,
        is_active=True,
        is_verified=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture
def test_inactive_user(db_session, test_roles, test_institution):
    """Creates an inactive test user"""
    user = User(
        id=uuid4(),
        email="inactive@test.com",
        username="inactive",
        password_hash=hash_password("Inactive123!"),
        first_name="Inactive",
        last_name="User",
        role_id=test_roles["analyst"].id,
        institution_id=test_institution.id,
        is_active=False,
        is_verified=False,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture
def mock_current_user(test_admin_user):
    """Returns a mock current user for dependency override"""
    return test_admin_user


@pytest.fixture
def authenticated_admin_client(db_session, test_admin_user):
    """
    Provides an authenticated client with admin user.
    Overrides both get_current_user and RequirePermission dependencies.
    Uses the same db_session as the test for consistency.
    """
    from api.v1.dependencies.auth_dependency import get_current_user, get_token_from_header
    from api.v1.dependencies.permission_dependency import RequirePermission

    def override_get_db():
        # Reutilizar la misma sesión del test
        yield db_session

    def override_get_current_user():
        return test_admin_user

    def override_get_token():
        return "mock_token"

    # Store original __call__ method
    original_call = RequirePermission.__call__

    # Create a mock __call__ that returns the admin user
    def mock_call(self, current_user=None):
        return test_admin_user

    # Apply the monkey patch
    RequirePermission.__call__ = mock_call

    # Apply dependency overrides
    app.dependency_overrides[get_sync_db_pg] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_token_from_header] = override_get_token

    with TestClient(app) as client:
        yield client

    # Restore original
    RequirePermission.__call__ = original_call
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_regular_client(db_session, test_regular_user):
    """
    Provides an authenticated client with regular (analyst) user.
    Uses the same db_session as the test for consistency.
    """
    from api.v1.dependencies.auth_dependency import get_current_user, get_token_from_header
    from api.v1.dependencies.permission_dependency import RequirePermission

    def override_get_db():
        # Reutilizar la misma sesión del test
        yield db_session

    def override_get_current_user():
        return test_regular_user

    def override_get_token():
        return "mock_token"

    # Store original __call__ method
    original_call = RequirePermission.__call__

    # Create a mock __call__ that returns the regular user
    def mock_call(self, current_user=None):
        return test_regular_user

    # Apply the monkey patch
    RequirePermission.__call__ = mock_call

    # Apply dependency overrides
    app.dependency_overrides[get_sync_db_pg] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_token_from_header] = override_get_token

    with TestClient(app) as client:
        yield client

    # Restore original
    RequirePermission.__call__ = original_call
    app.dependency_overrides.clear()
