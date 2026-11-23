"""Filter values settled before a table calculation runs: Korean bounds, and another table's column as a list."""
import re

from app.agent.query.gpt_calc_filters import _number


# "2020년 이후", "2024년 3월까지": a Korean bound includes the period it names.
_BOUND = re.compile(r"((?:19|20)\d{2})\s*년\s*(?:(\d{1,2})\s*월\s*)?(?:도\s*)?(이후|부터|이전|까지)")


def inclusive(question, item):
    """A date or year bound as the question states it: 2020년 이후 is ge 2020, not gt 2020 or ge 2021-01-01."""
    if item.op not in {"gt", "ge", "lt", "le"} or not re.fullmatch(
            r"\d{4}(?:-\d{1,2}){0,2}(?:\.0)?(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z?)?", item.value.strip()):
        return item
    for year, month, word in _BOUND.findall(question):
        later = word in {"이후", "부터"}
        if later != (item.op in {"gt", "ge"}):
            continue
        named = f"{year}-{int(month):02d}" if month else year
        if abs(int(item.value.strip()[:4]) - int(year)) <= 1:  # the bound GPT moved by a day or a year
            return item.model_copy(update={"op": "ge" if later else "le", "value": named})
    return item


_RANGE = re.compile(r"\[?\s*'?([^\[\]!']+)'?!([A-Za-z]{1,3})(\d+):([A-Za-z]{1,3})(\d+)\s*\]?")


def _column_values(item, cells):
    """A filter naming another table's column as a range ([거래!C2:C152]) carries that column's values: in / not_in."""
    found = _RANGE.fullmatch(item.value.strip()) if item.op in {"in", "not_in", "eq", "ne"} else None
    if found is None:
        return item
    from openpyxl.utils import column_index_from_string, get_column_letter
    from app.agent.query.gpt_calc_filters import LISTED
    from app.agent.query.references import normalize_reference
    sheet, first, top, last, bottom = found.groups()
    if (bottom_row := int(found.group(5))) - int(top) > 5000:
        return item
    values = [str(cell.value) for column in range(column_index_from_string(first), column_index_from_string(last) + 1)
              for row in range(int(top), bottom_row + 1)
              if (cell := cells.get(normalize_reference(f"'{sheet}'!{get_column_letter(column)}{row}"))) is not None
              and cell.value not in (None, "")]
    op = {"eq": "in", "ne": "not_in"}.get(item.op, item.op)
    return item.model_copy(update={"op": op, "value": LISTED.join(values)}) if values else item


def _with_mean(table, column, item):
    """A filter compared with the column's mean ("mean") gets that mean as its value: 평균 이상인 거래."""
    if column is None or item.op not in {"gt", "ge", "lt", "le"} or item.value.strip().casefold() not in {"mean", "평균", "average"}:
        return item
    numbers = [value for row in table.rows if _number(value := row.values.get(column.id))]
    return item.model_copy(update={"value": repr(sum(numbers) / len(numbers))}) if numbers else item
