import re
from typing import Any

from app.services.insights.facts.comparable_transactions import extract_comparable_transactions
from app.services.insights.display.derived_metrics import change_score
from app.services.insights.facts.fact_labels import (
    build_fact_labels,
    header_addresses,
    is_technical_row,
)
from app.services.insights.facts.fact_records import (
    fact_value, identity_score, record_location, record_score,
)
from app.services.insights.facts.fact_trends import date_value, numeric_changes
from app.services.insights.facts.horizontal_series import extract_horizontal_series
from app.services.insights.facts.region_rows import visible_region_rows
from app.services.insights.facts.table_inputs import build_table_regions, legacy_table_rows

MAX_VALUES_PER_ROW = 10


def build_business_facts(
    sheet_name: str,
    regions: list[dict[str, Any]],
    column_schemas: list[dict[str, Any]],
    max_records: int,
) -> dict[str, object]:
    candidates = []
    trend_rows = []
    trend_groups = {}
    region_sources = [
        (region, *visible_region_rows(region)) for region in regions
    ]
    for region_index, (region, source_rows, region_complete) in enumerate(region_sources):
        visible_region = {**region, "preview_rows": source_rows}
        headers, schemas = build_fact_labels([visible_region], column_schemas)
        header_cells = header_addresses([visible_region])
        region_title = region.get("title")
        role = _semantic_role(region)
        for row in source_rows:
            if is_technical_row(row) or any(
                str(cell.get("address")) in header_cells for cell in row
            ):
                continue
            values = [fact_value(cell, headers, schemas) for cell in row]
            values = [value for value in values if value is not None]
            if not values:
                continue
            record = {
                "location": record_location(sheet_name, values),
                "region": region_title,
                "values": values[:MAX_VALUES_PER_ROW],
            }
            candidates.append(
                (record_score(values, role), identity_score(values), record)
            )
            if region_complete and date_value(values[0]["value"]) and len(values) > 1:
                scope = _trend_scope(regions, region_index, values)
                trend_record = {**record, "_trend_scope": scope}
                trend_rows.append(trend_record)
                trend_groups.setdefault(scope, []).append(trend_record)
    candidates.sort(key=lambda item: item[0], reverse=True)
    identities = sorted(
        (item for item in candidates if item[1]),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )[:2]
    selected = identities + [item for item in candidates if item not in identities]
    records = [record for _, _, record in selected[:max_records]]
    changes = [change for rows in trend_groups.values() for change in numeric_changes(rows)]
    tables = build_table_regions(regions)
    complete_regions = [
        {**region, "analysis_rows": rows}
        for region, rows, complete in region_sources if complete
    ]
    return {
        "selected_records": records,
        "numeric_changes": sorted(changes, key=change_score, reverse=True)[:4],
        "horizontal_series": extract_horizontal_series(complete_regions),
        "comparable_transactions": extract_comparable_transactions(
            sheet_name, complete_regions
        ),
        "time_series": trend_rows,
        "table_rows": legacy_table_rows(tables),
        "table_regions": tables,
        "table_analysis_complete": (
            len(tables) == len(regions)
            and all(table.get("rows_complete") for table in tables)
        ),
        "selection_note": "원본 전체가 아닌 핵심 값 행만 선별한 결과",
    }


def _trend_scope(regions, region_index, values):
    signature = tuple(
        (re.match(r"[A-Z]+", str(value.get("cell", ""))).group(0), value.get("label"))
        for value in values if re.match(r"[A-Z]+", str(value.get("cell", "")))
    )
    for previous in reversed(regions[:region_index + 1]):
        if _semantic_role(previous) in {"title", "description"} and previous.get("title"):
            return " ".join(str(previous["title"]).split()), signature
    return region_index, signature


def _semantic_role(region: dict[str, Any]) -> str | None:
    semantic = region.get("semantic")
    return str(semantic.get("role")) if isinstance(semantic, dict) else None
