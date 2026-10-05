"""
Guards on the recurring-competition feeds.

These exist because volume is the easy half. Every high-volume competition feed
that is free and needs no auth is computer science — CTFtime, Codeforces,
Devpost, Hack Club, Kaggle, all of it. app/match.py boosts a field match, so an
uncapped import makes CS crowd out every other field and a student who wrote
"biology" starts being shown capture-the-flag events. The shelf would get bigger
and worse at the same time, which is the specific failure this catalog has
already had once, with 134 of 138 AI-imported rows landing on one shelf.

So the caps are not politeness to an API. They are the product constraint, and
a test is the only thing that keeps a constant from being raised to "just get
more rows".
"""

from __future__ import annotations

import importlib
import pathlib
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

ctftime = importlib.import_module("scrape_ctftime")
codeforces = importlib.import_module("scrape_codeforces")


def test_per_run_import_caps_stay_small() -> None:
    """A single CS feed must not be able to outnumber the curated shelf.

    The high-school shelf is ~55 rows across 9 fields. One feed importing 50 a
    day would pass 55 within a day and 500 within a fortnight.
    """
    assert ctftime.MAX_IMPORT <= 30, (
        f"CTFtime cap is {ctftime.MAX_IMPORT}. Above ~30 per run, one field "
        "overwhelms the shelf — see this module's docstring before raising it."
    )
    assert codeforces.MAX_IMPORT <= 15, (
        f"Codeforces cap is {codeforces.MAX_IMPORT}. Six to eight rounds are "
        "scheduled at a time and the feed refills; a larger cap only imports "
        "contests nobody will reach."
    )


def test_ctftime_only_imports_entry_that_needs_no_permission() -> None:
    """The whole point is "an individual can dive right in".

    CTFtime's `restrictions` field is the signal: Prequalified means you must
    have qualified elsewhere, which is entry_gate='qualify' by another name, and
    Academic usually means university enrolment. Importing either would recreate
    the 15 rows that carried an application deadline for something you cannot
    apply to.
    """
    assert ctftime.OPEN_RESTRICTIONS == {"Open", "Casual"}, (
        "CTFtime restrictions widened. 'Prequalified' and 'Academic' are not "
        "things a student can just enter."
    )


def test_a_combined_division_round_is_not_discouraged() -> None:
    """A Div. 1 + Div. 2 round is enterable by Div. 2 competitors.

    Matching "Div. 1" first told a beginner to skip a contest they were welcome
    at — eligible but walled, the same error as a juniors-only programme listed
    for grades 9-12.
    """
    combined = codeforces.beginner_note("Codeforces Round (Div. 1 + Div. 2)")
    assert "combined" in combined.lower()
    assert "instead" not in combined.lower(), (
        "a combined round is being described as one to skip"
    )
    # And the plain divisions must still say the right thing.
    assert "instead" in codeforces.beginner_note("Codeforces Round 1124 (Div. 1)")
    assert "newer competitors" in codeforces.beginner_note("Codeforces Round (Div. 3)")


def test_feeds_are_registered_in_the_daily_run() -> None:
    """An adapter nobody calls is a file, not a feature. This is the mistake
    that left three semantic-matching files committed but unreachable."""
    body = (SCRIPTS / "scrape_all.py").read_text()
    for name in ("scrape_ctftime", "scrape_codeforces"):
        assert f"import {name}" in body, f"{name} is not imported by scrape_all"
    assert '("ctftime", scrape_ctftime, False)' in body
    assert '("codeforces", scrape_codeforces, False)' in body


def test_feeds_never_import_a_past_deadline() -> None:
    """Codeforces returns its entire 2,153-contest history in one response, and
    CTFtime's archive is likewise complete. Importing finished events is how the
    catalog reached 123 expired rows out of 195."""
    cf = (SCRIPTS / "scrape_codeforces.py").read_text()
    assert 'phase") == "BEFORE"' in cf, (
        "the Codeforces adapter no longer filters to upcoming contests"
    )
    ct = (SCRIPTS / "scrape_ctftime.py").read_text()
    assert '"start": int(now.timestamp())' in ct, (
        "the CTFtime adapter no longer bounds its query to future events"
    )


