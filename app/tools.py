"""Pure calculation functions. Agents call them as tools (calls are logged in the trace)."""
from __future__ import annotations
from .models import UserProfile, Context

DTI_LIMIT = 0.40
CATEGORY_LIMITS = {          # max share of income considered "normal"
    "dining": 0.08, "shopping": 0.10, "entertainment": 0.06,
    "subscriptions": 0.03, "transport": 0.12,
}


def monthly_payment(principal: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 12
    if r == 0:
        return principal / months
    return principal * r / (1 - (1 + r) ** -months)


def principal_for_payment(payment: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 12
    if r == 0:
        return payment * months
    return payment * (1 - (1 + r) ** -months) / r


def future_value(balance: float, monthly_contribution: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 12
    value = balance
    for _ in range(months):
        value = value * (1 + r) + monthly_contribution
    return value


def max_affordable_payment(user: UserProfile) -> float:
    """Largest new monthly payment that keeps total DTI under the limit."""
    return max(0.0, DTI_LIMIT * user.monthly_income - user.monthly_debt_payments)


def category_overspend(user: UserProfile) -> list[dict]:
    out = []
    for cat, spent in user.spend_by_category.items():
        limit = CATEGORY_LIMITS.get(cat)
        if limit is None:
            continue
        cap = limit * user.monthly_income
        if spent > cap:
            out.append({"category": cat, "spent": spent, "limit": round(cap, 2),
                        "excess": round(spent - cap, 2)})
    return sorted(out, key=lambda d: d["excess"], reverse=True)


def value_score(gain: float, scale: float = 800.0) -> float:
    return max(0.0, min(1.0, gain / scale))


def derive_context(user: UserProfile) -> Context:
    surplus = user.monthly_income - user.monthly_expenses - user.monthly_debt_payments
    dti = user.monthly_debt_payments / max(user.monthly_income, 1)
    liquid = user.balance + user.savings_balance
    emergency = liquid / max(user.monthly_expenses, 1)
    idle = max(0.0, user.balance - user.monthly_expenses)
    vulnerable = (surplus <= 0 or dti > 0.5
                  or user.balance < 0.25 * user.monthly_expenses)
    return Context(surplus, dti, emergency, idle, vulnerable)
