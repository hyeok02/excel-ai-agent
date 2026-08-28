import re
from collections import defaultdict
from typing import Any

from openpyxl.utils import column_index_from_string, range_boundaries
from openpyxl.utils.cell import coordinate_from_string

HEADER_MARKERS = (
    "name",
    "id",
    "date",
    "total",
    "latest",
    "rate",
    "type",
    "headline",
    "industry",
    "region",
    "amount",
    "revenue",
    "employee",
    "headcount",
    "회사",
    "기업",
    "날짜",
    "합계",
    "직원",
    "매출",
)


def build_fact_labels(
    regions: list[dict[str, Any]], column_schemas: list[dict[str, Any]]
) -> tuple[dict[str, list[tuple[int, str]]], list[tuple[int, int, int, str]]]:
    headers: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for region in regions:
        for row in _region_header_rows(region):
            for cell in row:
                value = _raw_value(cell)
                if isinstance(value, str) and value.strip():
                    column, row_number = coordinate_from_string(cell["address"])
                    headers[column].append((row_number, value.strip()))
    schemas = []
    for schema in column_schemas:
        source = schema.get("source_range")
        label = schema.get("display_name")
        if not source or not label:
            continue
        min_col, min_row, max_col, max_row = range_boundaries(str(source))
        column = column_index_from_string(str(schema["column"]))
        if min_col <= column <= max_col:
            schemas.append((column, min_row, max_row, str(label)))
    return dict(headers), schemas


def header_addresses(regions: list[dict[str, Any]]) -> set[str]:
    return {
        str(cell["address"])
        for region in regions
        for row in _region_header_rows(region)
        for cell in row
    }


def is_technical_row(row: list[dict[str, Any]]) -> bool:
    texts = [str(_raw_value(cell)).strip() for cell in row if _raw_value(cell)]
    return sum(_technical_label(text) for text in texts) >= 2


def resolve_fact_label(
    address: str,
    headers: dict[str, list[tuple[int, str]]],
    schemas: list[tuple[int, int, int, str]],
) -> str | None:
    column, row = coordinate_from_string(address)
    preceding = [item for item in headers.get(column, []) if item[0] < row]
    if preceding:
        return max(preceding, key=lambda item: item[0])[1]
    column_number = column_index_from_string(column)
    for schema_column, min_row, max_row, label in schemas:
        if schema_column == column_number and min_row <= row <= max_row:
            return label
    return None


def _looks_like_header(row: list[dict[str, Any]]) -> bool:
    texts = [str(_raw_value(cell)).strip() for cell in row if _raw_value(cell)]
    if len(texts) < 2 or any(_technical_label(text) for text in texts):
        return False
    matches = sum(
        any(marker in text.casefold() for marker in HEADER_MARKERS) for text in texts
    )
    return matches >= 2


def _region_header_rows(region: dict[str, Any]) -> list[list[dict[str, Any]]]:
    rows = [row for row in region.get("preview_rows", []) if any(_raw_value(c) for c in row)]
    return [row for row in rows[:3] if _looks_like_header(row)][:2]


def _technical_label(text: str) -> bool:
    return bool(re.match(r"^(SP|MI)_[A-Z0-9_]+$", text))


def _raw_value(cell: dict[str, Any]) -> object:
    return cell.get("cached_value") if cell.get("formula") else cell.get("value")
