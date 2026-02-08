-- rsh.entrevista_personas definition

CREATE TABLE rsh.entrevista_personas
(

    `personas_id` Int64,

    `hogar_id` Int64,

    `pd1_numero_correlativo_persona_hogar` Int32,

    `pd2_autoinformo` String,

    `pd2_descripcion` String,

    `pd3_tiene_dpi_o_certificado_nacimiento_renap` String,

    `pd3_descripcion` String,

    `pd3_1_razon_no_presenta_dpi` Int32,

    `pd3_1_descripcion` String,

    `pd4_numero_documento_identificacion` Int64,

    `pd5_1_primer_nombre` String,

    `pd5_2_segundo_nombre` String,

    `pd5_3_tercer_nombre` String,

    `pd5_4_cuarto_nombre` String,

    `pd5_5_primer_apellido` String,

    `pd5_6_segundo_apellido` String,

    `pd5_7_apellido_casada` String,

    `pd6_genero_id` String,

    `pd6_descripcion` String,

    `pd7_fecha_nacimiento` Date,

    `pd8_anios_cumplidos` Int32,

    `pd9_estado_civil_id` Int64,

    `pd9_descripcion` String,

    `pd10_celular` Int64,

    `pd11_parentesco_orelacion_con_jefaojefe_hogar` Int64,

    `pd11_descripcion` String,

    `pd12_origen_historia_considera_o_autoidentica` Int64,

    `pd12_descripcion` String,

    `pd13_comunidad_linguistica_maya_pertenece` Int64,

    `pd13_descripcion` String,

    `pd14_idioma_aprendio_hablar_id` Int64,

    `pd14_descripcion` String,

    `ps1_1_dificultad_ver_incluso_si_usa_lentes_o_anteojos` String,

    `ps1_1_descripcion` String,

    `ps1_2_dificultad_oir_incluso_si_usa_aparato_auditivo` String,

    `ps1_2_descripcion` String,

    `ps1_3_dificultad_caminar_o_subir_escaleras` String,

    `ps1_3_descripcion` String,

    `ps1_4_dificultad_recordar_o_concentrarse` String,

    `ps1_4_descripcion` String,

    `ps1_5_dificultad_cuidado_personal_o_vestirse` String,

    `ps1_5_descripcion` String,

    `ps1_6_dificultad_entender_o_hacerse_entender` String,

    `ps1_6_descripcion` String,

    `ps2_ha_incurrido_gastos_tratamiento_o_atencion` String,

    `ps2_descripcion` String,

    `ps3_requiere_cuidados_especiales` String,

    `ps3_descripcion` String,

    `ps4_relacion_cuidados_especiales_id` Int64,

    `ps4_descripcion` String,

    `ps5_dificultades_impiden_asistir_escuela_o_centrosalud` String,

    `ps5_descripcion` String,

    `ps6_mes_pasado_sufrio_enfermedad_accidente` String,

    `ps6_descripcion` String,

    `ps7_no_enfermo_o_accidente` String,

    `ps7_descripcion` String,

    `ps8_consulto_enfacc_o_chequeo_pmes_id` Int64,

    `ps_descripcion` String,

    `ps9_razon_no_consulto_medico_o_enfermero_id` Int64,

    `ps9_descripcion` String,

    `ps10_tipo_lugar_atencion_salud_id` Int64,

    `ps10_descripcion` String,

    `ps11_tipo_entidad_afiliado_o_cubierto_id` Int64,

    `ps11_descripcion` String,

    `ps12_afecha_embarazos_incluidas_las_perdidas` Int32,

    `ps13_embarazada_actualmente` String,

    `ps13_descripcion` String,

    `ps14_anio_ultimoembarazo` Int32,

    `ps14_mes_ultimoembarazo` Int32,

    `ps15_no_meses_embarazo_al_controlarse_1ervez` Int32,

    `ps15_descripcion` String,

    `ps16_veces_control_ultimo_o_actual_embarazo` Int32,

    `ps17_1_hijos_nacidos_vivos` Int32,

    `ps17_2_hijos_vivos_actualmente` Int32,

    `ps17_2_hijas_nacidas_vivos` Int32,

    `ps17_4_hijas_vivas_actualmente` Int32,

    `ps18_edad_tuvo_primer_embarazo` Int32,

    `ps19_tipo_personal_atendio_ultimo_parto_id` Int64,

    `ps19_descripcion` String,

    `ps20_lugar_donde_atendieron_ultimo_parto_id` Int64,

    `ps25_descripcion` String,

    `ps21_ayer_comio_algo` String,

    `ps22_que_comio_ayer` String,

    `ps22_1_comida_yogurt` String,

    `ps22_2_comida_cerealc` String,

    `ps22_3_comida_atoles` String,

    `ps22_4_comida_frijol` String,

    `ps22_5_comida_vegetales` String,

    `ps22_6_comida_fruta` String,

    `ps22_7_comida_carne` String,

    `ps22_8_comida_huevos` String,

    `ps22_9_comida_pescado` String,

    `ps22_10_comida_lacteos` String,

    `ps22_11_comida_golosina` String,

    `ps22_12_comida_fritura` String,

    `ps23_habitualmente_donde_lava_las_manos_id` Int64,

    `ps23_descripcion` String,

    `ps24_como_lava_las_manos` Int64,

    `ps24_descripcion` String,

    `pe1_sabe_leer_escribir` String,

    `pe1_descripcion` String,

    `pe2_inscrito_esteducativo_presente_anio_escolar` String,

    `pe2_descripcion` String,

    `pe3_nivel_educativo_inscrito_anio_escolar_id` Int64,

    `pe3_descripcion` String,

    `pe4_gado_inscrito` Int32,

    `pe4_actualanio_abandono_o_no_asiste_establ_educ_inscrito` String,

    `pe4_descripcion` String,

    `pe5_causa_abandono_educacion_anio_actual_id` Int64,

    `pe5_descripcion` String,

    `pe6_razon_no_inscribio_presente_anio_escolar_id` Int64,

    `pe6_descripcion` String,

    `pe7_nivel_grado_estudios_mas_alto_aprobo_id` Int64,

    `pe7_descripcion` String,

    `pe8_previas_permanecio_mayor_tiempo_menor6anios_id` Int64,

    `pe8_descripcion` String,

    `ie1_actividad_principal_semana_pasada_id` Int64,

    `ie1_descripcion` String,

    `ie2_actividad_no_principal_semana_pasada_id` Int64,

    `ie2_descripcion` String,

    `ie3_tenia_ingreso_o_paga` String,

    `ie3_descripcion` String,

    `ie4_razon_principal_no_trabajo_semana_pasada_id` Int64,

    `ie4_descripcion` String,

    `ie5_semana_pasada_hizo_tramite_buscatrabajo_o_inspropio_negocio` String,

    `ie5_descripcion` String,

    `ie6_trabajo_con_mas_horas_semana_pasada_id` Int64,

    `ie6_descripcion` String,

    `ie7_numero_personas_en_lugar_trabajo_id` Int64,

    `ie7_descripcion` String,

    `ie8_horas_dedico_actividad_no_remun_casa_hogar` Int32
)
ENGINE = MergeTree
PARTITION BY toYear(pd7_fecha_nacimiento)
ORDER BY (toYear(pd7_fecha_nacimiento),
 pd6_genero_id,
 hogar_id)
SETTINGS index_granularity = 8192;
