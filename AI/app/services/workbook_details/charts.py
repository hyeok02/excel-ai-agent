from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook

from app.services.workbook_details.cell_values import string_or_none
from app.services.workbook_details.chart_metadata import (
    chart_anchor,
    chart_title,
    nested_attr,
)
from app.services.workbook_details.chart_references import resolve_reference_values
from app.services.workbook_details.models import ChartSeriesSummary, ChartSummary

CHART_SERIES_LIMIT = 12
CHART_SAMPLE_VALUES = 12


def summarize_charts(
    workbook: Workbook,
    worksheet: Worksheet,
    value_workbook: Workbook | None = None,
) -> list[ChartSummary]:
    summaries: list[ChartSummary] = []
    for chart in worksheet._charts:
        all_series = list(chart.ser)
        series_summaries = [
            _summarize_chart_series(value_workbook or workbook, series)
            for series in all_series[:CHART_SERIES_LIMIT]
        ]
        summaries.append(
            ChartSummary(
                title=chart_title(chart),
                chart_type=type(chart).__name__,
                anchor_cell=chart_anchor(chart),
                series_count=len(all_series),
                series=series_summaries,
                is_truncated=len(all_series) > CHART_SERIES_LIMIT,
            )
        )
    return summaries


def _summarize_chart_series(
    workbook: Workbook,
    series: object,
) -> ChartSeriesSummary:
    title_reference = nested_attr(series, "tx", "strRef", "f")
    title_value = nested_attr(series, "tx", "v")
    categories_reference = (
        nested_attr(series, "cat", "strRef", "f")
        or nested_attr(series, "cat", "numRef", "f")
        or nested_attr(series, "cat", "multiLvlStrRef", "f")
    )
    values_reference = nested_attr(series, "val", "numRef", "f")
    resolved_title = resolve_reference_values(workbook, title_reference, 1)
    return ChartSeriesSummary(
        title=(
            str(resolved_title[0])
            if resolved_title and resolved_title[0] is not None
            else str(title_value) if title_value is not None else None
        ),
        categories_reference=string_or_none(categories_reference),
        values_reference=string_or_none(values_reference),
        category_samples=resolve_reference_values(
            workbook, categories_reference, CHART_SAMPLE_VALUES
        ),
        value_samples=resolve_reference_values(
            workbook, values_reference, CHART_SAMPLE_VALUES
        ),
    )
