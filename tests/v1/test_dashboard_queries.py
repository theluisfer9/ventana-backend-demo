from api.v1.models.data_source import DataSource, RoleDataSource, SavedQuery
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
