"""Pure ledger logic: balances, FIFO aging, DSO and daily Merkle roots.

Kept free of database code so it can be tested directly.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

CENT = Decimal("0.01")
AGING_BUCKETS = [(0, 7, "0-7"), (8, 15, "8-15"), (16, 30, "16-30"), (31, 60, "31-60"), (61, None, "60+")]


class EntryType(str, Enum):
    CHARGE = "charge"      # neighbor takes goods on credit
    PAYMENT = "payment"    # neighbor pays (cash, Yape, Plin, transfer)
    ADJUSTMENT = "adjustment"  # signed correction, never an edit


@dataclass(frozen=True)
class Entry:
    id: str
    customer_id: str
    type: EntryType
    amount: Decimal          # always positive; sign comes from type (adjustment may be negative)
    on: date
    due: date | None = None  # for charges
    confirmed: bool = False

    def signed(self) -> Decimal:
        if self.type is EntryType.PAYMENT:
            return -self.amount
        return self.amount


def balance(entries: list[Entry], customer_id: str) -> Decimal:
    """Amount the customer owes now (negative means credit in their favor)."""
    total = sum((e.signed() for e in entries if e.customer_id == customer_id), Decimal("0"))
    return total.quantize(CENT)


@dataclass
class OpenCharge:
    entry_id: str
    due: date
    remaining: Decimal


def open_charges_fifo(entries: list[Entry], customer_id: str) -> list[OpenCharge]:
    """Apply payments (and negative adjustments) to the oldest charges first."""
    mine = sorted((e for e in entries if e.customer_id == customer_id), key=lambda e: (e.on, e.id))
    open_: list[OpenCharge] = []
    credit = Decimal("0")
    for e in mine:
        value = e.signed()
        if value > 0:
            open_.append(OpenCharge(e.id, e.due or e.on, value))
        else:
            credit += -value
        # consume credit against oldest open charges
        while credit > 0 and open_:
            first = open_[0]
            used = min(first.remaining, credit)
            first.remaining -= used
            credit -= used
            if first.remaining == 0:
                open_.pop(0)
    return [c for c in open_ if c.remaining > 0]


def aging(entries: list[Entry], customer_ids: list[str], today: date) -> dict[str, Decimal]:
    """Outstanding balance by days past due, using FIFO application of payments."""
    result = {label: Decimal("0.00") for *_, label in AGING_BUCKETS}
    for cid in customer_ids:
        for charge in open_charges_fifo(entries, cid):
            days = max((today - charge.due).days, 0)
            for low, high, label in AGING_BUCKETS:
                if days >= low and (high is None or days <= high):
                    result[label] += charge.remaining
                    break
    return {k: v.quantize(CENT) for k, v in result.items()}


def dso(receivables: Decimal, credit_sales: Decimal, days: int = 30) -> Decimal:
    """Days Sales Outstanding = receivables / credit sales in the period * days."""
    if credit_sales <= 0:
        return Decimal("0.0")
    return (receivables / credit_sales * days).quantize(Decimal("0.1"))


def entry_hash(e: Entry) -> bytes:
    """Hash that identifies an entry without revealing who or how much (salted upstream)."""
    payload = f"{e.id}|{e.customer_id}|{e.type.value}|{e.amount}|{e.on.isoformat()}"
    return hashlib.sha256(payload.encode()).digest()


def merkle_root(leaves: list[bytes]) -> bytes:
    """Binary Merkle root (SHA-256). Odd node is paired with itself."""
    if not leaves:
        return hashlib.sha256(b"").digest()
    level = sorted(leaves)  # canonical order so the root is reproducible
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0]


def daily_root(entries: list[Entry], on: date) -> tuple[str, int]:
    """Root of the confirmed entries of a day, as hex, plus how many were sealed."""
    leaves = [entry_hash(e) for e in entries if e.on == on and e.confirmed]
    return merkle_root(leaves).hex(), len(leaves)