def test_feed_candidates_are_verified_before_the_reddit_pool() -> None:
    """A feed whose candidates are never reached imports nothing.

    The pool holds 9,000+ reddit candidates, the per-run verify cap is 60, and
    ordering inside a tier falls back to pool order, which is score-descending.
    A structured feed has no upvotes, so its entries sort last of all — the
    adapters would run daily, write candidates, and import nothing, which looks
    exactly like working.
    """
    import importlib

    vi = importlib.import_module("verify_and_import")
    assert {"ctftime", "codeforces"} <= vi.KNOWN_REAL_SOURCES, (
        "the competition feeds are not in the priority tier; their candidates "
        "will sit behind thousands of reddit links forever"
    )

    feed = {"source": "ctftime", "title": "Some CTF", "blurb": "competition",
            "url": "https://example.org/", "deadline_guess": "2026-10-01"}
    reddit = {"source": "reddit", "title": "Great internship program", "score": 9000,
              "blurb": "competition", "url": "https://example.com/"}
    assert vi.rank_key(feed) < vi.rank_key(reddit)
    assert vi.promising(feed) is True


def test_sooner_deadlines_are_verified_first() -> None:
    """A contest starting tomorrow deserves a token before one in three months."""
    import importlib

    vi = importlib.import_module("verify_and_import")
    soon = {"source": "ctftime", "title": "A", "blurb": "competition",
            "url": "https://a.org/", "deadline_guess": "2026-10-01"}
    later = {"source": "ctftime", "title": "B", "blurb": "competition",
             "url": "https://b.org/", "deadline_guess": "2026-12-01"}
    assert vi.rank_key(soon) < vi.rank_key(later)


# --- Pathways to Science: the non-CS counterweight -----------------------
#
# The docstring above says volume is the easy half and every free, auth-free
# competition feed is computer science. Measured on 2026-10-04, that had become
# the catalog's shape: of 34 high-school rows open to apply, 33 were cs and one
# was biology. Every dated candidate in the 10,568-row pool came from ctftime,
# devpost or codeforces; Reddit supplied the other 10,310 and has never supplied
# a deadline.
#
# scrape_pathways is the correction: a directory, not a forum, filtered to the
# programmes that take high schoolers. Of its first 65 candidates exactly one
# was cs. These guard the two things that would quietly break it -- the HTML
# parse, which has no classes worth anchoring to and reads inline background
# colours instead, and the rule that it never invents a deadline.

LISTING_FIXTURE = (
    "<div class='progigert' style='background: #dedede; padding: 2px;'>"
    "<h2 style='font-size:9pt;display:inline'>Woods Hole Oceanographic</h2>"
    "<i><span style='font-size:8pt;'> (Woods Hole, MA)</span></i></div>"
    "<div class='progigert' style='background: #efefef;'>"
    "<a href='programhub.aspx?sort=SUM-WHOI-Summer'>Summer Student Fellowship</a>"
    "<div style='padding-left:0px;'>Marine biology research for students."
    "<a href='programhub.aspx?sort=SUM-WHOI-Summer'> ...read more</a></div>"
    "<span style='float:right'><i>Application Deadline: 2/15/2027</i></span></div>"
    "<div class='progigert' style='background: #dedede; padding: 2px;'>"
    "<h2 style='font-size:9pt;display:inline'>Fermilab</h2>"
    "<i><span style='font-size:8pt;'> (Batavia, IL)</span></i></div>"
    "<div class='progigert' style='background: #efefef;'>"
    "<a href='programhub.aspx?sort=SUM-Fermilab-TARGET'>TARGET Program</a>"
    "<div style='padding-left:0px;'>Particle physics for high schoolers.</div></div>"
)


