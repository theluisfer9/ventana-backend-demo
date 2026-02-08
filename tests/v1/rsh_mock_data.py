"""
Generador de datos mock ClickHouse-compatible para RSH.

Produce tuplas + column_names que imitan la interfaz de clickhouse_connect:
    result.column_names -> list[str]
    result.result_rows  -> list[tuple]

Optimizado para generar miles de registros rápidamente.
"""
import random
from datetime import date, timedelta
from faker import Faker

fake = Faker("es")
Faker.seed(42)
random.seed(42)

# ── Catalogos Guatemala (22 departamentos, municipios reales) ─────

DEPARTAMENTOS = [
    ("01", "Guatemala"),
    ("02", "El Progreso"),
    ("03", "Sacatepequez"),
    ("04", "Chimaltenango"),
    ("05", "Escuintla"),
    ("06", "Santa Rosa"),
    ("07", "Solola"),
    ("08", "Totonicapan"),
    ("09", "Quetzaltenango"),
    ("10", "Suchitepequez"),
    ("11", "Retalhuleu"),
    ("12", "San Marcos"),
    ("13", "Huehuetenango"),
    ("14", "Quiche"),
    ("15", "Baja Verapaz"),
    ("16", "Alta Verapaz"),
    ("17", "Peten"),
    ("18", "Izabal"),
    ("19", "Zacapa"),
    ("20", "Chiquimula"),
    ("21", "Jalapa"),
    ("22", "Jutiapa"),
]

