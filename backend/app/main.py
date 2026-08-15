"""
FastAPI app factory for Northstar.

Keep this module's surface tiny so that ``uvicorn backend.main:app`` keeps
working unchanged; the original top-level ``backend/main.py`` is rewritten as a
thin entrypoint that re-exports ``app`` from this package. See PROMPTS.md #4.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .auth import CurrentUser, RequireUser
from .schemas import (
    AssessmentProfileSync,
    Bookmark,
    BookmarkCreate,
    Dismissal,
    DismissalCreate,
    Outcome,
    OutcomeCreate,
    StudentProfile,
    StudentProfileCreate,
)
from .settings import settings

# Used only by POST /students to translate ``consent: True`` into the
# ``consented_at`` column. We keep the import at module level because
# datetime is stdlib and lru-caching it would add no value.
from datetime import datetime, timezone

from .match import score_opportunities


def create_app() -> FastAPI:
    app = FastAPI(title="Northstar API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "Northstar API running"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/me")
    def me(user: CurrentUser = RequireUser) -> dict:
        """Return the signed-in student's profile, or 404 if none yet.

        The 404 is a contract with the frontend: when the dashboard sees a
        404 on /me it knows to POST /students (task 2) and upsert the row
        keyed by ``auth.users.id``.
        """

        # Lazy import keeps the route registered even when the Supabase env
        # vars are unset (e.g. during unit tests of the JWT layer).
        from .db import get_supabase

        sb = get_supabase()
        row = (
            sb.table("students")
            .select("id, name, email, grade, interests, goals, audience, trait_scores, field_scores, onboarded, consented_at")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        if not row.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found. POST /students to create.",
            )
        return row.data

    @app.post("/students", response_model=StudentProfile)
    def create_student(
        body: StudentProfileCreate,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Upsert the student profile keyed by ``auth.users.id``.

        The caller sends name, grade, interests, goals, onboarded. The backend
        fills ``id`` from the JWT and copies ``email`` from the token's email
        claim (or whatever the Supabase auth user has). RLS on ``students``
        already restricts reads/updates to the owning student; the service-role
        client here bypasses RLS to perform the upsert itself.
        """

        from .db import get_supabase

        row = body.model_dump()
        row["id"] = user.id
        row["email"] = user.email  # from JWT; can be None

        # Translate consent checkbox → timestamp. We never null-out an
        # existing consented_at: when consent is False on a stub call we
        # just don't touch the column at all.
        consent = row.pop("consent", False)
        if consent:
            row["consented_at"] = datetime.now(timezone.utc).isoformat()

        sb = get_supabase()
        result = sb.table("students").upsert(row, returning="representation").execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upsert student profile",
            )
        return result.data[0]  # upsert with representation returns a list

    @app.post("/assessment-profile")
    def sync_assessment_profile(
        body: AssessmentProfileSync,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Persist the quiz's trait + field scores onto the student row.

        Touches only those two columns (see AssessmentProfileSync). 404s
        when no profile row exists yet — the frontend creates the stub via
        POST /students first, same contract as everywhere else.
        """

        from .db import get_supabase

        sb = get_supabase()
        result = (
            sb.table("students")
            .update(
                {
                    "trait_scores": body.trait_scores,
                    "field_scores": body.field_scores,
                },
                returning="representation",
            )
            .eq("id", user.id)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found. POST /students to create.",
            )
        return {"synced": True}

    @app.get("/dismissals", response_model=list[Dismissal])
    def list_dismissals(user: CurrentUser = RequireUser) -> list[dict]:
        """The student's "not for me" marks."""
        from .db import get_supabase

        sb = get_supabase()
        result = (
            sb.table("dismissals")
            .select("id, opportunity_id, created_at")
            .eq("student_id", user.id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    @app.post("/dismissals", response_model=Dismissal)
    def create_dismissal(
        body: DismissalCreate,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Mark an opportunity "not for me" — excluded from /match."""
        from .db import get_supabase

        sb = get_supabase()
        row = {"student_id": user.id, "opportunity_id": body.opportunity_id}
        result = (
            sb.table("dismissals")
            .upsert(row, on_conflict="student_id,opportunity_id", returning="representation")
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to dismiss opportunity",
            )
        return result.data[0]

    @app.delete("/dismissals/{opp_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_dismissal(
        opp_id: str,
        user: CurrentUser = RequireUser,
    ):
        """Undo a dismissal by opportunity id."""
        from .db import get_supabase

        sb = get_supabase()
        sb.table("dismissals").delete().eq("student_id", user.id).eq("opportunity_id", opp_id).execute()

    @app.get("/match")
    def match(user: CurrentUser = RequireUser) -> list[dict]:
        """Ranked recommendations for the signed-in student.

        Fetches the student profile + catalog from Supabase, runs the TF-IDF
        scoring engine (``app/match.py``), upserts the scored results into
        ``public.matches`` keyed on the existing ``unique(student_id,
        opportunity_id)`` constraint, and returns MatchResult[] sorted by
        score desc. Re-running refreshes scores (and explanations) without
        creating duplicate rows.
        """

        from .db import get_supabase

        sb = get_supabase()

        # Profile
        prof = (
            sb.table("students")
            .select("id, name, email, grade, interests, goals, audience, field_scores")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        student = prof.data
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found. POST /students to create.",
            )

        # Catalog (all opportunities; for MVP scale this is fine). Filtered
        # in Python to the student's audience shelf — rows predating the
        # audience column count as high_school, matching its DB default.
        cat = sb.table("opportunities").select("*").execute()
        shelf = student.get("audience") or "high_school"
        opportunities = [
            o for o in (cat.data or [])
            if (o.get("audience") or "high_school") == shelf
        ]

        # Behavioral signals: bookmarks nudge their fields up a little;
        # dismissed opportunities leave the list entirely. Both additive —
        # a fetch failure must never block matching.
        bookmarked_fields: dict[str, int] = {}
        dismissed_ids: set[str] = set()
        try:
            marks = (
                sb.table("bookmarks")
                .select("opportunity_id")
                .eq("student_id", user.id)
                .execute()
            )
            marked_ids = {b["opportunity_id"] for b in (marks.data or [])}
            by_id = {o.get("id"): o for o in (cat.data or [])}
            for opp_id in marked_ids:
                field = (by_id.get(opp_id) or {}).get("opportunity_field")
                if field:
                    bookmarked_fields[field] = bookmarked_fields.get(field, 0) + 1
            gone = (
                sb.table("dismissals")
                .select("opportunity_id")
                .eq("student_id", user.id)
                .execute()
            )
            dismissed_ids = {d["opportunity_id"] for d in (gone.data or [])}
        except Exception:
            pass

        # The student's own outcomes feed the collaborative term. Additive
        # signal only — its absence must never block matching.
        try:
            logged = (
                sb.table("outcomes")
                .select("opportunity_id, status")
                .eq("student_id", user.id)
                .execute()
            )
            outcome_rows = logged.data or []
        except Exception:
            outcome_rows = []

        results = score_opportunities(
            student,
            opportunities,
            outcome_rows,
            bookmarked_fields=bookmarked_fields,
            dismissed_ids=dismissed_ids,
        )
        # Sanitize the opportunity dict to the shape the frontend expects.
        # DB uses ``opportunity_field``; TS expects ``field``.
        for r in results:
            opp = dict(r["opportunity"])
            if "opportunity_field" in opp:
                opp["field"] = opp.pop("opportunity_field")
            r["opportunity"] = opp

        # Persist the scored set into public.matches — upsert keyed on
        # the existing unique(student_id, opportunity_id) constraint. We
        # send only the FK columns + score + explanation so the row
        # stays valid for the matches table's check constraints.
        if results:
            rows = [
                {
                    "student_id": user.id,
                    "opportunity_id": r["score"]["opportunity_id"],
                    "score": float(r["score"]["score"]),
                    "explanation": r["score"]["explanation"],
                }
                for r in results
                if r["score"]["opportunity_id"] is not None
            ]
            if rows:
                sb.table("matches").upsert(
                    rows,
                    on_conflict="student_id,opportunity_id",
                    returning="minimal",
                ).execute()

        return results

    @app.get("/opportunities/{opp_id}")
    def get_opportunity(
        opp_id: str,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Return a single opportunity row by id.

        Auth-gated so only signed-in students can browse the catalog. The
        response is sanitized: DB ``opportunity_field`` is renamed to
        ``field`` to match the frontend ``Opportunity`` type.
        """

        from .db import get_supabase

        sb = get_supabase()
        row = (
            sb.table("opportunities")
            .select("*")
            .eq("id", opp_id)
            .maybe_single()
            .execute()
        )
        if not row.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found.",
            )
        opp = dict(row.data)
        if "opportunity_field" in opp:
            opp["field"] = opp.pop("opportunity_field")
        return opp

    @app.get("/bookmarks", response_model=list[Bookmark])
    def list_bookmarks(user: CurrentUser = RequireUser) -> list[dict]:
        """Return the student's bookmarked opportunities."""
        from .db import get_supabase

        sb = get_supabase()
        result = (
            sb.table("bookmarks")
            .select("id, opportunity_id, created_at")
            .eq("student_id", user.id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    @app.post("/bookmarks", response_model=Bookmark)
    def create_bookmark(
        body: BookmarkCreate,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Bookmark an opportunity for the signed-in student."""
        from .db import get_supabase

        sb = get_supabase()
        row = {"student_id": user.id, "opportunity_id": body.opportunity_id}
        result = (
            sb.table("bookmarks")
            .upsert(row, on_conflict="student_id,opportunity_id", returning="representation")
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bookmark opportunity",
            )
        return result.data[0]

    @app.delete("/bookmarks/{opp_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_bookmark(
        opp_id: str,
        user: CurrentUser = RequireUser,
    ):
        """Remove a bookmark by opportunity id."""
        from .db import get_supabase

        sb = get_supabase()
        sb.table("bookmarks").delete().eq("student_id", user.id).eq("opportunity_id", opp_id).execute()

    @app.post("/outcomes")
    def log_outcome(
        body: OutcomeCreate,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Log the student's outcome for a bookmarked opportunity.

        This is the feedback loop that future edge-weight update logic
        will observe (task 17). For now, it just inserts into public.outcomes.
        """

        if body.status not in ("accepted", "rejected", "waitlisted", "withdrew", "completed"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid outcome status.",
            )

        from .db import get_supabase
        from datetime import datetime, timezone

        sb = get_supabase()
        row = {
            "student_id": user.id,
            "opportunity_id": body.opportunity_id,
            "status": body.status,
            "impact_notes": body.impact_notes,
        }
        result = sb.table("outcomes").insert(row, returning="representation").execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to log outcome.",
            )
        return result.data[0]

    @app.get("/outcomes", response_model=list[Outcome])
    def list_outcomes(user: CurrentUser = RequireUser) -> list[dict]:
        """Return the student's logged outcomes."""
        from .db import get_supabase

        sb = get_supabase()
        result = (
            sb.table("outcomes")
            .select("id, opportunity_id, status, impact_notes, created_at")
            .eq("student_id", user.id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    @app.get("/pathways")
    def pathways(user: CurrentUser = RequireUser) -> dict:
        """Return nodes + edges for the Northstar pathway map.

        Nodes are the student's matched opportunities (from /match scores).
        Edges are derived from shared tags + same field between nodes — a
        self-contained graph that renders even without seeded pathway_edges.
        Each node carries ``score`` and ``field`` for coloring/sizing in D3.
        """

        from .db import get_supabase

        sb = get_supabase()

        # Profile
        prof = (
            sb.table("students")
            .select("id, name, email, grade, interests, goals, audience")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        student = prof.data
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found.",
            )

        cat = sb.table("opportunities").select("*").execute()
        shelf = student.get("audience") or "high_school"
        opportunities = [
            o for o in (cat.data or [])
            if (o.get("audience") or "high_school") == shelf
        ]

        results = score_opportunities(student, opportunities)

        # Limit to top 20 for a readable graph
        top = results[:20]

        nodes = []
        for r in top:
            opp = dict(r["opportunity"])
            field = opp.get("opportunity_field") or opp.get("field", "")
            nodes.append({
                "id": opp["id"],
                "title": opp.get("title", ""),
                "field": field,
                "type": opp.get("type", ""),
                "score": float(r["score"]["score"]),
                "tags": opp.get("tags", []) or [],
            })

        # Derive edges from shared tags + same field
        edges = []
        for i, n1 in enumerate(nodes):
            for n2 in nodes[i + 1:]:
                weight = 0.0
                if n1["field"] and n1["field"] == n2["field"]:
                    weight += 0.4
                shared = set(n1["tags"]) & set(n2["tags"])
                weight += 0.2 * len(shared)
                if weight > 0:
                    edges.append({
                        "source": n1["id"],
                        "target": n2["id"],
                        "weight": round(weight, 2),
                    })

        return {"nodes": nodes, "edges": edges}

    @app.get("/projects")
    def list_projects(
        fields: str = "",
        user: CurrentUser = RequireUser,
    ) -> list[dict]:
        """Real GitHub repos worth contributing to, ranked per field.

        ``fields`` is a comma-separated subset of the opportunity fields
        (the frontend sends the quiz's leading fields). Unknown values are
        dropped; an empty list falls back to interdisciplinary.
        """

        from .projects import FIELD_TOPICS, recommend_projects

        requested = [f.strip() for f in fields.split(",") if f.strip()]
        valid = [f for f in requested if f in FIELD_TOPICS]
        return recommend_projects(valid or ["interdisciplinary"])

    @app.get("/mentors")
    def list_mentors(user: CurrentUser = RequireUser) -> list[dict]:
        """Ranked mentor recommendations for the signed-in student.

        Reuses the TF-IDF / cosine pipeline from app/mentors.py. All
        mentors are returned (``select *``) — there are <100 in the
        catalog at MVP scale, so no need for server-side prefilter.
        """

        from .db import get_supabase
        from .mentors import score_mentors

        sb = get_supabase()

        prof = (
            sb.table("students")
            .select("id, name, email, grade, interests, goals")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        student = prof.data
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found.",
            )

        catalog = sb.table("mentors").select("*").execute()
        rows = catalog.data or []

        results = score_mentors(student, rows)
        top = results[:10]  # dashboard shows top 5; cap at 10 for the list page

        return [
            {
                "mentor": r["mentor"],
                "score": r["score"],
            }
            for r in top
        ]

    return app


app = create_app()
