from api.v1.services.query_engine.export import _normalize_export_value


class TestQueryExportService:
    def test_normalize_export_value_decodes_bytes(self):
        assert _normalize_export_value(b"1601") == "1601"
