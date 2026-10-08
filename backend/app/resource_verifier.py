"""
Guardrails for importing a free learning resource.

Separate from app/verifier.py because the two are checking different claims.
An opportunity is real or not; a resource is FREE or not, and that is the
claim this catalog exists to make. public.learning_resources is read by
students with no money, so getting it wrong is not a quality problem, it is
the specific harm the shelf was built to prevent: a list of free resources
where three are paywalled is worse for them than a list of forty where none
are, because now they have to check every one themselves.

THE ONE GUARD THAT MATTERS. free_evidence must appear VERBATIM in the page
that was fetched. Not "the model said it is free" -- a model will say that
about anything, and said it about a $49/month platform in testing. Not "the
model quoted something plausible" -- a quote it composed itself is a
hallucination with a citation shape. The quoted sentence is checked against
the bytes that came back from the URL, and a quote that is not in them drops
the row. That turns the receipt on every shelf row from a claim into a
check, and it is why `contains_quote` is normalised rather than exact: real
pages carry entities, soft hyphens and line wraps where their rendered text
has spaces.

Pure functions only, no network and no LLM, so every rule here is tested
without either. scripts/import_resources.py does the fetching.
"""

from __future__ import annotations

import html
import re
import unicodedata
from urllib.parse import urlparse

# public.learning_resources.kind is a check constraint, not an enum, so a bad
# value is a 400 from postgrest at insert time rather than anything caught
# earlier. Mirrored here (20260923150000_learning_resources.sql).
KINDS = frozenset({
    "course", "textbook", "pdf", "interactive",
    "problem-set", "video-series", "documentation",
})

# public.opportunity_field. A resource with no valid field is unreachable on the
# hub's subject filter, which is the only way most students will find it.
FIELDS = frozenset({
    "cs", "biology", "math", "physics", "engineering",
    "interdisciplinary", "design", "business", "humanities", "health",
})

# High enough that an unclear page is left for a human. The cost of a wrong
# "free" here is a student clicking into a paywall; the cost of a false negative
# is one row we did not add.
CONFIDENCE_FLOOR = 0.85

# A quote shorter than this proves nothing -- "Free" appears on almost every
# commercial page, usually followed by "trial".
MIN_EVIDENCE_CHARS = 18
MAX_EVIDENCE_CHARS = 300

# Hosts that cannot themselves be the resource: aggregators, link shorteners,
# and the places a reddit comment links when it is pointing at a conversation
# rather than at material.
NOT_A_RESOURCE_HOST = (
    "reddit.com", "redd.it", "imgur.com", "x.com", "twitter.com",
    "facebook.com", "instagram.com", "tiktok.com", "discord.gg",
    "discord.com", "bit.ly", "tinyurl.com", "t.co", "linktr.ee",
    "forms.gle", "goo.gl", "amazon.com", "amzn.to", "ebay.com",
    "patreon.com", "gofundme.com", "quora.com", "medium.com",
)

# Wording that means "free for now" or "free if you pay for the rest". A page
# whose only free language is one of these is not a free resource, and the model
# is not asked to make that judgement -- it is made here, on the quote.
#
# THE SAMPLE-OF-THE-PAID-THING FAMILY is the one that got through. On the first
# real run this module accepted roadmap.sh at 0.9 confidence quoting "Every pack
# starts with free lessons" -- which is a sentence about where the paywall is,
# written by a site that sells courses, and the earlier pattern only knew the
# phrasing "first lesson free". Anything saying SOME of it is free is saying the
# rest is not, and that is a price. Written broadly for that reason.
NOT_ACTUALLY_FREE = re.compile(
    # Time-limited.
    r"free\s+(trial|for\s+\d+\s+days?|for\s+a\s+(month|week|year)|tier|plan\s+available)"
    r"|start\s+(your\s+)?free\s+trial"
    r"|\d+[- ]day\s+free"
    r"|free\s+with\s+(a\s+)?(subscription|membership|purchase)"
    # A sample of the paid thing: "first lesson free", "free preview", "starts
    # with free lessons", "free to start".
    r"|first\s+\w+\s+(is\s+)?free"
    r"|free\s+(sample|preview|demo)"
    r"|(start|begin)s?\s+(with\s+)?(\w+\s+){0,2}free"
    r"|free\s+to\s+(start|try|begin|get\s+started)"
    # Quantified: if SOME of it is free, the rest is not. Proximity rather than
    # exact phrasing, because "Some of our lessons are free" and "a few chapters
    # are free to read" are the same sentence with different nouns in it.
    r"|\b(some|a\s+few|several|certain|most|parts?)\b.{0,30}?\bfree\b"
    # Free next to the price of not being free, in either order.
    r"|\bfree\b.{0,40}?\b(upgrade|premium|pro\s+plan|paid|subscription|membership|paywall)\b"
    r"|\b(upgrade|premium|pro\s+plan|paid\s+plan|subscription)\b.{0,40}?\bfree\b",
    re.I,
)


