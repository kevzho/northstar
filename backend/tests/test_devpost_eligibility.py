"""
Guards on how a Devpost hackathon picks its audience shelf.

The shelf is the whole decision about who sees a row, and both mistakes cost
something: a high schooler sent to an 18+ hackathon is rejected, and one the
shelf hides is a hackathon they never hear about. The page's own "Who can
participate" list is the evidence, so these tests pin the reading of it. The
lines are copied verbatim from live pages fetched on 2026-11-15.
"""

from __future__ import annotations

import importlib
import pathlib
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

devpost = importlib.import_module("scrape_devpost")

# Trimmed from arbiter-hacks-v1.devpost.com, markup kept as Devpost serves it.
PAGE = """
<div class="requirements-col">
    <h6>Who can participate</h6>
    <ul id="eligibility-list" class="no-bullet">
<li>Ages 13+ only</li>
<li>Students only</li>
<li>Companies/professional organizations excluded from participation</li>
<li>
    All countries/territories, excluding
      <span data-tooltip title="Brazil, Cuba" class="has-tip nowrap">standard exceptions <i class="fas fa-info-circle"></i></span>
</li>
</ul>
</div>
"""


def test_parse_reads_each_line_as_plain_text() -> None:
    assert devpost.parse_eligibility(PAGE) == [
        "Ages 13+ only",
        "Students only",
        "Companies/professional organizations excluded from participation",
        "All countries/territories, excluding standard exceptions",
    ]


def test_parse_page_without_list_is_empty() -> None:
    assert devpost.parse_eligibility("<html><body>No rules here</body></html>") == []
    assert devpost.parse_eligibility("") == []


def test_open_to_thirteen_year_olds_is_high_school() -> None:
    assert devpost.audience_from_eligibility(devpost.parse_eligibility(PAGE)) == "high_school"
    assert devpost.audience_from_eligibility(
        ["Ages 13 to 18 only", "Students only"]
    ) == "high_school"
    assert devpost.audience_from_eligibility(
        ["Ages 13+ only", "Students only", "US only"]
    ) == "high_school"


def test_adult_only_is_college() -> None:
    assert devpost.audience_from_eligibility(
        ["Above legal age of majority in country of residence", "Specific countries/territories excluded"]
    ) == "college"
    assert devpost.audience_from_eligibility(["Ages 18+ only"]) == "college"
    assert devpost.audience_from_eligibility(["Ages 17+ only", "Students only"]) == "college"


def test_minimum_age_above_ninth_grade_is_college() -> None:
    assert devpost.audience_from_eligibility(["Ages 16+ only"]) == "college"


def test_unrecognised_restriction_keeps_it_off_high_school() -> None:
    """An age that admits teens does not outweigh a rule we cannot judge."""
    assert devpost.audience_from_eligibility(
        ["Ages 13+ only", "Georgia Tech Students Only"]
    ) == "college"
    assert devpost.audience_from_eligibility(
        ["Ages 13+ only", "College students only"]
    ) == "college"


def test_explicit_high_school_line_is_high_school() -> None:
    assert devpost.audience_from_eligibility(["High school students only"]) == "high_school"


def test_silent_on_age_defers_to_title() -> None:
    assert devpost.audience_from_eligibility(["Students only", "US only"]) is None
    assert devpost.audience_from_eligibility([]) is None
    assert devpost.audience_from_title("Teen Hacks 2026", []) == "high_school"
    assert devpost.audience_from_title("Codegeist 2026", ["Web"]) == "college"
