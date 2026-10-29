from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from .agents import Trace, GuardrailAgent, default_registry
from .models import UserProfile, Recommendation
from .planner import RulePlanner
from .ranker import LinUCBRanker, user_vector, card_vector
from .tools import derive_context

REWARDS = {"click": 1.0, "convert": 3.0, "dismiss": -0.5}


class Orchestrator:
    def __init__(self, planner=None, ranker=None, registry=None, guardrail=None,
                 max_cards: int = 5, min_cards: int = 3, bandit_weight: float = 0.5):
        self.planner = planner or RulePlanner()
        self.ranker = ranker or LinUCBRanker()
        self.registry = registry or default_registry()
        self.guardrail = guardrail or GuardrailAgent()
        self.max_cards, self.min_cards, self.bandit_weight = max_cards, min_cards, bandit_weight
        self._shown: dict[tuple[str, str], tuple] = {}     # (user, card) -> (uvec, cvec)

    # ---------------------------------------------------------------- feed
    def home_feed(self, user: UserProfile) -> dict:
        trace = Trace()
        ctx = derive_context(user)
        trace.add("orchestrator", "context", surplus=round(ctx.surplus), dti=round(ctx.dti, 2),
                  emergency_months=round(ctx.emergency_months, 1), vulnerable=ctx.vulnerable)

        plan = self.planner.plan(user, ctx, self.registry)
        trace.add("orchestrator", "plan", agents=plan.agents, source=plan.source, reasons=plan.reasons)

        ran: set[str] = set()
        approved, blocked = self._run_and_review(plan.agents, user, ctx, trace, ran)

        replanned = False
        if len(approved) < self.min_cards:
            extra = self.planner.fallback(user, ctx, ran)
            if extra:
                replanned = True
                trace.add("orchestrator", "replan", reason=f"only {len(approved)} valid recommendations",
                          extra_agents=extra)
                more, more_blocked = self._run_and_review(extra, user, ctx, trace, ran)
                approved += more
                blocked += more_blocked

        approved = list({r.card_id: r for r in approved}.values())      # dedupe
        items = self._rank(user, ctx, approved, trace)
        return {"user_id": user.user_id, "plan": {"agents": plan.agents, "source": plan.source,
                "reasons": plan.reasons}, "replanned": replanned, "items": items,
                "blocked": blocked, "trace": trace.events}

    def _run_and_review(self, names, user, ctx, trace, ran):
        recs = []
        with ThreadPoolExecutor(max_workers=max(1, len(names))) as pool:
            futures = {n: pool.submit(self.registry[n].run, user, ctx, trace)
                       for n in names if n in self.registry}
            for name, fut in futures.items():
                ran.add(name)
                try:
                    out = fut.result(timeout=5)
                    trace.add("orchestrator", "agent_done", agent=name, n=len(out))
                    recs += out
                except Exception as e:      # a failed agent must not break the page
                    trace.add("orchestrator", "agent_error", agent=name, error=f"{type(e).__name__}: {e}")
        return self.guardrail.review(user, ctx, recs, trace)

    def _rank(self, user, ctx, recs: list[Recommendation], trace) -> list[dict]:
        if not recs:
            return []
        u = user_vector(user, ctx)
        C = [card_vector(r) for r in recs]
        mean, bonus = self.ranker.score(u, C)
        rows = []
        for r, c, m, b in zip(recs, C, mean, bonus):
            bandit = float(m + b)
            rows.append({"card_id": r.card_id, "agent": r.agent, "kind": r.kind, "title": r.title,
                         "body": r.body, "placement": r.placement, "reasons": r.reasons,
                         "priority": round(r.priority, 3), "bandit": round(bandit, 3),
                         "score": round(r.priority + self.bandit_weight * bandit, 3)})
            self._shown[(user.user_id, r.card_id)] = (u, c)
        rows.sort(key=lambda x: x["score"], reverse=True)
        alerts = [x for x in rows if x["placement"] == "alert"]       # alerts stay on top
        cards = [x for x in rows if x["placement"] != "alert"][: self.max_cards]
        trace.add("orchestrator", "rank", order=[x["card_id"] for x in alerts + cards])
        return alerts + cards

    # ------------------------------------------------------------ feedback
    def feedback(self, user_id: str, card_id: str, event: str) -> bool:
        shown = self._shown.get((user_id, card_id))
        if shown is None or event not in REWARDS:
            return False
        self.ranker.update(shown[0], shown[1], REWARDS[event])
        return True
