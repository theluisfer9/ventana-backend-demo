-- rsh.vivienda_caracteristicas definition

CREATE TABLE rsh.vivienda_caracteristicas
(

    `no_ficha` Int64,

    `id_odk` String,

    `id_departamento` String,

    `departamento_residencia` String,

    `id_municipio` String,

    `municipio_residencia` String,

    `id_lugar_poblado` String,

    `lugar_residencia` String,

    `direccion_residencia` String,

    `vivienda_es_des` String,

    `vivienda_ocupa_des` String,

    `vivienda_pared_des` String,

    `vivienda_techo_des` String,

    `vivienda_piso_des` String,

    `red_agua` Int32,

    `red_drenajes` Int32,

    `red_electrica` Int32,

    `red_telefonica` Int32,

    `id_vivienda_agua` String,

    `vivienda_sani_des` String,

    `vivienda_sani_uso_des` String,

    `vivienda_grises_des` String,

    `vivienda_comb_des` String,

    `vivienda_basura_des` String,

    `radio` Int32,

    `estufa` Int32,

    `television` Int32,

    `carro` Int32,

    `refri` Int32,

    `compu` Int32,

    `deposito_agua` Int32,

    `lavadora_ropa` Int32,

    `temazcal` Int32,

    `moto` Int32,

    `internet` String,

    `servicio_cable` Int32,

    `telefono_fijo` Int32,

    `agua_caliente` Int32,

    `no_cuartos` Int32,

    `no_cuartos_dormir` Int32,

    `no_integrante` Int32,

    `no_nucleos_familiares` Int32,

    `anio` Int32,

    `tipo_alumbrado_dispone_principalmente` String
)
ENGINE = MergeTree
PARTITION BY anio
ORDER BY (anio,
 id_departamento,
 id_municipio,
 id_lugar_poblado)
SETTINGS index_granularity = 8192;
