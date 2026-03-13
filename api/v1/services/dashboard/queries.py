"""Queries para el dashboard unificado (Admin + Institucional)."""
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from api.v1.models.user import User
from api.v1.models.institution import Institution
from api.v1.models.data_source import DataSource, SavedQuery


# ── PostgreSQL queries ───────────────────────────────────────────────

def query_system_stats(db: Session) -> dict:
    """Stats del sistema (instituciones, usuarios, consultas)."""
    total_inst = db.query(sa_func.count(Institution.id)).filter(Institution.is_active == True).scalar() or 0
    total_users = db.query(sa_func.count(User.id)).filter(User.is_active == True).scalar() or 0
    total_queries = db.query(sa_func.count(SavedQuery.id)).scalar() or 0

    # Usuarios y consultas por institucion
    users_by_inst = (
        db.query(
            Institution.name,
            Institution.code,
            sa_func.count(User.id).label("usuarios"),
        )
        .outerjoin(User, (User.institution_id == Institution.id) & (User.is_active == True))
        .filter(Institution.is_active == True)
        .group_by(Institution.id, Institution.name, Institution.code)
        .order_by(Institution.name)
        .all()
    )

    queries_by_inst = dict(
        db.query(
            SavedQuery.institution_id,
            sa_func.count(SavedQuery.id),
        )
        .filter(SavedQuery.institution_id.isnot(None))
        .group_by(SavedQuery.institution_id)
        .all()
    )

    # Map institution code -> institution id for queries count
    inst_id_map = dict(
        db.query(Institution.code, Institution.id)
        .filter(Institution.is_active == True)
        .all()
    )

    usuarios_por_inst = []
    for name, code, usuarios in users_by_inst:
        inst_id = inst_id_map.get(code)
        consultas = queries_by_inst.get(inst_id, 0) if inst_id else 0
        usuarios_por_inst.append({
            "institution": name,
            "code": code,
            "usuarios": usuarios,
            "consultas": consultas,
        })

    return {
        "total_instituciones": total_inst,
        "total_usuarios": total_users,
        "total_consultas_guardadas": total_queries,
        "usuarios_por_institucion": usuarios_por_inst,
    }


def query_institutional_pg_stats(db: Session, institution_id) -> dict:
    """Stats PG para una institucion especifica."""
    total_queries = (
        db.query(sa_func.count(SavedQuery.id))
        .filter(SavedQuery.institution_id == institution_id)
        .scalar() or 0
    )
    total_ds = (
        db.query(sa_func.count(DataSource.id))
        .filter(DataSource.institution_id == institution_id, DataSource.is_active == True)
        .scalar() or 0
    )
    return {"total_consultas": total_queries, "total_fuentes_datos": total_ds}


# ── ClickHouse queries ───────────────────────────────────────────────

