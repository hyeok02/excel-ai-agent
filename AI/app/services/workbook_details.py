from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import TypeAlias

from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook

from app.services.region_detector import CellRegion

CellValue: TypeAlias = str | int | float | bool | None

REGION_PREVIEW_ROWS = 8
REGION_PREVIEW_COLUMNS = 8
TABLE_PREVIEW_ROWS = 8
TABLE_PREVIEW_COLUMNS = 12
CHART_SERIES_LIMIT = 12
CHART_SAMPLE_VALUES = 12


@dataclass(frozen=True)
class CellSnapshot:
    address: str
    value: CellValue
    formula: str | None


@dataclass(frozen=True)
class RegionSummary:
    start_cell: str
    end_cell: str
    cell_count: int
    preview_rows: list[list[CellSnapshot]]
    is_truncated: bool


@dataclass(frozen=True)
class TableSummary:
    name: str
    display_name: str
    reference: str
    headers: list[str]
    row_count: int
    column_count: int
    preview_rows: list[list[CellSnapshot]]
    is_truncated: bool


@dataclass(frozen=True)
class ChartSeriesSummary:
    title: str | None
    categories_reference: str | None
    values_reference: str | None
    category_samples: list[CellValue]
    value_samples: list[CellValue]


@dataclass(frozen=True)
class ChartSummary:
    title: str | None
    chart_type: str
    anchor_cell: str | None
    series_count: int
    series: list[ChartSeriesSummary]
    is_truncated: bool


def summarize_regions(
    worksheet: Worksheet,
    regions: list[CellRegion],
) -> list[RegionSummary]:
    summaries: list[RegionSummary] = []

    for region in regions:
        min_column, min_row, max_column, max_row = range_boundaries(
            f"{region.start_cell}:{region.end_cell}"
        )
        preview_max_row = min(max_row, min_row + REGION_PREVIEW_ROWS - 1)
        preview_max_column = min(
            max_column,
            min_column + REGION_PREVIEW_COLUMNS - 1,
        )
        summaries.append(
            RegionSummary(
                start_cell=region.start_cell,
                end_cell=region.end_cell,
                cell_count=region.cell_count,
                preview_rows=_snapshot_range(
                    worksheet,
                    min_row,
                    preview_max_row,
                    min_column,
                    preview_max_column,
                ),
                is_truncated=(
                    preview_max_row < max_row or preview_max_column < max_column
                ),
            )
        )

    return summaries


def summarize_tables(worksheet: Worksheet) -> list[TableSummary]:
    summaries: list[TableSummary] = []

    for table in worksheet.tables.values():
        min_column, min_row, max_column, max_row = range_boundaries(table.ref)
        preview_max_row = min(max_row, min_row + TABLE_PREVIEW_ROWS - 1)
        preview_max_column = min(
            max_column,
            min_column + TABLE_PREVIEW_COLUMNS - 1,
        )
        summaries.append(
            TableSummary(
                name=table.name,
                display_name=table.displayName,
                reference=table.ref,
                headers=[column.name for column in table.tableColumns],
                row_count=max_row - min_row + 1,
                column_count=max_column - min_column + 1,
                preview_rows=_snapshot_range(
                    worksheet,
                    min_row,
                    preview_max_row,
                    min_column,
                    preview_max_column,
                ),
                is_truncated=(
                    preview_max_row < max_row or preview_max_column < max_column
                ),
            )
        )

    return summaries


def summarize_charts(workbook: Workbook, worksheet: Worksheet) -> list[ChartSummary]:
    summaries: list[ChartSummary] = []

    for chart in worksheet._charts:
        all_series = list(chart.ser)
        series_summaries = [
            _summarize_chart_series(workbook, series)
            for series in all_series[:CHART_SERIES_LIMIT]
        ]
        summaries.append(
            ChartSummary(
                title=_chart_title(chart),
                chart_type=type(chart).__name__,
                anchor_cell=_chart_anchor(chart),
                series_count=len(all_series),
                series=series_summaries,
                is_truncated=len(all_series) > CHART_SERIES_LIMIT,
            )
        )

    return summaries


