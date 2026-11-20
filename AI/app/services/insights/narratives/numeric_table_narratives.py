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
from app.services.insights.narratives.numeric_group_means import group_means
from app.services.insights.narratives.record_display import display_value

MEAN_RECORDS = 8
_TOTAL = re.compile(r"\b(?:grand\s+)?total\b|합계|총계|소계", re.I)


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
            # Each row's name is its first text cell; a total row ("합계") is not one of the values.
            names = {_row(row[0]): next((cell for cell in row if isinstance(cell.get("value"), str)
                                         and cell["value"].strip()), None) for row in rows if row}
            selected = [cell for row in rows for cell in row
                        if re.sub(r"[\d$]", "", str(cell.get("cell", ""))) == schema.get("column")
                        and cell.get("value") not in (None, "") and not _TOTAL.search(
                            str((names.get(_row(cell)) or {}).get("value", "")).strip())]
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
            # Many records (scores, ratings, prices) are read by their mean too: 만족도 평균 3.48.
            average = ({**selected[0], "value": round(sum(cell["value"] for cell in selected) / len(selected), 2)}
                       if len(selected) >= MEAN_RECORDS else None)
            # A few named rows are read by name: 618(인사팀)~1,556(영업2팀).
            named = [names.get(_row(cell)) for cell in (low, high)] if not average else [None, None]
            shown = [display_value(cell) + (f"({tag['value'].strip()})" if tag and tag is not cell else "")
                     for cell, tag in zip((low, high), named)]
            # Scores per group of a repeating category: 반별 국어 평균은 2반 81.5, 3반 74.25, 1반 59.5.
            grouped = group_means(rows, selected, cells) if average else None
            by_group = ""
            if grouped:
                category, means, labels = grouped
                listed = ", ".join(f"{group} {display_value({**selected[0], 'value': round(mean, 2)})}"
                                   for mean, group in means)
                by_group = f" {category['value'].strip()}별 평균은 {listed}로, ‘{means[0][1]}’{_subject(means[0][1])} 가장 높습니다."
            items.append(insight(
                f"{label} {'평균과 범위' if average else '값 범위'}",
                f"‘{name}’ 시트의 ‘{label}’ 열에서 숫자로 기록된 {number(len(selected))}개 값의 "
                + (f"평균은 {display_value(average)}이고, " if average else "")
                + f"범위는 {shown[0]}~{shown[1]}입니다." + by_group,
                [*(reference(name, cell["cell"]) for cell in headers), reference(name, f"{start}:{end}"),
                 *(reference(name, tag["cell"]) for tag in named if tag),
                 *([reference(name, grouped[0]["cell"]), reference(name, f"{grouped[2][0]['cell']}:{grouped[2][-1]['cell']}")]
                   if grouped else [])],
                "metric", topic=label,
            ))
            if len(items) >= 3:
                return items
    return items


def _subject(word):
    last = word[-1] if word else ""
    if "가" <= last <= "힣":
        return "이" if (ord(last) - 0xAC00) % 28 else "가"
    return "이(가)"


def _row(cell):
    return int(re.sub(r"\D", "", str(cell.get("cell", ""))) or 0)


def _inside(address, source_range):
    try:
        left, top, right, bottom = range_boundaries(source_range)
        cell_left, cell_top, _, _ = range_boundaries(address)
        return left <= cell_left <= right and top <= cell_top <= bottom
    except (ValueError, TypeError):
        return False
