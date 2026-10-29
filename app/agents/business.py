from ..data import CATALOG
from ..models import Recommendation
from ..tools import future_value, monthly_payment, value_score
from .base import Agent


class BusinessAgent(Agent):
    name = "business"
    description = "Business accounts: earning on idle cash, working-capital line, liquidity alert."

    def run(self, user, ctx, trace):
        if user.account_type != "business":
            return []
        recs = []
        idle = user.balance - 2 * user.monthly_expenses
        if idle > 5000:
            rate = CATALOG["business_deposit"]["rate"]
            gain = self.use(trace, future_value, idle, 0, rate, 12) - idle
            recs.append(Recommendation(
                card_id="business:deposit", agent=self.name, kind="business",
                title=f"Overnight deposit: +{gain:,.0f} RON/year",
                body=f"{idle:,.0f} RON is sitting idle above a 2-month expense reserve.",
                priority=value_score(gain, 3000),
                reasons=[f"cash above 2 months of expenses: {idle:,.0f} RON"],
                data={"idle": idle, "gain": round(gain, 2)}))

        line = CATALOG["business_credit_line"]
        amount = user.monthly_expenses
        pay = self.use(trace, monthly_payment, amount, line["rate"], line["months"])
        if pay <= 0.15 * user.monthly_income:
            recs.append(Recommendation(
                card_id="business:credit_line", agent=self.name, kind="business",
                title=f"Working-capital line of {amount:,.0f} RON",
                body=f"{line['rate']:.1%} interest; payment at most {pay:,.0f} RON/month, "
                     f"under 15% of monthly revenue.",
                priority=0.45, risk=0.5, reasons=["payment < 15% of revenue"],
                data={"amount": amount, "payment": round(pay, 2)}))

        if user.balance < 2 * user.monthly_expenses:
            recs.append(Recommendation(
                card_id="business:liquidity_alert", agent=self.name, kind="business",
                title="Liquidity below 2 months of expenses",
                body="The company's cash reserve is below the recommended threshold.",
                priority=0.9, placement="alert", reasons=["cash < 2 x monthly expenses"], data={}))
        return recs
