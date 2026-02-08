from pydantic import BaseModel


class ViviendaDetalle(BaseModel):
    """Detalle de vivienda y hogar con servicios, bienes y seguridad alimentaria."""
    # Vivienda (entrevistas_viviendas)
    condicion_vivienda: str = ""
    tipo_vivienda: str = ""
    material_paredes: str = ""
    material_techo: str = ""
    material_piso: str = ""
    tenencia: str = ""
    propietario: str = ""
    # Hogar (entrevista_hogares)
    personas_habituales: int = 0
    personas_hogar: int = 0
    hombres: int = 0
    mujeres: int = 0
    ninos: int = 0
    ninas: int = 0
    cuartos: int = 0
    dormitorios: int = 0
    cocina_exclusiva: str = ""
    combustible_cocina: str = ""
    usa_lenia: str = ""
    lugar_cocina: str = ""
    chimenea: str = ""
    fuente_agua: str = ""
    dias_sin_agua: int = 0
    tratamiento_agua: str = ""
    tipo_sanitario: str = ""
    uso_sanitario: str = ""
    aguas_grises: str = ""
    alumbrado: str = ""
    dias_sin_electricidad: int = 0
    eliminacion_basura: str = ""
    # Bienes
    radio: str = ""
    estufa_lenia: str = ""
    estufa_gas: str = ""
    televisor: str = ""
    refrigerador: str = ""
    lavadora: str = ""
    computadora: str = ""
    internet: str = ""
    moto: str = ""
    carro: str = ""
    # Seguridad alimentaria ELCSA
    preocupacion_alimentos: str = ""
    sin_alimentos: str = ""
    adulto_sin_alimentacion_saludable: str = ""
    nino_sin_alimentacion_saludable: str = ""
    adulto_sin_variedad: str = ""
    nino_sin_variedad: str = ""
    adulto_sin_tiempo_comida: str = ""
    nino_sin_tiempo_comida: str = ""
    adulto_comio_menos: str = ""
    nino_comio_menos: str = ""
    adulto_sintio_hambre: str = ""
    nino_sintio_hambre: str = ""
    adulto_comio_una_vez: str = ""
    nino_comio_una_vez: str = ""
