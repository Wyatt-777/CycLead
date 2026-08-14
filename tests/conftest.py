"""Shared isolated SQLite fixtures for persistence tests."""

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db import Base, create_db_engine, create_session_factory


@pytest.fixture
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    """Yield a fresh SQLite session with foreign-key enforcement enabled."""

    database_url = f"sqlite:///{(tmp_path / 'cyclelead.db').as_posix()}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
