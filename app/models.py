from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserProfile:
    user_id: str
    name: str
    age: int
    account_type: str            # student | standard | premium | business
    balance: float               # cash in the current account (RON)
    savings_balance: float
    monthly_income: float        # for business accounts: monthly revenue
    monthly_expenses: float
    monthly_debt_payments: float
    credit_score: int            # 300-850
    risk_profile: str            # low | medium | high
    has_savings_account: bool = False
    has_credit_card: bool = False
    has_loan: bool = False
    spend_by_category: dict[str, float] = field(default_factory=dict)


@dataclass
class Context:
    """Derived metrics, computed once and shared by all agents."""
    surplus: float               # income - expenses - debt payments
    dti: float                   # debt payments / income
    emergency_months: float      # (cash + savings) / monthly expenses
    idle_cash: float             # cash above a one-month buffer
    vulnerable: bool


@dataclass
class Recommendation:
    card_id: str
    agent: str
    kind: str                    # savings | credit | investment | budget | business
    title: str
    body: str
    priority: float              # 0..1, estimated value for the client (computed by the agent)
    risk: float = 0.0            # 0 = no risk, 1 = high risk
    placement: str = "card"      # card | alert
    reasons: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
