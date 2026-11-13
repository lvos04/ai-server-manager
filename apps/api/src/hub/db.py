"""Database-engine en sessies (SQLAlchemy 2, psycopg 3)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(url: str) -> Engine:
    # hide_parameters: een databasefout noemt de parameterwaarden niet in de fout en dus niet in de log (V-094).
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5, future=True, hide_parameters=True)


def make_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Sessie per request; schrijvende routes committen expliciet, de rest wordt bij sluiten teruggedraaid."""
    db = factory()
    try:
        yield db
    finally:
        db.close()
