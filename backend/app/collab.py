"""
Collaborative filtering via alternating least squares (ALS) — pure stdlib.

The TF-IDF engine scores what a student *says* (interests, goals). This
module scores what students *did*: logged outcomes become a students x
opportunities ratings matrix, factorized as R ~ U · Vᵀ so that opportunities
liked by similar students land near each other in a small latent space.

Two halves, deliberately separated:

  Training (offline, scripts/train_als.py): alternate closed-form
  least-squares solves for user rows and item rows until RMSE settles,
  then write the ITEM factors to app/data/als_item_factors.json. User
  factors are never shipped — they are derivable and privacy-irrelevant
  to keep.

  Serving (here, at request time): "fold in" the current student — one
  regularized least-squares solve of their own outcomes against the fixed
  item factors — then predict a score for every opportunity. Students with
  no logged outcomes get no collaborative signal (the term simply stays
  out of their ranking; nothing is invented for them).

The linear algebra is a k x k Gaussian elimination (k = 8), small enough
to derive by hand — consistent with the rest of the engine, no numpy.
"""

from __future__ import annotations

import json
import math
import pathlib
import random
from functools import lru_cache

# Outcome status → rating. Signs mirror the pathway edge-weight trigger:
# what strengthens an edge strengthens a preference.
STATUS_RATING: dict[str, float] = {
    "accepted": 1.0,
    "completed": 0.8,
    "waitlisted": 0.3,
    "withdrew": -0.3,
    "rejected": -0.5,
}

FACTORS_PATH = pathlib.Path(__file__).parent / "data" / "als_item_factors.json"

# Serving-time blend parameters (read by match.py). The collaborative term
# nudges, never dominates: at weight 0.15 it moves a score by at most ±0.075.
COLLAB_WEIGHT = 0.15


# --------------------------------------------------------------------------
# Small dense linear algebra (k x k), stdlib only
# --------------------------------------------------------------------------

def solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve A x = b by Gaussian elimination with partial pivoting.

    A is k x k and symmetric positive definite in our usage (Gram matrix
    plus L2 ridge), so the pivot never vanishes; pivoting is kept anyway
    for numerical hygiene.
    """
    n = len(b)
    # Augmented copy so callers' matrices stay untouched.
    m = [row[:] + [b[i]] for i, row in enumerate(a)]

    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[pivot] = m[pivot], m[col]
        pivot_val = m[col][col]
        if abs(pivot_val) < 1e-12:
            pivot_val = 1e-12
        for r in range(col + 1, n):
            factor = m[r][col] / pivot_val
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                m[r][c] -= factor * m[col][c]

    x = [0.0] * n
    for row in range(n - 1, -1, -1):
        acc = m[row][n] - sum(m[row][c] * x[c] for c in range(row + 1, n))
        denom = m[row][row] if abs(m[row][row]) > 1e-12 else 1e-12
        x[row] = acc / denom
    return x


def _least_squares_row(
    ratings: list[tuple[list[float], float]],
    n_factors: int,
    l2: float,
) -> list[float]:
    """Closed-form ridge solve for one row (user or item).

    minimizes  Σ (r - x·v)²  +  l2‖x‖²   over x,
    i.e. solve  (Σ v vᵀ + l2·I) x = Σ r·v.
    """
    gram = [[l2 if i == j else 0.0 for j in range(n_factors)] for i in range(n_factors)]
    rhs = [0.0] * n_factors
    for vec, rating in ratings:
        for i in range(n_factors):
            rhs[i] += rating * vec[i]
            for j in range(n_factors):
                gram[i][j] += vec[i] * vec[j]
    return solve(gram, rhs)


# --------------------------------------------------------------------------
# Training
# --------------------------------------------------------------------------

def train_als(
    interactions: list[tuple[str, str, float]],
    n_factors: int = 8,
    l2: float = 0.1,
    iterations: int = 15,
    seed: int = 20261103,
) -> tuple[dict[str, list[float]], dict[str, list[float]], list[float]]:
    """Factorize (user, item, rating) triples; returns (U, V, rmse_history)."""
    rng = random.Random(seed)
    users = sorted({u for u, _, _ in interactions})
    items = sorted({i for _, i, _ in interactions})

    def small_vec() -> list[float]:
        return [rng.gauss(0.0, 0.1) for _ in range(n_factors)]

    user_factors = {u: small_vec() for u in users}
    item_factors = {i: small_vec() for i in items}

    by_user: dict[str, list[tuple[str, float]]] = {u: [] for u in users}
    by_item: dict[str, list[tuple[str, float]]] = {i: [] for i in items}
    for u, i, r in interactions:
        by_user[u].append((i, r))
        by_item[i].append((u, r))

    rmse_history: list[float] = []
    for _ in range(iterations):
        for u, rated in by_user.items():
            user_factors[u] = _least_squares_row(
                [(item_factors[i], r) for i, r in rated], n_factors, l2
            )
        for i, rated in by_item.items():
            item_factors[i] = _least_squares_row(
                [(user_factors[u], r) for u, r in rated], n_factors, l2
            )
        se = 0.0
        for u, i, r in interactions:
            pred = predict(user_factors[u], item_factors[i])
            se += (r - pred) ** 2
        rmse_history.append(math.sqrt(se / len(interactions)))

    return user_factors, item_factors, rmse_history


def predict(user_vec: list[float], item_vec: list[float]) -> float:
    return sum(a * b for a, b in zip(user_vec, item_vec))


# --------------------------------------------------------------------------
# Serving
# --------------------------------------------------------------------------

def fold_in_user(
    outcome_pairs: list[tuple[str, float]],
    item_factors: dict[str, list[float]],
    n_factors: int,
    l2: float,
) -> list[float] | None:
    """One ridge solve for the current student against fixed item factors."""
    rated = [
        (item_factors[item_id], rating)
        for item_id, rating in outcome_pairs
        if item_id in item_factors
    ]
    if not rated:
        return None
    return _least_squares_row(rated, n_factors, l2)


@lru_cache(maxsize=1)
def load_item_factors() -> dict | None:
    """The trained artifact, or None when no model has been trained yet."""
    try:
        return json.loads(FACTORS_PATH.read_text())
    except (OSError, ValueError):
        return None


def collaborative_scores(
    outcomes: list[dict],
    opportunity_ids: list[str],
) -> dict[str, float]:
    """Map opportunity_id → collaborative score in [0, 1].

    Returns {} when there is no trained model or the student has no usable
    outcomes — callers treat an empty dict as "no collaborative signal."
    Predictions live on the rating scale [-0.5, 1.0] and are mapped
    linearly onto [0, 1] so 0.5 means "no opinion."
    """
    artifact = load_item_factors()
    if not artifact:
        return {}

    item_factors: dict[str, list[float]] = artifact.get("items", {})
    n_factors = int(artifact.get("k", 8))
    l2 = float(artifact.get("l2", 0.1))

    pairs = [
        (o["opportunity_id"], STATUS_RATING[o["status"]])
        for o in outcomes
        if o.get("status") in STATUS_RATING and o.get("opportunity_id")
    ]
    user_vec = fold_in_user(pairs, item_factors, n_factors, l2)
    if user_vec is None:
        return {}

    scores: dict[str, float] = {}
    for opp_id in opportunity_ids:
        vec = item_factors.get(opp_id)
        if vec is None:
            continue
        raw = predict(user_vec, vec)  # rating scale, roughly [-0.5, 1.0]
        scores[opp_id] = min(1.0, max(0.0, (raw + 0.5) / 1.5))
    return scores
