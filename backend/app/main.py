"""
FastAPI app factory for Northstar.

Keep this module's surface tiny so that ``uvicorn backend.main:app`` keeps
working unchanged; the original top-level ``backend/main.py`` is rewritten as a
thin entrypoint that re-exports ``app`` from this package. See PROMPTS.md #4.
"""

from uuid import UUID

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
from .catalog import fetch_shelf, public_view, shelf_for
from .params import either_direction, uuid_field
from .settings import settings

# Used only by POST /students to translate ``consent: True`` into the
# ``consented_at`` column. We keep the import at module level because
# datetime is stdlib and lru-caching it would add no value.
from datetime import datetime, timezone

# The exact sentence a mentor agrees to, stored alongside their consent.
#
# Stored rather than referenced, because this wording will change and an old
# consent must keep meaning what it said at the time. 20260922090000 deleted 25
# invented mentor profiles partly because nobody could reconstruct afterwards
# what, if anything, any of them had agreed to.
CONSENT_TEXT = (
    "I am happy to be listed in Northstar's mentor directory, where high-school "
    "students can see my name, what I work on, and an email address they may "
    "write to. I understand students may contact me directly, that Northstar "
    "does not supervise those conversations, and that I can ask to be removed "
    "at any time."
)

from .match import score_opportunities

