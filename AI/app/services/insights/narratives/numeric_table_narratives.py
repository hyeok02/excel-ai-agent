"""Literal ranges for complete numeric tables without a narrative-specific shape.

Never assume that rows are additive, that a numeric code is a measurement, or
that a first record is the workbook's subject. Headers and source ranges bind
each column; mixed text/error columns and incomplete tables are left alone.
"""
import re

from openpyxl.utils.cell import range_boundaries

from app.services.insights.facts.sheet_scope import narrative_sheet_groups
from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.narratives.narrative_values import finite, insight, number, reference
from app.services.insights.narratives.record_display import display_value


def numeric_table_report(context):
    primary, comparisons = narrative_sheet_groups(context)
    for _, sheet in primary or comparisons:
        items = _sheet_report(sheet)
        if items:
            return items, " ".join(item.fact for item in items[:2])
    return [], ""


def _sheet_report(sheet):
    name = str(sheet.get("name", ""))
    regions = list(narrative_regions(sheet.get("business_facts", {})))
    schemas = sheet.get("column_schema_samples", [])
    cells = [cell for region in regions for row in region.get("rows", []) for cell in row]
    items = []
    for region in regions:
        rows = region.get("rows", [])
        if len(rows) < 3 or region.get("rows_complete") is False:
            continue
        for schema in schemas:
            if schema.get("data_type") != "number" or schema.get("standard_field") in {"identifier", "date", "year"}:
                continue
            label = str(schema.get("display_name") or "").strip()
            path = schema.get("header_path") or [label]
            source_range = str(schema.get("source_range") or "")
            selected = [cell for row in rows for cell in row
                        if re.sub(r"[\d$]", "", str(cell.get("cell", ""))) == schema.get("column")
                        and cell.get("value") not in (None, "")]
            if not label or len(selected) < 3 or not all(finite(cell.get("value")) for cell in selected):
                continue
            if not all(_inside(cell.get("cell", ""), source_range) for cell in selected):
                continue
            headers = [cell for cell in cells
                       if cell.get("value") in path and _inside(cell.get("cell", ""), source_range)
                       and _row(cell) < min(_row(value) for value in selected)]
            if not set(path) <= {cell.get("value") for cell in headers}:
                continue
            percent = ["%" in str(cell.get("number_format", "")) for cell in selected]
            if any(percent) and not all(percent):
                continue
            low = min(selected, key=lambda cell: cell["value"])
            high = max(selected, key=lambda cell: cell["value"])
            start = min(selected, key=_row)["cell"]
            end = max(selected, key=_row)["cell"]
            items.append(insight(
                f"{label} 값 범위",
                f"‘{name}’ 시트의 ‘{label}’ 열에서 숫자로 기록된 {number(len(selected))}개 값의 "
                f"범위는 {display_value(low)}~{display_value(high)}입니다.",
                [*(reference(name, cell["cell"]) for cell in headers), reference(name, f"{start}:{end}")],
                "metric", topic=label,
            ))
            if len(items) >= 3:
                return items
    return items


def _row(cell):
    return int(re.sub(r"\D", "", str(cell.get("cell", ""))) or 0)


def _inside(address, source_range):
    try:
        left, top, right, bottom = range_boundaries(source_range)
        cell_left, cell_top, _, _ = range_boundaries(address)
        return left <= cell_left <= right and top <= cell_top <= bottom
    except (ValueError, TypeError):
        return False
