import pytest
from server import config, db, interceptor

config.MOCK_LLM = True
quiet = lambda *a: None


@pytest.fixture(autouse=True)
def fresh(tmp_path):
    db.reset(str(tmp_path / "t.db"))
    yield
    db.reset()


def test_deny_rule_never_executes():
    db.add_rule("Never email outside Acme", "send_email", {"arg": "to", "not_domain": "acme.example"}, "deny")
    calls = []
    tools = interceptor.wrap({"send_email": lambda **a: calls.append(a) or "sent"}, run_id=1, on_event=quiet)
    out = tools["send_email"](to="x@evil.example", subject="s", body="b")
    assert calls == [] and out.startswith("BLOCKED")


def test_allow_internal_runs():
    calls = []
    tools = interceptor.wrap({"send_email": lambda **a: calls.append(a) or "sent"}, run_id=1, on_event=quiet)
    assert tools["send_email"](to="bob@acme.example", subject="s", body="b") == "sent"
    assert len(calls) == 1


def test_deny_beats_allow():
    db.add_rule("allow all email", "send_email", {}, "allow")
    db.add_rule("no evil", "send_email", {"arg": "to", "domain": "evil.example"}, "deny")
    d = interceptor.decide("send_email", {"to": "a@evil.example"}, db.list_rules(True))
    assert d["verdict"] == "deny"


def test_payment_threshold_rule():
    db.add_rule("ask over $20", "transfer_money", {"max_amount": 20}, "ask")
    r = db.list_rules(True)
    assert interceptor.decide("transfer_money", {"to": "a", "amount": 500}, r)["verdict"] == "ask"
    assert interceptor.decide("transfer_money", {"to": "a", "amount": 5}, r)["decided_by"] != "rule"


def test_ask_timeout_denies(monkeypatch):
    monkeypatch.setattr(config, "ASK_TIMEOUT_S", 0.05)
    calls = []
    tools = interceptor.wrap({"transfer_money": lambda **a: calls.append(a) or "ok"}, run_id=1, on_event=quiet)
    out = tools["transfer_money"](to="a", amount=999)
    assert calls == [] and "denied" in out.lower()


def test_unleashed_runs_everything():
    calls = []
    tools = interceptor.wrap({"send_email": lambda **a: calls.append(a) or "sent"}, run_id=2, leashed=False, on_event=quiet)
    tools["send_email"](to="x@evil.example", subject="s", body="b")
    assert len(calls) == 1


def test_always_like_this_creates_rule():
    r = interceptor.rule_from_action("send_email", {"to": "x@partner.example"}, "allow")
    assert r["verdict"] == "allow" and r["source"] == "approval"
    d = interceptor.decide("send_email", {"to": "y@partner.example"}, db.list_rules(True))
    assert d["decided_by"] == "rule" and d["verdict"] == "allow"
