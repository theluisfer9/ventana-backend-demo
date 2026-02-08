-- rsh.pobreza_hogar definition

CREATE TABLE rsh.pobreza_hogar
(

    `departamento` String,

    `departamento_codigo` FixedString(2),

    `municipio` String,

    `municipio_codigo` FixedString(4),

    `area` String,

    `lugar_poblado` String,

    `lugarpoblado_codigo` FixedString(8),

    `tipo_area_id` Int64,

    `vivienda_id` Int64,

    `hogar_id` Int64,

    `geolocalizacion_vivienda_latitud` Float64,

    `geolocalizacion_vivienda_longitud` Float64,

    `direccion_vivienda` String,

    `numero_personas` Int32,

    `personas` Int64,

    `hombres` Int64,

    `mujeres` Int64,

    `pmt` Decimal(38,
 10),

    `pmt_clasificacion` String,

    `ipm_indicadores` Int32,

    `ipm_gt` Decimal(38,
 10),

    `ipm_gt_clasificacion` String,

    `nbi_clasificacion` String,

    `nbi` Decimal(38,
 10),

    `nbi_indicadores` Int32,

    `puntaje_nbi` Decimal(38,
 10),

    `cui_jefe_hogar` Int64,

    `nombre_jefe_hogar` String,

    `celular_jefe_hogar` Int32,

    `sexo_jefe_hogar` FixedString(1),

    `cui_madre` Int64,

    `nombre_madre` String,

    `celular_madre` Int32,

    `sexo_madre` FixedString(1),

    `cui_otro_integrante` Int64,

    `nombre_otro_integrante` String,

    `celular_otro_integrante` Int32,

    `parentesco_otro_integrante` String,

    `anio` Decimal(10,
 0),

    `fecha` Date,

    `familia` String,

    `fase` String,

    `fase_estado` String,

    `fase_inicio` Date,

    `fase_fin` Date,

    `sincronizar` UInt8,

    `_inserted_at` DateTime DEFAULT now(),

    `_batch_id` UInt64 DEFAULT 0
)
ENGINE = MergeTree
PARTITION BY toYear(fecha)
ORDER BY (departamento_codigo,
 municipio_codigo,
 lugarpoblado_codigo,
 hogar_id)
SETTINGS index_granularity = 8192;
