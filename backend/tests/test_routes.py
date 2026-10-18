"""
Route-level smoke tests using FastAPI's TestClient.

These need no Supabase credentials: they cover the public routes and assert that
every data route fails closed with 401 when the Authorization header is absent
or invalid. That is the property that matters for a public deploy — a missing
token must never reach the service-role Supabase client.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

PROTECTED_GETS = [
    "/me",
    "/match",
    "/opportunities/00000000-0000-0000-0000-000000000000",
    "/bookmarks",
    "/outcomes",
    "/pathways",
    "/mentors",
    "/teamup/settings",
    "/teamup/candidates",
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch):
    """Give the app a signing secret so rejections are 401, not the 500 the
    auth layer returns when the server itself is misconfigured."""
    from app import auth as auth_mod

    monkeypatch.setattr(auth_mod.settings, "supabase_jwt_secret", "test-jwt-secret-value")


def test_root_is_public(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"message": "Northstar API running"}


def test_health_is_public(client: TestClient) -> None:
    """Render's healthCheckPath points here (backend/render.yaml)."""
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    # Also reports which build answered, so "is the new code deployed?" is a
    # curl rather than a guess. "local" off Vercel; a short SHA on it.
    assert body["commit"]
    assert body["semantic"] in ("available", "unconfigured", "unavailable")
    assert body["advisor"] in ("available", "unconfigured", "unavailable")


def test_health_reports_unconfigured_when_the_llm_key_is_absent(
    client: TestClient,
) -> None:
    """The first version of /health checked whether app.embeddings IMPORTED,
    which is true on a host with no LLM_API_KEY — so it answered "available"
    for a feature that cannot run. Both /advisor and every profile embedding
    need that key, and production did not have it while the code and the
    frontend looked fine. A health check that goes green on the outage it was
    written to catch is worse than no health check."""
    from app import settings as settings_module

    original = settings_module.settings.llm_api_key
    try:
        settings_module.settings.llm_api_key = ""
        body = client.get("/health").json()
        assert body["status"] == "ok", "a missing key is not a liveness failure"
        assert body["semantic"] == "unconfigured"
        assert body["advisor"] == "unconfigured"
    finally:
        settings_module.settings.llm_api_key = original


