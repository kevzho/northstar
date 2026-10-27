"""
Tests for app/sheets.py, the stdlib .xlsx reader.

It exists instead of openpyxl because this venv has no pip, so a new dependency
could be neither installed nor tested here and would have landed first in the
nightly GitHub job. That trade is only defensible if the sixty lines are actually
tested, so these build real .xlsx files with zipfile and read them back.

The two traps a naive reader falls into, both covered below: blank cells are
ABSENT from the XML rather than empty, so reading cells positionally shifts every
later value into the wrong column; and sheet parts are numbered in creation
order, not tab order, so picking sheet1.xml by position can return the wrong tab.
"""

from __future__ import annotations

import pathlib
import zipfile

import pytest

from app.sheets import read_rows

MAIN = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
RELNS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def build(path: pathlib.Path, sheets: dict[str, str], order: list[str]) -> None:
    """A minimal workbook. `sheets` maps tab name -> sheetData XML."""
    with zipfile.ZipFile(path, "w") as zf:
        rels = "".join(
            f'<Relationship Id="rId{i+1}" Target="worksheets/{name}.xml" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            f'relationships/worksheet"/>'
            for i, name in enumerate(order)
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            f'<?xml version="1.0"?><Relationships xmlns="http://schemas.'
            f'openxmlformats.org/package/2006/relationships">{rels}</Relationships>',
        )
        tabs = "".join(
            f'<sheet name="{tab}" sheetId="{i+1}" r:id="rId{i+1}"/>'
            for i, tab in enumerate(sheets)
        )
        zf.writestr(
            "xl/workbook.xml",
            f'<?xml version="1.0"?><workbook {MAIN} {RELNS}><sheets>{tabs}</sheets></workbook>',
        )
        for part, body in zip(order, sheets.values()):
            zf.writestr(
                f"xl/worksheets/{part}.xml",
                f'<?xml version="1.0"?><worksheet {MAIN}><sheetData>{body}</sheetData></worksheet>',
            )


def inline(ref: str, text: str) -> str:
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def test_a_header_row_becomes_dict_keys(tmp_path) -> None:
    body = (
        f'<row r="1">{inline("A1","name")}{inline("B1","url")}</row>'
        f'<row r="2">{inline("A2","IMO")}{inline("B2","https://imo.example")}</row>'
    )
    path = tmp_path / "w.xlsx"
    build(path, {"Data": body}, ["sheet1"])
    assert read_rows(str(path)) == [{"name": "IMO", "url": "https://imo.example"}]


def test_a_blank_cell_does_not_shift_later_columns(tmp_path) -> None:
    """The trap. A row with an empty middle cell omits it entirely, so reading
    positionally would put the URL under 'organizer'."""
    body = (
        f'<row r="1">{inline("A1","name")}{inline("B1","organizer")}{inline("C1","url")}</row>'
        # B2 is absent, not empty.
        f'<row r="2">{inline("A2","IBO")}{inline("C2","https://ibo.example")}</row>'
    )
    path = tmp_path / "gap.xlsx"
    build(path, {"Data": body}, ["sheet1"])
    row = read_rows(str(path))[0]
    assert row["url"] == "https://ibo.example", f"columns shifted: {row}"
    assert row["organizer"] == ""


def test_shared_strings_are_resolved(tmp_path) -> None:
    """Excel's own exports use the string table, not inline strings, and a styled
    string is split across several <t> runs that must be rejoined."""
    path = tmp_path / "shared.xlsx"
    build(path, {"Data": '<row r="1"><c r="A1" t="s"><v>0</v></c></row>'
                         '<row r="2"><c r="A2" t="s"><v>1</v></c></row>'}, ["sheet1"])
    with zipfile.ZipFile(path, "a") as zf:
        zf.writestr(
            "xl/sharedStrings.xml",
            f'<?xml version="1.0"?><sst {MAIN}>'
            f"<si><t>name</t></si>"
            f"<si><r><t>Regeneron </t></r><r><t>STS</t></r></si>"
            f"</sst>",
        )
    assert read_rows(str(path)) == [{"name": "Regeneron STS"}]


def test_a_named_sheet_is_found_by_name_not_position(tmp_path) -> None:
    """Parts are numbered in creation order. Here the second TAB is stored in
    sheet1.xml, so position-based lookup returns the wrong tab."""
    readme = f'<row r="1">{inline("A1","note")}</row>{{}}'.format(
        f'<row r="2">{inline("A2","read me")}</row>'
    )
    data = (f'<row r="1">{inline("A1","name")}</row>'
            f'<row r="2">{inline("A2","IOI")}</row>')
    path = tmp_path / "two.xlsx"
    # Tab order: README first, Data second, but Data lives in sheet1.xml.
    build(path, {"README": readme, "Data": data}, ["sheet2", "sheet1"])
    assert read_rows(str(path), "Data") == [{"name": "IOI"}]
    assert read_rows(str(path), "README") == [{"note": "read me"}]


