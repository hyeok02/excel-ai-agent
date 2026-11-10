"""A summed column must not count its own SUM row twice.

Totals!C5:C8 hold region totals and C9 is =SUM(C5:C8). Summing C5:C9 doubles the
result. A row is set aside only when its cell is a plain SUM over a range of the
same column whose every row is also being summed; the answer says so. Any other
formula is left alone, as before.
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
