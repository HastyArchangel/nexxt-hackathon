from ..models import Recommendation
from ..tools import category_overspend
from .base import Agent


class BudgetAgent(Agent):
    name = "budget"
    description = "Budget alerts: category overspending, expenses above income, low balance."

    def run(self, user, ctx, trace):
        recs = []
        for o in self.use(trace, category_overspend, user)[:2]:
            recs.append(Recommendation(
                card_id=f"budget:over_{o['category']}", agent=self.name, kind="budget",
                title=f"{o['category'].capitalize()} spending is {o['excess']:,.0f} RON over the limit",
                body=f"You spent {o['spent']:,.0f} RON this month; the recommended limit for your "
                     f"income is {o['limit']:,.0f} RON.",
                priority=min(1.0, 0.4 + 5 * o["excess"] / max(user.monthly_income, 1)),
                placement="alert",
                reasons=[f"{o['spent']:,.0f} RON out of {user.monthly_income:,.0f} RON income"],
                data=o))
        if ctx.surplus <= 0:
            outflow = user.monthly_expenses + user.monthly_debt_payments
            recs.append(Recommendation(
                card_id="budget:negative_surplus", agent=self.name, kind="budget",
                title="Your expenses exceed your income",
                body=f"You are {-ctx.surplus:,.0f} RON short every month. Let's find where to cut back.",
                priority=0.95, placement="alert",
                reasons=[f"income {user.monthly_income:,.0f} vs outflow {outflow:,.0f}"],
                data={"surplus": ctx.surplus}))
        if user.balance < 0.25 * user.monthly_expenses:
            recs.append(Recommendation(
                card_id="budget:low_balance", agent=self.name, kind="budget",
                title="Low balance in your current account",
                body=f"You have {user.balance:,.0f} RON, less than a quarter of your monthly expenses.",
                priority=0.9, placement="alert",
                reasons=["balance < 25% of monthly expenses"], data={}))
        if ctx.vulnerable:
            recs.append(Recommendation(
                card_id="budget:plan", agent=self.name, kind="budget",
                title="Personalized budget plan",
                body="A simple per-category plan to get your monthly surplus back.",
                priority=0.8, reasons=["tight financial situation"], data={}))
        return recs
