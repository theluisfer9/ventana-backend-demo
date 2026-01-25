from typing import Callable, Sequence, Any, Tuple
from fastapi_pagination import Params, create_page
from fastapi_pagination.api import AbstractPage
from math import ceil

T = Any  

def run_sp_with_pagination(
    conn,
    sp_sql: str,
    sp_args: Tuple[Any, ...],
    mapper: Callable[[Sequence[Any]], T],
    params: Params
) -> AbstractPage:
   
    with conn.cursor() as cursor:
        cursor.execute(sp_sql, sp_args)
        
        # Primer result set
        rows = cursor.fetchall()
        items = [mapper(row) for row in rows]

        # Segundo result set: total
        total = 0
        if cursor.nextset():
            total_row = cursor.fetchone()
            if total_row and total_row[0] is not None:
                total = int(total_row[0])

    return create_page(items, total=total, params=params)
