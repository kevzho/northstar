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
    Mission,
    MissionCompleteBody,
    MissionCompletion,
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
    # Error tracking, armed only when SENTRY_DSN is set (production).
    # Local dev and CI run without it and without noise.
    import os

    dsn = os.getenv("SENTRY_DSN", "")
    if dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)

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
            .select("id, name, email, grade, interests, goals, audience, trait_scores, field_scores, handle, public_profile, onboarded, consented_at")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        if not (row.data if row else None):
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

        # Append to history unless nothing changed — re-finishing the quiz
        # with identical answers is a visit, not an evolution.
        try:
            latest = (
                sb.table("profile_history")
                .select("trait_scores, field_scores")
                .eq("student_id", user.id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            last = (latest.data or [{}])[0] if latest.data else {}
            if (
                last.get("trait_scores") != body.trait_scores
                or last.get("field_scores") != body.field_scores
            ):
                sb.table("profile_history").insert(
                    {
                        "student_id": user.id,
                        "trait_scores": body.trait_scores,
                        "field_scores": body.field_scores,
                    },
                    returning="minimal",
                ).execute()
        except Exception:
            # History is additive; its failure must never fail the sync.
            pass

        return {"synced": True}

    @app.get("/timeline")
    def timeline(user: CurrentUser = RequireUser) -> list[dict]:
        """The evidence stream: every recorded step, newest first.

        Aggregates assessment syncs (with field deltas between consecutive
        snapshots), mission completions, outcomes, bookmarks, and
        dismissals into one chronological list of
        ``{kind, at, title, detail}`` events.
        """

        from .db import get_supabase

        sb = get_supabase()
        events: list[dict] = []

        def opp_titles() -> dict:
            rows = sb.table("opportunities").select("id, title").execute()
            return {r["id"]: r["title"] for r in (rows.data or [])}

        titles = opp_titles()

        history = (
            sb.table("profile_history")
            .select("field_scores, created_at")
            .eq("student_id", user.id)
            .order("created_at")
            .execute()
        ).data or []
        previous: dict = {}
        for row in history:
            current = row.get("field_scores") or {}
            deltas = [
                f"{field} {'+' if current[field] > previous.get(field, 0) else ''}"
                f"{round(current[field] - previous.get(field, 0))}"
                for field in current
                if round(current[field] - previous.get(field, 0)) != 0
            ]
            events.append({
                "kind": "assessment",
                "at": row["created_at"],
                "title": "Assessment synced",
                "detail": ", ".join(deltas[:3]) if previous else "first profile snapshot",
            })
            previous = current

        completions = (
            sb.table("mission_completions")
            .select("evidence, created_at, missions(title, trait_focus)")
            .eq("student_id", user.id)
            .execute()
        ).data or []
        for row in completions:
            mission = row.get("missions") or {}
            events.append({
                "kind": "mission",
                "at": row["created_at"],
                "title": mission.get("title", "Mission completed"),
                "detail": row.get("evidence", ""),
            })

        outcomes = (
            sb.table("outcomes")
            .select("opportunity_id, status, created_at")
            .eq("student_id", user.id)
            .execute()
        ).data or []
        for row in outcomes:
            events.append({
                "kind": "outcome",
                "at": row["created_at"],
                "title": titles.get(row["opportunity_id"], "An opportunity"),
                "detail": row["status"],
            })

        marks = (
            sb.table("bookmarks")
            .select("opportunity_id, created_at")
            .eq("student_id", user.id)
            .execute()
        ).data or []
        for row in marks:
            events.append({
                "kind": "bookmark",
                "at": row["created_at"],
                "title": titles.get(row["opportunity_id"], "An opportunity"),
                "detail": "bookmarked",
            })

        gone = (
            sb.table("dismissals")
            .select("opportunity_id, created_at")
            .eq("student_id", user.id)
            .execute()
        ).data or []
        for row in gone:
            events.append({
                "kind": "dismissal",
                "at": row["created_at"],
                "title": titles.get(row["opportunity_id"], "An opportunity"),
                "detail": "not for me",
            })

        events.sort(key=lambda e: e["at"] or "", reverse=True)
        return events

    @app.post("/advisor")
    def route_advisor(
        body: dict,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Exploratory route advice grounded in the student's own matches.

        Returns {answer, sources} where sources are the numbered catalog
        entries the model was allowed to cite. 503 when no LLM key is
        configured — the feature is off, not broken.
        """

        from .advisor import advisor_enabled, ask_advisor, build_sources
        from .db import get_supabase

        if not advisor_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Advisor not configured (LLM_API_KEY unset).",
            )

        question = str(body.get("question", "")).strip()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A question is required.",
            )

        sb = get_supabase()
        prof = (
            sb.table("students")
            .select("interests, goals, audience, trait_scores, field_scores")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        student = (prof.data if prof else None) or {}

        cat = sb.table("opportunities").select("*").execute()
        shelf = student.get("audience") or "high_school"
        opportunities = [
            o for o in (cat.data or [])
            if (o.get("audience") or "high_school") == shelf
        ]
        ranked = score_opportunities(student, opportunities)
        sources = build_sources(ranked)

        try:
            answer = ask_advisor(question, student, sources)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The advisor's model call failed; try again shortly.",
            )
        return {"answer": answer, "sources": sources}

    @app.post("/sharing")
    def update_sharing(
        body: dict,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Set the handle and/or the public toggle on the student's record."""
        from .db import get_supabase
        from .social import valid_handle

        updates: dict = {}
        if "handle" in body:
            handle = str(body["handle"] or "").strip().lower()
            if handle and not valid_handle(handle):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Handles are 3-20 characters: lowercase letters, digits, dashes.",
                )
            updates["handle"] = handle or None
        if "public_profile" in body:
            updates["public_profile"] = bool(body["public_profile"])
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Nothing to update.",
            )

        sb = get_supabase()
        try:
            result = (
                sb.table("students")
                .update(updates, returning="representation")
                .eq("id", user.id)
                .execute()
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That handle is taken.",
            )
        if not (result.data if result else None):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found. POST /students to create.",
            )
        row = result.data[0]
        return {"handle": row.get("handle"), "public_profile": row.get("public_profile")}

    @app.get("/public/{handle}")
    def public_profile(handle: str) -> dict:
        """The shareable record — deliberately unauthenticated.

        Serves highlights only, and only for students who opted in
        (public_profile true). Everyone else is a uniform 404, so the
        endpoint cannot be used to probe which handles exist.
        """

        from .db import get_supabase
        from .social import public_payload

        sb = get_supabase()
        row = (
            sb.table("students")
            .select("id, name, handle, audience, trait_scores, field_scores, chosen_archetype, chosen_kind, public_profile")
            .eq("handle", handle.lower())
            .maybe_single()
            .execute()
        )
        student = row.data if row else None
        if not student or not student.get("public_profile"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No public profile here.",
            )
        return public_payload(sb, student)

    @app.post("/chosen-path")
    def sync_chosen_path(
        body: dict,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Persist the charted path so friends can compare career choices."""
        from .db import get_supabase

        archetype = str(body.get("archetype_id", ""))[:60]
        kind = str(body.get("kind", ""))[:20]
        sb = get_supabase()
        sb.table("students").update(
            {"chosen_archetype": archetype or None, "chosen_kind": kind or None}
        ).eq("id", user.id).execute()
        return {"synced": True}

    @app.post("/friends")
    def send_friend_request(
        body: dict,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Request friendship by handle. The target must have set one."""
        from .db import get_supabase

        handle = str(body.get("handle", "")).strip().lower()
        if not handle:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A handle is required.",
            )
        sb = get_supabase()
        target_row = (
            sb.table("students").select("id").eq("handle", handle).maybe_single().execute()
        )
        target = target_row.data if target_row else None
        if not target or target["id"] == user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No student with that handle.",
            )
        # One row per pair, whichever direction exists.
        existing = (
            sb.table("friendships")
            .select("id, status")
            .or_(
                f"and(requester.eq.{user.id},addressee.eq.{target['id']}),"
                f"and(requester.eq.{target['id']},addressee.eq.{user.id})"
            )
            .execute()
        ).data or []
        if existing:
            return {"id": existing[0]["id"], "status": existing[0]["status"]}
        result = (
            sb.table("friendships")
            .insert(
                {"requester": user.id, "addressee": target["id"]},
                returning="representation",
            )
            .execute()
        )
        return {"id": result.data[0]["id"], "status": "pending"}

    @app.get("/friends")
    def list_friends(user: CurrentUser = RequireUser) -> dict:
        """Accepted friends plus pending requests, with handles and names."""
        from .db import get_supabase
        from .social import first_name

        sb = get_supabase()
        rows = (
            sb.table("friendships")
            .select("id, requester, addressee, status, created_at")
            .or_(f"requester.eq.{user.id},addressee.eq.{user.id}")
            .order("created_at", desc=True)
            .execute()
        ).data or []

        other_ids = list({
            (r["addressee"] if r["requester"] == user.id else r["requester"])
            for r in rows
        })
        people: dict[str, dict] = {}
        if other_ids:
            students = (
                sb.table("students")
                .select("id, name, handle")
                .in_("id", other_ids)
                .execute()
            ).data or []
            people = {s["id"]: s for s in students}

        def entry(r: dict) -> dict:
            other_id = r["addressee"] if r["requester"] == user.id else r["requester"]
            other = people.get(other_id, {})
            return {
                "id": r["id"],
                "student_id": other_id,
                "name": first_name(other.get("name")),
                "handle": other.get("handle"),
                "direction": "sent" if r["requester"] == user.id else "received",
            }

        return {
            "accepted": [entry(r) for r in rows if r["status"] == "accepted"],
            "pending": [entry(r) for r in rows if r["status"] == "pending"],
        }

    @app.post("/friends/{friendship_id}/accept")
    def accept_friend(
        friendship_id: str,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Only the addressee can accept."""
        from .db import get_supabase

        sb = get_supabase()
        result = (
            sb.table("friendships")
            .update({"status": "accepted"}, returning="representation")
            .eq("id", friendship_id)
            .eq("addressee", user.id)
            .execute()
        )
        if not (result.data if result else None):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No such pending request for you.",
            )
        return {"status": "accepted"}

    @app.delete("/friends/{friendship_id}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_friend(
        friendship_id: str,
        user: CurrentUser = RequireUser,
    ):
        """Either party can decline or unfriend."""
        from .db import get_supabase

        sb = get_supabase()
        sb.table("friendships").delete().eq("id", friendship_id).or_(
            f"requester.eq.{user.id},addressee.eq.{user.id}"
        ).execute()

    @app.get("/discover")
    def discover(user: CurrentUser = RequireUser) -> list[dict]:
        """Opted-in peers who share the student's interests, ranked.

        Gated by the target's public_profile flag — only findable students
        appear — and by same audience. Excludes anyone already connected.
        Empty list (not an error) when the student has no profile or when
        no one else has opted in yet.
        """

        from .db import get_supabase
        from .social import discover_peers

        sb = get_supabase()
        me_row = (
            sb.table("students")
            .select("id, audience, field_scores, chosen_archetype, chosen_kind")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        me = me_row.data if me_row else None
        if not me:
            return []

        links = (
            sb.table("friendships")
            .select("requester, addressee")
            .or_(f"requester.eq.{user.id},addressee.eq.{user.id}")
            .execute()
        ).data or []
        exclude = {
            (link["addressee"] if link["requester"] == user.id else link["requester"])
            for link in links
        }
        return discover_peers(sb, me, exclude)

    @app.get("/friends/{student_id}/compare")
    def compare_with_friend(
        student_id: str,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Side-by-side records — accepted friendships only."""
        from .db import get_supabase
        from .social import compare_payload

        sb = get_supabase()
        link = (
            sb.table("friendships")
            .select("id")
            .eq("status", "accepted")
            .or_(
                f"and(requester.eq.{user.id},addressee.eq.{student_id}),"
                f"and(requester.eq.{student_id},addressee.eq.{user.id})"
            )
            .execute()
        ).data or []
        if not link:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only compare with accepted friends.",
            )

        cols = "id, name, handle, audience, trait_scores, field_scores, chosen_archetype, chosen_kind"
        mine = (sb.table("students").select(cols).eq("id", user.id).maybe_single().execute())
        theirs = (sb.table("students").select(cols).eq("id", student_id).maybe_single().execute())
        me_row = mine.data if mine else None
        them_row = theirs.data if theirs else None
        if not me_row or not them_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile missing.")
        return {
            "me": compare_payload(sb, me_row),
            "friend": compare_payload(sb, them_row),
        }

    @app.get("/missions", response_model=list[Mission])
    def list_missions(
        archetype: str = "",
        user: CurrentUser = RequireUser,
    ) -> list[dict]:
        """Proof missions, optionally filtered to one archetype (path)."""
        from .db import get_supabase

        sb = get_supabase()
        query = sb.table("missions").select(
            "id, archetype_id, title, description, trait_focus, effort, sort_order"
        )
        if archetype:
            query = query.eq("archetype_id", archetype)
        result = query.order("sort_order").execute()
        return result.data or []

    @app.get("/missions/completions", response_model=list[MissionCompletion])
    def list_mission_completions(user: CurrentUser = RequireUser) -> list[dict]:
        """The student's completed missions, newest first."""
        from .db import get_supabase

        sb = get_supabase()
        result = (
            sb.table("mission_completions")
            .select("id, mission_id, evidence, created_at")
            .eq("student_id", user.id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    @app.post("/missions/{mission_id}/complete", response_model=MissionCompletion)
    def complete_mission(
        mission_id: str,
        body: MissionCompleteBody,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Record mission evidence onto the student record.

        Idempotent by the unique(student_id, mission_id) constraint —
        completing twice updates the evidence instead of duplicating.
        """

        from .db import get_supabase

        sb = get_supabase()
        row = {
            "student_id": user.id,
            "mission_id": mission_id,
            "evidence": body.evidence[:1000],
        }
        result = (
            sb.table("mission_completions")
            .upsert(row, on_conflict="student_id,mission_id", returning="representation")
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record mission completion",
            )
        return result.data[0]

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
        student = prof.data if prof else None
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
        if not (row.data if row else None):
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
        # Idempotent: the same (student, opportunity, status) is one fact.
        # A double-click updates notes instead of double-firing the
        # edge-weight trigger and polluting the ALS training data.
        result = (
            sb.table("outcomes")
            .upsert(
                row,
                on_conflict="student_id,opportunity_id,status",
                returning="representation",
            )
            .execute()
        )
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
        student = prof.data if prof else None
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

        # Limit to top 14 for a readable graph
        top = results[:14]

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
                "deadline": opp.get("deadline"),
                "tags": opp.get("tags", []) or [],
            })

        # Derive edges from shared tags + same field. A same-field pair
        # alone (0.4) qualifies; a lone shared tag (0.2) does not — weak
        # ties are what turn the graph into a hairball.
        edges = []
        for i, n1 in enumerate(nodes):
            for n2 in nodes[i + 1:]:
                weight = 0.0
                if n1["field"] and n1["field"] == n2["field"]:
                    weight += 0.4
                shared = set(n1["tags"]) & set(n2["tags"])
                weight += 0.2 * len(shared)
                if weight >= 0.4:
                    edges.append({
                        "source": n1["id"],
                        "target": n2["id"],
                        "weight": round(weight, 2),
                    })

        # Prune to a readable constellation: an edge survives only if it
        # ranks among either endpoint's three strongest. Clusters stay
        # legible; the O(n^2) same-field mesh does not.
        by_node: dict[str, list[dict]] = {}
        for edge in edges:
            by_node.setdefault(edge["source"], []).append(edge)
            by_node.setdefault(edge["target"], []).append(edge)
        keep: set[tuple[str, str]] = set()
        for node_edges in by_node.values():
            node_edges.sort(key=lambda e: e["weight"], reverse=True)
            for edge in node_edges[:3]:
                keep.add((edge["source"], edge["target"]))
        edges = [e for e in edges if (e["source"], e["target"]) in keep]

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
        student = prof.data if prof else None
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
