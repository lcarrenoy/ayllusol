"""API over the pure ledger, persisted with SQLAlchemy (SQLite in dev)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_session, init_db
from .ledger import Entry, EntryType, aging, balance, daily_root, dso
from .models import Confirmation, Customer, LedgerEntry, Seal


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="AylluSol API", version="0.2.0", lifespan=lifespan)
Db = Annotated[Session, Depends(get_session)]

Amount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    credit_limit: Amount
    credit_days: int = Field(default=7, ge=1, le=60)


class ChargeIn(BaseModel):
    customer_id: str
    amount: Amount
    on: date | None = None


class PaymentIn(BaseModel):
    customer_id: str
    amount: Amount
    on: date | None = None


def _customer(db: Session, cid: str) -> Customer:
    c = db.get(Customer, cid)
    if c is None:
        raise HTTPException(404, "customer not found")
    return c


def _entries(db: Session, customer_id: str | None = None) -> list[Entry]:
    q = select(LedgerEntry)
    if customer_id is not None:
        q = q.where(LedgerEntry.customer_id == customer_id)
    return [row.to_entry() for row in db.scalars(q)]


def _customer_out(c: Customer, owed: Decimal | None = None) -> dict:
    out = {"id": c.id, "name": c.name, "credit_limit": str(c.credit_limit), "credit_days": c.credit_days}
    if owed is not None:
        out["balance"] = str(owed)
    return out


@app.post("/customers")
def create_customer(body: CustomerIn, db: Db) -> dict:
    c = Customer(id=uuid4().hex[:8], **body.model_dump())
    db.add(c)
    db.commit()
    return _customer_out(c)


@app.get("/customers")
def list_customers(db: Db) -> list[dict]:
    entries = _entries(db)
    return [_customer_out(c, balance(entries, c.id)) for c in db.scalars(select(Customer).order_by(Customer.name))]


@app.post("/charges")
def add_charge(body: ChargeIn, db: Db, override_limit: bool = False) -> dict:
    c = _customer(db, body.customer_id)
    on = body.on or date.today()
    new_balance = balance(_entries(db, c.id), c.id) + body.amount
    if new_balance > c.credit_limit and not override_limit:
        raise HTTPException(409, f"over limit: would owe {new_balance} of {c.credit_limit}; owner must confirm")
    row = LedgerEntry(id=uuid4().hex, customer_id=c.id, type=EntryType.CHARGE.value, amount=body.amount,
                      on=on, due=on + timedelta(days=c.credit_days))
    db.add(row)
    db.commit()
    return {"entry_id": row.id, "balance": str(new_balance), "status": "pending_confirmation"}


@app.post("/entries/{entry_id}/confirm")
def confirm(entry_id: str, db: Db, channel: str = "counter") -> dict:
    row = db.get(LedgerEntry, entry_id)
    if row is None:
        raise HTTPException(404, "entry not found")
    if row.confirmation is None:  # idempotent: a second confirm is a no-op
        db.add(Confirmation(entry_id=entry_id, channel=channel))
        db.commit()
    return {"entry_id": entry_id, "confirmed": True}


@app.post("/payments")
def add_payment(body: PaymentIn, db: Db) -> dict:
    c = _customer(db, body.customer_id)
    db.add(LedgerEntry(id=uuid4().hex, customer_id=c.id, type=EntryType.PAYMENT.value,
                       amount=body.amount, on=body.on or date.today()))
    db.commit()
    return {"balance": str(balance(_entries(db, c.id), c.id))}


@app.get("/customers/{cid}/balance")
def get_balance(cid: str, db: Db) -> dict:
    c = _customer(db, cid)
    return {"customer_id": cid, "balance": str(balance(_entries(db, cid), cid)), "limit": str(c.credit_limit)}


@app.get("/customers/{cid}/entries")
def statement(cid: str, db: Db) -> dict:
    """Running account of one neighbor, oldest first."""
    _customer(db, cid)
    rows = db.scalars(select(LedgerEntry).where(LedgerEntry.customer_id == cid)
                      .order_by(LedgerEntry.on, LedgerEntry.created_at))
    running, lines = Decimal("0.00"), []
    for row in rows:
        running += row.to_entry().signed()
        lines.append({"entry_id": row.id, "type": row.type, "amount": str(row.amount), "on": row.on.isoformat(),
                      "confirmed": row.confirmation is not None, "running_balance": str(running)})
    return {"customer_id": cid, "balance": str(running), "entries": lines}


@app.get("/dashboard/portfolio")
def portfolio(db: Db, today: date | None = None) -> dict:
    today = today or date.today()
    ids = list(db.scalars(select(Customer.id)))
    entries = _entries(db)
    total = sum((balance(entries, cid) for cid in ids), Decimal("0"))
    since = today - timedelta(days=30)
    sales = sum((e.amount for e in entries if e.type is EntryType.CHARGE and e.on > since), Decimal("0"))
    return {
        "receivables": str(total),
        "dso_days": str(dso(total, sales)),
        "aging": {k: str(v) for k, v in aging(entries, ids, today).items()},
        "customers": len(ids),
    }


@app.post("/seal/{day}")
def seal(day: date, db: Db) -> dict:
    day_rows = db.scalars(select(LedgerEntry).where(LedgerEntry.on == day))
    root, n = daily_root([r.to_entry() for r in day_rows], day)
    # Solana submission comes in the next step (programs/ayllu_ledger).
    db.add(Seal(day=day, merkle_root=root, entries=n, tx=None))
    db.commit()
    return {"date": day.isoformat(), "merkle_root": root, "entries": n, "tx": None}
