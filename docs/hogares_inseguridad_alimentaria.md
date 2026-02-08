-- rsh.hogares_inseguridad_alimentaria definition

CREATE TABLE rsh.hogares_inseguridad_alimentaria
(

    `hogar_id` Int64,

    `cantidad_personas` Int64,

    `cantidad_nino` Int64,

    `puntos_elcsa` Int64,

    `nivel_inseguridad_alimentaria` String
)
ENGINE = MergeTree
ORDER BY hogar_id
SETTINGS index_granularity = 8192;