def test_the_listing_parse_survives_its_own_markup() -> None:
    pathways = importlib.import_module("scrape_pathways")
    rows = pathways.parse_listing(LISTING_FIXTURE)

    assert len(rows) == 2, "one record per programme block"
    first, second = rows
    assert first["title"] == "Summer Student Fellowship"
    assert first["institution"] == "Woods Hole Oceanographic"
    assert first["location"] == "Woods Hole, MA"
    assert first["slug"] == "SUM-WHOI-Summer"
    # The "...read more" anchor points at the same slug and must not become a row.
    assert "read more" not in first["blurb"]
    assert first["listing_deadline"] == "2/15/2027"
    # A programme with no printed deadline yields none, rather than a guess.
    assert second["listing_deadline"] == ""


def test_a_deadline_is_only_ever_the_printed_one() -> None:
    """The listing prints a date for a handful of rows and the detail page for
    none. Anything this scraper cannot read, it leaves for the verifier to take
    off the organiser's own page -- see northstar-docs/SHEET-SPEC.md."""
    pathways = importlib.import_module("scrape_pathways")

    assert pathways.us_date("2/15/2027") == "2027-02-15"
    for junk in ("", "Rolling", "spring 2027", "2/2027", "31/31/2027"):
        assert pathways.us_date(junk) == "", f"{junk!r} must not become a date"


def test_the_field_hint_does_not_default_everything_to_cs() -> None:
    """The whole point of this source. A wrong specific guess is worse than
    declining to guess, so anything unrecognised lands on interdisciplinary."""
    pathways = importlib.import_module("scrape_pathways")

    assert pathways.field_guess("Marine biology research fellowship") == "biology"
    assert pathways.field_guess("Particle physics at Fermilab") == "physics"
    assert pathways.field_guess("Biomedical engineering internship") == "engineering"
    assert pathways.field_guess("Summer Student Fellowship") == "interdisciplinary"
    # Ordered hints: "biomedical engineering" is engineering, not health.
    assert pathways.field_guess("biomedical engineering") == "engineering"


def test_the_scraper_prefers_the_organisers_own_url() -> None:
    """A deep link is the field that makes a row verifiable. The directory page
    is a fallback, not the goal, and social links are never the answer."""
    import inspect

    pathways = importlib.import_module("scrape_pathways")
    src = inspect.getsource(pathways.official_url)
    assert "pathwaystoscience" in src, "must exclude the directory's own domain"
    assert "facebook" in src, "must skip social links"
    assert 'split("#", 1)[0]' in src, "must drop scroll-to-text fragments"


# --- Society for Science fairs: non-CS, dated AND local ------------------
#
# The directory re-affiliates fairs each autumn, so in October most rows still
# show LAST cycle: "Entry Deadline 2/4/2026" on a fair whose 2027 date nobody has
# published yet. Of 163 fairs seen on 2026-10-04, 138 were in that state and 12
# carried a real future date.
#
# Carrying the stale one forward a year is the specific mistake this catalog has
# already made and undone -- a date no human confirmed, shown to a student as
# though someone had. So it is dropped, the fair's own site goes in the row, and
# the verifier reads the real date from the organiser.

FAIR_FIXTURE = (
    '<div class="formListFair"><div class="row" id="divFairDisplay">'
    "<div><h4>USCA01</h4><h4><b>"
    '<a href="http://www.ocsef.org/#section" target="_blank">'
    "<u>Orange County Science and Engineering Fair</u></a></b></h4>"
    "<h4>Orange County</h4></div>"
    "<div><span><strong>Competition Dates</strong></span><br />"
    "<span>3/11/2027 — 3/22/2027</span><br />"
    "<span><strong>Entry Deadline</strong></span><br /><span>2/4/2027 </span><br />"
    "<span><strong>Contact Person</strong></span><br /><span>Elizabeth Cronin</span><br />"
    "<span><b>Territory</b></span><br /><span>Orange County</span>"
    "</div></div></div>"
)


