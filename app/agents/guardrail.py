from __future__ import annotations
from ..models import UserProfile, Context, Recommendation
from ..tools import max_affordable_payment
from .base import Trace

RISK_LIMIT = {"low": 0.3, "medium": 0.5, "high": 1.0}


class GuardrailAgent:
    """Agents propose, the guardrail decides. Deterministic rules, independent of the agents."""
    name = "guardrail"

    def review(self, user: UserProfile, ctx: Context, recs: list[Recommendation], trace: Trace):
        approved, blocked = [], []
        for r in recs:
            reason = self._violation(user, ctx, r)
            if reason:
                blocked.append({"card_id": r.card_id, "title": r.title, "reason": reason})
                trace.add(self.name, "block", card_id=r.card_id, reason=reason)
            else:
                approved.append(r)
        return approved, blocked

    @staticmethod
    def _violation(user, ctx, r):
        if r.placement == "alert":
            return None                                   # alerts protect the client
        if r.kind in ("credit", "investment") and user.age < 18:
            return "minor: product unavailable"
        if r.kind == "credit" and (ctx.vulnerable or ctx.surplus <= 0):
            return f"vulnerable client (surplus {ctx.surplus:,.0f} RON): no credit offers"
        if r.kind == "credit" and r.data.get("payment", 0) > max_affordable_payment(user):
            return "payment exceeds repayment capacity"
        if r.kind == "investment" and ctx.emergency_months < 3:
            return "emergency fund below 3 months"
        if r.risk > RISK_LIMIT[user.risk_profile]:
            return f"risk {r.risk:.1f} above the '{user.risk_profile}' risk profile"
        return None
