"""
Mock ClickHouse client para tests.

Intercepta queries SQL por patron y devuelve datos del dataset generado.
Imita la interfaz de clickhouse_connect: result.column_names, result.result_rows.
"""
import re
from dataclasses import dataclass, field
from tests.v1.rsh_mock_data import RSHMockDataset


@dataclass
class MockQueryResult:
    """Imita clickhouse_connect QueryResult."""
    column_names: list[str] = field(default_factory=list)
    result_rows: list[tuple] = field(default_factory=list)


class MockClickHouseClient:
    """Mock client que parsea SQL y devuelve datos del RSHMockDataset."""

    def __init__(self, dataset: RSHMockDataset | None = None):
        self.dataset = dataset or RSHMockDataset(n_hogares=5000, personas_por_hogar=3)
        self._closed = False

    def close(self):
        self._closed = True

    def query(self, sql: str, parameters: dict | None = None) -> MockQueryResult:
        """Despacha la query al handler correcto segun patron SQL."""
        sql_clean = " ".join(sql.split()).lower()
        params = parameters or {}

        # ── Consulta: handlers for beneficios_x_hogar (FODES) ──
        if "beneficios_x_hogar" in sql_clean:
            # Dashboard global for consulta
            if "uniq(ig3_departamento_codigo)" in sql_clean:
                return self._handle_consulta_dashboard(sql_clean, params)

            # Intervenciones count
            if "sumif" in sql_clean:
                return self._handle_consulta_intervenciones(sql_clean, params)

            # Count for consulta
            if "select count()" in sql_clean:
                return self._handle_consulta_count(sql_clean, params)

            # Lista for consulta (has limit+offset)
            if "limit" in sql_clean and "offset" in sql_clean:
                if "hogar_id" not in params or "offset" in params:
                    return self._handle_consulta_lista(sql_clean, params)

            # Detalle for consulta
            if "hogar_id" in params:
                return self._handle_consulta_detalle(params, sql_clean)

            # Catalogos DISTINCT for consulta
            if "distinct" in sql_clean and "ig3_departamento_codigo" in sql_clean:
                return self._handle_consulta_catalogo_departamentos(sql_clean, params)

        # ── Dashboard: metricas globales (must be before count handler) ──
        if "uniq(departamento_codigo)" in sql_clean or "uniq(municipio_codigo)" in sql_clean:
            return self._handle_dashboard_global()

        # ── Stats: estadisticas generales (countIf before simple count) ──
        if "countif" in sql_clean and "pobreza_hogar" in sql_clean:
            return self._handle_stats_general(sql_clean, params)

        # ── Beneficiarios lista: count ──
        if "select count()" in sql_clean and "pobreza_hogar" in sql_clean:
            return self._handle_count(sql_clean, params)

        # ── Beneficiarios lista: data (tiene LIMIT/OFFSET) ──
        if "pobreza_hogar" in sql_clean and "limit" in sql_clean and "offset" in sql_clean:
            # Detalle tiene hogar_id param, pero no offset
            if "left join" in sql_clean and "hogares_datos_demograficos" in sql_clean and "hogares_inseguridad_alimentaria" in sql_clean:
                if "hogar_id" in params and "offset" not in params:
                    return self._handle_detalle(params)
            return self._handle_lista(sql_clean, params)

        # ── Detalle de beneficiario ──
        if "pobreza_hogar" in sql_clean and "hogares_datos_demograficos" in sql_clean and "hogar_id" in params:
            return self._handle_detalle(params)

        # ── Personas de un hogar ──
        if "entrevista_personas" in sql_clean and "hogar_id" in params:
            return self._handle_personas(params)

        # ── Vivienda de un hogar ──
        if "entrevistas_viviendas" in sql_clean and "hogar_id" in params:
            return self._handle_vivienda(params)

        # ── Stats: distribucion IPM (GROUP BY ipm_gt_clasificacion) ──
        if "group by" in sql_clean and "group by p.ipm_gt_clasificacion" in sql_clean:
            return self._handle_distribucion_ipm(sql_clean, params)

        # ── Stats/dashboard: distribucion por departamento ──
        if "group by" in sql_clean and "group by p.departamento" in sql_clean and "cantidad_hogares" in sql_clean:
            return self._handle_distribucion_departamentos(sql_clean, params)

        # ── Dashboard: inseguridad alimentaria ──
        if "hogares_inseguridad_alimentaria" in sql_clean and "group by" in sql_clean:
            return self._handle_inseguridad_distribucion()

        # ── Catalogos: departamentos DISTINCT ──
        if "distinct" in sql_clean and "departamento_codigo" in sql_clean and "departamento" in sql_clean and "pobreza_hogar" in sql_clean:
            if "municipio_codigo" not in sql_clean:
                return self._handle_catalogo_departamentos()

        # ── Catalogos: municipios por departamento ──
        if "distinct" in sql_clean and "municipio_codigo" in sql_clean and "depto" in params:
            return self._handle_catalogo_municipios(params)

        # ── Catalogos: lugares poblados por municipio ──
        if "distinct" in sql_clean and "lugarpoblado_codigo" in sql_clean and "muni" in params:
            return self._handle_catalogo_lugares(params)

        # ── Catalogos: clasificaciones y valores DISTINCT ──
        if "distinct" in sql_clean:
            return self._handle_catalogo_distinct(sql_clean)

        return MockQueryResult()

    # ── Handlers ─────────────────────────────────────────────────────

    _PROG_COLUMNS = ["prog_fodes", "prog_maga", "prog_mides"]
    _ALL_INTERVENTIONS = [
        "estufa_mejorada", "ecofiltro", "letrina", "repello", "piso",
        "sembro", "crio_animal",
        "bono_unico", "bono_salud", "bono_educacion", "bolsa_social",
    ]

    def _apply_consulta_filters(self, beneficios: list[dict], params: dict, sql_clean: str = "") -> list[dict]:
        """Aplica filtros a beneficios_x_hogar para consultas institucionales."""
        filtered = beneficios

        # ── Base filter: prog_X = 1 (dinamico) ──
        for prog_col in self._PROG_COLUMNS:
            if f"{prog_col} = 1" in sql_clean or f"{prog_col}=1" in sql_clean:
                filtered = [b for b in filtered if b.get(prog_col) == 1]

        # ── Filtros geograficos ──
        if "depto" in params:
            filtered = [b for b in filtered if b["ig3_departamento_codigo"].strip() == params["depto"]]
        if "muni" in params:
            filtered = [b for b in filtered if b["ig4_municipio_codigo"].strip() == params["muni"]]

        # ── Buscar por hogar_id ──
        if "buscar" in params:
            term = params["buscar"].strip("%").lower()
            filtered = [b for b in filtered if term in str(b["hogar_id"])]

        # ── Filtros de intervenciones (dinamico) ──
        for col in self._ALL_INTERVENTIONS:
            if f"{col} = 1" in sql_clean or f"{col}=1" in sql_clean:
                filtered = [b for b in filtered if b.get(col) == 1]

        return filtered

    def _apply_filters(self, hogares: list[dict], params: dict, sql_clean: str = "") -> list[dict]:
        """Aplica filtros a la lista de hogares, incluyendo cross-table."""
        filtered = hogares

        # ── Filtros directos en hogar (params-based) ──
        if "depto" in params:
            filtered = [h for h in filtered if h["departamento_codigo"].strip() == params["depto"]]
        if "muni" in params:
            filtered = [h for h in filtered if h["municipio_codigo"].strip() == params["muni"]]
        if "lugar" in params:
            filtered = [h for h in filtered if h["lugarpoblado_codigo"].strip() == params["lugar"]]
        if "area" in params:
            term = params["area"].strip("%").lower()
            filtered = [h for h in filtered if term in h["area"].lower()]
        if "sexo" in params:
            filtered = [h for h in filtered if h["sexo_jefe_hogar"].strip().upper() == params["sexo"].upper()]
        if "ipm_min" in params:
            filtered = [h for h in filtered if h["ipm_gt"] >= params["ipm_min"]]
        if "ipm_max" in params:
            filtered = [h for h in filtered if h["ipm_gt"] <= params["ipm_max"]]
        if "ipm_clase" in params:
            term = params["ipm_clase"].strip("%").lower()
            filtered = [h for h in filtered if term in h["ipm_gt_clasificacion"].lower()]
        if "pmt_clase" in params:
            term = params["pmt_clase"].strip("%").lower()
            filtered = [h for h in filtered if term in h["pmt_clasificacion"].lower()]
        if "nbi_clase" in params:
            term = params["nbi_clase"].strip("%").lower()
            filtered = [h for h in filtered if term in h["nbi_clasificacion"].lower()]
        if "anio" in params:
            filtered = [h for h in filtered if h["anio"] == params["anio"]]
        if "fase" in params:
            term = params["fase"].strip("%").lower()
            filtered = [h for h in filtered if term in h.get("fase", "").lower()]
        if "buscar" in params:
            term = params["buscar"].strip("%").lower()
            filtered = [h for h in filtered if term in h["nombre_jefe_hogar"].lower() or term in str(h["cui_jefe_hogar"])]

        # ── Filtros cross-table (vivienda bienes) - detectados por SQL patterns ──
        if "ch_18_bien_hogar_internet" in sql_clean:
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {v["hogar_id"] for v in self.dataset.viviendas
                     if v["hogar_id"] in hogar_ids and v.get("ch_18_bien_hogar_internet", "").lower() == "si"}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "ch_18_bien_hogar_compu_laptop" in sql_clean:
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {v["hogar_id"] for v in self.dataset.viviendas
                     if v["hogar_id"] in hogar_ids and v.get("ch_18_bien_hogar_compu_laptop", "").lower() == "si"}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "ch_18_bien_hogar_refrigerador" in sql_clean and "= 'si'" in sql_clean:
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {v["hogar_id"] for v in self.dataset.viviendas
                     if v["hogar_id"] in hogar_ids and v.get("ch_18_bien_hogar_refrigerador", "").lower() == "si"}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        # Hacinamiento: personas/dormitorios > 3
        if "ch2_cuantas_personas_residen_habitualmente_en_hogar / h.ch4" in sql_clean:
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = set()
            for v in self.dataset.viviendas:
                if v["hogar_id"] in hogar_ids:
                    dorms = v.get("ch4_total_cuartos_utiliza_como_dormitorios", 0)
                    pers = v.get("ch2_cuantas_personas_residen_habitualmente_en_hogar", 0)
                    if dorms > 0 and pers / dorms > 3:
                        valid.add(v["hogar_id"])
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        # ── Filtros cross-table (vivienda servicios) - params-based ──
        if "fuente_agua" in params:
            term = params["fuente_agua"].strip("%").lower()
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {v["hogar_id"] for v in self.dataset.viviendas
                     if v["hogar_id"] in hogar_ids and term in v.get("ch10_descripcion", "").lower()}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "tipo_sanitario" in params:
            term = params["tipo_sanitario"].strip("%").lower()
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {v["hogar_id"] for v in self.dataset.viviendas
                     if v["hogar_id"] in hogar_ids and term in v.get("ch13_descripcion", "").lower()}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "alumbrado" in params:
            term = params["alumbrado"].strip("%").lower()
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {v["hogar_id"] for v in self.dataset.viviendas
                     if v["hogar_id"] in hogar_ids and term in v.get("ch16_descripcion", "").lower()}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "combustible" in params:
            term = params["combustible"].strip("%").lower()
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {v["hogar_id"] for v in self.dataset.viviendas
                     if v["hogar_id"] in hogar_ids and term in v.get("ch06_descripcion", "").lower()}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        # ── Filtros cross-table (demograficos) - SQL patterns ──
        if "d.p_0_5 > 0" in sql_clean:
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {d["hogar_id"] for d in self.dataset.demograficos
                     if d["hogar_id"] in hogar_ids and d.get("p_0_5", 0) > 0}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "d.adultos_mayores > 0" in sql_clean:
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {d["hogar_id"] for d in self.dataset.demograficos
                     if d["hogar_id"] in hogar_ids and d.get("adultos_mayores", 0) > 0}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "d.personas_embarazadas > 0" in sql_clean:
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {d["hogar_id"] for d in self.dataset.demograficos
                     if d["hogar_id"] in hogar_ids and d.get("personas_embarazadas", 0) > 0}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "d.personas_con_dificultad > 0" in sql_clean:
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {d["hogar_id"] for d in self.dataset.demograficos
                     if d["hogar_id"] in hogar_ids and d.get("personas_con_dificultad", 0) > 0}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        # ── Filtros cross-table (inseguridad) - params-based ──
        if "nivel_inseg" in params:
            term = params["nivel_inseg"].strip("%").lower()
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {i["hogar_id"] for i in self.dataset.inseguridad
                     if i["hogar_id"] in hogar_ids and term in i.get("nivel_inseguridad_alimentaria", "").lower()}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        # ── Filtros cross-table (personas via subqueries) - SQL patterns ──
        if "ep.pe1_descripcion" in sql_clean and "'no'" in sql_clean:
            # con_analfabetismo: EXISTS persona con pe1 = 'no'
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = {p["hogar_id"] for p in self.dataset.personas
                     if p["hogar_id"] in hogar_ids and p.get("pe1_descripcion", "").lower() == "no"}
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "ep.pe2_descripcion" in sql_clean and "pd8_anios_cumplidos" in sql_clean:
            # con_menores_sin_escuela: EXISTS persona <18, >=5, pe2='no'
            hogar_ids = {h["hogar_id"] for h in filtered}
            valid = set()
            for p in self.dataset.personas:
                if (p["hogar_id"] in hogar_ids
                        and 5 <= p.get("pd8_anios_cumplidos", 0) < 18
                        and p.get("pe2_descripcion", "").lower() == "no"):
                    valid.add(p["hogar_id"])
            filtered = [h for h in filtered if h["hogar_id"] in valid]

        if "not exists" in sql_clean and "ep.ie1_descripcion" in sql_clean:
            # sin_empleo: NOT EXISTS persona con ie1 LIKE '%trabaj%'
            hogar_ids = {h["hogar_id"] for h in filtered}
            employed = {p["hogar_id"] for p in self.dataset.personas
                        if p["hogar_id"] in hogar_ids and "trabaj" in p.get("ie1_descripcion", "").lower()}
            filtered = [h for h in filtered if h["hogar_id"] not in employed]

        return filtered

    def _handle_consulta_count(self, sql_clean: str, params: dict) -> MockQueryResult:
        """Count para beneficios_x_hogar."""
        filtered = self._apply_consulta_filters(self.dataset.beneficios_x_hogar, params, sql_clean)
        return MockQueryResult(
            column_names=["total"],
            result_rows=[(len(filtered),)],
        )

    def _handle_consulta_lista(self, sql_clean: str, params: dict) -> MockQueryResult:
        """Lista paginada de beneficios_x_hogar."""
        filtered = self._apply_consulta_filters(self.dataset.beneficios_x_hogar, params, sql_clean)
        offset = params.get("offset", 0)
        limit = params.get("limit", 100)
        page = filtered[offset: offset + limit]

        base_columns = [
            "hogar_id", "ig3_departamento", "ig3_departamento_codigo",
            "ig4_municipio", "ig4_municipio_codigo", "ig5_lugar_poblado",
            "area", "numero_personas", "hombres", "mujeres",
            "ipm_gt", "ipm_gt_clasificacion",
        ]
        interv_cols = [c for c in self._ALL_INTERVENTIONS if c in sql_clean]
        columns = base_columns + interv_cols

        rows = [tuple(b.get(c) for c in columns) for b in page]
        return MockQueryResult(column_names=columns, result_rows=rows)

    def _handle_consulta_detalle(self, params: dict, sql_clean: str = "") -> MockQueryResult:
        """Detalle de un beneficio por hogar_id."""
        hogar_id = params["hogar_id"]
        beneficio = self.dataset.get_beneficio(hogar_id)

        if not beneficio:
            return MockQueryResult(column_names=[], result_rows=[])

        # Check base filter dynamically
        for prog_col in self._PROG_COLUMNS:
            if f"{prog_col} = 1" in sql_clean:
                if beneficio.get(prog_col) != 1:
                    return MockQueryResult(column_names=[], result_rows=[])

        base_columns = [
            "hogar_id", "ig3_departamento", "ig3_departamento_codigo",
            "ig4_municipio", "ig4_municipio_codigo", "ig5_lugar_poblado",
            "area", "numero_personas", "hombres", "mujeres",
            "ipm_gt", "ipm_gt_clasificacion",
        ]
        interv_cols = [c for c in self._ALL_INTERVENTIONS if c in sql_clean]
        columns = base_columns + interv_cols

        row = tuple(beneficio.get(c) for c in columns)
        return MockQueryResult(column_names=columns, result_rows=[row])

    def _handle_consulta_dashboard(self, sql_clean: str, params: dict) -> MockQueryResult:
        """Dashboard global para consulta institucional."""
        # Filter to prog_fodes=1
        filtered = self._apply_consulta_filters(self.dataset.beneficios_x_hogar, params, sql_clean)

        total = len(filtered)
        deptos = set(b["ig3_departamento_codigo"] for b in filtered)
        munis = set(b["ig4_municipio_codigo"] for b in filtered)
        total_personas = sum(b["numero_personas"] for b in filtered)

        columns = ["total_hogares", "total_departamentos", "total_municipios", "total_personas"]
        row = (total, len(deptos), len(munis), total_personas)

        return MockQueryResult(column_names=columns, result_rows=[row])

    def _handle_consulta_intervenciones(self, sql_clean: str, params: dict) -> MockQueryResult:
        """Count de intervenciones institucionales."""
        filtered = self._apply_consulta_filters(self.dataset.beneficios_x_hogar, params, sql_clean)

        interv_cols = [c for c in self._ALL_INTERVENTIONS if c in sql_clean]
        columns = interv_cols
        row = tuple(sum(b.get(c, 0) for b in filtered) for c in interv_cols)

        return MockQueryResult(column_names=columns, result_rows=[row])

    def _handle_consulta_catalogo_departamentos(self, sql_clean: str, params: dict) -> MockQueryResult:
        """DISTINCT departamentos para consulta institucional."""
        filtered = self._apply_consulta_filters(self.dataset.beneficios_x_hogar, params, sql_clean)

        seen = {}
        for b in filtered:
            code = b["ig3_departamento_codigo"].strip()
            if code and code not in seen:
                seen[code] = b["ig3_departamento"]

        columns = ["codigo", "nombre"]
        rows = [(c, n) for c, n in sorted(seen.items())]
        return MockQueryResult(column_names=columns, result_rows=rows)

    def _handle_count(self, sql_clean: str, params: dict) -> MockQueryResult:
        filtered = self._apply_filters(self.dataset.hogares, params, sql_clean)
        return MockQueryResult(
            column_names=["total"],
            result_rows=[(len(filtered),)],
        )

    def _handle_lista(self, sql_clean: str, params: dict) -> MockQueryResult:
        filtered = self._apply_filters(self.dataset.hogares, params, sql_clean)
        offset = params.get("offset", 0)
        limit = params.get("limit", 100)
        page = filtered[offset: offset + limit]

        columns = [
            "hogar_id", "vivienda_id", "departamento", "departamento_codigo",
            "municipio", "municipio_codigo", "lugar_poblado", "lugarpoblado_codigo",
            "area", "numero_personas", "hombres", "mujeres",
            "ipm_gt", "ipm_gt_clasificacion", "pmt", "pmt_clasificacion",
            "nbi", "nbi_clasificacion", "cui_jefe_hogar", "nombre_jefe_hogar",
            "sexo_jefe_hogar", "anio",
        ]

        rows = [
            tuple(h[c] for c in columns)
            for h in page
        ]

        return MockQueryResult(column_names=columns, result_rows=rows)

    def _handle_detalle(self, params: dict) -> MockQueryResult:
        hogar_id = params["hogar_id"]
        hogar = self.dataset.get_hogar(hogar_id)
        if not hogar:
            return MockQueryResult(column_names=[], result_rows=[])

        demo = self.dataset.get_demografico(hogar_id) or {}
        inseg = self.dataset.get_inseguridad(hogar_id) or {}

        columns = [
            "hogar_id", "vivienda_id", "departamento", "departamento_codigo",
            "municipio", "municipio_codigo", "lugar_poblado", "lugarpoblado_codigo",
            "area", "tipo_area_id", "numero_personas", "hombres", "mujeres",
            "ipm_gt", "ipm_gt_clasificacion", "pmt", "pmt_clasificacion",
            "nbi", "nbi_clasificacion", "nbi_indicadores",
            "geolocalizacion_vivienda_latitud", "geolocalizacion_vivienda_longitud",
            "direccion_vivienda",
            "cui_jefe_hogar", "nombre_jefe_hogar", "celular_jefe_hogar",
            "sexo_jefe_hogar", "cui_madre", "nombre_madre", "celular_madre",
            "fase", "fase_estado", "anio", "fecha",
            # Demograficos
            "total_personas", "total_hombres", "total_mujeres",
            "personas_embarazadas", "personas_con_dificultad",
            "primera_infancia", "ninos", "adolescentes", "jovenes", "adultos", "adultos_mayores",
            "p_0_5", "tipo_jefatura", "comunidad_linguistica", "pueblo_de_pertenencia",
            # Inseguridad
            "nivel_inseguridad_alimentaria", "puntos_elcsa",
            "cantidad_personas", "cantidad_nino",
        ]

        merged = {**hogar, **demo, **inseg}
        row = tuple(merged.get(c) for c in columns)

        return MockQueryResult(column_names=columns, result_rows=[row])

    def _handle_personas(self, params: dict) -> MockQueryResult:
        hogar_id = params["hogar_id"]
        personas = self.dataset.get_personas_hogar(hogar_id)

        columns = [
            "personas_id", "pd1_numero_correlativo_persona_hogar",
            "pd4_numero_documento_identificacion",
            "pd5_1_primer_nombre", "pd5_2_segundo_nombre", "pd5_3_tercer_nombre",
            "pd5_4_cuarto_nombre", "pd5_5_primer_apellido", "pd5_6_segundo_apellido",
            "pd5_7_apellido_casada",
            "pd6_descripcion", "pd7_fecha_nacimiento", "pd8_anios_cumplidos",
            "pd9_descripcion", "pd10_celular",
            "pd11_descripcion", "pd12_descripcion", "pd13_descripcion", "pd14_descripcion",
            "ps1_1_descripcion", "ps1_2_descripcion", "ps1_3_descripcion",
            "ps1_4_descripcion", "ps1_5_descripcion", "ps1_6_descripcion",
            "ps13_descripcion",
            "pe1_descripcion", "pe2_descripcion", "pe7_descripcion",
            "ie1_descripcion", "ie3_descripcion",
        ]

        rows = [
            tuple(p.get(c) for c in columns)
            for p in personas
        ]

        return MockQueryResult(column_names=columns, result_rows=rows)

    def _handle_vivienda(self, params: dict) -> MockQueryResult:
        hogar_id = params["hogar_id"]
        viv = self.dataset.get_vivienda(hogar_id)
        if not viv:
            return MockQueryResult(column_names=[], result_rows=[])

        columns = [
            "cv1_condicion_vivienda", "cv2_tipo_vivienda_particular",
            "cv3_material_predominante_en_paredes_exteriores",
            "cv4_material_predominante_techo", "cv5_material_predominante_piso",
            "cv7_vivienda_que_ocupa_este_hogar_es",
            "cv8_persona_propietaria_de_esta_vivienda_es",
            "ih1_personas_viven_habitualmente_vivienda",
            "ch2_cuantas_personas_residen_habitualmente_en_hogar",
            "ch2_numero_habitantes_hombres", "ch2_numero_habitantes_mujeres",
            "ch2_numero_habitantes_ninios", "ch2_numero_habitantes_ninias",
            "ch3_cuantos_cuartos_dispone_hogar",
            "ch4_total_cuartos_utiliza_como_dormitorios",
            "ch05_dispone_en_hogar_un_cuarto_exclusivo_para_cocinar",
            "ch06_descripcion", "ch07_descripcion", "ch08_descripcion", "ch09_descripcion",
            "ch10_descripcion",
            "ch11_mes_pasado_dias_completos_sin_agua",
            "ch12_descripcion", "ch13_descripcion",
            "ch14_uso_servicio_sanitario", "ch15_descripcion", "ch16_descripcion",
            "ch17_mes_pasado_cuantos_dias_continuos_sin_energia_electrica",
            "ch19_descripcion",
            "ch_18_bien_hogar_radio", "ch_18_bien_hogar_estufa_lenia",
            "ch_18_bien_hogar_estufa_gas", "ch_18_bien_hogar_televisor",
            "ch_18_bien_hogar_refrigerador", "ch_18_bien_hogar_lavadora",
            "ch_18_bien_hogar_compu_laptop", "ch_18_bien_hogar_internet",
            "ch_18_bien_hogar_moto", "ch_18_bien_hogar_carro",
            "sn1_descripcion", "sn2_descripcion",
            "sn3_aduto_sin_alimentacion_saludable", "sn3_nino_sin_alimentacion_saludable",
            "sn4_adulto_alimentacion_variedad", "sn4_nino_alimentacion_variedad",
            "sn5_adulto_sin_tiempo_comida", "sn5_nino_sin_tiempo_comida",
            "sn6_adulto_comio_menos", "sn6_nino_no_comio_menos",
            "sn7_adulto_sintio_hambre", "sn7_nino_sintio_hambre",
            "sn8_adulto_comio_un_tiempo", "sn8_menor18_comio_un_tiempo",
        ]

        row = tuple(viv.get(c) for c in columns)
        return MockQueryResult(column_names=columns, result_rows=[row])

    def _handle_stats_general(self, sql_clean: str, params: dict) -> MockQueryResult:
        filtered = self._apply_filters(self.dataset.hogares, params, sql_clean)
        total = len(filtered)
        ipm_avg = sum(h["ipm_gt"] for h in filtered) / total if total else 0
        fem = sum(1 for h in filtered if h["sexo_jefe_hogar"].strip() == "F")
        masc = total - fem
        total_personas = sum(h["numero_personas"] for h in filtered)
        total_hombres = sum(h["hombres"] for h in filtered)
        total_mujeres = sum(h["mujeres"] for h in filtered)

        columns = [
            "total_hogares", "ipm_promedio",
            "hogares_jefatura_femenina", "hogares_jefatura_masculina",
            "total_personas", "total_hombres", "total_mujeres",
        ]
        row = (total, round(ipm_avg, 4), fem, masc, total_personas, total_hombres, total_mujeres)

        return MockQueryResult(column_names=columns, result_rows=[row])

    def _handle_distribucion_departamentos(self, sql_clean: str, params: dict) -> MockQueryResult:
        filtered = self._apply_filters(self.dataset.hogares, params, sql_clean)
        deptos = {}
        for h in filtered:
            key = (h["departamento"], h["departamento_codigo"])
            if key not in deptos:
                deptos[key] = {"cantidad": 0, "personas": 0}
            deptos[key]["cantidad"] += 1
            deptos[key]["personas"] += h["numero_personas"]

        columns = ["departamento", "departamento_codigo", "cantidad_hogares", "total_personas"]
        if "ipm_promedio" in sql_clean:
            columns.append("ipm_promedio")

        rows = []
        for (depto, codigo), vals in sorted(deptos.items(), key=lambda x: -x[1]["cantidad"]):
            row = [depto, codigo, vals["cantidad"], vals["personas"]]
            if "ipm_promedio" in sql_clean:
                hogares_depto = [h for h in filtered if h["departamento_codigo"] == codigo]
                avg_ipm = sum(h["ipm_gt"] for h in hogares_depto) / len(hogares_depto) if hogares_depto else 0
                row.append(round(avg_ipm, 4))
            rows.append(tuple(row))

        return MockQueryResult(column_names=columns, result_rows=rows[:22])

    def _handle_distribucion_ipm(self, sql_clean: str, params: dict) -> MockQueryResult:
        filtered = self._apply_filters(self.dataset.hogares, params, sql_clean)
        ipm_groups = {}
        for h in filtered:
            key = h["ipm_gt_clasificacion"]
            if key not in ipm_groups:
                ipm_groups[key] = {"cantidad": 0, "ipm_sum": 0}
            ipm_groups[key]["cantidad"] += 1
            ipm_groups[key]["ipm_sum"] += h["ipm_gt"]

        columns = ["ipm_gt_clasificacion", "cantidad_hogares", "ipm_promedio"]
        rows = []
        for clasif, vals in sorted(ipm_groups.items(), key=lambda x: -x[1]["cantidad"]):
            avg = round(vals["ipm_sum"] / vals["cantidad"], 4) if vals["cantidad"] else 0
            rows.append((clasif, vals["cantidad"], avg))

        return MockQueryResult(column_names=columns, result_rows=rows)

    def _handle_dashboard_global(self) -> MockQueryResult:
        hogares = self.dataset.hogares
        total = len(hogares)
        deptos = set(h["departamento_codigo"] for h in hogares)
        munis = set(h["municipio_codigo"] for h in hogares)
        ipm_avg = sum(h["ipm_gt"] for h in hogares) / total if total else 0
        total_personas = sum(h["numero_personas"] for h in hogares)

        columns = ["total_hogares", "total_departamentos", "total_municipios", "ipm_promedio", "total_personas"]
        row = (total, len(deptos), len(munis), round(ipm_avg, 4), total_personas)

        return MockQueryResult(column_names=columns, result_rows=[row])

    def _handle_inseguridad_distribucion(self) -> MockQueryResult:
        niveles = {}
        for i in self.dataset.inseguridad:
            nivel = i["nivel_inseguridad_alimentaria"]
            if nivel:
                niveles[nivel] = niveles.get(nivel, 0) + 1

        columns = ["nivel_inseguridad_alimentaria", "cantidad_hogares"]
        rows = [
            (nivel, cant)
            for nivel, cant in sorted(niveles.items(), key=lambda x: -x[1])
        ]

        return MockQueryResult(column_names=columns, result_rows=rows)

    def _handle_catalogo_departamentos(self) -> MockQueryResult:
        seen = {}
        for h in self.dataset.hogares:
            code = h["departamento_codigo"].strip()
            if code and code not in seen:
                seen[code] = h["departamento"]

        columns = ["codigo", "nombre"]
        rows = [(c, n) for c, n in sorted(seen.items())]
        return MockQueryResult(column_names=columns, result_rows=rows)

    def _handle_catalogo_municipios(self, params: dict) -> MockQueryResult:
        depto = params["depto"].strip()
        seen = {}
        for h in self.dataset.hogares:
            if h["departamento_codigo"].strip() == depto:
                code = h["municipio_codigo"].strip()
                if code and code not in seen:
                    seen[code] = h["municipio"]

        columns = ["codigo", "nombre"]
        rows = [(c, n) for c, n in sorted(seen.items())]
        return MockQueryResult(column_names=columns, result_rows=rows)

    def _handle_catalogo_lugares(self, params: dict) -> MockQueryResult:
        muni = params["muni"].strip()
        seen = {}
        for h in self.dataset.hogares:
            if h["municipio_codigo"].strip() == muni:
                code = h["lugarpoblado_codigo"].strip()
                if code and code not in seen:
                    seen[code] = h["lugar_poblado"]

        columns = ["codigo", "nombre"]
        rows = [(c, n) for c, n in sorted(seen.items())]
        return MockQueryResult(column_names=columns, result_rows=rows)

    def _handle_catalogo_distinct(self, sql_clean: str) -> MockQueryResult:
        """Maneja queries DISTINCT para catalogos varios."""

        if "ipm_gt_clasificacion" in sql_clean:
            vals = sorted(set(h["ipm_gt_clasificacion"] for h in self.dataset.hogares if h["ipm_gt_clasificacion"]))
            return MockQueryResult(column_names=["ipm_gt_clasificacion"], result_rows=[(v,) for v in vals])

        if "pmt_clasificacion" in sql_clean:
            vals = sorted(set(h["pmt_clasificacion"] for h in self.dataset.hogares if h["pmt_clasificacion"]))
            return MockQueryResult(column_names=["pmt_clasificacion"], result_rows=[(v,) for v in vals])

        if "nbi_clasificacion" in sql_clean:
            vals = sorted(set(h["nbi_clasificacion"] for h in self.dataset.hogares if h["nbi_clasificacion"]))
            return MockQueryResult(column_names=["nbi_clasificacion"], result_rows=[(v,) for v in vals])

        if "select distinct area" in sql_clean:
            vals = sorted(set(h["area"] for h in self.dataset.hogares if h["area"]))
            return MockQueryResult(column_names=["area"], result_rows=[(v,) for v in vals])

        if "nivel_inseguridad_alimentaria" in sql_clean:
            vals = sorted(set(i["nivel_inseguridad_alimentaria"] for i in self.dataset.inseguridad if i["nivel_inseguridad_alimentaria"]))
            return MockQueryResult(column_names=["nivel_inseguridad_alimentaria"], result_rows=[(v,) for v in vals])

        if "select distinct fase" in sql_clean:
            vals = sorted(set(h["fase"] for h in self.dataset.hogares if h["fase"]))
            return MockQueryResult(column_names=["fase"], result_rows=[(v,) for v in vals])

        if "comunidad_linguistica" in sql_clean:
            vals = sorted(set(d["comunidad_linguistica"] for d in self.dataset.demograficos if d["comunidad_linguistica"]))
            return MockQueryResult(column_names=["comunidad_linguistica"], result_rows=[(v,) for v in vals])

        if "pueblo_de_pertenencia" in sql_clean:
            vals = sorted(set(d["pueblo_de_pertenencia"] for d in self.dataset.demograficos if d["pueblo_de_pertenencia"]))
            return MockQueryResult(column_names=["pueblo_de_pertenencia"], result_rows=[(v,) for v in vals])

        if "ch10_descripcion" in sql_clean:
            vals = sorted(set(v["ch10_descripcion"] for v in self.dataset.viviendas if v.get("ch10_descripcion")))
            return MockQueryResult(column_names=["ch10_descripcion"], result_rows=[(v,) for v in vals])

        if "ch13_descripcion" in sql_clean:
            vals = sorted(set(v["ch13_descripcion"] for v in self.dataset.viviendas if v.get("ch13_descripcion")))
            return MockQueryResult(column_names=["ch13_descripcion"], result_rows=[(v,) for v in vals])

        if "ch16_descripcion" in sql_clean:
            vals = sorted(set(v["ch16_descripcion"] for v in self.dataset.viviendas if v.get("ch16_descripcion")))
            return MockQueryResult(column_names=["ch16_descripcion"], result_rows=[(v,) for v in vals])

        if "ch06_descripcion" in sql_clean:
            vals = sorted(set(v["ch06_descripcion"] for v in self.dataset.viviendas if v.get("ch06_descripcion")))
            return MockQueryResult(column_names=["ch06_descripcion"], result_rows=[(v,) for v in vals])

        return MockQueryResult()
