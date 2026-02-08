from fastapi import Query
from typing import Optional
from typing_extensions import Annotated

from api.v1.schemas.beneficiario import BeneficiarioFilters


def beneficiario_filters_dep(
    departamento_codigo: Annotated[Optional[str], Query(description="Codigo de departamento")] = None,
    municipio_codigo: Annotated[Optional[str], Query(description="Codigo de municipio")] = None,
    lugar_poblado_codigo: Annotated[Optional[str], Query(description="Codigo de lugar poblado")] = None,
    area: Annotated[Optional[str], Query(description="Area (Urbano/Rural)")] = None,
    sexo_jefe: Annotated[Optional[str], Query(description="Sexo jefe hogar (M/F)")] = None,
    ipm_min: Annotated[Optional[float], Query(description="IPM minimo")] = None,
    ipm_max: Annotated[Optional[float], Query(description="IPM maximo")] = None,
    ipm_clasificacion: Annotated[Optional[str], Query(description="Clasificacion IPM")] = None,
    pmt_clasificacion: Annotated[Optional[str], Query(description="Clasificacion PMT")] = None,
    nbi_clasificacion: Annotated[Optional[str], Query(description="Clasificacion NBI")] = None,
    tiene_menores_5: Annotated[Optional[bool], Query(description="Hogares con menores de 5")] = None,
    tiene_adultos_mayores: Annotated[Optional[bool], Query(description="Hogares con adultos mayores")] = None,
    tiene_embarazadas: Annotated[Optional[bool], Query(description="Hogares con embarazadas")] = None,
    tiene_discapacidad: Annotated[Optional[bool], Query(description="Hogares con discapacidad")] = None,
    nivel_inseguridad: Annotated[Optional[str], Query(description="Nivel inseguridad alimentaria")] = None,
    buscar: Annotated[Optional[str], Query(description="Buscar por nombre o CUI")] = None,
    anio: Annotated[Optional[int], Query(description="Anio de captura")] = None,
    fase: Annotated[Optional[str], Query(description="Fase de intervencion")] = None,
) -> BeneficiarioFilters:
    return BeneficiarioFilters(
        departamento_codigo=departamento_codigo,
        municipio_codigo=municipio_codigo,
        lugar_poblado_codigo=lugar_poblado_codigo,
        area=area,
        sexo_jefe=sexo_jefe,
        ipm_min=ipm_min,
        ipm_max=ipm_max,
        ipm_clasificacion=ipm_clasificacion,
        pmt_clasificacion=pmt_clasificacion,
        nbi_clasificacion=nbi_clasificacion,
        tiene_menores_5=tiene_menores_5,
        tiene_adultos_mayores=tiene_adultos_mayores,
        tiene_embarazadas=tiene_embarazadas,
        tiene_discapacidad=tiene_discapacidad,
        nivel_inseguridad=nivel_inseguridad,
        buscar=buscar,
        anio=anio,
        fase=fase,
    )
