"""
Tests de control de acceso RBAC.
Verifica que un usuario ANALYST (solo reports:read) recibe 403 en endpoints protegidos,
y que un usuario ADMIN con todos los permisos puede acceder.

Usa fixtures propios que NO hacen monkey-patch de RequirePermission.__call__,
dejando que la logica real de permisos ejecute.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from api.v1.models.user import User
from api.v1.models.role import Role
from api.v1.models.permission import Permission
from api.v1.models.institution import Institution
from api.v1.auth.password import hash_password
from api.v1.config.database import get_sync_db_pg
from api.v1.dependencies.auth_dependency import get_current_user, get_token_from_header
from main import app

from tests.v1.conftest import TestingSessionLocal


# ==================== Fixtures RBAC (sin monkey-patch) ====================


@pytest.fixture
def rbac_permissions(db_session):
    """Crea permisos necesarios para las pruebas RBAC."""
    perms = [
        Permission(id=uuid4(), code="users:read", name="Leer usuarios", module="users"),
        Permission(id=uuid4(), code="users:create", name="Crear usuarios", module="users"),
        Permission(id=uuid4(), code="users:update", name="Actualizar usuarios", module="users"),
        Permission(id=uuid4(), code="users:delete", name="Eliminar usuarios", module="users"),
        Permission(id=uuid4(), code="roles:manage", name="Gestionar roles", module="roles"),
        Permission(id=uuid4(), code="reports:read", name="Leer reportes", module="reports"),
    ]
    for p in perms:
        db_session.add(p)
    db_session.commit()
    return {p.code: p for p in perms}


@pytest.fixture
def rbac_roles(db_session, rbac_permissions):
    """Crea roles ADMIN (todos los permisos) y ANALYST (solo reports:read)."""
    admin_role = Role(
        id=uuid4(),
        code="RBAC_ADMIN",
        name="RBAC Admin",
        is_system=True,
    )
    admin_role.permissions = list(rbac_permissions.values())

    analyst_role = Role(
        id=uuid4(),
        code="RBAC_ANALYST",
        name="RBAC Analyst",
        is_system=False,
    )
    analyst_role.permissions = [rbac_permissions["reports:read"]]

    db_session.add(admin_role)
    db_session.add(analyst_role)
    db_session.commit()

    return {"admin": admin_role, "analyst": analyst_role}


@pytest.fixture
def rbac_institution(db_session):
    """Crea una institucion para los usuarios RBAC."""
    inst = Institution(
        id=uuid4(),
        code="RBAC_INST",
        name="RBAC Institution",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    return inst


@pytest.fixture
def rbac_admin_user(db_session, rbac_roles, rbac_institution):
    """Crea un usuario admin con todos los permisos."""
    user = User(
        id=uuid4(),
        email="rbac_admin@test.com",
        username="rbac_admin",
        password_hash=hash_password("Admin123!"),
        first_name="RBAC",
        last_name="Admin",
        phone="+1234567890",
        role_id=rbac_roles["admin"].id,
        institution_id=rbac_institution.id,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def rbac_analyst_user(db_session, rbac_roles, rbac_institution):
    """Crea un usuario analyst con solo reports:read."""
    user = User(
        id=uuid4(),
        email="rbac_analyst@test.com",
        username="rbac_analyst",
        password_hash=hash_password("Analyst123!"),
        first_name="RBAC",
        last_name="Analyst",
        phone="+0987654321",
        role_id=rbac_roles["analyst"].id,
        institution_id=rbac_institution.id,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_rbac_client(db_session, user):
    """
    Crea un TestClient que inyecta el usuario dado como current_user,
    pero NO hace monkey-patch de RequirePermission.__call__,
    dejando la logica real de permisos activa.
    """
    def override_get_db():
        yield db_session

    def override_get_current_user():
        return user

    def override_get_token():
        return "mock_rbac_token"

    app.dependency_overrides[get_sync_db_pg] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_token_from_header] = override_get_token

    return TestClient(app)


@pytest.fixture
def admin_rbac_client(db_session, rbac_admin_user):
    """Cliente autenticado como admin (permisos reales activos)."""
    client = _make_rbac_client(db_session, rbac_admin_user)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def analyst_rbac_client(db_session, rbac_analyst_user):
    """Cliente autenticado como analyst (permisos reales activos)."""
    client = _make_rbac_client(db_session, rbac_analyst_user)
    yield client
    app.dependency_overrides.clear()


# ==================== Analyst DENIED Tests ====================


class TestAnalystDeniedUsers:
    """Analyst NO puede acceder a endpoints de usuarios."""

    def test_analyst_cannot_list_users(self, analyst_rbac_client):
        response = analyst_rbac_client.get("/api/v1/users/")
        assert response.status_code == 403

    def test_analyst_cannot_create_user(self, analyst_rbac_client, rbac_roles, rbac_institution):
        payload = {
            "email": "new@test.com",
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "role_id": str(rbac_roles["analyst"].id),
            "institution_id": str(rbac_institution.id),
        }
        response = analyst_rbac_client.post("/api/v1/users/", json=payload)
        assert response.status_code == 403

    def test_analyst_cannot_update_user(self, analyst_rbac_client, rbac_admin_user):
        payload = {"first_name": "Hacked"}
        response = analyst_rbac_client.put(
            f"/api/v1/users/{rbac_admin_user.id}", json=payload
        )
        assert response.status_code == 403

    def test_analyst_cannot_delete_user(self, analyst_rbac_client, rbac_admin_user):
        response = analyst_rbac_client.delete(
            f"/api/v1/users/{rbac_admin_user.id}"
        )
        assert response.status_code == 403


class TestAnalystDeniedRoles:
    """Analyst NO puede acceder a endpoints de roles."""

    def test_analyst_cannot_list_roles(self, analyst_rbac_client):
        response = analyst_rbac_client.get("/api/v1/roles/")
        assert response.status_code == 403

    def test_analyst_cannot_create_role(self, analyst_rbac_client):
        payload = {"code": "EVIL", "name": "Evil Role"}
        response = analyst_rbac_client.post("/api/v1/roles/", json=payload)
        assert response.status_code == 403

    def test_analyst_cannot_get_role(self, analyst_rbac_client, rbac_roles):
        response = analyst_rbac_client.get(
            f"/api/v1/roles/{rbac_roles['admin'].id}"
        )
        assert response.status_code == 403

    def test_analyst_cannot_delete_role(self, analyst_rbac_client, rbac_roles):
        response = analyst_rbac_client.delete(
            f"/api/v1/roles/{rbac_roles['analyst'].id}"
        )
        assert response.status_code == 403

    def test_analyst_cannot_list_permissions(self, analyst_rbac_client):
        response = analyst_rbac_client.get("/api/v1/roles/permissions")
        assert response.status_code == 403


class TestAnalystDeniedInstitutions:
    """Analyst NO puede acceder a endpoints de instituciones."""

    def test_analyst_cannot_list_institutions(self, analyst_rbac_client):
        response = analyst_rbac_client.get("/api/v1/institutions/")
        assert response.status_code == 403

    def test_analyst_cannot_create_institution(self, analyst_rbac_client):
        payload = {"code": "EVIL_INST", "name": "Evil Institution"}
        response = analyst_rbac_client.post("/api/v1/institutions/", json=payload)
        assert response.status_code == 403

    def test_analyst_cannot_update_institution(self, analyst_rbac_client, rbac_institution):
        payload = {"name": "Hacked"}
        response = analyst_rbac_client.put(
            f"/api/v1/institutions/{rbac_institution.id}", json=payload
        )
        assert response.status_code == 403

    def test_analyst_cannot_delete_institution(self, analyst_rbac_client, rbac_institution):
        response = analyst_rbac_client.delete(
            f"/api/v1/institutions/{rbac_institution.id}"
        )
        assert response.status_code == 403


# ==================== Admin ALLOWED Tests ====================


class TestAdminAllowed:
    """Admin SI puede acceder a endpoints protegidos."""

    def test_admin_can_list_users(self, admin_rbac_client):
        response = admin_rbac_client.get("/api/v1/users/")
        assert response.status_code == 200

    def test_admin_can_list_roles(self, admin_rbac_client):
        response = admin_rbac_client.get("/api/v1/roles/")
        assert response.status_code == 200

    def test_admin_can_list_institutions(self, admin_rbac_client):
        response = admin_rbac_client.get("/api/v1/institutions/")
        assert response.status_code == 200

    def test_admin_can_create_institution(self, admin_rbac_client):
        payload = {
            "code": "ADMIN_CREATED",
            "name": "Admin Created Institution",
        }
        response = admin_rbac_client.post("/api/v1/institutions/", json=payload)
        assert response.status_code == 201
