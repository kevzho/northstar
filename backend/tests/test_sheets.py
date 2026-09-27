"""
Tests for app/sheets.py — the stdlib .xlsx reader.

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
    # Tab order: README first, Data second — but Data lives in sheet1.xml.
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
    are not — they are a 70KB download, not repo content."""
    real = pathlib.Path.home() / "Downloads" / "stem_competitions_1000.xlsx"
    if not real.exists():
        pytest.skip("curated sheet not present on this machine")
    rows = read_rows(str(real), "Competitions")
    assert len(rows) == 1000
    assert {"name", "website", "level", "country", "confidence"} <= set(rows[0])