@pytest.mark.parametrize("path", PROTECTED_GETS)
def test_protected_get_requires_auth(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", PROTECTED_GETS)
def test_protected_get_rejects_garbage_token(client: TestClient, path: str) -> None:
    res = client.get(path, headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


def test_protected_writes_require_auth(client: TestClient) -> None:
    assert client.post("/students", json={}).status_code == 401
    assert client.post("/bookmarks", json={"opportunity_id": "x"}).status_code == 401
    assert client.post("/outcomes", json={"opportunity_id": "x", "status": "accepted"}).status_code == 401
    assert client.delete("/bookmarks/x").status_code == 401


def test_server_without_jwt_secret_fails_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deploy that forgot SUPABASE_JWT_SECRET must refuse traffic, not serve it."""
    from app import auth as auth_mod

    monkeypatch.setattr(auth_mod.settings, "supabase_jwt_secret", "")
    res = client.get("/me", headers={"Authorization": "Bearer anything"})
    assert res.status_code == 500
    assert "SUPABASE_JWT_SECRET" in res.json()["detail"]


def test_every_route_except_public_ones_declares_auth() -> None:
    """No route may be added later without the RequireUser dependency."""
    app = create_app()
    public = {
        "/", "/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc",
        # Deliberately public: serves opt-in highlight data only, uniform
        # 404 for private/unknown handles (see app/main.py public_profile).
        "/public/{handle}",
        # Deliberately public: the high-school shelf, so a visitor who has not
        # made an account sees opportunities rather than an empty page. Every
        # catalog route was gated until 2026-10-05, and /opportunities,
        # /discover and /plan each rendered zero rows signed out while the API
        # answered 401 — which reads as broken rather than as gated.
        #
        # It is a separate route from /catalog precisely so this entry is not a
        # loophole: /catalog returns the whole row including added_by,
        # verified_at and retired_reason, while this one serves an allowlist of
        # fields. A column added to the table later stays private until someone
        # adds it there on purpose.
        #
        # Under /catalog/ and not /public/ because `/public/{handle}` matches
        # any string and is registered first, so `/public/catalog` was being
        # served as a profile lookup and 404ing.
        "/catalog/public",
        # Deliberately public: the learning shelf. Same reasoning as the
        # catalog above, and the stronger case — free material a student can
        # start tonight is the half of this product that needs no account, no
        # transcript, no teacher and no money, so putting it behind a login was
        # backwards. Allowlisted in app/resources.py SHELF_FIELDS; see
        # test_public_shelf_serves_an_allowlist_not_the_row below.
        "/resources/public",
        # Deliberately public: someone offering to mentor is not a student and
        # must not have to create a student account to volunteer. It writes to
        # mentor_applications, which no public role can read or write, and
        # never to public.mentors — see test_a_mentor_application_cannot_reach
        # _the_live_directory below.
        "/mentors/apply",
    }

    for route in app.routes:
        path = getattr(route, "path", None)
        if path is None or path in public:
            continue
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        names = {d.call.__name__ for d in dependant.dependencies if d.call is not None}
        assert "get_current_user" in names, f"{path} is not auth-gated"


def test_public_catalog_serves_an_allowlist_not_the_row() -> None:
    """The open internet gets what a student needs to judge an opportunity, and
    nothing about how it got here.

    /catalog returns dict(row), which carries added_by, verified_at,
    retired_reason and the recurrence columns. None of that is secret and all of
    it is curation bookkeeping. This route exists so that distinction is
    enforced by construction rather than by remembering.
    """
    import ast
    import inspect
    import textwrap

    from app import main as main_mod

    src = inspect.getsource(main_mod.create_app)
    start = src.index('@app.get("/catalog/public")')
    body = src[start : src.index('@app.get("/catalog")', start)]

    # Parse the allowlist rather than grep the text: this function's own
    # docstring NAMES the columns it withholds, and a substring check would
    # punish the explanation instead of the behaviour.
    tree = ast.parse(textwrap.dedent(body.split("\n", 1)[1]))
    fields: tuple[str, ...] = ()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") == "PUBLIC_FIELDS" for t in node.targets
        ):
            fields = tuple(
                el.value for el in node.value.elts if isinstance(el, ast.Constant)
            )
    assert fields, "PUBLIC_FIELDS not found; the shape must stay an allowlist"

    for withheld in ("added_by", "verified_at", "retired_at", "retired_reason",
                     "recurrence_month", "recurrence_verified_at", "description"):
        assert withheld not in fields, (
            f"the public catalog would expose {withheld}, which is curation "
            "bookkeeping, not something a visitor needs"
        )
    # And it must still carry the things that make a row actionable.
    for needed in ("title", "host", "url", "deadline", "cost"):
        assert needed in fields, f"the public catalog omits {needed}"

    # Retired rows are never browsable, and this is the high-school shelf.
    assert 'is_("retired_at", "null")' in body
    assert '"high_school"' in body


def test_locality_is_the_one_thing_recall_cannot_give_and_must_survive() -> None:
    """Measured 2026-10-05: a frontier model with no web access, asked to recall
    24 curated catalog rows, knew all 24 existed. The catalog's existence claim
    is therefore not a differentiator. Locality is: no model can say which of
    Alabama's four ISEF-affiliated fairs serves Bullock County.

    That fact was already being scraped and then dropped. scrape_sciencefairs.py
    extracts each fair's territory and passes "Bullock County, AL";
    app/verifier.py collapsed it into location_scope — an enum of three values —
    and every regional fair in the catalog read location=NULL.
    """
    import ast
    import inspect
    import textwrap

    from app import main as main_mod
    from app.verifier import parse_locality

    src = inspect.getsource(main_mod.create_app)
    start = src.index('@app.get("/catalog/public")')
    body = src[start : src.index('@app.get("/catalog")', start)]
    tree = ast.parse(textwrap.dedent(body.split("\n", 1)[1]))
    fields = ()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") == "PUBLIC_FIELDS" for t in node.targets
        ):
            fields = tuple(e.value for e in node.value.elts if isinstance(e, ast.Constant))
    for needed in ("state", "location"):
        assert needed in fields, (
            f"the public catalog drops {needed}, which is the only field in it a "
            "chat model cannot produce from memory"
        )

    # Conservative by design: a wrong state is worse than none, because it drops
    # the row out of the filter for the student it belongs to.
    assert parse_locality("Bullock County, AL") == ("Bullock County", "AL")
    assert parse_locality("Woods Hole, MA") == ("Woods Hole", "MA")
    assert parse_locality("Some Place, ZZ") == ("Some Place, ZZ", None)
    # A scope word is not a place. Three rows were written location='us' on the
    # first backfill before this was tightened.
    for scope_word in ("us", "USA", "global", "online", "Various", "international"):
        assert parse_locality(scope_word) == (None, None), f"{scope_word} became a place"


def test_a_mentor_application_cannot_reach_the_live_directory() -> None:
    """public.mentors is rendered to minors with a mailto: link.

    Until 2026-10-07 there was no write path to it at all, which is why the
    directory could never fill. Adding one had to not also add a way for a
    stranger to put their address in front of children: applications land in
    mentor_applications, which carries no RLS policy for anon or authenticated,
    and a person moves them across. The separation is the safeguard — a status
    column on the live table would not be, because nothing enforces reading it.
    """
    import inspect

    from app import main as main_mod

    src = inspect.getsource(main_mod.create_app)
    start = src.index('@app.post("/mentors/apply"')
    body = src[start : src.index('@app.get("/mentors")', start)]

    assert 'table("mentor_applications")' in body
    assert 'table("mentors")' not in body, (
        "the public application endpoint writes to the live mentor directory"
    )
    # Consent is recorded as a fact with a time and the sentence agreed to.
    # 20260922090000 deleted 25 invented mentors partly because nobody could
    # reconstruct what, if anything, any of them had agreed to.
    assert "consented_at" in body and "CONSENT_TEXT" in body
    assert 'data.get("consent")' in body, "consent must be required, not assumed"
    # A database error must not be echoed to an unauthenticated caller.
    assert "Could not record that just now" in body


def test_the_consent_sentence_is_stored_not_referenced() -> None:
    """Wording changes. An old consent has to keep meaning what it said when it
    was given, so the sentence travels with the row."""
    from app.main import CONSENT_TEXT

    assert "students may contact me directly" in CONSENT_TEXT
    assert "does not supervise" in CONSENT_TEXT
    assert "removed at any time" in CONSENT_TEXT


def test_mentor_matching_works_when_the_directory_is_not_empty() -> None:
    """The directory being empty is a data state, not a broken feature — but
    nothing was proving the ranking still worked, because every test ran
    against zero rows."""
    from app.mentors import score_mentors

    student = {"interests": ["biology", "genomics"], "goals": "work in a wet lab"}
    mentors = [
        {"id": "m1", "name": "Dr Vega", "bio": "Computational genomics.",
         "expertise": ["biology", "cs"], "consented_at": "2026-01-01"},
        {"id": "m2", "name": "Sam Okafor", "bio": "Structural engineer, bridges.",
         "expertise": ["engineering"], "consented_at": "2026-01-01"},
    ]
    ranked = score_mentors(student, mentors)
    assert len(ranked) == 2
    top = ranked[0]
    name = (top.get("mentor") or top).get("name")
    assert name == "Dr Vega", "a biology mentor must outrank an engineer here"
    assert score_mentors(student, []) == []


def test_public_shelf_serves_an_allowlist_not_the_row() -> None:
    """The open internet gets what a student needs to judge a resource, and
    nothing about how it got here.

    Same contract as the public catalog, enforced the same way. learning_resources
    carries added_by, verified_at, verified_note and the retirement columns; a
    visitor has no reason to receive curation bookkeeping, and a column added to
    the table later must stay private until someone adds it here on purpose.
    """
    from app.resources import SHELF_FIELDS

    for withheld in ("added_by", "verified_at", "verified_note", "retired_at",
                     "retired_reason", "created_at", "is_free"):
        assert withheld not in SHELF_FIELDS, (
            f"the public shelf would expose {withheld}, which is curation "
            "bookkeeping, not something a visitor needs"
        )
    # And it must still carry what makes a row usable tonight.
    for needed in ("title", "host", "url", "kind", "effort", "prerequisite",
                   "why_this_one", "free_evidence"):
        assert needed in SHELF_FIELDS, f"the public shelf omits {needed}"


def test_the_shelf_never_serves_a_free_claim_without_its_receipt() -> None:
    """is_free is a claim; free_evidence is the sentence on the page that proves
    it. This catalog exists for students with no money, so a row whose evidence
    went missing is dropped rather than shown on trust -- and that has to hold
    on the browse-all path too, not only on the per-skill one it was written for.
    """
    from app import resources

    rows = [
        {"id": "a", "title": "Has evidence", "kind": "course", "skill_label": "Stats",
         "free_evidence": "Free to audit.", "opportunity_field": "math"},
        {"id": "b", "title": "No evidence", "kind": "course", "skill_label": "Stats",
         "free_evidence": "   ", "opportunity_field": "math"},
        {"id": "c", "title": "Null evidence", "kind": "course", "skill_label": "Stats",
         "free_evidence": None, "opportunity_field": "math"},
    ]

    class _Query:
        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def is_(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def execute(self):
            return type("R", (), {"data": rows})()

    class _SB:
        def table(self, name):
            assert name == "learning_resources"
            return _Query()

    resources.clear_cache()
    served = resources.fetch_shelf(_SB())
    assert [r["title"] for r in served] == ["Has evidence"]
    resources.clear_cache()


def test_every_handler_can_resolve_the_names_it_calls() -> None:
    """No handler may reference a name nothing in its scope binds.

    THE BUG THIS EXISTS FOR. Forty-one handlers in app/main.py open with a
    local ``from .db import get_supabase``; POST /roadmap/spine called
    ``get_supabase()`` without one. Python does not notice until the line runs,
    the line only runs on a real request, and no test called it -- so the
    endpoint raised NameError on every request from the day it shipped, and
    "None of these are me" never once produced a plan for anybody.

    Nothing caught it because the failure is invisible to every other kind of
    check: it imports, it type-checks, the route is registered, the OpenAPI
    contract matches, and the handler's own tests mock the parts around it.
    This walks each handler's AST instead and asks the only question that
    mattered -- is every name it loads actually bound somewhere it can see.

    Deliberately scoped to the module's TOP LEVEL rather than ast.walk over the
    whole file: the first version of this check swept up those forty-one local
    imports, decided ``get_supabase`` was module-level, and passed cleanly on
    the broken code. It was fixed by putting the bug back and watching it fail.
    """
    import ast
    import builtins
    import inspect

    from app import main as main_mod

    def bound_names(node: ast.AST) -> set[str]:
        """Every name a function body binds, however it binds it."""
        out: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
                out.add(child.id)
            elif isinstance(child, ast.arg):
                out.add(child.arg)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                for alias in child.names:
                    out.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.add(child.name)
            elif isinstance(child, ast.ExceptHandler) and child.name:
                out.add(child.name)
            elif isinstance(child, (ast.Global, ast.Nonlocal)):
                out.update(child.names)
        return out

    def top_level_bindings(body: list) -> set[str]:
        """Only what the MODULE binds — see the docstring above."""
        out: set[str] = set()
        for stmt in body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                for alias in stmt.names:
                    out.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.add(stmt.name)
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = (
                    [stmt.target]
                    if getattr(stmt, "target", None) is not None
                    else getattr(stmt, "targets", [])
                )
                for target in targets:
                    for node in ast.walk(target):
                        if isinstance(node, ast.Name):
                            out.add(node.id)
            elif isinstance(stmt, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
                for field in ("body", "orelse", "finalbody", "handlers"):
                    out |= top_level_bindings(getattr(stmt, field, []) or [])
            elif isinstance(stmt, ast.ExceptHandler):
                if stmt.name:
                    out.add(stmt.name)
                out |= top_level_bindings(stmt.body)
        return out

    tree = ast.parse(inspect.getsource(main_mod))
    module_level = top_level_bindings(tree.body) | set(dir(builtins))

    create_app = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    handlers = [
        node for node in create_app.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    # What create_app binds for its handlers to close over — its own body, minus
    # the handlers' private locals.
    enclosing = {arg.arg for arg in create_app.args.args}
    enclosing |= {handler.name for handler in handlers}
    for stmt in create_app.body:
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            enclosing |= bound_names(stmt)

    unresolved = {
        handler.name: sorted(
            {
                node.id
                for node in ast.walk(handler)
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
            }
            - bound_names(handler)
            - enclosing
            - module_level
        )
        for handler in handlers
    }
    broken = {name: names for name, names in unresolved.items() if names}
    assert not broken, (
        "these handlers reference names nothing binds, and will raise NameError "
        f"the first time a real request reaches the line: {broken}"
    )
    # Sanity: if the walk stops finding handlers the assertion above is vacuous.
    assert len(handlers) > 30, f"only found {len(handlers)} handlers to check"


def test_a_completion_can_be_taken_back_and_only_your_own() -> None:
    """Marking a mission done used to be a one-way door.

    The only write was an upsert, so a student who ticked the wrong card — or
    ticked one and then did not finish it — was stuck looking at a claim about
    themselves they could not correct. An evidence record nobody can amend is
    not a stronger record, it is one people stop trusting.

    Two things this pins: the delete is filtered by the CALLER's student_id as
    well as the mission, so nobody can un-complete someone else's work; and it
    answers 204 whether or not a row was there, because the end state the caller
    asked for is the end state they get.
    """
    import app.db
    from app.auth import get_current_user

    calls: list[tuple] = []

    class _Query:
        def delete(self):
            calls.append(("delete",))
            return self

        def eq(self, column, value):
            calls.append(("eq", column, value))
            return self

        def execute(self):
            return type("R", (), {"data": []})()

    class _SB:
        def table(self, name):
            calls.append(("table", name))
            return _Query()

    api = create_app()

    class _User:
        id = "11111111-1111-1111-1111-111111111111"
        email = "student@example.com"

    api.dependency_overrides[get_current_user] = lambda: _User()
    original = app.db.get_supabase
    app.db.get_supabase = lambda: _SB()
    try:
        response = TestClient(api).delete(
            "/missions/22222222-2222-2222-2222-222222222222/complete"
        )
    finally:
        app.db.get_supabase = original

    assert response.status_code == 204
    assert ("table", "mission_completions") in calls
    assert ("delete",) in calls
    assert ("eq", "student_id", _User.id) in calls, (
        "the delete is not scoped to the caller — one student could un-complete "
        "another's mission"
    )
    assert ("eq", "mission_id", "22222222-2222-2222-2222-222222222222") in calls


def test_deleting_an_account_requires_typing_the_email_and_removes_everything() -> None:
    """The one irreversible action in the product.

    Two things are pinned. It refuses without a matching confirmation, because
    the API must not be a softer door than the typed confirmation in the UI.
    And it VERIFIES the cascade afterwards rather than assuming it fired — a
    student told their data is gone when it is not is worse off than one shown
    an error.
    """
    import app.db
    from app.auth import get_current_user

    deleted: list[str] = []
    remaining = {"rows": [{"id": "11111111-1111-1111-1111-111111111111"}]}

    class _Admin:
        def delete_user(self, uid):
            deleted.append(uid)
            remaining["rows"] = []

    class _Auth:
        admin = _Admin()

    class _Query:
        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def execute(self):
            return type("R", (), {"data": remaining["rows"]})()

    class _SB:
        auth = _Auth()

        def table(self, name):
            return _Query()

    api = create_app()

    class _User:
        id = "11111111-1111-1111-1111-111111111111"
        email = "Student@Example.com"

    api.dependency_overrides[get_current_user] = lambda: _User()
    original = app.db.get_supabase
    app.db.get_supabase = lambda: _SB()
    try:
        client = TestClient(api)

        # No confirmation, wrong confirmation, empty confirmation: all refused.
        for body in ({}, {"confirm": ""}, {"confirm": "someone@else.com"}):
            response = client.request("DELETE", "/me", json=body)
            assert response.status_code == 400, body
        assert deleted == [], "an account was deleted without confirmation"

        # The real thing, case-insensitively — a student typing their own
        # address in lowercase is confirming, not failing a string match.
        response = client.request("DELETE", "/me", json={"confirm": "student@example.com"})
        assert response.status_code == 204
        assert deleted == [_User.id]
    finally:
        app.db.get_supabase = original


def test_a_cascade_that_did_not_fire_is_reported_not_swallowed() -> None:
    """If the student row survives the delete, say so. Silence here means a
    student believes their assessment answers are gone when they are not."""
    import app.db
    from app.auth import get_current_user

    class _Admin:
        def delete_user(self, uid):
            return None  # claims success, removes nothing

    class _Auth:
        admin = _Admin()

    class _Query:
        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def execute(self):
            return type("R", (), {"data": [{"id": "still-here"}]})()

    class _SB:
        auth = _Auth()

        def table(self, name):
            return _Query()

    api = create_app()

    class _User:
        id = "11111111-1111-1111-1111-111111111111"
        email = "s@example.com"

    api.dependency_overrides[get_current_user] = lambda: _User()
    original = app.db.get_supabase
    app.db.get_supabase = lambda: _SB()
    try:
        response = TestClient(api).request("DELETE", "/me", json={"confirm": "s@example.com"})
    finally:
        app.db.get_supabase = original
    assert response.status_code == 500
    assert "by hand" in response.json()["detail"]
