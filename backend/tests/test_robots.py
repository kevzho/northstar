"""
Asking robots.txt, and failing closed when it will not answer.

The scrapers that fetch other people's HTML had no check at all -- one had a
comment recording that somebody read the file by hand once. A comment does not
notice when a site adds a rule.
"""

from __future__ import annotations

import urllib.error

import pytest

from app import robots


@pytest.fixture(autouse=True)
def _clean():
    robots.reset()
    yield
    robots.reset()


def _serve(monkeypatch, body: str | Exception):
    class _Response:
        def __init__(self, text): self.text = text
        def read(self): return self.text.encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _open(request, timeout=None):
        if isinstance(body, Exception):
            raise body
        return _Response(body)

    monkeypatch.setattr(robots.urllib.request, "urlopen", _open)


UA = "northstar-catalog/1.0"


def test_an_empty_disallow_means_everything_is_allowed(monkeypatch) -> None:
    """What societyforscience.org and devpost.com actually publish."""
    _serve(monkeypatch, "User-agent: *\nDisallow:\n")
    assert robots.allowed("https://example.org/listing", UA) is True


def test_no_robots_file_means_everything_is_allowed(monkeypatch) -> None:
    """RFC 9309: a 4xx is 'nothing published', not 'stay out'."""
    _serve(monkeypatch, urllib.error.HTTPError("u", 404, "nf", None, None))
    assert robots.allowed("https://example.org/anything", UA) is True


def test_a_disallowed_path_is_refused(monkeypatch) -> None:
    _serve(monkeypatch, "User-agent: *\nDisallow: /private/\n")
    assert robots.allowed("https://example.org/private/x", UA) is False
    assert robots.allowed("https://example.org/public/x", UA) is True


def test_a_rule_aimed_at_us_is_obeyed(monkeypatch) -> None:
    """A site blocks us by our PRODUCT TOKEN, not by our full string.

    robotparser compares `useragent.split("/")[0].lower()` against the agent
    names in the file, so "northstar-catalog" is what a site would write to
    exclude us -- the version with "/1.0" on it matches nothing and silently
    falls through to the `*` group. Worth knowing before telling anyone how to
    block this crawler.
    """
    _serve(monkeypatch, "User-agent: northstar-catalog\nDisallow: /\n\nUser-agent: *\nDisallow:\n")
    assert robots.allowed("https://example.org/", UA) is False
    # And a rule for a different crawler does not apply to us.
    robots.reset()
    _serve(monkeypatch, "User-agent: BLEXBot\nDisallow: /\n\nUser-agent: *\nDisallow:\n")
    assert robots.allowed("https://example.org/", UA) is True


def test_a_server_error_fails_closed(monkeypatch) -> None:
    """THE RULE THAT MATTERS. A site that is erroring is a site having a bad
    day, and reading 'I cannot tell you' as 'yes' is why people block
    scrapers. One missed run is the cheaper mistake."""
    _serve(monkeypatch, urllib.error.HTTPError("u", 503, "busy", None, None))
    assert robots.allowed("https://example.org/", UA) is False


def test_a_network_failure_fails_closed(monkeypatch) -> None:
    _serve(monkeypatch, urllib.error.URLError("dns is down"))
    assert robots.allowed("https://example.org/", UA) is False


def test_it_asks_once_per_host(monkeypatch) -> None:
    """Eighty detail pages, one robots fetch."""
    calls = []

    class _Response:
        def read(self): return b"User-agent: *\nDisallow:\n"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _open(request, timeout=None):
        calls.append(request.full_url)
        return _Response()

    monkeypatch.setattr(robots.urllib.request, "urlopen", _open)
    for i in range(20):
        assert robots.allowed(f"https://example.org/page/{i}", UA) is True
    assert len(calls) == 1, f"fetched robots.txt {len(calls)} times"


def test_a_url_with_no_host_is_refused() -> None:
    assert robots.allowed("not-a-url", UA) is False
