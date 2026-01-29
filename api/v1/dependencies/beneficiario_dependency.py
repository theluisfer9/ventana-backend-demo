from fastapi import Query
from typing import Optional
from typing_extensions import Annotated

from api.v1.schemas.beneficiario import BeneficiarioFilters


def beneficiario_filters_dep(
    departamento_code: Annotated[
        Optional[str],
        Query(description="Filtrar por codigo de departamento"),
    ] = None,
    municipio_code: Annotated[
        Optional[str],
        Query(description="Filtrar por codigo de municipio"),
    ] = None,
    institucion_code: Annotated[
        Optional[str],
        Query(description="Filtrar por codigo de institucion"),
    ] = None,
    tipo_intervencion_code: Annotated[
        Optional[str],
        Query(description="Filtrar por tipo de intervencion"),
    ] = None,
    sin_intervencion: Annotated[
        Optional[bool],
        Query(description="Solo beneficiarios sin intervencion"),
    ] = None,
    genero: Annotated[
        Optional[str],
        Query(description="Filtrar por genero (M/F)"),
    ] = None,
    edad_min: Annotated[
        Optional[int],
        Query(description="Edad minima"),
    ] = None,
    edad_max: Annotated[
        Optional[int],
        Query(description="Edad maxima"),
    ] = None,
    miembros_hogar_min: Annotated[
        Optional[int],
        Query(description="Minimo de miembros del hogar"),
    ] = None,
    miembros_hogar_max: Annotated[
        Optional[int],
        Query(description="Maximo de miembros del hogar"),
    ] = None,
    con_menores_5: Annotated[
        Optional[bool],
        Query(description="Solo hogares con menores de 5 anios"),
    ] = None,
    con_adultos_mayores: Annotated[
        Optional[bool],
        Query(description="Solo hogares con adultos mayores"),
    ] = None,
    nivel_privacion: Annotated[
        Optional[str],
        Query(description="Nivel de privacion (extrema, alta, media, baja)"),
    ] = None,
    ipm_min: Annotated[
        Optional[float],
        Query(description="IPM minimo"),
    ] = None,
    ipm_max: Annotated[
        Optional[float],
        Query(description="IPM maximo"),
    ] = None,
    buscar: Annotated[
        Optional[str],
        Query(description="Buscar por nombre o DPI"),
    ] = None,
) -> BeneficiarioFilters:
    return BeneficiarioFilters(
        departamento_code=departamento_code,
        municipio_code=municipio_code,
        institucion_code=institucion_code,
        tipo_intervencion_code=tipo_intervencion_code,
        sin_intervencion=sin_intervencion,
        genero=genero,
        edad_min=edad_min,
        edad_max=edad_max,
        miembros_hogar_min=miembros_hogar_min,
        miembros_hogar_max=miembros_hogar_max,
        con_menores_5=con_menores_5,
        con_adultos_mayores=con_adultos_mayores,
        nivel_privacion=nivel_privacion,
        ipm_min=ipm_min,
        ipm_max=ipm_max,
        buscar=buscar,
    )
