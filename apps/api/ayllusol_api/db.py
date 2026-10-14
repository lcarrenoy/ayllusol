"""Database wiring: engine, session factory and an exact Money column type."""
from __future__ import annotations

import os
from collections.abc import Iterator
from decimal import Decimal

from sqlalchemy import Engine, Integer, Numeric, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

CENT = Decimal("0.01")


class Base(DeclarativeBase):
    pass


class Money(TypeDecorator):
    """NUMERIC(12,2) on PostgreSQL; integer cents on SQLite.

    SQLite has no exact decimal storage (NUMERIC falls back to REAL), so cents
    as integers is the only way to keep money exact there.
    """

    impl = Numeric(12, 2)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(Integer())
        return dialect.type_descriptor(Numeric(12, 2, asdecimal=True))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        value = Decimal(value).quantize(CENT)
        return int(value * 100) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            return (Decimal(value) / 100).quantize(CENT)
        return Decimal(value).quantize(CENT)


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine(os.getenv("DATABASE_URL", "sqlite:///./ayllusol.db"))
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db(bind: Engine = engine) -> None:
    # Hackathon shortcut: create tables on startup. Alembic once we move to PostgreSQL.
    from . import models  # noqa: F401  (registers tables on Base.metadata)

    Base.metadata.create_all(bind)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
