from pydantic import BaseModel

class EmployeeByDepartmentOut(BaseModel):
    id_ficha: int
    nombre: str
    puesto: str
    unidad: str
