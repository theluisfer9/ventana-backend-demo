"""
Comprehensive tests for User services and routes.
Tests CRUD operations, filters, pagination, permissions, and edge cases.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from api.v1.services.user import (
    get_user_by_id,
    get_user_by_email,
    get_user_by_username,
    create_user,
    update_user,
    update_user_password,
    delete_user,
    get_all_users,
    activate_user,
    verify_user,
)
from api.v1.schemas.user import (
    UserCreate,
    UserCreateByAdmin,
    UserUpdate,
    UserFilters,
)
from api.v1.models.user import User
from api.v1.auth.password import verify_password


# ==================== Service Layer Tests ====================


class TestUserServices:
    """Tests for user service functions"""

    def test_get_user_by_id_success(self, db_session, test_admin_user):
        """Test getting user by ID"""
        user = get_user_by_id(db_session, test_admin_user.id)
        assert user is not None
        assert user.id == test_admin_user.id
        assert user.email == test_admin_user.email

    def test_get_user_by_id_not_found(self, db_session):
        """Test getting non-existent user by ID"""
        user = get_user_by_id(db_session, uuid4())
        assert user is None

    def test_get_user_by_email_success(self, db_session, test_admin_user):
        """Test getting user by email"""
        user = get_user_by_email(db_session, "admin@test.com")
        assert user is not None
        assert user.email == "admin@test.com"
        assert user.id == test_admin_user.id

    def test_get_user_by_email_not_found(self, db_session):
        """Test getting non-existent user by email"""
        user = get_user_by_email(db_session, "nonexistent@test.com")
        assert user is None

    def test_get_user_by_username_success(self, db_session, test_admin_user):
        """Test getting user by username"""
        user = get_user_by_username(db_session, "admin")
        assert user is not None
        assert user.username == "admin"
        assert user.id == test_admin_user.id

    def test_get_user_by_username_not_found(self, db_session):
        """Test getting non-existent user by username"""
        user = get_user_by_username(db_session, "nonexistent")
        assert user is None

    def test_create_user_with_password(self, db_session, test_roles):
        """Test creating user with password"""
        user_data = UserCreate(
            email="newuser@test.com",
            username="newuser",
            first_name="New",
            last_name="User",
            password="SecurePass123!",
            role_id=test_roles["analyst"].id,
        )

        user = create_user(db_session, user_data)

        assert user.id is not None
        assert user.email == "newuser@test.com"
        assert user.username == "newuser"
        assert user.password_hash is not None
        assert verify_password("SecurePass123!", user.password_hash)
        assert user.role_id == test_roles["analyst"].id

    def test_create_user_by_admin_without_password(self, db_session, test_roles, test_admin_user):
        """Test admin creating user without password (Keycloak user)"""
        user_data = UserCreateByAdmin(
            email="keycloak@test.com",
            username="keycloak_user",
            first_name="Keycloak",
            last_name="User",
            role_id=test_roles["analyst"].id,
            keycloak_id="kc-123456",
        )

        user = create_user(db_session, user_data, created_by=test_admin_user.id)

        assert user.id is not None
        assert user.email == "keycloak@test.com"
        assert user.password_hash is None
        assert user.keycloak_id == "kc-123456"
        assert user.created_by == test_admin_user.id

    def test_update_user_basic_fields(self, db_session, test_regular_user):
        """Test updating user basic fields"""
        update_data = UserUpdate(
            first_name="Updated",
            last_name="Name",
            phone="+9999999999",
        )

        updated_user = update_user(db_session, test_regular_user, update_data)

        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.phone == "+9999999999"
        assert updated_user.email == test_regular_user.email  # Unchanged

    def test_update_user_partial(self, db_session, test_regular_user):
        """Test partial update of user"""
        original_first_name = test_regular_user.first_name
        update_data = UserUpdate(last_name="OnlyLastName")

        updated_user = update_user(db_session, test_regular_user, update_data)

        assert updated_user.first_name == original_first_name
        assert updated_user.last_name == "OnlyLastName"

    def test_update_user_password(self, db_session, test_regular_user):
        """Test updating user password"""
        new_password = "NewSecurePass123!"

        updated_user = update_user_password(db_session, test_regular_user, new_password)

        assert verify_password(new_password, updated_user.password_hash)

    def test_delete_user_soft(self, db_session, test_regular_user):
        """Test soft delete (deactivation)"""
        result = delete_user(db_session, test_regular_user, soft_delete=True)

        assert result is True
        db_session.refresh(test_regular_user)
        assert test_regular_user.is_active is False

        # User should still exist in DB
        user = get_user_by_id(db_session, test_regular_user.id)
        assert user is not None

    def test_delete_user_hard(self, db_session, test_regular_user):
        """Test hard delete (permanent removal)"""
        user_id = test_regular_user.id

        result = delete_user(db_session, test_regular_user, soft_delete=False)

        assert result is True

        # User should not exist in DB
        user = get_user_by_id(db_session, user_id)
        assert user is None

    def test_activate_user(self, db_session, test_inactive_user):
        """Test activating inactive user"""
        assert test_inactive_user.is_active is False

        activated_user = activate_user(db_session, test_inactive_user)

        assert activated_user.is_active is True

    def test_verify_user(self, db_session, test_inactive_user):
        """Test verifying user"""
        assert test_inactive_user.is_verified is False

        verified_user = verify_user(db_session, test_inactive_user)

        assert verified_user.is_verified is True

    def test_get_all_users_no_filters(self, db_session, test_admin_user, test_regular_user):
        """Test getting all users without filters"""
        filters = UserFilters()
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)

        assert total >= 2
        assert len(users) >= 2

    def test_get_all_users_with_pagination(
        self, db_session, test_admin_user, test_regular_user, test_inactive_user
    ):
        """Test pagination"""
        filters = UserFilters()

        # First page
        users_page1, total = get_all_users(db_session, offset=0, limit=2, filters=filters)
        assert len(users_page1) == 2
        assert total >= 3

        # Second page
        users_page2, total = get_all_users(db_session, offset=2, limit=2, filters=filters)
        assert len(users_page2) >= 1

        # No overlap
        page1_ids = [u.id for u in users_page1]
        page2_ids = [u.id for u in users_page2]
        assert not any(uid in page2_ids for uid in page1_ids)

    def test_get_all_users_filter_by_role(self, db_session, test_admin_user, test_regular_user, test_roles):
        """Test filtering by role"""
        filters = UserFilters(role_id=test_roles["admin"].id)
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)

        assert total >= 1
        assert all(u.role_id == test_roles["admin"].id for u in users)

    def test_get_all_users_filter_by_active_status(
        self, db_session, test_admin_user, test_inactive_user
    ):
        """Test filtering by active status"""
        # Active users only
        filters = UserFilters(is_active=True)
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)
        assert all(u.is_active is True for u in users)

        # Inactive users only
        filters = UserFilters(is_active=False)
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)
        assert all(u.is_active is False for u in users)

    def test_get_all_users_filter_by_verified_status(self, db_session, test_admin_user, test_inactive_user):
        """Test filtering by verified status"""
        filters = UserFilters(is_verified=True)
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)
        assert all(u.is_verified is True for u in users)

    def test_get_all_users_search_by_email(self, db_session, test_admin_user):
        """Test search by email"""
        filters = UserFilters(search="admin@test")
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)

        assert total >= 1
        assert any(u.email == "admin@test.com" for u in users)

    def test_get_all_users_search_by_username(self, db_session, test_regular_user):
        """Test search by username"""
        filters = UserFilters(search="testuser")
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)

        assert total >= 1
        assert any(u.username == "testuser" for u in users)

    def test_get_all_users_search_by_name(self, db_session, test_admin_user):
        """Test search by name"""
        filters = UserFilters(search="Admin")
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)

        assert total >= 1
        assert any("Admin" in u.first_name for u in users)

    def test_get_all_users_filter_by_institution(
        self, db_session, test_admin_user, test_institution
    ):
        """Test filtering by institution"""
        filters = UserFilters(institution_id=test_institution.id)
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)

        assert total >= 1
        assert all(u.institution_id == test_institution.id for u in users)

    def test_get_all_users_filter_by_date_range(
        self, db_session, test_admin_user, test_regular_user
    ):
        """Test filtering by creation date range"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        filters = UserFilters(created_from=yesterday)
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)

        assert total >= 2

    def test_get_all_users_combined_filters(
        self, db_session, test_admin_user, test_regular_user, test_roles, test_institution
    ):
        """Test combining multiple filters"""
        filters = UserFilters(
            role_id=test_roles["analyst"].id,
            institution_id=test_institution.id,
            is_active=True,
            is_verified=True,
        )
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)

        for user in users:
            assert user.role_id == test_roles["analyst"].id
            assert user.institution_id == test_institution.id
            assert user.is_active is True
            assert user.is_verified is True


