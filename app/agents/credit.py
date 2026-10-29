from ..data import CATALOG
from ..models import Recommendation
from ..tools import max_affordable_payment, monthly_payment, principal_for_payment
from .base import Agent


class CreditAgent(Agent):
    name = "credit"
    description = "Personal loan and credit card, sized to the client's repayment capacity (DTI)."

    def run(self, user, ctx, trace):
        if user.age < 18:
            return []
        recs = []
        loan = CATALOG["personal_loan"]

        if user.credit_score >= loan["min_score"]:
            capacity = self.use(trace, max_affordable_payment, user)
            rate = loan["rate_good"] if user.credit_score >= 700 else loan["rate_std"]
            months = loan["months"]
            principal = min(self.use(trace, principal_for_payment, capacity * 0.8, rate, months),
                            loan["max_amount"])
            if principal >= loan["min_amount"]:
                payment = self.use(trace, monthly_payment, principal, rate, months)
                recs.append(Recommendation(
                    card_id="credit:personal_loan", agent=self.name, kind="credit",
                    title=f"Loan of up to {principal:,.0f} RON, {payment:,.0f} RON/month",
                    body=f"{rate:.1%} interest over {months} months. The payment stays below your "
                         f"repayment capacity ({capacity:,.0f} RON/month, with a 20% margin).",
                    priority=min(1.0, 0.2 + 0.6 * capacity / max(user.monthly_income, 1)),
                    risk=0.5,
                    reasons=[f"credit score {user.credit_score}", f"current DTI {ctx.dti:.0%}"],
                    data={"principal": round(principal, 2), "payment": round(payment, 2),
                          "rate": rate, "months": months}))

        cc = CATALOG["credit_card_basic"]
        if (not user.has_credit_card and user.monthly_income >= cc["min_income"]
                and user.credit_score >= cc["min_score"]):
            recs.append(Recommendation(
                card_id="credit:credit_card", agent=self.name, kind="credit",
                title="Credit card with an interest-free period",
                body="Eligible based on your income and credit score.",
                priority=0.3, risk=0.3,
                reasons=[f"income {user.monthly_income:,.0f} RON", f"credit score {user.credit_score}"],
                data={}))
        return recs
