-- rsh.hogar_caracteristicas definition

CREATE TABLE rsh.hogar_caracteristicas
(

    `id_departamento` String,

    `departamento_residencia` String,

    `id_municipio` String,

    `municipio_residencia` String,

    `id_lugar_poblado` String,

    `lugar_residencia` String,

    `apellidos` String,

    `asiste_centro_educativo` String,

    `centro_educativo` String,

    `cui` Int64,

    `deficiencia` String,

    `edad` Int32,

    `edad_agrupacion` String,

    `edad_grupo` String,

    `fecha_nacimiento` Date,

    `id_comunidad_linguistica` String,

    `id_conyugal` String,

    `id_discapacidad` String,

    `id_ficha` Int64,

    `id_integrante` Int64,

    `id_lee_escribe` String,

    `id_nivel` String,

    `id_no_estudia` String,

    `id_nucleo` Int32,

    `id_parentesco` String,

    `id_pueblo` String,

    `id_trabaja` String,

    `id_ultimo_grado` Int32,

    `nombres` String,

    `rangos_ciclos_vida` String,

    `sexo` String,

    `trabaja` String,

    `analfabetismo` Int32,

    `no_lee` Int32,

    `numero_de_registros` Int32,

    `poblacion_masculino` Int32,

    `poblacion_femenino` Int32,

    `si_lee` Int32,

    `anio` Int32,

    `pueblo_autoidentifica` String
)
ENGINE = MergeTree
PARTITION BY anio
ORDER BY (anio,
 id_departamento,
 id_municipio,
 lugar_residencia,
 id_ficha)
SETTINGS index_granularity = 8192;
