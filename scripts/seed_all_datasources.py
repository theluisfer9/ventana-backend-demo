"""
Auto-discovers ALL tables and columns from the ClickHouse DW and seeds them
as DataSources in PostgreSQL with proper names and descriptions.

Run from backend/: python scripts/seed_all_datasources.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import clickhouse_connect
from dotenv import load_dotenv
from sqlalchemy.orm import Session, sessionmaker
from api.v1.config.database import pg_sync_engine
from api.v1.models.data_source import (
    DataSource, DataSourceColumn, ColumnDataType, ColumnCategory,
    SavedQuery,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Table metadata: code, name, description
# ---------------------------------------------------------------------------
TABLE_META = {
    "vw_beneficios_x_hogar": {
        "code": "BENEFICIOS_HOGAR",
        "name": "Beneficios por Hogar",
        "description": (
            "Registro consolidado de hogares beneficiarios del RSH. "
            "Incluye ubicacion geografica, indices de pobreza (PMT, IPM, NBI), "
            "datos demograficos, intervenciones realizadas (estufa, ecofiltro, "
            "letrina, etc.) y programas asociados (FODES, MAGA, MIDES)."
        ),
    },
    "vw_beneficios_x_persona": {
        "code": "BENEFICIOS_PERSONA",
        "name": "Beneficios por Persona",
        "description": (
            "Datos a nivel individual de personas beneficiarias. "
            "Incluye identificacion (CUI), nombre, fecha de nacimiento, edad, "
            "sexo, etnia, comunidad linguistica, ubicacion geografica e "
            "indicadores de pobreza del hogar al que pertenecen."
        ),
    },
    "vw_elcsa_hogar": {
        "code": "ELCSA",
        "name": "Inseguridad Alimentaria (ELCSA)",
        "description": (
            "Escala Latinoamericana y Caribena de Seguridad Alimentaria. "
            "Mide el nivel de inseguridad alimentaria por hogar: leve, "
            "moderada o severa, basado en el puntaje ELCSA."
        ),
    },
    "vw_fase": {
        "code": "FASE",
        "name": "Fases por Municipio",
        "description": (
            "Estado de las fases de intervencion por municipio y lugar poblado. "
            "Permite conocer en que fase se encuentra cada localidad dentro "
            "del proceso de levantamiento del RSH."
        ),
    },
    "vw_hogar_carac": {
        "code": "HOGAR_CARAC",
        "name": "Caracteristicas de Integrantes del Hogar",
        "description": (
            "Informacion detallada de cada integrante del hogar: educacion, "
            "trabajo, etnia, edad, sexo, parentesco, analfabetismo y "
            "agrupaciones por rangos de edad y ciclos de vida."
        ),
    },
    "vw_hogar_fecs_v2": {
        "code": "HOGAR_FECS",
        "name": "Condiciones del Hogar (FECS v2)",
        "description": (
            "Ficha de Evaluacion de Condiciones Socioeconomicas del hogar. "
            "Cubre: composicion familiar, cuartos, fuente de energia para cocinar, "
            "agua, saneamiento, alumbrado, bienes del hogar, eliminacion de basura "
            "y seguridad alimentaria (preguntas SN1 a SN12)."
        ),
    },
    "vw_hogares_datos_demograficos": {
        "code": "HOGAR_DEMO",
        "name": "Demografia por Hogar",
        "description": (
            "Desgloses demograficos detallados por hogar: total personas, "
            "hombres/mujeres, embarazadas, personas con dificultad, y rangos "
            "de edad (primera infancia, ninos, adolescentes, jovenes, adultos, "
            "adultos mayores) con cortes por sexo."
        ),
    },
    "vw_pobreza_hogars": {
        "code": "POBREZA_HOGAR",
        "name": "Pobreza por Hogar",
        "description": (
            "Indicadores de pobreza por hogar: PMT, IPM, NBI con sus "
            "clasificaciones. Incluye datos de contacto del jefe de hogar "
            "y madre, geolocalizacion, fase del municipio e informacion "
            "de sincronizacion."
        ),
    },
    "vw_vivienda_carac": {
        "code": "VIVIENDA_CARAC",
        "name": "Caracteristicas de Vivienda",
        "description": (
            "Datos de la vivienda: tipo de construccion (paredes, techo, piso), "
            "acceso a servicios (agua, drenajes, electricidad, telefono), "
            "bienes del hogar (radio, estufa, TV, refrigerador, vehiculos) "
            "y condiciones habitacionales."
        ),
    },
    "vw_viviendas_fecs_v2": {
        "code": "VIVIENDA_FECS",
        "name": "Viviendas FECS v2",
        "description": (
            "Datos de la entrevista FECS sobre la vivienda: resultado de "
            "entrevista, duracion, ubicacion geografica, condicion y tipo "
            "de vivienda, materiales de construccion (paredes, techo, piso), "
            "forma de ocupacion y propiedad."
        ),
    },
    "w_personas_fecs_v2": {
        "code": "PERSONAS_FECS",
        "name": "Personas FECS v2",
        "description": (
            "Registro completo de personas entrevistadas en la FECS. "
            "Cubre: identificacion, parentesco, etnia, discapacidades, "
            "salud, embarazo, nutricion (dieta ayer), higiene, educacion "
            "(inscripcion, nivel, grado, abandono) e ingreso/empleo."
        ),
    },
}

# ---------------------------------------------------------------------------
# Column labels and descriptions
# ---------------------------------------------------------------------------
COLUMN_LABELS = {
    # --- Identificadores ---
    "hogar_id": ("ID Hogar", "Identificador unico del hogar en el RSH"),
    "vivienda_id": ("ID Vivienda", "Identificador unico de la vivienda"),
    "ig2_vivienda": ("ID Vivienda", "Identificador de la vivienda"),
    "personas_id": ("ID Persona", "Identificador unico de la persona"),
    "id": ("ID Registro", "Identificador del registro"),

    # --- Geografia ---
    "ig3_codigo_departamento": ("Cod. Departamento", "Codigo numerico del departamento (2 digitos)"),
    "ig3_departamento": ("Departamento", "Nombre del departamento"),
    "ig4_codigo_municipio": ("Cod. Municipio", "Codigo numerico del municipio (4 digitos)"),
    "ig4_municipio": ("Municipio", "Nombre del municipio"),
    "ig5_codigo_de_sector": ("Cod. Sector", "Codigo del sector censal"),
    "ig6_codigo_del_lugar_poblado": ("Cod. Lugar Poblado", "Codigo del lugar poblado (8 digitos)"),
    "ig6_lugar_poblado": ("Lugar Poblado", "Nombre del lugar poblado o comunidad"),
    "ig7_manzana_id": ("ID Manzana", "Identificador de la manzana censal"),
    "ig7_manzana_nombre": ("Manzana", "Nombre de la manzana censal"),
    "ig8_codigo_area": ("Cod. Area", "Codigo de area (urbano/rural)"),
    "ig8_area": ("Area", "Tipo de area: Urbano o Rural"),
    "ig9_codigo_categoria_lugar_poblado": ("Cod. Categoria", "Codigo de categoria del lugar poblado"),
    "ig9_categoria_lugar_poblado": ("Categoria Lugar Poblado", "Categoria del lugar poblado (aldea, caserio, etc.)"),
    "ig10_direccion_de_la_vivienda": ("Direccion", "Direccion de la vivienda"),
    "ig1_estructura": ("Estructura", "Numero de estructura"),
    "direccion_vivienda": ("Direccion Vivienda", "Direccion completa de la vivienda"),
    "geolocalizacion_vivienda_latitud": ("Latitud", "Coordenada de latitud de la vivienda"),
    "geolocalizacion_vivienda_longitud": ("Longitud", "Coordenada de longitud de la vivienda"),
    "area": ("Area", "Tipo de area: Urbano o Rural"),
    "direccion": ("Direccion", "Direccion de referencia"),

    # Geo alternos (otras tablas)
    "id_departamento": ("Cod. Departamento", "Identificador del departamento"),
    "nombre_departamento": ("Departamento", "Nombre del departamento"),
    "departamento": ("Departamento", "Nombre del departamento"),
    "departamento_codigo": ("Cod. Departamento", "Codigo del departamento"),
    "departamento_residencia": ("Departamento", "Departamento de residencia"),
    "id_municipio": ("Cod. Municipio", "Identificador del municipio"),
    "nombre_municipio": ("Municipio", "Nombre del municipio"),
    "municipio": ("Municipio", "Nombre del municipio"),
    "municipio_codigo": ("Cod. Municipio", "Codigo del municipio"),
    "municipio_residencia": ("Municipio", "Municipio de residencia"),
    "id_lugar_poblado": ("Cod. Lugar Poblado", "Identificador del lugar poblado"),
    "nombre_lugar_poblado": ("Lugar Poblado", "Nombre del lugar poblado"),
    "lugar_poblado": ("Lugar Poblado", "Nombre del lugar poblado"),
    "lugarpoblado_codigo": ("Cod. Lugar Poblado", "Codigo del lugar poblado"),
    "lugar_poblado_nombre": ("Lugar Poblado", "Nombre del lugar poblado"),
    "lugar_poblado_id": ("ID Lugar Poblado", "Identificador del lugar poblado"),
    "lugar_residencia": ("Lugar de Residencia", "Lugar poblado de residencia"),
    "id_lugar_poblado": ("Cod. Lugar Poblado", "Identificador del lugar poblado"),
    "tipo_area_id": ("Cod. Tipo Area", "Codigo del tipo de area"),
    "tipo_area": ("Tipo Area", "Tipo de area (Urbano/Rural)"),
    "direccion_residencia": ("Direccion", "Direccion de residencia"),

    # --- Pobreza ---
    "pmt": ("PMT", "Proxy Means Test - indicador de pobreza monetaria"),
    "pmt_clasificacion": ("Clasif. PMT", "Clasificacion de pobreza segun PMT"),
    "ipm_gt": ("IPM", "Indice de Pobreza Multidimensional de Guatemala"),
    "ipm_gt_clasificacion": ("Clasif. IPM", "Clasificacion segun IPM (Pobre, No pobre, etc.)"),
    "ipm_indicadores": ("Indicadores IPM", "Cantidad de indicadores de pobreza multidimensional"),
    "nbi": ("NBI", "Necesidades Basicas Insatisfechas"),
    "nbi_clasificacion": ("Clasif. NBI", "Clasificacion segun NBI"),
    "nbi_indicadores": ("Indicadores NBI", "Cantidad de indicadores NBI insatisfechos"),
    "puntaje_nbi": ("Puntaje NBI", "Puntaje numerico de NBI"),

    # --- Demografia ---
    "personas": ("No. Personas", "Total de personas que residen en el hogar"),
    "numero_personas": ("No. Personas", "Total de personas en el hogar"),
    "hombres": ("Hombres", "Cantidad de hombres en el hogar"),
    "mujeres": ("Mujeres", "Cantidad de mujeres en el hogar"),
    "total_personas": ("Total Personas", "Total de personas en el hogar"),
    "total_hombres": ("Total Hombres", "Total de hombres en el hogar"),
    "total_mujeres": ("Total Mujeres", "Total de mujeres en el hogar"),

    # Contacto jefe/madre
    "cui_jefe_hogar": ("CUI Jefe Hogar", "Codigo Unico de Identificacion del jefe de hogar"),
    "nombre_jefe_hogar": ("Nombre Jefe Hogar", "Nombre completo del jefe de hogar"),
    "celular_jefe_hogar": ("Celular Jefe", "Numero de celular del jefe de hogar"),
    "sexo_jefe_hogar": ("Sexo Jefe", "Sexo del jefe de hogar"),
    "cui_madre": ("CUI Madre", "CUI de la madre"),
    "nombre_madre": ("Nombre Madre", "Nombre completo de la madre"),
    "celular_madre": ("Celular Madre", "Numero de celular de la madre"),
    "sexo_madre": ("Sexo Madre", "Sexo de la madre"),
    "cui_otro_integrante": ("CUI Otro Integrante", "CUI de otro integrante de referencia"),
    "nombre_otro_integrante": ("Nombre Otro Integrante", "Nombre de otro integrante"),
    "celular_otro_integrante": ("Celular Otro Integrante", "Celular de otro integrante"),
    "parentesco_otro_integrante": ("Parentesco Otro", "Parentesco del otro integrante con el jefe"),

    # --- Intervenciones ---
    "estufa_mejorada": ("Estufa Mejorada", "Hogar beneficiado con estufa mejorada (0=No, 1=Si)"),
    "ecofiltro": ("Ecofiltro", "Hogar beneficiado con ecofiltro (0=No, 1=Si)"),
    "letrina": ("Letrina", "Hogar beneficiado con letrina (0=No, 1=Si)"),
    "repello": ("Repello", "Hogar beneficiado con repello de vivienda (0=No, 1=Si)"),
    "piso": ("Piso", "Hogar beneficiado con piso (0=No, 1=Si)"),
    "sembro": ("Siembra", "Hogar beneficiado con programa de siembra (0=No, 1=Si)"),
    "crio_animal": ("Cria de Animal", "Hogar beneficiado con cria de animales (0=No, 1=Si)"),
    "bono_unico": ("Bono Unico", "Hogar beneficiado con bono unico (0=No, 1=Si)"),
    "bono_salud": ("Bono Salud", "Hogar beneficiado con bono de salud (0=No, 1=Si)"),
    "bono_educacion": ("Bono Educacion", "Hogar beneficiado con bono de educacion (0=No, 1=Si)"),
    "bolsa_social": ("Bolsa Social", "Hogar beneficiado con bolsa social (0=No, 1=Si)"),
    "total_intervenciones": ("Total Intervenciones", "Cantidad total de intervenciones recibidas"),

    # --- Programas ---
    "prog_fodes": ("Prog. FODES", "Hogar es beneficiario de FODES (0=No, 1=Si)"),
    "prog_maga": ("Prog. MAGA", "Hogar es beneficiario de MAGA (0=No, 1=Si)"),
    "prog_bono_social": ("Prog. Bono Social", "Hogar es beneficiario de Bono Social (0=No, 1=Si)"),
    "prog_bolsa_social": ("Prog. Bolsa Social", "Hogar es beneficiario de Bolsa Social (0=No, 1=Si)"),
    "prog_bono_unico": ("Prog. Bono Unico", "Hogar es beneficiario de Bono Unico (0=No, 1=Si)"),

    # --- Tiempo ---
    "anio": ("Anio", "Anio de captura del registro"),
    "fecha": ("Fecha", "Fecha del registro"),
    "anio_captura": ("Anio Captura", "Anio en que se capturo la informacion"),
    "fecha_captura": ("Fecha Captura", "Fecha en que se capturo la informacion"),
    "mes_captura": ("Mes Captura", "Mes de captura"),
    "familia": ("Familia", "Identificador de familia"),

    # --- ELCSA ---
    "cantidad_personas": ("Personas en Hogar", "Cantidad de personas en el hogar"),
    "cantidad_nino": ("Ninos en Hogar", "Cantidad de ninos en el hogar"),
    "puntos_elcsa": ("Puntaje ELCSA", "Puntaje de la escala de seguridad alimentaria"),
    "nivel_inseguridad_alimentaria": ("Nivel Inseguridad", "Nivel de inseguridad alimentaria (leve, moderada, severa)"),

    # --- Fases ---
    "id_fase": ("ID Fase", "Identificador de la fase"),
    "nombre_fase": ("Fase", "Nombre de la fase de intervencion"),
    "estado_fase_municipio": ("Estado Fase", "Estado actual de la fase en el municipio"),
    "fase": ("Fase", "Fase del municipio"),
    "fase_estado": ("Estado Fase", "Estado de la fase"),
    "fase_inicio": ("Inicio Fase", "Fecha de inicio de la fase"),
    "fase_fin": ("Fin Fase", "Fecha de fin de la fase"),

    # --- Persona beneficios ---
    "pd4_numero_documento_identificacion": ("CUI", "Codigo Unico de Identificacion de la persona"),
    "nombre_completo": ("Nombre Completo", "Nombre completo de la persona"),
    "pd7_fecha_nacimiento": ("Fecha Nacimiento", "Fecha de nacimiento"),
    "celular": ("Celular", "Numero de celular"),
    "pd8_anios_cumplidos": ("Edad", "Edad en anios cumplidos"),
    "etnia": ("Etnia", "Etnia de autoidentificacion"),
    "comunidad_linguistica": ("Comunidad Linguistica", "Comunidad linguistica maya a la que pertenece"),
    "sexo": ("Sexo", "Sexo de la persona"),
    "personas_con_dificultad": ("Personas con Dificultad", "Indica si la persona tiene alguna dificultad"),
    "beca_artesano": ("Beca Artesano", "Beneficiario de beca artesano (0=No, 1=Si)"),
    "adulto_mayor": ("Adulto Mayor", "Es adulto mayor (0=No, 1=Si)"),
    "link__maps": ("Link Maps", "Enlace a Google Maps de la ubicacion"),

    # --- Hogar FECS ---
    "codigo_departamento": ("Cod. Departamento", "Codigo del departamento"),
    "codigo_municipio": ("Cod. Municipio", "Codigo del municipio"),
    "id_vivienda": ("ID Vivienda", "Identificador de la vivienda"),

    # --- Demografia hogar ---
    "categoria": ("Categoria", "Categoria del hogar"),
    "tipo_jefatura": ("Tipo Jefatura", "Tipo de jefatura del hogar (masculina/femenina)"),
    "sexo_jefe": ("Sexo Jefe", "Sexo del jefe de hogar"),
    "jefe_count": ("Jefes", "Cantidad de jefes de hogar"),
    "pareja_count": ("Parejas", "Cantidad de parejas en el hogar"),
    "hijos_count": ("Hijos", "Cantidad de hijos en el hogar"),
    "otros_count": ("Otros", "Cantidad de otros integrantes"),
    "personas_embarazadas": ("Embarazadas", "Cantidad de personas embarazadas"),
    "personas_con_dificultad": ("Con Dificultad", "Cantidad de personas con dificultad"),
    "primera_infancia": ("Primera Infancia", "Ninos de 0-5 anios"),
    "primera_infancia_hombres": ("Primera Infancia H", "Ninos hombres 0-5 anios"),
    "primera_infancia_mujeres": ("Primera Infancia M", "Ninas mujeres 0-5 anios"),
    "ninos": ("Ninos", "Ninos de 6-12 anios"),
    "ninos_hombres": ("Ninos H", "Ninos hombres 6-12"),
    "ninos_mujeres": ("Ninas M", "Ninas mujeres 6-12"),
    "adolescentes": ("Adolescentes", "Adolescentes 13-17 anios"),
    "adolescentes_hombres": ("Adolescentes H", "Adolescentes hombres"),
    "adolescentes_mujeres": ("Adolescentes M", "Adolescentes mujeres"),
    "jovenes": ("Jovenes", "Jovenes 18-29 anios"),
    "jovenes_hombres": ("Jovenes H", "Jovenes hombres"),
    "jovenes_mujeres": ("Jovenes M", "Jovenes mujeres"),
    "adultos": ("Adultos", "Adultos 30-59 anios"),
    "adultos_hombres": ("Adultos H", "Adultos hombres"),
    "adultos_mujeres": ("Adultos M", "Adultos mujeres"),
    "adultos_mayores": ("Adultos Mayores", "Adultos mayores 60+ anios"),
    "adultos_mayores_hombres": ("Adultos Mayores H", "Adultos mayores hombres"),
    "adultos_mayores_mujeres": ("Adultos Mayores M", "Adultos mayores mujeres"),
    "comunidad_linguistica_id": ("Cod. Comunidad Linguistica", "Codigo de la comunidad linguistica"),
    "pueblo_de_pertenencia_id": ("Cod. Pueblo Pertenencia", "Codigo del pueblo de pertenencia"),
    "pueblo_de_pertenencia": ("Pueblo Pertenencia", "Pueblo de pertenencia"),

    # Rangos de edad abreviados
    "p_0_2": ("0-2 anios", "Personas de 0 a 2 anios"),
    "p_0_2_hombres": ("0-2 H", "Hombres de 0 a 2 anios"),
    "p_0_2_mujeres": ("0-2 M", "Mujeres de 0 a 2 anios"),
    "p_0_4": ("0-4 anios", "Personas de 0 a 4 anios"),
    "p_0_4_hombres": ("0-4 H", "Hombres de 0 a 4 anios"),
    "p_0_4_mujeres": ("0-4 M", "Mujeres de 0 a 4 anios"),
    "p_0_5": ("0-5 anios", "Personas de 0 a 5 anios"),
    "p_0_5_hombres": ("0-5 H", "Hombres de 0 a 5 anios"),
    "p_0_5_mujeres": ("0-5 M", "Mujeres de 0 a 5 anios"),
    "p_6_12": ("6-12 anios", "Personas de 6 a 12 anios"),
    "p_6_12_hombres": ("6-12 H", "Hombres de 6 a 12 anios"),
    "p_6_12_mujeres": ("6-12 M", "Mujeres de 6 a 12 anios"),
    "p_6_14": ("6-14 anios", "Personas de 6 a 14 anios"),
    "p_6_14_hombres": ("6-14 H", "Hombres de 6 a 14 anios"),
    "p_6_14_mujeres": ("6-14 M", "Mujeres de 6 a 14 anios"),
    "p_7_17": ("7-17 anios", "Personas de 7 a 17 anios"),
    "p_7_17_hombres": ("7-17 H", "Hombres de 7 a 17 anios"),
    "p_7_17_mujeres": ("7-17 M", "Mujeres de 7 a 17 anios"),
    "p_12_17": ("12-17 anios", "Personas de 12 a 17 anios"),
    "p_12_17_hombres": ("12-17 H", "Hombres de 12 a 17 anios"),
    "p_12_17_mujeres": ("12-17 M", "Mujeres de 12 a 17 anios"),
    "p_18_60": ("18-60 anios", "Personas de 18 a 60 anios"),
    "p_18_60_hombres": ("18-60 H", "Hombres de 18 a 60 anios"),
    "p_18_60_mujeres": ("18-60 M", "Mujeres de 18 a 60 anios"),
    "p_15_49": ("15-49 anios", "Personas de 15 a 49 anios"),
    "p_15_49_hombres": ("15-49 H", "Hombres de 15 a 49 anios"),
    "p_15_49_mujeres": ("15-49 M", "Mujeres de 15 a 49 anios"),
    "p_65_mas": ("65+ anios", "Personas de 65 anios o mas"),
    "p_65_mas_hombres": ("65+ H", "Hombres de 65 anios o mas"),
    "p_65_mas_mujeres": ("65+ M", "Mujeres de 65 anios o mas"),

    # --- Vivienda carac ---
    "no_ficha": ("No. Ficha", "Numero de ficha de la vivienda"),
    "id_odk": ("ID ODK", "Identificador del formulario ODK"),
    "vivienda_es_des": ("Tipo Vivienda", "Descripcion del tipo de vivienda"),
    "vivienda_ocupa_des": ("Ocupacion Vivienda", "Forma de ocupacion de la vivienda"),
    "vivienda_pared_des": ("Material Pared", "Material predominante en paredes"),
    "vivienda_techo_des": ("Material Techo", "Material predominante en techo"),
    "vivienda_piso_des": ("Material Piso", "Material predominante en piso"),
    "red_agua": ("Red Agua", "Acceso a red de agua (0=No, 1=Si)"),
    "red_drenajes": ("Red Drenajes", "Acceso a red de drenajes (0=No, 1=Si)"),
    "red_electrica": ("Red Electrica", "Acceso a red electrica (0=No, 1=Si)"),
    "red_telefonica": ("Red Telefonica", "Acceso a red telefonica (0=No, 1=Si)"),
    "id_vivienda_agua": ("Cod. Agua", "Codigo de fuente de agua"),
    "vivienda_sani_des": ("Saneamiento", "Tipo de servicio sanitario"),
    "vivienda_sani_uso_des": ("Uso Sanitario", "Uso del servicio sanitario"),
    "vivienda_grises_des": ("Aguas Grises", "Manejo de aguas grises"),
    "vivienda_comb_des": ("Combustible", "Combustible para cocinar"),
    "vivienda_basura_des": ("Basura", "Eliminacion de basura"),
    "radio": ("Radio", "Tiene radio (0=No, 1=Si)"),
    "estufa": ("Estufa", "Tiene estufa (0=No, 1=Si)"),
    "television": ("Television", "Tiene television (0=No, 1=Si)"),
    "carro": ("Carro", "Tiene carro (0=No, 1=Si)"),
    "refri": ("Refrigerador", "Tiene refrigerador (0=No, 1=Si)"),
    "compu": ("Computadora", "Tiene computadora (0=No, 1=Si)"),
    "deposito_agua": ("Deposito Agua", "Tiene deposito de agua (0=No, 1=Si)"),
    "lavadora_ropa": ("Lavadora", "Tiene lavadora de ropa (0=No, 1=Si)"),
    "temazcal": ("Temazcal", "Tiene temazcal (0=No, 1=Si)"),
    "moto": ("Moto", "Tiene motocicleta (0=No, 1=Si)"),
    "internet": ("Internet", "Tiene acceso a internet"),
    "servicio_cable": ("Cable TV", "Tiene servicio de cable (0=No, 1=Si)"),
    "telefono_fijo": ("Telefono Fijo", "Tiene telefono fijo (0=No, 1=Si)"),
    "agua_caliente": ("Agua Caliente", "Tiene agua caliente (0=No, 1=Si)"),
    "no_cuartos": ("No. Cuartos", "Numero de cuartos de la vivienda"),
    "no_cuartos_dormir": ("No. Dormitorios", "Numero de cuartos para dormir"),
    "no_integrante": ("No. Integrantes", "Numero de integrantes"),
    "no_nucleos_familiares": ("No. Nucleos", "Numero de nucleos familiares"),
    "tipo_alumbrado_dispone_principalmente": ("Tipo Alumbrado", "Tipo de alumbrado principal"),

    # --- Hogar carac ---
    "apellidos": ("Apellidos", "Apellidos del integrante"),
    "nombres": ("Nombres", "Nombres del integrante"),
    "asiste_centro_educativo": ("Asiste Centro Educativo", "Si asiste a centro educativo"),
    "centro_educativo": ("Centro Educativo", "Nombre del centro educativo"),
    "cui": ("CUI", "Codigo Unico de Identificacion"),
    "deficiencia": ("Deficiencia", "Tipo de deficiencia"),
    "edad": ("Edad", "Edad en anios"),
    "edad_agrupacion": ("Grupo Edad", "Agrupacion por edad"),
    "edad_grupo": ("Rango Edad", "Rango de edad"),
    "fecha_nacimiento": ("Fecha Nacimiento", "Fecha de nacimiento"),
    "id_comunidad_linguistica": ("Cod. Comunidad Ling.", "Codigo de comunidad linguistica"),
    "id_conyugal": ("Cod. Estado Conyugal", "Codigo de estado conyugal"),
    "id_discapacidad": ("Cod. Discapacidad", "Codigo de discapacidad"),
    "id_ficha": ("No. Ficha", "Numero de ficha"),
    "id_integrante": ("ID Integrante", "Identificador del integrante"),
    "id_lee_escribe": ("Lee/Escribe", "Si sabe leer y escribir"),
    "id_nivel": ("Nivel Educativo", "Nivel educativo alcanzado"),
    "id_no_estudia": ("No Estudia", "Razon por la que no estudia"),
    "id_nucleo": ("No. Nucleo", "Numero de nucleo familiar"),
    "id_parentesco": ("Parentesco", "Parentesco con el jefe de hogar"),
    "id_pueblo": ("Pueblo", "Pueblo de pertenencia"),
    "id_trabaja": ("Trabaja", "Si trabaja actualmente"),
    "id_ultimo_grado": ("Ultimo Grado", "Ultimo grado aprobado"),
    "rangos_ciclos_vida": ("Ciclo de Vida", "Rango segun ciclo de vida"),
    "trabaja": ("Trabaja", "Si trabaja actualmente"),
    "analfabetismo": ("Analfabetismo", "Indicador de analfabetismo (0=No, 1=Si)"),
    "no_lee": ("No Lee", "No sabe leer (0=No, 1=Si)"),
    "numero_de_registros": ("No. Registros", "Numero de registros"),
    "poblacion_masculino": ("Poblacion Masculina", "Poblacion masculina"),
    "poblacion_femenino": ("Poblacion Femenina", "Poblacion femenina"),
    "si_lee": ("Si Lee", "Sabe leer (0=No, 1=Si)"),
    "pueblo_autoidentifica": ("Pueblo Autoidentifica", "Pueblo con el que se autoidentifica"),

    # --- Sincronizacion ---
    "sincronizar": ("Sincronizar", "Indicador de sincronizacion"),
    "_inserted_at": ("Fecha Insercion", "Fecha de insercion del registro"),
    "_batch_id": ("ID Lote", "Identificador del lote de carga"),
}

# ---------------------------------------------------------------------------
# ClickHouse type → ColumnDataType mapping
# ---------------------------------------------------------------------------
CH_TYPE_TO_DATA_TYPE = {
    "String": ColumnDataType.TEXT,
    "FixedString": ColumnDataType.TEXT,
    "Date": ColumnDataType.TEXT,
    "DateTime": ColumnDataType.TEXT,
    "Int8": ColumnDataType.INTEGER,
    "Int16": ColumnDataType.INTEGER,
    "Int32": ColumnDataType.INTEGER,
    "Int64": ColumnDataType.INTEGER,
    "UInt8": ColumnDataType.INTEGER,
    "UInt16": ColumnDataType.INTEGER,
    "UInt32": ColumnDataType.INTEGER,
    "UInt64": ColumnDataType.INTEGER,
    "Float32": ColumnDataType.FLOAT,
    "Float64": ColumnDataType.FLOAT,
    "Decimal": ColumnDataType.FLOAT,
}

# Columns that are interventions (binary 0/1)
INTERVENTION_COLUMNS = {
    "estufa_mejorada", "ecofiltro", "letrina", "repello", "piso",
    "sembro", "crio_animal", "bono_unico", "bono_salud",
    "bono_educacion", "bolsa_social", "prog_fodes", "prog_maga",
    "prog_bono_social", "prog_bolsa_social", "prog_bono_unico",
    "beca_artesano", "adulto_mayor",
}

# Columns that are geographic
GEO_KEYWORDS = {
    "departamento", "municipio", "lugar_poblado", "area", "direccion",
    "latitud", "longitud", "sector", "manzana", "categoria_lugar",
    "residencia", "vivienda_id", "id_vivienda", "ig2_vivienda",
}


def parse_ch_type(ch_type_str: str) -> ColumnDataType:
    """Parse a ClickHouse type string to our ColumnDataType."""
    base = ch_type_str.split("(")[0].strip()
    return CH_TYPE_TO_DATA_TYPE.get(base, ColumnDataType.TEXT)


def classify_category(col_name: str, data_type: ColumnDataType) -> ColumnCategory:
    """Classify a column into a category."""
    if col_name in INTERVENTION_COLUMNS:
        return ColumnCategory.INTERVENTION
    lower = col_name.lower()
    for kw in GEO_KEYWORDS:
        if kw in lower:
            return ColumnCategory.GEO
    if data_type in (ColumnDataType.INTEGER, ColumnDataType.FLOAT):
        return ColumnCategory.MEASURE
    return ColumnCategory.DIMENSION


def make_label(col_name: str) -> str:
    """Generate a human-readable label from a column name."""
    label = col_name
    # Remove common prefixes
    for prefix in ["ig3_", "ig4_", "ig5_", "ig6_", "ig7_", "ig8_", "ig9_", "ig10_",
                    "cv1_", "cv2_", "cv3_", "cv4_", "cv5_", "cv7_", "cv8_",
                    "ch_18_bien_hogar_", "pd_", "ps_", "pe_", "ie_"]:
        if label.startswith(prefix):
            label = label[len(prefix):]
            break
    # Replace underscores with spaces and title case
    label = label.replace("_", " ").strip().title()
    return label


def seed():
    # Connect to ClickHouse
    ch_host = os.getenv("LOCAL_CH_HOST", "localhost")
    ch_port = int(os.getenv("LOCAL_CH_PORT", "8123"))
    ch_user = os.getenv("LOCAL_CH_USER", "default")
    ch_password = os.getenv("LOCAL_CH_PASSWORD", "")
    ch_database = os.getenv("LOCAL_CH_DATABASE", "rsh")
    ch_secure = os.getenv("LOCAL_CH_SECURE", "false").lower() == "true"

    print(f"Connecting to ClickHouse at {ch_host}:{ch_port}/{ch_database}...")
    ch_client = clickhouse_connect.get_client(
        host=ch_host, port=ch_port,
        username=ch_user, password=ch_password,
        database=ch_database, secure=ch_secure,
    )

    # Get all tables
    tables_result = ch_client.query(f"SHOW TABLES FROM {ch_database}")
    tables = [row[0] for row in tables_result.result_rows]
    print(f"Found {len(tables)} tables: {tables}")

    # Connect to PostgreSQL
    SessionLocal = sessionmaker(bind=pg_sync_engine)
    db: Session = SessionLocal()

    try:
        # Clear existing data
        sq_count = db.query(SavedQuery).delete()
        col_count = db.query(DataSourceColumn).delete()
        ds_count = db.query(DataSource).delete()
        print(f"Cleared: {ds_count} datasources, {col_count} columns, {sq_count} saved queries")

        for table_name in tables:
            meta = TABLE_META.get(table_name)
            if not meta:
                print(f"  SKIP: {table_name} (no metadata configured)")
                continue

            # Get columns from ClickHouse
            cols_result = ch_client.query(f"DESCRIBE TABLE {ch_database}.{table_name}")

            # Create DataSource
            ds = DataSource(
                code=meta["code"],
                name=meta["name"],
                description=meta["description"],
                ch_table=f"{ch_database}.{table_name}",
                base_filter=None,
                institution_id=None,
                is_active=True,
            )
            db.add(ds)
            db.flush()

            # Create columns
            for order, row in enumerate(cols_result.result_rows):
                col_name = row[0]
                ch_type = row[1]

                data_type = parse_ch_type(ch_type)
                category = classify_category(col_name, data_type)

                # Get label and description from our mappings
                if col_name in COLUMN_LABELS:
                    label, description = COLUMN_LABELS[col_name]
                else:
                    label = make_label(col_name)
                    description = None

                dsc = DataSourceColumn(
                    datasource_id=ds.id,
                    column_name=col_name,
                    label=label,
                    description=description,
                    data_type=data_type,
                    category=category,
                    is_selectable=True,
                    is_filterable=True,
                    display_order=order,
                )
                db.add(dsc)

            col_total = len(cols_result.result_rows)
            print(f"  Seeded: {meta['code']} ({meta['name']}) - {col_total} columns")

        db.commit()
        print("\nDone!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
