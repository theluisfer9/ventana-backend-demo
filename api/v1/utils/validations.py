from fastapi.exceptions import RequestValidationError

def get_custom_validation_message(exc: RequestValidationError) -> str | None:
    for error in exc.errors():
        loc = error.get("loc")
        err_type = error.get("type")

        if loc == ("query", "size") and err_type == "less_than_equal":
            return "No se permiten más de 100 registros por página."

        # Puedes agregar otras reglas aquí
        
    return None
