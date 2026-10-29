from __future__ import annotations
import time
from ..models import UserProfile, Context, Recommendation


class Trace:
    """Audit log of one request: who decided what and which tools were called."""

    def __init__(self):
        self.events: list[dict] = []
        self._t0 = time.perf_counter()

    def add(self, actor: str, action: str, **detail):
        self.events.append({"t_ms": round((time.perf_counter() - self._t0) * 1000, 1),
                            "actor": actor, "action": action, **detail})


def _short(v):
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, UserProfile):
        return v.user_id
    if isinstance(v, (int, str, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple, dict)):
        return f"{type(v).__name__}[{len(v)}]"
    return type(v).__name__


class Agent:
    name = ""
    description = ""

    def run(self, user: UserProfile, ctx: Context, trace: Trace) -> list[Recommendation]:
        raise NotImplementedError

    def use(self, trace: Trace, fn, *args):
        """Call a tool and log the call in the trace."""
        out = fn(*args)
        trace.add(self.name, f"tool:{fn.__name__}", args=[_short(a) for a in args], result=_short(out))
        return out
