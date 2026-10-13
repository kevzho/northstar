"""
Deciding whether a link is dead, which is not the same as deciding it failed.

WHY THIS MODULE EXISTS. /opportunities tells every visitor: "Each one has been
checked against the programme's own page, and anything that stopped holding up
was removed rather than left to pad the total." On 2026-10-12 that sentence was
false. Seven of the sixty-six open rows did not load in a real browser — four
CTF domains no longer resolved, one programme page had 404'd, one host was
timing out through Cloudflare — and nothing in the daily job had ever checked.
A claim that strong has to be enforced by something, or it is just confidence.

THE DANGEROUS MISTAKE IS THE OPPOSITE ONE. A checker that treats every failed
request as death will empty this catalog on the first bad afternoon: big
institutions bot-block aggressively (broadinstitute.org and mathworks.com both
return 403 to a headless browser while serving a human fine), rate limits look
like refusals, and a Cloudflare challenge is a 403 that means "prove you are a
person", not "this is gone". Retiring a real programme is worse than keeping a
dead link for one more day, because a student who never sees an opportunity
cannot discover it was wrongly hidden.

So: three verdicts, not two, and only one of them is actionable.

    alive          it answered
    dead           the domain no longer resolves -- the only verdict that retires
    moved          the host is there, this page is not; a human needs to re-find it
    inconclusive   something refused us; that is about us, not about the page

And death has to be repeated. A row is retired only after FAIL_STRIKES separate
runs agree, so a host that is down for an evening comes back on its own.

THE DISTINCTION THAT MATTERS MOST: A MOVED PAGE IS NOT A DEAD PROGRAMME.
The first version of this retired on any repeated failure, and its first real
run took out USA Mathematical Olympiad (maa.org reorganised its site, so
/math-competitions/ 404s), the Clark Scholar Program, the Adroit Prizes,
Harvard International Review (their server timed out twice) and the Conrad
Challenge (a TLS misconfiguration). Every one of those programmes is running.
Only the URL was stale, and deleting a real opportunity to keep a link-health
promise is a straight trade of the student's interest for ours.

So only ONE verdict retires anything: the domain itself no longer resolves.
Nobody is bot-blocking a DNS lookup and no live organisation loses its domain
by accident, so that is the one failure that genuinely means "this is gone". A
404 on a domain that still answers, a TLS error, a timeout and a 5xx are all
"moved" — kept on the shelf, flagged for a human to find the new URL.

Pure functions, no network, so every rule here is tested without one. The
fetching lives in scripts/check_links.py.
"""

from __future__ import annotations

# How many consecutive runs must agree before a row is retired. At one run a day
# this is "down for two days running", which no transient outage survives and no
# genuinely dead domain escapes for long.
FAIL_STRIKES = 2

# Refusals aimed at the CLIENT, not statements about the resource. 403 is the
# big one: it is what Akamai, Cloudflare and friends return to anything that
# does not look like a browser, and three of the first ten links tested this way
# were live pages behind exactly that.
INCONCLUSIVE_STATUS = frozenset({401, 403, 405, 406, 418, 429, 999})

# The page is gone and the server is willing to say so.
DEAD_STATUS = frozenset({404, 410})

# Network-layer failures. A name that does not resolve is the strongest signal
# available — nobody is bot-blocking a DNS lookup.
# These strings are copied from what the libraries ACTUALLY emit, not from what
# they ought to. The first version of this tuple listed "gaierror" and
# "ERR_NAME_NOT_RESOLVED" and missed every real case, because requests wraps a
# DNS failure as `ConnectionError: ... NameResolutionError ... Failed to resolve
# 'host'` and none of those substrings appear in it. Five dead domains — four
# CTFs and summerinstitutes.stanford.edu — were filed as "inconclusive" and
# would have sat on the shelf forever.
DEAD_ERRORS = (
    "NameResolutionError",
    "Failed to resolve",
    "ERR_NAME_NOT_RESOLVED",
    "NXDOMAIN",
    "gaierror",
    "nodename nor servname",
    "ERR_CONNECTION_REFUSED",
    "ConnectionRefusedError",
    "Connection refused",
)

# Could be a dead host, could be an overloaded one. Needs the strike count.
SOFT_ERRORS = (
    "ERR_CONNECTION_CLOSED",
    "ERR_CONNECTION_RESET",
    "timeout",
    "TimeoutError",
    "ReadTimeout",
    "ConnectTimeout",
    "SSLError",
    "ERR_SSL",
    "RemoteDisconnected",
)


def classify(outcome: object) -> str:
    """One request's outcome -> "alive" | "dead" | "inconclusive".

    `outcome` is an int HTTP status, or a string naming the transport failure.
    """
    if isinstance(outcome, bool):
        return "inconclusive"
    if isinstance(outcome, int):
        if 200 <= outcome < 400:
            return "alive"
        if outcome in DEAD_STATUS:
            # The host answered, so the organisation still exists -- this is a
            # page that moved, not a programme that ended. See the note above.
            return "moved"
        if outcome in INCONCLUSIVE_STATUS:
            return "inconclusive"
        if 500 <= outcome < 600:
            # Includes Cloudflare's 52x family. A server erroring is not proof
            # of anything about the programme.
            return "moved"
        return "inconclusive"

    text = str(outcome or "")
    if any(marker in text for marker in DEAD_ERRORS):
        return "dead"
    if any(marker in text for marker in SOFT_ERRORS):
        return "moved"
    return "inconclusive"


def should_retire(verdicts: list[str]) -> bool:
    """Whether a row's recent history justifies retiring it.

    `verdicts` is oldest-first. Any "alive" at all clears the record: a page that
    answered once this week is not gone, whatever happened on the other days.

    Only "dead" counts -- a domain that stopped resolving, FAIL_STRIKES runs
    running. "moved" never retires however long it persists, because the whole
    point of that verdict is that somebody has to go and look.
    """
    recent = verdicts[-FAIL_STRIKES:]
    if len(recent) < FAIL_STRIKES:
        return False
    if any(v == "alive" for v in verdicts):
        return False
    return all(v == "dead" for v in recent)


def needs_url_review(verdicts: list[str]) -> bool:
    """Whether a human should go and find this programme's new URL.

    The output nobody acts on automatically. These rows stay visible to
    students -- a stale link is a worse experience than a correct one and a far
    better one than a programme silently deleted.
    """
    recent = verdicts[-FAIL_STRIKES:]
    if len(recent) < FAIL_STRIKES:
        return False
    if any(v == "alive" for v in verdicts):
        return False
    return any(v == "moved" for v in recent)
