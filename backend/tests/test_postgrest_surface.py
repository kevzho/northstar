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

MAIN = pathlib.Path(__file__).resolve().parents[1] / "app" / "main.py"


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


def test_route_query_chains_use_real_postgrest_methods() -> None:
    valid = _valid_builder_methods()
    called = _collect_chain_methods(ast.parse(MAIN.read_text()))
    assert called, "AST walk found no sb.table(...) chains — the guard is broken"

    unknown = sorted(called - valid)
    assert not unknown, (
        f"app/main.py calls PostgREST methods that do not exist: {unknown}. "
        f"These raise AttributeError at request time, not import time."
    )


@pytest.mark.parametrize("name", ["maybe_single", "single", "select", "upsert", "execute"])
def test_expected_methods_are_in_the_valid_set(name: str) -> None:
    """Sanity-check the guard itself against known-good method names."""
    assert name in _valid_builder_methods()


def test_typo_would_be_rejected() -> None:
    """The exact bug this file exists for must not be in the valid set."""
    assert "maybesingle" not in _valid_builder_methods()
