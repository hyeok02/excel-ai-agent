"""Keep table captions with the facts they describe, without trusting model prose.

Only captions on the numeric evidence's own sheet and above its columns are
eligible. Workbook filenames, documentation on other sheets, and unrelated
titles are not substitutes for that relationship.
"""
import re

from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

from app.services.insights.narratives.narrative_values import finite, reference
from app.services.insights.verification.validation_index import extract_references

_META = re.compile(r"^(title|summary|제목|개요)\s*[:：]?$", re.I)
_EXCLUDE = re.compile(
    r"freeze panes|worksheet contains|please |click |select |refresh|"
    r"^\s*(?:source|data|note|footnote|http|copyright|자료출처|출처|주석)\s*[:：]|"
    r"\b(?:not|never|ignore|instruction)\b|아님|아닙|무시|명령", re.I,
)
_SECTION = re.compile(r"^(?:annual totals?|year to date|year\s*\d{4}|\d{4}|연간 합계|누적)$", re.I)


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


def _joined_captions(candidates):
    result = []
    for row, col, text, cited in candidates:
        if (result and row == result[-1][0] + len(result[-1][3])
                and col == result[-1][1]
                and re.match(r"^(?:by|for|in|during)\b", text, re.I)):
            previous = result[-1]
            result[-1] = (previous[0], col, previous[2] + " " + text, previous[3] + cited)
        else:
            result.append((row, col, text, cited))
    return result


def _header(populated, left, right):
    relevant = [(col, cell) for col, cell in populated if left - 1 <= col <= right]
    if len(relevant) < 2:
        return False
    values = [cell.get("value") for _, cell in relevant]
    if any(re.fullmatch(r"[-—–.]+|N/?A|N/?M|W|#\w+[!?]?|not available|없음", str(value).strip(), re.I)
           for value in values):
        return False
    if all(isinstance(value, str) and len(value) < 100 for value in values):
        return True
    # A cross-tab's first heading can be any source dimension, not just Year.
    # Consecutive year columns are structural headings even when stored as
    # Excel numbers. A single year-like amount is insufficient evidence.
    periods = values[1:]
    return bool(isinstance(values[0], str) and len(values[0]) < 100 and len(periods) >= 2
                and all(finite(value) and int(value) == value and 1900 <= value <= 2099 for value in periods)
                and len(set(periods)) == len(periods)
                and (periods == sorted(periods) or periods == sorted(periods, reverse=True)))


def _column_window(rows, top, left, right):
    """Keep notes in the same side-by-side header block as numeric evidence."""
    for row in sorted((row for row in rows if row < top), reverse=True):
        populated = sorted(rows[row], key=lambda pair: pair[0])
        if not _header(populated, left, right):
            continue
        groups = []
        for col, _ in populated:
            if not groups or col > groups[-1][-1] + 1:
                groups.append([col])
            else:
                groups[-1].append(col)
        selected = [index for index, group in enumerate(groups)
                    if any(left <= col <= right for col in group)]
        if len(selected) != 1:
            return None
        index = selected[0]
        start = groups[index][0] if index else 1
        end = groups[index + 1][0] if index + 1 < len(groups) else float("inf")
        return start, end
    return 1, float("inf")


def _same_column_block(rows, candidate, top, left, right):
    for row in sorted((row for row in rows if candidate[0] < row < top), reverse=True):
        populated = sorted(rows[row], key=lambda pair: pair[0])
        if not _header(populated, left, right):
            continue
        groups = []
        for col, _ in populated:
            if not groups or col > groups[-1][-1] + 1:
                groups.append([col])
            else:
                groups[-1].append(col)
        selected = [group for group in groups if any(left <= col <= right for col in group)]
        if len(selected) > 1:
            return False
        if selected and any(group[-1] < selected[0][0] for group in groups):
            return candidate[1] >= selected[0][0] - 1
        break
    return True


def _caption(value, explicit=False):
    if not isinstance(value, str):
        return False
    text = " ".join(value.split()).strip()
    if not 15 <= len(text) <= (600 if explicit else 240) or _EXCLUDE.search(text) or _SECTION.fullmatch(text):
        return False
    if (re.search(r"\b(?:preliminary|provisional|final|revised)\b|잠정치|확정치|수정치", text, re.I)
            and re.match(r"^(?:(?:values?|figures?|data|estimates?)\s+(?:for\s+)?(?:19|20)\d{2}"
                         r"|(?:19|20)\d{2}(?:년|\s+(?:values?|figures?|data|estimates?)))", text, re.I)):
        return False  # a year-status sentence is not a new table boundary
    if text.startswith("(") and text.endswith(")"):
        return False  # a unit note alone is not a subject
    # Descriptive table-title syntax; a naked category ('New England') or
    # metric row ('Total Revenue') is insufficient to label an entire table.
    return bool(re.search(
        r"\b(?:table\s+[\w.]+|indicator\s+[\w.]+|percentage of|number of|"
        r"estimates?\s*:|by\s+|for\s+|timeseries|time series|average price|net generation)\b|"
        r"(?:현황|추이|통계|내역|분석|자료|보고서)", text, re.I,
    ))


def _cells(sheet):
    result = {}
    facts = sheet.get("business_facts", {})
    regions = facts.get("table_regions") or [{"rows": facts.get("table_rows", [])}]
    for region in regions:
        for row in region.get("rows", []):
            for cell in row:
                address = cell.get("cell")
                if address and cell.get("value") not in (None, ""):
                    result[address] = cell
    return result


def compact_facts(items, limit=3, max_chars=440):
    """An overview shows conclusions; full point-by-point paths stay on cards.

    Use complete source-generated sentences, not character truncation or a new
    model call. Recent reversals stay beside the full-period change so a long
    decline is never rewritten as continuous decline.
    """
    parts = []
    for item in items[:limit]:
        sentences = re.split(r"(?<=다\.)\s+", item.fact.strip())
        if not sentences:
            continue
        first = sentences[0]
        # Split complete Korean narrative sentences, never decimal points or
        # abbreviations inside a source's company/category name.
        recent = next((s for s in sentences if s.startswith("최근 구간은 ")), "")
        if recent:
            first += " " + recent
        elif len(sentences) > 1 and sentences[1].startswith("이전 기간 대비 "):
            first += " " + sentences[1]
        # Never cut a sentence or its numeric unit to fit a character budget.
        # Additional conclusions remain available in the detailed cards.
        if parts and len(" ".join([*parts, first])) > max_chars:
            break
        parts.append(first)
    return " ".join(parts)
