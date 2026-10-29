from ..data import CATALOG
from ..models import Recommendation
from ..tools import future_value, value_score
from .base import Agent


class SavingsAgent(Agent):
    name = "savings"
    description = "Savings: interest on idle cash, term deposits, emergency fund."

    def run(self, user, ctx, trace):
        recs = []
        product = CATALOG["savings_student" if user.account_type == "student" else "savings_flex"]

        if ctx.idle_cash >= 500:
            gain = self.use(trace, future_value, ctx.idle_cash, 0, product["rate"], 12) - ctx.idle_cash
            extra = gain - ctx.idle_cash * CATALOG["current_account_rate"]
            recs.append(Recommendation(
                card_id=f"savings:{product['id']}", agent=self.name, kind="savings",
                title=f"{product['name']}: +{extra:,.0f} RON/year from idle cash",
                body=f"You have {ctx.idle_cash:,.0f} RON above a one-month buffer in your current account. "
                     f"At {product['rate']:.1%} interest you would earn ~{extra:,.0f} RON in a year.",
                priority=value_score(extra), risk=0.0,
                reasons=[f"idle cash {ctx.idle_cash:,.0f} RON", f"interest rate {product['rate']:.1%}"],
                data={"idle_cash": ctx.idle_cash, "extra_interest_12m": round(extra, 2)}))

        td = CATALOG["term_deposit_12m"]
        if user.savings_balance >= 5000 and ctx.emergency_months >= 6:
            amount = user.savings_balance * 0.5
            flex = CATALOG["savings_flex"]["rate"]
            extra = (self.use(trace, future_value, amount, 0, td["rate"], 12)
                     - self.use(trace, future_value, amount, 0, flex, 12))
            recs.append(Recommendation(
                card_id=f"savings:{td['id']}", agent=self.name, kind="savings",
                title=f"{td['name']}: +{extra:,.0f} RON vs. Flex account",
                body=f"Of your {user.savings_balance:,.0f} RON in savings, locking {amount:,.0f} RON at "
                     f"{td['rate']:.1%} earns {extra:,.0f} RON more than the Flex account.",
                priority=value_score(extra), risk=0.0,
                reasons=[f"emergency reserve {ctx.emergency_months:.1f} months (>= 6)"],
                data={"amount": amount, "extra_vs_flex": round(extra, 2)}))

        if 0 < ctx.emergency_months < 3 and ctx.surplus > 0:
            liquid = user.balance + user.savings_balance
            target = 3 * user.monthly_expenses - liquid
            monthly = min(ctx.surplus * 0.5, target / 6)
            recs.append(Recommendation(
                card_id="savings:emergency_fund", agent=self.name, kind="savings",
                title="Build a 3-month emergency fund",
                body=f"You still need {target:,.0f} RON. Saving {monthly:,.0f} RON/month gets you there in "
                     f"~{target / monthly:.0f} months.",
                priority=0.5 + 0.3 * (1 - ctx.emergency_months / 3), risk=0.0,
                reasons=[f"current reserve {ctx.emergency_months:.1f} months (< 3)"],
                data={"target": target, "monthly": monthly}))
        return recs