# ==================== Route/API Tests ====================


class TestUserRoutes:
    """Tests for user API endpoints using authenticated_admin_client"""

    def test_list_users_success(self, authenticated_admin_client, test_regular_user):
        """Test listing users with pagination"""
        response = authenticated_admin_client.get("/api/v1/users/?page=1&size=10")

        assert response.status_code == 200
        json_data = response.json()
        # Handle wrapped response structure
        data = json_data.get("data", json_data)
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_users_with_filters(self, authenticated_admin_client, test_roles):
        """Test listing users with filters"""
        response = authenticated_admin_client.get(
            f"/api/v1/users/?page=1&size=10&role_id={test_roles['admin'].id}&is_active=true"
        )

        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert "items" in data

    def test_create_user_success(self, authenticated_admin_client, test_roles):
        """Test creating a new user"""
        user_data = {
            "email": "newcreated@test.com",
            "username": "newcreated",
            "first_name": "New",
            "last_name": "Created",
            "password": "SecurePass123!",
            "role_id": str(test_roles["analyst"].id),
            "is_active": True,
            "is_verified": False,
        }

        response = authenticated_admin_client.post("/api/v1/users/", json=user_data)

        assert response.status_code == 201
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["email"] == "newcreated@test.com"
        assert data["username"] == "newcreated"
        assert "id" in data

    def test_create_user_duplicate_email(
        self, authenticated_admin_client, test_regular_user, test_roles
    ):
        """Test creating user with duplicate email fails"""
        user_data = {
            "email": test_regular_user.email,  # Duplicate
            "username": "different",
            "first_name": "Test",
            "last_name": "User",
            "password": "SecurePass123!",
            "role_id": str(test_roles["analyst"].id),
        }

        response = authenticated_admin_client.post("/api/v1/users/", json=user_data)

        assert response.status_code == 400
        json_data = response.json()
        detail = json_data.get("detail", json_data.get("message", ""))
        assert "email" in detail.lower()

    def test_create_user_duplicate_username(
        self, authenticated_admin_client, test_regular_user, test_roles
    ):
        """Test creating user with duplicate username fails"""
        user_data = {
            "email": "unique@test.com",
            "username": test_regular_user.username,  # Duplicate
            "first_name": "Test",
            "last_name": "User",
            "password": "SecurePass123!",
            "role_id": str(test_roles["analyst"].id),
        }

        response = authenticated_admin_client.post("/api/v1/users/", json=user_data)

        assert response.status_code == 400
        json_data = response.json()
        detail = json_data.get("detail", json_data.get("message", ""))
        assert "usuario" in detail.lower()

    def test_get_user_by_id_success(self, authenticated_admin_client, test_admin_user):
        """Test getting user by ID"""
        response = authenticated_admin_client.get(f"/api/v1/users/{test_admin_user.id}")

        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["id"] == str(test_admin_user.id)
        assert data["email"] == test_admin_user.email

    def test_get_user_by_id_not_found(self, authenticated_admin_client):
        """Test getting non-existent user"""
        response = authenticated_admin_client.get(f"/api/v1/users/{uuid4()}")

        assert response.status_code == 404
        json_data = response.json()
        detail = json_data.get("detail", json_data.get("message", ""))
        assert "no encontrado" in detail.lower()

    def test_update_user_success(self, authenticated_admin_client, test_regular_user):
        """Test updating user"""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "+1111111111",
        }

        response = authenticated_admin_client.put(
            f"/api/v1/users/{test_regular_user.id}", json=update_data
        )

        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["phone"] == "+1111111111"

    def test_update_user_not_found(self, authenticated_admin_client):
        """Test updating non-existent user"""
        update_data = {"first_name": "Updated"}

        response = authenticated_admin_client.put(f"/api/v1/users/{uuid4()}", json=update_data)

        assert response.status_code == 404

    def test_update_user_duplicate_email(
        self, authenticated_admin_client, test_admin_user, test_regular_user
    ):
        """Test updating user with duplicate email fails"""
        update_data = {"email": test_admin_user.email}  # Already taken

        response = authenticated_admin_client.put(
            f"/api/v1/users/{test_regular_user.id}", json=update_data
        )

        assert response.status_code == 400
        json_data = response.json()
        detail = json_data.get("detail", json_data.get("message", ""))
        assert "email" in detail.lower()

    def test_delete_user_success(self, authenticated_admin_client, test_regular_user):
        """Test deleting (deactivating) user"""
        response = authenticated_admin_client.delete(f"/api/v1/users/{test_regular_user.id}")

        assert response.status_code == 200
        json_data = response.json()
        # Check in data.message or top-level message
        message = json_data.get("data", json_data).get("message", json_data.get("message", ""))
        assert "desactivado" in message.lower()

    def test_delete_user_self_deletion_prevented(self, authenticated_admin_client, test_admin_user):
        """Test that user cannot delete themselves"""
        response = authenticated_admin_client.delete(f"/api/v1/users/{test_admin_user.id}")

        assert response.status_code == 400
        json_data = response.json()
        detail = json_data.get("detail", json_data.get("message", ""))
        assert "propia cuenta" in detail.lower()

    def test_activate_user_success(self, authenticated_admin_client, test_inactive_user):
        """Test activating inactive user"""
        assert test_inactive_user.is_active is False

        response = authenticated_admin_client.put(
            f"/api/v1/users/{test_inactive_user.id}/activate"
        )

        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["is_active"] is True

    def test_revoke_user_sessions_success(self, authenticated_admin_client, test_regular_user, db_session):
        """Test revoking all user sessions"""
        # Create some sessions for the user
        from api.v1.models.user_session import UserSession
        from datetime import datetime, timezone, timedelta

        session1 = UserSession(
            user_id=test_regular_user.id,
            token_jti="test-jti-1",
            ip_address="127.0.0.1",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        session2 = UserSession(
            user_id=test_regular_user.id,
            token_jti="test-jti-2",
            ip_address="127.0.0.1",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        db_session.add(session1)
        db_session.add(session2)
        db_session.commit()

        response = authenticated_admin_client.delete(
            f"/api/v1/users/{test_regular_user.id}/sessions"
        )

        assert response.status_code == 200
        json_data = response.json()
        message = json_data.get("data", json_data).get("message", json_data.get("message", ""))
        assert "sesiones revocadas" in message.lower()
        assert "2" in message


# ==================== Edge Cases and Validation ====================


class TestUserEdgeCases:
    """Tests for edge cases and validation"""

    def test_create_user_with_long_name(self, db_session, test_roles):
        """Test creating user with very long name"""
        user_data = UserCreate(
            email="longname@test.com",
            username="longname",
            first_name="A" * 99,  # Max is 100
            last_name="B" * 99,
            password="SecurePass123!",
            role_id=test_roles["analyst"].id,
        )

        user = create_user(db_session, user_data)
        assert len(user.first_name) == 99

    def test_user_full_name_property(self, test_admin_user):
        """Test full_name property"""
        assert test_admin_user.full_name == "Admin User"

    def test_user_has_permission(self, db_session, test_admin_user, test_regular_user):
        """Test has_permission method"""
        # Admin has users:read permission
        assert test_admin_user.has_permission("users:read") is True
        assert test_admin_user.has_permission("users:create") is True

        # Regular user doesn't have users permissions
        assert test_regular_user.has_permission("users:read") is False
        assert test_regular_user.has_permission("reports:read") is True

    def test_get_all_users_empty_result(self, db_session):
        """Test getting users when none match filters"""
        filters = UserFilters(role_id=uuid4())  # Non-existent role
        users, total = get_all_users(db_session, offset=0, limit=10, filters=filters)

        assert total == 0
        assert len(users) == 0

    def test_update_user_empty_update(self, db_session, test_regular_user):
        """Test updating user with no changes"""
        original_email = test_regular_user.email
        update_data = UserUpdate()  # No fields set

        updated_user = update_user(db_session, test_regular_user, update_data)

        assert updated_user.email == original_email
