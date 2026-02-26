"""
Tests para el CRUD de roles y permisos.
Cubre servicios (role_service) y rutas (/api/v1/roles/).
"""

import pytest
from uuid import uuid4

from api.v1.models.role import Role
from api.v1.models.permission import Permission
from api.v1.services.role import (
    get_role_by_id,
    get_role_by_code,
    get_all_roles,
    create_role,
    update_role,
    delete_role,
    update_role_permissions,
    get_all_permissions,
)
from api.v1.schemas.role import RoleCreate, RoleUpdate


# ==================== Service Tests ====================


class TestRoleServiceGetById:
    """Tests for get_role_by_id"""

    def test_get_role_by_id_found(self, db_session, test_roles):
        role = get_role_by_id(db_session, test_roles["admin"].id)
        assert role is not None
        assert role.code == "ADMIN"

    def test_get_role_by_id_not_found(self, db_session):
        role = get_role_by_id(db_session, uuid4())
        assert role is None


class TestRoleServiceGetByCode:
    """Tests for get_role_by_code"""

    def test_get_role_by_code_found(self, db_session, test_roles):
        role = get_role_by_code(db_session, "ADMIN")
        assert role is not None
        assert role.name == "Administrador"

    def test_get_role_by_code_not_found(self, db_session):
        role = get_role_by_code(db_session, "NONEXISTENT")
        assert role is None


class TestRoleServiceGetAll:
    """Tests for get_all_roles"""

    def test_get_all_roles(self, db_session, test_roles):
        roles = get_all_roles(db_session)
        assert len(roles) == 2
        # Ordered by name
        names = [r.name for r in roles]
        assert names == sorted(names)


class TestRoleServiceCreate:
    """Tests for create_role"""

    def test_create_role_without_permissions(self, db_session):
        role_data = RoleCreate(
            code="NEW_ROLE",
            name="Nuevo Rol",
            description="Descripcion del rol",
        )
        role = create_role(db_session, role_data)
        assert role.id is not None
        assert role.code == "NEW_ROLE"
        assert role.name == "Nuevo Rol"
        assert len(role.permissions) == 0

    def test_create_role_with_permissions(self, db_session, test_permissions):
        perm_ids = [
            test_permissions["users:read"].id,
            test_permissions["users:create"].id,
        ]
        role_data = RoleCreate(
            code="CUSTOM",
            name="Custom Role",
            permission_ids=perm_ids,
        )
        role = create_role(db_session, role_data)
        assert len(role.permissions) == 2
        perm_codes = {p.code for p in role.permissions}
        assert "users:read" in perm_codes
        assert "users:create" in perm_codes


class TestRoleServiceUpdate:
    """Tests for update_role"""

    def test_update_non_system_role(self, db_session):
        # Create a non-system role first
        role = Role(
            id=uuid4(),
            code="EDITABLE",
            name="Editable",
            is_system=False,
        )
        db_session.add(role)
        db_session.commit()

        update_data = RoleUpdate(code="EDITED", name="Edited Role", description="Updated")
        updated = update_role(db_session, role, update_data)
        assert updated.code == "EDITED"
        assert updated.name == "Edited Role"
        assert updated.description == "Updated"

    def test_update_system_role_only_description(self, db_session, test_roles):
        admin_role = test_roles["admin"]
        original_code = admin_role.code
        original_name = admin_role.name

        update_data = RoleUpdate(code="CHANGED", name="Changed", description="New desc")
        updated = update_role(db_session, admin_role, update_data)

        # System roles only allow description changes
        assert updated.code == original_code
        assert updated.name == original_name
        assert updated.description == "New desc"


class TestRoleServiceDelete:
    """Tests for delete_role"""

    def test_delete_non_system_role(self, db_session):
        role = Role(id=uuid4(), code="DELETABLE", name="Deletable", is_system=False)
        db_session.add(role)
        db_session.commit()

        result = delete_role(db_session, role)
        assert result is True
        assert get_role_by_id(db_session, role.id) is None

    def test_delete_system_role_fails(self, db_session, test_roles):
        result = delete_role(db_session, test_roles["admin"])
        assert result is False
        # Role still exists
        assert get_role_by_id(db_session, test_roles["admin"].id) is not None


