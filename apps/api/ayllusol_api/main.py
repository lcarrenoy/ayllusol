"""Minimal API over the pure ledger. In-memory store for the hackathon demo."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .ledger import Entry, EntryType, aging, balance, daily_root, dso

app = FastAPI(title="AylluSol API", version="0.1.0")

CUSTOMERS: dict[str, dict] = {}
ENTRIES: list[Entry] = []


class CustomerIn(BaseModel):
    name: str
    credit_limit: Decimal = Field(gt=0)
    credit_days: int = Field(default=7, ge=1, le=60)


class ChargeIn(BaseModel):
    customer_id: str
    amount: Decimal = Field(gt=0)
    on: date | None = None


class PaymentIn(BaseModel):
    customer_id: str
    amount: Decimal = Field(gt=0)
    on: date | None = None


@app.post("/customers")
def create_customer(body: CustomerIn) -> dict:
    cid = uuid4().hex[:8]
    CUSTOMERS[cid] = {"id": cid, **body.model_dump()}
    return CUSTOMERS[cid]


def _customer(cid: str) -> dict:
    if cid not in CUSTOMERS:
        raise HTTPException(404, "customer not found")
    return CUSTOMERS[cid]


@app.post("/charges")
def add_charge(body: ChargeIn, override_limit: bool = False) -> dict:
    c = _customer(body.customer_id)
    on = body.on or date.today()
    new_balance = balance(ENTRIES, c["id"]) + body.amount
    if new_balance > c["credit_limit"] and not override_limit:
        raise HTTPException(409, f"over limit: would owe {new_balance} of {c['credit_limit']}; owner must confirm")
    e = Entry(uuid4().hex, c["id"], EntryType.CHARGE, body.amount, on, on + timedelta(days=c["credit_days"]))
    ENTRIES.append(e)
    return {"entry_id": e.id, "balance": str(new_balance), "status": "pending_confirmation"}


@app.post("/entries/{entry_id}/confirm")
def confirm(entry_id: str) -> dict:
    for i, e in enumerate(ENTRIES):
        if e.id == entry_id:
            ENTRIES[i] = Entry(**{**e.__dict__, "confirmed": True})
            return {"entry_id": entry_id, "confirmed": True}
    raise HTTPException(404, "entry not found")


@app.post("/payments")
def add_payment(body: PaymentIn) -> dict:
    c = _customer(body.customer_id)
    e = Entry(uuid4().hex, c["id"], EntryType.PAYMENT, body.amount, body.on or date.today())
    ENTRIES.append(e)
    return {"entry_id": e.id, "balance": str(balance(ENTRIES, c["id"]))}


@app.get("/customers/{cid}/balance")
def get_balance(cid: str) -> dict:
    c = _customer(cid)
    return {"customer_id": cid, "balance": str(balance(ENTRIES, cid)), "limit": str(c["credit_limit"])}


@app.get("/dashboard/portfolio")
def portfolio(today: date | None = None) -> dict:
    today = today or date.today()
    ids = list(CUSTOMERS)
    total = sum((balance(ENTRIES, cid) for cid in ids), Decimal("0"))
    since = today - timedelta(days=30)
    sales = sum((e.amount for e in ENTRIES if e.type is EntryType.CHARGE and e.on > since), Decimal("0"))
    return {
        "receivables": str(total),
        "dso_days": str(dso(total, sales)),
        "aging": {k: str(v) for k, v in aging(ENTRIES, ids, today).items()},
        "customers": len(ids),
    }


@app.post("/seal/{day}")
def seal(day: date) -> dict:
    root, n = daily_root(ENTRIES, day)
    # Solana submission comes in the next step (programs/ayllu_ledger).
    return {"date": day.isoformat(), "merkle_root": root, "entries": n, "tx": None}
