from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.v1.config.database import get_db_sql
from api.v1.services.employee import List_employees_by_departmentId
from fastapi_pagination import Params


router = APIRouter(prefix="/empleados", tags=["empleados"])

@router.get("/{unidad_id}")
def get_employees_by_departmentId(
    unidad_id: int,
    params: Params = Depends(),
    db: Session = Depends(get_db_sql)
):
     return List_employees_by_departmentId(db, unidad_id, params)
