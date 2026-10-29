import json
import numpy as np
import pytest
from app.agents import Trace, GuardrailAgent, default_registry
from app.agents.base import Agent
from app.data import USERS
from app.models import Recommendation
from app.orchestrator import Orchestrator
from app.planner import LLMPlanner, RulePlanner, allowed_agents
from app.ranker import LinUCBRanker, user_vector, card_vector
from app.tools import monthly_payment, principal_for_payment, derive_context


def test_loan_math_roundtrip():
    assert monthly_payment(10000, 0.12, 12) == pytest.approx(888.49, abs=0.01)
    p = principal_for_payment(monthly_payment(10000, 0.12, 12), 0.12, 12)
    assert p == pytest.approx(10000, rel=1e-9)


def plan_for(uid):
    u = USERS[uid]
    return RulePlanner().plan(u, derive_context(u), default_registry()).agents


def test_planner_routes_by_profile():
    assert plan_for("ioana") == ["business"]
    assert "credit" not in plan_for("radu") and "investment" not in plan_for("radu")
    assert {"credit", "investment"} <= set(plan_for("mihai"))


def test_guardrail_blocks_credit_for_vulnerable():
    u = USERS["dan"]                    # good credit score, but spends more than they earn
    ctx = derive_context(u)
    rec = Recommendation("credit:x", "credit", "credit", "t", "b", 0.5, risk=0.5, data={"payment": 100})
    ok, blocked = GuardrailAgent().review(u, ctx, [rec], Trace())
    assert not ok and "vulnerable" in blocked[0]["reason"]


def test_guardrail_blocks_risk_above_profile():
    u = USERS["radu"]
    rec = Recommendation("inv:x", "investment", "investment", "t", "b", 0.5, risk=0.7)
    ok, blocked = GuardrailAgent().review(u, derive_context(u), [rec], Trace())
    assert blocked


def test_failing_agent_does_not_break_feed():
    class Boom(Agent):
        name, description = "savings", "x"
        def run(self, *a): raise RuntimeError("down")
    reg = default_registry(); reg["savings"] = Boom()
    feed = Orchestrator(registry=reg).home_feed(USERS["mihai"])
    assert any(e["action"] == "agent_error" for e in feed["trace"])
    assert feed["items"]


def test_replan_when_too_few_cards():
    class OnlyBudget(RulePlanner):
        def plan(self, user, ctx, registry):
            p = super().plan(user, ctx, registry); p.agents = ["budget"]; return p
    feed = Orchestrator(planner=OnlyBudget()).home_feed(USERS["mihai"])
    assert feed["replanned"] and len(feed["items"]) >= 3


def test_forced_credit_for_vulnerable_is_blocked_end_to_end():
    class ForceCredit(RulePlanner):
        def plan(self, user, ctx, registry):
            p = super().plan(user, ctx, registry); p.agents = ["credit"]; return p
    feed = Orchestrator(planner=ForceCredit()).home_feed(USERS["dan"])
    assert all(i["kind"] != "credit" for i in feed["items"])
    assert any(b["card_id"].startswith("credit") for b in feed["blocked"])


def test_alerts_pinned_first():
    items = Orchestrator().home_feed(USERS["victor"])["items"]
    kinds = [i["placement"] for i in items]
    assert kinds == sorted(kinds, key=lambda k: k != "alert")


def test_ranker_learns_from_positive_feedback():
    r = LinUCBRanker(alpha=0.0)
    u = USERS["mihai"]; ctx = derive_context(u)
    uv = user_vector(u, ctx)
    rec = Recommendation("a", "savings", "savings", "t", "b", 0.5)
    cv = card_vector(rec)
    before = r.score(uv, [cv])[0][0]
    for _ in range(5):
        r.update(uv, cv, 1.0)
    assert r.score(uv, [cv])[0][0] > before


def test_feedback_requires_shown_card():
    o = Orchestrator()
    assert not o.feedback("mihai", "savings:flex", "click")
    o.home_feed(USERS["mihai"])
    assert o.feedback("mihai", "savings:flex", "click")
    assert o.ranker.n_updates == 1


class FakeLLM:
    def __init__(self, content): self.content = content
    @property
    def chat(self): return self
    @property
    def completions(self): return self
    def create(self, **kw):
        msg = type("M", (), {"content": self.content})
        return type("R", (), {"choices": [type("C", (), {"message": msg})]})


def test_llm_planner_filters_disallowed_agents():
    u = USERS["radu"]; ctx = derive_context(u)
    client = FakeLLM(json.dumps({"agents": ["credit", "budget"], "reasons": {}}))
    plan = LLMPlanner(client=client).plan(u, ctx, default_registry())
    assert plan.agents == ["budget"] and plan.source == "llm"


def test_llm_planner_falls_back_on_bad_output():
    u = USERS["mihai"]; ctx = derive_context(u)
    plan = LLMPlanner(client=FakeLLM("not json")).plan(u, ctx, default_registry())
    assert plan.source.startswith("rules") and plan.agents


def test_api_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_PATH", str(tmp_path / "r.npz"))
    from fastapi.testclient import TestClient
    import importlib, app.api as api
    importlib.reload(api)
    c = TestClient(api.app)
    assert c.get("/home-feed/nobody").status_code == 404
    feed = c.get("/home-feed/mihai").json()
    cid = next(i["card_id"] for i in feed["items"] if i["placement"] == "card")
    assert c.post("/event", json={"user_id": "mihai", "card_id": cid, "event": "click"}).json()["updates"] == 1
    assert c.post("/event", json={"user_id": "mihai", "card_id": cid, "event": "zzz"}).status_code == 422
