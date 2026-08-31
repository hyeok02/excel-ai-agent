import re
from collections import defaultdict
from datetime import datetime

from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_headers import HeaderContext, header_for


def build_time_series_comparison(
    rows: list[IndexedRow], headers: HeaderContext, query: str
) -> dict[str, object] | None:
    series: dict[tuple[str, str], list[tuple[datetime, IndexedRow]]] = defaultdict(list)
    for row in rows:
        for cell in row.cells:
            header = header_for(headers, row.sheet_name, row.row_number, cell.address)
            parsed = _date(cell.value) if header and "date" in header.casefold() else None
            if parsed:
                series[(row.sheet_name, _column(cell.address))].append((parsed, row))
    threshold = _question_date(query)
    candidates = []
    for key, points in series.items():
        filtered = [point for point in points if threshold is None or point[0] >= threshold]
        unique = {point[0]: point[1] for point in filtered}
        if len(unique) >= 2:
            candidates.append((key, sorted(unique.items())))
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
        "metrics": metrics,
        "largest_absolute_changes": sorted(
            metrics, key=lambda item: abs(item["change"]), reverse=True
        )[:5],
    }


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


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _number(cell: IndexedCell) -> bool:
    return isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool)


def _column(address: str) -> str:
    return re.match(r"[A-Z]+", address.upper()).group(0)


def _column_number(column: str) -> int:
    result = 0
    for character in column:
        result = result * 26 + ord(character) - ord("A") + 1
    return result
