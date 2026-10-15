import re
from collections import defaultdict
from datetime import datetime

from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_headers import (
    HEADER_LOOKBACK_ROWS,
    HeaderContext,
    header_for,
)

SeriesKey = tuple[str, str]
SeriesPoint = tuple[datetime, IndexedRow]
DATE_HEADERS = ("date", "period", "month", "year", "날짜", "일자", "기간", "기준월")


def time_series_candidates(
    rows: list[IndexedRow],
    headers: HeaderContext,
    bounds: tuple[datetime | None, datetime | None],
) -> list[tuple[SeriesKey, list[SeriesPoint]]]:
    start, end = bounds
    series: dict[SeriesKey, list[SeriesPoint]] = defaultdict(list)
    for row in rows:
        for cell in row.cells:
            header = header_for(headers, row.sheet_name, row.row_number, cell.address)
            parsed = _date(cell.value) if header and _date_header(header) else None
            if parsed:
                key = (row.sheet_name, _column(cell.address))
                series[key].append((parsed, row))

    candidates = []
    for key, points in series.items():
        for run in _row_runs(points):
            filtered = [
                point for point in run
                if (start is None or point[0] >= start)
                and (end is None or point[0] <= end)
            ]
            unique = {date: row for date, row in filtered}
            if len(unique) >= 2 or unique and start is not None and end is not None:
                candidates.append((key, sorted(unique.items())))
    return candidates


def _row_runs(points: list[SeriesPoint]) -> list[list[SeriesPoint]]:
    runs: list[list[SeriesPoint]] = []
    for point in sorted(points, key=lambda item: item[1].row_number):
        # A header cannot describe rows beyond this gap, so neither can one table run.
        if not runs or point[1].row_number - runs[-1][-1][1].row_number > HEADER_LOOKBACK_ROWS:
            runs.append([])
        runs[-1].append(point)
    return runs


def _date(value: object) -> datetime | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return _year(int(value))
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if re.fullmatch(r"\d{4}", stripped):
        return _year(int(stripped))
    try:
        return datetime.fromisoformat(stripped)
    except ValueError:
        return None


def _year(value: int) -> datetime | None:
    if not 1900 <= value <= 9999:
        return None
    try:
        return datetime(value, 1, 1)
    except ValueError:
        return None


def _date_header(header: str) -> bool:
    normalized = header.casefold()
    return any(term in normalized for term in DATE_HEADERS)


def _column(address: str) -> str:
    match = re.match(r"[A-Z]+", address.upper())
    return match.group(0) if match else address
