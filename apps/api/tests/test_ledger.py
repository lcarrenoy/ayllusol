from datetime import date
from decimal import Decimal as D

from fastapi.testclient import TestClient

from ayllusol_api import main
from ayllusol_api.ledger import Entry, EntryType, aging, balance, daily_root, dso, merkle_root

T = EntryType


def e(i, t, amt, day, due=None, ok=True, c="rosa"):
    return Entry(str(i), c, t, D(amt), date(2026, 10, day), due and date(2026, 10, due), ok)


def test_balance_charges_minus_payments():
    entries = [e(1, T.CHARGE, "8.50", 1), e(2, T.CHARGE, "14.00", 2), e(3, T.PAYMENT, "20.00", 5)]
    assert balance(entries, "rosa") == D("2.50")


def test_fifo_payment_clears_oldest_first():
    entries = [e(1, T.CHARGE, "30", 1, due=1), e(2, T.CHARGE, "10", 25, due=25), e(3, T.PAYMENT, "30", 26)]
    buckets = aging(entries, ["rosa"], date(2026, 10, 26))
    assert buckets["0-7"] == D("10.00")      # only the recent charge remains
    assert buckets["16-30"] == D("0.00")     # the old one was paid first


def test_overpayment_is_credit_not_hidden_debt():
    entries = [e(1, T.CHARGE, "10", 1), e(2, T.PAYMENT, "15", 2)]
    assert balance(entries, "rosa") == D("-5.00")
    assert aging(entries, ["rosa"], date(2026, 10, 2))["0-7"] == D("0.00")


def test_dso_matches_excel_definition():
    assert dso(D("1240"), D("3100")) == D("12.0")
    assert dso(D("100"), D("0")) == D("0.0")


def test_merkle_root_is_order_independent_and_changes_with_data():
    a, b, c = (bytes([i]) * 32 for i in (1, 2, 3))
    assert merkle_root([a, b, c]) == merkle_root([c, a, b])
    assert merkle_root([a, b, c]) != merkle_root([a, b])


def test_daily_root_only_seals_confirmed():
    entries = [e(1, T.CHARGE, "5", 3, ok=True), e(2, T.CHARGE, "7", 3, ok=False)]
    _, n = daily_root(entries, date(2026, 10, 3))
    assert n == 1


def test_api_flow_limit_confirm_and_portfolio():
    main.CUSTOMERS.clear(); main.ENTRIES.clear()
    api = TestClient(main.app)
    rosa = api.post("/customers", json={"name": "Rosa (demo)", "credit_limit": "80"}).json()
    r = api.post("/charges", json={"customer_id": rosa["id"], "amount": "45", "on": "2026-10-10"})
    assert r.status_code == 200
    assert api.post("/charges", json={"customer_id": rosa["id"], "amount": "40", "on": "2026-10-10"}).status_code == 409
    api.post(f"/entries/{r.json()['entry_id']}/confirm")
    api.post("/payments", json={"customer_id": rosa["id"], "amount": "20", "on": "2026-10-11"})
    assert api.get(f"/customers/{rosa['id']}/balance").json()["balance"] == "25.00"
    p = api.get("/dashboard/portfolio", params={"today": "2026-10-12"}).json()
    assert p["receivables"] == "25.00"
    s = api.post("/seal/2026-10-10").json()
    assert s["entries"] == 1 and len(s["merkle_root"]) == 64
