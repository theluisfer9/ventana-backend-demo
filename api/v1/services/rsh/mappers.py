"""Mapea filas ClickHouse a diccionarios de beneficiario."""
from decimal import Decimal


def _safe_float(val) -> float:
    """Convierte Decimal/None a float."""
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


def _safe_str(val) -> str:
    """Limpia strings de ClickHouse (trim FixedString)."""
    if val is None:
        return ""
    return str(val).strip()


def row_to_beneficiario_resumen(row: dict) -> dict:
    """Convierte una fila del query principal a formato resumen."""
    return {
        "hogar_id": row["hogar_id"],
        "cui_jefe_hogar": row.get("cui_jefe_hogar"),
        "nombre_completo": _safe_str(row.get("nombre_jefe_hogar")),
        "sexo_jefe_hogar": _safe_str(row.get("sexo_jefe_hogar")),
        "departamento": _safe_str(row.get("departamento")),
        "departamento_codigo": _safe_str(row.get("departamento_codigo")),
        "municipio": _safe_str(row.get("municipio")),
        "municipio_codigo": _safe_str(row.get("municipio_codigo")),
        "lugar_poblado": _safe_str(row.get("lugar_poblado")),
        "area": _safe_str(row.get("area")),
        "numero_personas": row.get("numero_personas", 0) or 0,
        "hombres": row.get("hombres", 0) or 0,
        "mujeres": row.get("mujeres", 0) or 0,
        "ipm_gt": _safe_float(row.get("ipm_gt")),
        "ipm_gt_clasificacion": _safe_str(row.get("ipm_gt_clasificacion")),
        "pmt": _safe_float(row.get("pmt")),
        "pmt_clasificacion": _safe_str(row.get("pmt_clasificacion")),
        "nbi": _safe_float(row.get("nbi")),
        "nbi_clasificacion": _safe_str(row.get("nbi_clasificacion")),
    }


def row_to_beneficiario_detalle(row: dict) -> dict:
    """Convierte fila con JOINs a formato detalle completo."""
    base = row_to_beneficiario_resumen(row)
    base.update({
        "latitud": row.get("geolocalizacion_vivienda_latitud"),
        "longitud": row.get("geolocalizacion_vivienda_longitud"),
        "direccion": _safe_str(row.get("direccion_vivienda")),
        "celular_jefe": row.get("celular_jefe_hogar"),
        "cui_madre": row.get("cui_madre"),
        "nombre_madre": _safe_str(row.get("nombre_madre")),
        "fase": _safe_str(row.get("fase")),
        "fase_estado": _safe_str(row.get("fase_estado")),
        "anio": int(row["anio"]) if row.get("anio") else None,
        # Demograficos (de JOIN con hogares_datos_demograficos)
        "total_personas": row.get("total_personas"),
        "menores_5": row.get("p_0_5"),
        "adultos_mayores": row.get("adultos_mayores"),
        "personas_embarazadas": row.get("personas_embarazadas"),
        "personas_con_dificultad": row.get("personas_con_dificultad"),
        "tipo_jefatura": _safe_str(row.get("tipo_jefatura")),
        "comunidad_linguistica": _safe_str(row.get("comunidad_linguistica")),
        "pueblo_de_pertenencia": _safe_str(row.get("pueblo_de_pertenencia")),
        # Inseguridad alimentaria (de JOIN con hogares_inseguridad_alimentaria)
        "nivel_inseguridad_alimentaria": _safe_str(row.get("nivel_inseguridad_alimentaria")),
        "puntos_elcsa": row.get("puntos_elcsa"),
        # Conteos por grupo etario
        "primera_infancia": row.get("primera_infancia"),
        "ninos": row.get("ninos"),
        "adolescentes": row.get("adolescentes"),
        "jovenes": row.get("jovenes"),
        "adultos": row.get("adultos"),
    })
    return base


def _safe_date(val) -> str:
    """Convierte fecha a string ISO."""
    if val is None:
        return ""
    return val.isoformat() if hasattr(val, "isoformat") else str(val)


