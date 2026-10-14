"""Load invented demo neighbors into the dev database: `uv run python -m ayllusol_api.seed`.

All names are fictional. Dates are relative to today so the aging buckets look alive.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal as D

from .db import SessionLocal, init_db
from .models import Confirmation, Customer, LedgerEntry

# (id, name, limit, credit_days, [(days_ago, type, amount, confirmed)])
DEMO = [
    ("demo-rosa", "Rosa Quispe (demo)", "80", 7,
     [(20, "charge", "32.50", True), (12, "payment", "20.00", True), (3, "charge", "14.00", True)]),
    ("demo-juan", "Juan Mamani (demo)", "120", 15,
     [(45, "charge", "60.00", True), (9, "charge", "18.70", True), (1, "charge", "9.90", False)]),
    ("demo-carmen", "Carmen Huamán (demo)", "50", 7,
     [(6, "charge", "12.00", True), (2, "payment", "12.00", True)]),
    ("demo-pedro", "Pedro Condori (demo)", "100", 7,
     [(70, "charge", "45.00", True), (35, "payment", "10.00", True), (0, "charge", "6.50", False)]),
]


def seed(today: date | None = None) -> int:
    today = today or date.today()
    init_db()
    added = 0
    with SessionLocal() as s:
        for cid, name, limit, days, moves in DEMO:
            if s.get(Customer, cid):
                continue  # idempotent: never touch existing ledger rows
            s.add(Customer(id=cid, name=name, credit_limit=D(limit), credit_days=days))
            for i, (ago, kind, amount, ok) in enumerate(moves):
                on = today - timedelta(days=ago)
                eid = f"{cid}-{i}"
                s.add(LedgerEntry(id=eid, customer_id=cid, type=kind, amount=D(amount), on=on,
                                  due=on + timedelta(days=days) if kind == "charge" else None))
                if ok:
                    s.add(Confirmation(entry_id=eid))
            added += 1
        s.commit()
    return added


if __name__ == "__main__":
    print(f"seeded {seed()} demo customers")
