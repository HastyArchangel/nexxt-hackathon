import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .data import USERS
from .orchestrator import Orchestrator, REWARDS
from .planner import make_planner
from .ranker import LinUCBRanker

STATE_PATH = os.getenv("STATE_PATH", "state/ranker.npz")

app = FastAPI(title="Bank home-feed agents")
orch = Orchestrator(planner=make_planner(), ranker=LinUCBRanker.load_or_new(STATE_PATH))


class Event(BaseModel):
    user_id: str
    card_id: str
    event: str            # click | convert | dismiss


@app.get("/health")
def health():
    return {"ok": True, "planner": type(orch.planner).__name__, "updates": orch.ranker.n_updates}


@app.get("/users")
def users():
    return list(USERS)


@app.get("/home-feed/{user_id}")
def home_feed(user_id: str):
    user = USERS.get(user_id)
    if user is None:
        raise HTTPException(404, "unknown user")
    return orch.home_feed(user)


@app.post("/event")
def event(e: Event):
    if e.event not in REWARDS:
        raise HTTPException(422, f"event must be one of {list(REWARDS)}")
    if not orch.feedback(e.user_id, e.card_id, e.event):
        raise HTTPException(404, "this card was not shown to this user (call /home-feed first)")
    orch.ranker.save(STATE_PATH)
    return {"ok": True, "updates": orch.ranker.n_updates}
