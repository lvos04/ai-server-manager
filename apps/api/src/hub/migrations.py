"""Alembic-hulpfuncties: migraties uitvoeren vanuit code (image) of vanuit de broncode (ontwikkeling/CI)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.orm import Session

import hub


def script_location() -> Path:
    pkg = Path(hub.__file__).resolve().parent
    candidates = [pkg / "_alembic", pkg.parents[1] / "alembic"]
    for c in candidates:
        if (c / "env.py").exists():
            return c
    raise FileNotFoundError("alembic-migraties niet gevonden")


def alembic_config(url: str | None = None) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(script_location()))
    if url:
        cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def upgrade(url: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(url), revision)


def downgrade(url: str, revision: str) -> None:
    command.downgrade(alembic_config(url), revision)


@lru_cache(maxsize=1)
def head_revision() -> str | None:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def current_revision(db: Session) -> str | None:
    conn = db.connection()
    return MigrationContext.configure(conn).get_current_revision()


def pending_migrations(url: str) -> bool:
    from sqlalchemy import create_engine

    engine = create_engine(url, hide_parameters=True)  # geen parameterwaarden in fout of log (V-094)
    try:
        with engine.connect() as conn:
            cur = MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()
    return cur != head_revision()