def row_to_persona(row: dict) -> dict:
    """Convierte fila de entrevista_personas a formato PersonaResumen."""
    partes_nombre = [
        _safe_str(row.get("pd5_1_primer_nombre")),
        _safe_str(row.get("pd5_2_segundo_nombre")),
        _safe_str(row.get("pd5_3_tercer_nombre")),
        _safe_str(row.get("pd5_4_cuarto_nombre")),
        _safe_str(row.get("pd5_5_primer_apellido")),
        _safe_str(row.get("pd5_6_segundo_apellido")),
        _safe_str(row.get("pd5_7_apellido_casada")),
    ]
    nombre_completo = " ".join(p for p in partes_nombre if p)

    return {
        "personas_id": row["personas_id"],
        "correlativo": int(row.get("pd1_numero_correlativo_persona_hogar") or 0),
        "cui": row.get("pd4_numero_documento_identificacion"),
        "nombre_completo": nombre_completo,
        "genero": _safe_str(row.get("pd6_descripcion")),
        "fecha_nacimiento": _safe_date(row.get("pd7_fecha_nacimiento")),
        "edad": int(row.get("pd8_anios_cumplidos") or 0),
        "estado_civil": _safe_str(row.get("pd9_descripcion")),
        "celular": row.get("pd10_celular"),
        "parentesco": _safe_str(row.get("pd11_descripcion")),
        "pueblo": _safe_str(row.get("pd12_descripcion")),
        "comunidad_linguistica": _safe_str(row.get("pd13_descripcion")),
        "idioma_materno": _safe_str(row.get("pd14_descripcion")),
        "dificultad_ver": _safe_str(row.get("ps1_1_descripcion")),
        "dificultad_oir": _safe_str(row.get("ps1_2_descripcion")),
        "dificultad_caminar": _safe_str(row.get("ps1_3_descripcion")),
        "dificultad_recordar": _safe_str(row.get("ps1_4_descripcion")),
        "dificultad_cuidado_personal": _safe_str(row.get("ps1_5_descripcion")),
        "dificultad_entender": _safe_str(row.get("ps1_6_descripcion")),
        "embarazada": _safe_str(row.get("ps13_descripcion")),
        "sabe_leer_escribir": _safe_str(row.get("pe1_descripcion")),
        "inscrito_escuela": _safe_str(row.get("pe2_descripcion")),
        "nivel_educativo": _safe_str(row.get("pe7_descripcion")),
        "actividad_principal": _safe_str(row.get("ie1_descripcion")),
        "tiene_ingreso": _safe_str(row.get("ie3_descripcion")),
    }


