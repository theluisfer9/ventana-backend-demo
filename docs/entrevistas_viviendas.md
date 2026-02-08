-- rsh.entrevistas_viviendas definition

CREATE TABLE rsh.entrevistas_viviendas
(

    `id` Int64,

    `codigo_resultado_entrevista` Int32,

    `fecha_hora_inicio` DateTime,

    `fecha_hora_finaliza` DateTime,

    `tiempo_transcurrido` String,

    `duracion_minutos` Float64,

    `resultado_entrevista` String,

    `no_hogares` Int32,

    `no_hogares_registrados` Int64,

    `ig1_estructura` Int32,

    `ig2_vivienda` Int64,

    `ig3_codigo_departamento` String,

    `ig3_departamento` String,

    `ig4_codigo_municipio` String,

    `ig4_municipio` String,

    `ig5_codigo_de_sector` String,

    `ig6_codigo_del_lugar_poblado` String,

    `ig6_lugar_poblado` String,

    `ig7_manzana_id` Int32,

    `ig7_manzana_nombre` String,

    `ig8_codigo_area` Int64,

    `ig8_area` String,

    `ig9_codigo_categoria_lugar_poblado` Int64,

    `ig9_categoria_lugar_poblado` String,

    `ig10_direccion_de_la_vivienda` String,

    `cv1_codigo_condicion_vivienda` Int64,

    `cv1_condicion_vivienda` String,

    `cv2_codigo_tipo_vivienda_particular` Int64,

    `cv2_tipo_vivienda_particular` String,

    `cv3_codigo_material_predominante_en_paredes_exteriores` Int64,

    `cv3_material_predominante_en_paredes_exteriores` String,

    `cv4_codigo_material_predominante_techo` Int64,

    `cv4_material_predominante_techo` String,

    `cv5_codigo_material_predominante_piso` Int64,

    `cv5_material_predominante_piso` String,

    `cv7_codigo_vivienda_que_ocupa_este_hogar_es` Int64,

    `cv7_vivienda_que_ocupa_este_hogar_es` String,

    `cv8_codigo_persona_propietaria_de_esta_vivienda_es` Int64,

    `cv8_persona_propietaria_de_esta_vivienda_es` String
)
ENGINE = MergeTree
PARTITION BY toYear(fecha_hora_inicio)
ORDER BY (toYear(fecha_hora_inicio),
 ig3_codigo_departamento,
 ig4_codigo_municipio,
 ig6_codigo_del_lugar_poblado)
SETTINGS index_granularity = 8192;
