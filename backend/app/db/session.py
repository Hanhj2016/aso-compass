from collections.abc import Generator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.core.settings import get_settings


def build_engine(
    url: str,
    pool_size: int = 3,
    max_overflow: int = 2,
    pool_timeout_seconds: float = 15.0,
) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    pool_args = (
        {}
        if url.startswith("sqlite")
        else {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout_seconds,
        }
    )
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True, **pool_args)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


settings = get_settings()
engine = build_engine(
    settings.database_url,
    settings.db_pool_size,
    settings.db_max_overflow,
    settings.db_pool_timeout_seconds,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
