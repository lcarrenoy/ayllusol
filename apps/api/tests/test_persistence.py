from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from ayllusol_api.db import init_db, make_engine
from ayllusol_api.models import AppendOnlyError, Customer, LedgerEntry


def _seed_rosa(s):
    s.add(Customer(id="rosa", name="Rosa (demo)", credit_limit=D("80"), credit_days=7))
    s.add(LedgerEntry(id="e1", customer_id="rosa", type="charge", amount=D("0.10"), on=date(2026, 10, 1)))
    s.add(LedgerEntry(id="e2", customer_id="rosa", type="charge", amount=D("0.20"), on=date(2026, 10, 1)))
    s.commit()


def test_money_is_exact_on_sqlite(session_factory):
    with session_factory() as s:
        _seed_rosa(s)
        assert s.execute(text("select amount from ledger_entries where id='e1'")).scalar() == 10  # cents
    with session_factory() as s:
        total = sum(e.amount for e in s.query(LedgerEntry))
        assert total == D("0.30") and isinstance(total, D)


def test_ledger_rows_cannot_be_edited_or_deleted(session_factory):
    with session_factory() as s:
        _seed_rosa(s)
        s.get(LedgerEntry, "e1").amount = D("99")
        with pytest.raises(AppendOnlyError):
            s.commit()
        s.rollback()
        s.delete(s.get(LedgerEntry, "e2"))
        with pytest.raises(AppendOnlyError):
            s.commit()


def test_data_survives_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'ayllusol.db'}"
    first = make_engine(url)
    init_db(first)
    with sessionmaker(bind=first)() as s:
        _seed_rosa(s)
    first.dispose()

    second = make_engine(url)
    with sessionmaker(bind=second)() as s:
        assert s.query(LedgerEntry).count() == 2
    second.dispose()


def test_statement_confirm_is_idempotent_and_seal_is_recorded(api):
    rosa = api.post("/customers", json={"name": "Rosa (demo)", "credit_limit": "80"}).json()
    r = api.post("/charges", json={"customer_id": rosa["id"], "amount": "8.50", "on": "2026-10-10"}).json()
    api.post("/payments", json={"customer_id": rosa["id"], "amount": "3.00", "on": "2026-10-11"})
    assert api.post(f"/entries/{r['entry_id']}/confirm").status_code == 200
    assert api.post(f"/entries/{r['entry_id']}/confirm").status_code == 200

    st = api.get(f"/customers/{rosa['id']}/entries").json()
    assert [ln["running_balance"] for ln in st["entries"]] == ["8.50", "5.50"]
    assert st["entries"][0]["confirmed"] is True
    assert api.get("/customers").json()[0]["balance"] == "5.50"
    assert api.post("/seal/2026-10-10").json()["entries"] == 1


def test_amount_with_more_than_two_decimals_is_rejected(api):
    rosa = api.post("/customers", json={"name": "Rosa (demo)", "credit_limit": "80"}).json()
    assert api.post("/charges", json={"customer_id": rosa["id"], "amount": "1.005"}).status_code == 422
