"""Queries a ClickHouse para RSH."""
from typing import Any


def build_filters(**kwargs) -> tuple[str, dict, set[str]]:
    """
    Construye cláusula WHERE y parámetros ClickHouse desde filtros.

    Returns:
        (where_clause, parameters, needed_joins)
        - where_clause: string SQL con condiciones (sin 'WHERE')
        - parameters: dict de parámetros para ClickHouse {nombre: valor}
        - needed_joins: set de tablas requeridas ('demograficos', 'inseguridad')
    """
    conditions = []
    params = {}
    joins_needed = set()

    # Filtros geográficos (requieren trim por FixedString)
    if departamento := kwargs.get("departamento_codigo"):
        conditions.append("trim(p.departamento_codigo) = {depto:String}")
        params["depto"] = str(departamento).strip()

    if municipio := kwargs.get("municipio_codigo"):
        conditions.append("trim(p.municipio_codigo) = {muni:String}")
        params["muni"] = str(municipio).strip()

    if lugar_poblado := kwargs.get("lugar_poblado_codigo"):
        conditions.append("trim(p.lugarpoblado_codigo) = {lugar:String}")
        params["lugar"] = str(lugar_poblado).strip()

    # Área (rural/urbano)
    if area := kwargs.get("area"):
        conditions.append("p.area ILIKE {area:String}")
        params["area"] = f"%{area}%"

    # Sexo del jefe de hogar (FixedString)
    if sexo := kwargs.get("sexo_jefe"):
        conditions.append("trim(p.sexo_jefe_hogar) = {sexo:String}")
        params["sexo"] = str(sexo).strip().upper()

    # Rangos IPM
    if ipm_min := kwargs.get("ipm_min"):
        conditions.append("p.ipm_gt >= {ipm_min:Float64}")
        params["ipm_min"] = float(ipm_min)

    if ipm_max := kwargs.get("ipm_max"):
        conditions.append("p.ipm_gt <= {ipm_max:Float64}")
        params["ipm_max"] = float(ipm_max)

    # Clasificaciones
    if ipm_clasificacion := kwargs.get("ipm_clasificacion"):
        conditions.append("p.ipm_gt_clasificacion ILIKE {ipm_clase:String}")
        params["ipm_clase"] = f"%{ipm_clasificacion}%"

    if pmt_clasificacion := kwargs.get("pmt_clasificacion"):
        conditions.append("p.pmt_clasificacion ILIKE {pmt_clase:String}")
        params["pmt_clase"] = f"%{pmt_clasificacion}%"

    if nbi_clasificacion := kwargs.get("nbi_clasificacion"):
        conditions.append("p.nbi_clasificacion ILIKE {nbi_clase:String}")
        params["nbi_clase"] = f"%{nbi_clasificacion}%"

    # Año
    if anio := kwargs.get("anio"):
        conditions.append("p.anio = {anio:Int32}")
        params["anio"] = int(anio)

    # Fase
    if fase := kwargs.get("fase"):
        conditions.append("p.fase ILIKE {fase:String}")
        params["fase"] = f"%{fase}%"

    # Filtros que requieren JOIN con demograficos
    if kwargs.get("tiene_menores_5"):
        joins_needed.add("demograficos")
        conditions.append("d.p_0_5 > 0")

    if kwargs.get("tiene_adultos_mayores"):
        joins_needed.add("demograficos")
        conditions.append("d.adultos_mayores > 0")

    if kwargs.get("tiene_embarazadas"):
        joins_needed.add("demograficos")
        conditions.append("d.personas_embarazadas > 0")

    if kwargs.get("tiene_discapacidad"):
        joins_needed.add("demograficos")
        conditions.append("d.personas_con_dificultad > 0")

    # Filtros que requieren JOIN con entrevista_hogares
    if fuente_agua := kwargs.get("fuente_agua"):
        joins_needed.add("hogares")
        conditions.append("h.ch10_descripcion ILIKE {fuente_agua:String}")
        params["fuente_agua"] = f"%{fuente_agua}%"

    if tipo_sanitario := kwargs.get("tipo_sanitario"):
        joins_needed.add("hogares")
        conditions.append("h.ch13_descripcion ILIKE {tipo_sanitario:String}")
        params["tipo_sanitario"] = f"%{tipo_sanitario}%"

    if alumbrado_val := kwargs.get("alumbrado"):
        joins_needed.add("hogares")
        conditions.append("h.ch16_descripcion ILIKE {alumbrado:String}")
        params["alumbrado"] = f"%{alumbrado_val}%"

    if combustible := kwargs.get("combustible_cocina"):
        joins_needed.add("hogares")
        conditions.append("h.ch06_descripcion ILIKE {combustible:String}")
        params["combustible"] = f"%{combustible}%"

    if kwargs.get("tiene_internet"):
        joins_needed.add("hogares")
        conditions.append("lower(h.ch_18_bien_hogar_internet) = 'si'")

    if kwargs.get("tiene_computadora"):
        joins_needed.add("hogares")
        conditions.append("lower(h.ch_18_bien_hogar_compu_laptop) = 'si'")

    if kwargs.get("tiene_refrigerador"):
        joins_needed.add("hogares")
        conditions.append("lower(h.ch_18_bien_hogar_refrigerador) = 'si'")

    if kwargs.get("con_hacinamiento"):
        joins_needed.add("hogares")
        conditions.append(
            "h.ch4_total_cuartos_utiliza_como_dormitorios > 0 AND "
            "h.ch2_cuantas_personas_residen_habitualmente_en_hogar / h.ch4_total_cuartos_utiliza_como_dormitorios > 3"
        )

    # Filtros que requieren subquery en entrevista_personas
    if kwargs.get("con_analfabetismo"):
        conditions.append(
            "EXISTS (SELECT 1 FROM rsh.entrevista_personas AS ep "
            "WHERE ep.hogar_id = p.hogar_id AND lower(ep.pe1_descripcion) = 'no')"
        )

    if kwargs.get("con_menores_sin_escuela"):
        conditions.append(
            "EXISTS (SELECT 1 FROM rsh.entrevista_personas AS ep "
            "WHERE ep.hogar_id = p.hogar_id AND ep.pd8_anios_cumplidos < 18 "
            "AND ep.pd8_anios_cumplidos >= 5 AND lower(ep.pe2_descripcion) = 'no')"
        )

    if kwargs.get("sin_empleo"):
        conditions.append(
            "NOT EXISTS (SELECT 1 FROM rsh.entrevista_personas AS ep "
            "WHERE ep.hogar_id = p.hogar_id AND lower(ep.ie1_descripcion) LIKE '%trabaj%')"
        )

    # Filtros que requieren JOIN con inseguridad
    if nivel_inseg := kwargs.get("nivel_inseguridad"):
        joins_needed.add("inseguridad")
        conditions.append("i.nivel_inseguridad_alimentaria ILIKE {nivel_inseg:String}")
        params["nivel_inseg"] = f"%{nivel_inseg}%"

    # Búsqueda por nombre o CUI
    if buscar := kwargs.get("buscar"):
        # Buscar en nombre o CUI (convertir Int64 a string)
        conditions.append(
            "(p.nombre_jefe_hogar ILIKE {buscar:String} OR toString(p.cui_jefe_hogar) ILIKE {buscar:String})"
        )
        params["buscar"] = f"%{buscar}%"

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params, joins_needed