def test_a_fair_block_yields_its_own_site_and_dates() -> None:
    fairs = importlib.import_module("scrape_sciencefairs")
    [fair] = fairs.parse_fairs(FAIR_FIXTURE)

    assert fair["name"] == "Orange County Science and Engineering Fair"
    assert fair["code"] == "USCA01"
    # Its OWN site, not the directory's, and without the fragment.
    assert fair["url"] == "http://www.ocsef.org/"
    assert fair["deadline"] == "2027-02-04"
    assert fair["window"] == "3/11/2027 — 3/22/2027"
    assert fair["territory"] == "Orange County"


def test_a_contact_email_is_never_mistaken_for_the_fair_site() -> None:
    """Every block carries a mailto: link. Taking it as the url would make a row
    whose only destination is somebody's inbox."""
    fairs = importlib.import_module("scrape_sciencefairs")
    block = (
        '<div class="formListFair"><h4>USXX01</h4>'
        '<a href="mailto:info@example.org">info@example.org</a></div>'
    )
    assert fairs.parse_fairs(block) == []


def test_last_cycles_deadline_is_dropped_not_advanced() -> None:
    import inspect

    fairs = importlib.import_module("scrape_sciencefairs")
    src = inspect.getsource(fairs.main)
    assert 'fair["deadline"] >= today' in src, (
        "a past entry deadline must be dropped; the directory shows last cycle "
        "for most of the autumn"
    )
    # And it must never be reconstructed with a bumped year.
    assert "+ 1" not in src.replace("index + 1", ""), (
        "no year arithmetic: a date nobody confirmed is not a date"
    )
    assert fairs.us_date("2/4/2027") == "2027-02-04"
    for junk in ("", "TBD", "spring", "2/2027"):
        assert fairs.us_date(junk) == ""


def test_the_fair_import_stays_capped() -> None:
    """~400 affiliated fairs exist. Arriving at once they would do to
    `interdisciplinary` what an uncapped CTFtime does to `cs`."""
    fairs = importlib.import_module("scrape_sciencefairs")
    assert fairs.MAX_IMPORT <= 200, (
        f"MAX_IMPORT is {fairs.MAX_IMPORT}; the cap is the product constraint, "
        "not politeness to the server"
    )


def test_every_structured_scraper_is_trusted_by_the_verifier() -> None:
    """The failure this prevents is silent, which is why it needs a test.

    verify_and_import.rank_key explains it against ctftime and codeforces: a
    structured feed writes score 0, the generic tier falls back to pool order,
    pool order is score-descending, and the pool holds ten thousand upvoted
    reddit threads. A source missing from KNOWN_REAL_SOURCES therefore sorts
    below all of them, is never reached by the per-run budget, and the daily job
    stays green while importing nothing from it.

    It happened once when ctftime and codeforces were added, and again on
    2026-10-04 when pathways and sciencefairs were. So the rule is now checked
    rather than remembered: whatever source string a scraper writes into the
    pool must be a source the verifier trusts.
    """
    import re

    verify = importlib.import_module("verify_and_import")

    emitted: dict[str, str] = {}
    for script in sorted(SCRIPTS.glob("scrape_*.py")):
        # scrape_reddit emits a subreddit name per candidate ("r/premed"), which
        # is the open-ended tier by design -- a thread is not a listing.
        if script.name in {"scrape_reddit.py", "scrape_all.py"}:
            continue
        for match in re.finditer(r'"source":\s*"([a-z0-9_.-]+)"', script.read_text()):
            emitted[match.group(1)] = script.name

    assert emitted, "no structured scrapers found; has the naming changed?"
    missing = {src: where for src, where in emitted.items()
               if src not in verify.KNOWN_REAL_SOURCES}
    assert not missing, (
        f"these scrapers write a source the verifier does not trust: {missing}. "
        "Their candidates will sort below every reddit thread in the pool and "
        "never be verified, while the daily run reports success."
    )