def row_to_vivienda(row: dict) -> dict:
    """Convierte fila de vivienda/hogar a formato detalle."""
    return {
        # Vivienda
        "condicion_vivienda": _safe_str(row.get("cv1_condicion_vivienda")),
        "tipo_vivienda": _safe_str(row.get("cv2_tipo_vivienda_particular")),
        "material_paredes": _safe_str(row.get("cv3_material_predominante_en_paredes_exteriores")),
        "material_techo": _safe_str(row.get("cv4_material_predominante_techo")),
        "material_piso": _safe_str(row.get("cv5_material_predominante_piso")),
        "tenencia": _safe_str(row.get("cv7_vivienda_que_ocupa_este_hogar_es")),
        "propietario": _safe_str(row.get("cv8_persona_propietaria_de_esta_vivienda_es")),
        # Hogar
        "personas_habituales": row.get("ih1_personas_viven_habitualmente_vivienda") or 0,
        "personas_hogar": row.get("ch2_cuantas_personas_residen_habitualmente_en_hogar") or 0,
        "hombres": row.get("ch2_numero_habitantes_hombres") or 0,
        "mujeres": row.get("ch2_numero_habitantes_mujeres") or 0,
        "ninos": row.get("ch2_numero_habitantes_ninios") or 0,
        "ninas": row.get("ch2_numero_habitantes_ninias") or 0,
        "cuartos": row.get("ch3_cuantos_cuartos_dispone_hogar") or 0,
        "dormitorios": row.get("ch4_total_cuartos_utiliza_como_dormitorios") or 0,
        "cocina_exclusiva": _safe_str(row.get("ch05_dispone_en_hogar_un_cuarto_exclusivo_para_cocinar")),
        "combustible_cocina": _safe_str(row.get("ch06_descripcion")),
        "usa_lenia": _safe_str(row.get("ch07_descripcion")),
        "lugar_cocina": _safe_str(row.get("ch08_descripcion")),
        "chimenea": _safe_str(row.get("ch09_descripcion")),
        "fuente_agua": _safe_str(row.get("ch10_descripcion")),
        "dias_sin_agua": row.get("ch11_mes_pasado_dias_completos_sin_agua") or 0,
        "tratamiento_agua": _safe_str(row.get("ch12_descripcion")),
        "tipo_sanitario": _safe_str(row.get("ch13_descripcion")),
        "uso_sanitario": _safe_str(row.get("ch14_uso_servicio_sanitario")),
        "aguas_grises": _safe_str(row.get("ch15_descripcion")),
        "alumbrado": _safe_str(row.get("ch16_descripcion")),
        "dias_sin_electricidad": row.get("ch17_mes_pasado_cuantos_dias_continuos_sin_energia_electrica") or 0,
        "eliminacion_basura": _safe_str(row.get("ch19_descripcion")),
        # Bienes
        "radio": _safe_str(row.get("ch_18_bien_hogar_radio")),
        "estufa_lenia": _safe_str(row.get("ch_18_bien_hogar_estufa_lenia")),
        "estufa_gas": _safe_str(row.get("ch_18_bien_hogar_estufa_gas")),
        "televisor": _safe_str(row.get("ch_18_bien_hogar_televisor")),
        "refrigerador": _safe_str(row.get("ch_18_bien_hogar_refrigerador")),
        "lavadora": _safe_str(row.get("ch_18_bien_hogar_lavadora")),
        "computadora": _safe_str(row.get("ch_18_bien_hogar_compu_laptop")),
        "internet": _safe_str(row.get("ch_18_bien_hogar_internet")),
        "moto": _safe_str(row.get("ch_18_bien_hogar_moto")),
        "carro": _safe_str(row.get("ch_18_bien_hogar_carro")),
        # Seguridad alimentaria ELCSA
        "preocupacion_alimentos": _safe_str(row.get("sn1_descripcion")),
        "sin_alimentos": _safe_str(row.get("sn2_descripcion")),
        "adulto_sin_alimentacion_saludable": _safe_str(row.get("sn3_aduto_sin_alimentacion_saludable")),
        "nino_sin_alimentacion_saludable": _safe_str(row.get("sn3_nino_sin_alimentacion_saludable")),
        "adulto_sin_variedad": _safe_str(row.get("sn4_adulto_alimentacion_variedad")),
        "nino_sin_variedad": _safe_str(row.get("sn4_nino_alimentacion_variedad")),
        "adulto_sin_tiempo_comida": _safe_str(row.get("sn5_adulto_sin_tiempo_comida")),
        "nino_sin_tiempo_comida": _safe_str(row.get("sn5_nino_sin_tiempo_comida")),
        "adulto_comio_menos": _safe_str(row.get("sn6_adulto_comio_menos")),
        "nino_comio_menos": _safe_str(row.get("sn6_nino_no_comio_menos")),
        "adulto_sintio_hambre": _safe_str(row.get("sn7_adulto_sintio_hambre")),
        "nino_sintio_hambre": _safe_str(row.get("sn7_nino_sintio_hambre")),
        "adulto_comio_una_vez": _safe_str(row.get("sn8_adulto_comio_un_tiempo")),
        "nino_comio_una_vez": _safe_str(row.get("sn8_menor18_comio_un_tiempo")),
    }