def _build_joins(joins_needed: set[str]) -> str:
    """Construye las cláusulas LEFT JOIN según las tablas requeridas."""
    join_clauses = []

    if "demograficos" in joins_needed:
        join_clauses.append("""
            LEFT JOIN rsh.hogares_datos_demograficos AS d
            ON p.hogar_id = d.hogar_id AND p.anio = d.anio_captura
        """)

    if "inseguridad" in joins_needed:
        join_clauses.append("""
            LEFT JOIN rsh.hogares_inseguridad_alimentaria AS i
            ON p.hogar_id = i.hogar_id
        """)

    if "hogares" in joins_needed:
        join_clauses.append("""
            LEFT JOIN rsh.entrevista_hogares AS h
            ON p.hogar_id = h.hogar_id
        """)

    return "\n".join(join_clauses)


def query_beneficiarios_lista(
    client, offset: int = 0, limit: int = 100, **filter_kwargs
) -> tuple[list[dict], int]:
    """
    Consulta lista paginada de beneficiarios con filtros.

    Returns:
        (lista_beneficiarios, total_count)
    """
    where_clause, params, joins_needed = build_filters(**filter_kwargs)
    joins = _build_joins(joins_needed)

    # Query de conteo
    count_query = f"""
        SELECT count() as total
        FROM rsh.pobreza_hogar AS p
        {joins}
        WHERE {where_clause}
    """

    count_result = client.query(count_query, parameters=params)
    total = count_result.result_rows[0][0] if count_result.result_rows else 0

    # Query de datos paginados
    params["offset"] = offset
    params["limit"] = limit

    data_query = f"""
        SELECT
            p.hogar_id,
            p.vivienda_id,
            p.departamento,
            trim(p.departamento_codigo) as departamento_codigo,
            p.municipio,
            trim(p.municipio_codigo) as municipio_codigo,
            p.lugar_poblado,
            trim(p.lugarpoblado_codigo) as lugarpoblado_codigo,
            p.area,
            p.numero_personas,
            p.hombres,
            p.mujeres,
            p.ipm_gt,
            p.ipm_gt_clasificacion,
            p.pmt,
            p.pmt_clasificacion,
            p.nbi,
            p.nbi_clasificacion,
            p.cui_jefe_hogar,
            p.nombre_jefe_hogar,
            trim(p.sexo_jefe_hogar) as sexo_jefe_hogar,
            p.anio
        FROM rsh.pobreza_hogar AS p
        {joins}
        WHERE {where_clause}
        ORDER BY p.departamento_codigo, p.municipio_codigo, p.hogar_id
        LIMIT {{limit:Int32}}
        OFFSET {{offset:Int32}}
    """

    data_result = client.query(data_query, parameters=params)

    # Convertir filas a diccionarios
    beneficiarios = [
        dict(zip(data_result.column_names, row))
        for row in data_result.result_rows
    ]

    return beneficiarios, total