MUNICIPIOS_POR_DEPTO = {
    "01": [("0101", "Guatemala"), ("0102", "Santa Catarina Pinula"), ("0103", "San Jose Pinula"), ("0104", "San Jose del Golfo"), ("0105", "Palencia"), ("0106", "Chinautla"), ("0107", "San Pedro Ayampuc"), ("0108", "Mixco"), ("0109", "San Pedro Sacatepequez"), ("0110", "San Juan Sacatepequez"), ("0111", "San Raymundo"), ("0112", "Chuarrancho"), ("0113", "Fraijanes"), ("0114", "Amatitlan"), ("0115", "Villa Nueva"), ("0116", "Villa Canales"), ("0117", "Petapa")],
    "02": [("0201", "Guastatoya"), ("0202", "Morazan"), ("0203", "San Agustin Acasaguastlan"), ("0204", "San Cristobal Acasaguastlan"), ("0205", "El Jicaro"), ("0206", "Sansare"), ("0207", "Sanarate"), ("0208", "San Antonio La Paz")],
    "03": [("0301", "Antigua Guatemala"), ("0302", "Jocotenango"), ("0303", "Pastores"), ("0304", "Sumpango"), ("0305", "Santo Domingo Xenacoj"), ("0306", "Santiago Sacatepequez"), ("0307", "San Bartolome Milpas Altas"), ("0308", "San Lucas Sacatepequez"), ("0309", "Santa Lucia Milpas Altas"), ("0310", "Magdalena Milpas Altas"), ("0311", "Santa Maria de Jesus"), ("0312", "Ciudad Vieja"), ("0313", "San Miguel Duenas"), ("0314", "Alotenango"), ("0315", "San Antonio Aguas Calientes"), ("0316", "Santa Catarina Barahona")],
    "04": [("0401", "Chimaltenango"), ("0402", "San Jose Poaquil"), ("0403", "San Martin Jilotepeque"), ("0404", "Comalapa"), ("0405", "Santa Apolonia"), ("0406", "Tecpan Guatemala"), ("0407", "Patzun"), ("0408", "Pochuta"), ("0409", "Patzicia"), ("0410", "Santa Cruz Balanya"), ("0411", "Acatenango"), ("0412", "Yepocapa"), ("0413", "San Andres Itzapa"), ("0414", "Parramos"), ("0415", "Zaragoza"), ("0416", "El Tejar")],
    "05": [("0501", "Escuintla"), ("0502", "Santa Lucia Cotzumalguapa"), ("0503", "La Democracia"), ("0504", "Siquinala"), ("0505", "Masagua"), ("0506", "Tiquisate"), ("0507", "La Gomera"), ("0508", "Guanagazapa"), ("0509", "San Jose"), ("0510", "Iztapa"), ("0511", "Palin"), ("0512", "San Vicente Pacaya"), ("0513", "Nueva Concepcion")],
    "06": [("0601", "Cuilapa"), ("0602", "Barberena"), ("0603", "Santa Rosa de Lima"), ("0604", "Casillas"), ("0605", "San Rafael Las Flores"), ("0606", "Oratorio"), ("0607", "San Juan Tecuaco"), ("0608", "Chiquimulilla"), ("0609", "Taxisco"), ("0610", "Santa Maria Ixhuatan"), ("0611", "Guazacapan"), ("0612", "Santa Cruz Naranjo"), ("0613", "Pueblo Nuevo Vinas"), ("0614", "Nueva Santa Rosa")],
    "07": [("0701", "Solola"), ("0702", "San Jose Chacaya"), ("0703", "Santa Maria Visitacion"), ("0704", "Santa Lucia Utatlan"), ("0705", "Nahuala"), ("0706", "Santa Catarina Ixtahuacan"), ("0707", "Santa Clara La Laguna"), ("0708", "Concepcion"), ("0709", "San Andres Semetabaj"), ("0710", "Panajachel"), ("0711", "Santa Catarina Palopo"), ("0712", "San Antonio Palopo"), ("0713", "San Lucas Toliman"), ("0714", "Santa Cruz La Laguna"), ("0715", "San Pablo La Laguna"), ("0716", "San Marcos La Laguna"), ("0717", "San Juan La Laguna"), ("0718", "San Pedro La Laguna"), ("0719", "Santiago Atitlan")],
    "08": [("0801", "Totonicapan"), ("0802", "San Cristobal Totonicapan"), ("0803", "San Francisco El Alto"), ("0804", "San Andres Xecul"), ("0805", "Momostenango"), ("0806", "Santa Maria Chiquimula"), ("0807", "Santa Lucia La Reforma"), ("0808", "San Bartolo")],
    "09": [("0901", "Quetzaltenango"), ("0902", "Salcaja"), ("0903", "Olintepeque"), ("0904", "San Carlos Sija"), ("0905", "Sibilia"), ("0906", "Cabrican"), ("0907", "Cajola"), ("0908", "San Miguel Siguila"), ("0909", "Ostuncalco"), ("0910", "San Mateo"), ("0911", "Concepcion Chiquirichapa"), ("0912", "San Martin Sacatepequez"), ("0913", "Almolonga"), ("0914", "Cantel"), ("0915", "Huitan"), ("0916", "Zunil"), ("0917", "Colomba"), ("0918", "San Francisco La Union"), ("0919", "El Palmar"), ("0920", "Coatepeque"), ("0921", "Genova"), ("0922", "Flores Costa Cuca"), ("0923", "La Esperanza"), ("0924", "Palestina de Los Altos")],
    "10": [("1001", "Mazatenango"), ("1002", "Cuyotenango"), ("1003", "San Francisco Zapotitlan"), ("1004", "San Bernardino"), ("1005", "San Jose El Idolo"), ("1006", "Santo Domingo Suchitepequez"), ("1007", "San Lorenzo"), ("1008", "Samayac"), ("1009", "San Pablo Jocopilas"), ("1010", "San Antonio Suchitepequez"), ("1011", "San Miguel Panan"), ("1012", "San Gabriel"), ("1013", "Chicacao"), ("1014", "Patulul"), ("1015", "Santa Barbara"), ("1016", "San Juan Bautista"), ("1017", "Santo Tomas La Union"), ("1018", "Zunilito"), ("1019", "Pueblo Nuevo"), ("1020", "Rio Bravo")],
    "11": [("1101", "Retalhuleu"), ("1102", "San Sebastian"), ("1103", "Santa Cruz Mulua"), ("1104", "San Martin Zapotitlan"), ("1105", "San Felipe"), ("1106", "San Andres Villa Seca"), ("1107", "Champerico"), ("1108", "Nuevo San Carlos"), ("1109", "El Asintal")],
    "12": [("1201", "San Marcos"), ("1202", "San Pedro Sacatepequez"), ("1203", "San Antonio Sacatepequez"), ("1204", "Comitancillo"), ("1205", "San Miguel Ixtahuacan"), ("1206", "Concepcion Tutuapa"), ("1207", "Tajumulco"), ("1208", "Tejutla"), ("1209", "San Rafael Pie de la Cuesta"), ("1210", "Nuevo Progreso"), ("1211", "El Tumbador"), ("1212", "El Rodeo"), ("1213", "Malacatan"), ("1214", "Catarina"), ("1215", "Ayutla"), ("1216", "Ocos"), ("1217", "San Pablo"), ("1218", "El Quetzal"), ("1219", "La Reforma"), ("1220", "Pajapita"), ("1221", "Ixchiguan"), ("1222", "San Jose Ojetenam"), ("1223", "San Cristobal Cucho"), ("1224", "Sipacapa"), ("1225", "Esquipulas Palo Gordo"), ("1226", "Rio Blanco"), ("1227", "San Lorenzo"), ("1228", "La Blanca"), ("1229", "San Jose El Rodeo")],
    "13": [("1301", "Huehuetenango"), ("1302", "Chiantla"), ("1303", "Malacatancito"), ("1304", "Cuilco"), ("1305", "Nenton"), ("1306", "San Pedro Necta"), ("1307", "Jacaltenango"), ("1308", "Soloma"), ("1309", "Ixtahuacan"), ("1310", "Santa Barbara"), ("1311", "La Libertad"), ("1312", "La Democracia"), ("1313", "San Miguel Acatan"), ("1314", "San Rafael La Independencia"), ("1315", "Todos Santos Cuchumatan"), ("1316", "San Juan Atitan"), ("1317", "Santa Eulalia"), ("1318", "San Mateo Ixtatan"), ("1319", "Colotenango"), ("1320", "San Sebastian Huehuetenango"), ("1321", "Tectitan"), ("1322", "Concepcion Huista"), ("1323", "San Juan Ixcoy"), ("1324", "San Antonio Huista"), ("1325", "San Sebastian Coatan"), ("1326", "Barillas"), ("1327", "Aguacatan"), ("1328", "San Rafael Petzal"), ("1329", "San Gaspar Ixchil"), ("1330", "Santiago Chimaltenango"), ("1331", "Santa Ana Huista"), ("1332", "Union Cantinil")],
    "14": [("1401", "Santa Cruz del Quiche"), ("1402", "Chiche"), ("1403", "Chinique"), ("1404", "Zacualpa"), ("1405", "Chajul"), ("1406", "Chichicastenango"), ("1407", "Patzite"), ("1408", "San Antonio Ilotenango"), ("1409", "San Pedro Jocopilas"), ("1410", "Cunen"), ("1411", "San Juan Cotzal"), ("1412", "Joyabaj"), ("1413", "Nebaj"), ("1414", "San Andres Sajcabaja"), ("1415", "Uspantan"), ("1416", "Sacapulas"), ("1417", "San Bartolome Jocotenango"), ("1418", "Canilla"), ("1419", "Chicaman"), ("1420", "Ixcan"), ("1421", "Pachalum")],
    "15": [("1501", "Salama"), ("1502", "San Miguel Chicaj"), ("1503", "Rabinal"), ("1504", "Cubulco"), ("1505", "Granados"), ("1506", "Santa Cruz El Chol"), ("1507", "San Jeronimo"), ("1508", "Purulha")],
    "16": [("1601", "Coban"), ("1602", "Santa Cruz Verapaz"), ("1603", "San Cristobal Verapaz"), ("1604", "Tactic"), ("1605", "Tamahu"), ("1606", "Tucuru"), ("1607", "Panzos"), ("1608", "Senahu"), ("1609", "San Pedro Carcha"), ("1610", "San Juan Chamelco"), ("1611", "Lanquin"), ("1612", "Cahabon"), ("1613", "Chisec"), ("1614", "Chahal"), ("1615", "Fray Bartolome de las Casas"), ("1616", "Santa Catalina La Tinta"), ("1617", "Raxruha")],
    "17": [("1701", "Flores"), ("1702", "San Jose"), ("1703", "San Benito"), ("1704", "San Andres"), ("1705", "La Libertad"), ("1706", "San Francisco"), ("1707", "Santa Ana"), ("1708", "Dolores"), ("1709", "San Luis"), ("1710", "Sayaxche"), ("1711", "Melchor de Mencos"), ("1712", "Poptun"), ("1713", "Las Cruces"), ("1714", "El Chal")],
    "18": [("1801", "Puerto Barrios"), ("1802", "Livingston"), ("1803", "El Estor"), ("1804", "Morales"), ("1805", "Los Amates")],
    "19": [("1901", "Zacapa"), ("1902", "Estanzuela"), ("1903", "Rio Hondo"), ("1904", "Gualan"), ("1905", "Teculutan"), ("1906", "Usumatlan"), ("1907", "Cabanas"), ("1908", "San Diego"), ("1909", "La Union"), ("1910", "Huite")],
    "20": [("2001", "Chiquimula"), ("2002", "San Jose La Arada"), ("2003", "San Juan Ermita"), ("2004", "Jocotan"), ("2005", "Camotan"), ("2006", "Olopa"), ("2007", "Esquipulas"), ("2008", "Concepcion Las Minas"), ("2009", "Quezaltepeque"), ("2010", "San Jacinto"), ("2011", "Ipala")],
    "21": [("2101", "Jalapa"), ("2102", "San Pedro Pinula"), ("2103", "San Luis Jilotepeque"), ("2104", "San Manuel Chaparron"), ("2105", "San Carlos Alzatate"), ("2106", "Monjas"), ("2107", "Mataquescuintla")],
    "22": [("2201", "Jutiapa"), ("2202", "El Progreso"), ("2203", "Santa Catarina Mita"), ("2204", "Agua Blanca"), ("2205", "Asuncion Mita"), ("2206", "Yupiltepeque"), ("2207", "Atescatempa"), ("2208", "Jerez"), ("2209", "El Adelanto"), ("2210", "Zapotitlan"), ("2211", "Comapa"), ("2212", "Jalpatagua"), ("2213", "Conguaco"), ("2214", "Moyuta"), ("2215", "Pasaco"), ("2216", "San Jose Acatempa"), ("2217", "Quesada")],
}