def query_rsh_global_stats(client) -> dict:
    """Estadisticas globales RSH desde ClickHouse."""
    # Stats generales
    r = client.query("""
        SELECT
            count() as total_hogares,
            uniq(departamento_codigo) as deptos,
            uniq(municipio_codigo) as munis,
            uniq(lugarpoblado_codigo) as lugares,
            round(avg(ipm_gt), 4) as ipm_avg,
            round(avg(pmt), 4) as pmt_avg,
            round(avg(nbi), 4) as nbi_avg,
            sum(hombres) as total_hombres,
            sum(mujeres) as total_mujeres
        FROM rsh.vw_pobreza_hogars
    """)
    stats = dict(zip(r.column_names, r.result_rows[0]))

    # Total personas distintas por CUI
    r_personas = client.query("""
        SELECT count(DISTINCT pd4_numero_documento_identificacion) as total_personas
        FROM rsh.vw_beneficios_x_persona
    """)
    stats["total_personas"] = r_personas.result_rows[0][0]

    # Municipios finalizados vs en progreso
    r2 = client.query("""
        SELECT
            countIf(ultimo_estado = 'Finalizado') as finalizados,
            countIf(ultimo_estado = 'En Proceso') as en_progreso
        FROM (
            SELECT
                municipio_codigo,
                argMax(fase_estado, fecha) as ultimo_estado
            FROM rsh.vw_pobreza_hogars
            WHERE fase_estado != ''
            GROUP BY municipio_codigo
        )
    """)
    muni_stats = dict(zip(r2.column_names, r2.result_rows[0]))
    stats["municipios_finalizados"] = muni_stats.get("finalizados", 0)
    stats["municipios_en_progreso"] = muni_stats.get("en_progreso", 0)

    # Distribucion IPM
    r3 = client.query("""
        SELECT ipm_gt_clasificacion, count() as cantidad
        FROM rsh.vw_pobreza_hogars
        WHERE ipm_gt_clasificacion != ''
        GROUP BY ipm_gt_clasificacion
        ORDER BY cantidad DESC
    """)
    stats["por_ipm"] = [dict(zip(r3.column_names, row)) for row in r3.result_rows]

    # Distribucion NBI
    r3b = client.query("""
        SELECT nbi_clasificacion as clasificacion, count() as cantidad
        FROM rsh.vw_pobreza_hogars
        WHERE nbi_clasificacion != ''
        GROUP BY nbi_clasificacion
        ORDER BY cantidad DESC
    """)
    stats["por_nbi"] = [dict(zip(r3b.column_names, row)) for row in r3b.result_rows]

    # Distribucion PMT
    r3c = client.query("""
        SELECT pmt_clasificacion as clasificacion, count() as cantidad
        FROM rsh.vw_pobreza_hogars
        WHERE pmt_clasificacion != ''
        GROUP BY pmt_clasificacion
        ORDER BY cantidad DESC
    """)
    stats["por_pmt"] = [dict(zip(r3c.column_names, row)) for row in r3c.result_rows]

    # Pobreza por departamento (IPM / PMT / NBI) — una query por indice
    for field, key in [
        ("ipm_gt_clasificacion", "ipm_por_departamento"),
        ("pmt_clasificacion", "pmt_por_departamento"),
        ("nbi_clasificacion", "nbi_por_departamento"),
    ]:
        rp = client.query(f"""
            SELECT
                departamento,
                trim(departamento_codigo) as codigo,
                {field} as clasificacion,
                count() as cantidad
            FROM rsh.vw_pobreza_hogars
            WHERE {field} != ''
            GROUP BY departamento, departamento_codigo, {field}
            ORDER BY departamento, cantidad DESC
        """)
        stats[key] = [dict(zip(rp.column_names, row)) for row in rp.result_rows]

    # Por departamento
    r4 = client.query("""
        SELECT
            departamento,
            trim(departamento_codigo) as codigo,
            count() as cantidad
        FROM rsh.vw_pobreza_hogars
        GROUP BY departamento, departamento_codigo
        ORDER BY cantidad DESC
    """)
    stats["por_departamento"] = [dict(zip(r4.column_names, row)) for row in r4.result_rows]

    # Inseguridad alimentaria
    r5 = client.query("""
        SELECT
            nivel_inseguridad_alimentaria as nivel,
            count() as cantidad
        FROM rsh.vw_elcsa_hogar
        WHERE nivel_inseguridad_alimentaria != ''
        GROUP BY nivel_inseguridad_alimentaria
        ORDER BY cantidad DESC
    """)
    stats["inseguridad"] = [dict(zip(r5.column_names, row)) for row in r5.result_rows]

    # Potenciales beneficiarios por institucion (distinct personas por CUI)
    r6 = client.query("""
        SELECT
            uniqIf(p.pd4_numero_documento_identificacion, h.prog_fodes = 1) as FODES,
            uniqIf(p.pd4_numero_documento_identificacion, h.prog_maga = 1) as MAGA,
            uniqIf(p.pd4_numero_documento_identificacion,
                   h.prog_bono_social = 1 OR h.prog_bolsa_social = 1 OR h.prog_bono_unico = 1) as MIDES
        FROM rsh.vw_beneficios_x_persona AS p
        INNER JOIN rsh.vw_beneficios_x_hogar AS h ON p.hogar_id = h.hogar_id
    """)
    benef_row = dict(zip(r6.column_names, r6.result_rows[0]))
    stats["beneficiarios_por_institucion"] = benef_row

    return stats


