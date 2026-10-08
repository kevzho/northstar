"""
The comment harvester, tested without the network.

Every case here is a shape reddit actually returns or a string a person actually
typed. The scraper's whole job is turning the second into a list of links, and
the counts it produces decide what import_resources spends verdicts on -- so a
quiet off-by-one here wastes a day's budget on nothing.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from scrape_reddit_resources import (  # noqa: E402
    ASKS_FOR_MATERIAL,
    extract_links,
    merge,
    tally,
    trim_url,
    walk_comments,
)


def comment(body: str, score: int = 1, replies: list[dict] | None = None) -> dict:
    return {
        "kind": "t1",
        "data": {
            "body": body,
            "score": score,
            "replies": (
                {"kind": "Listing", "data": {"children": replies}} if replies else ""
            ),
        },
    }


def listing(children: list[dict]) -> dict:
    return {"kind": "Listing", "data": {"children": children}}


class TestTrimUrl:
    def test_sentence_punctuation_comes_off(self) -> None:
        assert trim_url("https://ocw.mit.edu/18.06.") == "https://ocw.mit.edu/18.06"
        assert trim_url("https://x.edu/a,") == "https://x.edu/a"
        assert trim_url("https://x.edu/a!?") == "https://x.edu/a"

    def test_a_balanced_paren_is_part_of_the_path(self) -> None:
        """The case that made this a function instead of an rstrip: stripping
        the paren turns a working wiki link into a 404."""
        url = "https://en.wikipedia.org/wiki/Algebra_(ring_theory)"
        assert trim_url(url) == url
        assert trim_url(url + ")") == url  # the markdown's paren, not the path's

    def test_an_unbalanced_paren_belongs_to_the_prose(self) -> None:
        assert trim_url("https://example.edu/notes.pdf)") == "https://example.edu/notes.pdf"
        assert trim_url("https://example.edu/notes.pdf),") == "https://example.edu/notes.pdf"


class TestExtractLinks:
    def test_bare_and_markdown_links_both_come_out(self) -> None:
        body = "try https://ocw.mit.edu/18.06 and [this](https://openintro.org/book/os/)"
        assert extract_links(body) == [
            "https://ocw.mit.edu/18.06",
            "https://openintro.org/book/os",
        ]

    def test_reddit_and_aggregator_links_are_not_resources(self) -> None:
        body = (
            "see https://www.reddit.com/r/learnmath/comments/a/b/ or "
            "https://bit.ly/x or https://www.amazon.com/dp/B000 or "
            "https://imgur.com/a/b"
        )
        assert extract_links(body) == []

    def test_the_same_link_twice_in_one_comment_counts_once(self) -> None:
        body = "https://openintro.org/a and also https://openintro.org/a/"
        assert extract_links(body) == ["https://openintro.org/a"]

    def test_an_empty_or_missing_body_is_not_an_error(self) -> None:
        assert extract_links("") == []
        assert extract_links(None) == []  # type: ignore[arg-type]


class TestWalkComments:
    def test_nested_replies_are_reached(self) -> None:
        tree = listing([
            comment("top https://a.edu/1", replies=[comment("nested https://b.edu/2")]),
            comment("sibling https://c.edu/3"),
        ])
        bodies = [c["body"] for c in walk_comments(tree)]
        assert bodies == ["top https://a.edu/1", "nested https://b.edu/2", "sibling https://c.edu/3"]

    def test_the_more_stub_and_empty_replies_do_not_crash_it(self) -> None:
        """`replies` is the empty STRING when there are none, and every listing
        ends with a "more" child that has no body."""
        tree = listing([comment("a https://a.edu/1"), {"kind": "more", "data": {"count": 12}}])
        assert [c["body"] for c in walk_comments(tree)] == ["a https://a.edu/1"]
        assert walk_comments("") == []
        assert walk_comments(None) == []
        assert walk_comments({}) == []


class TestTally:
    def thread(self, name: str, bodies: list[tuple[str, int]], field: str = "math") -> dict:
        return {
            "subreddit": f"r/{name}",
            "field": field,
            "permalink": f"https://www.reddit.com/r/{name}/comments/{name}/",
            "title": "best free resource?",
            "comments": [comment(body, score)["data"] for body, score in bodies],
        }

    def test_threads_are_counted_separately_from_mentions(self) -> None:
        """Ten people in one thread agreeing is ONE thread agreeing, and the
        import stage sorts on threads for exactly that reason."""
        threads = [
            self.thread("learnmath", [("https://openintro.org/a", 40), ("https://openintro.org/a", 3)]),
            self.thread("statistics", [("https://openintro.org/a", 9)]),
        ]
        found = tally(threads)
        entry = found["https://openintro.org/a"]
        assert entry["mentions"] == 3
        assert entry["thread_count"] == 2
        assert entry["upvotes"] == 52
        assert sorted(entry["subreddits"]) == ["r/learnmath", "r/statistics"]

    def test_a_reply_telling_you_not_to_use_it_is_not_a_recommendation(self) -> None:
        threads = [self.thread("learnmath", [("don't bother with https://bad.edu/x", 80)])]
        assert tally(threads) == {}

    def test_a_quote_is_kept_so_a_human_can_see_why(self) -> None:
        threads = [self.thread("learnmath", [("OpenIntro https://openintro.org/a is the gentlest", 5)])]
        entry = tally(threads)["https://openintro.org/a"]
        assert "gentlest" in entry["quotes"][0]
        assert len(entry["quotes"]) == 1


class TestMerge:
    def test_a_rerun_never_erases_a_human_verdict(self) -> None:
        """Same contract as the opportunity pool. A maintainer who marked a row
        'drop' must not have to mark it again tomorrow."""
        existing = [{
            "url": "https://openintro.org/a",
            "mentions": 2,
            "thread_count": 1,
            "threads": ["t1"],
            "subreddits": ["r/learnmath"],
            "review": "drop",
            "quotes": ["the original quote"],
        }]
        found = {"https://openintro.org/a": {
            "url": "https://openintro.org/a",
            "mentions": 5,
            "threads": ["t2"],
            "subreddits": ["r/statistics"],
            "upvotes": 10,
            "quotes": ["a new quote"],
            "thread_count": 1,
        }}
        merged = merge(existing, found)
        assert len(merged) == 1
        assert merged[0]["review"] == "drop"
        assert merged[0]["mentions"] == 5
        assert merged[0]["threads"] == ["t1", "t2"]
        assert merged[0]["thread_count"] == 2
        assert merged[0]["quotes"] == ["the original quote"]

    def test_the_most_agreed_on_candidates_sort_first(self) -> None:
        rows = merge([], {
            "https://a.edu": {"url": "https://a.edu", "mentions": 9, "threads": ["t1"], "thread_count": 1},
            "https://b.edu": {"url": "https://b.edu", "mentions": 2, "threads": ["t1", "t2", "t3"], "thread_count": 3},
        })
        assert [r["url"] for r in rows] == ["https://b.edu", "https://a.edu"]


class TestAsksForMaterial:
    def test_it_keeps_requests_for_material(self) -> None:
        for title in (
            "Best free textbook for linear algebra?",
            "Where should I start with statistics",
            "Any free courses on electronics?",
            "How did you learn organic chem",
            "Recommend lecture notes for QM",
            "free problem sets for olympiad prep",
        ):
            assert ASKS_FOR_MATERIAL.search(title), title

    def test_it_drops_threads_whose_replies_are_opinions_about_a_programme(self) -> None:
        for title in (
            "Got into SSP, is it worth the money",
            "Rejected from RSI again",
            "My internship pays $25/hr, is that normal",
        ):
            assert not ASKS_FOR_MATERIAL.search(title), title
