"""Checklist tables: short status marks repeated across neighbouring columns."""
from collections import Counter
import re

from app.services.insights.narratives.table_dates import column as col
from app.services.insights.facts.flag_marks import SYMBOLS, mark_of

MIN_ITEMS = 4
MIN_COLUMNS = 2
MAX_MARKS = 5
MIN_MARK_SHARE = .7


def flag_matrix(header, records):
    """
    같은 표식이 이웃한 여러 칸에 반복되면 그 표는 점검표다.

    한 칸에 담긴 값이 'o' 하나뿐이라 분류로도 수치로도 잡히지 않고, 빈칸이 많아
    기존 열 선택 기준(80% 이상 채워짐)에서도 탈락해 통째로 설명되지 않았다.
    """
    marked = [found for cell in header
              if (found := _marked_column(cell, records)) is not None]
    run = _longest_run(marked)
    # Zeroes, dashes and question marks alone can be ordinary missing/numeric
    # data. At least one explicit status symbol must establish a checklist.
    explicit = any(mark_of(item["value"]) is not None
                   and str(item["value"]).strip()[:1].casefold() not in {"0", "-", "ー", "–", "?"}
                   for _, _, _, filled in run for item in filled)
    if len(run) < MIN_COLUMNS or not explicit:
        return None
    return _label_column(header, records, run[0][0]), run


def blank_records(records, run):
    """A row with no mark at all is an item nobody has checked yet."""
    positions = {position for position, *_ in run}
    return [record for record in records
            if not any(col(item) in positions and item.get("value") not in (None, "")
                       for item in record)]


def checklist_records(records, label, run):
    """Keep item rows, not a source note below the table, in the denominator."""
    positions = {position for position, *_ in run}
    checked = [record for record in records if any(
        col(item) in positions and mark_of(item.get("value")) is not None
        for item in record
    )]
    if not checked:
        return []
    # Key fields present on every marked row identify unmarked item rows too.
    # In a table with both ID and name, a note in the ID column is not an item.
    keys = set.intersection(*[
        {col(item) for item in record if col(item) < min(positions)
         and item.get("value") not in (None, "")}
        for record in checked
    ])
    if label is not None:
        keys.add(col(label))
    result = []
    for record in records:
        filled = [item for item in record if item.get("value") not in (None, "")]
        if any(col(item) in positions and mark_of(item.get("value")) is not None for item in filled):
            result.append(record)
        elif keys and keys <= {col(item) for item in filled}:
            if len(filled) == 1 and re.match(
                r"^(?:source|sources|note|notes|footnote|출처|자료|주|비고)\s*[:：.]",
                str(filled[0]["value"]).strip(), re.I,
            ):
                continue
            result.append(record)
    return result


def _marked_column(cell, records):
    name = cell.get("value")
    if not isinstance(name, str) or not name.strip():
        return None
    position = col(cell)
    filled = [item for record in records
              for item in record
              if col(item) == position and item.get("value") not in (None, "")]
    marks = [(found, str(item["value"]).strip()[:1]) for item in filled
             if (found := mark_of(item.get("value")))]
    if len(filled) < MIN_ITEMS or len(marks) / len(filled) < MIN_MARK_SHARE:
        return None
    # Some checklists combine marks with a few written statuses. Preserve each
    # such category in the distribution; numeric/missing values cannot become
    # statuses and unknown values must never disappear from the total.
    for item in filled:
        value = item["value"]
        if mark_of(value) is not None:
            continue
        if not isinstance(value, str):
            return None
        text = value.strip()
        if len(text) > 80 or not re.search(r"[^\W\d_]", text):
            return None
        marks.append((f"text:{text}", text))
    counts = _as_written(marks)
    if not 1 <= len(counts) <= MAX_MARKS:
        return None
    return position, cell, counts, filled


def _as_written(marks):
    """Count by the symbol the sheet actually shows: ✓ must not be reported as v."""
    forms: dict[str, Counter] = {}
    for normalized, written in marks:
        forms.setdefault(normalized, Counter())[written] += 1
    return Counter({
        written.most_common(1)[0][0]: sum(written.values())
        for written in forms.values()
    })


def _longest_run(marked):
    best, run = [], []
    for item in sorted(marked, key=lambda found: found[0]):
        if run and item[0] != run[-1][0] + 1:
            run = []
        run.append(item)
        if len(run) > len(best):
            best = list(run)
    return best


def _label_column(header, records, first_marked):
    """Name the thing being checked: the nearest text column left of the marks."""
    for cell in sorted(header, key=col, reverse=True):
        position = col(cell)
        if position >= first_marked or not isinstance(cell.get("value"), str):
            continue
        values = [item.get("value") for record in records for item in record
                  if col(item) == position and item.get("value") not in (None, "")]
        texts = [value for value in values if isinstance(value, str)]
        if len(texts) >= MIN_ITEMS and len(set(texts)) > len(texts) / 2:
            return cell
    return None