# Pesos por departamento (aproximan la distribución real de pobreza)
_DEPTO_WEIGHTS = [
    0.08, 0.02, 0.02, 0.05, 0.04, 0.03, 0.04, 0.04, 0.05, 0.04,
    0.02, 0.06, 0.08, 0.07, 0.03, 0.10, 0.05, 0.03, 0.02, 0.04,
    0.03, 0.04,
]

AREAS = ["Urbano", "Rural"]
IPM_CLASIFICACIONES = ["Pobreza Extrema", "Pobre", "No Pobre"]
PMT_CLASIFICACIONES = ["Pobre extremo", "Pobre", "No pobre"]
NBI_CLASIFICACIONES = ["Con NBI", "Sin NBI"]
NIVELES_INSEGURIDAD = ["Seguridad Alimentaria", "Inseguridad Leve", "Inseguridad Moderada", "Inseguridad Severa"]
FASES = ["Fase 1", "Fase 2", "Fase 3"]
COMUNIDADES_LINGUISTICAS = ["Kiche", "Kaqchikel", "Mam", "Qeqchi", "Espanol"]
PUEBLOS = ["Maya", "Ladino", "Xinca", "Garifuna"]
FUENTES_AGUA = ["Tuberia dentro de la vivienda", "Tuberia fuera de la vivienda", "Pozo", "Rio o lago"]
TIPOS_SANITARIO = ["Inodoro conectado a red", "Letrina", "Pozo ciego", "No tiene"]
TIPOS_ALUMBRADO = ["Electricidad", "Candela", "Panel solar", "Gas corriente"]
COMBUSTIBLES_COCINA = ["Lenia", "Gas propano", "Electricidad", "Carbon"]

