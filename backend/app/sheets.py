"""
Minimal .xlsx reader, standard library only.

WHY NOT openpyxl. The catalog is curated in a spreadsheet and re-exported as the
list grows, so reading .xlsx belongs in the repo rather than in a one-off
conversion someone has to remember to run. But this venv has no pip, so a new
dependency could not be installed or tested here, and adding one to
requirements.txt untested would land first in the nightly GitHub job, the exact
place a broken import is least visible. An .xlsx is a zip of XML; reading the
handful of parts a flat export uses is about sixty lines, and those sixty lines
can be tested against the real files right now.

SCOPE, DELIBERATELY SMALL. Values as strings, one header row, no formulas
evaluated, no styles, no dates reconstructed from serial numbers. Anything richer
belongs in a real library. If a future sheet needs merged cells or typed dates,
that is the moment to add the dependency properly rather than to grow this.
"""

from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    """The string table. A cell with t="s" holds an index into this."""
    try:
        raw = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []  # a sheet of only numbers has no table
    out: list[str] = []
    for si in ElementTree.fromstring(raw).findall(f"{_MAIN}si"):
        # A styled string is split across several <t> runs; join them, or a
        # value that happened to be bolded mid-word would come back truncated.
        out.append("".join(t.text or "" for t in si.iter(f"{_MAIN}t")))
    return out


def sheet_names(zf: zipfile.ZipFile) -> dict[str, str]:
    """{sheet name: part path}, resolved through the relationships.

    Not by guessing sheet1.xml from position: Excel numbers the PARTS in
    creation order, not tab order, so a workbook whose tabs were reordered or
    whose first sheet was deleted maps the wrong way round.
    """
    rels = {
        r.get("Id"): r.get("Target")
        for r in ElementTree.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    }
    out: dict[str, str] = {}
    for sheet in ElementTree.fromstring(zf.read("xl/workbook.xml")).iter(f"{_MAIN}sheet"):
        target = rels.get(sheet.get(f"{_REL}id")) or ""
        target = target.lstrip("/")
        out[sheet.get("name") or ""] = (
            target if target.startswith("xl/") else f"xl/{target}"
        )
    return out


def _col_index(ref: str) -> int:
    """'C7' -> 2. Cells are addressed, not ordered: a blank cell is simply
    absent from the XML, so reading them positionally shifts every value after
    the first gap into the wrong column."""
    letters = re.match(r"([A-Z]+)", ref or "")
    if not letters:
        return 0
    index = 0
    for char in letters.group(1):
        index = index * 26 + (ord(char) - 64)
    return index - 1


def read_rows(path: str, sheet: str | None = None) -> list[dict[str, str]]:
    """Rows as dicts keyed by the header row. Empty rows are dropped."""
    with zipfile.ZipFile(path) as zf:
        strings = _shared_strings(zf)
        sheets = sheet_names(zf)
        if sheet is None:
            sheet = next(iter(sheets))
        if sheet not in sheets:
            raise KeyError(f"no sheet named {sheet!r}; have {sorted(sheets)}")
        root = ElementTree.fromstring(zf.read(sheets[sheet]))

    table: list[list[str]] = []
    for row in root.iter(f"{_MAIN}row"):
        cells: dict[int, str] = {}
        for cell in row.findall(f"{_MAIN}c"):
            kind = cell.get("t")
            if kind == "inlineStr":
                node = cell.find(f"{_MAIN}is")
                value = "".join(t.text or "" for t in node.iter(f"{_MAIN}t")) if node is not None else ""
            else:
                node = cell.find(f"{_MAIN}v")
                value = (node.text or "") if node is not None else ""
                if kind == "s":
                    try:
                        value = strings[int(value)]
                    except (ValueError, IndexError):
                        value = ""
            cells[_col_index(cell.get("r") or "")] = value.strip()
        if not cells:
            continue
        width = max(cells) + 1
        table.append([cells.get(i, "") for i in range(width)])

    if not table:
        return []
    header = [h or f"col{i}" for i, h in enumerate(table[0])]
    out: list[dict[str, str]] = []
    for row in table[1:]:
        if not any(row):
            continue
        padded = row + [""] * (len(header) - len(row))
        out.append(dict(zip(header, padded)))
    return out
