from sqlalchemy.orm import Session
from sqlalchemy import text
from api.v1.schemas.employee import EmployeeByDepartmentOut
from fastapi_pagination import Page, create_page, Params
from api.v1.utils.store_procedures import run_sp_with_pagination


def List_employees_by_departmentId(db: Session, unidad_id: int, params: Params):    
    conn = db.connection().connection  
    
    return run_sp_with_pagination(
        conn=conn,
        sp_sql="EXEC SARH.Sp_Get_EmpleadosPorUnidad ?, ?, ?",
        sp_args=(unidad_id, (params.page - 1) * params.size, params.size),
        mapper=lambda row: EmployeeByDepartmentOut(
            id_ficha=row[0],
            nombre=row[1],
            puesto=row[2],
            unidad=row[3],
        ),
        params=params
    ) 
