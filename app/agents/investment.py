from ..data import CATALOG
from ..models import Recommendation
from ..tools import future_value
from .base import Agent


class InvestmentAgent(Agent):
    name = "investment"
    description = "Investments (funds/ETF) matched to the risk profile, only after an emergency fund exists."

    def run(self, user, ctx, trace):
        if user.age < 18 or ctx.emergency_months < 3:
            return []
        liquid = user.balance + user.savings_balance
        investable = liquid - 6 * user.monthly_expenses     # keep a 6-month reserve untouched
        if investable < 1000:
            return []

        product = CATALOG[{"low": "bond_fund", "medium": "balanced_fund", "high": "equity_etf"}[user.risk_profile]]
        amount = investable * 0.5
        expected = self.use(trace, future_value, amount, 0, product["exp"], 60)
        pessimistic = self.use(trace, future_value, amount, 0, max(product["exp"] - product["vol"], -0.5), 60)
        gain = expected - amount
        return [Recommendation(
            card_id=f"investment:{product['id']}", agent=self.name, kind="investment",
            title=f"{product['name']}: {amount:,.0f} RON over 5 years",
            body=f"Expected scenario: {expected:,.0f} RON. Cautious scenario: {pessimistic:,.0f} RON. "
                 f"The value can fall; don't invest money you need in the short term.",
            priority=min(1.0, gain / (user.monthly_income * 3)), risk=product["risk"],
            reasons=["6-month reserve stays untouched",
                     f"risk profile {user.risk_profile}"],
            data={"amount": amount, "expected_5y": round(expected, 2),
                  "pessimistic_5y": round(pessimistic, 2)})]