def normalise(text: str) -> str:
    """Collapse a page or a quote to comparable text.

    Entities decoded, unicode folded to its compatibility form (so a page's
    curly quote matches a model's straight one), dashes unified, whitespace
    collapsed, lowercased. Everything here exists because a real page failed
    an exact comparison for a reason that had nothing to do with honesty.
    """
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("­", "")  # soft hyphen
    text = re.sub(r"[‐-―−]", "-", text)  # dashes
    text = re.sub(r"[‘’‛′]", "'", text)
    text = re.sub(r"[“”‟″]", '"', text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def contains_quote(page: str, quote: str) -> bool:
    """Whether the page really says that.

    The whole receipt rests on this. Normalised on both sides for the reasons
    in `normalise`, and nothing weaker -- no fuzzy ratio, no "most of the words
    appear". A model that paraphrases has not quoted, and a paraphrase is
    exactly what an invented receipt looks like.
    """
    quote = (quote or "").strip().strip('"“”')
    if len(quote) < MIN_EVIDENCE_CHARS:
        return False
    return normalise(quote) in normalise(page)


def host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def is_resource_host(url: str) -> bool:
    host = host_of(url)
    if not host:
        return False
    if not urlparse(url).scheme in {"http", "https"}:
        return False
    return not any(
        host == bad or host.endswith("." + bad) for bad in NOT_A_RESOURCE_HOST
    )


def slug(value: object, *, limit: int = 64) -> str:
    """A skill_key the hub can group on and a URL can carry."""
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    return text.strip("-")[:limit]


def decide_resource(candidate: dict, verdict: dict, page: str) -> dict | None:
    """Turn a verdict about a fetched page into a learning_resources row, or None.

    `candidate` is what the scraper found (url, and the mention counts that made
    it worth a look). `verdict` is the model's reading of the page. `page` is the
    text that was actually fetched -- the only thing here that cannot be talked
    into saying something.
    """
    url = str(candidate.get("url") or "").strip()
    if not is_resource_host(url):
        return None

    if not verdict.get("is_free"):
        return None
    if not verdict.get("teaches_a_skill"):
        return None
    # A graduate seminar is free and useless to a 15-year-old with no calculus.
    if verdict.get("high_school_reachable") is False:
        return None

    try:
        confidence = float(verdict.get("confidence", 0))
    except (TypeError, ValueError):
        return None
    if confidence < CONFIDENCE_FLOOR:
        return None

    evidence = str(verdict.get("free_evidence") or "").strip().strip('"“”')
    if len(evidence) > MAX_EVIDENCE_CHARS:
        return None
    if not contains_quote(page, evidence):
        # The receipt is not on the page. Either the model wrote it, or the page
        # changed between fetch and verdict. Both mean we cannot vouch for it.
        return None
    if NOT_ACTUALLY_FREE.search(evidence):
        # "Start your free trial" is a price, not an absence of one.
        return None

    kind = str(verdict.get("kind") or "").strip().lower()
    if kind not in KINDS:
        return None

    field = str(verdict.get("field") or "").strip().lower()
    if field not in FIELDS:
        return None

    skill_key = slug(verdict.get("skill_key"))
    skill_label = str(verdict.get("skill_label") or "").strip()[:200]
    if not skill_key or not skill_label:
        return None

    title = str(verdict.get("title") or "").strip()[:200]
    if not title:
        return None

    why = str(verdict.get("why_this_one") or "").strip()[:400]
    if not why:
        return None

    return {
        "title": title,
        "host": (str(verdict.get("host") or "").strip() or host_of(url))[:200],
        "url": url,
        "kind": kind,
        "skill_key": skill_key,
        "skill_label": skill_label,
        "opportunity_field": field,
        "effort": (str(verdict.get("effort") or "").strip() or "a weekend")[:80],
        "prerequisite": (str(verdict.get("prerequisite") or "").strip() or "none")[:200],
        "why_this_one": why,
        "is_free": True,
        "free_evidence": evidence,
        "added_by": "ai",
    }