# How many scored rows GET /match persists into public.matches. The route used
# to write every one (144 per call). Twenty is more than any surface renders
# and keeps a live denominator for the impact figure — see the upsert comment
# in match().
MATCHES_PERSISTED = 20


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
        allow_origins=settings.frontend_urls,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "Northstar API running"}

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness, plus which build is answering.

        "Is the new code actually deployed?" was unanswerable from outside, and
        being unable to answer it cost real time twice: once when three files
        were committed but never pushed while main.py imported them (Vercel kept
        serving the last good build, so the symptom was "old behaviour", not an
        error), and once when the backend simply lagged the frontend and that
        looked like a bug.

        commit is Vercel's build SHA, short.

        semantic and advisor report whether each feature can actually RUN, not
        whether its module imports. The first version of this endpoint checked
        importability and would have answered "available" on a host with no
        LLM_API_KEY — a false green in the exact check written to prevent one.
        Both features need that key: without it /advisor 503s and no student
        ever gets a profile embedding, while the code and the frontend look
        completely fine.
        """
        import os

        def capability(probe) -> str:
            try:
                return "available" if probe() else "unconfigured"
            except Exception:
                return "unavailable"

        def semantic_probe() -> bool:
            from .embeddings import enabled

            return enabled()

        def advisor_probe() -> bool:
            from .advisor import advisor_enabled

            return advisor_enabled()

        return {
            "status": "ok",
            "commit": (os.getenv("VERCEL_GIT_COMMIT_SHA") or "local")[:7],
            "semantic": capability(semantic_probe),
            "advisor": capability(advisor_probe),
            # Which model is answering, because LLM_MODEL is set per
            # environment and a code default says nothing about production. On
            # 2026-10-26 the branch endpoint was fixed, deployed and still
            # broken, because prod pinned gpt-oss-20b and there was no way to
            # see that from outside. The name of a hosted model is public; the
            # key is what is secret, and that is not here.
            "model": settings.llm_model or "unset",
        }

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
            .select("id, name, email, grade, interests, goals, audience, location_pref, trait_scores, field_scores, handle, public_profile, social_links, onboarded, consented_at")
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

        # Same never-null-out contract for social links: absent means
        # "leave the column alone", present means "replace after validation".
        socials = row.pop("social_links", None)
        if socials is not None:
            from .social import clean_social_links

            try:
                row["social_links"] = clean_social_links(socials)
            except ValueError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(error),
                )

        sb = get_supabase()
        result = sb.table("students").upsert(row, returning="representation").execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upsert student profile",
            )
        # Re-embed the profile: interests and goals are both scoring inputs, and
        # `goals` is the only free text a student writes — the only field that
        # can express "I want to help people with cancer". Best effort: a stale
        # embedding costs ranking precision, a 500 here costs the student their
        # onboarding.
        from .embeddings import refresh_student_embedding

        refresh_student_embedding(sb, user.id, result.data[0])
        return result.data[0]  # upsert with representation returns a list

    @app.post("/assessment-profile")
    def sync_assessment_profile(
        body: AssessmentProfileSync,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Persist the quiz's trait + field scores onto the student row.

        Touches only those two columns (see AssessmentProfileSync). 404s
        when no profile row exists yet. The row is created by POST /students
        at the end of onboarding — the dashboard no longer writes a stub
        ahead of it, because that stub made an abandoned onboarding
        permanent.
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

        Returns {answer, sources, cached} where sources are the numbered
        catalog entries the model was allowed to cite. 503 when no LLM key
        is configured — the feature is off, not broken. 429 when the credit
        budget for the student, the minute, or the day is used up.
        """

        from .advisor import (
            advisor_enabled,
            ask_advisor,
            budget_block,
            build_sources,
            cache_key,
            cached_answer,
            record_call,
        )
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

        opportunities = fetch_shelf(sb, shelf_for(student))
        ranked = score_opportunities(student, opportunities)
        sources = build_sources(ranked)
        key = cache_key(question, sources)

        # Before the budget check, deliberately: a question already answered
        # over the same sources costs nothing, so it must not spend quota.
        hit = cached_answer(sb, key)
        if hit:
            return {
                "answer": hit["answer"],
                "sources": hit.get("sources") or sources,
                "cached": True,
            }

        refusal = budget_block(sb, user.id)
        if refusal:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=refusal,
            )

        try:
            result = ask_advisor(question, student, sources)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The advisor's model call failed; try again shortly.",
            )

        # The usage block is what lets the daily TOKEN budget mean anything. A
        # call ceiling limits how many questions are asked; this limits what they
        # cost, and at hundreds of users those stop being the same number.
        record_call(
            sb,
            user.id,
            key,
            question,
            result.text,
            sources,
            usage=(result.prompt_tokens, result.completion_tokens, result.total_tokens),
        )
        return {"answer": result.text, "sources": sources, "cached": False}

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
        # Ceiling on an action that costs a PERSON something rather than
        # money. See app/limits.py.
        from .limits import limit_block, record_event

        refused = limit_block(sb, "handle", user.id)
        if refused:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=refused
            )
        record_event(sb, "handle", user.id)

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
        from .social import public_payload, valid_handle

        # Unauthenticated, and `handle` reaches .eq() — whose criteria
        # postgrest-py does not escape. valid_handle is an allowlist, so a
        # handle that passes cannot carry a filter metacharacter. A reject
        # returns the SAME uniform 404 as an unknown handle, preserving the
        # property that this endpoint cannot be used to probe what exists.
        if not valid_handle(handle.lower()):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No public profile here.",
            )

        sb = get_supabase()
        row = (
            sb.table("students")
            .select("id, name, handle, audience, trait_scores, field_scores, chosen_archetype, chosen_kind, social_links, public_profile")
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
        from .social import blocked_ids

        handle = str(body.get("handle", "")).strip().lower()
        if not handle:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A handle is required.",
            )
        sb = get_supabase()
        # Ceiling on an action that costs a PERSON something rather than
        # money. See app/limits.py for why each of these has one.
        from .limits import limit_block, record_event

        refused = limit_block(sb, "friend_request", user.id)
        if refused:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=refused
            )
        record_event(sb, "friend_request", user.id)

        target_row = (
            sb.table("students").select("id").eq("handle", handle).maybe_single().execute()
        )
        target = target_row.data if target_row else None
        # A blocked pair gets the same 404 as an unknown handle, so blocking
        # is not detectable from the outside.
        if (
            not target
            or target["id"] == user.id
            or target["id"] in blocked_ids(sb, user.id)
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No student with that handle.",
            )
        # One row per pair, whichever direction exists.
        existing = (
            either_direction(
                sb.table("friendships").select("id, status"),
                "requester", "addressee", user.id, str(target["id"]),
            ).execute()
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
        friendship_id: UUID,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Only the addressee can accept."""
        from .db import get_supabase

        sb = get_supabase()
        result = (
            sb.table("friendships")
            .update({"status": "accepted"}, returning="representation")
            .eq("id", str(friendship_id))
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
        friendship_id: UUID,
        user: CurrentUser = RequireUser,
    ):
        """Either party can decline or unfriend."""
        from .db import get_supabase

        sb = get_supabase()
        sb.table("friendships").delete().eq("id", str(friendship_id)).or_(
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
        from .social import blocked_ids, discover_peers

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
        exclude |= blocked_ids(sb, user.id)
        return discover_peers(sb, me, exclude)

    @app.get("/friends/{student_id}/compare")
    def compare_with_friend(
        student_id: UUID,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Side-by-side records — accepted friendships only."""
        from .db import get_supabase
        from .social import compare_payload

        sb = get_supabase()
        # This filter IS the authorization gate, so it must not be built by
        # string interpolation: postgrest-py hands `.or_()` its argument
        # verbatim, and student_id used to arrive here as an unvalidated
        # path param. It is a UUID now, and the pair match is structural.
        friend_id = str(student_id)
        link = (
            either_direction(
                sb.table("friendships").select("id").eq("status", "accepted"),
                "requester", "addressee", user.id, friend_id,
            ).execute()
        ).data or []
        if not link:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only compare with accepted friends.",
            )

        cols = "id, name, handle, audience, trait_scores, field_scores, chosen_archetype, chosen_kind"
        mine = (sb.table("students").select(cols).eq("id", user.id).maybe_single().execute())
        theirs = (sb.table("students").select(cols).eq("id", friend_id).maybe_single().execute())
        me_row = mine.data if mine else None
        them_row = theirs.data if theirs else None
        if not me_row or not them_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile missing.")
        return {
            "me": compare_payload(sb, me_row),
            "friend": compare_payload(sb, them_row),
        }

    # -- Team up: mutual-interest collaborator / study-buddy matching -------
    #
    # Not dating. The pool is opt-in, interest is invisible until mutual,
    # and every surface carries report + block. A match simply creates an
    # accepted friendship — the same connection the rest of the app uses.

    @app.get("/teamup/settings")
    def teamup_settings(user: CurrentUser = RequireUser) -> dict:
        """Whether the student is in the matching pool, and their pitch."""
        from .db import get_supabase

        sb = get_supabase()
        row = (
            sb.table("students")
            .select("teamup_enabled, teamup_pitch")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        data = row.data if row else None
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found. POST /students to create.",
            )
        return {
            "enabled": bool(data.get("teamup_enabled")),
            "pitch": data.get("teamup_pitch") or "",
        }

    @app.post("/teamup/settings")
    def update_teamup_settings(
        body: dict,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Join or leave the matching pool and set the pitch."""
        from .db import get_supabase
        from .social import TEAMUP_PITCH_MAX

        updates: dict = {}
        if "enabled" in body:
            updates["teamup_enabled"] = bool(body["enabled"])
        if "pitch" in body:
            pitch = str(body["pitch"] or "").strip()[:TEAMUP_PITCH_MAX]
            updates["teamup_pitch"] = pitch or None
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Nothing to update.",
            )

        sb = get_supabase()
        result = (
            sb.table("students")
            .update(updates, returning="representation")
            .eq("id", user.id)
            .execute()
        )
        if not (result.data if result else None):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found. POST /students to create.",
            )
        row = result.data[0]
        return {
            "enabled": bool(row.get("teamup_enabled")),
            "pitch": row.get("teamup_pitch") or "",
        }

    @app.get("/teamup/candidates")
    def teamup_candidates_route(user: CurrentUser = RequireUser) -> list[dict]:
        """Ranked collaborator candidates for the signed-in student.

        409 until the student opts in themselves — you cannot browse the
        pool without being in it. Excludes existing connections (any
        status), anyone already decided on, and blocked pairs.
        """
        from .db import get_supabase
        from .social import blocked_ids, teamup_candidates

        sb = get_supabase()
        me_row = (
            sb.table("students")
            .select(
                "id, audience, field_scores, chosen_archetype, chosen_kind, teamup_enabled"
            )
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        me = me_row.data if me_row else None
        if not me:
            return []
        if not me.get("teamup_enabled"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Join team-up matching first.",
            )

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
        decided = (
            sb.table("teamup_interest")
            .select("target")
            .eq("student", user.id)
            .execute()
        ).data or []
        exclude |= {d["target"] for d in decided}
        exclude |= blocked_ids(sb, user.id)
        return teamup_candidates(sb, me, exclude)

    @app.post("/teamup/interest")
    def record_teamup_interest(
        body: dict,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Record interest or a pass; mutual interest connects both students.

        The target never learns about a one-sided decision — the response
        only says ``matched`` when BOTH said interested, at which point an
        accepted friendship is created (or the pending one is upgraded).
        """
        from .db import get_supabase
        from .social import blocked_ids

        target_id = uuid_field(body.get("student_id"), "student_id")
        decision = body.get("decision")
        if decision not in ("interested", "passed"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="decision must be one of: interested, passed.",
            )
        if target_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="That's you.",
            )

        sb = get_supabase()
        # Ceiling on an action that costs a PERSON something rather than
        # money. See app/limits.py.
        from .limits import limit_block, record_event

        refused = limit_block(sb, "teamup", user.id)
        if refused:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=refused
            )
        record_event(sb, "teamup", user.id)

        target_row = (
            sb.table("students")
            .select("id, teamup_enabled")
            .eq("id", target_id)
            .maybe_single()
            .execute()
        )
        target = target_row.data if target_row else None
        # Same 404 for unknown, opted-out, and blocked targets: no probing.
        if (
            not target
            or not target.get("teamup_enabled")
            or target_id in blocked_ids(sb, user.id)
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No such student in matching.",
            )

        sb.table("teamup_interest").upsert(
            {"student": user.id, "target": target_id, "decision": decision},
            on_conflict="student,target",
        ).execute()
        if decision == "passed":
            return {"matched": False}

        reciprocal = (
            sb.table("teamup_interest")
            .select("id")
            .eq("student", target_id)
            .eq("target", user.id)
            .eq("decision", "interested")
            .execute()
        ).data or []
        if not reciprocal:
            return {"matched": False}

        existing = (
            either_direction(
                sb.table("friendships").select("id, status"),
                "requester", "addressee", user.id, target_id,
            ).execute()
        ).data or []
        if existing:
            if existing[0]["status"] != "accepted":
                sb.table("friendships").update({"status": "accepted"}).eq(
                    "id", existing[0]["id"]
                ).execute()
        else:
            sb.table("friendships").insert(
                {"requester": user.id, "addressee": target_id, "status": "accepted"}
            ).execute()
        return {"matched": True}

    # -- Safety: report + block ---------------------------------------------

    @app.post("/report", status_code=status.HTTP_201_CREATED)
    def report_student(
        body: dict,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """File a safety report about another student.

        Reports go to a moderation queue read via the service role; the
        reported student never sees who filed. Accepts a student_id or a
        handle so every surface (cards, friends, public pages) can report.
        """
        from .db import get_supabase
        from .social import REPORT_DETAILS_MAX, REPORT_REASONS, valid_handle

        reason = body.get("reason")
        if reason not in REPORT_REASONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"reason must be one of: {', '.join(REPORT_REASONS)}.",
            )

        # Validate the whole request before building a database client. A
        # malformed id is refused by shape alone, so it should never cost a
        # connection — and a route that reaches for the client first cannot
        # be tested without credentials, which is how this ordering slipped
        # past a local run and failed in CI.
        raw_id = str(body.get("student_id", "")).strip()
        target_id = uuid_field(raw_id, "student_id") if raw_id else ""
        handle = str(body.get("handle", "")).strip().lower()
        if not target_id and not (handle and valid_handle(handle)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No such student.",
            )

        sb = get_supabase()
        # Ceiling on an action that costs a PERSON something rather than
        # money. See app/limits.py.
        from .limits import limit_block, record_event

        refused = limit_block(sb, "report", user.id)
        if refused:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=refused
            )
        record_event(sb, "report", user.id)

        if not target_id:
            # valid_handle is an allowlist (^[a-z0-9][a-z0-9-]{2,19}$), so a
            # handle that passes it cannot carry a PostgREST metacharacter
            # into the .eq() below — which postgrest-py does not escape.
            row = (
                sb.table("students")
                .select("id")
                .eq("handle", handle)
                .maybe_single()
                .execute()
            )
            target_id = (row.data or {}).get("id", "") if row else ""
        if not target_id or target_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No such student.",
            )

        sb.table("reports").insert({
            "reporter": user.id,
            "reported": target_id,
            "reason": reason,
            "details": str(body.get("details", "") or "").strip()[:REPORT_DETAILS_MAX] or None,
        }).execute()
        return {"filed": True}

    @app.post("/block", status_code=status.HTTP_201_CREATED)
    def block_student(
        body: dict,
        user: CurrentUser = RequireUser,
    ) -> dict:
        """Hard wall: removes any connection and hides both students from
        each other in discover, team-up, and friend requests."""
        from .db import get_supabase

        target_id = uuid_field(body.get("student_id"), "student_id")
        if target_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A student_id (not your own) is required.",
            )

        sb = get_supabase()
        sb.table("blocks").upsert(
            {"blocker": user.id, "blocked": target_id},
            on_conflict="blocker,blocked",
        ).execute()
        # DELETEs driven by a request-body value. These were built by
        # f-string into `.or_()`, which postgrest-py passes through verbatim,
        # so a filter injection here would have widened a delete.
        either_direction(
            sb.table("friendships").delete(),
            "requester", "addressee", user.id, target_id,
        ).execute()
        either_direction(
            sb.table("teamup_interest").delete(),
            "student", "target", user.id, target_id,
        ).execute()
        return {"blocked": True}

    @app.get("/roadmap")
    def roadmap(user: CurrentUser = RequireUser) -> dict:
        """The student's sequenced roadmap: what to do, in order.

        This is the route that makes Northstar something other than a ranked
        list. It assembles four kinds of step -- learn, build, publish, apply --
        and orders them on the student's grade progression rather than on
        catalog deadlines, because against production a 9th grader has exactly
        ONE catalog row with a future deadline and 25 of 61 are locked above
        their grade. A deadline-anchored sequencer has nothing to say to them.

        No model runs here. Provenance is a foreign key: a step naming a
        program or a course carries its id, so app/roadmap.py cannot emit a
        step for something absent from the catalog and the insert would refuse
        it anyway.

        Steps are persisted to public.actions under a generation, merged on
        step_key so completing a step survives a regeneration.
        """
        from datetime import date

        from .db import get_supabase
        from .resources import fetch_for_skill
        from .roadmap import build_roadmap
        from .spines import spine_for

        sb = get_supabase()

        prof = (
            sb.table("students")
            .select("id, name, grade, interests, goals, audience, location_pref, "
                    "field_scores, trait_scores, chosen_archetype, chosen_kind")
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

        archetype = student.get("chosen_archetype") or ""
        spine = spine_for(archetype)

        # A spine written for THIS student, when one has been generated, else
        # the authored one for their archetype.
        #
        # The fallback is a designed state, not a degraded one. Generation is
        # refused outright when the model picks a skill key with no verified
        # resources, writes a url, or returns prose that will not parse -- and in
        # each of those cases the hand-written spine is the better answer. See
        # app/spine_generation.py.
        #
        # Wrapped because the table arrives in 20261004120000 and this endpoint
        # must keep serving every student before that migration is applied.
        try:
            generated = (
                sb.table("generated_spines")
                .select("project, publish, skill, skill_key, model, generated_at")
                .eq("user_id", user.id)
                .maybe_single()
                .execute()
            )
            row = generated.data if generated else None
        except Exception:
            row = None
        if row and row.get("project") and row.get("skill_key"):
            spine = {
                "project": row["project"],
                "publish": row["publish"],
                "skill": row["skill"],
                "skillKey": row["skill_key"],
                # roadmap.py words authored edges as "a common route, not a
                # requirement". No human wrote this one, so it must not inherit
                # that sentence -- see the edge note in build_steps.
                "source": "generated",
                "model": row.get("model") or "",
            }

        # Resources for this path's skill rung. Absent spine or unseeded skill
        # returns [] and the roadmap simply has no learning steps, rather than
        # borrowing another path's.
        resources = (
            fetch_for_skill(sb, spine["skillKey"]) if spine else []
        )

        opportunities = fetch_shelf(sb, shelf_for(student))
        try:
            logged = (
                sb.table("outcomes")
                .select("opportunity_id, status")
                .eq("student_id", user.id)
                .execute()
            ).data or []
        except Exception:
            logged = []
        ranked = score_opportunities(student, opportunities, logged)
        for r in ranked:
            r["opportunity"] = public_view(r["opportunity"])

        missions: list[dict] = []
        if archetype:
            try:
                missions = (
                    sb.table("missions")
                    .select("id, title, description, trait_focus, effort, sort_order")
                    .eq("archetype_id", archetype)
                    .order("sort_order")
                    .execute()
                ).data or []
            except Exception:
                missions = []

        plan = build_roadmap(
            student, spine, resources, ranked, missions, date.today()
        )
        plan["archetype_id"] = archetype
        plan["has_spine"] = spine is not None
        plan["resource_count"] = len(resources)
        # Who wrote the path the student is reading, and whether the authored
        # one can actually deliver its learn rung.
        #
        # `spine_hollow` is the honest trigger for offering a written-for-you
        # path. Twelve of the twenty-four authored spines name a skillKey with
        # no verified resource behind it, so those students' learn rung renders
        # as nothing at all. The UI can offer a replacement where the shelf is
        # genuinely empty rather than nagging everyone.
        plan["spine_source"] = (spine or {}).get("source", "authored")
        plan["spine_hollow"] = bool(spine) and not resources

        # Sub-steps this student already asked for, keyed by the step they hang
        # under. Without this the table was write-only: you could break a step
        # down, reload, and watch the breakdown disappear while its row sat in
        # Postgres. Unread rows are worse than no rows -- they look like the
        # feature works until someone refreshes.
        try:
            saved = (
                sb.table("roadmap_branches")
                .select("parent_step_key, steps")
                .eq("user_id", user.id)
                .execute()
            ).data or []
        except Exception:
            saved = []
        plan["branches"] = {
            row["parent_step_key"]: row["steps"]
            for row in saved
            if isinstance(row.get("steps"), list) and row["steps"]
        }
        return plan

    @app.post("/roadmap/branch")
    def branch_step(body: dict | None = None, user: CurrentUser = RequireUser) -> dict:
        """Break one step of this student's plan into the moves inside it.

        THE THING THE PLAN COULD NOT DO. A roadmap step is a whole instruction
        -- "build a web app that calculates break-even" -- and a student who
        has never shipped one has no way to ask what that actually involves.
        They could accept the plan or regenerate the whole spine. Nothing in
        between. This is the in between: point at a step, get two or three
        concrete moves, written from the same profile the step came from.

        IDEMPOTENT PER STEP. One row per (student, parent step), replaced on
        request. Asking twice means wanting a different answer, not a second
        list -- and an unbounded children table behind a button on a diagram is
        how a plan becomes a thousand-item outline nobody reads.

        GATES, in the order they are cheapest to answer:
          1. a step_key, and a step title to work from
          2. app/limits.py "branch": 25 per student per day, 1500 across
             everyone -- this is a control on a diagram with a dozen nodes
          3. the advisor budget, the same wallet as the advisor, the manual
             regenerate and the automatic first path

        Refusals are quiet and leave the plan exactly as it was. See
        app/branch_generation.py for what is rejected: a url, a named
        programme, one step, six steps, or two identical ones.
        """
        from .advisor import budget_block, record_call
        from .branch_generation import (
            BRANCH_MAX_DEPTH,
            SYSTEM_PROMPT,
            build_prompt,
            parse_branch,
        )
        from .db import get_supabase
        from .limits import limit_block, record_event

        data = body or {}
        step_key = str(data.get("step_key") or "").strip()[:120]
        step_title = str(data.get("step_title") or "").strip()[:400]
        step_category = str(data.get("step_category") or "step").strip()[:40]
        reason = str(data.get("reason") or "").strip()[:300]
        if not step_key or not step_title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A step_key and step_title are required.",
            )

        # DEPTH CAP, enforced here and not only in the UI. A sub-step can be
        # broken down too -- "spine:project::branch:0::branch:1" -- and each
        # generation is a model call behind a button, so unbounded nesting is
        # an unbounded bill on one page. components/SubSteps.tsx stops offering
        # the control at the same number; this is what makes that a rule rather
        # than a suggestion, because the client is not the thing being billed.
        if step_key.count("::branch:") >= BRANCH_MAX_DEPTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "That is as far down as a step breaks. If the move in "
                    "front of you still is not startable, it is probably a "
                    "different step."
                ),
            )

        sb = get_supabase()

        prof = (
            sb.table("students")
            .select("id, grade, trait_scores, field_scores")
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

        refused = limit_block(sb, "branch", user.id)
        if refused:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=refused
            )
        # Not against the advisor's ten questions: limits.py already caps
        # this at 25 a day per student. See budget_block's docstring.
        blocked = budget_block(
            sb, user.id, per_student=False, what="step breakdown"
        )
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=blocked
            )

        # Counted before the call. Counting successes would make a step the
        # model keeps refusing free, and therefore pressable forever.
        record_event(sb, "branch", user.id)

        from .llm import LLMUnavailable, chat as llm_chat

        # TWO ATTEMPTS, AND WHY THE SECOND ONE EXISTS. Measured 2026-10-26 over
        # four real steps x three tries: gpt-oss-20b ignored
        # reasoning_effort="none" and spent the reply thinking out loud --
        # "We need to break ONE step of a high-school student's plan", then
        # counting characters by hand -- so the JSON never arrived inside 900
        # tokens. 5 of 12 usable. At 1600 tokens, 10 of 12 but a 16s median.
        # nemotron-3.5-bolt-e4b was 12 of 12 at 1.7s and is the default now.
        #
        # A retry is not a fix for a bad model, it is cover for the tail. One
        # extra call, only when the first reply was unusable, with the schema
        # restated. Worst case per press is two provider calls, so the 25/day
        # in limits.py is a 50-call ceiling, not 25. Said plainly because a
        # retry hidden behind a rate limit is how a budget stops meaning what
        # it says.
        user_prompt = build_prompt(step_title, step_category, student, reason)
        attempts: list[str] = []
        steps = None
        for attempt in range(2):
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
            if attempt:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your last reply was not usable. Reply with the "
                            'JSON object only -- {"steps": [{"title": "...", '
                            '"detail": "..."}]} -- and nothing before or '
                            "after it. No reasoning, no preamble."
                        ),
                    }
                )
            try:
                result = llm_chat(
                    base=settings.llm_api_base,
                    key=settings.llm_api_key,
                    model=settings.llm_model,
                    messages=messages,
                    max_tokens=1600,
                    temperature=0.4,
                    response_format={"type": "json_object"},
                    reasoning_effort="none",
                )
            except LLMUnavailable:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Could not reach the model just now. Your plan is "
                        "unchanged."
                    ),
                )

            attempts.append(result.text)
            record_call(
                sb, user.id, f"branch:{user.id}:{step_key}:{attempt}", step_title,
                result.text[:2000], [],
                (result.prompt_tokens, result.completion_tokens, result.total_tokens),
            )
            steps = parse_branch(result.text)
            if steps:
                break

        if not steps:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "That came back as something we will not put in a plan \u2014 "
                    "a link we have not checked, a programme we cannot verify, "
                    "or not a real breakdown. Your plan is unchanged."
                ),
            )

        sb.table("roadmap_branches").upsert(
            {
                "user_id": user.id,
                "parent_step_key": step_key,
                "steps": steps,
                "model": settings.llm_model,
            },
            on_conflict="user_id,parent_step_key",
        ).execute()
        return {"parent_step_key": step_key, "steps": steps}

    @app.post("/roadmap/spine/auto")
    def auto_generate_spine(user: CurrentUser = RequireUser) -> dict:
        """Write this student a first path, if nobody ever has.

        WHAT IT FIXES. A plan is learn -> build -> publish -> apply. The middle
        two come from a "spine", and a spine arrives only by charting a path on
        /futures. Measured 2026-10-18 across the real accounts: most students
        had no archetype and no generated spine, so spine_for("") returned
        nothing and their plan was three application steps and a cold email --
        no project at all. The product's whole claim is that it tells you what
        to build, and for a student who never pressed a button on another page
        it was not telling them anything.

        A POST, NOT A SIDE EFFECT ON GET /roadmap. A GET that spends money is
        a GET that a prefetch, a retry, a crawler or a double-mount can bill
        you for. This fires only when the plan page has looked at its own
        has_spine and found it false.

        IDEMPOTENT AND CHEAP TO REFUSE. A student who already has a spine --
        generated or authored, by having charted a path -- gets it back without
        a model call. Only a genuinely empty plan reaches the provider.

        THREE GATES, AND THE ORDER MATTERS.
          1. Does it need one at all. Costs nothing to answer.
          2. app/limits.py "auto_spine": three per student per thirty days,
             400 a day across everyone.
          3. The advisor budget -- the same wallet as the advisor and the
             manual regenerate, so there is one place the money is counted
             rather than three ceilings that each look small.

        The attempt is recorded BEFORE the call. A reply that fails to parse
        still counts, because counting only successes makes a persistently
        failing profile free and therefore infinite -- it would retry on every
        page load for a month.
        """
        from .advisor import budget_block, record_call
        from .db import get_supabase
        from .spine_generation import (
            generate_spine,
            skill_choices,
            store_spine,
        )
        from .spines import spine_for

        sb = get_supabase()

        student = (
            sb.table("students")
            .select("id, grade, audience, interests, goals, field_scores, "
                    "trait_scores, chosen_archetype, location_pref")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        student = student.data if student else None
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found.",
            )

        # Gate 1: does this student actually have nothing?
        existing = (
            sb.table("generated_spines")
            .select("project, publish, skill, skill_key")
            .eq("user_id", user.id)
            .execute()
        ).data or []
        if existing:
            row = existing[0]
            return {
                "generated": False,
                "reason": "already-written",
                "project": row["project"],
                "publish": row["publish"],
                "skill": row["skill"],
                "skillKey": row["skill_key"],
                "source": "generated",
            }
        archetype = (student.get("chosen_archetype") or "").strip()
        if archetype and spine_for(archetype):
            # They charted a path; the authored spine is theirs and writing
            # over it would be answering a question they did not ask.
            return {"generated": False, "reason": "has-authored-path"}

        # Gate 2: the per-student and global ceilings on automatic spend.
        from .limits import limit_block, record_event

        refused = limit_block(sb, "auto_spine", user.id)
        if refused:
            return {"generated": False, "reason": "rate-limited", "detail": refused}

        # Gate 3: the shared wallet.
        blocked = budget_block(sb, user.id)
        if blocked:
            return {"generated": False, "reason": "budget", "detail": blocked}

        labels, keys = skill_choices(sb)
        if not keys:
            return {"generated": False, "reason": "no-resources"}

        shelf = fetch_shelf(sb, shelf_for(student))
        ranked = score_opportunities(student, shelf, [])[:8]
        matches = [r["opportunity"] for r in ranked]

        # Counted here, before the call, for the reason in the docstring.
        record_event(sb, "auto_spine", user.id)

        from .llm import LLMUnavailable, chat as llm_chat

        try:
            spine, result = generate_spine(
                student=student,
                matches=matches,
                skill_keys=keys,
                skill_labels=labels,
                rejected=None,
                reason=(
                    "This student has not chosen a career path and may not want "
                    "to. Write them a first project from what they already have."
                ),
                llm_chat=llm_chat,
                settings=settings,
            )
        except LLMUnavailable:
            # Quiet: the student did not ask for this, so a provider outage
            # should not become an error message on their plan.
            return {"generated": False, "reason": "unavailable"}

        record_call(
            sb,
            user.id,
            f"auto-spine:{user.id}",
            "(automatic first path)",
            result.text[:2000],
            [],
            (result.prompt_tokens, result.completion_tokens, result.total_tokens),
        )

        if not spine:
            return {"generated": False, "reason": "unusable"}

        store_spine(sb, user.id, spine, settings.llm_model, archetype or None)
        return {**spine, "generated": True}

    @app.post("/roadmap/spine")
    def regenerate_spine(
        body: dict | None = None, user: CurrentUser = RequireUser
    ) -> dict:
        """Write this student a different path, because they said so.

        A student turning a plan down is the most useful signal this system
        gets — better than any trait score, because they are telling you
        directly — so the rejected plan and their reason go into the prompt and
        the model is told not to repeat it. Without that, a regenerate button is
        a dice roll that can hand back the same idea reworded.

        Refusal is still a success path. If the model picks a skill rung with no
        resources, writes a url, or returns prose that will not parse, the
        student keeps what they had and is told so plainly. See
        app/spine_generation.py.

        Charged against the advisor budget, because it is the same provider and
        the same wallet, and a regenerate button with no ceiling is the one
        control a bored student will hold down.
        """
        from .advisor import budget_block, record_call
        # Imported here like the other forty handlers in this file. It was not,
        # and `sb = get_supabase()` below raised NameError on every single call
        # from the day this endpoint shipped -- so "None of these are me" and
        # the regenerate button have never once worked. See
        # test_every_handler_can_resolve_the_names_it_calls.
        from .db import get_supabase
        from .spine_generation import SYSTEM_PROMPT, build_prompt, parse_spine

        sb = get_supabase()
        blocked = budget_block(sb, user.id)
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=blocked
            )

        prof = (
            sb.table("students")
            .select("id, grade, audience, interests, goals, field_scores, "
                    "trait_scores, chosen_archetype, location_pref")
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

        rows = (
            sb.table("learning_resources")
            .select("skill_key, skill_label")
            .not_.is_("verified_at", "null")
            .execute()
        ).data or []
        labels: dict[str, str] = {}
        keys: list[dict] = []
        for row in rows:
            key = row.get("skill_key")
            if key and key not in labels:
                labels[key] = row.get("skill_label") or ""
                keys.append({"skill_key": key, "skill_label": labels[key]})
        if not keys:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No verified learning resources to build a path from yet.",
            )

        # What they are turning down: their generated one if they have it, else
        # the authored spine for their archetype.
        from .spines import spine_for

        try:
            current = (
                sb.table("generated_spines")
                .select("project, publish, skill_key")
                .eq("user_id", user.id)
                .maybe_single()
                .execute()
            )
            rejected = current.data if current else None
        except Exception:
            rejected = None
        if not rejected:
            rejected = spine_for(student.get("chosen_archetype") or "")

        shelf = fetch_shelf(sb, shelf_for(student))
        ranked = score_opportunities(student, shelf, [])[:8]
        matches = [r["opportunity"] for r in ranked]
        reason = str((body or {}).get("reason") or "")[:300]

        prompt = build_prompt(student, matches, keys, rejected=rejected, reason=reason)
        # Through app.llm.chat for the same reasons the advisor and the verifier
        # use it: one dialect table for providers that disagree about request
        # shape, and a usage block so the call can be charged rather than
        # guessed at.
        from .llm import LLMUnavailable, chat as llm_chat

        try:
            result = llm_chat(
                base=settings.llm_api_base,
                key=settings.llm_api_key,
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                # Generous, for the reason verify_candidate documents: a
                # reasoning model emits its thinking as message content before
                # the JSON, and 700 tokens were spent entirely on "We need to
                # produce JSON with three keys..." -- the object never arrived,
                # parse_spine found no braces, and every single request refused
                # with "the path that came back did not meet the bar". The
                # spine itself is about 120 tokens.
                max_tokens=1600,
                # Low but not zero: a plan should read as written for one
                # person, which greedy decoding tends not to manage, and a
                # student pressing this twice should not get the same sentence.
                temperature=0.4,
                # The two settings that stop the preamble at the source rather
                # than paying for it. Both are dropped by providers that do not
                # know them (see app/llm.py), which is why the verifier can use
                # them against Azure and NIM alike.
                response_format={"type": "json_object"},
                reasoning_effort="none",
            )
        except LLMUnavailable:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Could not reach the model just now. Your current path is "
                    "unchanged."
                ),
            )

        record_call(
            sb,
            user.id,
            f"spine:{user.id}",
            reason or "(no reason given)",
            result.text[:2000],
            [],
            (result.prompt_tokens, result.completion_tokens, result.total_tokens),
        )

        spine = parse_spine(result.text, labels)
        if not spine:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "The path that came back did not meet the bar — it pointed at "
                    "a skill with nothing behind it, or included a link we have "
                    "not checked. Your current path is unchanged. Try again, and "
                    "it helps to say what did not fit."
                ),
            )

        sb.table("generated_spines").upsert(
            {
                "user_id": user.id,
                "project": spine["project"],
                "publish": spine["publish"],
                "skill": spine["skill"],
                "skill_key": spine["skillKey"],
                "model": settings.llm_model,
                "source_archetype": student.get("chosen_archetype") or None,
            },
            on_conflict="user_id",
        ).execute()
        return {**spine, "regenerated": True}

    @app.get("/resources/public")
    def public_resources() -> list[dict]:
        """The learning shelf, to anyone, signed in or not.

        WHAT THIS CHANGES. public.learning_resources was reachable only as
        ``/resources?skill=<rung>``, which needs an account and needs the
        student to already be on the path that names that rung. So the material
        existed and nobody could browse it: a student who wanted to learn
        something their plan had not told them to learn had no route to it, and
        a visitor could not see that it was there at all.

        A catalog of programmes with deadlines answers "what can I apply to".
        It does not answer "what do I do on a Tuesday in February when nothing
        is open", which for most students is most of the year. That is what
        this shelf is for, and it is the half that does not need an account,
        a transcript, a teacher, or a dollar.

        Every row is free, not retired, and carries the quoted sentence from
        the page that proves the free claim -- app/resources.py drops the rest
        rather than showing them on trust.
        """
        from .db import get_supabase
        from .resources import fetch_shelf

        return fetch_shelf(get_supabase())

    @app.get("/resources")
    def list_resources(
        skill: str = "",
        user: CurrentUser = RequireUser,
    ) -> list[dict]:
        """Free learning resources for one spine skill rung.

        The plan page's skill step used to be a bare instruction -- "run a
        focused 5-hour sprint on statistics -- the hypothesis tests behind the
        figure you reproduced" -- with nowhere to go. This is the where.

        Every row served is free, not retired, and carries the quoted evidence
        from the page that proves it (app/resources.py drops rows whose
        evidence is missing). No model is involved and nothing is ranked
        against the student: on a given rung there is one right set.
        """
        from .db import get_supabase
        from .resources import fetch_for_skill

        if not skill:
            return []
        return fetch_for_skill(get_supabase(), skill)

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
        mission_id: UUID,
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
            "mission_id": str(mission_id),
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

    @app.delete("/missions/{mission_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
    def uncomplete_mission(
        mission_id: UUID,
        user: CurrentUser = RequireUser,
    ) -> None:
        """Take a completion back.

        Marking a mission done was a one-way door: the only write was an upsert,
        so a student who ticked the wrong card, or ticked one and then did not
        finish it, was stuck looking at a claim about themselves they could not
        correct. An evidence record nobody can amend is not a stronger record,
        it is one people stop trusting -- and a student lying to their own
        progress bar because the UI made them is the worst version of this.

        A real delete, not a tombstone. The catalog stamps retired_at and never
        deletes because a programme's history is shared and a student's finished
        step must keep its title; this row is one person's note about themselves
        and a mistaken tick is not history worth preserving. Scoped to the
        caller's own student_id, so one student cannot un-complete another's.

        Idempotent: deleting a completion that is not there is a 204, because
        the end state the caller asked for is the end state they get.
        """
        from .db import get_supabase

        sb = get_supabase()
        (
            sb.table("mission_completions")
            .delete()
            .eq("student_id", user.id)
            .eq("mission_id", str(mission_id))
            .execute()
        )
        return None

    @app.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
    def delete_me(body: dict | None = None, user: CurrentUser = RequireUser) -> None:
        """Delete this account and everything attached to it.

        WHY THIS EXISTS. /privacy told students "email dev.thorfinn@gmail.com
        and we will delete your account", with a note that a self-serve button
        was being built. That is an honest answer at twenty users and a bad one
        at five hundred, and these are minors: asking a sixteen-year-old to
        email a stranger their name in order to withdraw their own assessment
        answers is a barrier where there should be a button.

        ONE DELETE DOES ALL OF IT. public.students.id references
        auth.users(id) on delete cascade, and twenty tables reference
        students(id) the same way, so removing the auth user removes the
        profile, the assessment scores, matches, bookmarks, dismissals,
        outcomes, missions, friendships, team-up interest, blocks, profile
        history, advisor call records and the generated spine. Nothing is
        tombstoned and nothing is kept "for analytics".

        WHAT THIS COSTS, SAID PLAINLY. public.reports references both parties
        with cascade, so a report naming this account goes with it. That is a
        real trade -- it means an account can erase a complaint about its own
        conduct -- and it is made deliberately in favour of the privacy promise
        while the moderation queue has had zero rows in it. If reports ever
        start arriving, this is the first thing to revisit, and the fix is a
        tombstone on reports rather than a weaker delete.

        Requires the student to type their own email back. Not theatre: this is
        the one irreversible action in the product, the UI puts it behind a
        typed confirmation, and the API should not be a softer door than the
        button.
        """
        from .db import get_supabase

        typed = str((body or {}).get("confirm") or "").strip().lower()
        if typed != (user.email or "").strip().lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Type the email address on this account to confirm. Nothing "
                    "has been deleted."
                ),
            )

        sb = get_supabase()
        try:
            sb.auth.admin.delete_user(user.id)
        except Exception as error:  # noqa: BLE001 — the SDK raises broadly
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Could not delete the account just now. Nothing was "
                    "removed — try again, or email dev.thorfinn@gmail.com."
                ),
            ) from error

        # Verify rather than assume. A cascade that silently did not fire would
        # leave a student believing their data is gone when it is not, which is
        # worse than an error.
        remaining = (
            sb.table("students").select("id").eq("id", user.id).execute()
        ).data or []
        if remaining:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "The account was partly removed. Email "
                    "dev.thorfinn@gmail.com and it will be finished by hand."
                ),
            )
        return None

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
        opp_id: UUID,
        user: CurrentUser = RequireUser,
    ):
        """Undo a dismissal by opportunity id."""
        from .db import get_supabase

        sb = get_supabase()
        sb.table("dismissals").delete().eq("student_id", user.id).eq("opportunity_id", str(opp_id)).execute()

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
            .select("id, name, email, grade, interests, goals, audience, location_pref, field_scores")
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

        # The audience shelf is filtered in Postgres and cached briefly
        # (app/catalog.py). This used to select("*") the whole catalog and
        # filter in Python: 106 KB per call, three calls per student session,
        # 9.8 GB/month of egress at 1,000 students against a 5 GB free tier.
        opportunities = fetch_shelf(sb, shelf_for(student))

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
            by_id = {o.get("id"): o for o in opportunities}
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

        # Semantic similarity, computed in Postgres so the 2048-float vectors
        # never cross the wire. Empty on any failure, and scoring then behaves
        # exactly as it did before embeddings existed.
        from .embeddings import semantic_scores

        results = score_opportunities(
            student,
            opportunities,
            outcome_rows,
            bookmarked_fields=bookmarked_fields,
            dismissed_ids=dismissed_ids,
            semantic=semantic_scores(sb, user.id),
        )
        # Sanitize to the shape the frontend expects: ``opportunity_field``
        # becomes ``field``, and ``description`` is dropped — it is 23% of the
        # payload, no list view renders it, and GET /opportunities/{id} serves
        # it to the one page that does. It stays in what was SCORED above,
        # because app/match.py feeds it into the TF-IDF corpus.
        for r in results:
            r["opportunity"] = public_view(r["opportunity"])

        # Persist the scored set into public.matches — upsert keyed on
        # the existing unique(student_id, opportunity_id) constraint. We
        # send only the FK columns + score + explanation so the row
        # stays valid for the matches table's check constraints.
        # Bounded to the top MATCHES_PERSISTED. This wrote every scored row —
        # 144 per call, 432,000 rows/day at 1,000 students — into a table no
        # read path touches. It is NOT deleted, because it is the denominator
        # for "opportunities served" in the impact figure; it is capped at more
        # than any surface renders.
        if results:
            rows = [
                {
                    "student_id": user.id,
                    "opportunity_id": r["score"]["opportunity_id"],
                    "score": float(r["score"]["score"]),
                    "explanation": r["score"]["explanation"],
                }
                for r in results[:MATCHES_PERSISTED]
                if r["score"]["opportunity_id"] is not None
            ]
            if rows:
                sb.table("matches").upsert(
                    rows,
                    on_conflict="student_id,opportunity_id",
                    returning="minimal",
                ).execute()

        return results

    @app.get("/catalog/public")
    def public_catalog() -> list[dict]:
        """The high-school shelf, to anyone, signed in or not.

        NOT under /public/. That prefix already has `/public/{handle}`, which
        takes any string, is registered earlier, and therefore swallowed
        `/public/catalog` as a profile lookup for the handle "catalog" —
        answering with its uniform 404. Ordering could fix it; a path that
        cannot collide fixes it permanently.

        WHY THIS EXISTS. Every catalog route was auth-gated, so a visitor who
        clicked "Opportunities" before making an account got a heading and an
        empty page -- not a locked door, just nothing. Measured on 2026-10-05:
        /opportunities, /discover and /plan each rendered zero rows signed out,
        while the API answered 401 to /match, /discover and /roadmap. Some
        people read that as broken rather than as gated, and the catalog is the
        strongest thing this project has to show.

        WHY IT IS A SEPARATE ROUTE RATHER THAN /catalog WITH OPTIONAL AUTH.
        /catalog returns dict(row) -- the whole record, including added_by,
        verified_at, retired_reason and the recurrence columns. None of that is
        secret, and all of it is curation bookkeeping that the open internet has
        no reason to receive. The fields below are an allowlist, so a column
        added to the table later is private until someone decides otherwise.

        Unranked by construction: ranking needs a student, and there isn't one.
        """
        from datetime import date

        from .db import get_supabase

        # What a visitor needs to decide whether an opportunity is worth their
        # time, and nothing about how it got here.
        PUBLIC_FIELDS = (
            "id", "title", "host", "url", "deadline", "cost", "tags",
            "audience", "grade_min", "grade_max", "type", "entry_gate",
            "entry_note", "blurb", "location_scope",
            # The locality. Added 2026-10-07 because it is the only field here
            # a model cannot produce from recall: asked to name 24 curated rows
            # it knew all 24 existed, but no model can say which of Alabama's
            # four ISEF-affiliated fairs serves Bullock County.
            "state", "location",
        )

        # CACHED, because this is served to everyone and is identical for
        # everyone. It was re-querying and re-sorting ~300 rows per request at
        # 2.8s p50 -- long enough that /opportunities rendered an empty-looking
        # page and then popped. fetch_shelf already holds exactly these rows
        # behind a 5-minute TTL for the authenticated paths; this was the only
        # catalog route not using it. It applies the audience filter and the
        # is_("retired_at", "null") filter itself, so the guarantees below are
        # unchanged -- see app/catalog.py and the test that pins both.
        from .catalog import fetch_shelf

        sb = get_supabase()
        rows = fetch_shelf(sb, "high_school")

        today = date.today().isoformat()
        out: list[dict] = []
        for row in rows:
            item = {k: row.get(k) for k in PUBLIC_FIELDS}
            item["field"] = row.get("opportunity_field")
            # Said once here rather than recomputed in every client.
            item["is_open"] = bool(row.get("deadline")) and str(row["deadline"]) >= today
            out.append(item)
        # Open ones first, soonest deadline leading; rolling and closed after.
        out.sort(key=lambda r: (not r["is_open"], r["deadline"] or "9999-12-31"))

        # Then spread the open ones across fields, because sorting by deadline
        # alone hands the top of the page to whichever feed publishes most
        # often -- which was ctftime and codeforces, 8 of the first 10 rows. See
        # app/catalog.py#interleave_by_field. Closed rows keep plain deadline
        # order; nobody is browsing those for discovery.
        from .catalog import interleave_by_field

        open_rows = [r for r in out if r["is_open"]]
        closed_rows = [r for r in out if not r["is_open"]]
        return interleave_by_field(open_rows) + closed_rows

    @app.get("/catalog")
    def catalog(user: CurrentUser = RequireUser) -> list[dict]:
        """The full opportunity bank — every catalog entry, unranked.

        Distinct from /match (personalized, scored): this is browse-all,
        for a student who wants to see everything and filter it themselves.
        Sanitized the same way (opportunity_field -> field).
        """

        from datetime import date

        from .db import get_supabase

        sb = get_supabase()
        rows = (
            sb.table("opportunities")
            .select("*")
            # Retired programs are never browsable — see
            # 20260923120000_opportunity_verification.sql for what "retired"
            # found (a program that ended in 2016, one re-scoped to middle
            # school, and two that never accepted high schoolers).
            .is_("retired_at", "null")
            .order("deadline", desc=False, nullsfirst=False)
            .execute()
        ).data or []
        catalog: list[dict] = []
        for row in rows:
            opp = dict(row)
            if "opportunity_field" in opp:
                opp["field"] = opp.pop("opportunity_field")
            catalog.append(opp)

        # Ascending-by-deadline alone opens this route on the single MOST
        # expired row in the catalog. A comment here used to excuse that with
        # "the frontend filters to open opportunities by default" — it does not.
        # frontend/app/opportunities/page.tsx reads ?status= and falls back to
        # "all", so the first card a student saw was the deadest one we had.
        #
        # Closed rows are still returned, deliberately: a sophomore needs to see
        # that RSI exists and closed in January, which is what the roadmap is
        # preparing them for. They just sort last, and the card dims them and
        # says "closed <date>".
        today_iso = date.today().isoformat()

        def browse_order(opp: dict) -> tuple[int, float, str]:
            """(bucket, within-bucket key, title) — buckets: live-dated,
            rolling, closed."""
            raw = opp.get("deadline")
            deadline = str(raw) if raw else ""
            title = str(opp.get("title") or "")
            if not deadline:
                # Rolling/undated: after live dated rows, before closed ones.
                return (1, 0.0, title)
            try:
                ordinal = float(date.fromisoformat(deadline).toordinal())
            except ValueError:
                # A malformed date is not a reason to 500 a browse request.
                return (1, 0.0, title)
            if deadline < today_iso:
                # Closed. Negated so the most recently closed sorts first: it is
                # the likeliest to reopen, and the least confusing to look at.
                return (2, -ordinal, title)
            return (0, ordinal, title)

        catalog.sort(key=browse_order)
        return catalog

    @app.get("/opportunities/{opp_id}")
    def get_opportunity(
        opp_id: UUID,
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
            .eq("id", str(opp_id))
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
        opp_id: UUID,
        user: CurrentUser = RequireUser,
    ):
        """Remove a bookmark by opportunity id."""
        from .db import get_supabase

        sb = get_supabase()
        sb.table("bookmarks").delete().eq("student_id", user.id).eq("opportunity_id", str(opp_id)).execute()

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

        opportunities = fetch_shelf(sb, shelf_for(student))

        # A DISMISSED PROGRAMME MUST NOT ORBIT.
        #
        # /match drops them (see the behavioral-signals block there); this
        # endpoint never did. While the map was its own route that was merely
        # inconsistent. Now that it renders inside /plan, a programme the
        # student explicitly marked "not for me" would circle its star inches
        # from a step list, mission board and roadmap tree that all come from
        # /match and therefore never mention it -- the one thing they said no
        # to, drawn as the brightest object on the page.
        #
        # Additive and failure-tolerant, exactly like /match: a dismissals
        # query that errors must never blank the map.
        dismissed_ids: set[str] = set()
        try:
            gone = (
                sb.table("dismissals")
                .select("opportunity_id")
                .eq("student_id", user.id)
                .execute()
            )
            dismissed_ids = {d["opportunity_id"] for d in (gone.data or [])}
        except Exception:
            pass
        if dismissed_ids:
            opportunities = [
                o for o in opportunities if o.get("id") not in dismissed_ids
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

    @app.post("/mentors/apply", status_code=status.HTTP_201_CREATED)
    def apply_to_mentor(body: dict | None = None) -> dict:
        """Someone offering to mentor. Unauthenticated, because mentors are not
        students and should not have to make a student account to volunteer.

        WRITES TO mentor_applications, NEVER TO mentors. public.mentors is
        rendered to minors with a mailto: link; nothing reachable from the open
        internet may insert there. An application waits for a person to read it.
        See 20261007140000.

        Consent is recorded as a fact with a time and the exact sentence agreed
        to, not as a boolean. 20260922090000 had to delete 25 invented mentors
        partly because nobody could tell afterwards which of them had agreed to
        anything.
        """
        data = body or {}
        name = str(data.get("name") or "").strip()[:120]
        email = str(data.get("email") or "").strip()[:200]
        bio = str(data.get("bio") or "").strip()[:2000]
        link = str(data.get("link") or "").strip()[:300] or None
        expertise = [
            str(x).strip()[:40] for x in (data.get("expertise") or []) if str(x).strip()
        ][:8]
        consented = bool(data.get("consent"))

        if not name or "@" not in email or "." not in email.split("@")[-1]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A name and a working email address are required.",
            )
        if not bio:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Please say what you work on — it is what a student matches against.",
            )
        if not consented:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "We cannot list you without your agreement to be contacted "
                    "by students."
                ),
            )

        from .db import get_supabase

        sb = get_supabase()

        # The only write on this API that the open internet can reach, so the
        # only one with no account to count against. Limited globally instead
        # (app/limits.py): a human reads every row here, and a human reading
        # ten thousand rows reads none of them.
        from .limits import limit_block, record_event

        refused = limit_block(sb, "mentor_apply", None)
        if refused:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=refused
            )
        record_event(sb, "mentor_apply", None)

        try:
            sb.table("mentor_applications").insert({
                "name": name,
                "email": email,
                "bio": bio,
                "expertise": expertise,
                "link": link,
                "consented_at": datetime.now(timezone.utc).isoformat(),
                "consent_text": CONSENT_TEXT,
                "source": "web",
            }).execute()
        except Exception:
            # Never echo a database error to an unauthenticated caller.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not record that just now. Please try again shortly.",
            )
        return {
            "received": True,
            "next": (
                "A person reads every application. Nothing is published "
                "automatically, and you will hear back before your name appears "
                "anywhere students can see."
            ),
        }

    @app.get("/mentors")
    def list_mentors(user: CurrentUser = RequireUser) -> list[dict]:
        """Ranked mentor recommendations for the signed-in student.

        Reuses the TF-IDF / cosine pipeline from app/mentors.py. Only
        mentors with a recorded ``consented_at`` are returned; the
        directory is empty until real mentors opt in, so there is nothing
        to prefilter server-side.
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

        # Only mentors with recorded written consent are ever shown: the page
        # renders a mailto, so an unconsented row means a student emails
        # someone who never agreed to hear from them. NULL consented_at is
        # invisible rather than an error, so a row can exist while outreach is
        # still in progress.
        catalog = (
            sb.table("mentors")
            .select("*")
            .not_.is_("consented_at", "null")
            .execute()
        )
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
