-- rsh.beneficios_x_hogar definition

CREATE TABLE rsh.beneficios_x_hogar
(

    `hogar_id` Int64,

    `ig2_vivienda` Int64,

    `ig3_codigo_departamento` String,

    `ig3_departamento` String,

    `ig4_codigo_municipio` String,

    `ig4_municipio` String,

    `ig6_codigo_del_lugar_poblado` String,

    `ig6_lugar_poblado` String,

    `ig8_codigo_area` Int64,

    `ig8_area` String,

    `direccion_vivienda` String,

    `geolocalizacion_vivienda_latitud` Float64,

    `geolocalizacion_vivienda_longitud` Float64,

    `pmt` Float64,

    `pmt_clasificacion` String,

    `ipm_gt` Float64,

    `ipm_gt_clasificacion` String,

    `nbi` Float64,

    `nbi_clasificacion` String,

    `personas` Int64,

    `hombres` Int64,

    `mujeres` Int64,

    `cui_jefe_hogar` Int64,

    `nombre_jefe_hogar` String,

    `celular_jefe_hogar` Int32,

    `sexo_jefe_hogar` String,

    `cui_madre` Int64,

    `nombre_madre` String,

    `celular_madre` Int32,

    `sexo_madre` String,

    `cui_otro_integrante` Int64,

    `nombre_otro_integrante` String,

    `celular_otro_integrante` Int32,

    `parentesco_otro_integrante` String,

    `anio` Int32,

    `fecha` Date,

    `estufa_mejorada` Int32,

    `ecofiltro` Int32,

    `letrina` Int32,

    `repello` Int32,

    `piso` Int32,

    `sembro` Int32,

    `crio_animal` Int32,

    `bono_unico` Int32,

    `bono_salud` Int32,

    `bono_educacion` Int32,

    `bolsa_social` Int32,

    `total_intervenciones` Int32,

    `prog_fodes` Int32,

    `prog_bono_social` Int32,

    `prog_bolsa_social` Int32,

    `prog_maga` Int32,

    `prog_bono_unico` Int32,

    `familia` String
)
ENGINE = MergeTree
PARTITION BY anio
ORDER BY (ig3_codigo_departamento,
 ig4_codigo_municipio,
 hogar_id,
 fecha)
SETTINGS index_granularity = 8192;
