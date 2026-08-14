from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect

from alembic import command
from app.db import create_db_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = {
    "alembic_version",
    "discovery_runs",
    "evidences",
    "leads",
    "queries",
    "raw_candidates",
    "reviews",
}


def migration_config(database_path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_initial_migration_can_upgrade_and_downgrade_an_empty_database(tmp_path: Path) -> None:
    config = migration_config(tmp_path / "cyclelead.db")
    command.upgrade(config, "head")

    engine = create_db_engine(config.get_main_option("sqlalchemy.url"))
    assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
    engine.dispose()

    command.downgrade(config, "base")
    engine = create_db_engine(config.get_main_option("sqlalchemy.url"))
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert not (EXPECTED_TABLES - {"alembic_version"}) & tables