def query_beneficiario_detalle(client, hogar_id: int) -> dict | None:
    """
    Consulta detalle completo de un beneficiario con todos los JOINs.

    Returns:
        Diccionario con todos los datos o None si no existe.
    """
    query = """
        SELECT
            p.hogar_id,
            p.vivienda_id,
            p.departamento,
            trim(p.departamento_codigo) as departamento_codigo,
            p.municipio,
            trim(p.municipio_codigo) as municipio_codigo,
            p.lugar_poblado,
            trim(p.lugarpoblado_codigo) as lugarpoblado_codigo,
            p.area,
            p.tipo_area_id,
            p.numero_personas,
            p.hombres,
            p.mujeres,
            p.ipm_gt,
            p.ipm_gt_clasificacion,
            p.pmt,
            p.pmt_clasificacion,
            p.nbi,
            p.nbi_clasificacion,
            p.nbi_indicadores,
            p.geolocalizacion_vivienda_latitud,
            p.geolocalizacion_vivienda_longitud,
            p.direccion_vivienda,
            p.cui_jefe_hogar,
            p.nombre_jefe_hogar,
            p.celular_jefe_hogar,
            trim(p.sexo_jefe_hogar) as sexo_jefe_hogar,
            p.cui_madre,
            p.nombre_madre,
            p.celular_madre,
            p.fase,
            p.fase_estado,
            p.anio,
            p.fecha,
            -- Datos demográficos
            d.total_personas,
            d.total_hombres,
            d.total_mujeres,
            d.personas_embarazadas,
            d.personas_con_dificultad,
            d.primera_infancia,
            d.ninos,
            d.adolescentes,
            d.jovenes,
            d.adultos,
            d.adultos_mayores,
            d.p_0_5,
            d.tipo_jefatura,
            d.comunidad_linguistica,
            d.pueblo_de_pertenencia,
            -- Inseguridad alimentaria
            i.nivel_inseguridad_alimentaria,
            i.puntos_elcsa,
            i.cantidad_personas,
            i.cantidad_nino
        FROM rsh.pobreza_hogar AS p
        LEFT JOIN rsh.hogares_datos_demograficos AS d
            ON p.hogar_id = d.hogar_id AND p.anio = d.anio_captura
        LEFT JOIN rsh.hogares_inseguridad_alimentaria AS i
            ON p.hogar_id = i.hogar_id
        WHERE p.hogar_id = {hogar_id:Int64}
        LIMIT 1
    """

    result = client.query(query, parameters={"hogar_id": hogar_id})

    if not result.result_rows:
        return None

    return dict(zip(result.column_names, result.result_rows[0]))