def _snapshot_range(
    worksheet: Worksheet,
    min_row: int,
    max_row: int,
    min_column: int,
    max_column: int,
) -> list[list[CellSnapshot]]:
    return [
        [_snapshot_cell(worksheet.cell(row=row, column=column)) for column in range(min_column, max_column + 1)]
        for row in range(min_row, max_row + 1)
    ]


def _snapshot_cell(cell: object) -> CellSnapshot:
    address = str(getattr(cell, "coordinate"))
    raw_value = getattr(cell, "value", None)
    is_formula = getattr(cell, "data_type", None) == "f" and isinstance(
        raw_value, str
    )
    return CellSnapshot(
        address=address,
        value=None if is_formula else _json_value(raw_value),
        formula=raw_value if is_formula else None,
    )


def _json_value(value: object) -> CellValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _summarize_chart_series(
    workbook: Workbook,
    series: object,
) -> ChartSeriesSummary:
    title_reference = _nested_attr(series, "tx", "strRef", "f")
    title_value = _nested_attr(series, "tx", "v")
    categories_reference = (
        _nested_attr(series, "cat", "strRef", "f")
        or _nested_attr(series, "cat", "numRef", "f")
        or _nested_attr(series, "cat", "multiLvlStrRef", "f")
    )
    values_reference = _nested_attr(series, "val", "numRef", "f")
    resolved_title = _resolve_reference_values(workbook, title_reference, 1)

    return ChartSeriesSummary(
        title=(
            str(resolved_title[0])
            if resolved_title and resolved_title[0] is not None
            else str(title_value) if title_value is not None else None
        ),
        categories_reference=_string_or_none(categories_reference),
        values_reference=_string_or_none(values_reference),
        category_samples=_resolve_reference_values(
            workbook,
            categories_reference,
            CHART_SAMPLE_VALUES,
        ),
        value_samples=_resolve_reference_values(
            workbook,
            values_reference,
            CHART_SAMPLE_VALUES,
        ),
    )


def _resolve_reference_values(
    workbook: Workbook,
    reference: object,
    limit: int,
) -> list[CellValue]:
    if not isinstance(reference, str) or "!" not in reference or "[" in reference:
        return []

    sheet_token, range_token = reference.lstrip("=").rsplit("!", 1)
    sheet_name = sheet_token.strip("'").replace("''", "'")
    if sheet_name not in workbook.sheetnames:
        return []

    try:
        min_column, min_row, max_column, max_row = range_boundaries(
            range_token.replace("$", "")
        )
    except ValueError:
        return []

    values: list[CellValue] = []
    worksheet = workbook[sheet_name]
    for row in worksheet.iter_rows(
        min_row=min_row,
        max_row=max_row,
        min_col=min_column,
        max_col=max_column,
    ):
        for cell in row:
            values.append(_json_value(cell.value))
            if len(values) == limit:
                return values
    return values


def _chart_title(chart: object) -> str | None:
    title = getattr(chart, "title", None)
    if isinstance(title, str):
        return title

    rich_text = _nested_attr(title, "tx", "rich")
    paragraphs = getattr(rich_text, "p", []) if rich_text is not None else []
    parts: list[str] = []
    for paragraph in paragraphs:
        for run in getattr(paragraph, "r", []) or []:
            text = getattr(run, "t", None)
            if text:
                parts.append(str(text))
        for field in getattr(paragraph, "fld", []) or []:
            text = getattr(field, "t", None)
            if text:
                parts.append(str(text))
    return "".join(parts) or None


def _chart_anchor(chart: object) -> str | None:
    marker = getattr(getattr(chart, "anchor", None), "_from", None)
    row = getattr(marker, "row", None)
    column = getattr(marker, "col", None)
    if not isinstance(row, int) or not isinstance(column, int):
        return None
    return f"{get_column_letter(column + 1)}{row + 1}"


def _nested_attr(value: object, *attributes: str) -> object | None:
    current = value
    for attribute in attributes:
        if current is None:
            return None
        current = getattr(current, attribute, None)
    return current


def _string_or_none(value: object) -> str | None:
    return str(value) if value is not None else None
