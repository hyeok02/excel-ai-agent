"""A summed column must not count its own SUM row twice.

Totals!C5:C8 hold region totals and C9 is =SUM(C5:C8). Summing C5:C9 doubles the
result. A row is set aside only when its cell is a plain SUM over a range of the
same column whose every row is also being summed; the answer says so. Any other
formula is left alone, as before. A total typed in as a value ("Total greenhouse gas emissions"
790.8 under seven gases) is found by typed_total: its label says total and every summed cell equals
the sum of the other rows, so adding it would double the result.
"""
import re

_SUM = re.compile(r"=\s*SUM\(\s*\$?([A-Z]{1,3})\$?(\d+)\s*:\s*\$?([A-Z]{1,3})\$?(\d+)\s*\)\s*", re.I)


def without_subtotals(rows, columns, sheet):
    """(rows without SUM rows of the summed columns, a note per row set aside)."""
    numbers = {row.row_number for row in rows}
    dropped = {}
    for row in rows:
        for column in columns:
            found = _SUM.fullmatch(row.formulas.get(column, "") or "")
            if (found and found[1].upper() == found[3].upper() == column.upper()
                    and row.row_number not in range(int(found[2]), int(found[4]) + 1)
                    and set(range(int(found[2]), int(found[4]) + 1)) <= numbers - {row.row_number}):
                dropped[row.row_number] = f"{sheet}!{column}{row.row_number}"
    if not dropped:
        return rows, []
    notes = [f"{', '.join(dropped.values())}은(는) 위 행들을 더한 합계 행이라 중복 합산하지 않았습니다."]
    return [row for row in rows if row.row_number not in dropped], notes


_TOTAL = re.compile(r"(?:^|\b)(?:grand\s+)?total\b|합계|총계|총합|^전체", re.I)


def typed_total(rows, columns):
    """The one row labelled total whose summed values are the sums of all other rows, or None."""
    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    labelled = [row for row in rows if any(isinstance(value, str) and _TOTAL.search(value.strip())
                                           for key, value in getattr(row, "values", {}).items() if key not in columns)]
    if len(labelled) != 1 or len(rows) < 3:
        return None
    total = labelled[0]
    for column in columns:
        parts = [row.values.get(column) for row in rows if row is not total]
        value = total.values.get(column)
        if not number(value) or not all(number(part) for part in parts) \
                or abs(sum(parts) - value) > 1e-6 * max(1.0, abs(value)):
            return None
    return total
