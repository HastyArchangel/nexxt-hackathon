"""Mock data: product catalog and synthetic users. All figures are fictional."""
from .models import UserProfile

CATALOG = {
    "current_account_rate": 0.001,
    "savings_flex":    {"id": "flex",    "name": "Flex Savings Account",    "rate": 0.035},
    "savings_student": {"id": "student", "name": "Student Savings Account", "rate": 0.045},
    "term_deposit_12m": {"id": "td12", "name": "12-month Term Deposit", "rate": 0.052, "min": 1000},
    "personal_loan": {"min_score": 620, "rate_good": 0.095, "rate_std": 0.115,
                      "months": 48, "min_amount": 3000, "max_amount": 60000},
    "credit_card_basic": {"min_income": 2500, "min_score": 600},
    "bond_fund":     {"id": "bond",     "name": "Bond Fund",           "exp": 0.05,  "vol": 0.04, "risk": 0.2},
    "balanced_fund": {"id": "balanced", "name": "Balanced Fund",       "exp": 0.065, "vol": 0.10, "risk": 0.45},
    "equity_etf":    {"id": "equity",   "name": "Global Equity ETF",   "exp": 0.08,  "vol": 0.18, "risk": 0.7},
    "business_deposit": {"rate": 0.03},
    "business_credit_line": {"rate": 0.105, "months": 12},
}

USERS = {u.user_id: u for u in [
    UserProfile("ana", "Ana", 20, "student", 1800, 0, 1500, 1400, 0, 600, "low",
                spend_by_category={"dining": 250, "entertainment": 150, "subscriptions": 60}),
    UserProfile("mihai", "Mihai", 34, "standard", 24000, 8000, 7000, 4000, 0, 780, "medium",
                has_savings_account=True, has_credit_card=True,
                spend_by_category={"dining": 400, "shopping": 500, "transport": 300}),
    UserProfile("elena", "Elena", 45, "premium", 60000, 90000, 18000, 9000, 0, 820, "high",
                has_savings_account=True, has_credit_card=True,
                spend_by_category={"dining": 900, "shopping": 1500, "entertainment": 400}),
    UserProfile("radu", "Radu", 41, "standard", 300, 0, 4000, 3900, 900, 560, "low",
                has_loan=True, spend_by_category={"dining": 500, "shopping": 600}),
    UserProfile("dan", "Dan", 29, "standard", 200, 0, 4000, 4200, 0, 700, "medium",
                spend_by_category={"dining": 600, "entertainment": 300}),
    UserProfile("victor", "Victor", 31, "standard", 6000, 0, 5000, 3000, 1500, 690, "medium",
                has_loan=True, has_credit_card=True,
                spend_by_category={"dining": 700, "shopping": 800, "subscriptions": 250}),
    UserProfile("ioana", "Ioana (business)", 38, "business", 120000, 0, 50000, 30000, 0, 760, "medium"),
]}