def test_a_missing_sheet_name_says_what_is_available(tmp_path) -> None:
    path = tmp_path / "one.xlsx"
    build(path, {"Data": f'<row r="1">{inline("A1","name")}</row>'}, ["sheet1"])
    with pytest.raises(KeyError) as caught:
        read_rows(str(path), "Nope")
    assert "Data" in str(caught.value)


def test_trailing_blank_rows_are_dropped(tmp_path) -> None:
    """Spreadsheet exports routinely carry empty rows; they must not become
    dicts of empty strings that later code treats as real leads."""
    body = (
        f'<row r="1">{inline("A1","name")}</row>'
        f'<row r="2">{inline("A2","AtCoder")}</row>'
        f'<row r="3"><c r="A3" t="inlineStr"><is><t></t></is></c></row>'
    )
    path = tmp_path / "blanks.xlsx"
    build(path, {"Data": body}, ["sheet1"])
    assert read_rows(str(path)) == [{"name": "AtCoder"}]


def test_the_real_sheets_parse_if_present() -> None:
    """Against the actual files when they are on disk. Skipped in CI, where they
    are not, they are a 70KB download, not repo content."""
    real = pathlib.Path.home() / "Downloads" / "stem_competitions_1000.xlsx"
    if not real.exists():
        pytest.skip("curated sheet not present on this machine")
    rows = read_rows(str(real), "Competitions")
    assert len(rows) == 1000
    assert {"name", "website", "level", "country", "confidence"} <= set(rows[0])


# --- sheet timing must never become a deadline ---------------------------
#
# stem_database_2000_with_timing.xlsx adds typical_deadline and
# typical_event_timing, and its README grades them: "Known typical annual cycle"
# (the programme's usual month, from past cycles), "Estimate based on program
# type" (a placeholder), "Not known". It then says plainly: "None of these are
# verified dates for the 2026-27 cycle."
#
# opportunities.deadline is a real date that app/roadmap.py renders as "Closes
# 2026-12-15 - 79 days away. Start today." Deriving that from "~mid-December"
# would put an invented date in front of a student and let expire_opportunities
# retire the row when the invented date passed. recurrence_month is the column
# for an unverified usual month, and recurrence_verified_at stays NULL because
# that is the licence for a date claim and no human has given it.

import sys as _sys
_sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))


def test_only_a_known_cycle_yields_a_month() -> None:
    from import_opportunity_sheet import recurrence_month_of

    known = "Known typical annual cycle — confirm this year's exact date"
    assert recurrence_month_of(
        {"timing_basis": known, "typical_deadline": "Application ~mid-December"}
    ) == 12
    # An estimate about a CATEGORY is not a claim about this programme.
    assert recurrence_month_of(
        {"timing_basis": "Estimate based on program type — placeholder",
         "typical_deadline": "Application ~mid-December"}
    ) is None
    assert recurrence_month_of(
        {"timing_basis": "Not known — check organizer",
         "typical_deadline": "Application ~mid-December"}
    ) is None


def test_prose_without_a_month_yields_nothing() -> None:
    """886 of the 1,000 competition rows read "Via national team selection" -
    which is entry-gate information, not timing, and must not be coerced."""
    from import_opportunity_sheet import recurrence_month_of

    known = "Known typical annual cycle"
    for prose in ("Via national team selection", "Rolling / open enrollment",
                  "Application ~spring", "Via national coordinator", ""):
        assert recurrence_month_of(
            {"timing_basis": known, "typical_deadline": prose}
        ) is None, f"{prose!r} should not produce a month"


def test_the_first_month_named_wins() -> None:
    """"Registration November, event March" is about closing in November."""
    from import_opportunity_sheet import recurrence_month_of

    assert recurrence_month_of({
        "timing_basis": "Known typical annual cycle",
        "typical_deadline": "Registration closes November, contest held March",
    }) == 11


def test_the_importer_never_writes_deadline_from_the_sheet() -> None:
    """The guard that matters. to_row must take its deadline only from the page
    reading, and must refuse a past one even then."""
    import inspect

    import import_opportunity_sheet as mod

    src = inspect.getsource(mod.to_row)
    assert 'verdict.get("deadline")' in src, "deadline must come from the page verdict"
    assert "typical_deadline" not in src, (
        "to_row references the sheet's unverified timing prose for the deadline "
        "column — that is a fabricated date in front of a student"
    )
    # Assignment, not mention: to_row carries a comment explaining why this
    # column is deliberately left alone, and a test that banned the words would
    # punish the explanation rather than the behaviour.
    assert 'row["recurrence_verified_at"]' not in src, (
        "recurrence_verified_at is being written: it is the licence for a "
        "forward-looking date claim, and no human has checked these pages"
    )
    assert 'row["recurrence_month"]' in src, (
        "the sheet's usual month should still be recorded, just unverified"
    )
