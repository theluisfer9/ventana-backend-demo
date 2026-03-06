from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.v1.config.database import get_sync_db_pg, get_ch_client
from api.v1.dependencies.auth_dependency import get_current_active_user
from api.v1.auth.permissions import PermissionCode
from api.v1.models.user import User
from api.v1.models.data_source import DataSource
from api.v1.schemas.dashboard import (
    AdminDashboardStats,
    InstitutionalDashboardStats,
    DepartamentoCount,
    ClasificacionCount,
    InseguridadCount,
    SexoCount,
    InstitutionUsersCount,
    InstitutionBeneficiariosCount,
)
from api.v1.services.dashboard.queries import (
    query_system_stats,
    query_rsh_global_stats,
    query_rsh_institutional_stats,
    query_institutional_pg_stats,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _is_admin(user: User) -> bool:
    if not user.role:
        return False
    user_permissions = {p.code for p in user.role.permissions}
    return PermissionCode.SYSTEM_CONFIG.value in user_permissions


def _get_user_base_filters(user: User, db: Session) -> tuple[list[str], str] | None:
    """Get base_filter_columns for user's institution from their datasources."""
    if not user.institution_id:
        return None
    ds = (
        db.query(DataSource)
        .filter(
            DataSource.institution_id == user.institution_id,
            DataSource.is_active == True,
        )
        .first()
    )
    if not ds or not ds.base_filter_columns:
        return None
    return ds.base_filter_columns, ds.base_filter_logic or "OR"


@router.get("/")
def get_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db_pg),
    client=Depends(get_ch_client),
):
    """
    Dashboard unificado. Devuelve datos segun el rol del usuario:
    - Super Admin: datos globales del sistema + RSH completo
    - Admin/Usuario Institucional: datos scoped a su institucion
    """
    if _is_admin(current_user):
        return _build_admin_dashboard(db, client)
    else:
        return _build_institutional_dashboard(current_user, db, client)


def _build_admin_dashboard(db: Session, client) -> AdminDashboardStats:
    """Dashboard para Super Admin."""
    # Stats del sistema (PG)
    sys_stats = query_system_stats(db)

    # Stats RSH (ClickHouse)
    rsh = query_rsh_global_stats(client)

    # Beneficiarios por institucion
    benef_map = rsh.get("beneficiarios_por_institucion", {})
    benef_por_inst = [
        InstitutionBeneficiariosCount(
            institution=name,
            code=code,
            potenciales_beneficiarios=benef_map.get(code, 0),
        )
        for code, name in [
            ("FODES", "FODES"),
            ("MAGA", "MAGA"),
            ("MIDES", "MIDES"),
        ]
    ]

    return AdminDashboardStats(
        # Sistema
        total_instituciones=sys_stats["total_instituciones"],
        total_usuarios=sys_stats["total_usuarios"],
        total_consultas_guardadas=sys_stats["total_consultas_guardadas"],
        usuarios_por_institucion=[
            InstitutionUsersCount(**u) for u in sys_stats["usuarios_por_institucion"]
        ],
        beneficiarios_por_institucion=benef_por_inst,
        # RSH general
        total_hogares=rsh.get("total_hogares", 0),
        total_personas=rsh.get("total_personas", 0),
        departamentos_cubiertos=rsh.get("deptos", 0),
        municipios_cubiertos=rsh.get("munis", 0),
        lugares_poblados=rsh.get("lugares", 0),
        # Municipios estado
        municipios_finalizados=rsh.get("municipios_finalizados", 0),
        municipios_en_progreso=rsh.get("municipios_en_progreso", 0),
        # Pobreza
        promedio_ipm=float(rsh.get("ipm_avg", 0) or 0),
        por_ipm_clasificacion=[
            ClasificacionCount(clasificacion=r["ipm_gt_clasificacion"], cantidad=r["cantidad"])
            for r in rsh.get("por_ipm", [])
        ],
        # Sexo
        personas_por_sexo=[
            SexoCount(sexo="Hombres", cantidad=rsh.get("total_hombres", 0)),
            SexoCount(sexo="Mujeres", cantidad=rsh.get("total_mujeres", 0)),
        ],
        # Geografico
        por_departamento=[
            DepartamentoCount(departamento=d["departamento"], codigo=d["codigo"], cantidad=d["cantidad"])
            for d in rsh.get("por_departamento", [])
        ],
        # Inseguridad
        inseguridad_alimentaria=[
            InseguridadCount(nivel=i["nivel"], cantidad=i["cantidad"])
            for i in rsh.get("inseguridad", [])
        ],
    )


def _build_institutional_dashboard(user: User, db: Session, client) -> InstitutionalDashboardStats:
    """Dashboard para Admin Institucional o Usuario Institucional."""
    institution = user.institution
    inst_name = institution.name if institution else ""
    inst_code = institution.code if institution else ""

    # Stats PG
    pg_stats = query_institutional_pg_stats(db, user.institution_id) if user.institution_id else {}

    # Stats RSH scoped
    base_filters = _get_user_base_filters(user, db)
    if base_filters:
        rsh = query_rsh_institutional_stats(client, base_filters[0], base_filters[1])
    else:
        rsh = {}

    return InstitutionalDashboardStats(
        institution_name=inst_name,
        institution_code=inst_code,
        # RSH scoped
        total_hogares=rsh.get("total_hogares", 0),
        total_personas=rsh.get("total_personas", 0),
        departamentos_cubiertos=rsh.get("deptos", 0),
        municipios_cubiertos=rsh.get("munis", 0),
        lugares_poblados=rsh.get("lugares", 0),
        # Municipios estado
        municipios_finalizados=rsh.get("municipios_finalizados", 0),
        municipios_en_progreso=rsh.get("municipios_en_progreso", 0),
        # Pobreza
        promedio_ipm=float(rsh.get("ipm_avg", 0) or 0),
        por_ipm_clasificacion=[
            ClasificacionCount(clasificacion=r["ipm_gt_clasificacion"], cantidad=r["cantidad"])
            for r in rsh.get("por_ipm", [])
        ],
        # Sexo
        personas_por_sexo=[
            SexoCount(sexo="Hombres", cantidad=rsh.get("total_hombres", 0)),
            SexoCount(sexo="Mujeres", cantidad=rsh.get("total_mujeres", 0)),
        ],
        # Geografico
        por_departamento=[
            DepartamentoCount(departamento=d["departamento"], codigo=d["codigo"], cantidad=d["cantidad"])
            for d in rsh.get("por_departamento", [])
        ],
        # Inseguridad
        inseguridad_alimentaria=[
            InseguridadCount(nivel=i["nivel"], cantidad=i["cantidad"])
            for i in rsh.get("inseguridad", [])
        ],
        # PG stats
        total_consultas=pg_stats.get("total_consultas", 0),
        total_fuentes_datos=pg_stats.get("total_fuentes_datos", 0),
    )
