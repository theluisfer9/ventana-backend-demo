-- rsh.entrevista_hogares definition

CREATE TABLE rsh.entrevista_hogares
(

    `hogar_id` Int64,

    `id_vivienda` Int64,

    `codigo_departamento` String,

    `departamento` String,

    `codigo_municipio` String,

    `municipio` String,

    `ih1_personas_viven_habitualmente_vivienda` Int32,

    `ih2_personas_preparan_alimentos_x_separado` String,

    `ih3_no_hogares_vivienda` Int32,

    `ch1_numero_hogar` Int64,

    `ch1_1_nucleos_hogar` Int32,

    `ch2_cuantas_personas_residen_habitualmente_en_hogar` Int32,

    `ch2_numero_habitantes_hombres` Int32,

    `ch2_numero_habitantes_mujeres` Int32,

    `ch2_numero_habitantes_ninios` Int32,

    `ch2_numero_habitantes_ninias` Int32,

    `ch3_cuantos_cuartos_dispone_hogar` Int32,

    `ch4_total_cuartos_utiliza_como_dormitorios` Int32,

    `ch05_codigo_dispone_en_hogar_un_cuarto_exclusivo_para_cocinar` String,

    `ch05_dispone_en_hogar_un_cuarto_exclusivo_para_cocinar` String,

    `ch06_codigo_cual_es_fuente_principal_que_utiliza_el_hogar_para_` Int64,

    `ch06_descripcion` String,

    `ch07_codigo_mes_pasado_utilizaron_lenia_para_cocinar` String,

    `ch07_descripcion` String,

    `ch08_codigo_lugar_donde_cocinan` Int64,

    `ch08_descripcion` String,

    `ch09_codigo_cocina_con_chimenea_o_salida_humo` String,

    `ch09_descripcion` String,

    `ch10_codigo_fuente_agua_consumo_hogar` Int64,

    `ch10_descripcion` String,

    `ch11_mes_pasado_dias_completos_sin_agua` Int32,

    `ch12_codigo_tratamiento_dan_agua_beber` Int64,

    `ch12_descripcion` String,

    `ch13_codigo_tipo_servicio_sanitario` Int64,

    `ch13_descripcion` String,

    `ch14_codigo_uso_servicio_sanitario` Int64,

    `ch14_uso_servicio_sanitario` String,

    `ch15_codigo_como_deshace_aguas_grises` Int64,

    `ch15_descripcion` String,

    `ch16_codigo_tipo_alumbrado_dispone_principalmente` Int64,

    `ch16_descripcion` String,

    `ch17_mes_pasado_cuantos_dias_continuos_sin_energia_electrica` Int32,

    `ch_18_bien_hogar_radio` String,

    `ch_18_bien_hogar_estufa_lenia` String,

    `ch_18_bien_hogar_estufa_gas` String,

    `ch_18_bien_hogar_televisor` String,

    `ch_18_bien_hogar_refrigerador` String,

    `ch_18_bien_hogar_lavadora` String,

    `ch_18_bien_hogar_compu_laptop` String,

    `ch_18_bien_hogar_internet` String,

    `ch_18_bien_hogar_moto` String,

    `ch_18_bien_hogar_carro` String,

    `ch19_codigo_modo_eliminacion_basura` Int64,

    `ch19_descripcion` String,

    `ch20_codigo_persona_aporta_mas_recursos` Int64,

    `ch20_descripcion` String,

    `sn1_codigo_se_preocupo_x_alimientos_se_acabaran_u3meses` Int32,

    `sn1_descripcion` String,

    `sn2_codigo_se_quedaron_sin_alimentos_u3meses` Int32,

    `sn2_descripcion` String,

    `sn3_codigo_aduto_sin_alimentacion_saludable` Int32,

    `sn3_aduto_sin_alimentacion_saludable` String,

    `sn3_codigo_nino_sin_alimentacion_saludable` Int32,

    `sn3_nino_sin_alimentacion_saludable` String,

    `sn4_codigo_adulto_alimentacion_variedad` Int32,

    `sn4_adulto_alimentacion_variedad` String,

    `sn4_codigo_nino_alimentacion_variedad` Int32,

    `sn4_nino_alimentacion_variedad` String,

    `sn5_codigo_aduto_sin_tiempo_comida` Int32,

    `sn5_adulto_sin_tiempo_comida` String,

    `sn5_codigo_nino_sin_tiempo_comida` Int32,

    `sn5_nino_sin_tiempo_comida` String,

    `sn6_codigo_adulto_comio_menos` Int32,

    `sn6_adulto_comio_menos` String,

    `sn6_codigo_nino_no_comio_menos` Int32,

    `sn6_nino_no_comio_menos` String,

    `sn7_codigo_adulto_sintio_hambre` Int32,

    `sn7_adulto_sintio_hambre` String,

    `sn7_codigo_nino_sintio_hambre` Int32,

    `sn7_nino_sintio_hambre` String,

    `sn8_codigo_adulto_comio_un_tiempo` Int32,

    `sn8_adulto_comio_un_tiempo` String,

    `sn8_nino_aldia_no_comio_o_comio_una_vez_u3meses` Int32,

    `sn8_menor18_comio_un_tiempo` String,

    `sn9_codigo_nino_cantidad_servida` Int32,

    `sn9_nino_cantidad_servida` String,

    `sn10_codigo_uanio_sembro_cosecho_crioanimal_talo` String,

    `sn10_uanio_sembro_cosecho_crioanimal_talo` String,

    `sn11_codigo_uanio_crio_animal_para_consumo_propio` String,

    `sn11_uanio_crio_animal_para_consumo_propio` String,

    `sn12_codigo_talo` Int32,

    `sn12_talo` String,

    `lugar_poblado_nombre` String,

    `lugar_poblado_id` Int64
)
ENGINE = MergeTree
PARTITION BY codigo_departamento
ORDER BY (hogar_id,
 id_vivienda)
SETTINGS index_granularity = 8192;
