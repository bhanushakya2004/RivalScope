"""Database session and declarative base configuration."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy domain models."""

    pass


def get_engine():
    """Create SQLAlchemy engine with connection pooling."""
    settings = get_settings()
    url = settings.database_url

    # Configure connection args based on dialect
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif "postgres" in url:
        connect_args["connect_timeout"] = 3

    return create_engine(
        url,
        echo=settings.debug and settings.env == "development",
        pool_pre_ping=True,
        connect_args=connect_args,
    )


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_agno_db():
    """Return Agno's native storage DB instance for sessions, runs, and memories."""
    settings = get_settings()
    url = settings.database_url
    try:
        if "postgres" in url:
            from agno.db.postgres import PostgresDb

            return PostgresDb(
                db_engine=engine,
                db_url=url,
                session_table="agno_sessions",
                runs_table="agno_runs",
                memory_table="agno_memories",
                create_schema=True,
            )
        elif "sqlite" in url:
            from agno.db.sqlite import SqliteDb

            return SqliteDb(
                db_engine=engine,
                session_table="agno_sessions",
                create_schema=True,
            )
    except Exception as exc:
        import logging

        logging.getLogger("db.session").warning(f"Could not initialize Agno native DB: {exc}")
    return None
