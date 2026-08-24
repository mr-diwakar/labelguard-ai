"""Phase 3: engine and session factory exist without a live database."""

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.connection import (
    check_database,
    create_engine_from_settings,
    dispose_engine,
    get_db,
    get_engine,
    get_session_factory,
)


def setup_function() -> None:
    dispose_engine()


def teardown_function() -> None:
    dispose_engine()


def test_database_url_is_secret_and_uses_psycopg() -> None:
    settings = Settings(database_url="postgresql://inspector:secret@127.0.0.1:5432/labelguard")

    assert settings.database_url_value == "postgresql+psycopg://inspector:secret@127.0.0.1:5432/labelguard"
    assert "secret" not in repr(settings)
    assert "secret" not in str(settings.database_url)


def test_non_postgres_url_is_rejected() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(database_url="sqlite:///./labelguard.db")


def test_engine_is_created_without_connecting() -> None:
    settings = Settings(database_url="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/labelguard")
    engine = create_engine_from_settings(settings)

    assert engine.dialect.name == "postgresql"
    assert engine.url.drivername == "postgresql+psycopg"
    engine.dispose()


def test_session_factory_binds_to_process_engine() -> None:
    settings = Settings()
    engine = get_engine(settings)
    factory = get_session_factory(settings)
    session = factory()

    assert session.get_bind() is engine
    session.close()


def test_get_db_yields_and_closes_session() -> None:
    generator = get_db()
    session = next(generator)

    assert isinstance(session, Session)
    generator.close()
    assert not session.in_transaction()


def test_check_database_returns_false_when_postgres_is_down() -> None:
    settings = Settings(database_url="postgresql+psycopg://postgres:postgres@127.0.0.1:1/labelguard")
    engine = create_engine_from_settings(settings)

    assert check_database(engine) is False
    engine.dispose()