class TestRoleServicePermissions:
    """Tests for update_role_permissions and get_all_permissions"""

    def test_update_role_permissions(self, db_session, test_roles, test_permissions):
        analyst = test_roles["analyst"]
        # Analyst only has reports:read, let's add users:read
        new_perm_ids = [
            test_permissions["reports:read"].id,
            test_permissions["users:read"].id,
        ]
        updated = update_role_permissions(db_session, analyst, new_perm_ids)
        assert len(updated.permissions) == 2
        codes = {p.code for p in updated.permissions}
        assert "reports:read" in codes
        assert "users:read" in codes

    def test_get_all_permissions(self, db_session, test_permissions):
        perms = get_all_permissions(db_session)
        assert len(perms) == 7
        # Ordered by module, code
        modules = [p.module for p in perms]
        assert modules == sorted(modules)


# ==================== Route Tests ====================


class TestRoleRoutes:
    """Tests for role API endpoints"""

    def test_list_roles(self, authenticated_admin_client, test_roles):
        response = authenticated_admin_client.get("/api/v1/roles/")
        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_create_role(self, authenticated_admin_client, test_permissions):
        payload = {
            "code": "REVIEWER",
            "name": "Reviewer",
            "description": "Can review items",
        }
        response = authenticated_admin_client.post("/api/v1/roles/", json=payload)
        assert response.status_code == 201
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["code"] == "REVIEWER"

    def test_create_role_duplicate_code(self, authenticated_admin_client, test_roles):
        payload = {
            "code": "ADMIN",
            "name": "Another Admin",
        }
        response = authenticated_admin_client.post("/api/v1/roles/", json=payload)
        assert response.status_code == 400

    def test_get_role_by_id(self, authenticated_admin_client, test_roles):
        role_id = str(test_roles["admin"].id)
        response = authenticated_admin_client.get(f"/api/v1/roles/{role_id}")
        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["code"] == "ADMIN"

    def test_get_role_not_found(self, authenticated_admin_client):
        response = authenticated_admin_client.get(f"/api/v1/roles/{uuid4()}")
        assert response.status_code == 404

    def test_update_role(self, authenticated_admin_client, db_session):
        # Create a non-system role
        role = Role(id=uuid4(), code="UPDATABLE", name="Updatable", is_system=False)
        db_session.add(role)
        db_session.commit()

        payload = {"code": "UPDATED_CODE", "name": "Updated Name"}
        response = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}", json=payload
        )
        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["code"] == "UPDATED_CODE"

    def test_update_role_duplicate_code(self, authenticated_admin_client, test_roles, db_session):
        # Create another role
        role = Role(id=uuid4(), code="UNIQUE_ROLE", name="Unique", is_system=False)
        db_session.add(role)
        db_session.commit()

        # Try to change code to existing "ADMIN"
        payload = {"code": "ADMIN"}
        response = authenticated_admin_client.put(
            f"/api/v1/roles/{role.id}", json=payload
        )
        assert response.status_code == 400

    def test_delete_non_system_role(self, authenticated_admin_client, db_session):
        role = Role(id=uuid4(), code="TO_DELETE", name="To Delete", is_system=False)
        db_session.add(role)
        db_session.commit()

        response = authenticated_admin_client.delete(f"/api/v1/roles/{role.id}")
        assert response.status_code == 200

    def test_delete_system_role_fails(self, authenticated_admin_client, test_roles):
        role_id = str(test_roles["admin"].id)
        response = authenticated_admin_client.delete(f"/api/v1/roles/{role_id}")
        assert response.status_code == 400

    def test_list_permissions(self, authenticated_admin_client, test_permissions):
        response = authenticated_admin_client.get("/api/v1/roles/permissions")
        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert isinstance(data, list)
        assert len(data) == 7

    def test_update_role_permissions(self, authenticated_admin_client, test_roles, test_permissions):
        role_id = str(test_roles["analyst"].id)
        perm_ids = [
            str(test_permissions["users:read"].id),
            str(test_permissions["users:create"].id),
        ]
        payload = {"permission_ids": perm_ids}
        response = authenticated_admin_client.put(
            f"/api/v1/roles/{role_id}/permissions", json=payload
        )
        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert len(data["permissions"]) == 2
