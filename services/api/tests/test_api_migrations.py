from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from styleid_api.db.models import Base

INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def test_alembic_upgrade_head_matches_models(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'migrated.db'}"
    cfg = Config(str(INI))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert tables == set(Base.metadata.tables)
    for name, table in Base.metadata.tables.items():
        migrated = {c["name"] for c in inspector.get_columns(name)}
        assert migrated == {c.name for c in table.columns}, name
    fks = {fk["name"] for fk in inspector.get_foreign_keys("products")}
    assert "fk_products_chart_id_size_charts" in fks

    command.downgrade(cfg, "base")
    assert set(inspect(create_engine(url)).get_table_names()) <= {"alembic_version"}
