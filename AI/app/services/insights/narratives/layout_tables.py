"""Tables read as their header rows and the data rows right under them, for narratives that relate tables.

Regions come from the parser's layout: a header region, the data region starting on the next row in
the same columns, and the title or unit line above. Nothing here depends on a file's words.
"""
import re

from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.narratives.narrative_values import finite, number, reference

TOTAL = re.compile(r"\b(?:grand\s+)?total\b|합계|총계|소계|^계$", re.I)
NONADDITIVE = re.compile(r"\b(?:unit|per|average|avg|mean|rate|ratio|percent(?:age)?|margin|price|score)\b"
                         r"|단가|평균|비율|비중|률|율|점수|순위", re.I)
UNIT = re.compile(r"[(（]\s*(?:단위\s*[:：]\s*)?([^)）:：]{1,8})\s*[)）]")


def _place(cell):
    letters, row = coordinate_from_string(cell)
    return column_index_from_string(letters), row


def sheet_tables(sheet):
    """[{sheet, title, unit, header, rows}] of a sheet: header rows as given, data rows as {column: cell}."""
    regions = [region for region in narrative_regions(sheet.get("business_facts", {}))
               if region.get("start_cell") and region.get("end_cell")]
    tables = []
    for index, region in enumerate(regions):
        if region.get("role") != "header" or not region.get("rows"):
            continue
        (left, top), (right, bottom) = _place(region["start_cell"]), _place(region["end_cell"])
        data = next((item for item in regions[index + 1:] if item.get("role") == "data" and item.get("rows")
                     and _place(item["start_cell"]) == (left, bottom + 1)
                     and _place(item["end_cell"])[0] == right), None)
        if data is None:
            continue
        above = [item for item in regions[:index] if item.get("role") in {"title", "description", "unit"}
                 and _place(item["start_cell"])[0] == left and _place(item["end_cell"])[1] < top]
        title = str(above[-1].get("title") or "").strip() if above else ""
        unit = UNIT.search(title)
        tables.append({"sheet": str(sheet.get("name", "")), "title": title, "unit": unit[1].strip() if unit else "",
                       "title_cell": above[-1]["start_cell"] if above else None,
                       "header": [{_place(cell["cell"])[0]: cell for cell in row} for row in region["rows"]],
                       "rows": [{_place(cell["cell"])[0]: cell for cell in row} for row in data["rows"]]})
    return tables


def label(table, position):
    """The lowest header text over a column: '제품' written once over two header rows."""
    for row in reversed(table["header"]):
        if (cell := row.get(position)) and str(cell.get("value") or "").strip():
            return " ".join(str(cell["value"]).split())
    return ""


def kept_rows(table, key):
    """Data rows with a key text that is not a total line."""
    return [row for row in table["rows"] if isinstance(row.get(key, {}).get("value"), str)
            and row[key]["value"].strip() and not TOTAL.search(row[key]["value"].strip())]


def numbers(rows, position):
    """The column's values when every row holds a plain number (not a percentage)."""
    cells = [row.get(position, {}) for row in rows]
    if not cells or not all(finite(cell.get("value")) for cell in cells):
        return None
    if any("%" in str(cell.get("number_format", "")) for cell in cells):
        return None
    return [float(cell["value"]) for cell in cells]


def texts(rows, position):
    values = [row.get(position, {}).get("value") for row in rows]
    return [" ".join(value.split()) for value in values] if all(isinstance(v, str) and v.strip()
                                                               for v in values) else None


def span(table, rows, position):
    """The cited range of a column over the given rows."""
    cells = [row[position]["cell"] for row in rows if position in row]
    return reference(table["sheet"], f"{cells[0]}:{cells[-1]}" if len(cells) > 1 else cells[0])


def heading(table, position, row=-1):
    cell = table["header"][row].get(position) or next(
        (line[position] for line in reversed(table["header"]) if position in line), None)
    return reference(table["sheet"], cell["cell"]) if cell else None


def amount(value, unit=""):
    """A value as shown; its unit is said once per sentence by noted(), not after every number."""
    return number(round(value, 2))


def noted(fact, unit):
    """'... 증가했습니다(단위: 백만원).' — the table's unit written once, at the end."""
    return f"{fact[:-1]}(단위: {unit})." if unit and fact.endswith(".") else fact


def change(before, after, unit="", ending="했습니다"):
    """'1,176에서 666으로 510(43.4%) 감소했습니다' — the change between two values, ending as asked."""
    from app.services.insights.narratives.narrative_values import direction_particle
    shown = amount(after, unit)
    start = f"{amount(before, unit)}에서 {shown}{direction_particle(shown)}"
    if after == before:
        return f"{start} 변동이 없{'었습니다' if ending == '했습니다' else '어'}"
    rate = f"({abs(after - before) / abs(before) * 100:.1f}%)" if before else ""
    return f"{start} {amount(abs(after - before), unit)}{rate} {'증가' if after > before else '감소'}{ending}"
