"""Resolve a question that repeats a verified insight's title to the columns it counted.

Suggested questions are built from insight titles ("주요 사건 구성" → "주요 사건 구성을
항목별로 요약해줘"). The insight cites the header cell of every column it counted,
so the question needs no column name of its own. Row identifiers (every value
distinct) are labels of the counted rows, not distributions, and are left out.
"""
import re

from app.agent.query.verified_facts import build_verified_question_context

# How a suggested question reshapes a title: "점검 현황" → "점검을", "표시" → "의 표시별 건수".
_TITLE_TAILS = ("현황", "표시")


def insight_columns(question, summary, tables):
    """([(table, columns)], [title spelled in the question]) for one matching insight."""
    asked = _normal(question)
    matches = []
    for item in build_verified_question_context(summary)["insights"]:
        spelled = _spelled(str(item.get("title") or ""), asked)
        cited = {_reference(value) for value in item.get("evidence") or ()}
        found = [(table, columns) for table in tables
                 if (columns := [column for column in table.columns
                                 if _reference(column.header_reference) in cited
                                 and column.id not in getattr(table, "hidden_columns", ())])]
        if spelled and len(found) == 1:
            matches.append(((found[0][0], _without_identifiers(*found[0])), spelled))
    if len(matches) != 1:
        return [], []
    found, spelled = matches[0]
    return ([found], [spelled]) if found[1] else ([], [])


def _spelled(title, asked):
    """The longest spelling of the title the question contains, or ''."""
    title = _normal(title)
    candidates = [title, *(title[:-len(tail)].strip() for tail in _TITLE_TAILS if title.endswith(tail))]
    return next((text for text in candidates if len(text) >= 4 and text in asked), "")


def _without_identifiers(table, columns):
    counted = [column for column in columns if not _identifier(table, column)]
    return counted or columns


def _identifier(table, column):
    values = [row.values.get(column.id) for row in table.rows if row.values.get(column.id) not in (None, "")]
    return len(values) > 1 and len(set(map(str, values))) == len(values)


def _reference(value):
    sheet, _, cell = str(value).rpartition("!")
    if sheet.startswith("'") and sheet.endswith("'"):
        sheet = sheet[1:-1].replace("''", "'")
    return f"{sheet}!{cell.replace('$', '').upper()}"


def _normal(value):
    return re.sub(r"\s+", " ", str(value).casefold()).strip()
