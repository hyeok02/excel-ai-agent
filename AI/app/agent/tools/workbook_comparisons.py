import re
from datetime import datetime

from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_comparison_series import time_series_candidates
from app.agent.tools.workbook_headers import HeaderContext, header_for


def build_time_series_comparison(
    rows: list[IndexedRow], headers: HeaderContext, query: str
) -> dict[str, object] | None:
    candidates = time_series_candidates(rows, headers, _question_date(query))
    if not candidates:
        return None
    (sheet_name, date_column), points = max(candidates, key=lambda item: len(item[1]))
    start_date, start_row = points[0]
    end_date, end_row = points[-1]
    metrics = _metric_changes(start_row, end_row, date_column, headers)
    if not metrics:
        return None
    return {
        "sheet_name": sheet_name,
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "start_reference": f"{sheet_name}!{date_column}{start_row.row_number}",
        "end_reference": f"{sheet_name}!{date_column}{end_row.row_number}",
        "metrics": metrics,
        "largest_absolute_changes": sorted(
            metrics, key=lambda item: abs(item["change"]), reverse=True
        )[:5],
    }


def time_series_calculations(
    comparison: dict[str, object] | None,
) -> list[dict[str, object]]:
    if not comparison or not isinstance(comparison.get("metrics"), list):
        return []
    calculations = []
    metrics = comparison.get("largest_absolute_changes") or comparison["metrics"]
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        start = metric.get("start_value")
        end = metric.get("end_value")
        references = [metric.get("start_reference"), metric.get("end_reference")]
        numeric = all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            for item in (start, end)
        )
        if not all(isinstance(item, str) for item in references) or not numeric:
            continue
        common = {
            "operand_references": references,
            "operand_values": [start, end],
            "label": metric.get("header"),
        }
        calculations.append(
            {
                **common,
                "operation": "difference",
                "result": metric.get("change"),
                "unit": "source_unit",
            }
        )
        if float(start) != 0:
            calculations.append(
                {
                    **common,
                    "operation": "percent_change",
                    "result": (float(end) - float(start)) / abs(float(start)) * 100,
                    "unit": "percent",
                }
            )
    return calculations


def _metric_changes(
    start_row: IndexedRow,
    end_row: IndexedRow,
    date_column: str,
    headers: HeaderContext,
) -> list[dict[str, object]]:
    end_cells = {_column(cell.address): cell for cell in end_row.cells}
    metrics = []
    for start in start_row.cells:
        column = _column(start.address)
        end = end_cells.get(column)
        header = header_for(headers, start_row.sheet_name, start_row.row_number, start.address)
        if (
            _column_number(column) <= _column_number(date_column)
            or not header
            or not _number(start)
            or end is None
            or not _number(end)
        ):
            continue
        metrics.append(
            {
                "header": header,
                "start_value": start.value,
                "end_value": end.value,
                "change": round(float(end.value) - float(start.value), 10),
                "start_reference": start.reference,
                "end_reference": end.reference,
            }
        )
    return metrics


def _question_date(query: str) -> datetime | None:
    match = re.search(r"(20\d{2})\s*년?\s*(\d{1,2})?\s*월?", query)
    if not match:
        return None
    return datetime(int(match.group(1)), int(match.group(2) or 1), 1)


def _number(cell: IndexedCell) -> bool:
    return isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool)


def _column(address: str) -> str:
    return re.match(r"[A-Z]+", address.upper()).group(0)


def _column_number(column: str) -> int:
    result = 0
    for character in column:
        result = result * 26 + ord(character) - ord("A") + 1
    return result
