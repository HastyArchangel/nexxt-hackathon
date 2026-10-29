"""Terminal demo: python main.py [user_id ...]"""
import sys
from app.data import USERS
from app.orchestrator import Orchestrator

orch = Orchestrator()
ids = sys.argv[1:] or list(USERS)
for uid in ids:
    u = USERS[uid]
    feed = orch.home_feed(u)
    print(f"\n=== {u.name} | {u.account_type} | cash {u.balance:,.0f} RON | score {u.credit_score} ===")
    print(f"plan [{feed['plan']['source']}]: {feed['plan']['agents']}" + ("  (replanned)" if feed["replanned"] else ""))
    for it in feed["items"]:
        tag = "ALERT" if it["placement"] == "alert" else "card "
        print(f"  {tag} {it['score']:.2f}  [{it['agent']}] {it['title']}")
    for b in feed["blocked"]:
        print(f"  BLOCKED {b['card_id']}: {b['reason']}")