def query_stats(client, **filter_kwargs) -> dict:
    """
    Calcula estadísticas agregadas sobre beneficiarios con filtros opcionales.

    Returns:
        Diccionario con conteos, promedios y distribuciones.
    """
    where_clause, params, joins_needed = build_filters(**filter_kwargs)
    joins = _build_joins(joins_needed)

    # Estadísticas generales
    stats_query = f"""
        SELECT
            count() as total_hogares,
            round(avg(p.ipm_gt), 4) as ipm_promedio,
            countIf(trim(p.sexo_jefe_hogar) = 'F') as hogares_jefatura_femenina,
            countIf(trim(p.sexo_jefe_hogar) = 'M') as hogares_jefatura_masculina,
            sum(p.numero_personas) as total_personas,
            sum(p.hombres) as total_hombres,
            sum(p.mujeres) as total_mujeres
        FROM rsh.pobreza_hogar AS p
        {joins}
        WHERE {where_clause}
    """

    stats_result = client.query(stats_query, parameters=params)
    stats = dict(zip(stats_result.column_names, stats_result.result_rows[0]))

    # Distribución por departamento
    depto_query = f"""
        SELECT
            p.departamento,
            trim(p.departamento_codigo) as departamento_codigo,
            count() as cantidad_hogares,
            sum(p.numero_personas) as total_personas
        FROM rsh.pobreza_hogar AS p
        {joins}
        WHERE {where_clause}
        GROUP BY p.departamento, p.departamento_codigo
        ORDER BY cantidad_hogares DESC
        LIMIT 22
    """

    depto_result = client.query(depto_query, parameters=params)
    distribucion_depto = [
        dict(zip(depto_result.column_names, row))
        for row in depto_result.result_rows
    ]

    # Distribución por clasificación IPM
    ipm_query = f"""
        SELECT
            p.ipm_gt_clasificacion,
            count() as cantidad_hogares,
            round(avg(p.ipm_gt), 4) as ipm_promedio
        FROM rsh.pobreza_hogar AS p
        {joins}
        WHERE {where_clause}
        GROUP BY p.ipm_gt_clasificacion
        ORDER BY cantidad_hogares DESC
    """

    ipm_result = client.query(ipm_query, parameters=params)
    distribucion_ipm = [
        dict(zip(ipm_result.column_names, row))
        for row in ipm_result.result_rows
    ]

    return {
        **stats,
        "distribucion_departamentos": distribucion_depto,
        "distribucion_ipm": distribucion_ipm,
    }


def query_dashboard(client) -> dict:
    """
    Estadísticas globales para dashboard (sin filtros).

    Returns:
        Diccionario con métricas principales y distribuciones.
    """
    # Métricas globales
    global_query = """
        SELECT
            count() as total_hogares,
            uniq(departamento_codigo) as total_departamentos,
            uniq(municipio_codigo) as total_municipios,
            round(avg(ipm_gt), 4) as ipm_promedio,
            sum(numero_personas) as total_personas
        FROM rsh.pobreza_hogar
    """

    global_result = client.query(global_query)
    stats = dict(zip(global_result.column_names, global_result.result_rows[0]))

    # Top 10 departamentos
    top_depto_query = """
        SELECT
            departamento,
            trim(departamento_codigo) as departamento_codigo,
            count() as cantidad_hogares,
            sum(numero_personas) as total_personas,
            round(avg(ipm_gt), 4) as ipm_promedio
        FROM rsh.pobreza_hogar
        GROUP BY departamento, departamento_codigo
        ORDER BY cantidad_hogares DESC
        LIMIT 10
    """

    top_depto_result = client.query(top_depto_query)
    top_departamentos = [
        dict(zip(top_depto_result.column_names, row))
        for row in top_depto_result.result_rows
    ]

    # Distribución inseguridad alimentaria
    inseg_query = """
        SELECT
            i.nivel_inseguridad_alimentaria,
            count() as cantidad_hogares
        FROM rsh.hogares_inseguridad_alimentaria AS i
        WHERE i.nivel_inseguridad_alimentaria != ''
        GROUP BY i.nivel_inseguridad_alimentaria
        ORDER BY cantidad_hogares DESC
    """

    inseg_result = client.query(inseg_query)
    distribucion_inseguridad = [
        dict(zip(inseg_result.column_names, row))
        for row in inseg_result.result_rows
    ]

    return {
        **stats,
        "top_departamentos": top_departamentos,
        "distribucion_inseguridad_alimentaria": distribucion_inseguridad,
    }


