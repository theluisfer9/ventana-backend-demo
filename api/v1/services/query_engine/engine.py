from api.v1.models.data_source import DataSource, DataSourceColumn

_CH_TYPE_MAP = {
    "TEXT": "String",
    "INTEGER": "Int64",
    "FLOAT": "Float64",
    "BOOLEAN": "Int32",
}

_OP_MAP = {
    "eq": "=",
    "neq": "!=",
    "gt": ">",
    "lt": "<",
    "gte": ">=",
    "lte": "<=",
    "like": "ILIKE",
}

_AGG_ALIAS = {
    "COUNT": "count",
    "SUM": "sum",
}


def build_select(columns: list[DataSourceColumn]) -> str:
    return ", ".join(c.column_name for c in columns)


def build_select_grouped(
    group_columns: list[DataSourceColumn],
    aggregations: list[dict],
) -> str:
    parts = [c.column_name for c in group_columns]
    for agg in aggregations:
        func = agg["function"].upper()
        col = agg["column"]
        if col == "*":
            parts.append(f"{func}(*) AS {_AGG_ALIAS.get(func, func.lower())}")
        else:
            alias = f"{_AGG_ALIAS.get(func, func.lower())}_{col}"
            parts.append(f"{func}({col}) AS {alias}")
    return ", ".join(parts)


def build_group_by(group_column_names: list[str]) -> str:
    return ", ".join(group_column_names)


def build_where(
    base_filter: str | None,
    filters: list[dict],
    columns_map: dict[str, DataSourceColumn],
) -> tuple[str, dict]:
    conditions = []
    params = {}

    if base_filter:
        conditions.append(base_filter)

    for i, f in enumerate(filters):
        col_name = f["column"]
        op = f["op"]
        value = f["value"]
        col_def = columns_map[col_name]
        ch_type = _CH_TYPE_MAP.get(col_def.data_type.value if hasattr(col_def.data_type, 'value') else col_def.data_type, "String")
        param_name = f"p_{i}"

        if op == "in":
            if isinstance(value, list):
                placeholders = ", ".join(
                    f"{{{param_name}_{j}:{ch_type}}}" for j in range(len(value))
                )
                conditions.append(f"{col_name} IN ({placeholders})")
                for j, v in enumerate(value):
                    params[f"{param_name}_{j}"] = v
            continue

        if op == "like":
            conditions.append(f"{col_name} ILIKE {{{param_name}:String}}")
            params[param_name] = f"%{value}%"
            continue

        sql_op = _OP_MAP.get(op, "=")
        conditions.append(f"{col_name} {sql_op} {{{param_name}:{ch_type}}}")
        params[param_name] = value

    where = " AND ".join(conditions) if conditions else "1=1"
    return where, params


def execute_query(
    client,
    ds: DataSource,
    columns: list[DataSourceColumn],
    filters: list[dict],
    offset: int,
    limit: int,
    group_by: list[str] | None = None,
    aggregations: list[dict] | None = None,
) -> tuple[list[dict], int]:
    col_map = {c.column_name: c for c in ds.columns_def}
    where_clause, params = build_where(ds.base_filter, filters, col_map)

    if group_by and aggregations:
        # Grouped query
        group_cols = [col_map[name] for name in group_by if name in col_map]
        select_clause = build_select_grouped(group_cols, aggregations)
        group_clause = build_group_by(group_by)

        count_sql = (
            f"SELECT count() FROM ("
            f"SELECT {group_clause} FROM {ds.ch_table} "
            f"WHERE {where_clause} GROUP BY {group_clause}"
            f") AS sub"
        )
        count_result = client.query(count_sql, parameters=params)
        total = count_result.result_rows[0][0]

        params["_offset"] = offset
        params["_limit"] = limit
        order_col = group_by[0]
        data_sql = (
            f"SELECT {select_clause} FROM {ds.ch_table} "
            f"WHERE {where_clause} "
            f"GROUP BY {group_clause} "
            f"ORDER BY {order_col} "
            f"LIMIT {{_limit:Int32}} OFFSET {{_offset:Int32}}"
        )
    else:
        # Non-grouped query (existing behavior)
        select_clause = build_select(columns)

        count_sql = f"SELECT count() FROM {ds.ch_table} WHERE {where_clause}"
        count_result = client.query(count_sql, parameters=params)
        total = count_result.result_rows[0][0]

        params["_offset"] = offset
        params["_limit"] = limit
        order_col = columns[0].column_name
        data_sql = (
            f"SELECT {select_clause} FROM {ds.ch_table} "
            f"WHERE {where_clause} "
            f"ORDER BY {order_col} "
            f"LIMIT {{_limit:Int32}} OFFSET {{_offset:Int32}}"
        )

    data_result = client.query(data_sql, parameters=params)
    rows = [
        dict(zip(data_result.column_names, row))
        for row in data_result.result_rows
    ]

    return rows, total
