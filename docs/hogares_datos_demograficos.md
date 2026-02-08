-- rsh.hogares_datos_demograficos definition

CREATE TABLE rsh.hogares_datos_demograficos
(

    `vivienda_id` Int64,

    `hogar_id` Int64,

    `anio_captura` Int16,

    `fecha_captura` Date,

    `mes_captura` Int8,

    `departamento` String,

    `departamento_codigo` String,

    `municipio` String,

    `municipio_codigo` String,

    `lugar_poblado` String,

    `lugarpoblado_codigo` String,

    `tipo_area_id` Int64,

    `tipo_area` String,

    `categoria` String,

    `tipo_jefatura` String,

    `sexo_jefe` String,

    `jefe_count` Int64,

    `pareja_count` Int64,

    `hijos_count` Int64,

    `otros_count` Int64,

    `total_personas` Int64,

    `total_hombres` Int64,

    `total_mujeres` Int64,

    `personas_embarazadas` Int64,

    `personas_con_dificultad` Int64,

    `primera_infancia` Int64,

    `primera_infancia_hombres` Int64,

    `primera_infancia_mujeres` Int64,

    `ninos` Int64,

    `ninos_hombres` Int64,

    `ninos_mujeres` Int64,

    `adolescentes` Int64,

    `adolescentes_hombres` Int64,

    `adolescentes_mujeres` Int64,

    `jovenes` Int64,

    `jovenes_hombres` Int64,

    `jovenes_mujeres` Int64,

    `adultos` Int64,

    `adultos_hombres` Int64,

    `adultos_mujeres` Int64,

    `adultos_mayores` Int64,

    `adultos_mayores_hombres` Int64,

    `adultos_mayores_mujeres` Int64,

    `p_0_2` Int64,

    `p_0_2_hombres` Int64,

    `p_0_2_mujeres` Int64,

    `p_0_4` Int64,

    `p_0_4_hombres` Int64,

    `p_0_4_mujeres` Int64,

    `p_0_5` Int64,

    `p_0_5_hombres` Int64,

    `p_0_5_mujeres` Int64,

    `p_6_12` Int64,

    `p_6_12_hombres` Int64,

    `p_6_12_mujeres` Int64,

    `p_6_14` Int64,

    `p_6_14_hombres` Int64,

    `p_6_14_mujeres` Int64,

    `p_7_17` Int64,

    `p_7_17_hombres` Int64,

    `p_7_17_mujeres` Int64,

    `p_12_17` Int64,

    `p_12_17_hombres` Int64,

    `p_12_17_mujeres` Int64,

    `p_18_60` Int64,

    `p_18_60_hombres` Int64,

    `p_18_60_mujeres` Int64,

    `p_15_49` Int64,

    `p_15_49_hombres` Int64,

    `p_15_49_mujeres` Int64,

    `p_65_mas` Int64,

    `p_65_mas_hombres` Int64,

    `p_65_mas_mujeres` Int64,

    `comunidad_linguistica_id` Int64,

    `comunidad_linguistica` String,

    `pueblo_de_pertenencia_id` Int64,

    `pueblo_de_pertenencia` String
)
ENGINE = MergeTree
PARTITION BY anio_captura
ORDER BY (anio_captura,
 departamento_codigo,
 municipio_codigo,
 hogar_id,
 vivienda_id)
SETTINGS index_granularity = 8192;