def query_catalogos(client) -> dict:
    """
    Obtiene valores DISTINCT de catálogos desde datos reales.

    Returns:
        Diccionario con listas de valores únicos para cada catálogo.
    """
    catalogos = {}

    # Departamentos
    depto_query = """
        SELECT DISTINCT
            trim(departamento_codigo) as codigo,
            departamento as nombre
        FROM rsh.pobreza_hogar
        WHERE departamento_codigo != ''
        ORDER BY codigo
    """
    depto_result = client.query(depto_query)
    catalogos["departamentos"] = [
        {"codigo": row[0], "nombre": row[1]}
        for row in depto_result.result_rows
    ]

    # Clasificaciones IPM
    ipm_query = """
        SELECT DISTINCT ipm_gt_clasificacion
        FROM rsh.pobreza_hogar
        WHERE ipm_gt_clasificacion != ''
        ORDER BY ipm_gt_clasificacion
    """
    ipm_result = client.query(ipm_query)
    catalogos["clasificaciones_ipm"] = [row[0] for row in ipm_result.result_rows]

    # Clasificaciones PMT
    pmt_query = """
        SELECT DISTINCT pmt_clasificacion
        FROM rsh.pobreza_hogar
        WHERE pmt_clasificacion != ''
        ORDER BY pmt_clasificacion
    """
    pmt_result = client.query(pmt_query)
    catalogos["clasificaciones_pmt"] = [row[0] for row in pmt_result.result_rows]

    # Clasificaciones NBI
    nbi_query = """
        SELECT DISTINCT nbi_clasificacion
        FROM rsh.pobreza_hogar
        WHERE nbi_clasificacion != ''
        ORDER BY nbi_clasificacion
    """
    nbi_result = client.query(nbi_query)
    catalogos["clasificaciones_nbi"] = [row[0] for row in nbi_result.result_rows]

    # Áreas
    area_query = """
        SELECT DISTINCT area
        FROM rsh.pobreza_hogar
        WHERE area != ''
        ORDER BY area
    """
    area_result = client.query(area_query)
    catalogos["areas"] = [row[0] for row in area_result.result_rows]

    # Niveles inseguridad alimentaria
    inseg_query = """
        SELECT DISTINCT nivel_inseguridad_alimentaria
        FROM rsh.hogares_inseguridad_alimentaria
        WHERE nivel_inseguridad_alimentaria != ''
        ORDER BY nivel_inseguridad_alimentaria
    """
    inseg_result = client.query(inseg_query)
    catalogos["niveles_inseguridad"] = [row[0] for row in inseg_result.result_rows]

    # Fases
    fase_query = """
        SELECT DISTINCT fase
        FROM rsh.pobreza_hogar
        WHERE fase != ''
        ORDER BY fase
    """
    fase_result = client.query(fase_query)
    catalogos["fases"] = [row[0] for row in fase_result.result_rows]

    # Comunidades lingüísticas
    comunidad_query = """
        SELECT DISTINCT comunidad_linguistica
        FROM rsh.hogares_datos_demograficos
        WHERE comunidad_linguistica != ''
        ORDER BY comunidad_linguistica
    """
    comunidad_result = client.query(comunidad_query)
    catalogos["comunidades_linguisticas"] = [row[0] for row in comunidad_result.result_rows]

    # Pueblos de pertenencia
    pueblo_query = """
        SELECT DISTINCT pueblo_de_pertenencia
        FROM rsh.hogares_datos_demograficos
        WHERE pueblo_de_pertenencia != ''
        ORDER BY pueblo_de_pertenencia
    """
    pueblo_result = client.query(pueblo_query)
    catalogos["pueblos"] = [row[0] for row in pueblo_result.result_rows]

    # Fuentes de agua
    agua_query = """
        SELECT DISTINCT ch10_descripcion
        FROM rsh.entrevista_hogares
        WHERE ch10_descripcion != ''
        ORDER BY ch10_descripcion
    """
    agua_result = client.query(agua_query)
    catalogos["fuentes_agua"] = [row[0] for row in agua_result.result_rows]

    # Tipos sanitario
    sanitario_query = """
        SELECT DISTINCT ch13_descripcion
        FROM rsh.entrevista_hogares
        WHERE ch13_descripcion != ''
        ORDER BY ch13_descripcion
    """
    sanitario_result = client.query(sanitario_query)
    catalogos["tipos_sanitario"] = [row[0] for row in sanitario_result.result_rows]

    # Tipos alumbrado
    alumbrado_query = """
        SELECT DISTINCT ch16_descripcion
        FROM rsh.entrevista_hogares
        WHERE ch16_descripcion != ''
        ORDER BY ch16_descripcion
    """
    alumbrado_result = client.query(alumbrado_query)
    catalogos["tipos_alumbrado"] = [row[0] for row in alumbrado_result.result_rows]

    # Combustibles cocina
    combustible_query = """
        SELECT DISTINCT ch06_descripcion
        FROM rsh.entrevista_hogares
        WHERE ch06_descripcion != ''
        ORDER BY ch06_descripcion
    """
    combustible_result = client.query(combustible_query)
    catalogos["combustibles_cocina"] = [row[0] for row in combustible_result.result_rows]

    return catalogos