def test_a_location_hint_never_reaches_the_enum_raw() -> None:
    """Postgres answers 22P02 and the row is simply lost.

    public.location_scope has three values. Candidates carry free text: "Mono
    County, CA" from the fair directory, "Woods Hole, MA" from Pathways,
    "onsite" from CTFtime since the day that feed was written. On 2026-10-04,
    29 of 60 verdicts in one run were spent on rows that could never be
    inserted, and no onsite CTF had ever imported. The verdict cost was paid and
    the failure was invisible, which is the expensive combination.
    """
    import sys as _s
    _s.path.insert(0, str(SCRIPTS.parent))
    from app.verifier import SCOPES, clean_date, normalise_scope

    for hint in ("Mono County, CA", "onsite", "Woods Hole, MA", "", None,
                 "united states", "Orange County", "global", "international"):
        assert normalise_scope(hint) in SCOPES, f"{hint!r} escaped the enum"

    assert normalise_scope("global") == "global"
    assert normalise_scope("International (online)") == "international"
    assert normalise_scope("Searcy County, AR") == "us"


def test_an_absent_deadline_is_null_not_empty_string() -> None:
    """"" is honest in JSON and invalid in a date column (22007). NULL is what
    the rest of the product already reads as "Rolling deadline"."""
    import sys as _s
    _s.path.insert(0, str(SCRIPTS.parent))
    from app.verifier import clean_date

    assert clean_date("") is None
    assert clean_date("   ") is None
    assert clean_date(None) is None
    assert clean_date("2027-02-04") == "2027-02-04"


def test_a_fair_without_an_upcoming_date_is_not_imported() -> None:
    """Tried the other way on 2026-10-04, and it made the shelf worse.

    89 fair rows landed and 3 of them had a date. `interdisciplinary` went to
    54% of the high-school shelf. Every one of the 89 contains the words
    "science" and "fair" and 64 contain "engineering", so to the matcher they
    are one row repeated — and location_scope is us/international/global, with
    no state granularity, so a student in Alabama is shown all 89 rather than
    the four that are theirs.

    The 94 undated rows were retired and the rule moved into the scraper. This
    costs nothing: the directory republishes dates each autumn, and a fair comes
    back on the first run after it posts one, with a date a student can act on.
    """
    import inspect

    fairs = importlib.import_module("scrape_sciencefairs")
    src = inspect.getsource(fairs.main)
    assert "if not upcoming:" in src and "continue" in src, (
        "a fair with no confirmed upcoming deadline must be skipped, not stored"
    )
    # And the skip must be driven by a real comparison against today, so it
    # cannot be satisfied by storing a stale date and calling it upcoming.
    assert 'fair["deadline"] >= today' in src


def test_the_pathways_detail_fetch_happens_once_per_programme() -> None:
    """Politeness, and it is measurable.

    Without a cache this scraper fetched all ~80 detail pages on every daily run
    to rediscover addresses it already had — 80 requests a day at a small
    nonprofit directory to learn nothing. The listing changes a few times a
    year; the mapping from a slug to the organiser's own site does not change at
    all. Measured after the fix: 66 fetched on the first run, 0 on the second.

    The cache file is tracked rather than ignored, because it is the record of
    what has already been asked, and a fresh clone that lost it would start the
    80 requests over.
    """
    import inspect

    pathways = importlib.import_module("scrape_pathways")
    src = inspect.getsource(pathways.main)
    assert "slug in cache" in src, (
        "every run re-fetches every detail page; cache the slug -> url mapping"
    )
    assert "URL_CACHE.write_text" in src, "a cache that is never written is not a cache"
    # The sleep must sit with the fetch, not outside it, or a fully cached run
    # still pauses 80 times for no reason.
    fetch_block = src[src.index("slug in cache"):]
    assert "time.sleep" in fetch_block.split("else:")[1][:400], (
        "the delay belongs to the fetch; a cached run should not sleep"
    )
