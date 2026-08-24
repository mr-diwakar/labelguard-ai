"""
SQLAlchemy engine and session factory.

The engine is created on first use so the API process can start, and health
checks can pass, even when PostgreSQL is not running. Connecting happens only
when a session is actually used.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger

logger = get_logger("db")

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def create_engine_from_settings(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url_value,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
        connect_args={"connect_timeout": 3},
    )


def get_engine(settings: Settings | None = None) -> Engine:
    global _engine

    if _engine is None:
        _engine = create_engine_from_settings(settings or get_settings())
        logger.info("stage=db event=engine_created")

    return _engine


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    global _session_factory

    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(settings),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency. Yields one session per request and always closes it."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database(engine: Engine | None = None) -> bool:
    """Returns True when PostgreSQL answers a trivial query."""
    target = engine or get_engine()

    try:
        with target.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.warning("stage=db event=unreachable")
        return False

    return True


def dispose_engine() -> None:
    """Drops the process-wide pool. Called on application shutdown and in tests."""
    global _engine, _session_factory

    if _engine is not None:
        _engine.dispose()
        logger.info("stage=db event=engine_disposed")

    _engine = None
    _session_factory = None
