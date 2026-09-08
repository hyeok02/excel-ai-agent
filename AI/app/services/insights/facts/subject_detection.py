"""Find the workbook's subject where a sheet writes it down, never by guessing.

Some workbooks name the company in a labelled row; others repeat it as the
header spanning every period column of each sheet. Both are written in the
file, so both may be cited. A filename is not a source and is never read here.
"""
from app.services.insights.narratives.narrative_values import reference
from app.services.insights.narratives.table_dates import column as col
from app.services.insights.facts.table_inputs import narrative_regions

MIN_SPAN = 3
MIN_SHEETS = 2
MIN_LENGTH = 4
MAX_LENGTH = 80


def spanning_subject(context) -> tuple[str, list[str]]:
    """A name repeated as a table header across sheets is what the file is about.

    Requiring two sheets keeps single-table wording such as a period label out.
    Among the survivors the longest is taken: a workbook usually carries both a
    ticker and a full name, and the full name is the one a reader can use.
    """
    found: dict[str, list] = {}
    for sheet in context.get("sheets", []):
        if not isinstance(sheet, dict):
            continue
        name = str(sheet.get("name", ""))
        for value, cell in _spans(sheet):
            entry = found.setdefault(value, [set(), reference(name, cell)])
            entry[0].add(name)
    ranked = sorted(
        ((value, entry[1]) for value, entry in found.items()
         if len(entry[0]) >= MIN_SHEETS),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    return (ranked[0][0], [ranked[0][1]]) if ranked else ("", [])


def _spans(sheet):
    for region in narrative_regions(sheet.get("business_facts", {})):
        for row in region.get("rows", []):
            yield from _row_spans(row)


def _row_spans(row):
    cells = [cell for cell in row if isinstance(cell.get("value"), str)]
    index = 0
    while index < len(cells):
        end = index
        while (end + 1 < len(cells)
               and cells[end + 1]["value"] == cells[index]["value"]
               and col(cells[end + 1]) == col(cells[end]) + 1):
            end += 1
        text = " ".join(str(cells[index]["value"]).split())
        if end - index + 1 >= MIN_SPAN and MIN_LENGTH <= len(text) <= MAX_LENGTH:
            yield text, cells[index]["cell"]
        index = end + 1
