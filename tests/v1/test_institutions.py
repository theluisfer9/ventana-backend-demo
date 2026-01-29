"""
Tests para el CRUD de instituciones.
Cubre servicios (institution_service) y rutas (/api/v1/institutions/).
"""

import pytest
from uuid import uuid4

from api.v1.models.institution import Institution
from api.v1.services.institution import (
    get_institution_by_id,
    get_institution_by_code,
    get_all_institutions,
    create_institution,
    update_institution,
    delete_institution,
)
from api.v1.schemas.institution import InstitutionCreate, InstitutionUpdate


# ==================== Service Tests ====================


class TestInstitutionServiceGetById:
    """Tests for get_institution_by_id"""

    def test_get_institution_by_id_found(self, db_session, test_institution):
        inst = get_institution_by_id(db_session, test_institution.id)
        assert inst is not None
        assert inst.code == "TEST_INST"

    def test_get_institution_by_id_not_found(self, db_session):
        inst = get_institution_by_id(db_session, uuid4())
        assert inst is None


class TestInstitutionServiceGetByCode:
    """Tests for get_institution_by_code"""

    def test_get_institution_by_code_found(self, db_session, test_institution):
        inst = get_institution_by_code(db_session, "TEST_INST")
        assert inst is not None
        assert inst.name == "Test Institution"

    def test_get_institution_by_code_not_found(self, db_session):
        inst = get_institution_by_code(db_session, "NONEXISTENT")
        assert inst is None


class TestInstitutionServiceGetAll:
    """Tests for get_all_institutions"""

    def test_get_all_active_only(self, db_session, test_institution):
        # Add an inactive institution
        inactive = Institution(
            id=uuid4(),
            code="INACTIVE_INST",
            name="Inactive",
            is_active=False,
        )
        db_session.add(inactive)
        db_session.commit()

        institutions = get_all_institutions(db_session, include_inactive=False)
        assert len(institutions) == 1
        assert institutions[0].code == "TEST_INST"

    def test_get_all_including_inactive(self, db_session, test_institution):
        inactive = Institution(
            id=uuid4(),
            code="INACTIVE_INST",
            name="Inactive",
            is_active=False,
        )
        db_session.add(inactive)
        db_session.commit()

        institutions = get_all_institutions(db_session, include_inactive=True)
        assert len(institutions) == 2


class TestInstitutionServiceCreate:
    """Tests for create_institution"""

    def test_create_institution(self, db_session):
        data = InstitutionCreate(
            code="NEW_INST",
            name="New Institution",
            description="A new institution",
        )
        inst = create_institution(db_session, data)
        assert inst.id is not None
        assert inst.code == "NEW_INST"
        assert inst.is_active is True


class TestInstitutionServiceUpdate:
    """Tests for update_institution"""

    def test_update_institution(self, db_session, test_institution):
        update_data = InstitutionUpdate(name="Updated Name", description="Updated desc")
        updated = update_institution(db_session, test_institution, update_data)
        assert updated.name == "Updated Name"
        assert updated.description == "Updated desc"
        assert updated.code == "TEST_INST"  # unchanged


class TestInstitutionServiceDelete:
    """Tests for delete_institution"""

    def test_soft_delete_institution(self, db_session, test_institution):
        result = delete_institution(db_session, test_institution, soft_delete=True)
        assert result is True
        db_session.refresh(test_institution)
        assert test_institution.is_active is False

    def test_hard_delete_institution(self, db_session):
        inst = Institution(
            id=uuid4(),
            code="HARD_DEL",
            name="Hard Delete",
            is_active=True,
        )
        db_session.add(inst)
        db_session.commit()
        inst_id = inst.id

        result = delete_institution(db_session, inst, soft_delete=False)
        assert result is True
        assert get_institution_by_id(db_session, inst_id) is None


# ==================== Route Tests ====================


class TestInstitutionRoutes:
    """Tests for institution API endpoints"""

    def test_list_institutions(self, authenticated_admin_client, test_institution):
        response = authenticated_admin_client.get("/api/v1/institutions/")
        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_list_institutions_with_inactive(self, authenticated_admin_client, db_session, test_institution):
        inactive = Institution(
            id=uuid4(),
            code="INACTIVE",
            name="Inactive",
            is_active=False,
        )
        db_session.add(inactive)
        db_session.commit()

        response = authenticated_admin_client.get(
            "/api/v1/institutions/?include_inactive=true"
        )
        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert len(data) == 2

    def test_create_institution(self, authenticated_admin_client):
        payload = {
            "code": "CREATED_INST",
            "name": "Created Institution",
            "description": "Created via API",
        }
        response = authenticated_admin_client.post("/api/v1/institutions/", json=payload)
        assert response.status_code == 201
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["code"] == "CREATED_INST"

    def test_create_institution_duplicate_code(self, authenticated_admin_client, test_institution):
        payload = {
            "code": "TEST_INST",
            "name": "Duplicate",
        }
        response = authenticated_admin_client.post("/api/v1/institutions/", json=payload)
        assert response.status_code == 400

    def test_get_institution_by_id(self, authenticated_admin_client, test_institution):
        inst_id = str(test_institution.id)
        response = authenticated_admin_client.get(f"/api/v1/institutions/{inst_id}")
        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["code"] == "TEST_INST"

    def test_get_institution_not_found(self, authenticated_admin_client):
        response = authenticated_admin_client.get(f"/api/v1/institutions/{uuid4()}")
        assert response.status_code == 404

    def test_update_institution(self, authenticated_admin_client, test_institution):
        payload = {"name": "Updated Via API"}
        response = authenticated_admin_client.put(
            f"/api/v1/institutions/{test_institution.id}", json=payload
        )
        assert response.status_code == 200
        json_data = response.json()
        data = json_data.get("data", json_data)
        assert data["name"] == "Updated Via API"

    def test_update_institution_duplicate_code(self, authenticated_admin_client, db_session, test_institution):
        other = Institution(
            id=uuid4(),
            code="OTHER_INST",
            name="Other",
            is_active=True,
        )
        db_session.add(other)
        db_session.commit()

        payload = {"code": "TEST_INST"}
        response = authenticated_admin_client.put(
            f"/api/v1/institutions/{other.id}", json=payload
        )
        assert response.status_code == 400

    def test_delete_institution(self, authenticated_admin_client, test_institution):
        response = authenticated_admin_client.delete(
            f"/api/v1/institutions/{test_institution.id}"
        )
        assert response.status_code == 200

    def test_delete_institution_not_found(self, authenticated_admin_client):
        response = authenticated_admin_client.delete(
            f"/api/v1/institutions/{uuid4()}"
        )
        assert response.status_code == 404