def query_rsh_institutional_stats(client, base_filter_columns: list[str], base_filter_logic: str = "OR", intervention_columns: list[str] | None = None, departamento_codigo: str | None = None) -> dict:
    """Estadisticas RSH scoped a una institucion via base_filter_columns."""
    if not base_filter_columns:
        return {}

    conditions = [f"{col} = 1" for col in base_filter_columns]
    where = f" {base_filter_logic} ".join(conditions)
    if len(conditions) > 1:
        where = f"({where})"

    # Filtro opcional por departamento
    depto_filter = ""
    depto_params = {}
    if departamento_codigo:
        depto_filter = " AND trim(ig3_codigo_departamento) = {depto:String}"
        depto_params = {"depto": departamento_codigo}

    # Stats generales scoped
    r = client.query(f"""
        SELECT
            count() as total_hogares,
            uniq(ig3_codigo_departamento) as deptos,
            uniq(ig4_codigo_municipio) as munis,
            uniq(ig6_codigo_del_lugar_poblado) as lugares,
            round(avg(ipm_gt), 4) as ipm_avg,
            round(avg(pmt), 4) as pmt_avg,
            round(avg(nbi), 4) as nbi_avg,
            sum(hombres) as total_hombres,
            sum(mujeres) as total_mujeres
        FROM rsh.vw_beneficios_x_hogar
        WHERE {where}{depto_filter}
    """, parameters=depto_params)
    stats = dict(zip(r.column_names, r.result_rows[0]))

    # Total personas distintas por CUI
    r_personas = client.query(f"""
        SELECT count(DISTINCT p.pd4_numero_documento_identificacion) as total_personas
        FROM rsh.vw_beneficios_x_persona AS p
        INNER JOIN rsh.vw_beneficios_x_hogar AS h ON p.hogar_id = h.hogar_id
        WHERE {where}{depto_filter}
    """, parameters=depto_params)
    stats["total_personas"] = r_personas.result_rows[0][0]

    # Municipios estado - join con pobreza_hogars para fase_estado
    r2 = client.query(f"""
        SELECT
            countIf(ultimo_estado = 'Finalizado') as finalizados,
            countIf(ultimo_estado = 'En Proceso') as en_progreso
        FROM (
            SELECT
                b.ig4_codigo_municipio as municipio_codigo,
                argMax(p.fase_estado, p.fecha) as ultimo_estado
            FROM rsh.vw_beneficios_x_hogar AS b
            INNER JOIN rsh.vw_pobreza_hogars AS p ON b.hogar_id = p.hogar_id
            WHERE ({where}){depto_filter} AND p.fase_estado != ''
            GROUP BY municipio_codigo
        )
    """, parameters=depto_params)
    muni_stats = dict(zip(r2.column_names, r2.result_rows[0]))
    stats["municipios_finalizados"] = muni_stats.get("finalizados", 0)
    stats["municipios_en_progreso"] = muni_stats.get("en_progreso", 0)

    # IPM clasificacion
    r3 = client.query(f"""
        SELECT ipm_gt_clasificacion, count() as cantidad
        FROM rsh.vw_beneficios_x_hogar
        WHERE ({where}){depto_filter} AND ipm_gt_clasificacion != ''
        GROUP BY ipm_gt_clasificacion
        ORDER BY cantidad DESC
    """, parameters=depto_params)
    stats["por_ipm"] = [dict(zip(r3.column_names, row)) for row in r3.result_rows]

    # NBI clasificacion
    r3b = client.query(f"""
        SELECT nbi_clasificacion as clasificacion, count() as cantidad
        FROM rsh.vw_beneficios_x_hogar
        WHERE ({where}){depto_filter} AND nbi_clasificacion != ''
        GROUP BY nbi_clasificacion
        ORDER BY cantidad DESC
    """, parameters=depto_params)
    stats["por_nbi"] = [dict(zip(r3b.column_names, row)) for row in r3b.result_rows]

    # PMT clasificacion
    r3c = client.query(f"""
        SELECT pmt_clasificacion as clasificacion, count() as cantidad
        FROM rsh.vw_beneficios_x_hogar
        WHERE ({where}){depto_filter} AND pmt_clasificacion != ''
        GROUP BY pmt_clasificacion
        ORDER BY cantidad DESC
    """, parameters=depto_params)
    stats["por_pmt"] = [dict(zip(r3c.column_names, row)) for row in r3c.result_rows]

    # Pobreza por departamento (IPM / PMT / NBI) scoped
    for field, key in [
        ("ipm_gt_clasificacion", "ipm_por_departamento"),
        ("pmt_clasificacion", "pmt_por_departamento"),
        ("nbi_clasificacion", "nbi_por_departamento"),
    ]:
        rp = client.query(f"""
            SELECT
                ig3_departamento as departamento,
                trim(ig3_codigo_departamento) as codigo,
                {field} as clasificacion,
                count() as cantidad
            FROM rsh.vw_beneficios_x_hogar
            WHERE ({where}){depto_filter} AND {field} != ''
            GROUP BY ig3_departamento, ig3_codigo_departamento, {field}
            ORDER BY departamento, cantidad DESC
        """, parameters=depto_params)
        stats[key] = [dict(zip(rp.column_names, row)) for row in rp.result_rows]

    # Por departamento (siempre sin filtro de depto para que el front tenga la lista completa)
    r4 = client.query(f"""
        SELECT
            ig3_departamento as departamento,
            trim(ig3_codigo_departamento) as codigo,
            count() as cantidad
        FROM rsh.vw_beneficios_x_hogar
        WHERE {where}
        GROUP BY ig3_departamento, ig3_codigo_departamento
        ORDER BY cantidad DESC
    """)
    stats["por_departamento"] = [dict(zip(r4.column_names, row)) for row in r4.result_rows]

    # Inseguridad alimentaria scoped
    r5 = client.query(f"""
        SELECT
            i.nivel_inseguridad_alimentaria as nivel,
            count() as cantidad
        FROM rsh.vw_beneficios_x_hogar AS b
        INNER JOIN rsh.vw_elcsa_hogar AS i ON b.hogar_id = i.hogar_id
        WHERE ({where}){depto_filter} AND i.nivel_inseguridad_alimentaria != ''
        GROUP BY nivel
        ORDER BY cantidad DESC
    """, parameters=depto_params)
    stats["inseguridad"] = [dict(zip(r5.column_names, row)) for row in r5.result_rows]

    # Bonos e intervenciones scoped (solo columnas de la institucion)
    if intervention_columns:
        sums = ", ".join(f"sum({col}) as {col}" for col in intervention_columns)
        # Totales (con filtro de depto si aplica)
        r6 = client.query(f"""
            SELECT {sums}, sum(total_intervenciones) as total_intervenciones
            FROM rsh.vw_beneficios_x_hogar
            WHERE {where}{depto_filter}
        """, parameters=depto_params)
        stats["bonos"] = dict(zip(r6.column_names, r6.result_rows[0]))

        # Bonos por departamento (con filtro de depto si aplica)
        r7 = client.query(f"""
            SELECT
                ig3_departamento as departamento,
                trim(ig3_codigo_departamento) as codigo,
                {sums},
                sum(total_intervenciones) as total_intervenciones
            FROM rsh.vw_beneficios_x_hogar
            WHERE {where}{depto_filter}
            GROUP BY ig3_departamento, ig3_codigo_departamento
            ORDER BY total_intervenciones DESC
        """, parameters=depto_params)
        stats["bonos_por_departamento"] = [dict(zip(r7.column_names, row)) for row in r7.result_rows]

    return stats
