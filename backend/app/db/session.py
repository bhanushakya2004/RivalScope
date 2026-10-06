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
