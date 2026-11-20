"""A score column's mean per group of a repeating category column (반별 국어 평균, 연령대별 추천점수).

The category is read from the values: a text column every scored row fills, whose few labels
(2~12) each come back on several rows. Nothing is chosen by its header words.
"""
import re

MAX_GROUPS = 12


def group_means(rows, selected, cells):
    """(header cell, [(mean, label)] highest first, category cells), or None when no column groups the rows."""
    scored = {_row(cell) for cell in selected}
    first = min(scored)
    by_column = {}
    for row in rows:
        for cell in row:
            value = cell.get("value")
            if _row(cell) in scored and isinstance(value, str) and value.strip():
                by_column.setdefault(_column(cell), {})[_row(cell)] = (value.strip(), cell)
    for column, labelled in sorted(by_column.items()):
        distinct = {label for label, _ in labelled.values()}
        if len(labelled) != len(scored) or not 2 <= len(distinct) <= MAX_GROUPS or len(distinct) * 2 > len(scored):
            continue
        header = max((cell for cell in cells if _column(cell) == column and _row(cell) < first
                      and isinstance(cell.get("value"), str) and cell["value"].strip()), key=_row, default=None)
        if header is None:
            continue
        groups = {}
        for cell in selected:
            groups.setdefault(labelled[_row(cell)][0], []).append(cell["value"])
        means = sorted(((sum(values) / len(values), label) for label, values in groups.items()), reverse=True)
        return header, means, sorted((cell for _, cell in labelled.values()), key=_row)
    return None


def _row(cell):
    return int(re.sub(r"\D", "", str(cell.get("cell", ""))) or 0)


def _column(cell):
    return re.sub(r"[\d$]", "", str(cell.get("cell", "")))
