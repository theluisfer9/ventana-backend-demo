"""
Migrates the 3 hardcoded institutional presets to the data_sources tables.
Run from backend/: python scripts/seed_data_sources.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from api.v1.config.database import pg_sync_engine
from api.v1.models.institution import Institution
from api.v1.models.data_source import (
    DataSource, DataSourceColumn, ColumnDataType, ColumnCategory,
)
from api.v1.config.institutional_presets import INSTITUTIONAL_PRESETS

GEO_COLUMNS = {
    "hogar_id", "ig3_departamento", "ig3_codigo_departamento",
    "ig4_municipio", "ig4_codigo_municipio", "ig6_lugar_poblado", "ig8_area",
}
MEASURE_COLUMNS = {
    "personas", "hombres", "mujeres", "ipm_gt", "pmt", "nbi",
    "total_intervenciones",
}

def classify_column(col_name: str, intervention_columns: list[str]) -> tuple[ColumnDataType, ColumnCategory]:
    if col_name in intervention_columns:
        return ColumnDataType.BOOLEAN, ColumnCategory.INTERVENTION
    if col_name in GEO_COLUMNS:
        return ColumnDataType.TEXT, ColumnCategory.GEO
    if col_name in MEASURE_COLUMNS:
        if col_name == "ipm_gt":
            return ColumnDataType.FLOAT, ColumnCategory.MEASURE
        return ColumnDataType.INTEGER, ColumnCategory.MEASURE
    return ColumnDataType.TEXT, ColumnCategory.DIMENSION


def seed():
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=pg_sync_engine)
    db: Session = SessionLocal()

    try:
        for code, preset in INSTITUTIONAL_PRESETS.items():
            existing = db.query(DataSource).filter(DataSource.code == code).first()
            if existing:
                print(f"  DataSource '{code}' already exists, skipping.")
                continue

            institution = db.query(Institution).filter(Institution.code == code).first()

            ds = DataSource(
                code=code,
                name=preset["name"],
                ch_table=preset["table"],
                base_filter_columns=preset.get("base_filter_columns", []),
                base_filter_logic=preset.get("base_filter_logic", "OR"),
                institution_id=institution.id if institution else None,
            )
            db.add(ds)
            db.flush()

            all_cols = list(dict.fromkeys(
                preset["columns"]
                + preset.get("detail_columns", [])
                + preset["intervention_columns"]
            ))
            intervention_cols = preset["intervention_columns"]
            labels = preset["labels"]

            for order, col_name in enumerate(all_cols):
                data_type, category = classify_column(col_name, intervention_cols)
                is_filterable = col_name in preset["allowed_filters"] or col_name in intervention_cols
                dsc = DataSourceColumn(
                    datasource_id=ds.id,
                    column_name=col_name,
                    label=labels.get(col_name, col_name),
                    data_type=data_type,
                    category=category,
                    is_selectable=True,
                    is_filterable=is_filterable,
                    display_order=order,
                )
                db.add(dsc)

            print(f"  Seeded DataSource '{code}' with {len(all_cols)} columns.")

        db.commit()
        print("Done.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
