"""
Ask robots.txt before fetching a page, rather than asking a person once.

WHAT THIS REPLACES. Two scrapers fetch HTML from sites that are not ours
(pathwaystoscience.org and findafair.societyforscience.org). Neither checked
robots.txt. One of them carried a docstring saying the site "carries no
Disallow rules", which was true when somebody read it by hand and is a comment,
not a check -- if either site adds a rule tomorrow, a comment keeps scraping
through it. Verified 2026-10-24: both are still permissive, so nothing was
being violated. That is compliance by luck, and luck is not a policy.

FAIL-CLOSED ON DOUBT, per RFC 9309:

    2xx                  parse it and obey it
    4xx (incl. 404)      no rules published, everything allowed
    5xx, timeout, DNS    treat as disallowed for now

The last line is the one that matters. A site that is erroring is a site having
a bad day, and a scraper that reads "I cannot tell you" as "yes" is the reason
people block scrapers. The cost of being wrong in that direction is one missed
run; the cost of the other direction is being the traffic somebody blocks.

Cached per host for the process, so a run that fetches eighty detail pages asks
once rather than eighty-one times.

HOW A SITE BLOCKS US. By the product token, not the full string: robotparser
compares ``useragent.split("/")[0].lower()`` against the names in the file, so
``User-agent: northstar-catalog`` excludes us and ``northstar-catalog/1.0``
matches nothing and falls through to ``*``. Worth knowing before telling anyone
how to opt out.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

#: host -> parser, or None when the host said "no rules".
_cache: dict[str, RobotFileParser | None] = {}
#: Hosts whose robots.txt could not be read. Disallowed until the process ends.
_unreachable: set[str] = set()

TIMEOUT_S = 10


def _load(host: str, scheme: str, user_agent: str) -> RobotFileParser | None:
    url = f"{scheme}://{host}/robots.txt"
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        if 400 <= error.code < 500:
            return None  # nothing published: everything is allowed
        _unreachable.add(host)
        return None
    except Exception:
        _unreachable.add(host)
        return None

    parser = RobotFileParser()
    parser.parse(body.splitlines())
    return parser


def allowed(url: str, user_agent: str) -> bool:
    """Whether robots.txt permits fetching this url with this User-Agent."""
    parsed = urlparse(url)
    host, scheme = parsed.netloc, parsed.scheme or "https"
    if not host:
        return False
    if host not in _cache and host not in _unreachable:
        _cache[host] = _load(host, scheme, user_agent)
    if host in _unreachable:
        return False
    parser = _cache.get(host)
    if parser is None:
        return True
    return parser.can_fetch(user_agent, url)


def reset() -> None:
    """Forget what we learned. For tests, and for a long-lived process."""
    _cache.clear()
    _unreachable.clear()
