"""Keep table captions with the facts they describe, without trusting model prose.

Only captions on the numeric evidence's own sheet and above its columns are
eligible. Workbook filenames, documentation on other sheets, and unrelated
titles are not substitutes for that relationship.
"""
from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

from app.services.insights.narratives.narrative_values import finite, reference
from app.services.insights.verification.validation_index import extract_references
from app.services.insights.narratives.source_caption_rules import _META, _EXCLUDE, _SECTION, _joined_captions, _caption, _cells
from app.services.insights.narratives.source_caption_boundaries import _header, _column_window, _same_column_block
from app.services.insights.narratives.source_overview import compact_facts


def source_table_context(context, item):
    """Return (source caption, cited cells) for one numeric insight, or nothing."""
    scoped = _source_scope(context, item)
    if not scoped:
        return "", []
    sheet, top, _, start, _, candidates, _, _ = scoped
    eligible = [candidate for candidate in candidates if start <= candidate[0] < top]
    if not eligible:
        return "", []
    _, _, caption, cited = eligible[-1]
    return caption, [reference(sheet["name"], cell["cell"]) for cell in cited]


def source_table_window(context, item):
    """Source sheet and row/column intervals that can supply this table's notes."""
    scoped = _source_scope(context, item)
    if not scoped:
        return None
    sheet, _, _, start, end, _, left, right = scoped
    return str(sheet["name"]), start, end, left, right


def _source_scope(context, item):
    sheets = {str(s.get("name", "")).casefold(): s
              for s in context.get("sheets", []) if isinstance(s, dict)}
    bounds = {}
    for evidence in item.evidence:
        for ref in extract_references(str(evidence)):
            name, _, area = ref.partition("!")
            if name not in sheets:
                continue
            try:
                box = range_boundaries(area)
            except ValueError:
                continue
            bounds.setdefault(name, set()).add(box)
    # Index only cited sheets. Resolve each cell coordinate once, rather than
    # rescanning and reparsing the whole workbook for every evidence reference.
    maps = {name: _cells(sheets[name]) for name in bounds}
    numeric = {}
    for name, boxes in bounds.items():
        for address, cell in maps[name].items():
            if not finite(cell.get("value")):
                continue
            row, col = coordinate_to_tuple(address)
            if any(left <= col <= right and top <= row <= bottom
                   for left, top, right, bottom in boxes):
                numeric.setdefault(name, {})[address] = (row, col)
    # Even one numeric cell from a second sheet can change a comparison's
    # meaning. A dominant cell count is not evidence of a single subject.
    if len(numeric) != 1:
        return None
    name = next(iter(numeric))
    top = min(row for row, _ in numeric[name].values())
    bottom = max(row for row, _ in numeric[name].values())
    left = min(col for _, col in numeric[name].values())
    right = max(col for _, col in numeric[name].values())
    rows = {}
    for address, cell in maps[name].items():
        row, col = coordinate_to_tuple(address)
        rows.setdefault(row, []).append((col, cell))
    candidates = []
    for row, populated in sorted(rows.items()):
        populated.sort(key=lambda pair: pair[0])
        if len(populated) == 2 and _META.fullmatch(str(populated[0][1].get("value", "")).strip()):
            label, value = populated[0][1], populated[1][1]
            if populated[0][0] <= left and _caption(value.get("value"), explicit=True):
                # A source-authored summary is a better concise description
                # than a long title, but is still cited and scope-bound.
                candidates.append((row, populated[0][0], str(value["value"]), [label, value]))
        elif len(populated) == 1 and populated[0][0] <= left:
            value = populated[0][1]
            if _caption(value.get("value")):
                candidates.append((row, populated[0][0], str(value["value"]), [value]))
    candidates = _joined_captions(candidates)
    boundaries = {candidate[0] for candidate in candidates}
    numeric_rows = {row for row, populated in rows.items()
                    if any(left <= col <= right and finite(cell.get("value")) for col, cell in populated)}
    for row, populated in rows.items():
        if row in boundaries or not _header(populated, left, right):
            continue
        prior = max((previous for previous in numeric_rows if previous < row), default=0)
        title = max((candidate[0] for candidate in candidates if candidate[0] < row), default=0)
        if prior and title <= prior and any(later > row for later in numeric_rows):
            boundaries.add(row)
    # A caption below the first cited point, or a fresh header after prior
    # numeric records, splits tables. Never lend one table's title to another.
    if any(top < row <= bottom for row in boundaries):
        return None
    start = max((row for row in boundaries if row <= top), default=1)
    end = min((row for row in boundaries if row > bottom), default=float("inf"))
    columns = _column_window(rows, top, left, right)
    if columns is None:
        return None
    candidates = [candidate for candidate in candidates
                  if _same_column_block(rows, candidate, top, left, right)]
    return sheets[name], top, bottom, start, end, candidates, *columns