GENEROS = ["Masculino", "Femenino"]
ESTADOS_CIVILES = ["Soltero(a)", "Casado(a)", "Unido(a)", "Viudo(a)", "Divorciado(a)"]
PARENTESCOS = ["Jefe(a) de hogar", "Esposo(a)", "Hijo(a)", "Nieto(a)", "Otro pariente"]
DIFICULTADES = ["Sin dificultad", "Alguna dificultad", "Mucha dificultad", "No puede hacerlo"]
SI_NO = ["Si", "No"]
NIVELES_EDUCACION = ["Ninguno", "Primaria", "Basico", "Diversificado", "Universitario"]
ACTIVIDADES = ["Trabajo", "Busco trabajo", "Quehaceres del hogar", "Estudio"]
IDIOMAS_HABLA = ["Espanol", "Kiche", "Kaqchikel", "Mam"]

# ── Pre-generar pools de nombres (Faker es lento si se llama muchas veces) ──

_POOL_SIZE = 500

_first_names = [fake.first_name() for _ in range(_POOL_SIZE)]
_last_names = [fake.last_name() for _ in range(_POOL_SIZE)]
_female_names = [fake.name_female() for _ in range(_POOL_SIZE)]
_full_names = [fake.name() for _ in range(_POOL_SIZE)]
_addresses = [fake.address() for _ in range(_POOL_SIZE)]
_street_names = [fake.street_name() for _ in range(_POOL_SIZE)]