def query_municipios(client, departamento_codigo: str) -> list[dict]:
    """
    Obtiene municipios filtrados por departamento.

    Args:
        departamento_codigo: Código de departamento (FixedString, será trimmeado)

    Returns:
        Lista de diccionarios con {codigo, nombre}
    """
    query = """
        SELECT DISTINCT
            trim(municipio_codigo) as codigo,
            municipio as nombre
        FROM rsh.pobreza_hogar
        WHERE trim(departamento_codigo) = {depto:String}
          AND municipio_codigo != ''
        ORDER BY codigo
    """

    result = client.query(query, parameters={"depto": departamento_codigo.strip()})

    return [
        {"codigo": row[0], "nombre": row[1]}
        for row in result.result_rows
    ]


def query_lugares_poblados(client, municipio_codigo: str) -> list[dict]:
    """
    Obtiene lugares poblados filtrados por municipio.

    Args:
        municipio_codigo: Código de municipio (FixedString, será trimmeado)

    Returns:
        Lista de diccionarios con {codigo, nombre}
    """
    query = """
        SELECT DISTINCT
            trim(lugarpoblado_codigo) as codigo,
            lugar_poblado as nombre
        FROM rsh.pobreza_hogar
        WHERE trim(municipio_codigo) = {muni:String}
          AND lugarpoblado_codigo != ''
        ORDER BY codigo
    """

    result = client.query(query, parameters={"muni": municipio_codigo.strip()})

    return [
        {"codigo": row[0], "nombre": row[1]}
        for row in result.result_rows
    ]


def query_personas_hogar(client, hogar_id: int) -> list[dict]:
    """Consulta las personas de un hogar desde entrevista_personas."""
    query = """
        SELECT
            personas_id,
            pd1_numero_correlativo_persona_hogar,
            pd4_numero_documento_identificacion,
            pd5_1_primer_nombre,
            pd5_2_segundo_nombre,
            pd5_3_tercer_nombre,
            pd5_4_cuarto_nombre,
            pd5_5_primer_apellido,
            pd5_6_segundo_apellido,
            pd5_7_apellido_casada,
            pd6_descripcion,
            pd7_fecha_nacimiento,
            pd8_anios_cumplidos,
            pd9_descripcion,
            pd10_celular,
            pd11_descripcion,
            pd12_descripcion,
            pd13_descripcion,
            pd14_descripcion,
            ps1_1_descripcion,
            ps1_2_descripcion,
            ps1_3_descripcion,
            ps1_4_descripcion,
            ps1_5_descripcion,
            ps1_6_descripcion,
            ps13_descripcion,
            pe1_descripcion,
            pe2_descripcion,
            pe7_descripcion,
            ie1_descripcion,
            ie3_descripcion
        FROM rsh.entrevista_personas
        WHERE hogar_id = {hogar_id:Int64}
        ORDER BY pd1_numero_correlativo_persona_hogar
    """
    result = client.query(query, parameters={"hogar_id": hogar_id})
    return [
        dict(zip(result.column_names, row))
        for row in result.result_rows
    ]


