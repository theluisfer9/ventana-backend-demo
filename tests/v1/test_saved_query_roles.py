from uuid import uuid4

from api.v1.models.data_source import DataSource, SavedQuery, SavedQueryRole
from api.v1.models.role import Role


def test_saved_query_can_store_multiple_roles(db_session, test_admin_user):
    datasource = DataSource(
        code="ROLE_QUERY_DS",
        name="Role Query DS",
        ch_table="rsh.role_query_ds",
        base_filter_columns=[],
        base_filter_logic="OR",
        is_active=True,
    )
    db_session.add(datasource)
    db_session.flush()

    analyst_role = db_session.query(Role).filter(Role.code == "ANALYST").one()
    supervisor_role = Role(
        id=uuid4(),
        code="SUPERVISOR",
        name="Supervisor",
        description="Supervisor role for query assignment tests",
        is_system=False,
    )
    db_session.add(supervisor_role)
    db_session.flush()

    saved_query = SavedQuery(
        user_id=test_admin_user.id,
        datasource_id=datasource.id,
        name="Consulta por rol",
        selected_columns=["hogar_id"],
        filters=[],
        group_by=[],
        aggregations=[],
        agrupar=True,
    )
    db_session.add(saved_query)
    db_session.flush()

    db_session.add_all(
        [
            SavedQueryRole(saved_query_id=saved_query.id, role_id=analyst_role.id),
            SavedQueryRole(saved_query_id=saved_query.id, role_id=supervisor_role.id),
        ]
    )
    db_session.commit()
    db_session.refresh(saved_query)

    assert {role.code for role in saved_query.roles} == {"ANALYST", "SUPERVISOR"}
