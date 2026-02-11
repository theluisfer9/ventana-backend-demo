"""Queries a ClickHouse para consulta institucional (beneficios_x_hogar)."""


def build_consulta_filters(
    base_filter: str, intervention_columns: list[str], **kwargs
) -> tuple[str, dict]:
    """
    Construye clausula WHERE combinando base_filter institucional + filtros del usuario.

    Returns:
        (where_clause, parameters)
    """
    conditions = [base_filter]
    params = {}

    if departamento := kwargs.get("departamento_codigo"):
        conditions.append("trim(ig3_departamento_codigo) = {depto:String}")
        params["depto"] = str(departamento).strip()

    if municipio := kwargs.get("municipio_codigo"):
        conditions.append("trim(ig4_municipio_codigo) = {muni:String}")
        params["muni"] = str(municipio).strip()

    if buscar := kwargs.get("buscar"):
        conditions.append("toString(hogar_id) ILIKE {buscar:String}")
        params["buscar"] = f"%{buscar}%"

    # Filtros de intervenciones (booleanos -> columna = 1)
    for col in intervention_columns:
        if kwargs.get(col):
            conditions.append(f"{col} = 1")

    where_clause = " AND ".join(conditions)
    return where_clause, params


def _build_select_columns(intervention_columns: list[str]) -> str:
    """Construye la lista de columnas SELECT incluyendo intervenciones dinamicas."""
    base = [
        "hogar_id",
        "ig3_departamento",
        "trim(ig3_departamento_codigo) as ig3_departamento_codigo",
        "ig4_municipio",
        "trim(ig4_municipio_codigo) as ig4_municipio_codigo",
        "ig5_lugar_poblado",
        "area",
        "numero_personas",
        "hombres",
        "mujeres",
        "ipm_gt",
        "ipm_gt_clasificacion",
    ]
    return ",\n            ".join(base + intervention_columns)


def query_consulta_lista(
    client,
    base_filter: str,
    intervention_columns: list[str],
    offset: int = 0,
    limit: int = 100,
    **filter_kwargs,
) -> tuple[list[dict], int]:
    """Lista paginada de hogares con base_filter + filtros usuario."""
    where_clause, params = build_consulta_filters(
        base_filter, intervention_columns, **filter_kwargs
    )

    count_query = f"""
        SELECT count() as total
        FROM rsh.beneficios_x_hogar
        WHERE {where_clause}
    """
    count_result = client.query(count_query, parameters=params)
    total = count_result.result_rows[0][0] if count_result.result_rows else 0

    params["offset"] = offset
    params["limit"] = limit

    select_cols = _build_select_columns(intervention_columns)

    data_query = f"""
        SELECT
            {select_cols}
        FROM rsh.beneficios_x_hogar
        WHERE {where_clause}
        ORDER BY ig3_departamento_codigo, ig4_municipio_codigo, hogar_id
        LIMIT {{limit:Int32}}
        OFFSET {{offset:Int32}}
    """

    data_result = client.query(data_query, parameters=params)
    rows = [
        dict(zip(data_result.column_names, row))
        for row in data_result.result_rows
    ]
    return rows, total


def query_consulta_detalle(
    client,
    base_filter: str,
    intervention_columns: list[str],
    hogar_id: int,
) -> dict | None:
    """Detalle de un hogar scoped al base_filter institucional."""
    select_cols = _build_select_columns(intervention_columns)

    query = f"""
        SELECT
            {select_cols}
        FROM rsh.beneficios_x_hogar
        WHERE {base_filter} AND hogar_id = {{hogar_id:Int64}}
        LIMIT 1
    """
    result = client.query(query, parameters={"hogar_id": hogar_id})
    if not result.result_rows:
        return None
    return dict(zip(result.column_names, result.result_rows[0]))


def query_consulta_dashboard(
    client, base_filter: str, intervention_columns: list[str]
) -> dict:
    """Estadisticas globales del dashboard institucional."""
    global_query = f"""
        SELECT
            count() as total_hogares,
            uniq(ig3_departamento_codigo) as total_departamentos,
            uniq(ig4_municipio_codigo) as total_municipios,
            sum(numero_personas) as total_personas
        FROM rsh.beneficios_x_hogar
        WHERE {base_filter}
    """
    global_result = client.query(global_query, parameters={})
    stats = dict(zip(global_result.column_names, global_result.result_rows[0]))

    # Top departamentos
    depto_query = f"""
        SELECT
            ig3_departamento as departamento,
            trim(ig3_departamento_codigo) as departamento_codigo,
            count() as cantidad_hogares
        FROM rsh.beneficios_x_hogar
        WHERE {base_filter}
        GROUP BY ig3_departamento, ig3_departamento_codigo
        ORDER BY cantidad_hogares DESC
        LIMIT 22
    """
    depto_result = client.query(depto_query, parameters={})
    top_departamentos = [
        dict(zip(depto_result.column_names, row))
        for row in depto_result.result_rows
    ]

    # Conteo por intervencion (dinamico)
    sumif_parts = ", ".join(
        f"sumIf(1, {col} = 1) as {col}" for col in intervention_columns
    )
    interv_query = f"""
        SELECT
            {sumif_parts}
        FROM rsh.beneficios_x_hogar
        WHERE {base_filter}
    """
    interv_result = client.query(interv_query, parameters={})
    interv_row = dict(zip(interv_result.column_names, interv_result.result_rows[0]))

    return {
        **stats,
        "top_departamentos": top_departamentos,
        "intervenciones": interv_row,
    }


def query_consulta_catalogos(client, base_filter: str) -> dict:
    """Obtiene valores DISTINCT de catalogos scoped al base_filter."""
    catalogos = {}

    depto_query = f"""
        SELECT DISTINCT
            trim(ig3_departamento_codigo) as codigo,
            ig3_departamento as nombre
        FROM rsh.beneficios_x_hogar
        WHERE {base_filter} AND ig3_departamento_codigo != ''
        ORDER BY codigo
    """
    depto_result = client.query(depto_query, parameters={})
    catalogos["departamentos"] = [
        {"codigo": row[0], "nombre": row[1]}
        for row in depto_result.result_rows
    ]

    return catalogos
