from unittest.mock import Mock, patch

from api.v1.services.keycloak_admin import (
    build_user_payload,
    create_keycloak_user,
    get_admin_access_token,
)


def test_build_user_payload_marks_update_password_required_action():
    payload = build_user_payload(
        email="new@test.com",
        username="newuser",
        first_name="New",
        last_name="User",
        enabled=True,
    )

    assert payload["email"] == "new@test.com"
    assert payload["username"] == "newuser"
    assert payload["enabled"] is True
    assert payload["requiredActions"] == ["UPDATE_PASSWORD"]


@patch("api.v1.services.keycloak_admin.get_admin_access_token", return_value="admin-token")
@patch("api.v1.services.keycloak_admin.httpx.post")
@patch("api.v1.services.keycloak_admin.set_temporary_password")
def test_create_keycloak_user_creates_user_and_sets_temporary_password(
    mock_set_password,
    mock_post,
    _mock_token,
):
    response = Mock()
    response.status_code = 201
    response.headers = {
        "Location": "https://kc.local/admin/realms/test/users/kc-user-123"
    }
    response.raise_for_status = Mock()
    mock_post.return_value = response

    keycloak_id = create_keycloak_user(
        email="new@test.com",
        username="newuser",
        first_name="New",
        last_name="User",
        temporary_password="TempPass123!",
        enabled=True,
    )

    assert keycloak_id == "kc-user-123"
    mock_set_password.assert_called_once_with("kc-user-123", "TempPass123!")


@patch("api.v1.services.keycloak_admin.KEYCLOAK_ADMIN_CLIENT_ID", "")
@patch("api.v1.services.keycloak_admin.KEYCLOAK_ADMIN_CLIENT_SECRET", "")
@patch("api.v1.services.keycloak_admin.KEYCLOAK_ADMIN_USERNAME", "admin")
@patch("api.v1.services.keycloak_admin.KEYCLOAK_ADMIN_PASSWORD", "admin")
@patch("api.v1.services.keycloak_admin.httpx.post")
def test_get_admin_access_token_supports_password_grant_for_local_bootstrap_admin(
    mock_post,
):
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"access_token": "bootstrap-token"}
    mock_post.return_value = response

    token = get_admin_access_token()

    assert token == "bootstrap-token"
    assert mock_post.call_args.kwargs["data"] == {
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": "admin",
        "password": "admin",
    }
