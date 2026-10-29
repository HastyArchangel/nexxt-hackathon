"""Adaptive ranking with LinUCB (inverse of A kept up to date via Sherman-Morrison)."""
from __future__ import annotations
import threading
from pathlib import Path
import numpy as np
from .models import UserProfile, Context, Recommendation

KINDS = ["savings", "credit", "investment", "budget", "business"]
RISK = {"low": 0.0, "medium": 0.5, "high": 1.0}
USER_DIM, CARD_DIM = 9, len(KINDS) + 2
DIM = USER_DIM + CARD_DIM + USER_DIM * CARD_DIM


def user_vector(user: UserProfile, ctx: Context) -> np.ndarray:
    return np.array([
        np.clip(np.log10(1 + max(user.balance, 0)) / 6, 0, 1),
        np.clip(np.log10(1 + user.monthly_income) / 5, 0, 1),
        np.clip(ctx.dti, 0, 1),
        np.clip(ctx.surplus / max(user.monthly_income, 1), -1, 1),
        user.age / 80,
        float(user.account_type == "student"),
        float(user.account_type == "premium"),
        float(user.account_type == "business"),
        RISK[user.risk_profile],
    ])


def card_vector(rec: Recommendation) -> np.ndarray:
    onehot = [float(rec.kind == k) for k in KINDS]
    return np.array(onehot + [rec.risk, rec.priority])


def features(u: np.ndarray, c: np.ndarray) -> np.ndarray:
    # the user x card interaction is essential; without it every user gets the same top
    return np.concatenate([u, c, np.outer(u, c).ravel()])


class LinUCBRanker:
    def __init__(self, alpha: float = 0.3, lam: float = 1.0):
        self.alpha = alpha
        self.A_inv = np.eye(DIM) / lam
        self.b = np.zeros(DIM)
        self.n_updates = 0
        self._lock = threading.Lock()

    def score(self, u: np.ndarray, cards: np.ndarray):
        """Return (mean, exploration bonus) for each card."""
        X = np.stack([features(u, c) for c in cards])
        with self._lock:
            theta = self.A_inv @ self.b
            mean = X @ theta
            bonus = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", X, self.A_inv, X), 0))
        return mean, self.alpha * bonus

    def update(self, u: np.ndarray, c: np.ndarray, reward: float):
        x = features(u, c)
        with self._lock:
            Ax = self.A_inv @ x
            self.A_inv -= np.outer(Ax, Ax) / (1.0 + x @ Ax)
            self.b += reward * x
            self.n_updates += 1

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            np.savez(path, A_inv=self.A_inv, b=self.b, n=self.n_updates, alpha=self.alpha)

    @classmethod
    def load_or_new(cls, path: str, **kw):
        r = cls(**kw)
        p = Path(path)
        if p.exists():
            d = np.load(p)
            r.A_inv, r.b, r.n_updates = d["A_inv"], d["b"], int(d["n"])
        return r
