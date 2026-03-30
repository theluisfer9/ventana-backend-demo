from uuid import uuid4

from api.v1.models.data_source import DataSource, RoleDataSource, SavedQuery
from api.v1.models.institution import Institution
from api.v1.models.user import User
from api.v1.routes.dashboard_routes import (
    _build_admin_dashboard,
    _build_institutional_dashboard,
    _get_user_base_filters,
)
from api.v1.services.dashboard.queries import query_institutional_pg_stats


def test_query_institutional_pg_stats_uses_creator_institution_and_role_datasources(
    db_session,
    test_regular_user,
):
    datasource = DataSource(
        code="DASHBOARD_ROLE_DS",
        name="Dashboard Role DS",
        ch_table="rsh.test_table",
        base_filter_columns=["prog_test"],
        base_filter_logic="OR",
        is_active=True,
    )
    db_session.add(datasource)
    db_session.flush()

    db_session.add(
        RoleDataSource(
            role_id=test_regular_user.role_id,
            datasource_id=datasource.id,
        )
    )
    db_session.add(
        SavedQuery(
            user_id=test_regular_user.id,
            datasource_id=datasource.id,
            name="Dashboard Query",
            selected_columns=["hogar_id"],
            filters=[],
            group_by=[],
            aggregations=[],
            agrupar=True,
        )
    )
    db_session.commit()

    stats = query_institutional_pg_stats(
        db_session,
        test_regular_user.institution_id,
    )

    assert stats == {
        "total_consultas": 1,
        "total_fuentes_datos": 1,
    }


def test_get_user_base_filters_prefers_institutional_preset_over_role_datasource(
    db_session,
    test_roles,
):
    institution = Institution(
        id=uuid4(),
        code="MIDES",
        name="Ministerio de Desarrollo Social",
        description="Institution for MIDES dashboard",
        is_active=True,
    )
    db_session.add(institution)
    db_session.flush()

    user = User(
        id=uuid4(),
        email="mides@test.com",
        username="mides_user",
        first_name="Mides",
        last_name="User",
        role_id=test_roles["analyst"].id,
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.flush()

    legacy_datasource = DataSource(
        code="MIDES_LEGACY",
        name="MIDES Legacy",
        ch_table="rsh.vw_beneficios_x_hogar",
        base_filter_columns=["prog_mides"],
        base_filter_logic="AND",
        is_active=True,
    )
    db_session.add(legacy_datasource)
    db_session.flush()

    db_session.add(
        RoleDataSource(
            role_id=user.role_id,
            datasource_id=legacy_datasource.id,
        )
    )
    db_session.commit()

    assert _get_user_base_filters(user, db_session) == (
        ["prog_bono_social", "prog_bolsa_social", "prog_bono_unico"],
        "OR",
        ["bono_unico", "bono_salud", "bono_educacion", "bolsa_social"],
    )


def test_get_user_base_filters_returns_none_without_institutional_preset(
    db_session,
    test_regular_user,
):
    legacy_datasource = DataSource(
        code="NO_PRESET_LEGACY",
        name="No Preset Legacy",
        ch_table="rsh.vw_beneficios_x_hogar",
        base_filter_columns=["prog_mides"],
        base_filter_logic="AND",
        is_active=True,
    )
    db_session.add(legacy_datasource)
    db_session.flush()

    db_session.add(
        RoleDataSource(
            role_id=test_regular_user.role_id,
            datasource_id=legacy_datasource.id,
        )
    )
    db_session.commit()

    assert _get_user_base_filters(test_regular_user, db_session) is None


def test_build_admin_dashboard_exposes_flat_demographic_totals(
    db_session,
    mock_ch,
):
    dashboard = _build_admin_dashboard(db_session, mock_ch)

    assert dashboard.total_personas_stats == dashboard.total_personas
    assert dashboard.total_hombres > 0
    assert dashboard.total_mujeres > 0


def test_build_institutional_dashboard_exposes_flat_demographic_totals(
    db_session,
    test_roles,
    mock_ch,
):
    institution = Institution(
        id=uuid4(),
        code="MIDES",
        name="Ministerio de Desarrollo Social",
        description="Institution for MIDES dashboard",
        is_active=True,
    )
    db_session.add(institution)
    db_session.flush()

    user = User(
        id=uuid4(),
        email="mides@test.com",
        username="mides_user",
        first_name="Mides",
        last_name="User",
        role_id=test_roles["analyst"].id,
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    dashboard = _build_institutional_dashboard(user, db_session, mock_ch)

    assert dashboard.total_personas_stats == dashboard.total_personas
    assert dashboard.total_hombres > 0
    assert dashboard.total_mujeres > 0
