"""
Train the ALS collaborative model and write app/data/als_item_factors.json.

Data comes from two sources, kept honest and clearly labeled:

  1. Real outcomes from public.outcomes (every logged accepted/rejected/...
     row). With one demo user this is a handful of rows, that's fine, it
     grows with use, and retraining folds it in with more weight over time.

  2. A synthetic bootstrap cohort: seeded, simulated students whose outcome
     behavior follows one simple rule, students succeed more often in
     opportunities matching their interest fields. This exists only to give
     the latent space a sensible shape before real data accumulates (the
     classic cold-start move), and the artifact records exactly how many
     synthetic vs real users trained it.

Requires SUPABASE_URL + SUPABASE_SECRET_KEY in backend/.env (the catalog's
opportunity ids live in the database). Retrain whenever outcomes accumulate:

    cd backend && .venv/bin/python scripts/train_als.py
"""

from __future__ import annotations

import json
import os
import pathlib
import random
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.collab import FACTORS_PATH, STATUS_RATING, train_als  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass

N_FACTORS = 8
L2 = 0.1
ITERATIONS = 15
SEED = 20261103
SYNTHETIC_STUDENTS = 60

# The synthetic cohort's one behavioral rule (see module docstring).
P_POSITIVE_MATCHING_FIELD = 0.75
P_POSITIVE_OTHER_FIELD = 0.25
POSITIVE_STATUSES = ["accepted", "completed", "waitlisted"]
NEGATIVE_STATUSES = ["rejected", "withdrew"]

FIELDS = ["cs", "biology", "math", "physics", "engineering", "interdisciplinary"]


def fetch_catalog_and_outcomes() -> tuple[list[dict], list[dict]]:
    from supabase import create_client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SECRET_KEY", "")
    if not url or not key:
        sys.exit("Missing SUPABASE_URL / SUPABASE_SECRET_KEY in backend/.env.")
    sb = create_client(url, key)
    catalog = (
        sb.table("opportunities").select("id, opportunity_field").execute().data
        or []
    )
    outcomes = (
        sb.table("outcomes").select("student_id, opportunity_id, status").execute().data
        or []
    )
    return catalog, outcomes


def synthesize(catalog: list[dict], rng: random.Random) -> list[tuple[str, str, float]]:
    interactions: list[tuple[str, str, float]] = []
    for n in range(SYNTHETIC_STUDENTS):
        student_fields = set(rng.sample(FIELDS, rng.choice([1, 1, 2])))
        sample_size = min(rng.randint(4, 8), len(catalog))
        for opp in rng.sample(catalog, sample_size):
            matching = opp.get("opportunity_field") in student_fields
            p = P_POSITIVE_MATCHING_FIELD if matching else P_POSITIVE_OTHER_FIELD
            status = rng.choice(
                POSITIVE_STATUSES if rng.random() < p else NEGATIVE_STATUSES
            )
            interactions.append(
                (f"synthetic:{n}", opp["id"], STATUS_RATING[status])
            )
    return interactions


def main() -> None:
    rng = random.Random(SEED)
    catalog, real_outcomes = fetch_catalog_and_outcomes()
    if not catalog:
        sys.exit("No opportunities in the database — seed the catalog first.")

    interactions = synthesize(catalog, rng)
    real_users = set()
    for row in real_outcomes:
        status = row.get("status")
        if status not in STATUS_RATING:
            continue
        real_users.add(row["student_id"])
        interactions.append(
            (f"real:{row['student_id']}", row["opportunity_id"], STATUS_RATING[status])
        )

    _, item_factors, rmse = train_als(
        interactions, n_factors=N_FACTORS, l2=L2, iterations=ITERATIONS, seed=SEED
    )

    artifact = {
        "k": N_FACTORS,
        "l2": L2,
        "iterations": ITERATIONS,
        "seed": SEED,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "synthetic_users": SYNTHETIC_STUDENTS,
        "real_users": len(real_users),
        "real_outcome_rows": len(real_outcomes),
        "interactions": len(interactions),
        "rmse_first": round(rmse[0], 4),
        "rmse_last": round(rmse[-1], 4),
        "items": {
            item_id: [round(x, 6) for x in vec]
            for item_id, vec in item_factors.items()
        },
    }

    FACTORS_PATH.parent.mkdir(exist_ok=True)
    FACTORS_PATH.write_text(json.dumps(artifact, indent=1))

    print(f"catalog: {len(catalog)} opportunities")
    print(
        f"interactions: {len(interactions)} "
        f"({SYNTHETIC_STUDENTS} synthetic users, {len(real_users)} real users, "
        f"{len(real_outcomes)} real outcome rows)"
    )
    print(f"rmse: {rmse[0]:.4f} -> {rmse[-1]:.4f} over {ITERATIONS} iterations")
    print(f"item factors -> {FACTORS_PATH}")


if __name__ == "__main__":
    main()
