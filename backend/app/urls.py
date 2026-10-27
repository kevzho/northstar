"""
One spelling per address.

A URL that differs only by a trailing slash or a capital letter is the same
page, and treating the two as different rows put the same programme on the
shelf twice. Measured 2026-10-07: seven duplicate pairs on the high-school
shelf, including three regional science fairs a student would have seen listed
twice in the same filter.

Two separate mechanisms both missed them:

  - The scrapers dedupe their candidate pool on the exact url string, so
    "https://www.mathcamp.org" and "https://www.mathcamp.org/" were two
    candidates.
  - public.opportunities carries UNIQUE(title, host) (migration_005), and the
    host strings derived from those two urls differed, so both rows inserted.

Deliberately conservative. Only differences that cannot change which page is
served are normalised away: scheme case, host case, a trailing slash, a
default port, and tracking parameters. A path's case IS preserved, because
plenty of servers treat /Fellows and /fellows as different documents and
collapsing them would merge two real pages into one row.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

# Parameters that identify a referrer, never a document.
TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "igshid")


def canonical_url(raw: object) -> str:
    """A comparable form of a URL, for dedupe only.

    NOT for display or for fetching, the original string is what should be
    shown to a student and what should be requested, because this drops
    information a server may care about.
    """
    text = str(raw or "").strip()
    if not text:
        return ""
    if "://" not in text:
        text = f"https://{text}"
    try:
        parts = urlsplit(text)
    except ValueError:
        return text.lower()

    scheme = (parts.scheme or "https").lower()
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    # A default port says nothing about which page is served.
    port = parts.port
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        host = f"{host}:{port}"

    # Path case is PRESERVED. /Fellows and /fellows are different documents on
    # plenty of servers, and merging them would lose a real row.
    path = parts.path.rstrip("/")

    query = "&".join(
        sorted(
            part
            for part in parts.query.split("&")
            if part and not part.lower().startswith(TRACKING_PREFIXES)
        )
    )
    # A fragment is a position in a document, not a document.
    return urlunsplit((scheme, host, path, query, ""))
