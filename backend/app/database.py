"""SQLAlchemy engine, session factory and declarative base.

A single SQLite file (``detech_jobs.db``) lives next to this package so the
project is fully portable — clone, install, seed, run.
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Resolve the DB path relative to the backend root so it works regardless of the
# current working directory used to launch uvicorn.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BACKEND_ROOT, "detech_jobs.db")
DATABASE_URL = os.environ.get("DETECH_DATABASE_URL", f"sqlite:///{DB_PATH}")

# check_same_thread=False is required for SQLite under the threaded uvicorn worker.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped session and guaranteeing close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Import models first so they register on the metadata."""
    from app import models  # noqa: F401  (registers mappers)

    Base.metadata.create_all(bind=engine)
