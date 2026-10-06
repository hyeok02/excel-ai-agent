"""Select table headers without mistaking all-text records for a header row."""
from app.services.insights.narratives.narrative_values import finite
from app.services.insights.narratives.table_dates import column, is_date

MIN_RECORDS = 5
HEADER_PROMOTION_GAP = 0.5


def header_index(rows):
    candidates = [
        (index, row, _score(row, rows[index + 1:]))
        for index, row in enumerate(rows[:8])
        if len(rows) - index - 1 >= MIN_RECORDS and header_like(row)
    ]
    if not candidates:
        return None
    first = candidates[0]
    best = max(candidates, key=lambda item: (item[2], -item[0]))
    coverage_gain = best[2][0] - first[2][0]
    first_spans_table = _spans_active_columns(first[1], rows[first[0] + 1:])
    promote = (
        coverage_gain > 0 and _styled(best[1])
        or coverage_gain >= HEADER_PROMOTION_GAP and not first_spans_table
    )
    return best[0] if promote else first[0]


def header_like(row):
    filled = [cell for cell in row if cell.get("value") not in (None, "")]
    texts = [
        cell for cell in filled
        if isinstance(cell.get("value"), str) and cell["value"].strip()
    ]
    if len(texts) < 2 or len(texts) != len(filled):
        return False
    return not any(finite(cell.get("value")) or is_date(cell.get("value"))
                   for cell in filled)


def _score(header, records):
    named = {column(cell) for cell in header if cell.get("value") not in (None, "")}
    positions = {
        column(cell) for record in records for cell in record
        if cell.get("value") not in (None, "")
    }
    counts = {position: _coverage(position, records) for position in positions | named}
    covered = [counts[position] for position in named if counts[position] >= MIN_RECORDS]
    active = sum(count >= MIN_RECORDS for count in counts.values())
    return (len(covered) / active if active else 0, len(covered), sum(covered))


def _coverage(position, records):
    return sum(
        any(column(cell) == position and cell.get("value") not in (None, "")
            for cell in record)
        for record in records
    )


def _styled(row):
    filled = [cell for cell in row if cell.get("value") not in (None, "")]
    return bool(filled) and sum(bool(cell.get("bold")) for cell in filled) * 2 >= len(filled)


def _spans_active_columns(header, records):
    named = {column(cell) for cell in header if cell.get("value") not in (None, "")}
    positions = {
        column(cell) for record in records for cell in record
        if cell.get("value") not in (None, "")
    }
    active = sorted(
        position for position in positions
        if _coverage(position, records) >= MIN_RECORDS
    )
    return bool(active) and active[0] in named and active[-1] in named
