"""
Database Engine & Session Factory

SQLite for local development, upgradeable to PostgreSQL via DATABASE_URL.
"""

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# Default: SQLite in project data/ directory
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "aquaforge.db"
_DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH}")

# SQLite needs check_same_thread=False for FastAPI async
_connect_args = (
    {"check_same_thread": False} if _DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(_DATABASE_URL, echo=False, connect_args=_connect_args)


def init_db() -> None:
    """Create all tables. Safe to call multiple times."""
    # Import models so SQLModel registers them
    import swim_ai_reflex.backend.persistence.db_models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session."""
    return Session(engine)


def get_db_url() -> str:
    """Return the active database URL (for diagnostics)."""
    return _DATABASE_URL
