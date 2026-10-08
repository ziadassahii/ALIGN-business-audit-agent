"""Offline tests: no API key and no network needed.  Run:  pytest -q"""
import io, sys, zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine  # noqa: E402

DOCS = {
    "website.txt": "DELIVERY POLICY\nFree delivery is available for orders above $50.\nStandard delivery takes 3-5 business days.",
    "sales_policy.txt": "SALES PLAYBOOK\nFree delivery may be offered on orders above $75.\nStrategic exceptions require manager approval.",
    "support_script.txt": "CUSTOMER SUPPORT SCRIPT\nTell customers: Orders over $100 qualify for free delivery.",
    "refund_policy.txt": "REFUND POLICY\nStandard refunds are limited to $20. Agents may issue up to $50 for documented service failure.",
    "sop.txt": "ORDER SOP\n1. Receive order\n2. Verify payment\n3. Quality check\n4. Pack\n5. Ship",
}
ORDERS = pd.DataFrame([[1001, 45, 0], [1002, 62, 8], [1003, 68, 8], [1004, 72, 8], [1005, 81, 8], [1006, 120, 0],
                       [1007, 55, 8], [1008, 44, 15], [1009, 91, 8], [1010, 59, 8]],
                      columns=["order_id", "order_value", "delivery_fee"])


def audit():
    return engine.run_audit(DOCS, ORDERS, "")


def test_offline_finds_the_delivery_conflict():
    r = audit()
    assert r["mode"] == "offline" and len(r["findings"]) == 1
    f = r["findings"][0]
    assert f["vals"] == [50.0, 75.0, 100.0] and f["canonical"] == 75.0
    assert f["n"] == 7 and f["exposure"] == 56.0          # only orders inside the gap
    assert [p["changed"] for p in f["patches"]] == [True, False, True]
    assert all(c["verified"] for c in r["claims"])
    assert r["opportunity"] and len(r["opportunity"]["hot_steps"]) == 2


def test_fee_outside_the_gap_is_not_counted():
    orders = pd.concat([ORDERS, pd.DataFrame([[1011, 250, 12]], columns=ORDERS.columns)], ignore_index=True)
    f = engine.run_audit(DOCS, orders, "")["findings"][0]
    assert f["exposure"] == 56.0


def test_locate_returns_the_real_text():
    doc = "Free  delivery\nis available for orders above $50."
    assert engine.locate(doc, "free delivery is available for orders above $50.") == doc
    assert engine.locate(doc, "something else") is None


def test_case_drifted_quote_still_patches(monkeypatch):
    real = engine.regex_claims
    def drifted(text):
        cs = real(text)
        for c in cs:
            c.quote = c.quote.lower()                      # a model that lowercases its quote
        return cs
    monkeypatch.setattr(engine, "regex_claims", drifted)
    f = audit()["findings"][0]
    changed = [p for p in f["patches"] if p["changed"]]
    assert len(changed) == 2 and all("$75" in p["new"] or "$75" in p["diff"] for p in changed)


def test_export_applies_two_fixes_in_one_file():
    docs = {"a.txt": "Free delivery above $50. Express delivery above $20."}
    res = {"findings": [
        {"id": "f1", "patches": [dict(source="a.txt", changed=True, old="Free delivery above $50.", new="Free delivery above $75.")]},
        {"id": "f2", "patches": [dict(source="a.txt", changed=True, old="Express delivery above $20.", new="Express delivery above $30.")]}]}
    z = zipfile.ZipFile(io.BytesIO(engine.export_zip(res, {"f1", "f2"}, docs, "r")))
    assert z.read("aligned/a.txt").decode() == "Free delivery above $75. Express delivery above $30."
    assert "aligned/a.txt" not in zipfile.ZipFile(io.BytesIO(engine.export_zip(res, set(), docs, "r"))).namelist()


def test_api_failure_falls_back_offline(monkeypatch):
    real = engine._pipeline
    def flaky(docs, orders, key, emit, trace):
        if key:
            raise RuntimeError("boom")
        return real(docs, orders, key, emit, trace)
    monkeypatch.setattr(engine, "_pipeline", flaky)
    r = engine.run_audit(DOCS, ORDERS, "sk-test")
    assert r["mode"] == "offline" and "boom" in r["notice"] and r["findings"]


def _discount():
    p = Path(__file__).resolve().parents[1] / "sample_data" / "discount"
    docs = {f.name: f.read_text() for f in sorted(p.glob("*.txt"))}
    return docs, pd.read_csv(p / "deals.csv")


def test_discount_scenario_money_comes_from_the_data():
    docs, deals = _discount()
    f = engine.run_audit(docs, deals, "")["findings"][0]
    assert f["vals"] == [10.0, 12.0, 15.0] and f["canonical"] == 12.0 and f["column"] == "discount_pct"
    gap = deals[(deals.discount_pct > 10) & (deals.discount_pct <= 15)]       # "up to 10" is allowed, "up to 15" is the loosest
    assert f["n"] == len(gap) and f["exposure_kind"] == "discount"
    expected = (gap.deal_value * (gap.discount_pct - 12).clip(lower=0) / 100).sum()
    assert abs(f["exposure"] - expected) < 0.01


def test_boundary_deals_are_handled_correctly():
    docs, deals = _discount()
    f = engine.run_audit(docs, deals, "")["findings"][0]
    ids = set(f["row_ids"])
    assert not any(deals.loc[i, "discount_pct"] == 10 for i in ids)           # exactly 10% is allowed by every rule
    assert any(deals.loc[i, "discount_pct"] == 15 for i in ids)               # exactly 15% is allowed only by the contract


def test_approval_sop_is_flagged_as_a_process_to_test():
    docs, deals = _discount()
    o = engine.run_audit(docs, deals, "")["opportunity"]
    assert o and len(o["hot_steps"]) == 3
