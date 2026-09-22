"""
Guard: every PostgREST builder method the routes call must actually exist.

This exists because the whole API was dead on arrival for a subtle reason:
``backend/app/main.py`` called ``.maybesingle()`` on five query chains. The real
supabase-py method is ``.maybe_single()``. Python only discovers that at call
time, so ``py_compile`` passed, imports passed, the server booted, and then every
route that read a student profile (/me, /match, /pathways, /mentors,
/opportunities/{id}) raised AttributeError -> HTTP 500 on the first request.

Rather than test that one name, this walks the AST of app/main.py, collects every
method called on a chain rooted at ``sb.table(...)``, and asserts each name is a
real attribute of the installed postgrest request builders. Any future typo in a
query chain fails here instead of in front of a judge.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

APP = pathlib.Path(__file__).resolve().parents[1] / "app"

# Every module that builds sb.table(...) chains. Adding one here is the
# whole cost of keeping it guarded; forgetting to is how the next
# .maybesingle() reaches production.
QUERY_MODULES = [APP / "main.py", APP / "advisor.py"]


def _valid_builder_methods() -> set[str]:
    """Union of public attributes across the installed sync postgrest builders."""
    from postgrest._sync.request_builder import (
        SyncFilterRequestBuilder,
        SyncQueryRequestBuilder,
        SyncRequestBuilder,
        SyncSelectRequestBuilder,
    )

    valid: set[str] = set()
    for cls in (
        SyncRequestBuilder,
        SyncQueryRequestBuilder,
        SyncFilterRequestBuilder,
        SyncSelectRequestBuilder,
    ):
        valid |= {name for name in dir(cls) if not name.startswith("_")}
    return valid


def _collect_chain_methods(tree: ast.AST) -> set[str]:
    """Return method names invoked on chains that start at ``sb.table(...)``."""
    found: set[str] = set()

    def roots_at_sb_table(node: ast.AST) -> bool:
        """Walk down a call/attribute chain looking for ``sb.table(...)``."""
        current = node
        while True:
            if isinstance(current, ast.Call):
                current = current.func
            elif isinstance(current, ast.Attribute):
                if current.attr == "table" and isinstance(current.value, ast.Name):
                    return True
                current = current.value
            else:
                return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr == "table":
            continue
        if roots_at_sb_table(func.value):
            found.add(func.attr)

    return found


@pytest.mark.parametrize("module", QUERY_MODULES, ids=lambda p: p.name)
def test_route_query_chains_use_real_postgrest_methods(module: pathlib.Path) -> None:
    valid = _valid_builder_methods()
    called = _collect_chain_methods(ast.parse(module.read_text()))
    assert called, (
        f"AST walk found no sb.table(...) chains in {module.name} — either the "
        f"guard is broken or the module no longer belongs in QUERY_MODULES"
    )

    unknown = sorted(called - valid)
    assert not unknown, (
        f"app/{module.name} calls PostgREST methods that do not exist: "
        f"{unknown}. These raise AttributeError at request time, not import time."
    )


@pytest.mark.parametrize("name", ["maybe_single", "single", "select", "upsert", "execute"])
def test_expected_methods_are_in_the_valid_set(name: str) -> None:
    """Sanity-check the guard itself against known-good method names."""
    assert name in _valid_builder_methods()


def test_typo_would_be_rejected() -> None:
    """The exact bug this file exists for must not be in the valid set."""
    assert "maybesingle" not in _valid_builder_methods()


# ---------------------------------------------------------------------------
# Filter-injection guard.
#
# postgrest-py does not escape filter *values*. Reading the installed client:
# `filter(column, op, criteria)` sanitizes only the column; `or_(filters)`
# sanitizes only `reference_table` and interpolates `filters` verbatim; and
# `in_()`'s sanitize_param merely wraps a value containing one of ",:()" in
# double quotes without escaping a quote already inside it.
#
# So an f-string passed to `.or_()` is string-built query language. That is
# how GET /friends/{student_id}/compare came to interpolate an unvalidated
# path parameter into the filter that WAS its authorization gate.
#
# The rule: an f-string may reach `.or_()` only when every value it
# interpolates is provably a UUID. Adding a name here means asserting that,
# and should be as annoying as it sounds.
# ---------------------------------------------------------------------------

PROVABLY_UUID = {
    # auth.py parses the JWT `sub` claim with UUID() before building
    # CurrentUser, so this cannot carry a filter metacharacter.
    "user.id",
    # social.blocked_ids coerces its argument through UUID() on the line above.
    "sid",
}


def _expr(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - unparse is available on 3.9+
        return "<unparseable>"


def _or_call_args() -> list[tuple[str, int, ast.AST]]:
    """Every first argument passed to a `.or_(...)` call, with its location."""
    found = []
    for path in QUERY_MODULES + [APP / "social.py"]:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "or_"
                and node.args
            ):
                found.append((path.name, node.lineno, node.args[0]))
    return found


def test_or_filters_only_interpolate_provable_uuids() -> None:
    offenders = []
    for filename, lineno, arg in _or_call_args():
        if isinstance(arg, ast.Constant):
            continue  # a literal builds no query language from data
        if not isinstance(arg, ast.JoinedStr):
            offenders.append(
                f"{filename}:{lineno}: .or_() argument is {type(arg).__name__}, "
                f"not a literal or f-string: {_expr(arg)}"
            )
            continue
        for part in arg.values:
            if isinstance(part, ast.FormattedValue):
                expr = _expr(part.value)
                if expr not in PROVABLY_UUID:
                    offenders.append(
                        f"{filename}:{lineno}: .or_() interpolates {expr!r}, "
                        "which is not a provably-UUID value"
                    )

    assert not offenders, (
        "PostgREST filter injection risk — postgrest-py passes .or_() its "
        "argument verbatim. Validate the value as a UUID at the route "
        "boundary (annotate path params `UUID`, or use params.uuid_field for "
        "body fields), then either add it to PROVABLY_UUID or express the "
        "filter structurally with params.either_direction:\n  "
        + "\n  ".join(offenders)
    )


def test_no_route_takes_a_bare_str_id_path_param() -> None:
    """Path parameters named *_id must be typed UUID, not str.

    A `str` path param reaches `.eq()` unescaped. FastAPI validates a `UUID`
    annotation for free and returns 422, so this costs nothing to hold.
    """
    tree = ast.parse((APP / "main.py").read_text())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for a in node.args.args:
            if not a.arg.endswith("_id") or a.annotation is None:
                continue
            if _expr(a.annotation) == "str":
                offenders.append(f"main.py:{a.lineno}: {node.name}({a.arg}: str)")
    assert not offenders, (
        "id path parameters must be annotated UUID so FastAPI rejects "
        "anything else before it reaches a PostgREST filter:\n  "
        + "\n  ".join(offenders)
    )