def query_vivienda_hogar(client, hogar_id: int) -> dict | None:
    """Consulta detalle de vivienda y hogar con servicios, bienes y seguridad alimentaria."""
    query = """
        SELECT
            v.cv1_condicion_vivienda,
            v.cv2_tipo_vivienda_particular,
            v.cv3_material_predominante_en_paredes_exteriores,
            v.cv4_material_predominante_techo,
            v.cv5_material_predominante_piso,
            v.cv7_vivienda_que_ocupa_este_hogar_es,
            v.cv8_persona_propietaria_de_esta_vivienda_es,
            h.ih1_personas_viven_habitualmente_vivienda,
            h.ch2_cuantas_personas_residen_habitualmente_en_hogar,
            h.ch2_numero_habitantes_hombres,
            h.ch2_numero_habitantes_mujeres,
            h.ch2_numero_habitantes_ninios,
            h.ch2_numero_habitantes_ninias,
            h.ch3_cuantos_cuartos_dispone_hogar,
            h.ch4_total_cuartos_utiliza_como_dormitorios,
            h.ch05_dispone_en_hogar_un_cuarto_exclusivo_para_cocinar,
            h.ch06_descripcion,
            h.ch07_descripcion,
            h.ch08_descripcion,
            h.ch09_descripcion,
            h.ch10_descripcion,
            h.ch11_mes_pasado_dias_completos_sin_agua,
            h.ch12_descripcion,
            h.ch13_descripcion,
            h.ch14_uso_servicio_sanitario,
            h.ch15_descripcion,
            h.ch16_descripcion,
            h.ch17_mes_pasado_cuantos_dias_continuos_sin_energia_electrica,
            h.ch19_descripcion,
            h.ch_18_bien_hogar_radio,
            h.ch_18_bien_hogar_estufa_lenia,
            h.ch_18_bien_hogar_estufa_gas,
            h.ch_18_bien_hogar_televisor,
            h.ch_18_bien_hogar_refrigerador,
            h.ch_18_bien_hogar_lavadora,
            h.ch_18_bien_hogar_compu_laptop,
            h.ch_18_bien_hogar_internet,
            h.ch_18_bien_hogar_moto,
            h.ch_18_bien_hogar_carro,
            h.sn1_descripcion,
            h.sn2_descripcion,
            h.sn3_aduto_sin_alimentacion_saludable,
            h.sn3_nino_sin_alimentacion_saludable,
            h.sn4_adulto_alimentacion_variedad,
            h.sn4_nino_alimentacion_variedad,
            h.sn5_adulto_sin_tiempo_comida,
            h.sn5_nino_sin_tiempo_comida,
            h.sn6_adulto_comio_menos,
            h.sn6_nino_no_comio_menos,
            h.sn7_adulto_sintio_hambre,
            h.sn7_nino_sintio_hambre,
            h.sn8_adulto_comio_un_tiempo,
            h.sn8_menor18_comio_un_tiempo
        FROM rsh.pobreza_hogar AS p
        LEFT JOIN rsh.entrevistas_viviendas AS v
            ON p.vivienda_id = v.id
        LEFT JOIN rsh.entrevista_hogares AS h
            ON p.hogar_id = h.hogar_id
        WHERE p.hogar_id = {hogar_id:Int64}
        LIMIT 1
    """
    result = client.query(query, parameters={"hogar_id": hogar_id})
    if not result.result_rows:
        return None
    return dict(zip(result.column_names, result.result_rows[0]))