_TODAY = date.today()


def _rand_first():
    return random.choice(_first_names)


def _rand_last():
    return random.choice(_last_names)


def _rand_full_name():
    return random.choice(_full_names)


def _rand_female_name():
    return random.choice(_female_names)


def _rand_address():
    return random.choice(_addresses)


def _rand_street():
    return random.choice(_street_names)


def _pick_depto():
    return random.choices(DEPARTAMENTOS, weights=_DEPTO_WEIGHTS, k=1)[0]


def _pick_municipio(depto_codigo):
    munis = MUNICIPIOS_POR_DEPTO.get(depto_codigo, [])
    if munis:
        return random.choice(munis)
    code = f"{depto_codigo}{random.randint(1, 9):02d}"
    return (code, _rand_street())


def _pick_lugar(muni_codigo):
    code = f"{muni_codigo}{random.randint(1, 15):02d}"
    return (code, _rand_street())


class RSHMockDataset:
    """Genera y almacena un dataset RSH consistente."""

    def __init__(self, n_hogares: int = 5000, personas_por_hogar: int = 3):
        self.hogares: list[dict] = []
        self.personas: list[dict] = []
        self.viviendas: list[dict] = []
        self.demograficos: list[dict] = []
        self.inseguridad: list[dict] = []

        # Indices para lookup rápido
        self._hogar_idx: dict[int, int] = {}
        self._demo_idx: dict[int, int] = {}
        self._inseg_idx: dict[int, int] = {}
        self._viv_idx: dict[int, int] = {}
        self._personas_idx: dict[int, list[int]] = {}

        self._generate(n_hogares, personas_por_hogar)

    def _generate(self, n_hogares, personas_por_hogar):
        hogares = self.hogares
        personas = self.personas
        viviendas = self.viviendas
        demograficos = self.demograficos
        inseguridad_list = self.inseguridad

        for i in range(1, n_hogares + 1):
            hogar_id = 1000 + i
            vivienda_id = 2000 + i
            depto_codigo, depto_nombre = _pick_depto()
            muni_codigo, muni_nombre = _pick_municipio(depto_codigo)
            lugar_codigo, lugar_nombre = _pick_lugar(muni_codigo)
            area = "Rural" if random.random() < 0.65 else "Urbano"
            sexo_jefe = "F" if random.random() < 0.45 else "M"
            n_personas = random.randint(2, 8)
            hombres = random.randint(1, n_personas - 1)
            mujeres = n_personas - hombres
            ipm = round(random.uniform(0.0, 1.0), 4)
            ipm_clasif = (
                "Pobreza Extrema" if ipm > 0.6
                else "Pobre" if ipm > 0.3
                else "No Pobre"
            )
            pmt = round(random.uniform(100, 1000), 2)
            pmt_clasif = random.choice(PMT_CLASIFICACIONES)
            nbi = round(random.uniform(0, 5), 2)
            nbi_clasif = random.choice(NBI_CLASIFICACIONES)
            anio = random.choice([2023, 2024])
            fase = random.choice(FASES)
            cui_jefe = random.randint(1000000000000, 9999999999999)
            nombre_jefe = _rand_full_name()
            latitud = round(random.uniform(13.5, 17.8), 6)
            longitud = round(random.uniform(-92.2, -88.2), 6)

            hogar = {
                "hogar_id": hogar_id,
                "vivienda_id": vivienda_id,
                "departamento": depto_nombre,
                "departamento_codigo": depto_codigo,
                "municipio": muni_nombre,
                "municipio_codigo": muni_codigo,
                "lugar_poblado": lugar_nombre,
                "lugarpoblado_codigo": lugar_codigo,
                "area": area,
                "tipo_area_id": 1 if area == "Urbano" else 2,
                "numero_personas": n_personas,
                "hombres": hombres,
                "mujeres": mujeres,
                "ipm_gt": ipm,
                "ipm_gt_clasificacion": ipm_clasif,
                "pmt": pmt,
                "pmt_clasificacion": pmt_clasif,
                "nbi": nbi,
                "nbi_clasificacion": nbi_clasif,
                "cui_jefe_hogar": cui_jefe,
                "nombre_jefe_hogar": nombre_jefe,
                "sexo_jefe_hogar": sexo_jefe,
                "anio": anio,
                "geolocalizacion_vivienda_latitud": latitud,
                "geolocalizacion_vivienda_longitud": longitud,
                "direccion_vivienda": _rand_address(),
                "celular_jefe_hogar": random.randint(10000000, 99999999),
                "cui_madre": random.randint(1000000000000, 9999999999999),
                "nombre_madre": _rand_female_name(),
                "celular_madre": random.randint(10000000, 99999999),
                "fase": fase,
                "fase_estado": "Completada",
                "fecha": date(anio, random.randint(1, 12), random.randint(1, 28)),
                "nbi_indicadores": "Vivienda,Educacion",
            }
            self._hogar_idx[hogar_id] = len(hogares)
            hogares.append(hogar)

            # Demograficos
            comunidad = random.choice(COMUNIDADES_LINGUISTICAS)
            pueblo = random.choice(PUEBLOS)
            p_0_5 = random.randint(0, 2)
            adultos_mayores = random.randint(0, 2)
            demo = {
                "hogar_id": hogar_id,
                "anio_captura": anio,
                "total_personas": n_personas,
                "total_hombres": hombres,
                "total_mujeres": mujeres,
                "personas_embarazadas": random.randint(0, 1),
                "personas_con_dificultad": random.randint(0, 2),
                "primera_infancia": p_0_5,
                "ninos": random.randint(0, 3),
                "adolescentes": random.randint(0, 2),
                "jovenes": random.randint(0, 2),
                "adultos": random.randint(1, 4),
                "adultos_mayores": adultos_mayores,
                "p_0_5": p_0_5,
                "tipo_jefatura": "Femenina" if sexo_jefe == "F" else "Masculina",
                "comunidad_linguistica": comunidad,
                "pueblo_de_pertenencia": pueblo,
            }
            self._demo_idx[hogar_id] = len(demograficos)
            demograficos.append(demo)

            # Inseguridad alimentaria
            nivel = random.choice(NIVELES_INSEGURIDAD)
            inseg = {
                "hogar_id": hogar_id,
                "nivel_inseguridad_alimentaria": nivel,
                "puntos_elcsa": random.randint(0, 15),
                "cantidad_personas": n_personas,
                "cantidad_nino": random.randint(0, n_personas // 2),
            }
            self._inseg_idx[hogar_id] = len(inseguridad_list)
            inseguridad_list.append(inseg)

            # Vivienda
            viv = {
                "id": vivienda_id,
                "hogar_id": hogar_id,
                "cv1_condicion_vivienda": random.choice(["Ocupada", "Desocupada"]),
                "cv2_tipo_vivienda_particular": random.choice(["Casa formal", "Apartamento", "Rancho"]),
                "cv3_material_predominante_en_paredes_exteriores": random.choice(["Block", "Madera", "Lamina", "Adobe"]),
                "cv4_material_predominante_techo": random.choice(["Lamina", "Concreto", "Teja", "Palma"]),
                "cv5_material_predominante_piso": random.choice(["Torta de cemento", "Tierra", "Ladrillo ceramico"]),
                "cv7_vivienda_que_ocupa_este_hogar_es": random.choice(["Propia", "Alquilada", "Prestada"]),
                "cv8_persona_propietaria_de_esta_vivienda_es": random.choice(["Hombre", "Mujer", "Ambos"]),
                "ih1_personas_viven_habitualmente_vivienda": n_personas + random.randint(0, 2),
                "ch2_cuantas_personas_residen_habitualmente_en_hogar": n_personas,
                "ch2_numero_habitantes_hombres": hombres,
                "ch2_numero_habitantes_mujeres": mujeres,
                "ch2_numero_habitantes_ninios": random.randint(0, hombres),
                "ch2_numero_habitantes_ninias": random.randint(0, mujeres),
                "ch3_cuantos_cuartos_dispone_hogar": random.randint(1, 5),
                "ch4_total_cuartos_utiliza_como_dormitorios": random.randint(1, 3),
                "ch05_dispone_en_hogar_un_cuarto_exclusivo_para_cocinar": random.choice(SI_NO),
                "ch06_descripcion": random.choice(COMBUSTIBLES_COCINA),
                "ch07_descripcion": random.choice(SI_NO),
                "ch08_descripcion": random.choice(["Dentro de la vivienda", "Fuera de la vivienda"]),
                "ch09_descripcion": random.choice(SI_NO),
                "ch10_descripcion": random.choice(FUENTES_AGUA),
                "ch11_mes_pasado_dias_completos_sin_agua": random.randint(0, 10),
                "ch12_descripcion": random.choice(["Cloro", "Hierve", "Ninguno"]),
                "ch13_descripcion": random.choice(TIPOS_SANITARIO),
                "ch14_uso_servicio_sanitario": random.choice(["Uso exclusivo del hogar", "Compartido"]),
                "ch15_descripcion": random.choice(["Drenaje", "A flor de tierra", "Rio"]),
                "ch16_descripcion": random.choice(TIPOS_ALUMBRADO),
                "ch17_mes_pasado_cuantos_dias_continuos_sin_energia_electrica": random.randint(0, 7),
                "ch19_descripcion": random.choice(["Servicio municipal", "La queman", "La entierran"]),
                "ch_18_bien_hogar_radio": random.choice(SI_NO),
                "ch_18_bien_hogar_estufa_lenia": random.choice(SI_NO),
                "ch_18_bien_hogar_estufa_gas": random.choice(SI_NO),
                "ch_18_bien_hogar_televisor": random.choice(SI_NO),
                "ch_18_bien_hogar_refrigerador": random.choice(SI_NO),
                "ch_18_bien_hogar_lavadora": random.choice(SI_NO),
                "ch_18_bien_hogar_compu_laptop": random.choice(SI_NO),
                "ch_18_bien_hogar_internet": random.choice(SI_NO),
                "ch_18_bien_hogar_moto": random.choice(SI_NO),
                "ch_18_bien_hogar_carro": random.choice(SI_NO),
                "sn1_descripcion": random.choice(SI_NO),
                "sn2_descripcion": random.choice(SI_NO),
                "sn3_aduto_sin_alimentacion_saludable": random.choice(SI_NO),
                "sn3_nino_sin_alimentacion_saludable": random.choice(SI_NO),
                "sn4_adulto_alimentacion_variedad": random.choice(SI_NO),
                "sn4_nino_alimentacion_variedad": random.choice(SI_NO),
                "sn5_adulto_sin_tiempo_comida": random.choice(SI_NO),
                "sn5_nino_sin_tiempo_comida": random.choice(SI_NO),
                "sn6_adulto_comio_menos": random.choice(SI_NO),
                "sn6_nino_no_comio_menos": random.choice(SI_NO),
                "sn7_adulto_sintio_hambre": random.choice(SI_NO),
                "sn7_nino_sintio_hambre": random.choice(SI_NO),
                "sn8_adulto_comio_un_tiempo": random.choice(SI_NO),
                "sn8_menor18_comio_un_tiempo": random.choice(SI_NO),
            }
            self._viv_idx[hogar_id] = len(viviendas)
            viviendas.append(viv)

            # Personas
            persona_indices = []
            for j in range(1, personas_por_hogar + 1):
                persona_id = hogar_id * 100 + j
                edad = random.randint(0, 80)
                sexo = random.choice(GENEROS)
                persona = {
                    "personas_id": persona_id,
                    "hogar_id": hogar_id,
                    "pd1_numero_correlativo_persona_hogar": j,
                    "pd4_numero_documento_identificacion": random.randint(1000000000000, 9999999999999) if edad >= 18 else None,
                    "pd5_1_primer_nombre": _rand_first(),
                    "pd5_2_segundo_nombre": _rand_first() if random.random() > 0.3 else "",
                    "pd5_3_tercer_nombre": "",
                    "pd5_4_cuarto_nombre": "",
                    "pd5_5_primer_apellido": _rand_last(),
                    "pd5_6_segundo_apellido": _rand_last(),
                    "pd5_7_apellido_casada": "" if sexo == "Masculino" else (_rand_last() if random.random() > 0.7 else ""),
                    "pd6_descripcion": sexo,
                    "pd7_fecha_nacimiento": _TODAY - timedelta(days=edad * 365 + random.randint(0, 364)),
                    "pd8_anios_cumplidos": edad,
                    "pd9_descripcion": random.choice(ESTADOS_CIVILES) if edad >= 18 else "Soltero(a)",
                    "pd10_celular": random.randint(10000000, 99999999) if edad >= 12 else None,
                    "pd11_descripcion": PARENTESCOS[0] if j == 1 else random.choice(PARENTESCOS[1:]),
                    "pd12_descripcion": random.choice(PUEBLOS),
                    "pd13_descripcion": random.choice(COMUNIDADES_LINGUISTICAS),
                    "pd14_descripcion": random.choice(IDIOMAS_HABLA),
                    "ps1_1_descripcion": random.choice(DIFICULTADES),
                    "ps1_2_descripcion": random.choice(DIFICULTADES),
                    "ps1_3_descripcion": random.choice(DIFICULTADES),
                    "ps1_4_descripcion": random.choice(DIFICULTADES),
                    "ps1_5_descripcion": random.choice(DIFICULTADES),
                    "ps1_6_descripcion": random.choice(DIFICULTADES),
                    "ps13_descripcion": "Si" if (sexo == "Femenino" and 15 <= edad <= 45 and random.random() > 0.8) else "No",
                    "pe1_descripcion": "Si" if edad >= 7 and random.random() > 0.15 else "No",
                    "pe2_descripcion": "Si" if 5 <= edad <= 18 and random.random() > 0.2 else "No",
                    "pe7_descripcion": random.choice(NIVELES_EDUCACION),
                    "ie1_descripcion": random.choice(ACTIVIDADES) if edad >= 15 else "Estudio",
                    "ie3_descripcion": random.choice(SI_NO) if edad >= 15 else "No",
                }
                persona_indices.append(len(personas))
                personas.append(persona)

            self._personas_idx[hogar_id] = persona_indices

    # ── Accessors con lookup O(1) ────────────────────────────────────

    def get_hogar(self, hogar_id: int) -> dict | None:
        idx = self._hogar_idx.get(hogar_id)
        return self.hogares[idx] if idx is not None else None

    def get_demografico(self, hogar_id: int) -> dict | None:
        idx = self._demo_idx.get(hogar_id)
        return self.demograficos[idx] if idx is not None else None

    def get_inseguridad(self, hogar_id: int) -> dict | None:
        idx = self._inseg_idx.get(hogar_id)
        return self.inseguridad[idx] if idx is not None else None

    def get_vivienda(self, hogar_id: int) -> dict | None:
        idx = self._viv_idx.get(hogar_id)
        return self.viviendas[idx] if idx is not None else None

    def get_personas_hogar(self, hogar_id: int) -> list[dict]:
        indices = self._personas_idx.get(hogar_id, [])
        return [self.personas[i] for i in indices]

    def get_first_hogar_id(self) -> int:
        return self.hogares[0]["hogar_id"]

    def get_nonexistent_hogar_id(self) -> int:
        return 999999
