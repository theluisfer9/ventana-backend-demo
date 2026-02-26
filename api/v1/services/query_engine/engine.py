import re

from api.v1.models.data_source import DataSource, DataSourceColumn

_CH_TYPE_MAP = {
    "TEXT": "String",
    "INTEGER": "Int64",
    "FLOAT": "Float64",
    "BOOLEAN": "Int8",
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

# ClickHouse identifiers: letters, digits, underscores, dots (for schema.table)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _safe_identifier(name: str) -> str:
    """Validate that a string is a safe SQL identifier. Raises ValueError if not."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Identificador SQL no válido: {name!r}")
    return name


def build_where_from_columns(columns: list[str], logic: str) -> str | None:
    """Build a WHERE clause fragment from structured base_filter_columns.

    Each column becomes `column = 1`. Multiple columns are joined with logic (AND/OR).
    Returns None if columns is empty.
    """
    if not columns:
        return None
    parts = [f"{_safe_identifier(col)} = 1" for col in columns]
    if len(parts) == 1:
        return parts[0]
    joiner = f" {logic.upper()} "
    return f"({joiner.join(parts)})"


def build_select(columns: list[DataSourceColumn]) -> str:
    return ", ".join(_safe_identifier(c.column_name) for c in columns)


def build_select_grouped(
    group_columns: list[DataSourceColumn],
    aggregations: list[dict],
) -> str:
    parts = [_safe_identifier(c.column_name) for c in group_columns]
    for agg in aggregations:
        func = agg["function"].upper()
        col = agg["column"]
        if col == "*":
            alias = _safe_identifier(_AGG_ALIAS.get(func, func.lower()))
            parts.append(f"{func}(*) AS {alias}")
        else:
            safe_col = _safe_identifier(col)
            alias = _safe_identifier(f"{_AGG_ALIAS.get(func, func.lower())}_{col}")
            parts.append(f"{func}({safe_col}) AS {alias}")
    return ", ".join(parts)


def build_group_by(group_column_names: list[str]) -> str:
    return ", ".join(_safe_identifier(name) for name in group_column_names)


def build_where(
    base_filter_columns: list[str] | None,
    base_filter_logic: str | None,
    filters: list[dict],
    columns_map: dict[str, DataSourceColumn],
) -> tuple[str, dict]:
    conditions = []
    params = {}

    if base_filter_columns:
        base_clause = build_where_from_columns(base_filter_columns, base_filter_logic or "OR")
        if base_clause:
            conditions.append(base_clause)

    for i, f in enumerate(filters):
        col_name = _safe_identifier(f["column"])
        op = f["op"]
        value = f["value"]
        col_def = columns_map[f["column"]]
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
    table_name = _safe_identifier(ds.ch_table)
    where_clause, params = build_where(
        ds.base_filter_columns, ds.base_filter_logic, filters, col_map
    )

    if group_by and aggregations:
        # Grouped query
        group_cols = [col_map[name] for name in group_by if name in col_map]
        select_clause = build_select_grouped(group_cols, aggregations)
        group_clause = build_group_by(group_by)

        count_sql = (
            f"SELECT count() FROM ("
            f"SELECT {group_clause} FROM {table_name} "
            f"WHERE {where_clause} GROUP BY {group_clause}"
            f") AS sub"
        )
        count_result = client.query(count_sql, parameters=params)
        total = count_result.result_rows[0][0]

        params["_offset"] = offset
        params["_limit"] = limit
        order_col = _safe_identifier(group_by[0])
        data_sql = (
            f"SELECT {select_clause} FROM {table_name} "
            f"WHERE {where_clause} "
            f"GROUP BY {group_clause} "
            f"ORDER BY {order_col} "
            f"LIMIT {{_limit:Int32}} OFFSET {{_offset:Int32}}"
        )
    else:
        # Non-grouped query (existing behavior)
        select_clause = build_select(columns)

        count_sql = f"SELECT count() FROM {table_name} WHERE {where_clause}"
        count_result = client.query(count_sql, parameters=params)
        total = count_result.result_rows[0][0]

        params["_offset"] = offset
        params["_limit"] = limit
        order_col = _safe_identifier(columns[0].column_name)
        data_sql = (
            f"SELECT {select_clause} FROM {table_name} "
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
