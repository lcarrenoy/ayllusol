"""ORM tables. Ledger rows are append-only: corrections are new adjustment entries."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, Money
from .ledger import Entry, EntryType


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AppendOnlyError(RuntimeError):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    credit_limit: Mapped[Decimal] = mapped_column(Money)
    credit_days: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Money)
    on: Mapped[date] = mapped_column("on_date", Date, index=True)
    due: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    confirmation: Mapped[Confirmation | None] = relationship(lazy="selectin")

    def to_entry(self) -> Entry:
        return Entry(self.id, self.customer_id, EntryType(self.type), self.amount,
                     self.on, self.due, self.confirmation is not None)


class Confirmation(Base):
    """The neighbor's acknowledgement, stored as its own event so entries never change."""

    __tablename__ = "confirmations"

    entry_id: Mapped[str] = mapped_column(ForeignKey("ledger_entries.id"), primary_key=True)
    channel: Mapped[str] = mapped_column(String(16), default="counter")  # counter | whatsapp
    confirmed_at: Mapped[datetime] = mapped_column(default=utcnow)


class Seal(Base):
    """A daily Merkle root. Re-sealing a day adds a row; the latest one wins."""

    __tablename__ = "seals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    merkle_root: Mapped[str] = mapped_column(String(64))
    entries: Mapped[int]
    tx: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


@event.listens_for(LedgerEntry, "before_update")
@event.listens_for(LedgerEntry, "before_delete")
@event.listens_for(Confirmation, "before_update")
@event.listens_for(Confirmation, "before_delete")
def _append_only(mapper, connection, target) -> None:
    raise AppendOnlyError(f"{type(target).__name__} is append-only; post an adjustment instead")
