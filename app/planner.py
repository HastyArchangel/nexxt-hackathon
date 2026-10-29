"""The planner decides WHICH agents run for a user.
RulePlanner: deterministic rules. LLMPlanner: an LLM chooses, but only among the allowed agents,
with automatic fallback to the rules if the LLM fails or answers with something invalid."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from .models import UserProfile, Context


@dataclass
class Plan:
    agents: list[str]
    reasons: dict[str, str] = field(default_factory=dict)
    source: str = "rules"


def allowed_agents(user: UserProfile, ctx: Context) -> list[str]:
    """Hard constraints (also applied to the LLM): which agents may run for this user."""
    if user.account_type == "business":
        return ["business"]
    allowed = ["budget", "savings"]
    if not ctx.vulnerable and user.age >= 18:
        allowed.append("credit")
        if ctx.emergency_months >= 3:
            allowed.append("investment")
    return allowed


class RulePlanner:
    def plan(self, user, ctx, registry) -> Plan:
        allowed = allowed_agents(user, ctx)
        why = {
            "business": "business account",
            "budget": "budget alerts are always checked",
            "savings": f"idle cash {ctx.idle_cash:,.0f} RON / reserve {ctx.emergency_months:.1f} months",
            "credit": f"DTI {ctx.dti:.0%}, client not vulnerable",
            "investment": f"reserve {ctx.emergency_months:.1f} months >= 3",
        }
        chosen = [a for a in ["business", "budget", "savings", "credit", "investment"] if a in allowed]
        reasons = {a: why[a] for a in chosen}
        if ctx.vulnerable and user.account_type != "business":
            reasons["(omise)"] = "vulnerable client: no credit/investments"
        return Plan(chosen, reasons, "rules")

    def fallback(self, user, ctx, ran: set[str]) -> list[str]:
        return [a for a in allowed_agents(user, ctx) if a not in ran][:2]


class LLMPlanner:
    def __init__(self, client=None, model: str | None = None, fallback: RulePlanner | None = None):
        self._client = client
        self.model = model or os.getenv("PLANNER_MODEL", "gpt-4o-mini")
        self.rules = fallback or RulePlanner()

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI      # lazy import: optional dependency
            self._client = OpenAI()
        return self._client

    def plan(self, user, ctx, registry) -> Plan:
        allowed = allowed_agents(user, ctx)
        try:
            summary = {   # no name/ID: the LLM only sees aggregate metrics
                "account_type": user.account_type, "age": user.age, "cash": user.balance,
                "savings": user.savings_balance, "income": user.monthly_income,
                "surplus": round(ctx.surplus), "dti": round(ctx.dti, 2),
                "emergency_months": round(ctx.emergency_months, 1),
                "idle_cash": round(ctx.idle_cash), "vulnerable": ctx.vulnerable,
                "risk_profile": user.risk_profile,
            }
            system = ("You are the orchestrator of a banking app. You choose which recommendation "
                      "agents run for this client. Answer with JSON ONLY: "
                      '{"agents": [...], "reasons": {"agent": "short reason"}}. '
                      "Choose only from the available agents; leave out irrelevant ones.")
            catalog = {a: registry[a].description for a in allowed if a in registry}
            resp = self._get_client().chat.completions.create(
                model=self.model, temperature=0, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": json.dumps({"client": summary, "agents": catalog},
                                                                 ensure_ascii=False)}])
            data = json.loads(resp.choices[0].message.content)
            chosen = [a for a in data["agents"] if a in allowed]      # hard filter
            if not chosen:
                raise ValueError("empty plan")
            return Plan(list(dict.fromkeys(chosen)), data.get("reasons", {}), "llm")
        except Exception as e:
            plan = self.rules.plan(user, ctx, registry)
            plan.source = f"rules (llm failed: {type(e).__name__})"
            return plan

    def fallback(self, user, ctx, ran):
        return self.rules.fallback(user, ctx, ran)


def make_planner():
    return LLMPlanner() if os.getenv("PLANNER", "rules") == "llm" else RulePlanner()
