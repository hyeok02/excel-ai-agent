"""Checklist tables: short status marks repeated across neighbouring columns."""
from collections import Counter

from app.services.insights.narratives.table_dates import column as col

SYMBOLS = {
    "o": "o", "0": "o", "○": "o", "◯": "o", "●": "o",
    "x": "x", "×": "x", "✕": "x", "✗": "x",
    "△": "△", "▲": "△", "▽": "△",
    "v": "v", "✓": "v", "✔": "v", "√": "v",
    "?": "?", "-": "-", "ー": "-", "–": "-",
}
MIN_ITEMS = 4
MIN_COLUMNS = 2
MAX_MARKS = 5
MIN_MARK_SHARE = 0.7


def flag_matrix(header, records):
    """
    같은 표식이 이웃한 여러 칸에 반복되면 그 표는 점검표다.

    한 칸에 담긴 값이 'o' 하나뿐이라 분류로도 수치로도 잡히지 않고, 빈칸이 많아
    기존 열 선택 기준(80% 이상 채워짐)에서도 탈락해 통째로 설명되지 않았다.
    """
    marked = [found for cell in header
              if (found := _marked_column(cell, records)) is not None]
    run = _longest_run(marked)
    if len(run) < MIN_COLUMNS:
        return None
    return _label_column(header, records, run[0][0]), run


def blank_records(records, run):
    """A row with no mark at all is an item nobody has checked yet."""
    positions = {position for position, *_ in run}
    return [record for record in records
            if not any(col(item) in positions and item.get("value") not in (None, "")
                       for item in record)]


def mark_of(value):
    text = str(value or "").strip()
    return SYMBOLS.get(text[:1].casefold()) if text else None


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
    if len(filled) < MIN_ITEMS or len(marks) < len(filled) * MIN_MARK_SHARE:
        return None
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
