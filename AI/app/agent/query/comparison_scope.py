import re
from dataclasses import dataclass
from datetime import datetime

from app.agent.query.index import IndexedRow
from app.services.workbook_parsing.models import WorkbookSummary


GROUP_ALIASES = {
    "department": {"department", "departments", "부서", "부문"},
    "role": {"role", "roles", "직무", "역할"},
}
DECREASE_WORDS = ("감소", "줄어", "하락", "decreas", "declin", "drop", "fell")
INCREASE_WORDS = ("증가", "늘어", "상승", "increas", "growth", "grew", "rise")


@dataclass(frozen=True)
class ComparisonScope:
    metric_group: str | None
    columns_by_sheet: dict[str, dict[str, tuple[str, ...]]]


def comparison_scope(summary: WorkbookSummary, question: str) -> ComparisonScope:
    group = requested_metric_group(question)
    if group is None:
        return ComparisonScope(None, {})
    aliases = GROUP_ALIASES[group]
    columns: dict[str, dict[str, tuple[str, ...]]] = {}
    for sheet in summary.sheets:
        selected = {
            schema.column.upper(): tuple(schema.header_path)
            for schema in sheet.column_schemas
            if schema.header_path
            and _normalized(schema.header_path[0]) in aliases
        }
        if selected:
            columns[sheet.name] = selected
    return ComparisonScope(group, columns)


def requested_metric_group(question: str) -> str | None:
    normalized = question.casefold()
    for group, aliases in GROUP_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return group
    return None


def requested_change_direction(question: str) -> str | None:
    normalized = question.casefold()
    decrease = any(word in normalized for word in DECREASE_WORDS)
    increase = any(word in normalized for word in INCREASE_WORDS)
    if decrease == increase:
        return None
    if decrease:
        return "decrease"
    return "increase"


def rank_changes(metrics: list[dict[str, object]], direction: str | None):
    if direction == "decrease":
        candidates = [item for item in metrics if item["change"] < 0]
        return sorted(candidates, key=lambda item: item["change"])
    if direction == "increase":
        candidates = [item for item in metrics if item["change"] > 0]
        return sorted(candidates, key=lambda item: item["change"], reverse=True)
    return sorted(metrics, key=lambda item: abs(item["change"]), reverse=True)


def question_date_bounds(query: str) -> tuple[datetime | None, datetime | None]:
    matches = list(re.finditer(r"(20\d{2})\s*년?\s*(\d{1,2})?\s*월?", query))
    if len(matches) >= 2:
        return _matched_date(matches[0]), _matched_date(matches[1], end=True)
    if not matches:
        return None, None
    match = matches[0]
    if "까지" in query[match.end() : match.end() + 5]:
        return None, _matched_date(match, end=True)
    return _matched_date(match), None


def header_references(
    rows: list[IndexedRow],
    sheet_name: str,
    data_start_row: int,
    column: str,
    labels: tuple[str, ...],
) -> list[str]:
    expected = {str(label).strip().casefold() for label in labels}
    result = []
    for row in rows:
        if row.sheet_name != sheet_name or not 0 < data_start_row - row.row_number <= 12:
            continue
        for cell in row.cells:
            if column_from_address(cell.address) == column and isinstance(
                cell.value, str
            ):
                if cell.value.strip().casefold() in expected:
                    result.append(cell.reference)
    return result


def _normalized(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def column_from_address(address: str) -> str:
    match = re.match(r"[A-Z]+", address.upper())
    return match.group(0) if match else address


def column_number(column: str) -> int:
    result = 0
    for character in column:
        result = result * 26 + ord(character) - ord("A") + 1
    return result


def normalized_label(value: object) -> str:
    return _normalized(value)


def _matched_date(match: re.Match, end: bool = False) -> datetime:
    month = int(match.group(2) or (12 if end else 1))
    day = 31 if end and match.group(2) is None else 1
    return datetime(int(match.group(1)), month, day)
