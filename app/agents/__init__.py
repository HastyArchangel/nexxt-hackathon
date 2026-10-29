from .base import Agent, Trace
from .savings import SavingsAgent
from .credit import CreditAgent
from .investment import InvestmentAgent
from .budget import BudgetAgent
from .business import BusinessAgent
from .guardrail import GuardrailAgent


def default_registry() -> dict[str, Agent]:
    return {a.name: a for a in [SavingsAgent(), CreditAgent(), InvestmentAgent(),
                                BudgetAgent(), BusinessAgent()]}
