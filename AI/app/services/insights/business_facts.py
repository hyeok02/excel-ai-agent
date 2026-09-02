from typing import Any

from app.services.insights.fact_labels import (
    build_fact_labels,
    header_addresses,
    is_technical_row,
    resolve_fact_label,
)
from app.services.insights.fact_trends import (
    date_value,
    is_identity_row,
    numeric_changes,
)

MAX_VALUES_PER_ROW = 10


def build_business_facts(
    sheet_name: str,
    regions: list[dict[str, Any]],
    column_schemas: list[dict[str, Any]],
    max_records: int,
) -> dict[str, object]:
    headers, schemas = build_fact_labels(regions, column_schemas)
    header_cells = header_addresses(regions)
    candidates = []
    trend_rows = []
    for region in regions:
        region_title = region.get("title")
        role = _semantic_role(region)
        for row in region.get("preview_rows", []):
            if is_technical_row(row) or any(
                str(cell.get("address")) in header_cells for cell in row
            ):
                continue
            values = [_fact_value(cell, headers, schemas) for cell in row]
            values = [value for value in values if value is not None]
            if not values:
                continue
            record = {
                "location": _location(sheet_name, values),
                "region": region_title,
                "values": values[:MAX_VALUES_PER_ROW],
            }
            candidates.append(
                (_record_score(values, role), _identity_score(values), record)
            )
            if date_value(values[0]["value"]) and len(values) > 1:
                trend_rows.append(record)
    candidates.sort(key=lambda item: item[0], reverse=True)
    identities = sorted(
        (item for item in candidates if item[1]),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )[:2]
    selected = identities + [item for item in candidates if item not in identities]
    records = [record for _, _, record in selected[:max_records]]
    return {
        "selected_records": records,
        "numeric_changes": numeric_changes(trend_rows),
        "selection_note": "원본 전체가 아닌 핵심 값 행만 선별한 결과",
    }


def _fact_value(
    cell: dict[str, Any],
    headers: dict[str, list[tuple[int, str]]],
    schemas: list[tuple[int, int, int, str]],
) -> dict[str, object] | None:
    raw = cell.get("cached_value") if cell.get("formula") else cell.get("value")
    if raw in (None, "") or str(raw).startswith("<openpyxl"):
        return None
    text = str(raw)
    if text == "#PEND" or len(text) > 240:
        return None
    address = str(cell.get("address", ""))
    return {
        "cell": address,
        "label": resolve_fact_label(address, headers, schemas),
        "value": raw,
        "number_format": cell.get("number_format"),
    }


def _record_score(values: list[dict[str, object]], role: str | None) -> int:
    numeric = sum(isinstance(value["value"], (int, float)) for value in values)
    dated = sum(date_value(value["value"]) is not None for value in values)
    labeled = sum(bool(value.get("label")) for value in values)
    identifier = _identity_score(values)
    role_score = {"output": 8, "data": 6, "calculation": 4}.get(role, 0)
    return (
        role_score
        + numeric * 4
        + dated * 3
        + labeled * 2
        + len(values)
        + identifier * 10
    )


def _identity_score(values: list[dict[str, object]]) -> int:
    """대상을 적어 둔 식별 행을 행의 모양으로 찾는다."""
    return 2 if is_identity_row(values) else 0


def _semantic_role(region: dict[str, Any]) -> str | None:
    semantic = region.get("semantic")
    return str(semantic.get("role")) if isinstance(semantic, dict) else None


def _location(sheet_name: str, values: list[dict[str, object]]) -> str:
    first = values[0]["cell"]
    last = values[-1]["cell"]
    reference = first if first == last else f"{first}:{last}"
    return f"{sheet_name}!{reference}"
