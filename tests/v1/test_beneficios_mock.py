"""
Quick test to verify beneficios_x_hogar mock data works for all institutions.
"""
from tests.v1.rsh_mock_data import RSHMockDataset
from tests.v1.mock_ch_client import MockClickHouseClient


def test_beneficios_generation():
    """Verify beneficios_x_hogar data is generated with all program columns."""
    dataset = RSHMockDataset(n_hogares=200, personas_por_hogar=3)

    assert len(dataset.beneficios_x_hogar) == 200

    # Verify fields are present
    first = dataset.beneficios_x_hogar[0]
    required_fields = [
        "hogar_id", "ig3_departamento", "ig3_departamento_codigo",
        "ig4_municipio", "ig4_municipio_codigo", "ig5_lugar_poblado",
        "area", "numero_personas", "hombres", "mujeres",
        "ipm_gt", "ipm_gt_clasificacion",
        "prog_fodes", "prog_maga", "prog_mides",
        "estufa_mejorada", "ecofiltro", "letrina", "repello", "piso",
        "sembro", "crio_animal",
        "bono_unico", "bono_salud", "bono_educacion", "bolsa_social",
    ]
    for field in required_fields:
        assert field in first, f"Missing field: {field}"

    # Verify rough distribution
    with_fodes = sum(1 for b in dataset.beneficios_x_hogar if b["prog_fodes"] == 1)
    with_maga = sum(1 for b in dataset.beneficios_x_hogar if b["prog_maga"] == 1)
    with_mides = sum(1 for b in dataset.beneficios_x_hogar if b["prog_mides"] == 1)
    assert 30 <= with_fodes <= 90  # ~30% of 200
    assert 25 <= with_maga <= 80  # ~25% of 200
    assert 50 <= with_mides <= 120  # ~40% of 200

    # Verify accessor
    hogar_id = dataset.hogares[0]["hogar_id"]
    beneficio = dataset.get_beneficio(hogar_id)
    assert beneficio is not None
    assert beneficio["hogar_id"] == hogar_id


def test_consulta_handlers_fodes():
    """Verify consulta handlers work for FODES."""
    client = MockClickHouseClient()

    result = client.query(
        "SELECT count() FROM rsh.beneficios_x_hogar WHERE prog_fodes = 1", {}
    )
    assert result.column_names == ["total"]
    total_fodes = result.result_rows[0][0]
    assert total_fodes > 0

    result = client.query(
        "SELECT hogar_id, estufa_mejorada, ecofiltro, letrina, repello, piso "
        "FROM rsh.beneficios_x_hogar WHERE prog_fodes = 1 LIMIT 10 OFFSET 0",
        {"limit": 10, "offset": 0},
    )
    assert "hogar_id" in result.column_names
    assert "estufa_mejorada" in result.column_names
    assert len(result.result_rows) <= 10


def test_consulta_handlers_maga():
    """Verify consulta handlers work for MAGA."""
    client = MockClickHouseClient()

    result = client.query(
        "SELECT count() FROM rsh.beneficios_x_hogar WHERE prog_maga = 1", {}
    )
    total_maga = result.result_rows[0][0]
    assert total_maga > 0

    result = client.query(
        "SELECT hogar_id, sembro, crio_animal "
        "FROM rsh.beneficios_x_hogar WHERE prog_maga = 1 LIMIT 5 OFFSET 0",
        {"limit": 5, "offset": 0},
    )
    assert "hogar_id" in result.column_names
    assert "sembro" in result.column_names
    assert "crio_animal" in result.column_names

    # sumIf for MAGA interventions
    result = client.query(
        "SELECT sumIf(1, sembro = 1) as sembro, sumIf(1, crio_animal = 1) as crio_animal "
        "FROM rsh.beneficios_x_hogar WHERE prog_maga = 1",
        {},
    )
    assert "sembro" in result.column_names
    assert "crio_animal" in result.column_names


def test_consulta_handlers_mides():
    """Verify consulta handlers work for MIDES."""
    client = MockClickHouseClient()

    result = client.query(
        "SELECT count() FROM rsh.beneficios_x_hogar WHERE prog_mides = 1", {}
    )
    total_mides = result.result_rows[0][0]
    assert total_mides > 0

    result = client.query(
        "SELECT hogar_id, bono_unico, bono_salud, bono_educacion, bolsa_social "
        "FROM rsh.beneficios_x_hogar WHERE prog_mides = 1 LIMIT 5 OFFSET 0",
        {"limit": 5, "offset": 0},
    )
    assert "hogar_id" in result.column_names
    assert "bono_unico" in result.column_names
    assert "bolsa_social" in result.column_names


def test_consulta_detalle_scoped():
    """Verify detalle respects base_filter scope."""
    client = MockClickHouseClient()

    # Find a hogar with prog_maga=1 but prog_fodes=0
    target = None
    for b in client.dataset.beneficios_x_hogar:
        if b["prog_maga"] == 1 and b["prog_fodes"] == 0:
            target = b
            break

    if target:
        # Should return result when queried with MAGA filter
        result = client.query(
            f"SELECT * FROM rsh.beneficios_x_hogar "
            f"WHERE prog_maga = 1 AND hogar_id = {{hogar_id:Int64}} "
            f"sembro crio_animal",
            {"hogar_id": target["hogar_id"]},
        )
        assert len(result.result_rows) == 1

        # Should NOT return when queried with FODES filter
        result = client.query(
            f"SELECT * FROM rsh.beneficios_x_hogar "
            f"WHERE prog_fodes = 1 AND hogar_id = {{hogar_id:Int64}} "
            f"estufa_mejorada ecofiltro letrina repello piso",
            {"hogar_id": target["hogar_id"]},
        )
        assert len(result.result_rows) == 0
