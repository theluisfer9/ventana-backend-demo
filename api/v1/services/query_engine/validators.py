from fastapi import HTTPException, status
from api.v1.models.data_source import DataSourceColumn


def validate_columns(
    requested: list[str],
    available: list[DataSourceColumn],
    check_selectable: bool = True,
) -> list[DataSourceColumn]:
    """Validate requested columns exist and are selectable. Returns matched DataSourceColumn objects."""
    col_map = {c.column_name: c for c in available}
    validated = []
    for col_name in requested:
        col = col_map.get(col_name)
        if not col:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Columna no disponible: {col_name}",
            )
        if check_selectable and not col.is_selectable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Columna no seleccionable: {col_name}",
            )
        validated.append(col)
    return validated


def validate_filters(
    filters: list[dict],
    available: list[DataSourceColumn],
) -> None:
    """Validate filter columns exist and are filterable."""
    col_map = {c.column_name: c for c in available}
    for f in filters:
        col = col_map.get(f["column"])
        if not col:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Columna de filtro no disponible: {f['column']}",
            )
        if not col.is_filterable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Columna no filtrable: {f['column']}",
            )


def validate_group_by(
    requested: list[str],
    available: list[DataSourceColumn],
) -> list[DataSourceColumn]:
    """Validate requested group-by columns exist and are groupable."""
    col_map = {c.column_name: c for c in available}
    validated = []
    for col_name in requested:
        col = col_map.get(col_name)
        if not col:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Columna de agrupación no disponible: {col_name}",
            )
        if not col.is_groupable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Columna no agrupable: {col_name}",
            )
        validated.append(col)
    return validated
