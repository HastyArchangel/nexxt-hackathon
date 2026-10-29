# Bank home feed: orchestrator + specialist agents

```
GET /home-feed/{user}
   -> Orchestrator: derives context (surplus, DTI, emergency reserve, vulnerable?)
   -> Planner (rules or LLM): picks the agents allowed for this user
   -> Agents in parallel: savings | credit | investment | budget | business (calculation tools)
   -> Guardrail: blocks unsuitable recommendations (deterministic rules)
   -> Replan if fewer than 3 valid cards remain
   -> LinUCB ranker: score = priority (from the agent) + w * bandit
   -> alerts on top, then top-5 cards, plus a full audit trace
POST /event {user_id, card_id, event: click|convert|dismiss}  -> updates the bandit
```

## Run

    pip install -r requirements.txt
    python main.py                      # terminal demo
    python -m pytest -q                 # tests
    uvicorn app.api:app --reload        # API (docs at /docs)
    docker compose up --build           # PLANNER=llm also needs OPENAI_API_KEY

## Layout

    app/models.py        dataclasses: UserProfile, Context, Recommendation
    app/data.py          mock product catalog and synthetic users
    app/tools.py         pure calculation functions used by the agents as tools
    app/agents/          one file per specialist agent + guardrail + trace
    app/planner.py       RulePlanner and LLMPlanner (with fallback to rules)
    app/ranker.py        LinUCB ranker
    app/orchestrator.py  plan -> run -> guardrail -> replan -> rank
    app/api.py           FastAPI endpoints
